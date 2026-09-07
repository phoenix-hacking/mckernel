#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# PID 1 only inside the disposable four-vCPU native test guest.
set -euo pipefail
[ "$$" -eq 1 ] && [ "$EUID" -eq 0 ] || exit 125
export PATH=/bin:/sbin:/usr/bin:/usr/sbin LANG=C LC_ALL=C
exec </dev/console >/dev/console 2>&1
finish() {
    local status=$?
    trap - EXIT
    if [ "$status" -ne 0 ]; then
        printf 'NATIVE_CPU_GUEST FAIL status=%s\n' "$status"
    fi
    /bin/dmesg || true
    /poweroff
}
trap finish EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
read -r present </sys/devices/system/cpu/present
read -r online </sys/devices/system/cpu/online
[ "$present" = 0-3 ] && [ "$online" = 0-3 ]
printf 'NATIVE_CPU_GUEST BEGIN cpus=4 kernel=%s\n' "$(uname -r)"
if [ -f /expected-numa-nodes ]; then
    read -r expected_nodes </expected-numa-nodes
    read -r nodes </sys/devices/system/node/online
    read -r node0_cpus </sys/devices/system/node/node0/cpulist
    read -r node1_cpus </sys/devices/system/node/node1/cpulist
    [ "$expected_nodes" = 0-1 ] && [ "$nodes" = "$expected_nodes" ]
    [ "$node0_cpus" = 0-1 ] && [ "$node1_cpus" = 2-3 ]
    printf 'NATIVE_CPU_GUEST NUMA nodes=0-1 cpu-map=0-1/2-3 PASS\n'
fi
for cycle in 1 2; do
    insmod /modules/ihk.ko
    insmod /modules/ihk-smp-x86_64.ko
    insmod /modules/mcctrl.ko
    /bin/native-cpu-x86_64
    /bin/native-cpu-i386
    read -r online </sys/devices/system/cpu/online
    [ "$online" = 0-3 ]
    rmmod mcctrl
    rmmod ihk_smp_x86_64
    rmmod ihk
    [ ! -e /dev/mcd0 ]
    [ ! -e /sys/module/ihk_smp_x86_64 ]
    [ ! -e /sys/module/ihk ]
    [ ! -e /sys/module/mcctrl ]
    printf 'NATIVE_CPU_GUEST CYCLE=%s restored=0-3 unloaded=all PASS\n' "$cycle"
done
printf 'NATIVE_CPU_GUEST COMPLETE PASS\n'
