# AnyKernel3 configuration for Cronos / Exynos Galaxy S7 flat only.
# Framework: osm0sis; developer boot template: ananjaser1211 / corsicanu.
properties() { '
kernel.string=Cronos G930X OneUI-Q KernelSU Next legacy
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=1
device.name1=herolte
device.name2=heroltexx
device.name3=herolteskt
device.name4=heroltektt
device.name5=heroltelgt
supported.versions=10
supported.patchlevels=
supported.vendorpatchlevels=
'; }
BLOCK=/dev/block/platform/155a0000.ufs/by-name/BOOT
IS_SLOT_DEVICE=0
RAMDISK_COMPRESSION=none
PATCH_VBMETA_FLAG=0
NO_MAGISK_CHECK=1
. tools/ak3-core.sh
loader=$(getprop ro.bootloader)
[ -n "$loader" ] || loader=$(sed -n 's/.*androidboot.bootloader=\([^ ]*\).*/\1/p' /proc/cmdline)
case "$loader" in G930F*|G930S*|G930L*|G930K*) ;; *) abort "Unsupported bootloader: $loader" ;; esac
ui_print 'Installing developer clean ramdisk; removes Magisk/old kernel ramdisk changes.'
# Keep AK3 partition discovery/size/write checks, but unpack the exact Cronos
# clean boot template instead of carrying forward the previously installed ramdisk.
split_boot
cp -f "$AKHOME/cronos-boot-template.img" "$BOOTIMG" || abort 'Missing Cronos boot template'
cd "$SPLITIMG"
magiskboot unpack -h "$BOOTIMG" || abort 'Cannot unpack Cronos boot template'
cd "$AKHOME"
# The S7 Samsung DT table lives in the boot image extra field, not an
# appended Image-dtb. AK3 calls this payload "dt" when repacking extra.
flash_boot
