#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <stdio.h>
#include <string.h>

/* Eigenes Anwendungsfenster. Der lokale Server bleibt auf 127.0.0.1,
   die Oberfläche liegt in WebView2 statt in einem Browser-Tab. */

static wchar_t g_dir[MAX_PATH];
static wchar_t g_url[256];
static wchar_t g_status[640];
static HWND g_main;
static HWND g_label;
static HBRUSH g_brush;
static HANDLE g_python;
static HANDLE g_job;
static void *g_env;
static int g_port;
static int g_winsock;
static int g_wv_failed;

typedef struct Host {
    HWND hwnd;
    void *controller;
    void *webview;
    int main_window;
} Host;

static Host g_hosts[16];

typedef struct Handler {
    const void *lpVtbl;
    LONG refs;
    const GUID *iid;
    HWND hwnd;
    wchar_t uri[1024];
    void *args;
    void *deferral;
    int main_window;
} Handler;

static const GUID IID_NULL_UNKNOWN = {0x00000000, 0x0000, 0x0000, {0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46}};
static const GUID IID_ENV_DONE = {0x4e8a3389, 0xc9d8, 0x4bd2, {0xb6, 0xb5, 0x12, 0x4f, 0xee, 0x6c, 0xc1, 0x4d}};
static const GUID IID_CTRL_DONE = {0x6c4819f3, 0xc9b7, 0x4260, {0x81, 0x27, 0xc9, 0xf5, 0xbd, 0xe7, 0xf6, 0x8c}};
static const GUID IID_NEW_WINDOW = {0xd4c185fe, 0xc81c, 0x4989, {0x97, 0xaf, 0x2d, 0x3f, 0xa7, 0xab, 0x56, 0x51}};
static const GUID IID_CLOSE_WINDOW = {0x5c19e9e0, 0x092f, 0x486b, {0xaf, 0xfa, 0xca, 0x82, 0x31, 0x91, 0x30, 0x39}};

static void *vt(void *object, int index) {
    return (*(void ***)object)[index];
}

static ULONG STDMETHODCALLTYPE handler_add(Handler *self) {
    return (ULONG)InterlockedIncrement(&self->refs);
}

static ULONG STDMETHODCALLTYPE handler_release(Handler *self) {
    LONG refs = InterlockedDecrement(&self->refs);
    if (refs == 0) {
        HeapFree(GetProcessHeap(), 0, self);
    }
    return (ULONG)refs;
}

static HRESULT STDMETHODCALLTYPE handler_query(Handler *self, REFIID iid, void **out) {
    if (!out) {
        return E_POINTER;
    }
    if (memcmp(iid, &IID_NULL_UNKNOWN, sizeof(GUID)) == 0 || memcmp(iid, self->iid, sizeof(GUID)) == 0) {
        handler_add(self);
        *out = self;
        return S_OK;
    }
    *out = NULL;
    return E_NOINTERFACE;
}

static void set_status(HWND hwnd, const wchar_t *text) {
    wcsncpy(g_status, text, 639);
    g_status[639] = 0;
    if (g_label) {
        SetWindowTextW(g_label, g_status);
    }
    if (hwnd) {
        InvalidateRect(hwnd, NULL, TRUE);
    }
}

static Host *host_from_hwnd(HWND hwnd) {
    return (Host *)GetWindowLongPtrW(hwnd, GWLP_USERDATA);
}

static Host *empty_host(void) {
    for (int index = 0; index < 16; index += 1) {
        if (!g_hosts[index].hwnd) {
            ZeroMemory(&g_hosts[index], sizeof g_hosts[index]);
            return &g_hosts[index];
        }
    }
    return NULL;
}

static void release_object(void **object) {
    if (*object) {
        typedef ULONG (STDMETHODCALLTYPE *ReleaseFn)(void *);
        ReleaseFn release = vt(*object, 2);
        release(*object);
        *object = NULL;
    }
}

static void resize_host(Host *host) {
    if (!host || !host->controller) {
        return;
    }
    RECT bounds;
    GetClientRect(host->hwnd, &bounds);
    typedef HRESULT (STDMETHODCALLTYPE *PutBoundsFn)(void *, RECT);
    PutBoundsFn put_bounds = vt(host->controller, 6);
    put_bounds(host->controller, bounds);
}

static void prepare_webview(void *webview) {
    void *settings = NULL;
    typedef HRESULT (STDMETHODCALLTYPE *GetSettingsFn)(void *, void **);
    GetSettingsFn get_settings = vt(webview, 3);
    if (SUCCEEDED(get_settings(webview, &settings)) && settings) {
        typedef HRESULT (STDMETHODCALLTYPE *PutBoolFn)(void *, BOOL);
        PutBoolFn put_status = vt(settings, 10);
        put_status(settings, FALSE);
        release_object(&settings);
    }
}

static HRESULT STDMETHODCALLTYPE ctrl_invoke(Handler *self, HRESULT result, void *controller);
static HRESULT STDMETHODCALLTYPE new_window_invoke(Handler *self, void *sender, void *args);
static HRESULT STDMETHODCALLTYPE close_window_invoke(Handler *self, void *sender, void *args);

static const void *g_ctrl_vt[];
static const void *g_new_window_vt[];
static const void *g_close_vt[];

static Handler *new_handler(const void *vtable, const GUID *iid) {
    Handler *handler = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(Handler));
    if (!handler) {
        return NULL;
    }
    handler->lpVtbl = vtable;
    handler->refs = 1;
    handler->iid = iid;
    return handler;
}

static void watch_webview(void *webview) {
    Handler *opened = new_handler(g_new_window_vt, &IID_NEW_WINDOW);
    Handler *closed = new_handler(g_close_vt, &IID_CLOSE_WINDOW);
    typedef struct Token { long long value; } Token;
    Token token;
    typedef HRESULT (STDMETHODCALLTYPE *AddFn)(void *, void *, Token *);
    if (opened) {
        AddFn add = vt(webview, 44);
        add(webview, opened, &token);
        handler_release(opened);
    }
    if (closed) {
        AddFn add = vt(webview, 59);
        add(webview, closed, &token);
        handler_release(closed);
    }
}

static HRESULT STDMETHODCALLTYPE ctrl_invoke(Handler *self, HRESULT result, void *controller) {
    if (FAILED(result) || !controller) {
        if (self->deferral) {
            typedef HRESULT (STDMETHODCALLTYPE *CompleteFn)(void *);
            CompleteFn complete = vt(self->deferral, 3);
            complete(self->deferral);
        }
        if (self->args) {
            typedef HRESULT (STDMETHODCALLTYPE *PutBoolFn)(void *, BOOL);
            PutBoolFn put_handled = vt(self->args, 6);
            put_handled(self->args, FALSE);
        }
        release_object(&self->args);
        release_object(&self->deferral);
        if (self->hwnd && self->hwnd != g_main) {
            DestroyWindow(self->hwnd);
        }
        if (self->main_window) {
            g_wv_failed = 1;
            set_status(g_main, L"Das Anwendungsfenster konnte nicht erzeugt werden.");
        }
        return S_OK;
    }
    Host *host = host_from_hwnd(self->hwnd);
    if (!host) {
        host = empty_host();
        if (host) {
            host->hwnd = self->hwnd;
            SetWindowLongPtrW(self->hwnd, GWLP_USERDATA, (LONG_PTR)host);
        }
    }
    if (!host) {
        return S_OK;
    }
    typedef ULONG (STDMETHODCALLTYPE *AddFn)(void *);
    AddFn add_ref = vt(controller, 1);
    add_ref(controller);
    host->controller = controller;
    host->main_window = self->main_window;
    typedef HRESULT (STDMETHODCALLTYPE *PutBoolFn)(void *, BOOL);
    PutBoolFn put_visible = vt(controller, 4);
    put_visible(controller, TRUE);
    resize_host(host);
    void *webview = NULL;
    typedef HRESULT (STDMETHODCALLTYPE *GetWebFn)(void *, void **);
    GetWebFn get_web = vt(controller, 25);
    if (FAILED(get_web(controller, &webview)) || !webview) {
        return S_OK;
    }
    host->webview = webview;
    prepare_webview(webview);
    watch_webview(webview);
    if (self->main_window && g_label) {
        ShowWindow(g_label, SW_HIDE);
    }
    if (self->args) {
        typedef HRESULT (STDMETHODCALLTYPE *PutWebFn)(void *, void *);
        PutWebFn put_window = vt(self->args, 4);
        PutBoolFn put_handled = vt(self->args, 6);
        put_window(self->args, webview);
        put_handled(self->args, TRUE);
    } else if (self->uri[0]) {
        typedef HRESULT (STDMETHODCALLTYPE *NavigateFn)(void *, const wchar_t *);
        NavigateFn navigate = vt(webview, 5);
        navigate(webview, self->uri);
    }
    if (self->deferral) {
        typedef HRESULT (STDMETHODCALLTYPE *CompleteFn)(void *);
        CompleteFn complete = vt(self->deferral, 3);
        complete(self->deferral);
    }
    release_object(&self->args);
    release_object(&self->deferral);
    ShowWindow(self->hwnd, SW_SHOW);
    return S_OK;
}

static HWND create_window(int main_window, int width, int height);

static HRESULT STDMETHODCALLTYPE new_window_invoke(Handler *self, void *sender, void *args) {
    (void)self;
    (void)sender;
    if (!g_env || !args) {
        return S_OK;
    }
    typedef HRESULT (STDMETHODCALLTYPE *GetDeferralFn)(void *, void **);
    typedef HRESULT (STDMETHODCALLTYPE *GetUriFn)(void *, wchar_t **);
    void *deferral = NULL;
    wchar_t *uri = NULL;
    GetDeferralFn get_deferral = vt(args, 7);
    GetUriFn get_uri = vt(args, 3);
    get_deferral(args, &deferral);
    get_uri(args, &uri);
    HWND hwnd = create_window(0, 1100, 760);
    Handler *created = new_handler(g_ctrl_vt, &IID_CTRL_DONE);
    if (!hwnd || !created) {
        typedef HRESULT (STDMETHODCALLTYPE *PutBoolFn)(void *, BOOL);
        PutBoolFn put_handled = vt(args, 6);
        put_handled(args, FALSE);
        if (deferral) {
            typedef HRESULT (STDMETHODCALLTYPE *CompleteFn)(void *);
            CompleteFn complete = vt(deferral, 3);
            complete(deferral);
            release_object(&deferral);
        }
        if (uri) {
            CoTaskMemFree(uri);
        }
        if (created) {
            handler_release(created);
        }
        return S_OK;
    }
    created->hwnd = hwnd;
    created->main_window = 0;
    typedef ULONG (STDMETHODCALLTYPE *AddRefFn)(void *);
    AddRefFn add_ref = vt(args, 1);
    add_ref(args);
    created->args = args;
    created->deferral = deferral;
    if (uri) {
        wcsncpy(created->uri, uri, 1023);
        CoTaskMemFree(uri);
    }
    typedef HRESULT (STDMETHODCALLTYPE *CreateCtrlFn)(void *, HWND, void *);
    CreateCtrlFn create = vt(g_env, 3);
    create(g_env, hwnd, created);
    handler_release(created);
    return S_OK;
}

static HRESULT STDMETHODCALLTYPE close_window_invoke(Handler *self, void *sender, void *args) {
    (void)self;
    (void)args;
    for (int index = 0; index < 16; index += 1) {
        if (g_hosts[index].webview == sender && g_hosts[index].hwnd) {
            DestroyWindow(g_hosts[index].hwnd);
            break;
        }
    }
    return S_OK;
}

static HRESULT STDMETHODCALLTYPE env_invoke(Handler *self, HRESULT result, void *environment) {
    (void)self;
    if (FAILED(result) || !environment) {
        g_wv_failed = 1;
        set_status(g_main, L"WebView2 ist nicht verfügbar. Edge oder Chrome wird als Anwendungsfenster versucht.");
        g_env = NULL;
        return S_OK;
    }
    typedef ULONG (STDMETHODCALLTYPE *AddRefFn)(void *);
    AddRefFn add_ref = vt(environment, 1);
    add_ref(environment);
    g_env = environment;
    Handler *created = new_handler(g_ctrl_vt, &IID_CTRL_DONE);
    if (!created) {
        return S_OK;
    }
    created->hwnd = g_main;
    created->main_window = 1;
    wcsncpy(created->uri, g_url, 1023);
    typedef HRESULT (STDMETHODCALLTYPE *CreateCtrlFn)(void *, HWND, void *);
    CreateCtrlFn create = vt(environment, 3);
    create(environment, g_main, created);
    handler_release(created);
    return S_OK;
}

static const void *g_env_vt[] = {handler_query, handler_add, handler_release, env_invoke};
static const void *g_ctrl_vt[] = {handler_query, handler_add, handler_release, ctrl_invoke};
static const void *g_new_window_vt[] = {handler_query, handler_add, handler_release, new_window_invoke};
static const void *g_close_vt[] = {handler_query, handler_add, handler_release, close_window_invoke};

static void stop_python(void) {
    if (g_python) {
        TerminateProcess(g_python, 0);
        CloseHandle(g_python);
        g_python = NULL;
    }
}

static LRESULT CALLBACK window_proc(HWND hwnd, UINT message, WPARAM wparam, LPARAM lparam) {
    switch (message) {
    case WM_SIZE:
        resize_host(host_from_hwnd(hwnd));
        return 0;
    case WM_CTLCOLORSTATIC: {
        HDC dc = (HDC)wparam;
        SetTextColor(dc, RGB(230, 230, 230));
        SetBkColor(dc, RGB(28, 32, 38));
        return (LRESULT)g_brush;
    }
    case WM_PAINT: {
        PAINTSTRUCT paint;
        HDC dc = BeginPaint(hwnd, &paint);
        RECT bounds;
        GetClientRect(hwnd, &bounds);
        FillRect(dc, &bounds, g_brush);
        EndPaint(hwnd, &paint);
        return 0;
    }
    case WM_DESTROY: {
        Host *host = host_from_hwnd(hwnd);
        if (host && host->controller) {
            typedef HRESULT (STDMETHODCALLTYPE *CloseFn)(void *);
            release_object(&host->webview);
            CloseFn close = vt(host->controller, 24);
            close(host->controller);
            release_object(&host->controller);
            host->hwnd = NULL;
        }
        if (hwnd == g_main) {
            stop_python();
            PostQuitMessage(0);
        }
        return 0;
    }
    default:
        return DefWindowProcW(hwnd, message, wparam, lparam);
    }
}

static HWND create_window(int main_window, int width, int height) {
    RECT area = {0, 0, width, height};
    AdjustWindowRect(&area, WS_OVERLAPPEDWINDOW, FALSE);
    int w = area.right - area.left;
    int h = area.bottom - area.top;
    int x = (GetSystemMetrics(SM_CXSCREEN) - w) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - h) / 2;
    HWND hwnd = CreateWindowExW(
        0, L"ShatuIDEWindow", L"ShatuIDE", WS_OVERLAPPEDWINDOW,
        x, y, w, h, NULL, NULL, GetModuleHandleW(NULL), NULL);
    if (!hwnd) {
        return NULL;
    }
    Host *host = empty_host();
    if (host) {
        host->hwnd = hwnd;
        host->main_window = main_window;
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, (LONG_PTR)host);
    }
    if (main_window) {
        g_main = hwnd;
        g_label = CreateWindowExW(
            0, L"STATIC", g_status,
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            48, 48, width - 96, 160,
            hwnd, NULL, GetModuleHandleW(NULL), NULL);
        ShowWindow(hwnd, SW_SHOW);
        UpdateWindow(hwnd);
    }
    return hwnd;
}

static int file_ok(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY) == 0;
}

static void append_arg(wchar_t *cmdline, size_t cap, const wchar_t *arg) {
    size_t used = wcslen(cmdline);
    if (used + wcslen(arg) + 4 >= cap) {
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

static int option_is(const wchar_t *arg, const wchar_t *name) {
    return _wcsicmp(arg, name) == 0;
}

static void track_python(HANDLE process) {
    if (!g_job) {
        g_job = CreateJobObjectW(NULL, NULL);
        if (g_job) {
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION info;
            ZeroMemory(&info, sizeof info);
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(g_job, JobObjectExtendedLimitInformation, &info, sizeof info);
        }
    }
    if (g_job) {
        AssignProcessToJobObject(g_job, process);
    }
}

static int port_free(int port) {
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        return 0;
    }
    struct sockaddr_in address;
    ZeroMemory(&address, sizeof address);
    address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)port);
    address.sin_addr.s_addr = htonl(0x7f000001);
    int ok = bind(sock, (struct sockaddr *)&address, sizeof address) == 0;
    closesocket(sock);
    return ok;
}

static int choose_port(int requested) {
    if (requested > 0 && requested < 65536 && port_free(requested)) {
        return requested;
    }
    for (int port = 8765; port < 8865; port += 1) {
        if (port_free(port)) {
            return port;
        }
    }
    return 8765;
}

static int server_ready(void) {
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        return 0;
    }
    struct sockaddr_in address;
    ZeroMemory(&address, sizeof address);
    address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)g_port);
    address.sin_addr.s_addr = htonl(0x7f000001);
    int ready = 0;
    if (connect(sock, (struct sockaddr *)&address, sizeof address) == 0) {
        const char *request = "GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n";
        send(sock, request, (int)strlen(request), 0);
        char buffer[64];
        int count = recv(sock, buffer, sizeof buffer - 1, 0);
        ready = count > 0;
    }
    closesocket(sock);
    return ready;
}

static int pump(DWORD milliseconds) {
    DWORD start = GetTickCount();
    for (;;) {
        MSG message;
        while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
            if (message.message == WM_QUIT) {
                return 0;
            }
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
        if (GetTickCount() - start >= milliseconds) {
            return 1;
        }
        Sleep(20);
    }
}

static int start_python(int argc, wchar_t **argv) {
    wchar_t script[MAX_PATH];
    wchar_t python[MAX_PATH];
    wchar_t bundled[MAX_PATH];
    int via_py = 0;
    int requested = 0;
    int saw_browser = 0;
    int saw_port = 0;
    _snwprintf(script, MAX_PATH, L"%ls\\shatuide.py", g_dir);
    if (!file_ok(script)) {
        set_status(g_main, L"shatuide.py liegt nicht neben ShatuIDE.exe.");
        return 0;
    }
    python[0] = 0;
    _snwprintf(bundled, MAX_PATH, L"%ls\\python\\python.exe", g_dir);
    if (file_ok(bundled)) {
        wcscpy(python, bundled);
    } else if (SearchPathW(NULL, L"py.exe", NULL, MAX_PATH, python, NULL) || SearchPathW(NULL, L"py", NULL, MAX_PATH, python, NULL)) {
        via_py = 1;
    } else if (!SearchPathW(NULL, L"python.exe", NULL, MAX_PATH, python, NULL) && !SearchPathW(NULL, L"python3.exe", NULL, MAX_PATH, python, NULL)) {
        set_status(g_main, L"Python 3 nicht gefunden. Installieren Sie Python oder legen Sie python\\python.exe neben die Anwendung.");
        return 0;
    }
    for (int index = 1; index < argc; index += 1) {
        if (option_is(argv[index], L"--no-browser")) {
            saw_browser = 1;
        }
        if (option_is(argv[index], L"--port") && index + 1 < argc) {
            saw_port = 1;
            requested = _wtoi(argv[index + 1]);
        }
    }
    g_port = choose_port(requested);
    _snwprintf(g_url, 256, L"http://127.0.0.1:%d/", g_port);
    wchar_t cmdline[32768];
    if (via_py) {
        _snwprintf(cmdline, 32768, L"\"%ls\" -3 \"%ls\"", python, script);
    } else {
        _snwprintf(cmdline, 32768, L"\"%ls\" \"%ls\"", python, script);
    }
    for (int index = 1; index < argc; index += 1) {
        append_arg(cmdline, 32768, argv[index]);
    }
    if (!saw_browser) {
        append_arg(cmdline, 32768, L"--no-browser");
    }
    if (!saw_port) {
        wchar_t port_text[16];
        _snwprintf(port_text, 16, L"%d", g_port);
        append_arg(cmdline, 32768, L"--port");
        append_arg(cmdline, 32768, port_text);
    }
    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof startup);
    ZeroMemory(&process, sizeof process);
    startup.cb = sizeof startup;
    if (!CreateProcessW(python, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, g_dir, &startup, &process)) {
        set_status(g_main, L"Python konnte nicht gestartet werden.");
        return 0;
    }
    CloseHandle(process.hThread);
    g_python = process.hProcess;
    track_python(g_python);
    set_status(g_main, L"ShatuIDE wird gestartet …");
    for (int attempt = 0; attempt < 200; attempt += 1) {
        DWORD code = 0;
        if (!GetExitCodeProcess(g_python, &code) || code != STILL_ACTIVE) {
            set_status(g_main, L"Der lokale Server wurde beendet, bevor das Fenster fertig war.");
            return 0;
        }
        if (server_ready()) {
            return 1;
        }
        if (!pump(50)) {
            return 0;
        }
    }
    set_status(g_main, L"Der lokale Server antwortet nicht.");
    return 0;
}

static int start_webview(void) {
    wchar_t loader[MAX_PATH];
    wchar_t data[MAX_PATH];
    _snwprintf(loader, MAX_PATH, L"%ls\\WebView2Loader.dll", g_dir);
    HMODULE module = LoadLibraryW(loader);
    if (!module) {
        module = LoadLibraryW(L"WebView2Loader.dll");
    }
    if (!module) {
        return 0;
    }
    typedef HRESULT (STDMETHODCALLTYPE *CreateEnvFn)(const wchar_t *, const wchar_t *, void *, void *);
    FARPROC raw_create = GetProcAddress(module, "CreateCoreWebView2EnvironmentWithOptions");
    CreateEnvFn create = NULL;
    memcpy(&create, &raw_create, sizeof create);
    if (!create) {
        return 0;
    }
    wchar_t folder[MAX_PATH];
    if (FAILED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, 0, folder))) {
        wcscpy(folder, g_dir);
    }
    _snwprintf(data, MAX_PATH, L"%ls\\ShatuIDE\\WebView2", folder);
    SHCreateDirectoryExW(NULL, data, NULL);
    Handler *handler = new_handler(g_env_vt, &IID_ENV_DONE);
    if (!handler) {
        return 0;
    }
    HRESULT created = create(NULL, data, NULL, handler);
    handler_release(handler);
    if (FAILED(created)) {
        return 0;
    }
    for (int attempt = 0; attempt < 200 && !g_env && !g_wv_failed; attempt += 1) {
        if (!pump(50)) {
            return 0;
        }
    }
    if (g_wv_failed || !g_env) {
        return 0;
    }
    for (int attempt = 0; attempt < 200 && !g_wv_failed; attempt += 1) {
        Host *host = host_from_hwnd(g_main);
        if (host && host->webview) {
            return 1;
        }
        if (!pump(50)) {
            return 0;
        }
    }
    return g_env && host_from_hwnd(g_main) && host_from_hwnd(g_main)->webview;
}

static int find_browser(wchar_t *out) {
    const wchar_t *candidates[] = {
        L"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        L"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        L"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        L"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    };
    for (int index = 0; index < 4; index += 1) {
        if (file_ok(candidates[index])) {
            wcscpy(out, candidates[index]);
            return 1;
        }
    }
    if (SearchPathW(NULL, L"msedge.exe", NULL, MAX_PATH, out, NULL) || SearchPathW(NULL, L"chrome.exe", NULL, MAX_PATH, out, NULL)) {
        return 1;
    }
    return 0;
}

static int open_app_window(void) {
    wchar_t browser[MAX_PATH];
    if (!find_browser(browser)) {
        return 0;
    }
    wchar_t cmdline[1024];
    _snwprintf(cmdline, 1024, L"\"%ls\" --app=%ls --new-window", browser, g_url);
    STARTUPINFOW startup;
    PROCESS_INFORMATION process;
    ZeroMemory(&startup, sizeof startup);
    ZeroMemory(&process, sizeof process);
    startup.cb = sizeof startup;
    if (!CreateProcessW(browser, cmdline, NULL, NULL, FALSE, 0, NULL, g_dir, &startup, &process)) {
        return 0;
    }
    CloseHandle(process.hThread);
    ShowWindow(g_main, SW_HIDE);
    WaitForSingleObject(process.hProcess, INFINITE);
    CloseHandle(process.hProcess);
    return 1;
}

int main(void) {
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    SetProcessDPIAware();
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    WSADATA sockets;
    if (WSAStartup(MAKEWORD(2, 2), &sockets) == 0) {
        g_winsock = 1;
    }
    DWORD length = GetModuleFileNameW(NULL, g_dir, MAX_PATH);
    if (!length || length >= MAX_PATH) {
        MessageBoxW(NULL, L"Der Pfad der Anwendung ist zu lang.", L"ShatuIDE", MB_ICONERROR | MB_OK);
        return 1;
    }
    wchar_t *slash = wcsrchr(g_dir, L'\\');
    if (!slash) {
        MessageBoxW(NULL, L"Der Ordner der Anwendung fehlt.", L"ShatuIDE", MB_ICONERROR | MB_OK);
        return 1;
    }
    *slash = 0;
    WNDCLASSW klass;
    ZeroMemory(&klass, sizeof klass);
    klass.lpfnWndProc = window_proc;
    klass.hInstance = GetModuleHandleW(NULL);
    klass.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    klass.hIcon = LoadIconW(klass.hInstance, MAKEINTRESOURCEW(1));
    g_brush = CreateSolidBrush(RGB(28, 32, 38));
    klass.hbrBackground = g_brush;
    klass.lpszClassName = L"ShatuIDEWindow";
    RegisterClassW(&klass);
    wcscpy(g_status, L"ShatuIDE wird gestartet …");
    if (!create_window(1, 1280, 820)) {
        MessageBoxW(NULL, L"Das Anwendungsfenster konnte nicht geöffnet werden.", L"ShatuIDE", MB_ICONERROR | MB_OK);
        return 1;
    }
    int embedded = 0;
    if (start_python(argc, argv)) {
        embedded = start_webview();
        if (!embedded) {
            if (open_app_window()) {
                stop_python();
                DestroyWindow(g_main);
            } else {
                set_status(g_main, L"WebView2, Edge und Chrome fehlen. Die Windows-Anwendung braucht eines davon. Python 3 muss außerdem installiert sein.");
            }
        }
    }
    if (g_main && IsWindow(g_main)) {
        MSG message;
        while (GetMessageW(&message, NULL, 0, 0) > 0) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    stop_python();
    release_object(&g_env);
    if (g_job) {
        CloseHandle(g_job);
    }
    if (g_winsock) {
        WSACleanup();
    }
    CoUninitialize();
    LocalFree(argv);
    return 0;
}
