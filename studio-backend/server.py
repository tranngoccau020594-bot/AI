"""Independent local studio backend; no DTMAX code or licensing dependencies."""
import argparse
import base64
import binascii
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 2 * 1024 * 1024
MAX_IMAGE = 30 * 1024 * 1024
SIZES = {'1024x1024', '1536x1024', '1024x1536', '1792x1024', '1024x1792'}


class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def image_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png', 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg', 'image/jpeg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    raise ValueError('Dịch vụ không trả về PNG, JPEG hoặc WebP hợp lệ.')


class ImageProvider:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url if base_url is not None else os.getenv('STUDIO_API_BASE', 'https://api.openai.com/v1')).rstrip('/')
        self.api_key = api_key if api_key is not None else os.getenv('STUDIO_API_KEY', '')
        self.model = model if model is not None else os.getenv('STUDIO_IMAGE_MODEL', 'gpt-image-1')
        parsed = urllib.parse.urlsplit(self.base_url)
        self.ready = bool(self.api_key and self.model and parsed.scheme == 'https' and parsed.hostname
                          and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment)

    @property
    def supported_sizes(self):
        if self.model.startswith('gpt-image'):
            return {'1024x1024', '1536x1024', '1024x1536'}
        if self.model == 'dall-e-3':
            return {'1024x1024', '1792x1024', '1024x1792'}
        if self.model == 'dall-e-2':
            return {'1024x1024'}
        return SIZES

    def generate(self, job):
        if not self.ready:
            raise APIError(503, 'Chưa cấu hình API key; kiểm tra STUDIO_API_BASE và STUDIO_IMAGE_MODEL.')
        payload = {'model': self.model, 'prompt': job['prompt'], 'n': job['quantity'], 'size': job['size']}
        if self.model.startswith('dall-e'):
            payload['response_format'] = 'b64_json'
        req = urllib.request.Request(self.base_url + '/images/generations',
                                     data=json.dumps(payload).encode(), method='POST',
                                     headers={'Authorization': 'Bearer ' + self.api_key,
                                              'Content-Type': 'application/json'})
        # Never follow redirects carrying Authorization to another destination.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(req, timeout=180) as response:
                body = response.read(MAX_IMAGE * 2 + 1)
                if len(body) > MAX_IMAGE * 2:
                    raise ValueError('Phản hồi tạo ảnh vượt giới hạn.')
                result = json.loads(body)
        except urllib.error.HTTPError as exc:
            # Do not persist provider response bodies: they may contain private data.
            raise ValueError(f'Dịch vụ tạo ảnh trả HTTP {exc.code}. Kiểm tra cấu hình/quota/model.') from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError('Không kết nối được dịch vụ tạo ảnh hoặc hết thời gian chờ.') from None
        rows = result.get('data') if isinstance(result, dict) else None
        if not isinstance(rows, list) or not rows or len(rows) > job['quantity']:
            raise ValueError('Phản hồi tạo ảnh không có danh sách data hợp lệ.')
        images = []
        for row in rows:
            try:
                data = base64.b64decode(row['b64_json'], validate=True)
            except (KeyError, TypeError, ValueError, binascii.Error):
                raise ValueError('Adapter yêu cầu b64_json; chưa hỗ trợ dịch vụ chỉ trả URL.') from None
            if len(data) > MAX_IMAGE:
                raise ValueError('Ảnh vượt giới hạn 30 MB.')
            extension, mime = image_type(data)
            images.append((data, extension, mime))
        return images


class Studio:
    def __init__(self, data_dir, provider=None, start_worker=True):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir = self.data_dir / 'media'
        self.media_dir.mkdir(exist_ok=True)
        self.instance_lock = (self.data_dir / '.instance.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if self.instance_lock.tell() == 0:
                    self.instance_lock.write(b'0')
                    self.instance_lock.flush()
                self.instance_lock.seek(0)
                msvcrt.locking(self.instance_lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.instance_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.instance_lock.close()
            raise RuntimeError('Thư mục dữ liệu đang được một backend khác sử dụng.') from None
        self.db_path = self.data_dir / 'studio.sqlite3'
        self.provider = provider if provider is not None else ImageProvider()
        self.token = secrets.token_urlsafe(32)
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.lock = threading.Lock()
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                status TEXT NOT NULL, created REAL NOT NULL, error TEXT NOT NULL DEFAULT '', outputs TEXT NOT NULL DEFAULT '[]');
              CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, created REAL NOT NULL, message TEXT NOT NULL);
            ''')
            db.execute("UPDATE jobs SET status='failed', error='Backend đã khởi động lại; tác vụ cũ không tự gửi lại để tránh tính phí trùng.' WHERE status IN ('running','queued','cancelling')")
            db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', ('workspace', json.dumps({'projects': ['Dự án đầu tiên'], 'config': {'studio': 'Studio cá nhân'}})))
        self.worker = threading.Thread(target=self.work, daemon=True)
        if start_worker:
            self.worker.start()

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def log(self, message, db):
        db.execute('INSERT INTO logs(created,message) VALUES (?,?)', (time.time(), message))
        db.execute('DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 500)')

    def health(self):
        return {'ok': True, 'backend': 'independent-studio', 'version': '0.1.0',
                'images_ready': self.provider.ready, 'videos_ready': False,
                'model': self.provider.model if self.provider.ready else '',
                'supported_sizes': sorted(getattr(self.provider, 'supported_sizes', SIZES))}

    def list_jobs(self):
        with self.db() as db:
            rows = db.execute('SELECT * FROM jobs ORDER BY created DESC').fetchall()
        return [self.job_json(r) for r in rows]

    @staticmethod
    def job_json(row):
        return {**json.loads(row['payload']), 'id': row['id'], 'status': row['status'],
                'error': row['error'], 'outputs': json.loads(row['outputs']),
                'createdAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(row['created']))}

    def workspace(self):
        with self.db() as db:
            settings = json.loads(db.execute("SELECT value FROM settings WHERE key='workspace'").fetchone()[0])
            logs = [{'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(r['created'])), 'text': r['message']}
                    for r in db.execute('SELECT * FROM logs ORDER BY id DESC LIMIT 200')]
        return {'version': 1, **settings, 'jobs': self.list_jobs(), 'logs': logs}

    def save_workspace(self, data):
        projects, config = data.get('projects'), data.get('config')
        if (not isinstance(projects, list) or not 1 <= len(projects) <= 100
                or any(not isinstance(p, str) or not p.strip() or len(p) > 80 for p in projects)
                or not isinstance(config, dict) or not isinstance(config.get('studio'), str)
                or not config['studio'].strip() or len(config['studio']) > 80):
            raise APIError(400, 'Dự án hoặc cấu hình không hợp lệ.')
        clean = {'projects': list(dict.fromkeys(projects)), 'config': {'studio': config['studio'].strip()}}
        with self.db() as db:
            db.execute("UPDATE settings SET value=? WHERE key='workspace'", (json.dumps(clean),))
            self.log('Đã lưu cấu hình và dự án', db)
        return clean

    @staticmethod
    def validate_job(data):
        if not isinstance(data, dict):
            raise APIError(400, 'Tác vụ phải là đối tượng JSON.')
        prompt = data.get('prompt', '')
        quantity = data.get('quantity', 1)
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 3000:
            raise APIError(400, 'Mô tả phải có từ 1 đến 3000 ký tự.')
        if type(quantity) is not int or not 1 <= quantity <= 4:
            raise APIError(400, 'Backend hỗ trợ số lượng từ 1 đến 4 mỗi tác vụ.')
        if data.get('kind') not in ('image', 'video') or data.get('size', '1024x1024') not in SIZES:
            raise APIError(400, 'Loại tác vụ hoặc kích thước không hợp lệ.')
        project = data.get('project', '')
        if not isinstance(project, str) or len(project) > 80:
            raise APIError(400, 'Dự án không hợp lệ.')
        if data.get('referenceName'):
            raise APIError(422, 'Adapter hiện chưa hỗ trợ ảnh tham chiếu. Hãy bỏ ảnh hoặc chỉ giữ nháp ở bản web cũ.')
        ratio = data.get('ratio', '1:1')
        if ratio not in ('1:1', '16:9', '9:16', '4:3', '3:4'):
            raise APIError(400, 'Tỉ lệ không hợp lệ.')
        return {'prompt': prompt.strip(), 'quantity': quantity, 'kind': data['kind'], 'size': data.get('size', '1024x1024'),
                'project': project, 'ratio': ratio, 'quality': data.get('size', '1024x1024'), 'duration': '5'}

    def create_job(self, data):
        job = self.validate_job(data)
        jid = uuid.uuid4().hex
        with self.db() as db:
            if db.execute('SELECT count(*) FROM jobs').fetchone()[0] >= 1000:
                raise APIError(409, 'Tối đa 1000 tác vụ; hãy xuất hoặc xóa bớt dữ liệu.')
            db.execute('INSERT INTO jobs(id,payload,status,created) VALUES (?,?,?,?)', (jid, json.dumps(job), 'draft', time.time()))
            self.log('Đã tạo bản nháp ' + jid[:8], db)
        return next(j for j in self.list_jobs() if j['id'] == jid)

    def action(self, jid, action):
        with self.lock, self.db() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
            if row is None:
                raise APIError(404, 'Không tìm thấy tác vụ.')
            if action == 'run':
                if row['status'] not in ('draft', 'failed', 'cancelled'):
                    raise APIError(409, 'Tác vụ không ở trạng thái có thể gửi.')
                if json.loads(row['payload'])['kind'] == 'video':
                    raise APIError(501, 'Chưa tích hợp nhà cung cấp video. Không có video được tạo.')
                if json.loads(row['payload'])['size'] not in getattr(self.provider, 'supported_sizes', SIZES):
                    raise APIError(422, 'Kích thước không được model đã cấu hình hỗ trợ.')
                if not self.provider.ready:
                    raise APIError(503, 'Chưa cấu hình API tạo ảnh trên máy chạy backend.')
                db.execute("UPDATE jobs SET status='queued',error='' WHERE id=?", (jid,))
                self.log('Đã đưa vào hàng đợi ' + jid[:8], db)
            elif action == 'cancel':
                if row['status'] not in ('queued', 'running'):
                    raise APIError(409, 'Chỉ có thể hủy tác vụ đang chờ hoặc đang chạy.')
                target = 'cancelling' if row['status'] == 'running' else 'cancelled'
                db.execute('UPDATE jobs SET status=? WHERE id=?', (target, jid))
                self.log('Đã yêu cầu hủy ' + jid[:8] + '; dịch vụ ngoài có thể vẫn tính phí', db)
            elif action == 'delete':
                if row['status'] in ('queued', 'running', 'cancelling'):
                    raise APIError(409, 'Hãy hủy và đợi tác vụ dừng trước khi xóa.')
                for output in json.loads(row['outputs']):
                    (self.media_dir / Path(output['url']).name).unlink(missing_ok=True)
                db.execute('DELETE FROM jobs WHERE id=?', (jid,))
                self.log('Đã xóa tác vụ ' + jid[:8], db)
            else:
                raise APIError(404, 'Hành động không hợp lệ.')
        self.wake.set()
        return {'ok': True}

    def work(self):
        while not self.stop.is_set():
            if not self.process_one():
                self.wake.wait(0.5)
                self.wake.clear()

    def process_one(self):
        with self.lock, self.db() as db:
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return False
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (row['id'],))
        written = []
        try:
            images = self.provider.generate(json.loads(row['payload']))
            outputs = []
            for data, extension, mime in images:
                # Validate again at the trust boundary, including injected adapters.
                verified_ext, verified_mime = image_type(data)
                if verified_ext != extension or verified_mime != mime or len(data) > MAX_IMAGE:
                    raise ValueError('Adapter trả dữ liệu ảnh không hợp lệ.')
                name = uuid.uuid4().hex + '.' + extension
                target = self.media_dir / name
                target.write_bytes(data)
                written.append(target)
                outputs.append({'url': '/media/' + name, 'mime': mime, 'bytes': len(data)})
            if not outputs:
                raise ValueError('Nhà cung cấp không trả ảnh.')
            with self.lock, self.db() as db:
                status = db.execute('SELECT status FROM jobs WHERE id=?', (row['id'],)).fetchone()[0]
                if status == 'cancelling':
                    for path in written:
                        path.unlink(missing_ok=True)
                    db.execute("UPDATE jobs SET status='cancelled' WHERE id=?", (row['id'],))
                else:
                    db.execute("UPDATE jobs SET status='succeeded',outputs=? WHERE id=?", (json.dumps(outputs), row['id']))
                self.log('Đã kết thúc tác vụ ' + row['id'][:8], db)
        except Exception as exc:
            for path in written:
                path.unlink(missing_ok=True)
            with self.lock, self.db() as db:
                current = db.execute('SELECT status FROM jobs WHERE id=?', (row['id'],)).fetchone()[0]
                status = 'cancelled' if current == 'cancelling' else 'failed'
                # Built-in provider emits safe errors; never persist arbitrary adapter exceptions.
                message = str(exc) if isinstance(self.provider, ImageProvider) and isinstance(exc, (ValueError, APIError)) else 'Tác vụ thất bại; không ghi chi tiết để tránh lộ dữ liệu riêng tư.'
                db.execute('UPDATE jobs SET status=?,error=? WHERE id=?', (status, message[:300], row['id']))
                self.log('Tác vụ ' + row['id'][:8] + ': ' + status, db)
        return True

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.worker.is_alive():
            self.worker.join(timeout=2)
        if not self.instance_lock.closed:
            self.instance_lock.close()


def create_server(studio, web_root, port=8766):
    web_root = Path(web_root)
    bridge = Path(__file__).with_name('bridge.js')

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log tokens, prompts, query strings or provider credentials.

        def send(self, status, data, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            if self.headers.get('Transfer-Encoding'):
                raise APIError(400, 'Transfer-Encoding không được hỗ trợ.')
            if self.headers.get('Content-Type', '').split(';')[0].lower() != 'application/json':
                raise APIError(415, 'Yêu cầu application/json.')
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 <= length <= MAX_BODY:
                    raise APIError(413, 'JSON vượt giới hạn 2 MB.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError()
                return data
            except (ValueError, UnicodeDecodeError):
                raise APIError(400, 'JSON không hợp lệ.') from None

        def dispatch(self):
            try:
                hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
                if self.headers.get('Host') not in hosts:
                    raise APIError(403, 'Host không hợp lệ.')
                origin = self.headers.get('Origin')
                if origin and origin not in {'http://' + h for h in hosts}:
                    raise APIError(403, 'Origin không hợp lệ.')
                path = urllib.parse.urlsplit(self.path).path
                if path.startswith('/api/') and path not in ('/api/health', '/api/session'):
                    if not secrets.compare_digest(self.headers.get('X-Studio-Token', ''), studio.token):
                        raise APIError(401, 'Thiếu token phiên backend.')
                if self.command == 'GET':
                    if path == '/api/health':
                        return self.send(200, studio.health())
                    if path == '/api/session':
                        return self.send(200, {'token': studio.token})
                    if path == '/api/workspace':
                        return self.send(200, studio.workspace())
                    if path == '/api/jobs':
                        return self.send(200, {'jobs': studio.list_jobs()})
                    if path == '/api/media':
                        return self.send(200, {'media': [dict(o, jobId=j['id'], prompt=j['prompt']) for j in studio.list_jobs() for o in j['outputs']]})
                    if path in ('/', '/index.html'):
                        html = (web_root / 'index.html').read_text(encoding='utf-8')
                        html = html.replace('</body>', '<script src="/bridge.js"></script></body>')
                        return self.send(200, html.encode(), 'text/html; charset=utf-8')
                    if path == '/bridge.js':
                        return self.send(200, bridge.read_bytes(), 'text/javascript; charset=utf-8')
                    if path.startswith('/media/'):
                        name = path.removeprefix('/media/')
                        if len(name) > 40 or '/' in name or '\\' in name or '..' in name:
                            raise APIError(404, 'Không tìm thấy media.')
                        file = studio.media_dir / name
                        if not file.is_file():
                            raise APIError(404, 'Không tìm thấy media.')
                        data = file.read_bytes()
                        return self.send(200, data, image_type(data)[1])
                elif self.command == 'PUT' and path == '/api/workspace':
                    return self.send(200, studio.save_workspace(self.body()))
                elif self.command == 'POST' and path == '/api/jobs':
                    return self.send(201, studio.create_job(self.body()))
                elif self.command == 'POST' and path.startswith('/api/jobs/'):
                    self.body()
                    parts = path.split('/')
                    if len(parts) == 5:
                        return self.send(200, studio.action(parts[3], parts[4]))
                elif self.command == 'DELETE' and path.startswith('/api/jobs/') and path.count('/') == 3:
                    return self.send(200, studio.action(path.split('/')[-1], 'delete'))
                raise APIError(404, 'Endpoint không tồn tại.')
            except APIError as exc:
                self.send(exc.status, {'ok': False, 'error': str(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.send(500, {'ok': False, 'error': 'Lỗi backend nội bộ. Không trả dữ liệu nhạy cảm.'})

        do_GET = dispatch
        do_POST = dispatch
        do_PUT = dispatch
        do_DELETE = dispatch

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--data-dir', type=Path, default=Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'IndependentStudio')
    parser.add_argument('--web-root', type=Path, default=Path(__file__).resolve().parent.parent / 'web-demo')
    args = parser.parse_args()
    studio = Studio(args.data_dir)
    server = create_server(studio, args.web_root, args.port)
    print(f'Independent Studio: http://127.0.0.1:{server.server_port}', flush=True)
    print('Image provider: ' + ('configured' if studio.provider.ready else 'not configured') + '; video: not implemented', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        studio.close()
