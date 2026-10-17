"""Verify the unmodified original frontend snapshot independently of backend code."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'original-ui'
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
expected = {item['path'] for item in manifest['files']}
actual = {p.relative_to(root).as_posix() for p in (root / 'dist').rglob('*') if p.is_file()}
if actual != expected:
    raise SystemExit('FAIL: original UI files were added or removed')
aggregate = hashlib.sha256()
for item in sorted(manifest['files'], key=lambda item: item['path']):
    p = root / item['path']
    if not p.resolve().is_relative_to(root.resolve()) or p.is_symlink():
        raise SystemExit('FAIL: unexpected path or symlink')
    data = p.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != item['bytes'] or digest != item['sha256']:
        raise SystemExit('FAIL: altered original file: ' + item['path'])
    aggregate.update(item['path'].removeprefix('dist/').encode() + b'\0')
    aggregate.update(digest.encode())
    aggregate.update(b'\n')
original = 'b459139110b42e71c76b80f18f3bae4309263ebdee4c2af79c099e2f4ff2dd33'
if aggregate.hexdigest() != original or manifest['original_application_dist_sha256'] != original:
    raise SystemExit('FAIL: frontend does not match original application integrity hash')
print(f'PASS: {len(expected)} files match the preserved original UI and embedded application hash.')
