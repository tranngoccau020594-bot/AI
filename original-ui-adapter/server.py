"""Read-only original-frontend compatibility probe, backed by the independent studio."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('independent_studio', ROOT / 'studio-backend/server.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
DIST = ROOT / 'original-ui/dist'
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.woff2': 'font/woff2', '.png': 'image/png', '.ico': 'image/x-icon', '.json': 'application/json; charset=utf-8', '.bin': 'application/octet-stream'}

# Public, non-license API slots identified from frontend method names.
# These are adapter paths, not claims that the private string table was recovered.
API_SLOTS = {2: '/compat/i18n', 3: '/compat/ping', 8: '/compat/accounts', 0x27: '/compat/jobs', 0x30: '/compat/logs', 0x34: '/compat/media', 0x40: '/compat/ui-strings', 0x41: '/compat/characters'}


def create_server(studio, port=8770, bootstrap=True):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def reply(self, code, data, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes): data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)
        def dispatch(self):
            try:
                allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
                if self.headers.get('Host') not in allowed or self.headers.get('Origin') not in (None, *('http://' + h for h in allowed)):
                    return self.reply(403, {'ok': False, 'error': 'Host/Origin rejected'})
                path = urllib.parse.urlsplit(self.path).path
                if self.command != 'GET':
                    return self.reply(501, {'ok': False, 'error': 'Read-only compatibility probe. License activation and job execution are not implemented here.'})
                if path == '/adapter/status':
                    return self.reply(200, {'ok': True, 'stage': 'original-frontend-read-only', 'original_files_modified': False, 'license_emulation': False, 'job_execution': False})
                if path == '/adapter/bootstrap.js':
                    strings = json.loads((DIST / 'chuoi-mo.json').read_text(encoding='utf-8'))
                    strings.update({str(key): value for key, value in API_SLOTS.items()})
                    js = '"use strict";\nconst adapterPublicStrings=' + json.dumps(strings, ensure_ascii=False) + ';\n'
                    js += 'window.__adapterMissingStrings=new Set();\nwindow.__S=function(id){const value=adapterPublicStrings[String(id)];if(typeof value==="string")return value;window.__adapterMissingStrings.add(Number(id));return "";};\n'
                    return self.reply(200, js.encode(), 'text/javascript; charset=utf-8')
                if path in ('/', '/index.html'):
                    if not bootstrap:
                        return self.reply(200, (DIST / 'index.html').read_bytes(), MIME['.html'])
                    # Separate HTML host: original HTML on disk and its bundle remain unmodified.
                    html = '''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DTMAX original UI · compatibility probe</title><link rel="icon" href="/icon.ico"><link rel="stylesheet" href="/assets/index-DKk8lR4B.css"><script src="/adapter/bootstrap.js"></script><script type="module" src="/assets/index-B863TW1T.js"></script></head><body><div id="root"></div></body></html>'''
                    return self.reply(200, html.encode(), MIME['.html'])
                if path in ('/api/health', '/api/ping', '/compat/ping'):
                    return self.reply(200, studio.health())
                if path == '/compat/i18n':
                    return self.reply(200, {'ok': True, 'pairs': [], 'language': 'vi'})
                if path == '/compat/ui-strings':
                    return self.reply(200, {'ok': False, 'error': 'Only publicly supplied strings are available; protected runtime strings are not reconstructed.'})
                if path == '/compat/jobs':
                    return self.reply(200, {'ok': True, 'jobs': studio.list_jobs(), 'adapter_stage': 'read-only; legacy shape not yet validated'})
                if path == '/compat/logs':
                    return self.reply(200, {'ok': True, 'logs': studio.workspace()['logs']})
                if path == '/compat/media':
                    return self.reply(200, {'ok': True, 'media': [dict(output, jobId=job['id']) for job in studio.list_jobs() for output in job['outputs']], 'adapter_stage': 'read-only; legacy shape not yet validated'})
                if path in ('/compat/accounts', '/compat/characters'):
                    return self.reply(501, {'ok': False, 'error': 'This original frontend feature has not been adapted.'})
                if path.startswith('/media/'):
                    name = path.removeprefix('/media/')
                    if '/' in name or '\\' in name or '..' in name or len(name) > 40:
                        return self.reply(404, {'ok': False, 'error': 'Media not found'})
                    file = studio.media_dir / name
                    if not file.is_file():
                        return self.reply(404, {'ok': False, 'error': 'Media not found'})
                    data = file.read_bytes()
                    return self.reply(200, data, backend.image_type(data)[1])
                if path.startswith(('/api/', '/compat/')):
                    return self.reply(501, {'ok': False, 'error': 'Original endpoint not implemented. No replacement license token, signature or activation state is supplied.'})
                file = (DIST / path.lstrip('/')).resolve()
                if not file.is_relative_to(DIST.resolve()) or not file.is_file():
                    return self.reply(404, {'ok': False, 'error': 'Not found'})
                return self.reply(200, file.read_bytes(), MIME.get(file.suffix, 'application/octet-stream'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.reply(500, {'ok': False, 'error': 'Compatibility probe failed'})
        do_GET = dispatch
        do_POST = dispatch
        do_PUT = dispatch
        do_DELETE = dispatch
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--raw', action='store_true')
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / 'tools/verify-original-ui.py')], check=True)
    studio = backend.Studio(args.data_dir, start_worker=False)
    server = create_server(studio, args.port, bootstrap=not args.raw)
    print(f'Compatibility probe: http://127.0.0.1:{server.server_port}', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); studio.close()
