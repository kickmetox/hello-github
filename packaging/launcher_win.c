#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>

static void fail(const wchar_t *text) {
    fwprintf(stderr, L"%ls\n", text);
    MessageBoxW(NULL, text, L"ShatuIDE", MB_ICONERROR | MB_OK);
}

static int file_ok(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY) == 0;
}

static void append_arg(wchar_t *cmdline, size_t cap, const wchar_t *arg) {
    size_t used = wcslen(cmdline);
    size_t need = wcslen(arg) + 4;
    if (used + need >= cap) {
        return;
    }
    wcscat(cmdline, L" ");
    if (wcschr(arg, L' ') || wcschr(arg, L'\t')) {
        wcscat(cmdline, L"\"");
        wcscat(cmdline, arg);
        wcscat(cmdline, L"\"");
    } else {
        wcscat(cmdline, arg);
    }
}

int main(void) {
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    wchar_t exe[MAX_PATH];
    DWORD length = GetModuleFileNameW(NULL, exe, MAX_PATH);
    if (!length || length >= MAX_PATH) {
        fail(L"Der Pfad der EXE ist zu lang.");
        return 1;
    }
    wchar_t *slash = wcsrchr(exe, L'\\');
    if (!slash) {
        fail(L"Der Ordner der EXE fehlt.");
        return 1;
    }
    *slash = 0;
    wchar_t script[MAX_PATH];
    _snwprintf(script, MAX_PATH, L"%ls\\shatuide.py", exe);
    if (!file_ok(script)) {
        fail(L"shatuide.py liegt nicht neben ShatuIDE.exe.");
        return 1;
    }
    wchar_t python[MAX_PATH];
    wchar_t bundled[MAX_PATH];
    int via_py = 0;
    python[0] = 0;
    _snwprintf(bundled, MAX_PATH, L"%ls\\python\\python.exe", exe);
    if (file_ok(bundled)) {
        wcscpy(python, bundled);
    } else if (SearchPathW(NULL, L"py.exe", NULL, MAX_PATH, python, NULL) || SearchPathW(NULL, L"py", NULL, MAX_PATH, python, NULL)) {
        via_py = 1;
    } else if (!SearchPathW(NULL, L"python.exe", NULL, MAX_PATH, python, NULL) && !SearchPathW(NULL, L"python3.exe", NULL, MAX_PATH, python, NULL)) {
        fail(L"Python 3 nicht gefunden. Installieren Sie Python oder legen Sie python\\python.exe neben die EXE.");
        return 127;
    }
    wchar_t cmdline[32768];
    if (via_py) {
        _snwprintf(cmdline, 32768, L"\"%ls\" -3 \"%ls\"", python, script);
    } else {
        _snwprintf(cmdline, 32768, L"\"%ls\" \"%ls\"", python, script);
    }
    for (int index = 1; index < argc; index += 1) {
        append_arg(cmdline, 32768, argv[index]);
    }
    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof startup);
    startup.cb = sizeof startup;
    if (!CreateProcessW(python, cmdline, NULL, NULL, FALSE, 0, NULL, exe, &startup, &process)) {
        fail(L"Python konnte nicht gestartet werden.");
        LocalFree(argv);
        return 127;
    }
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hProcess);
    CloseHandle(process.hThread);
    LocalFree(argv);
    return (int)code;
}
