'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { deviceId, issueLicense, verifyLicense } = require('./license.cjs');
const pair = () => crypto.generateKeyPairSync('ed25519', {
  publicKeyEncoding: { type: 'spki', format: 'pem' }, privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
});
const keys = pair();
const machine = deviceId('test-machine');
const now = 1800000000000;
const base = { privateKey: keys.privateKey, product: 'my-studio', customer: 'test', deviceId: machine,
  expiresAt: now + 10000, now, features: ['images'] };
const options = { publicKey: keys.publicKey, product: 'my-studio', deviceId: machine, now };
test('accepts signed device-bound license and preserves features', () => {
  const r = verifyLicense(issueLicense(base), options); assert.equal(r.ok, true); assert.deepEqual(r.claims.features, ['images']);
});
test('rejects edited claims, wrong issuer and altered signature', () => {
  const token = issueLicense(base); const [p, s] = token.split('.');
  const edited = JSON.parse(Buffer.from(p, 'base64url')); edited.expiresAt += 100000;
  assert.equal(verifyLicense(Buffer.from(JSON.stringify(edited)).toString('base64url') + '.' + s, options).ok, false);
  assert.equal(verifyLicense(token, { ...options, publicKey: pair().publicKey }).ok, false);
  assert.equal(verifyLicense(p + '.' + (s[0] === 'A' ? 'B' : 'A') + s.slice(1), options).ok, false);
});
test('rejects different device and product', () => {
  const token = issueLicense(base);
  assert.equal(verifyLicense(token, { ...options, deviceId: deviceId('other') }).reason, 'device');
  assert.equal(verifyLicense(token, { ...options, product: 'other' }).reason, 'product');
});
test('enforces exact expiry and activation boundaries', () => {
  const token = issueLicense({ ...base, notBefore: now + 100 });
  assert.equal(verifyLicense(token, options).reason, 'not_yet_valid');
  assert.equal(verifyLicense(token, { ...options, now: now + 100 }).ok, true);
  assert.equal(verifyLicense(token, { ...options, now: base.expiresAt }).reason, 'expired');
});
test('rejects revoked ids', () => {
  const token = issueLicense(base); const r = verifyLicense(token, options);
  assert.equal(verifyLicense(token, { ...options, revokedIds: [r.claims.id] }).reason, 'revoked');
});
test('fails closed on malformed input and missing verification configuration', () => {
  for (const token of ['', null, 'abc.def', 'x'.repeat(17000)]) assert.equal(verifyLicense(token, options).ok, false);
  assert.equal(verifyLicense(issueLicense(base), { ...options, product: '' }).reason, 'configuration');
  assert.throws(() => issueLicense({ ...base, expiresAt: now }));
  assert.throws(() => deviceId(''));
});
