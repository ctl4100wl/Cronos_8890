#!/usr/bin/env python3
"""Package the same Image/DT table with Floyd and a configured AK3 installer."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)
IMAGE = ROOT / 'arch/arm64/boot/Image'
DTB = ROOT / 'arch/arm64/boot/dtb.img'
for path in (IMAGE, DTB):
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f'Missing build output: {path}')
# These exact assets were compared against the supplied V8.1 release ZIP.
assets = {
    'floyd/ramdisk.img': '8ee73726aec71a63c3401e020e6a54a0fed32f119a96f039ba609a7c529f5fd3',
    'floyd/tools/magiskboot': '5b9d75c2eaaed4479f5bc06580950b065a8f45ae0386a11ac7c1cbede3316b6c',
    'floyd/tools/busybox': '8d4edb906eabd996993f3fea62d72e03352a39a28ac0f11c1ad6dab814973f12',
}
for name, digest in assets.items():
    if hashlib.sha256((ROOT / 'Cronos/kernelzip' / name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f'Developer installer asset changed: {name}')
revision = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
sha = revision[:12]
name = f'Cronos-G930X-OneUI-Q-KSUN-{sha}'

def write_zip(target, files):
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data, executable in files:
            entry = zipfile.ZipInfo(name)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            archive.writestr(entry, data)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f'Invalid archive: {target}')

files = [(n, (ROOT / 'Cronos/kernelzip' / n).read_bytes(), '/tools/' in n) for n in assets]
files += [
    ('floyd/G930X-kernel', IMAGE.read_bytes(), False),
    ('floyd/G930X-dtb', DTB.read_bytes(), False),
    ('LICENSE', (ROOT / 'Cronos/kernelzip/LICENSE').read_bytes(), False),
    ('META-INF/com/google/android/update-binary', (ROOT / 'Cronos/installer-g930x/update-binary').read_bytes(), True),
    ('META-INF/com/google/android/updater-script', b'# Cronos G930X installer\n', False),
]
write_zip(OUT / f'{name}-Floyd.zip', files)
aksha = '41f04bdb4ee30a44e429c2c1131d5e8bb32b15f1'
akrepo = os.environ.get('ANYKERNEL3_DIR')
with tempfile.TemporaryDirectory() as temp:
    if not akrepo:
        akrepo = temp
        subprocess.run(['git', 'init', '-q', temp], check=True)
        subprocess.run(['git', '-C', temp, 'remote', 'add', 'origin', 'https://github.com/osm0sis/AnyKernel3.git'], check=True)
        subprocess.run(['git', '-C', temp, 'fetch', '--depth=1', 'origin', aksha], check=True)
        subprocess.run(['git', '-C', temp, 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    if subprocess.check_output(['git', '-C', akrepo, 'rev-parse', 'HEAD'], text=True).strip() != aksha:
        raise SystemExit('Wrong AnyKernel3 source revision')
    akrepo = Path(akrepo)
    files = []
    for folder in ['META-INF', 'tools']:
        for path in sorted((akrepo / folder).rglob('*')):
            if path.is_file():
                files.append((str(path.relative_to(akrepo)), path.read_bytes(), True))
    files += [
        ('anykernel.sh', (ROOT / 'Cronos/anykernel3/anykernel.sh').read_bytes(), True),
        ('Image', IMAGE.read_bytes(), False),
        ('dt', DTB.read_bytes(), False),
        ('cronos-boot-template.img', (ROOT / 'Cronos/kernelzip/floyd/ramdisk.img').read_bytes(), False),
        ('LICENSE-Cronos', (ROOT / 'Cronos/kernelzip/LICENSE').read_bytes(), False),
    ]
    for license in akrepo.glob('LICENSE*'):
        files.append((license.name, license.read_bytes(), False))
    write_zip(OUT / f'{name}-AnyKernel3.zip', files)
manifest = {
    'kernel_commit': revision,
    'device': 'G930F/S/L/K (Exynos herolte)', 'rom': 'OneUI Q',
    'kernelsu_next': 'v3.4.0-legacy 8af3d4fec33be32fa5d3f8dae4f380fac45bf2cd',
    'anykernel3': aksha, 'developer_installer_sha256': assets,
    'hardware_tested': False,
    'manager_uapi_version': 4,
    'manager_version_code': 33294,
    'manager_apk': 'https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v3.4.0/KernelSU_Next_v3.4.0-spoofed_33294-release.apk',
}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
with (OUT / 'SHA256SUMS').open('w') as sums:
    for path in sorted(OUT.glob('*.zip')):
        sums.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n')
print('\n'.join(str(p) for p in OUT.glob('*.zip')))
