#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# PID 1 only in the bounded native boot verification VM.
set -euo pipefail
[ "$$" -eq 1 ] && [ "$EUID" -eq 0 ] || exit 125
export PATH=/bin:/sbin:/usr/bin:/usr/sbin LANG=C LC_ALL=C
exec </dev/console >/dev/console 2>&1
finish() {
    local status=$?
    trap - EXIT
    if [ "$status" -ne 0 ]; then printf 'NATIVE_BOOT_GUEST FAIL status=%s\n' "$status"; fi
    /bin/dmesg || true
    /poweroff
}
trap finish EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t debugfs debugfs /sys/kernel/debug
printf '7\n' >/proc/sys/kernel/printk
read -r online </sys/devices/system/cpu/online
read -r nodes </sys/devices/system/node/online
[ "$online" = 0-3 ] && [ "$nodes" = 0-1 ]
read -r mode </boot-mode
if [ "$mode" = prepare ]; then
    for cycle in 1 2; do
        insmod /modules/ihk.ko
        insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288 native_boot_prepare_only=1
        insmod /modules/mcctrl.ko
        /bin/native-boot-x86_64
        /bin/native-boot-i386
        rmmod mcctrl
        rmmod ihk_smp_x86_64
        rmmod ihk
        read -r online </sys/devices/system/cpu/online
        [ "$online" = 0-3 ]
        printf 'NATIVE_BOOT_GUEST PREPARATION cycle=%s restored=1 unloaded=all\n' "$cycle"
    done
    printf 'NATIVE_BOOT_GUEST PREPARATION PASS\n'
else
    insmod /modules/ihk.ko
    insmod /modules/ihk-smp-x86_64.ko ihk_trampoline=524288
    insmod /modules/mcctrl.ko
    if [ "$mode" = start-i386 ]; then /bin/native-boot-i386; else /bin/native-boot-x86_64; fi
    printf 'NATIVE_BOOT_GUEST START_CAPTURE incomplete=1 restoration_proven=0\n'
fi
