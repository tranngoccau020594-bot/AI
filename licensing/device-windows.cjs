'use strict';
const { execFileSync } = require('node:child_process');
const { deviceId } = require('./license.cjs');
function windowsDeviceId() {
  if (process.platform !== 'win32') throw new Error('Windows is required for this device identity provider');
  const output = execFileSync('reg.exe', ['query', 'HKLM\\SOFTWARE\\Microsoft\\Cryptography',
    '/v', 'MachineGuid', '/reg:64'], { encoding: 'utf8', windowsHide: true, timeout: 5000 });
  const match = output.match(/MachineGuid\s+REG_SZ\s+([a-f0-9-]{36})/i);
  if (!match) throw new Error('Cannot read Windows MachineGuid');
  return deviceId(match[1].toLowerCase());
}
module.exports = { windowsDeviceId };
