#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${CROSS_COMPILE:?Set CROSS_COMPILE to Linaro 4.9.4 aarch64-linux-gnu- prefix}"
export ARCH=arm64 ANDROID_MAJOR_VERSION=p PLATFORM_VERSION=9.0.0
export LOCALVERSION=-Cronos-G930X-Q-KSUN
export KBUILD_BUILD_USER=cronos KBUILD_BUILD_HOST=github-actions
mkdir -p artifacts
config=arch/arm64/configs/cronos_g930x_defconfig
trap 'rm -f "$config" arch/arm64/boot/dts/exynos8890.dtsi' EXIT
# Same order and OneUI-Q HALL setting as the creator's cronos.sh.
cat arch/arm64/configs/{exynos8890,hero,oneui,cronos}_defconfig > "$config"
cat >> "$config" <<'CONFIG'
CONFIG_KSU=y
CONFIG_KSU_MANUAL_HOOK=y
# CONFIG_KSU_DEBUG is not set
# CONFIG_KPROBES is not set
# CONFIG_ALWAYS_PERMISSIVE is not set
CONFIG_HALL_EVENT_REVERSE=y
CONFIG
cp arch/arm64/boot/exynos8890_Oneui.dtsi arch/arm64/boot/dts/exynos8890.dtsi
# WireGuard is absent from the repository; obtain a fixed release rather than
# allowing Kbuild to download and replace sources while parsing makefiles.
if [[ ! -f net/wireguard/Kconfig ]]; then
    wg=$(mktemp -d)
    git -C "$wg" init -q
    git -C "$wg" remote add origin https://github.com/WireGuard/wireguard-linux-compat.git
    git -C "$wg" fetch --depth=1 origin 18fbcd68a35a892527345dc5679d0b2d860ee004
    git -C "$wg" checkout --detach FETCH_HEAD
    mkdir -p net/wireguard
    cp -a "$wg/src/." net/wireguard/
    rm -rf "$wg"
fi
make_args=(ARCH=arm64 "CROSS_COMPILE=$CROSS_COMPILE" CCACHE= 'HOSTCFLAGS=-O2 -fcommon')
make "${make_args[@]}" cronos_g930x_defconfig
for option in CONFIG_KSU=y CONFIG_KSU_MANUAL_HOOK=y CONFIG_MODEL_HEROLTE=y CONFIG_HALL_EVENT_REVERSE=y; do
    grep -qx "$option" .config || { echo "Missing $option" >&2; exit 1; }
done
grep -qx '# CONFIG_ALWAYS_PERMISSIVE is not set' .config
if grep -Eq '^CONFIG_KPROBES=[ym]$' .config; then
    echo 'KPROBES must be disabled for the manual-hook build' >&2
    exit 1
fi
cp .config artifacts/kernel.config
make -j"${JOBS:-$(nproc)}" "${make_args[@]}" Image dtb.img 2>&1 | tee artifacts/build.log
[[ -s arch/arm64/boot/Image && -s arch/arm64/boot/dtb.img ]]
python3 scripts/ci/package-g930x.py
