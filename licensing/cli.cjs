#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { issueLicense, verifyLicense } = require('./license.cjs');
const { windowsDeviceId } = require('./device-windows.cjs');
const [command, ...args] = process.argv.slice(2);
const usage = `Commands:
  init KEY_DIRECTORY
  device
  issue PRIVATE_KEY CLAIMS_JSON OUTPUT_LICENSE
  verify PUBLIC_KEY PRODUCT DEVICE_ID LICENSE_FILE
Claims JSON: {"product":"my-studio","customer":"customer-1","deviceId":"64 hex characters","expiresAt":1893456000000,"features":["images","videos"]}
Keep the private key on the issuer machine, outside application builds.`;
try {
  if (command === 'init' && args.length === 1) {
    const dir = path.resolve(args[0]);
    if (fs.existsSync(dir)) throw new Error('Key directory already exists; refusing to overwrite');
    const keys = crypto.generateKeyPairSync('ed25519', {
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
    });
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    fs.writeFileSync(path.join(dir, 'issuer.private.pem'), keys.privateKey, { flag: 'wx', mode: 0o600 });
    fs.writeFileSync(path.join(dir, 'app.public.pem'), keys.publicKey, { flag: 'wx' });
    console.log('Created keys. Ship only app.public.pem with your own application.');
  } else if (command === 'device' && args.length === 0) {
    console.log(windowsDeviceId());
  } else if (command === 'issue' && args.length === 3) {
    const claims = JSON.parse(fs.readFileSync(args[1], 'utf8'));
    // Explicit allowlist: input cannot override issuer time or signing key.
    const token = issueLicense({ privateKey: fs.readFileSync(args[0]), product: claims.product,
      customer: claims.customer, deviceId: claims.deviceId, expiresAt: claims.expiresAt,
      notBefore: claims.notBefore, features: claims.features });
    fs.writeFileSync(args[2], token + '\n', { flag: 'wx', mode: 0o600 });
    console.log('License written.');
  } else if (command === 'verify' && args.length === 4) {
    const result = verifyLicense(fs.readFileSync(args[3], 'utf8').trim(), {
      publicKey: fs.readFileSync(args[0]), product: args[1], deviceId: args[2] });
    console.log(JSON.stringify(result, null, 2));
    if (!result.ok) process.exitCode = 1;
  } else {
    console.error(usage); process.exitCode = 2;
  }
} catch (error) { console.error(error.message); process.exitCode = 1; }
