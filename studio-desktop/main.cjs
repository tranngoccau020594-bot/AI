'use strict';
const { app, BrowserWindow, dialog, session } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
let backend, win, exiting = false;
function healthy(url) {
  return new Promise(resolve => {
    const req = http.get(url + '/api/health', response => {
      let body = ''; response.on('data', chunk => { body += chunk; });
      response.on('end', () => { try { resolve(response.statusCode === 200 && JSON.parse(body).backend === 'independent-studio'); } catch { resolve(false); } });
    });
    req.on('error', () => resolve(false)); req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}
async function start() {
  const root = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
  const runtime = path.join(root, app.isPackaged ? 'python-embed' : 'recovered/python-embed', 'python.exe');
  const python = process.platform === 'win32' && fs.existsSync(runtime) ? runtime : process.platform === 'win32' ? 'python' : 'python3';
  const dataDir = path.join(app.getPath('userData'), 'backend-data');
  let alive = true;
  const ready = new Promise((resolve, reject) => {
    let text = '';
    const timeout = setTimeout(() => reject(new Error('Backend chưa sẵn sàng sau 30 giây.')), 30000);
    backend = spawn(python, ['-I', '-B', path.join(root, 'studio-backend/server.py'), '--port', '0', '--data-dir', dataDir, '--web-root', path.join(root, 'web-demo')], {
      cwd: root, env: { ...process.env }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']
    });
    backend.stdout.on('data', chunk => {
      text = (text + chunk.toString()).slice(-2000);
      const match = text.match(/Independent Studio: (http:\/\/127\.0\.0\.1:\d+)/);
      if (match) { clearTimeout(timeout); resolve(match[1]); }
    });
    backend.stderr.on('data', () => {}); // Do not expose environment or private provider response data.
    backend.on('error', () => { alive = false; clearTimeout(timeout); reject(new Error('Không khởi chạy được Python backend.')); });
    backend.on('exit', () => {
      alive = false; clearTimeout(timeout); reject(new Error('Backend đã dừng trước khi sẵn sàng.'));
      if (!exiting && win && !win.isDestroyed()) { dialog.showErrorBox('Backend đã dừng', 'Dữ liệu đã lưu vẫn nằm trong thư mục người dùng. Đóng rồi mở lại app.'); app.quit(); }
    });
  });
  const origin = await ready;
  if (!await healthy(origin) || !alive) throw new Error('Backend không vượt qua kiểm tra sức khỏe.');
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  win = new BrowserWindow({ width: 1450, height: 980, minWidth: 780, minHeight: 650, title: 'Independent Studio',
    backgroundColor: '#0d0e14', autoHideMenuBar: true,
    webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false } });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== origin) event.preventDefault(); });
  await win.loadURL(origin);
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(start).catch(error => { dialog.showErrorBox('Independent Studio', error.message); app.quit(); });
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', () => { exiting = true; if (backend && !backend.killed) backend.kill(); });
