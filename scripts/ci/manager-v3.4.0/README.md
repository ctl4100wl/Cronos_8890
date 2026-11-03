# Official Manager ABI fixture

Unmodified UAPI headers from KernelSU Next Manager v3.4.0 / versionCode 33294,
commit `1a879d6a866f80b1fa1c1009a2ffa747873cbb5e`:
https://github.com/KernelSU-Next/KernelSU-Next/tree/v3.4.0/uapi

Both the regular and spoofed APK flavors use this UAPI. The fixture is compiled
independently from the driver headers by `check-manager-abi.py`. It checks API
level, all 26 ioctl IDs, GET_INFO field offsets and shared structure sizes.
The code retains the upstream GPL-3.0 license (see LICENSE).
