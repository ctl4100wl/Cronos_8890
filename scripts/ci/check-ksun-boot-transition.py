#!/usr/bin/env python3
"""Exercise Cronos's actual SELinux transition hook with policy calls mocked."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[2] / 'security/selinux/hooks.c')
args = parser.parse_args()
source = args.source.read_text()
start = source.index('static int check_nnp_nosuid(')
brace = source.index('{', start)
depth = 1
end = brace + 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
hook = source[start:end]
preamble = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t u32;
#define LSM_UNSAFE_NO_NEW_PRIVS 1
#define MNT_NOSUID 2
struct vfsmount { int mnt_flags; };
struct path { struct vfsmount *mnt; };
struct file { struct path f_path; };
struct linux_binprm { int unsafe; struct file *file; };
struct task_security_struct { u32 sid; };
static int security_secctx_to_secid(const char *ctx, size_t len, u32 *sid) {
    (void)len;
    if (!strcmp(ctx, "u:r:ksu:s0")) *sid=20;
    else if (!strcmp(ctx, "u:r:su:s0")) *sid=21;
    else return -EINVAL;
    return 0;
}
static int security_secid_to_secctx(u32 sid, char **ctx, u32 *len) {
    *ctx = sid == 1 ? "u:r:init:s0" : "u:r:untrusted_app:s0";
    *len = strlen(*ctx)+1;
    return 0;
}
static void security_release_secctx(char *ctx, u32 len) { (void)ctx; (void)len; }
static int security_bounded_transition(u32 old, u32 new) { (void)old; (void)new; return -EACCES; }
'''
tests = r'''
static void check(u32 from, u32 to, int flags, int nnp, int expected) {
    struct vfsmount mnt={flags};
    struct file file={{&mnt}};
    struct linux_binprm bprm={nnp,&file};
    struct task_security_struct old={from}, new={to};
    int actual=check_nnp_nosuid(&bprm,&old,&new);
    if(actual!=expected) {
        fprintf(stderr,"transition %u->%u nosuid=%d nnp=%d: got %d expected %d\n",from,to,flags,nnp,actual,expected);
        exit(1);
    }
}
int main(void) {
#ifdef CONFIG_KSU
    check(1,20,MNT_NOSUID,0,0);
    check(1,20,0,LSM_UNSAFE_NO_NEW_PRIVS,0);
#else
    check(1,20,MNT_NOSUID,0,-EACCES);
    check(1,20,0,LSM_UNSAFE_NO_NEW_PRIVS,-EPERM);
#endif
    check(2,20,MNT_NOSUID,0,-EACCES);
    check(2,20,0,LSM_UNSAFE_NO_NEW_PRIVS,-EPERM);
    check(1,21,MNT_NOSUID,0,-EACCES);
    check(1,22,MNT_NOSUID,0,-EACCES);
    check(2,20,0,0,0);
    check(2,2,MNT_NOSUID,LSM_UNSAFE_NO_NEW_PRIVS,0);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'transition.c'
    c.write_text(preamble + hook + tests)
    for enabled in (True, False):
        executable = directory / ('ksu' if enabled else 'stock')
        command = ['cc', '-std=gnu11', str(c), '-o', str(executable)]
        if enabled:
            command.insert(1, '-DCONFIG_KSU=1')
        subprocess.run(command, check=True)
        subprocess.run([str(executable)], check=True)
print('SELinux boot transition checks passed: init->ksu allowed; unrelated transitions stay denied; CONFIG_KSU=n preserves stock checks')
