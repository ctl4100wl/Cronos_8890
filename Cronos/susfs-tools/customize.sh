#!/system/bin/sh
[ "$KSU" = true ] || abort "Install through KernelSU Next."
[ "$ARCH" = arm64 ] || abort "This package requires arm64."
set_perm "$MODPATH/ksu_susfs" 0 0 0755
version=$("$MODPATH/ksu_susfs" show version 2>/dev/null)
[ "$version" = v1.5.5 ] || abort "Boot the Cronos SUSFS v1.5.5 kernel first (reported: $version)."
# The CLI runs directly from its module directory; no system mounts required.
touch "$MODPATH/skip_mount"
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/action.sh" 0 0 0755
ui_print "SUSFS v1.5.5 control interface verified."
ui_print "Automatic KSU mount tagging is built into the kernel."
