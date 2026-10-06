"""Windows-Pfadtrenner für Copy/Anzeige; Dialoge akzeptieren / und \\."""

from __future__ import annotations

from pathlib import Path

from instantlensdoc.core.fs_path import as_native_path, native_fs_path, native_fs_paths
from instantlensdoc.ui.file_dialogs import picked_fs_path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_copy_path_uses_backslash():
    posix = "D:/AI_Temp/file.pdf"
    mixed = "D:\\AI_Temp/file.pdf"
    native = r"D:\AI_Temp\file.pdf"
    assert native_fs_path(posix, os_name="nt") == native
    assert native_fs_path(mixed, os_name="nt") == native
    assert native_fs_path(native, os_name="nt") == native
    assert native_fs_path("/InstantLensDoc/a.pdf", os_name="nt") == r"\InstantLensDoc\a.pdf"


def test_linux_keeps_posix_slashes():
    p = "/home/andreas/AI_Temp/file.pdf"
    assert native_fs_path(p, os_name="posix") == p
    assert "\\" not in native_fs_path(p, os_name="posix")
    assert native_fs_path("D:/AI_Temp/file.pdf", os_name="posix") == "D:/AI_Temp/file.pdf"


def test_empty_and_none():
    assert native_fs_path(None) == ""
    assert native_fs_path("   ") == ""
    assert native_fs_paths(["", None, "D:/a.pdf"], os_name="nt") == [r"D:\a.pdf"]


def test_as_native_path_posix_roundtrip():
    posix = as_native_path("/tmp/x.pdf", os_name="posix")
    assert isinstance(posix, Path)
    assert posix.as_posix() == "/tmp/x.pdf"


def test_picked_fs_path_matches_native():
    assert picked_fs_path("") == ""
    assert picked_fs_path("D:/AI_Temp/a.pdf") == native_fs_path("D:/AI_Temp/a.pdf")


def test_copy_helpers_call_native_fs_path():
    wel = (ROOT / "instantlensdoc" / "ui" / "welcome.py").read_text(encoding="utf-8")
    mw = (ROOT / "instantlensdoc" / "ui" / "main_window.py").read_text(encoding="utf-8")
    ptd = (ROOT / "instantlensdoc" / "ui" / "pdf_tools_dialog.py").read_text(
        encoding="utf-8"
    )
    rec = (ROOT / "instantlensdoc" / "core" / "recent.py").read_text(encoding="utf-8")
    fd = (ROOT / "instantlensdoc" / "ui" / "file_dialogs.py").read_text(encoding="utf-8")
    assert "from instantlensdoc.core.fs_path import native_fs_path" in wel
    assert "text = native_fs_path(path)" in wel
    assert "native_fs_path(self.doc.path)" in mw
    assert "text = native_fs_path(path)" in mw
    assert "native_fs_paths(paths)" in ptd
    assert "native_fs_path" in rec
    assert "def get_open_file_name(" in fd
    assert "def get_save_file_name(" in fd
    assert "native_fs_path(directory)" in fd
