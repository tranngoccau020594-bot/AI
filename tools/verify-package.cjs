'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const asar = require('@electron/asar');
const root = path.resolve(__dirname, '..');
const resources = path.join(root, 'release', 'win-unpacked', 'resources');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'recovered/recovery-manifest.json'), 'utf8'));
let count = 0;
for (const item of manifest) {
  let data;
  if (/^(python\/|python-embed\/|dist\/)/.test(item.path)) {
    data = fs.readFileSync(path.join(resources, item.path));
  } else if (/^electron\//.test(item.path) || item.path === 'icon.ico') {
    data = asar.extractFile(path.join(resources, 'app.asar'), item.path);
  } else continue;
  const hash = crypto.createHash('sha256').update(data).digest('hex');
  if (hash !== item.sha256) throw new Error(`Packaged content differs: ${item.path}`);
  count++;
}
const exe = fs.readFileSync(path.join(resources, '..', 'Seedance AI.exe'));
if (exe.subarray(0, 2).toString() !== 'MZ') throw new Error('Invalid Windows executable');
const pe = exe.readUInt32LE(60);
if (exe.readUInt16LE(pe + 4) !== 0x8664) throw new Error('Executable is not x64');
console.log(`PASS: Windows x64 executable and ${count} packaged original files verified. Runtime is untested.`);
