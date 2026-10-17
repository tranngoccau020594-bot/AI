'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
if (process.platform !== 'win32' || process.arch !== 'x64') {
  console.error('Backend gốc yêu cầu Windows x64 và Python 3.12. Không thể chạy trên máy này.');
  process.exit(1);
}
const root = path.resolve(__dirname, '..', 'recovered');
const pythonDir = path.join(root, 'python-embed');
for (const f of ['package.json', 'electron/main.cjs', 'python-embed/python.exe', 'python/server.cp312-win_amd64.pyd', 'dist/index.html']) {
  if (!fs.existsSync(path.join(root, f))) {
    console.error(`Thiếu ${f}. Chạy tools/recover.py trước.`);
    process.exit(1);
  }
}
const electron = require('electron');
const child = spawn(electron, [root], {
  cwd: root, stdio: 'inherit', windowsHide: false,
  env: { ...process.env, PATH: pythonDir + path.delimiter + process.env.PATH }
});
child.on('error', e => { console.error(e.message); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 1; });
