"""Reassemble uploaded resources without executing them or changing license logic."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import struct
import zipfile

LIMIT = 512 * 1024 * 1024


def safe_path(root, name):
    rel = PurePosixPath(name.replace('\\', '/'))
    if rel.is_absolute() or '..' in rel.parts or ':' in name:
        raise ValueError(f'Unsafe archive path: {name}')
    target = root.joinpath(*rel.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes output: {name}')
    return target


def put(root, name, data):
    target = safe_path(root, name)
    if target.exists():
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError(f'Refusing to overwrite different file: {target}')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def unpack_asar(root, data):
    if len(data) < 16:
        raise ValueError('Truncated ASAR')
    _, header_size, _, json_size = struct.unpack_from('<4I', data)
    base = 8 + header_size
    if 16 + json_size > base or base > len(data):
        raise ValueError('Invalid ASAR header')
    header = json.loads(data[16:16 + json_size])

    def walk(files, prefix=''):
        for name, entry in files.items():
            full = prefix + name
            if 'files' in entry:
                walk(entry['files'], full + '/')
            elif entry.get('unpacked') or 'link' in entry:
                raise ValueError(f'Unsupported external ASAR entry: {full}')
            else:
                start = base + int(entry['offset'])
                end = start + entry['size']
                if start < base or end < start or end > len(data):
                    raise ValueError(f'Invalid ASAR offset: {full}')
                put(root, full, data[start:end])
    walk(header['files'])


def verify(root):
    manifest = json.loads((root / 'recovery-manifest.json').read_text())
    for item in manifest:
        p = safe_path(root, item['path'])
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Missing or altered file: {p}')
    required = ['package.json', 'electron/main.cjs', 'dist/index.html',
                'python-embed/python.exe', 'python/server.cp312-win_amd64.pyd']
    missing = [p for p in required if not (root / p).is_file()]
    if missing:
        raise ValueError(f'Missing components: {missing}')
    main = (root / 'electron/main.cjs').read_text(encoding='utf-8')
    expected = re.search(r"DIST_HASH_EXPECTED='([0-9a-f]{64})'", main)
    if not expected:
        raise ValueError('Original frontend integrity hash not found')
    digest = hashlib.sha256()
    dist = root / 'dist'
    for p in sorted(dist.rglob('*')):
        if p.is_file():
            digest.update(p.relative_to(dist).as_posix().encode() + b'\0')
            digest.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
            digest.update(b'\n')
    if digest.hexdigest() != expected[1]:
        raise ValueError('Frontend differs from original application integrity hash')
    print('PASS: frontend matches the integrity hash embedded in original main.cjs.')
    print(f'PASS: {len(manifest)} files match recovery hashes. Runtime functionality is untested.')


def recover(root, archives):
    root.mkdir(parents=True, exist_ok=True)
    for archive in archives:
        with zipfile.ZipFile(archive) as z:
            if sum(i.file_size for i in z.infolist()) > LIMIT:
                raise ValueError('Archive exceeds expanded size limit')
            for item in z.infolist():
                if item.is_dir():
                    continue
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Archive symlinks are not supported')
                # Reading verifies ZIP CRC; no uploaded code is executed.
                data = z.read(item)
                put(root, item.filename, data)
                if item.filename == 'app.asar':
                    unpack_asar(root, data)
    manifest = [dict(path=p.relative_to(root).as_posix(),
                     sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)
                for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'recovery-manifest.json']
    put(root, 'recovery-manifest.json', json.dumps(manifest, indent=2).encode())
    verify(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--out', type=Path, default=Path('recovered'))
    parser.add_argument('archives', nargs='*', type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
    elif args.archives:
        recover(args.out, args.archives)
    else:
        parser.error('Provide ZIP archives or --verify DIRECTORY')
