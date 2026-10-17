'use strict';
const crypto = require('node:crypto');

const DOMAIN = 'studio-license-v1.';
function deviceId(deviceIdentity) {
  if (typeof deviceIdentity !== 'string' || !deviceIdentity.trim()) throw new Error('Device identity is required');
  return crypto.createHash('sha256').update('studio-device-v1\0' + deviceIdentity.trim()).digest('hex');
}
function validateClaims(c) {
  if (!c || c.version !== 1 || typeof c.id !== 'string' || !c.id ||
      typeof c.product !== 'string' || !c.product || typeof c.customer !== 'string' || !c.customer ||
      !/^[a-f0-9]{64}$/.test(c.deviceId) || !Number.isSafeInteger(c.issuedAt) ||
      !Number.isSafeInteger(c.notBefore) || !Number.isSafeInteger(c.expiresAt) ||
      c.issuedAt < 0 || c.notBefore < 0 || c.expiresAt <= c.notBefore ||
      c.expiresAt <= c.issuedAt || !Array.isArray(c.features) ||
      c.features.some(f => typeof f !== 'string' || !f || f.length > 128)) {
    throw new Error('Invalid license claims');
  }
}
function issueLicense({ privateKey, product, customer, deviceId: machine, expiresAt,
                        features = [], notBefore, now = Date.now() }) {
  const key = crypto.createPrivateKey(privateKey);
  if (key.asymmetricKeyType !== 'ed25519') throw new Error('Ed25519 private key required');
  const claims = { version: 1, id: crypto.randomUUID(), product, customer, deviceId: machine,
    issuedAt: now, notBefore: notBefore ?? now, expiresAt, features };
  validateClaims(claims);
  const payload = Buffer.from(JSON.stringify(claims)).toString('base64url');
  const signature = crypto.sign(null, Buffer.from(DOMAIN + payload), key).toString('base64url');
  return payload + '.' + signature;
}
function verifyLicense(token, { publicKey, product, deviceId: machine, now = Date.now(), revokedIds = [] }) {
  const fail = reason => ({ ok: false, reason });
  if (typeof product !== 'string' || !product || !/^[a-f0-9]{64}$/.test(machine) ||
      !Number.isSafeInteger(now) || now < 0 || !Array.isArray(revokedIds)) return fail('configuration');
  if (typeof token !== 'string' || token.length > 16384 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token)) return fail('format');
  const [payload, sig] = token.split('.');
  let claims;
  try {
    const key = crypto.createPublicKey(publicKey);
    const signature = Buffer.from(sig, 'base64url');
    if (key.asymmetricKeyType !== 'ed25519' || signature.length !== 64 ||
        signature.toString('base64url') !== sig ||
        !crypto.verify(null, Buffer.from(DOMAIN + payload), key, signature)) return fail('signature');
    const data = Buffer.from(payload, 'base64url');
    if (data.toString('base64url') !== payload) return fail('format');
    claims = JSON.parse(data.toString('utf8'));
    validateClaims(claims);
  } catch { return fail('invalid'); }
  if (claims.product !== product) return fail('product');
  if (claims.deviceId !== machine) return fail('device');
  if (now < claims.notBefore || now < claims.issuedAt) return fail('not_yet_valid');
  if (now >= claims.expiresAt) return fail('expired');
  if (revokedIds.includes(claims.id)) return fail('revoked');
  return { ok: true, claims };
}
module.exports = { deviceId, issueLicense, verifyLicense };
