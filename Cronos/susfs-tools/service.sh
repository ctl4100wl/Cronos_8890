#!/system/bin/sh
MODDIR=${0%/*}
# Keep boot output quiet. This does not disable hiding or change KSU hooks.
"$MODDIR/ksu_susfs" enable_log 0
