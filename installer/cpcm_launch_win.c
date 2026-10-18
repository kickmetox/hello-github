/* Startet die mitgelieferte python.exe mit cpcm.py.
   Kein ShellExecute auf eine .py-Datei, damit Windows die Datei nicht an ShatuIDE gibt. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

static void fail(const wchar_t *text) {
    MessageBoxW(NULL, text, L"CPCM", MB_ICONERROR | MB_OK);
}

int WINAPI WinMain(HINSTANCE instance, HINSTANCE previous, LPSTR command, int show) {
    (void)instance;
    (void)previous;
    (void)command;
    (void)show;
    wchar_t dir[MAX_PATH];
    wchar_t python[MAX_PATH];
    wchar_t script[MAX_PATH];
    wchar_t cmdline[2048];
    DWORD length = GetModuleFileNameW(NULL, dir, MAX_PATH);
    wchar_t *slash;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;

    if (length == 0 || length >= MAX_PATH) {
        fail(L"CPCM.exe findet den eigenen Ordner nicht.");
        return 1;
    }
    slash = wcsrchr(dir, L'\\');
    if (slash == NULL) {
        fail(L"CPCM.exe findet den eigenen Ordner nicht.");
        return 1;
    }
    *slash = 0;
    _snwprintf(python, MAX_PATH, L"%ls\\python\\python.exe", dir);
    _snwprintf(script, MAX_PATH, L"%ls\\cpcm.py", dir);
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script) == INVALID_FILE_ATTRIBUTES) {
        fail(L"Neben CPCM.exe fehlen python\\python.exe oder cpcm.py.");
        return 1;
    }
    _snwprintf(cmdline, 2048, L"\"%ls\" \"%ls\" serve", python, script);
    ZeroMemory(&si, sizeof si);
    si.cb = sizeof si;
    ZeroMemory(&pi, sizeof pi);
    if (!CreateProcessW(python, cmdline, NULL, NULL, FALSE, CREATE_NEW_CONSOLE, NULL, dir, &si, &pi)) {
        fail(L"Die mitgelieferte python.exe konnte nicht gestartet werden.");
        return 1;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
