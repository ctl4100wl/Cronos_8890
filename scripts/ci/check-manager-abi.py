#!/usr/bin/env python3
"""Compare the driver wire ABI to the actual supported Manager release headers."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--driver-include', type=Path, default=ROOT / 'drivers/kernelsu/include')
args = p.parse_args()
manager = ROOT / 'scripts/ci/manager-v3.4.0'
header = (manager / 'uapi/supercall.h').read_text()
commands = sorted(set(re.findall(r'\bKSU_IOCTL_[A-Z0-9_]+\b', header)))
structures = ['ksu_get_info_cmd', 'ksu_get_info_legacy_cmd', 'ksu_get_version_tag_cmd',
              'ksu_get_hook_mode_cmd', 'app_profile']
source = '#include <stdio.h>\n#include <stdbool.h>\n#include <stddef.h>\n#include "uapi/supercall.h"\nint main(void) {\n'
source += 'printf("uapi_version=%lu\\n", (unsigned long)KERNEL_SU_UAPI_VERSION);\n'
for command in commands:
    source += f'printf("{command}=%lu\\n", (unsigned long){command});\n'
for name in structures:
    source += f'printf("sizeof_{name}=%lu\\n", (unsigned long)sizeof(struct {name}));\n'
for field in ['version', 'flags', 'features', 'uapi_version']:
    source += f'printf("info_offset_{field}=%lu\\n", (unsigned long)offsetof(struct ksu_get_info_cmd, {field}));\n'
source += 'return 0; }\n'

def probe(include, temp, name):
    c = temp / f'{name}.c'
    binary = temp / name
    c.write_text(source)
    subprocess.run(['cc', '-std=gnu11', '-I', str(include), str(c), '-o', str(binary)], check=True)
    return dict(line.split('=', 1) for line in subprocess.check_output([str(binary)], text=True).splitlines())

with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    expected = probe(manager, temp, 'manager')
    actual = probe(args.driver_include, temp, 'driver')
errors = [f'{key}: driver={actual[key]}, Manager={value}' for key, value in expected.items() if actual[key] != value]
if errors:
    raise SystemExit('KernelSU Next Manager ABI mismatch:\n' + '\n'.join(errors))
print(f'Manager v3.4.0 (33294) ABI matched: UAPI {actual["uapi_version"]}, {len(commands)} ioctl IDs, structure sizes and GET_INFO offsets')
