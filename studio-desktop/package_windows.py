"""Build directory with electron-builder, then ZIP and verify without changing source files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'release-independent'
APP = OUT / 'win-unpacked'


def validate():
    resources = APP / 'resources'
    for name in ['server.py', 'bridge.js']:
        expected = ROOT / 'studio-backend' / name
        assert (resources / 'studio-backend' / name).read_bytes() == expected.read_bytes(), name
    assert (resources / 'web-demo/index.html').read_bytes() == (ROOT / 'web-demo/index.html').read_bytes()
    assert (resources / 'python-embed/python312._pth').read_bytes() == (ROOT / 'studio-desktop/runtime/python312._pth').read_bytes()
    assert not (resources / 'python').exists(), 'Original DTMAX backend must not be present'
    assert not (resources / 'python-embed/Lib').exists(), 'Unused third-party site-packages must not be bundled'
    assert not (resources / 'python-embed/get-pip.py').exists()
    assert (APP / 'OPEN-WITH-OPENAI.cmd').read_bytes() == (ROOT / 'studio-desktop/OPEN-WITH-OPENAI.cmd').read_bytes()
    exe = APP / 'Independent Studio.exe'
    assert exe.read_bytes()[:2] == b'MZ'
    # Inspect the application ASAR through the builder's installed library.
    subprocess.run(['node', '-e', "const fs=require('fs'),asar=require('@electron/asar');const a=process.argv[1];const expected=fs.readFileSync('studio-desktop/main.cjs');if(!asar.extractFile(a,'main.cjs').equals(expected))process.exit(1);console.log('PASS: independent Electron main matches source');", str(resources / 'app.asar')], cwd=ROOT, check=True)
    print('PASS: independent backend/frontend and isolated Python runtime match source; no DTMAX core modules.')


def package():
    subprocess.run(['node', str(ROOT / 'node_modules/electron-builder/cli.js'), '--config', 'studio-desktop/builder.json', '--win', '--x64', '--dir'], cwd=ROOT, check=True)
    shutil.copy2(ROOT / 'studio-desktop/OPEN-WITH-OPENAI.cmd', APP / 'OPEN-WITH-OPENAI.cmd')
    validate()
    archive = OUT / 'Independent-Studio-0.2.0-windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file in sorted(APP.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(APP).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None, 'ZIP CRC failure'
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    (OUT / 'SHA256SUMS.txt').write_text(sha + '  ' + archive.name + '\n')
    report = {'windows_build': 'passed', 'packaged_sources': 'matched', 'old_dtmax_backend': 'absent', 'third_party_site_packages': 'absent', 'zip_crc': 'passed', 'windows_runtime': 'not tested', 'real_openai_generation': 'not tested; API key not supplied', 'sha256': sha, 'bytes': archive.stat().st_size}
    (OUT / 'build-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    os.chdir(ROOT)
    package()
