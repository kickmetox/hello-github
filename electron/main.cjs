const { app, BrowserWindow, dialog, protocol, shell } = require('electron');
const fs = require('fs');
const path = require('path');

const SCHEME = 'reckongrid';
const DIST = path.join(__dirname, '..', 'dist');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

protocol.registerSchemesAsPrivileged([
  {
    scheme: SCHEME,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
      stream: true,
    },
  },
]);

function fileFromRequest(requestUrl) {
  const url = new URL(requestUrl);
  const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
  const root = path.resolve(DIST);
  const filePath = path.resolve(root, rel);
  if (filePath !== root && !filePath.startsWith(root + path.sep)) return null;
  return filePath;
}

function createWindow() {
  const icon = path.join(DIST, 'icon.png');
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 960,
    minHeight: 640,
    title: 'ReckonGrid',
    backgroundColor: '#1b1b1b',
    icon: fs.existsSync(icon) ? icon : undefined,
    autoHideMenuBar: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith(`${SCHEME}://`)) return;
    event.preventDefault();
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
  });

  win.loadURL(`${SCHEME}://app/index.html`);
  return win;
}

app.setName('ReckonGrid');
app.setAppUserModelId('de.sellerbach.reckongrid');

app.whenReady().then(() => {
  protocol.handle(SCHEME, (request) => {
    const filePath = fileFromRequest(request.url);
    if (!filePath) return new Response('Forbidden', { status: 403 });
    try {
      const data = fs.readFileSync(filePath);
      const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
      return new Response(data, { headers: { 'Content-Type': type } });
    } catch {
      return new Response('Not found', { status: 404 });
    }
  });

  if (!fs.existsSync(path.join(DIST, 'index.html'))) {
    dialog.showErrorBox(
      'ReckonGrid',
      'Die gebaute Oberfläche fehlt (dist/index.html). Bitte zuerst „npm run build“ ausführen.',
    );
    app.quit();
    return;
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  app.quit();
});
