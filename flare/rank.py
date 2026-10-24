"""Trigramm-Kosinus. CPU immer, CUDA-Treiber nur wenn er wirklich rechnen kann."""

from __future__ import annotations

import ctypes
import os
import sys
import threading
from ctypes import c_int, c_uint, c_uint32, c_uint64, c_void_p, c_float, c_size_t

# PTX wird vom Treiber zur Laufzeit übersetzt. sm_50 ist die portable Basis.
_PTX = rb"""
.version 6.5
.target sm_50
.address_size 64

.visible .entry tri_cos(
    .param .u64 Q,
    .param .u32 NQ,
    .param .u64 OFFS,
    .param .u64 GRAMS,
    .param .u64 OUT,
    .param .u32 N)
{
    .reg .pred %p;
    .reg .b32 %i, %n, %nq, %tid, %ntid, %bid, %hit, %k, %g, %j, %a, %b, %tmp;
    .reg .b64 %q, %offs, %grams, %out, %ptr, %off;
    .reg .f32 %hf, %qf, %res;

    ld.param.u32 %n, [N];
    mov.u32 %tid, %tid.x;
    mov.u32 %ntid, %ntid.x;
    mov.u32 %bid, %ctaid.x;
    mul.lo.u32 %i, %bid, %ntid;
    add.u32 %i, %i, %tid;
    setp.ge.u32 %p, %i, %n;
    @%p ret;

    ld.param.u32 %nq, [NQ];
    ld.param.u64 %offs, [OFFS];
    mul.wide.u32 %off, %i, 4;
    add.u64 %ptr, %offs, %off;
    ld.global.u32 %a, [%ptr];
    add.u64 %ptr, %ptr, 4;
    ld.global.u32 %b, [%ptr];

    ld.param.u64 %q, [Q];
    ld.param.u64 %grams, [GRAMS];
    mov.u32 %hit, 0;
    mov.u32 %k, 0;

kloop:
    setp.ge.u32 %p, %k, %nq;
    @%p bra kdone;
    mul.wide.u32 %off, %k, 4;
    add.u64 %ptr, %q, %off;
    ld.global.u32 %g, [%ptr];
    mov.u32 %j, %a;

jloop:
    setp.ge.u32 %p, %j, %b;
    @%p bra knext;
    mul.wide.u32 %off, %j, 4;
    add.u64 %ptr, %grams, %off;
    ld.global.u32 %tmp, [%ptr];
    setp.eq.u32 %p, %tmp, %g;
    @%p bra jfound;
    add.u32 %j, %j, 1;
    bra jloop;

jfound:
    add.u32 %hit, %hit, 1;

knext:
    add.u32 %k, %k, 1;
    bra kloop;

kdone:
    cvt.rn.f32.u32 %hf, %hit;
    cvt.rn.f32.u32 %qf, %nq;
    setp.eq.u32 %p, %nq, 0;
    mov.f32 %res, 0f;
    @%p bra store;
    div.rn.f32 %res, %hf, %qf;

store:
    ld.param.u64 %out, [OUT];
    mul.wide.u32 %off, %i, 4;
    add.u64 %ptr, %out, %off;
    st.global.f32 [%ptr], %res;
    ret;
}
"""


def trigrams(text: str) -> list[int]:
    raw = text.casefold().encode("utf-8", "ignore")
    if len(raw) < 3:
        return []
    seen: set[int] = set()
    out: list[int] = []
    for index in range(len(raw) - 2):
        value = raw[index] | (raw[index + 1] << 8) | (raw[index + 2] << 16)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def overlap_scores(query_grams: list[int], name_grams: list[list[int]]) -> list[float]:
    """Anteil der Such-Trigramme, die im Namen vorkommen. Stabil bei Tippfehlern."""
    query_set = set(query_grams)
    width = len(query_set)
    scores: list[float] = []
    for grams in name_grams:
        if width == 0:
            scores.append(0.0)
            continue
        name_set = set(grams)
        overlap = sum(1 for gram in query_set if gram in name_set)
        scores.append(overlap / width)
    return scores


def dice_scores(query_grams: list[int], name_grams: list[list[int]]) -> list[float]:
    """Sørensen-Dice über Trigramme. Symmetrisch, damit nahe Namen beiderseits treffen."""
    query_set = set(query_grams)
    width = len(query_set)
    scores: list[float] = []
    for grams in name_grams:
        name_set = set(grams)
        union = width + len(name_set)
        if union == 0:
            scores.append(0.0)
            continue
        overlap = sum(1 for gram in query_set if gram in name_set)
        scores.append((2.0 * overlap) / union)
    return scores


class _CudaRanker:
    """Driver-API ohne Toolkit. Ein Kontext, ein Modul, kurze Läufe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        name = "nvcuda.dll" if sys.platform == "win32" else "libcuda.so.1"
        self.lib = ctypes.CDLL(name)
        self._bind()
        rc = self.lib.cuInit(0)
        if rc != 0:
            raise OSError(f"cuInit {rc}")
        count = c_int()
        rc = self.lib.cuDeviceGetCount(ctypes.byref(count))
        if rc != 0 or count.value < 1:
            raise OSError("no cuda device")
        device = c_int()
        if self.lib.cuDeviceGet(ctypes.byref(device), 0) != 0:
            raise OSError("cuDeviceGet")
        self.ctx = c_void_p()
        if self.lib.cuDevicePrimaryCtxRetain(ctypes.byref(self.ctx), device) != 0:
            raise OSError("cuDevicePrimaryCtxRetain")
        if self.lib.cuCtxSetCurrent(self.ctx) != 0:
            raise OSError("cuCtxSetCurrent")
        module = c_void_p()
        if self.lib.cuModuleLoadData(ctypes.byref(module), _PTX) != 0:
            raise OSError("cuModuleLoadData")
        self.module = module
        self.fn = c_void_p()
        if self.lib.cuModuleGetFunction(ctypes.byref(self.fn), module, b"tri_cos") != 0:
            raise OSError("cuModuleGetFunction")
        self.device = device

    def _bind(self) -> None:
        lib = self.lib
        lib.cuInit.argtypes = [c_uint]
        lib.cuInit.restype = c_int
        lib.cuDeviceGetCount.argtypes = [ctypes.POINTER(c_int)]
        lib.cuDeviceGetCount.restype = c_int
        lib.cuDeviceGet.argtypes = [ctypes.POINTER(c_int), c_int]
        lib.cuDeviceGet.restype = c_int
        lib.cuDevicePrimaryCtxRetain.argtypes = [ctypes.POINTER(c_void_p), c_int]
        lib.cuDevicePrimaryCtxRetain.restype = c_int
        lib.cuCtxSetCurrent.argtypes = [c_void_p]
        lib.cuCtxSetCurrent.restype = c_int
        lib.cuModuleLoadData.argtypes = [ctypes.POINTER(c_void_p), c_void_p]
        lib.cuModuleLoadData.restype = c_int
        lib.cuModuleGetFunction.argtypes = [ctypes.POINTER(c_void_p), c_void_p, c_void_p]
        lib.cuModuleGetFunction.restype = c_int
        lib.cuMemAlloc.argtypes = [ctypes.POINTER(c_uint64), c_size_t]
        lib.cuMemAlloc.restype = c_int
        lib.cuMemFree.argtypes = [c_uint64]
        lib.cuMemFree.restype = c_int
        lib.cuMemcpyHtoD.argtypes = [c_uint64, c_void_p, c_size_t]
        lib.cuMemcpyHtoD.restype = c_int
        lib.cuMemcpyDtoH.argtypes = [c_void_p, c_uint64, c_size_t]
        lib.cuMemcpyDtoH.restype = c_int
        lib.cuLaunchKernel.argtypes = [
            c_void_p,
            c_uint, c_uint, c_uint,
            c_uint, c_uint, c_uint,
            c_uint,
            c_void_p,
            ctypes.POINTER(c_void_p),
            c_void_p,
        ]
        lib.cuLaunchKernel.restype = c_int
        lib.cuCtxSynchronize.argtypes = []
        lib.cuCtxSynchronize.restype = c_int

    def _copy(self, values: list[int], kind: type[ctypes._SimpleCData]) -> c_uint64:
        if not values and kind is c_uint32:
            values = [0]
        array = (kind * len(values))(*values)
        ptr = c_uint64()
        rc = self.lib.cuMemAlloc(ctypes.byref(ptr), ctypes.sizeof(array))
        if rc != 0:
            raise OSError(f"cuMemAlloc {rc}")
        rc = self.lib.cuMemcpyHtoD(ptr.value, ctypes.cast(array, c_void_p), ctypes.sizeof(array))
        if rc != 0:
            self.lib.cuMemFree(ptr.value)
            raise OSError(f"cuMemcpyHtoD {rc}")
        return ptr

    def score(self, query_grams: list[int], name_grams: list[list[int]]) -> list[float]:
        count = len(name_grams)
        if count == 0 or not query_grams:
            return [0.0] * count
        offs = [0]
        flat: list[int] = []
        for grams in name_grams:
            flat.extend(grams)
            offs.append(len(flat))
        if not flat:
            flat = [0]
        with self._lock:
            if self.lib.cuCtxSetCurrent(self.ctx) != 0:
                raise OSError("cuCtxSetCurrent")
            buffers: list[c_uint64] = []
            try:
                d_q = self._copy(query_grams, c_uint32)
                d_offs = self._copy(offs, c_uint32)
                d_grams = self._copy(flat, c_uint32)
                d_out = c_uint64()
                out_bytes = count * ctypes.sizeof(c_float)
                if self.lib.cuMemAlloc(ctypes.byref(d_out), out_bytes) != 0:
                    raise OSError("cuMemAlloc out")
                buffers.extend([d_q, d_offs, d_grams, d_out])
                nq = c_uint32(len(query_grams))
                n = c_uint32(count)
                arg_q = c_uint64(d_q.value)
                arg_offs = c_uint64(d_offs.value)
                arg_grams = c_uint64(d_grams.value)
                arg_out = c_uint64(d_out.value)
                params = (c_void_p * 6)(
                    ctypes.addressof(arg_q),
                    ctypes.addressof(nq),
                    ctypes.addressof(arg_offs),
                    ctypes.addressof(arg_grams),
                    ctypes.addressof(arg_out),
                    ctypes.addressof(n),
                )
                block = 128
                grid = (count + block - 1) // block
                rc = self.lib.cuLaunchKernel(
                    self.fn, grid, 1, 1, block, 1, 1, 0, None, params, None
                )
                if rc != 0:
                    raise OSError(f"cuLaunchKernel {rc}")
                if self.lib.cuCtxSynchronize() != 0:
                    raise OSError("cuCtxSynchronize")
                host = (c_float * count)()
                if self.lib.cuMemcpyDtoH(ctypes.cast(host, c_void_p), d_out.value, out_bytes) != 0:
                    raise OSError("cuMemcpyDtoH")
                return [float(value) for value in host]
            finally:
                for buf in buffers:
                    self.lib.cuMemFree(buf.value)

    def close(self) -> None:
        try:
            self.lib.cuDevicePrimaryCtxRelease(self.device)
        except Exception:
            return


class Ranker:
    def __init__(self, allow_cuda: bool | None = None) -> None:
        if allow_cuda is None:
            allow_cuda = os.environ.get("FLARE_FORCE_CPU") != "1"
        self.cuda_error = ""
        self._cuda: _CudaRanker | None = None
        self.mode = "cpu"
        if allow_cuda:
            try:
                self._cuda = _CudaRanker()
                self.mode = "cpu+cuda"
            except (OSError, AttributeError):
                self._cuda = None
                self.mode = "cpu"

    def close(self) -> None:
        if self._cuda is not None:
            self._cuda.close()
            self._cuda = None

    def fuzzy_scores(self, query: str, names: list[str]) -> list[float]:
        query_grams = trigrams(query)
        name_grams = [trigrams(name) for name in names]
        if (
            self._cuda is not None
            and len(names) >= 32
            and query_grams
        ):
            try:
                return self._cuda.score(query_grams, name_grams)
            except OSError as exc:
                self.cuda_error = str(exc)
                self._cuda.close()
                self._cuda = None
                self.mode = "cpu"
        return overlap_scores(query_grams, name_grams)

    def similarity_scores(self, query: str, names: list[str]) -> list[float]:
        """Nähe eines Namens zur Anfrage. Recall läuft ab 32 Kandidaten auf der GPU."""
        recall = self.fuzzy_scores(query, names)
        query_grams = trigrams(query)
        name_grams = [trigrams(name) for name in names]
        dice = dice_scores(query_grams, name_grams)
        return [max(left, right) for left, right in zip(dice, recall)]
