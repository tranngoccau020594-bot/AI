'use strict';
const path = require('node:path'), fs = require('node:fs'), os = require('node:os');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { createRequire } = require('node:module');
const { chromium } = createRequire(path.join(__dirname, '../web-demo/package.json'))('playwright');
const assert = require('node:assert/strict');
async function runProbe(browser, raw) {
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'original-ui-probe-'));
  const child = spawn(process.env.STUDIO_TEST_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
    ['-B', path.join(__dirname, 'server.py'), '--data-dir', data, '--port', '0', ...(raw ? ['--raw'] : [])],
    { env: { ...process.env, STUDIO_API_KEY: '', STUDIO_API_BASE: '', STUDIO_IMAGE_MODEL: '' }, stdio: ['ignore', 'pipe', 'pipe'] });
  try {
    const origin = await new Promise((resolve, reject) => {
      let text = ''; const timeout = setTimeout(() => reject(new Error('Probe readiness timeout')), 15000);
      child.stdout.on('data', chunk => { text += chunk.toString(); const match = text.match(/Compatibility probe: (http:\/\/127\.0\.0\.1:\d+)/); if (match) { clearTimeout(timeout); resolve(match[1]); } });
      child.on('error', reject); child.on('exit', () => { clearTimeout(timeout); reject(new Error('Probe process exited')); });
    });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = [], requests = [], external = [];
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) { external.push(url.origin + url.pathname); return route.abort(); }
      return route.continue();
    });
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { const url = new URL(response.url()); if (/^\/(api|compat)\//.test(url.pathname)) requests.push({ path: url.pathname, status: response.status() }); });
    await page.goto(origin);
    await page.waitForTimeout(3000);
    const report = { mode: raw ? 'original-html-without-bootstrap' : 'separate-host-with-public-bootstrap', errors, requests, externalBlocked: external,
      bodyText: (await page.locator('body').innerText()).slice(0, 8000),
      missingPublicStrings: await page.evaluate(() => [...(window.__adapterMissingStrings || [])]) };
    if (!raw) {
      assert.deepEqual(errors, []);
      assert.match(report.bodyText, /Kích hoạt bản quyền để sử dụng Studio/);
      assert.ok(requests.some(r => r.path === '/api/machine-id' && r.status === 501));
      await page.screenshot({ path: path.join(__dirname, 'original-ui-preview.png'), fullPage: true });
    } else assert.ok(errors.some(e => e.includes('__S')));
    await page.close(); return report;
  } finally {
    if (child.exitCode === null) { const exited = once(child, 'exit'); child.kill(); await exited; }
    fs.rmSync(data, { recursive: true, force: true });
  }
}
(async () => {
  const browser = await chromium.launch({ ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), args: ['--no-sandbox'] });
  try {
    const raw = await runProbe(browser, true), adapted = await runProbe(browser, false);
    const report = { result: 'blocked-before-studio', originalAssetsChanged: false, licenseEmulated: false, studioValidated: false, paidApiRequests: 0, probes: [raw, adapted] };
    fs.writeFileSync(path.join(__dirname, 'browser-report.json'), JSON.stringify(report, null, 2));
    console.log('PASS: original HTML failure diagnosed; public bootstrap renders genuine activation screen. Studio remains BLOCKED at missing /api/machine-id and original licensing/runtime dependencies.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
