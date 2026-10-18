"""Zeilendebugger für Bash und PowerShell.

Bash bleibt über eine DEBUG-Trap vor der gewählten Zeile stehen.
PowerShell setzt Set-PSBreakpoint auf jede nicht leere Zeile.
Beide sprechen dasselbe Kurzprotokoll und liefern dieselbe Sitzungsform wie der Python-Debugger.
"""

from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from shatuide.scripting import powershell_binary, shell_binary


def write_breakpoints(path: Path, script: str, points: list[dict]) -> None:
    lines: list[str] = []
    script_path = Path(script)
    try:
        script_resolved = script_path.resolve()
    except OSError:
        script_resolved = script_path
    for point in points or []:
        if not isinstance(point, dict):
            continue
        file_name = str(point.get("file") or "")
        target = script_resolved
        if file_name:
            candidate = Path(file_name)
            try:
                target = candidate.resolve()
            except OSError:
                continue
        try:
            line = int(point.get("line") or 0)
        except (TypeError, ValueError):
            continue
        if line <= 0:
            continue
        condition = str(point.get("condition") or "").replace("\n", " ").replace("\t", " ").replace("\x1f", " ")
        if target == script_resolved:
            lines.append(f"{line}\t{condition}" if condition else str(line))
        else:
            lines.append(f"{line}\x1f{target}\x1f{condition}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


class _LineSession:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.events: list[dict] = []
        self.output: list[str] = []
        self.paused: dict | None = None
        self.cond = threading.Condition()
        self.returncode: int | None = None
        self.script = ""
        self.bp_file: Path | None = None
        self._locals: dict[str, str] = {}
        self._last_expr = ""
        self._closed = False

    def update_breakpoints(self, points: list[dict]) -> None:
        if self.bp_file is not None:
            write_breakpoints(self.bp_file, self.script, points)

    def command(self, payload: dict) -> None:
        cmd = str(payload.get("cmd") or "")
        expr = str(payload.get("expr") or "")
        if cmd == "eval":
            if not self.paused:
                with self.cond:
                    self.events.append({"event": "eval", "expr": expr, "error": "Keine Pause."})
                    self.cond.notify_all()
                return
            self._last_expr = expr
            self._send("EVAL " + expr.replace("\n", " "))
            return
        word = {"continue": "CONT", "step": "STEP", "step_into": "INTO", "step_out": "OUT", "stop": "STOP"}.get(cmd, "CONT")
        if cmd in {"continue", "step", "step_into", "step_out", "stop"}:
            with self.cond:
                self.paused = None
        self._send(word)

    def _send(self, text: str) -> None:
        raise NotImplementedError

    def wait_event(self, name: str, timeout: float = 8) -> dict:
        deadline = time.time() + timeout
        with self.cond:
            while time.time() < deadline:
                for event in self.events:
                    if event.get("event") == name:
                        return event
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self.cond.wait(timeout=min(0.2, remaining))
        raise TimeoutError(name)

    def snapshot(self, output_from: int = 0) -> dict:
        with self.cond:
            running = self.proc is not None and self.proc.poll() is None
            return {
                "ok": True,
                "running": running,
                "paused": self.paused,
                "events": self.events[-40:],
                "output": self.output[output_from:],
                "output_next": len(self.output),
                "returncode": self.returncode if not running else None,
            }

    def _append_output(self, line: str) -> None:
        with self.cond:
            self.output.append(line)
            if len(self.output) > 4000:
                self.output = self.output[-3000:]
            self.cond.notify_all()

    def _finish(self, code: int | None) -> None:
        with self.cond:
            self.returncode = code
            self.paused = None
            self.events.append({"event": "terminated", "code": code})
            self.cond.notify_all()

    def _on_protocol(self, line: str) -> None:
        if line.startswith("STOP") or line.startswith("ERR"):
            self._locals = {}
            error = line.startswith("ERR")
            payload = line[3:].lstrip(" \t") if error else line[4:].lstrip(" \t")
            message = ""
            if error and payload.count("\t") >= 2:
                number_text, filename, message = payload.split("\t", 2)
            elif "\t" in payload:
                number_text, _, filename = payload.partition("\t")
            else:
                parts = payload.split()
                number_text = parts[0] if parts else "0"
                filename = ""
            try:
                number = int(number_text)
            except ValueError:
                number = 0
            with self.cond:
                self._pending_line = number
                self._pending_file = filename or self.script
                self._pending_reason = "exception" if error else "breakpoint"
                self._pending_exception = message
            return
        if line.startswith("VAR "):
            name, _, value = line[4:].partition(" ")
            if name and len(self._locals) < 40:
                self._locals[name] = value[:180]
            return
        if line == "END":
            with self.cond:
                number = getattr(self, "_pending_line", 0)
                self.paused = {
                    "event": "stopped",
                    "line": number,
                    "file": getattr(self, "_pending_file", "") or self.script,
                    "reason": getattr(self, "_pending_reason", "") or "breakpoint",
                    "locals": dict(self._locals),
                }
                if getattr(self, "_pending_exception", ""):
                    self.paused["exception"] = self._pending_exception
                self._pending_reason = "breakpoint"
                self._pending_exception = ""
                self.events.append(self.paused)
                self.cond.notify_all()
            return
        if line.startswith("EVAL "):
            with self.cond:
                self.events.append({"event": "eval", "expr": self._last_expr, "value": line[5:]})
                self.cond.notify_all()
            return
        if line == "DONE":
            self._finish(0)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.paused:
                self._send("STOP")
        except OSError:
            pass
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.proc is not None:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass


_BASH = r"""
SHATU_IN=0
SHATU_MODE=run
SHATU_DEPTH=0
shatu_vars() {
  local names name value count=0
  names=$(compgen -A variable 2>/dev/null) || return 0
  local IFS=$'\n'
  for name in $names; do
    case "$name" in
      SHATU_*|BASH_*|FUNCNAME|DIRSTACK|GROUPS|_|PIPESTATUS|BASHOPTS|SHELLOPTS|BASH_VERSINFO|BASH_ARGC|BASH_ARGV|BASH_LINENO|BASH_SOURCE|BASH_CMDS|COMP_*|EPOCH*|[A-Z]*) continue ;;
    esac
    value="${!name-}"
    value=${value//$'\n'/ }
    printf 'VAR %s %s\n' "$name" "${value:0:180}" >&4
    count=$((count + 1))
    [[ $count -ge 40 ]] && break
  done
}
shatu_hook() {
  [[ "${SHATU_IN:-0}" == 1 ]] && return 0
  SHATU_IN=1
  trap - DEBUG
  local line="${BASH_LINENO[0]}"
  local src="${BASH_SOURCE[1]}"
  if [[ -n "$src" && "$src" != /* ]]; then
    src="$(cd "$(dirname "$src")" 2>/dev/null && pwd)/$(basename "$src")"
  fi
  local allowed=0
  case "$src" in
    "$SHATU_SCRIPT"|"$SHATU_DIR"|"$SHATU_DIR"/*) allowed=1 ;;
  esac
  if [[ $allowed == 1 ]]; then
    local stop=0
    local depth=$(( ${#FUNCNAME[@]} - 1 ))
    if [[ "$SHATU_MODE" == step ]]; then stop=1; fi
    if [[ "$SHATU_MODE" == out && "$depth" -lt "$SHATU_DEPTH" ]]; then stop=1; fi
    if [[ -f "$SHATU_BP" ]]; then
      local entry n cond bfile
      while IFS= read -r entry || [[ -n "$entry" ]]; do
        if [[ "$entry" == *$'\x1f'* ]]; then
          IFS=$'\x1f' read -r n bfile cond <<<"$entry"
        else
          n=${entry%%$'\t'*}
          bfile=
          if [[ "$entry" == *$'\t'* ]]; then cond=${entry#*$'\t'}; else cond=; fi
        fi
        [[ "$n" == "$line" ]] || continue
        if [[ -n "$bfile" && "$bfile" != "$src" ]]; then continue; fi
        if [[ -z "$bfile" && "$src" != "$SHATU_SCRIPT" ]]; then continue; fi
        if [[ -n "$cond" ]]; then
          eval "$cond" && stop=1
        else
          stop=1
        fi
      done < "$SHATU_BP"
    fi
    if [[ $stop == 1 ]]; then
      printf 'STOP\t%s\t%s\n' "$line" "$src" >&4
      shatu_vars
      printf 'END\n' >&4
      local cmd
      while true; do
        IFS= read -r cmd <&3 || { trap shatu_hook DEBUG; SHATU_IN=0; exit 0; }
        case "$cmd" in
          STOP) trap shatu_hook DEBUG; SHATU_IN=0; exit 0 ;;
          STEP|INTO) SHATU_MODE=step; break ;;
          OUT) SHATU_MODE=out; SHATU_DEPTH=$depth; break ;;
          CONT) SHATU_MODE=run; break ;;
          EVAL\ *)
            local expr="${cmd#EVAL }"
            local val
            val=$(eval "$expr" 2>&1) || true
            val=${val//$'\n'/ }
            printf 'EVAL %s\n' "${val:0:500}" >&4
            ;;
          *) SHATU_MODE=run; break ;;
        esac
      done
    fi
  fi
  trap shatu_hook DEBUG
  SHATU_IN=0
}
shatu_err() {
  [[ "${SHATU_IN:-0}" == 1 ]] && return 0
  SHATU_IN=1
  local line="${BASH_LINENO[0]}"
  local src="${BASH_SOURCE[1]}"
  if [[ -n "$src" && "$src" != /* ]]; then
    src="$(cd "$(dirname "$src")" 2>/dev/null && pwd)/$(basename "$src")"
  fi
  local allowed=0
  case "$src" in
    "$SHATU_SCRIPT"|"$SHATU_DIR"|"$SHATU_DIR"/*) allowed=1 ;;
  esac
  if [[ $allowed != 1 ]]; then
    SHATU_IN=0
    return 0
  fi
  local msg="${BASH_COMMAND}"
  msg=${msg//$'\t'/ }
  msg=${msg//$'\n'/ }
  printf 'ERR\t%s\t%s\t%s\n' "$line" "$src" "${msg:0:300}" >&4
  shatu_vars
  printf 'END\n' >&4
  local cmd depth=$(( ${#FUNCNAME[@]} - 1 ))
  while true; do
    IFS= read -r cmd <&3 || { trap shatu_hook DEBUG; trap shatu_err ERR; SHATU_IN=0; exit 0; }
    case "$cmd" in
      STOP) trap shatu_hook DEBUG; trap shatu_err ERR; SHATU_IN=0; exit 0 ;;
      STEP|INTO) SHATU_MODE=step; break ;;
      OUT) SHATU_MODE=out; SHATU_DEPTH=$depth; break ;;
      CONT) SHATU_MODE=run; break ;;
      EVAL\ *)
        local expr="${cmd#EVAL }"
        local val
        val=$(eval "$expr" 2>&1) || true
        val=${val//$'\n'/ }
        printf 'EVAL %s\n' "${val:0:500}" >&4
        ;;
      *) SHATU_MODE=run; break ;;
    esac
  done
  SHATU_IN=0
}
exec 3<&__CMD_FD__
exec 4>&__EV_FD__
set -o functrace
trap shatu_hook DEBUG
trap shatu_err ERR
source "$SHATU_SCRIPT"
printf 'DONE\n' >&4
"""


class ShellDebugSession(_LineSession):
    def __init__(self) -> None:
        super().__init__()
        self._w_cmd: int | None = None
        self._r_ev: int | None = None

    def start(self, script: str, cwd: str, breakpoints: list[dict], bp_file: Path) -> None:
        binary = shell_binary()
        if not binary:
            raise RuntimeError("Keine Linux-Shell gefunden (bash oder sh).")
        self.script = str(Path(script).resolve())
        self.bp_file = bp_file.with_suffix(bp_file.suffix + ".lines")
        self.update_breakpoints(breakpoints)
        r_cmd, w_cmd = os.pipe()
        r_ev, w_ev = os.pipe()
        preamble = _BASH.replace("__CMD_FD__", str(r_cmd)).replace("__EV_FD__", str(w_ev))
        env = os.environ.copy()
        env["SHATU_SCRIPT"] = self.script
        env["SHATU_DIR"] = str(Path(self.script).parent)
        env["SHATU_BP"] = str(self.bp_file)
        self.proc = subprocess.Popen(
            [binary, "--noprofile", "--norc", "-c", preamble],
            cwd=cwd,
            env=env,
            pass_fds=(r_cmd, w_ev),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        os.close(r_cmd)
        os.close(w_ev)
        self._w_cmd = w_cmd
        self._r_ev = r_ev
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_events, daemon=True).start()

    def _send(self, text: str) -> None:
        if self._w_cmd is None:
            raise RuntimeError("Keine Debug-Sitzung.")
        os.write(self._w_cmd, (text + "\n").encode("utf-8"))

    def _read_stdout(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            self._append_output(line)
        code = self.proc.wait()
        self._finish(code)

    def _read_events(self) -> None:
        if self._r_ev is None:
            return
        buf = b""
        while True:
            try:
                chunk = os.read(self._r_ev, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", "replace").strip("\r")
                if text:
                    self._on_protocol(text)

    def close(self) -> None:
        super().close()
        for fd in (self._w_cmd, self._r_ev):
            if fd is None:
                continue
            try:
                os.close(fd)
            except OSError:
                pass
        self._w_cmd = None
        self._r_ev = None


_PS1 = r"""
param(
  [Parameter(Mandatory = $true)][int]$Port,
  [Parameter(Mandatory = $true)][string]$Script,
  [Parameter(Mandatory = $true)][string]$BpFile,
  [string[]]$Also = @()
)
$ErrorActionPreference = "Continue"
$client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", $Port)
$stream = $client.GetStream()
$reader = New-Object System.IO.StreamReader($stream)
$writer = New-Object System.IO.StreamWriter($stream)
$writer.AutoFlush = $true
$global:ShatuMode = "run"
$global:ShatuDepth = 0
$global:ShatuWriter = $writer
$global:ShatuReader = $reader
$global:ShatuBpFile = $BpFile

function global:Shatu-Vars {
  $skip = @{
    "_" = $true; "?" = $true; "args" = $true; "true" = $true; "false" = $true; "null" = $true
    "Host" = $true; "HOME" = $true; "PID" = $true; "input" = $true; "foreach" = $true
    "Error" = $true; "ExecutionContext" = $true; "MyInvocation" = $true; "PSItem" = $true
    "EnabledExperimentalFeatures" = $true; "ShellId" = $true
  }
  $count = 0
  foreach ($scope in 1..8) {
    $vars = $null
    try { $vars = @(Get-Variable -Scope $scope -ErrorAction Ignore) } catch { continue }
    if ($null -eq $vars) { continue }
    $names = @($vars | ForEach-Object { $_.Name })
    if ($names -contains "taken" -or $names -contains "Kind" -or $names -contains "fileLines") { continue }
    $user = @($vars | Where-Object {
      $_.Name -match '^[A-Za-z_][A-Za-z0-9_]*$' -and -not $skip.ContainsKey($_.Name) -and $_.Name -notmatch '^(PS|Is|Shatu)'
    })
    if (-not $user.Count) { continue }
    foreach ($var in $user) {
      $text = ""
      try { $text = [string]$var.Value } catch { $text = "" }
      $text = ($text -replace "[\r\n\t]", " ")
      if ($text.Length -gt 180) { $text = $text.Substring(0, 180) }
      $global:ShatuWriter.WriteLine("VAR $($var.Name) $text")
      $count++
      if ($count -ge 40) { return }
    }
    return
  }
}

$global:ShatuErr = 0
function global:Shatu-TakeError {
  if ($Error.Count -le $global:ShatuErr) { return $null }
  $record = $Error[0]
  $global:ShatuErr = $Error.Count
  $line = 0
  $name = ""
  $message = "Fehler"
  try { $line = [int]$record.InvocationInfo.ScriptLineNumber } catch { $line = 0 }
  try { $name = [string]$record.InvocationInfo.ScriptName } catch { $name = "" }
  try { if ($record.Exception.Message) { $message = [string]$record.Exception.Message } } catch { }
  $message = ($message -replace "[\r\n\t]", " ")
  if ($message.Length -gt 300) { $message = $message.Substring(0, 300) }
  if ($line -lt 1) { return $null }
  return @{ Line = $line; Name = $name; Message = $message }
}
function global:Shatu-Pause {
  param([string]$Kind, [int]$Line, [string]$ScriptName, [string]$Message)
  $depth = @(Get-PSCallStack).Count
  $global:ShatuMode = "run"
  if ($Kind -eq "error") {
    $global:ShatuWriter.WriteLine("ERR`t$Line`t$ScriptName`t$Message")
  } else {
    $global:ShatuWriter.WriteLine("STOP`t$Line`t$ScriptName")
  }
  Shatu-Vars
  $global:ShatuWriter.WriteLine("END")
  while ($true) {
    $cmd = $global:ShatuReader.ReadLine()
    if ($null -eq $cmd -or $cmd -eq "STOP") { exit 0 }
    if ($cmd -eq "STEP" -or $cmd -eq "INTO") { $global:ShatuMode = "step"; $global:ShatuErr = $Error.Count; return }
    if ($cmd -eq "OUT") { $global:ShatuMode = "out"; $global:ShatuDepth = $depth; $global:ShatuErr = $Error.Count; return }
    if ($cmd -eq "CONT") { $global:ShatuMode = "run"; $global:ShatuErr = $Error.Count; return }
    if ($cmd.StartsWith("EVAL ")) {
      $expr = $cmd.Substring(5)
      $val = ""
      try { $val = "$(Invoke-Expression $expr)" } catch { $val = $_.Exception.Message }
      $val = ($val -replace "[\r\n]", " ")
      if ($val.Length -gt 500) { $val = $val.Substring(0, 500) }
      $global:ShatuWriter.WriteLine("EVAL $val")
      continue
    }
    $global:ShatuMode = "run"
    $global:ShatuErr = $Error.Count
    return
  }
}
function global:Shatu-Hit {
  param([int]$Line, [string]$ScriptName)
  $taken = Shatu-TakeError
  if ($null -ne $taken) {
    $errName = $ScriptName
    if ($taken.Name) { $errName = $taken.Name }
    Shatu-Pause -Kind "error" -Line $taken.Line -ScriptName $errName -Message $taken.Message
  }
  $stop = $false
  $depth = @(Get-PSCallStack).Count
  if ($global:ShatuMode -eq "step") { $stop = $true }
  if ($global:ShatuMode -eq "out" -and $depth -lt $global:ShatuDepth) { $stop = $true }
  if (Test-Path -LiteralPath $global:ShatuBpFile) {
    foreach ($entry in @(Get-Content -LiteralPath $global:ShatuBpFile -ErrorAction SilentlyContinue)) {
      $fileSpec = ""
      $cond = ""
      $lineNo = ""
      if ($entry.Contains([char]31)) {
        $parts = $entry.Split([char]31, 3)
        $lineNo = $parts[0]
        if ($parts.Count -gt 1) { $fileSpec = $parts[1] }
        if ($parts.Count -gt 2) { $cond = $parts[2] }
      } else {
        $parts = $entry -split "`t", 2
        $lineNo = $parts[0]
        if ($parts.Count -gt 1) { $cond = $parts[1] }
      }
      if ($lineNo -ne "$Line") { continue }
      if ($fileSpec -and ($fileSpec -ne $ScriptName)) { continue }
      if (-not $fileSpec -and $ScriptName -and ($ScriptName -ne $Script)) { continue }
      if ($cond) {
        $ok = $false
        try { $ok = [bool](Invoke-Expression $cond) } catch { $ok = $false }
        if ($ok) { $stop = $true }
      } else {
        $stop = $true
      }
    }
  }
  if (-not $stop) { return }
  Shatu-Pause -Kind "break" -Line $Line -ScriptName $ScriptName -Message ""
}

$targets = New-Object System.Collections.Generic.List[string]
[void]$targets.Add($Script)
foreach ($extra in @($Also)) {
  if ($extra -and (Test-Path -LiteralPath $extra)) { [void]$targets.Add($extra) }
}
foreach ($target in $targets) {
  $fileLines = @(Get-Content -LiteralPath $target -ErrorAction SilentlyContinue)
  for ($i = 1; $i -le $fileLines.Count; $i++) {
    if ($fileLines[$i - 1] -match '\S') {
      $null = Set-PSBreakpoint -Script $target -Line $i -Action { Shatu-Hit -Line $_.Line -ScriptName ([string]$_.Script) }
    }
  }
}
$global:ShatuErr = $Error.Count
& $Script
if ($Error.Count -gt $global:ShatuErr) {
  Shatu-Hit -Line 1 -ScriptName $Script
}
$writer.WriteLine("DONE")
"""


class PowerShellDebugSession(_LineSession):
    def __init__(self) -> None:
        super().__init__()
        self.sock: socket.socket | None = None
        self.driver: Path | None = None

    def start(self, script: str, cwd: str, breakpoints: list[dict], bp_file: Path) -> None:
        binary = powershell_binary()
        if not binary:
            raise RuntimeError("PowerShell nicht gefunden (pwsh oder powershell).")
        self.script = str(Path(script).resolve())
        self.bp_file = bp_file.with_suffix(bp_file.suffix + ".lines")
        self.update_breakpoints(breakpoints)
        handle = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8")
        handle.write(_PS1)
        handle.close()
        self.driver = Path(handle.name)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        from shatuide.studio import powershell_companions

        command = [
            binary,
            "-NoProfile",
            "-File",
            str(self.driver),
            "-Port",
            str(port),
            "-Script",
            self.script,
            "-BpFile",
            str(self.bp_file),
        ]
        for extra in powershell_companions(Path(self.script), breakpoints):
            command.extend(["-Also", extra])
        self.proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        listener.settimeout(15)
        try:
            self.sock, _addr = listener.accept()
        except socket.timeout as exc:
            if self.proc.poll() is None:
                self.proc.kill()
            detail = "".join(self.output)[-800:]
            raise RuntimeError("PowerShell-Debugger hat sich nicht verbunden. " + detail) from exc
        finally:
            listener.close()
        self.sock.settimeout(None)
        threading.Thread(target=self._read_socket, daemon=True).start()

    def _send(self, text: str) -> None:
        if self.sock is None:
            raise RuntimeError("Keine Debug-Sitzung.")
        self.sock.sendall((text + "\n").encode("utf-8"))

    def _read_stdout(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            self._append_output(line)
        code = self.proc.wait()
        self._finish(code)

    def _read_socket(self) -> None:
        assert self.sock is not None
        buf = b""
        while True:
            try:
                chunk = self.sock.recv(65536)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                text = raw.decode("utf-8", "replace").strip("\r")
                if text:
                    self._on_protocol(text)

    def close(self) -> None:
        super().close()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        if self.driver is not None:
            try:
                self.driver.unlink()
            except OSError:
                pass
            self.driver = None
