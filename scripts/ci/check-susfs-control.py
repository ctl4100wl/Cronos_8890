#!/usr/bin/env python3
"""Exercise the actual legacy PRCTL dispatcher with mocked credentials/usercopy."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = root / 'drivers/kernelsu/feature/susfs.c'
config = (root / 'drivers/kernelsu/Kconfig').read_text()
options = re.findall(r'^config (KSU_SUSFS(?:_[A-Z_]+)?)$', config, re.M)
defs = (root / 'include/linux/susfs_def.h').read_text()
macros = '\n'.join(line for line in defs.splitlines() if line.startswith('#define CMD_SUSFS_'))
version = re.search(r'^#define SUSFS_VERSION ("[^"]+")', (root / 'include/linux/susfs.h').read_text(), re.M)[1]
functions = ['susfs_add_sus_path', 'susfs_add_sus_mount', 'susfs_add_sus_kstat',
             'susfs_update_sus_kstat', 'susfs_add_try_umount', 'susfs_set_uname',
             'susfs_set_cmdline_or_bootconfig', 'susfs_add_open_redirect']
common = '''#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
typedef uint64_t u64;
#define __user
#define VERIFY_WRITE 1
#define DEFINE_MUTEX(x) int x
#define mutex_lock(x) ((void)0)
#define mutex_unlock(x) ((void)0)
static unsigned test_uid;
static bool test_domain, test_access = true;
struct test_kuid { unsigned val; };
static struct test_kuid current_uid(void) { return (struct test_kuid){test_uid}; }
static void *current_cred(void) { return 0; }
static bool is_ksu_domain(void) { return test_domain; }
static bool is_zygote(void *unused) { return false; }
static bool access_ok(int mode, void *p, unsigned long n) { return test_access && p; }
static int copy_to_user(void *p, const void *s, unsigned long n) {
 if (!p) return 1; memcpy(p, s, n); return 0;
}
static void susfs_set_log(bool enabled) {}
void susfs_run_try_umount_for_current_mnt_ns(void) {}
'''
common += macros + '\n#define SUSFS_VERSION ' + version + '\n#define SUSFS_VARIANT "NON-GKI"\n'
common += '\n'.join(f'static int {fn}(void *p) {{ return 17; }}' for fn in functions)
tests = r'''
int main(void) {
 int error = 123;
 char version[16] = {0}, variant[16] = {0};
 uint64_t features = 0;
 #define CALL(cmd, arg) ksu_susfs_prctl(0xDEADBEEF, cmd, (unsigned long)(arg), 0, (unsigned long)&error)
 assert(ksu_susfs_prctl(1, CMD_SUSFS_SHOW_VERSION, 0, 0, 0) == -ENOSYS);
 assert(CALL(42, version) == -ENOSYS);
 test_uid = 10000; test_domain = true;
 assert(CALL(CMD_SUSFS_SHOW_VERSION, version) == -EPERM);
 test_uid = 0; test_domain = false;
 assert(CALL(CMD_SUSFS_SHOW_VERSION, version) == -EPERM);
 test_domain = true; test_access = false;
 assert(CALL(CMD_SUSFS_SHOW_VERSION, version) == -EFAULT);
 test_access = true;
 assert(CALL(CMD_SUSFS_SHOW_VERSION, version) == 0 && error == 0);
 assert(!strcmp(version, "v1.5.5"));
 assert(CALL(CMD_SUSFS_SHOW_VARIANT, variant) == 0 && error == 0);
 assert(!strcmp(variant, "NON-GKI"));
 assert(CALL(CMD_SUSFS_SHOW_ENABLED_FEATURES, &features) == 0 && error == 0);
 assert((features & (1ULL << 1)) && !(features & (1ULL << 5)));
 assert(CALL(CMD_SUSFS_ADD_SUS_PATH, version) == 0 && error == 17);
 assert(CALL(CMD_SUSFS_SUS_SU, version) == 0 && error == -EOPNOTSUPP);
 assert(CALL(CMD_SUSFS_SHOW_VERSION, 0) == 0 && error == -EFAULT);
 return 0;
}
'''
# Check every userspace payload member against the actual kernel structs,
# including padding-sensitive field widths (the old CLI used bool vs int).
cli = (root / 'tools/susfs/main.c').read_text()
kernel_header = (root / 'include/linux/susfs.h').read_text()
for name in ['st_susfs_sus_path', 'st_susfs_sus_mount', 'st_susfs_sus_kstat',
             'st_susfs_try_umount', 'st_susfs_uname', 'st_susfs_open_redirect']:
    def members(text):
        body = re.search(r'struct ' + name + r' \{(.*?)\};', text, re.S)[1]
        body = re.sub(r'//[^\n]*', '', body)
        return re.sub(r'\s+', '', body)
    assert members(cli) == members(kernel_header), f'{name}: userspace/kernel payload mismatch'
for line in macros.splitlines():
    name, value = line.split()[1:3]
    assert re.search(r'^#define ' + name + r' ' + value + r'$', cli, re.M), name
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    (td / 'common.h').write_text(common)
    for name in ['linux/cred.h', 'linux/errno.h', 'linux/namei.h', 'linux/mutex.h',
                 'linux/susfs.h', 'linux/uaccess.h', 'selinux/selinux.h']:
        p = td / name
        p.parent.mkdir(exist_ok=True)
        p.write_text('#include <asm-generic/errno.h>\n' if name == 'linux/errno.h' else '#include "common.h"\n')
    (td / 'probe.c').write_text(f'#include "{source}"\n' + tests)
    subprocess.run(['cc', '-std=gnu11', '-I', str(td)] +
                   [f'-DCONFIG_{op}=1' for op in options] +
                   [str(td / 'probe.c'), '-o', str(td / 'probe')], check=True)
    subprocess.run([str(td / 'probe')], check=True)
print('SUSFS v1.5.5 control checks passed: access restrictions, feature/version replies, errors; normal prctl preserved')
