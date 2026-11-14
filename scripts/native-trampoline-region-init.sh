#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Disposable guest only: no CPU executes the tested memory page.
set -eu
[ "$$" -eq 1 ] && [ "$EUID" -eq 0 ] || exit 125
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export LANG=C LC_ALL=C
exec </dev/console >/dev/console 2>&1
status=FAIL
finish() {
    printf 'MCKERNEL_TRAMPOLINE_REGION_GUEST %s\n' "$status"
    /bin/dmesg || true
    /poweroff
}
trap finish EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
[ "$(uname -r)" = '6.12.0-211.44.1.el10_2.mckernel1.x86_64' ]
read -r online </sys/devices/system/cpu/online
read -r nodes </sys/devices/system/node/online
[ "$online" = 0-3 ] && [ "$nodes" = 0-1 ]
for cycle in 1 2; do
    /sbin/insmod /modules/mckernel_trampoline_region_verify.ko
    /sbin/rmmod mckernel_trampoline_region_verify
    printf 'MCKERNEL_TRAMPOLINE_REGION_GUEST cycle=%s complete\n' "$cycle"
done
status=PASS
