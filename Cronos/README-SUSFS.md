# Cronos G930X SUSFS

This branch ports simonpunk's **SUSFS v1.5.5 kernel-4.9** implementation to
Samsung Cronos **3.18.140**, using the existing **KernelSU Next v3.4.0-legacy
33294 / Manager UAPI 4**. The creator's OneUI Q installer and configured
AnyKernel3 continue to package the same kernel and device tree.

Upstream source: https://gitlab.com/simonpunk/susfs4ksu/tree/kernel-4.9
Pinned source commit: `41ba0b533b8524a0ba95a5952506a75f17355450`.
The inherited SUSFS source license is preserved in `Cronos/susfs-tools/LICENSE`.

## Installation and verification

1. Flash either the Floyd or AnyKernel3 **SUSFS155** ZIP for Exynos G930F/S/L/K,
   OneUI Q, then fully reboot. Use one kernel installer.
2. Install `Cronos-S7-SUSFS155-Tools.zip` through the existing KernelSU Next
   Manager, then reboot. Its installer checks the live v1.5.5 control interface.
3. Tap that module's Action button. Version must report `v1.5.5`, variant
   `NON-GKI`, with the supported feature list.
4. Keep one functioning Zygisk implementation and AlwaysStrong as separate
   modules. This kernel does not bundle or certify either attestation engine.

Root-shell command:

```
/data/adb/modules/cronos_susfs155/ksu_susfs show version
/data/adb/modules/cronos_susfs155/ksu_susfs show enabled_features
```

Do not install a current SUSFS v2 control tool/module over this v1.5.5 interface.
The matching CLI is built from the vendored v1.5.5 source using the same pinned
Linaro compiler, statically linked for Linux 3.7+ (no Android dynamic linker), and
its SHA256 is recorded in the manifest. The upstream prebuilt targets Android 35;
this package builds from source to avoid that newer platform dependency. It runs
from its module directory, without introducing another system mount. The module
service only disables verbose SUSFS logging; it does not change attestation props,
set a fake GKI kernel version, or replace Next's su hooks.

## Implemented features and adaptations

- Path/dentry lookup and ARM64 plus ARM32 directory enumeration hiding.
- KSU-created mount IDs and peer groups, proc mount entries, namespace-copy
  renumbering, fdinfo and statfs handling.
- Per-app kstat/maps spoofing, uname, cmdline, open redirect and symbol filtering.
- Automatic KSU mount/bind tagging and a try-unmount list integrated into Next's
  existing credential-overridden task_work, respecting its app unmount policy.
- Legacy `0xDEADBEEF` PRCTL controls in a separate dispatcher, restricted to UID0
  in the KSU SELinux domain. Manager ioctl IDs/layouts stay unchanged.
- Legacy nameidata/path ownership, Samsung clone_mnt branches and int-returning
  seq-file APIs adapted for 3.18. RKP namespace protection excludes SUSFS in
  Kconfig; this G930X configuration already has that protection disabled.
- Table updates use RCU deletion/publication; potentially sleeping writer work
  uses mutexes. Cmdline usercopy happens before locking; unmount paths are copied
  before acquiring namespace locks. kstat defaults are filled before overrides.
- Deprecated `sus_su` and overlayfs stat spoofing are not exposed. Existing Next
  root/startup hooks and enforcing SELinux stay enabled.

## Validation and limits

CI checks the actual PRCTL dispatcher with mocked credentials/usercopy, compares
Manager release ABI headers, and runs the init-to-ksu transition regression.
It then builds Image and dtb.img, verifies linked SUSFS implementations, validates
installer assets/ZIPs and publishes a prerelease automatically.

A compile and host tests do not establish a successful device boot, correct
app-specific hiding, suspend/resume stability or a Play Integrity verdict. Those
checks remain physical-device tests. Keep a known-working BOOT backup.
