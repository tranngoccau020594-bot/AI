import base64
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from server import Studio, ImageProvider, APIError, create_server

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aV3sAAAAASUVORK5CYII=')
JOB = {'kind': 'image', 'prompt': 'Test scene', 'quantity': 1, 'size': '1024x1024', 'project': 'Test', 'ratio': '1:1'}


class FixtureProvider:
    ready = True
    model = 'fixture-only'
    def generate(self, job):
        return [(PNG, 'png', 'image/png')]


class StudioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Studio(self.tmp.name, provider=FixtureProvider(), start_worker=False)
    def tearDown(self):
        self.app.close()
        self.tmp.cleanup()
    def test_duplicate_instance_cannot_reset_existing_jobs(self):
        job = self.app.create_job(JOB)
        self.app.action(job['id'], 'run')
        with self.assertRaises(RuntimeError):
            Studio(self.tmp.name, provider=FixtureProvider(), start_worker=False)
        self.assertEqual(self.app.list_jobs()[0]['status'], 'queued')
    def test_image_lifecycle(self):
        job = self.app.create_job(JOB)
        self.assertEqual(job['status'], 'draft')
        self.app.action(job['id'], 'run')
        self.assertTrue(self.app.process_one())
        result = self.app.list_jobs()[0]
        self.assertEqual(result['status'], 'succeeded')
        output = self.app.media_dir / Path(result['outputs'][0]['url']).name
        self.assertEqual(output.read_bytes(), PNG)
        self.app.action(job['id'], 'delete')
        self.assertFalse(output.exists())
        self.assertEqual(self.app.list_jobs(), [])
    def test_missing_provider_does_not_claim_generation(self):
        self.app.provider = ImageProvider('', '', '')
        job = self.app.create_job(JOB)
        with self.assertRaises(APIError) as ctx:
            self.app.action(job['id'], 'run')
        self.assertEqual(ctx.exception.status, 503)
        self.assertEqual(self.app.list_jobs()[0]['status'], 'draft')
    def test_video_is_explicitly_unimplemented(self):
        job = self.app.create_job(dict(JOB, kind='video'))
        with self.assertRaises(APIError) as ctx:
            self.app.action(job['id'], 'run')
        self.assertEqual(ctx.exception.status, 501)
    def test_pending_cancellation_never_calls_provider(self):
        job = self.app.create_job(JOB)
        self.app.action(job['id'], 'run')
        self.app.action(job['id'], 'cancel')
        self.assertFalse(self.app.process_one())
        self.assertEqual(self.app.list_jobs()[0]['status'], 'cancelled')
    def test_running_cancel_discards_late_result(self):
        job = self.app.create_job(JOB)
        def generate(_):
            self.app.action(job['id'], 'cancel')
            return [(PNG, 'png', 'image/png')]
        self.app.provider.generate = generate
        self.app.action(job['id'], 'run')
        self.app.process_one()
        self.assertEqual(self.app.list_jobs()[0]['status'], 'cancelled')
        self.assertEqual(list(self.app.media_dir.iterdir()), [])
    def test_failure_can_retry_without_leaking_exception(self):
        job = self.app.create_job(JOB)
        def fail(_):
            raise RuntimeError('private-key-must-not-be-stored')
        self.app.provider.generate = fail
        self.app.action(job['id'], 'run')
        self.app.process_one()
        self.assertEqual(self.app.list_jobs()[0]['status'], 'failed')
        self.assertNotIn('private-key', json.dumps(self.app.workspace()))
        self.app.provider = FixtureProvider()
        self.app.action(job['id'], 'run')
        self.app.process_one()
        self.assertEqual(self.app.list_jobs()[0]['status'], 'succeeded')
    def test_restart_preserves_workspace_and_fails_inflight_without_resubmit(self):
        self.app.save_workspace({'projects': ['One'], 'config': {'studio': 'Own studio'}})
        job = self.app.create_job(JOB)
        self.app.action(job['id'], 'run')
        self.app.close()
        self.app = Studio(self.tmp.name, provider=FixtureProvider(), start_worker=False)
        self.assertEqual(self.app.workspace()['config']['studio'], 'Own studio')
        self.assertEqual(self.app.list_jobs()[0]['status'], 'failed')
        self.assertFalse(self.app.process_one())
    def test_input_and_state_validation(self):
        for data in [dict(JOB, prompt=''), dict(JOB, quantity=True), dict(JOB, quantity=9), dict(JOB, size='bad'), dict(JOB, referenceName='image.png')]:
            with self.assertRaises(APIError): self.app.create_job(data)
        job = self.app.create_job(JOB)
        self.app.action(job['id'], 'run')
        for action in ['run', 'delete']:
            with self.assertRaises(APIError): self.app.action(job['id'], action)
    def test_http_authorization_origin_host_media_and_workspace(self):
        web = Path(__file__).resolve().parent.parent / 'web-demo'
        server = create_server(self.app, web, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def request(path, data=None, method=None, headers=None):
            h = {'Content-Type': 'application/json', 'X-Studio-Token': self.app.token}
            h.update(headers or {})
            req = urllib.request.Request(base+path, data=json.dumps(data).encode() if data is not None else None, headers=h, method=method)
            return urllib.request.urlopen(req, timeout=5)
        try:
            with request('/api/health') as response: self.assertEqual(json.load(response)['backend'], 'independent-studio')
            with self.assertRaises(urllib.error.HTTPError) as ctx: request('/api/jobs', headers={'X-Studio-Token': 'wrong'})
            self.assertEqual(ctx.exception.code, 401)
            for h in [{'Origin': 'https://evil.example'}, {'Host': 'evil.example'}]:
                with self.assertRaises(urllib.error.HTTPError) as ctx: request('/api/session', headers=h)
                self.assertEqual(ctx.exception.code, 403)
            with request('/api/jobs', JOB, 'POST') as response: job = json.load(response)
            with request('/api/jobs/'+job['id']+'/run', {}, 'POST'): pass
            self.app.process_one()
            output = self.app.list_jobs()[0]['outputs'][0]['url']
            with request(output) as response: self.assertEqual(response.read(), PNG)
            with request('/') as response: self.assertIn(b'/bridge.js', response.read())
            with request('/api/workspace') as response: self.assertEqual(len(json.load(response)['jobs']), 1)
        finally:
            server.shutdown(); server.server_close(); thread.join()
    def test_provider_constructs_real_request_and_decodes_base64(self):
        provider = ImageProvider('https://provider.example/v1', 'test-only-key', 'gpt-image-test')
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, _): return json.dumps({'data': [{'b64_json': base64.b64encode(PNG).decode()}]}).encode()
        class Opener:
            def open(self, req, timeout):
                self.request = req
                return Response()
        opener = Opener()
        with patch('urllib.request.build_opener', return_value=opener):
            self.assertEqual(provider.generate(JOB)[0][0], PNG)
        self.assertEqual(opener.request.full_url, 'https://provider.example/v1/images/generations')
        self.assertEqual(json.loads(opener.request.data)['prompt'], JOB['prompt'])
        self.assertEqual(opener.request.get_header('Authorization'), 'Bearer test-only-key')


if __name__ == '__main__':
    unittest.main()
