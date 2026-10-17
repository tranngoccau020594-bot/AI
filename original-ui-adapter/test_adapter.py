import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import server


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = server.backend.Studio(self.tmp.name, start_worker=False)
        self.http = server.create_server(self.studio, 0)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.http.server_port}'
    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join()
        self.studio.close(); self.tmp.cleanup()
    def get(self, path, **kwargs):
        return urllib.request.urlopen(urllib.request.Request(self.base+path, **kwargs), timeout=5)
    def test_original_assets_match_snapshot(self):
        for name in ['assets/index-B863TW1T.js', 'assets/index-DKk8lR4B.css', 'assets/inter-vietnamese-CBcvBZtf.woff2', 'assets/logo-B1-uZFTe.png']:
            with self.get('/'+name) as response:
                self.assertEqual(response.read(), (server.DIST/name).read_bytes())
    def test_home_does_not_load_original_license_screen(self):
        with self.get('/') as response:
            html = response.read().decode()
            self.assertIn('Studio gốc chưa được kết nối', html)
            self.assertNotIn('<script', html)
            self.assertNotIn('index-B863TW1T.js', html)
    def test_new_host_loads_unchanged_original_bundle(self):
        with self.get('/original') as response:
            html = response.read().decode()
            self.assertIn('/adapter/bootstrap.js', html)
            self.assertIn('/assets/index-B863TW1T.js', html)
            self.assertNotIn('/bridge.js', html)
            self.assertIn("connect-src 'self'", response.headers['Content-Security-Policy'])
    def test_public_bootstrap_does_not_supply_licensed_state(self):
        with self.get('/adapter/bootstrap.js') as response:
            script = response.read().decode()
            self.assertIn('window.__S=function', script)
            self.assertIn('Kích hoạt bản quyền', script)
            for value in ['hostVerified', 'licenseStatus', 'PUBLIC_KEY', 'verifyLicense', 'privateKey']:
                self.assertNotIn(value, script)
    def test_missing_original_identity_is_an_explicit_error(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx: self.get('/api/machine-id')
        self.assertEqual(ctx.exception.code, 501)
        body = json.load(ctx.exception)
        self.assertFalse(body['ok'])
    def test_every_write_is_rejected_without_changing_jobs(self):
        for endpoint in ['/api/license/session', '/api/jobs', '/compat/jobs']:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                self.get(endpoint, data=b'{}', method='POST', headers={'Content-Type':'application/json'})
            self.assertEqual(ctx.exception.code, 501)
        self.assertEqual(self.studio.list_jobs(), [])
    def test_read_jobs_reflects_independent_backend(self):
        self.studio.create_job({'kind':'image','prompt':'Read-only fixture','quantity':1,'size':'1024x1024'})
        with self.get('/compat/jobs') as response:
            data = json.load(response)
            self.assertEqual(data['jobs'][0]['prompt'], 'Read-only fixture')
            self.assertEqual(data['jobs'][0]['status'], 'draft')
    def test_foreign_origin_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get('/adapter/status', headers={'Origin':'https://foreign.example'})
        self.assertEqual(ctx.exception.code, 403)


if __name__ == '__main__': unittest.main()
