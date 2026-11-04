#!/system/bin/sh
MODDIR=${0%/*}
echo "Cronos SUSFS kernel interface:"
"$MODDIR/ksu_susfs" show version
"$MODDIR/ksu_susfs" show variant
"$MODDIR/ksu_susfs" show enabled_features
