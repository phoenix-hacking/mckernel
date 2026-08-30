#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Initramfs PID 1 for credit-forbidden native Rust host-module evidence.

set -uo pipefail

readonly PROTOCOL=MCKERNEL_NATIVE_RUST_RUNTIME_V1
readonly EXPECTED_KERNEL_RELEASE=@EXPECTED_KERNEL_RELEASE@
readonly IHK=/modules/ihk.ko
readonly SMP=/modules/ihk-smp-x86_64.ko
readonly MCCTRL=/modules/mcctrl.ko
readonly MCD0_IOCTL_NATIVE=/bin/mcd0-ioctl-x86_64
readonly MCD0_IOCTL_COMPAT=/bin/mcd0-ioctl-i386

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export LANG=C
export LC_ALL=C
exec </dev/console >/dev/console 2>&1

runtime_status=incomplete
runtime_reason=unexpected-exit
dmesg_emitted=0

record() {
	printf '%s %s\n' "$PROTOCOL" "$*"
}

loaded() {
	local wanted="$1"
	local name rest

	while read -r name rest; do
		if [ "$name" = "$wanted" ]; then
			return 0
		fi
	done </proc/modules
	return 1
}

ihk_refcount() {
	local name size references users state address rest

	while read -r name size references users state address rest; do
		if [ "$name" = ihk ]; then
			printf '%s\n' "$references"
			return 0
		fi
	done </proc/modules
	return 1
}

ihk_users() {
	local name size references users state address rest

	while read -r name size references users state address rest; do
		if [ "$name" = ihk ]; then
			printf '%s\n' "$users"
			return 0
		fi
	done </proc/modules
	return 1
}

concurrent_mcd0_opens() {
	local worker pid index
	local -a pids

	pids=()
	: > /tmp/mcd0-release-pending
	for worker in 1 2 3 4 5 6 7 8; do
		(
			exec 7<>/dev/mcd0 || exit 10
			: > "/tmp/mcd0-open-$worker"
			while [ ! -e /tmp/mcd0-release ]; do :; done
			exec 7>&-
		) &
		pids+=("$!")
	done
	for index in "${!pids[@]}"; do
		worker=$((index + 1))
		pid="${pids[$index]}"
		while [ ! -e "/tmp/mcd0-open-$worker" ]; do
			kill -0 "$pid" 2>/dev/null || return 1
		done
	done
	: > /tmp/mcd0-release
	for pid in "${pids[@]}"; do
		wait "$pid" || return 1
	done
}

valid_mcd0_dev_identity() {
	local identity="$1"
	local minor

	case "$identity" in
	10:*) minor="${identity#10:}" ;;
	*) return 1 ;;
	esac
	case "$minor" in
	0) return 0 ;;
	[1-9]*)
		case "$minor" in
		*[!0-9]*) return 1 ;;
		*) ;;
		esac
		[ "${#minor}" -le 7 ] || return 1
		[ "$minor" -le 1048575 ] || return 1
		return 0
		;;
	*) return 1 ;;
	esac
}

mcd0_node_matches_identity() {
	local identity="$1"
	local minor expected actual

	valid_mcd0_dev_identity "$identity" || return 1
	minor="${identity#10:}"
	expected="$(printf 'a:%x' "$minor")" || return 1
	[ -c /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || return 1
	# GNU stat does not dereference symlinks by default.  Keep that property so
	# a path swap after the explicit ! -L check cannot be accepted as the
	# target character device's st_rdev.
	actual="$(/bin/stat -c '%t:%T' /dev/mcd0)" || return 1
	[ "$actual" = "$expected" ]
}

emit_state() {
	local label="$1"
	local name rest

	record "STATE_BEGIN label=$label"
	while read -r name rest; do
		case "$name" in
		ihk|ihk_smp_x86_64|mcctrl)
			record "MODULE $name $rest"
			;;
		esac
	done </proc/modules
	record "STATE_END label=$label"
}

emit_dmesg() {
	if [ "$dmesg_emitted" -eq 1 ]; then
		return
	fi
	dmesg_emitted=1
	record DMESG_BEGIN
	dmesg || true
	record DMESG_END
}

finish() {
	local exit_status=$?

	trap - EXIT
	emit_dmesg
	if [ "$runtime_status" = complete-unreviewed ] && [ "$exit_status" -eq 0 ]; then
		record "COMPLETE status=technical-capture-unreviewed credit=forbidden"
	else
		record "INCOMPLETE reason=$runtime_reason exit_status=$exit_status credit=forbidden"
	fi
	# Best-effort cleanup remains inside the disposable guest.
	rmmod mcctrl >/dev/null 2>&1 || true
	rmmod ihk_smp_x86_64 >/dev/null 2>&1 || true
	rmmod ihk >/dev/null 2>&1 || true
	/poweroff
	while :; do :; done
}
trap finish EXIT

fail() {
	runtime_reason="$1"
	return 1
}

mount -n -t proc proc /proc || { fail mount-proc; exit 1; }
mount -n -t sysfs sysfs /sys || { fail mount-sysfs; exit 1; }
mount -n -t devtmpfs devtmpfs /dev || { fail mount-devtmpfs; exit 1; }

record BEGIN
actual_release="$(uname -r)" || { fail uname; exit 1; }
record "KERNEL_RELEASE actual=$actual_release expected=$EXPECTED_KERNEL_RELEASE"
[ "$actual_release" = "$EXPECTED_KERNEL_RELEASE" ] || {
	fail wrong-kernel-release
	exit 1
}

if loaded ihk || loaded ihk_smp_x86_64 || loaded mcctrl; then
	fail dirty-initial-module-state
	exit 1
fi
emit_state initial-clean

insmod "$IHK" || { fail load-ihk; exit 1; }
record "LOAD module=ihk status=ok"
loaded ihk || { fail ihk-not-loaded; exit 1; }

insmod "$SMP" || { fail load-ihk-smp-x86-64; exit 1; }
record "LOAD module=ihk_smp_x86_64 status=ok"
loaded ihk_smp_x86_64 || { fail ihk-smp-not-loaded; exit 1; }

insmod "$MCCTRL" || { fail load-mcctrl; exit 1; }
record "LOAD module=mcctrl status=ok"
loaded mcctrl || { fail mcctrl-not-loaded; exit 1; }
emit_state all-loaded

references="$(ihk_refcount)" || { fail missing-ihk-refcount; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users; exit 1; }
record "REFCOUNT module=ihk phase=all-loaded references=$references users=$users"
[ "$references" = 2 ] || { fail wrong-provider-refcount; exit 1; }
case "$users" in
mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;
*) fail wrong-provider-users; exit 1 ;;
esac

[ -c /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {
	fail missing-or-linked-mcd0-device-node
	exit 1
}
[ -e /sys/class/misc/mcd0/dev ] || { fail missing-mcd0-sysfs-node; exit 1; }
IFS= read -r mcd0_dev </sys/class/misc/mcd0/dev || {
	fail unreadable-mcd0-dev-identity
	exit 1
}
valid_mcd0_dev_identity "$mcd0_dev" || {
	fail invalid-mcd0-dev-identity
	exit 1
}
mcd0_node_matches_identity "$mcd0_dev" || {
	fail mcd0-node-sysfs-identity-mismatch
	exit 1
}
record "MCD0 NODE status=present dev=$mcd0_dev"

for cycle in 1 2 3 4; do
	exec 8<>/dev/mcd0 || { fail mcd0-sequential-open; exit 1; }
	exec 8>&-
done
record "MCD0 OPEN_CLOSE mode=sequential count=4 status=ok"

concurrent_mcd0_opens || { fail mcd0-concurrent-open; exit 1; }
record "MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok"

"$MCD0_IOCTL_NATIVE" || { fail mcd0-native-negative-ioctl; exit 1; }
record "MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok"
"$MCD0_IOCTL_COMPAT" || { fail mcd0-compat-negative-ioctl; exit 1; }
record "MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok"

exec 9<>/dev/mcd0 || { fail mcd0-held-open; exit 1; }
set +e
mcd0_negative_output="$(rmmod ihk_smp_x86_64 2>&1)"
mcd0_negative_status=$?
set -e
record "MCD0 NEGATIVE operation=unload-smp-with-open-file status=$mcd0_negative_status"
record "MCD0 NEGATIVE_OUTPUT_BEGIN"
printf '%s\n' "$mcd0_negative_output"
record "MCD0 NEGATIVE_OUTPUT_END"
[ "$mcd0_negative_status" -eq 1 ] || {
	fail mcd0-module-owner-negative-status
	exit 1
}
case "$mcd0_negative_output" in
*"Module ihk_smp_x86_64 is in use"*) ;;
*) fail mcd0-module-owner-negative-diagnostic; exit 1 ;;
esac
loaded ihk_smp_x86_64 || { fail mcd0-negative-unloaded-smp; exit 1; }
[ -c /dev/mcd0 ] || { fail mcd0-negative-removed-node; exit 1; }
exec 9>&-
record "MCD0 CLOSE phase=after-module-owner-negative status=ok"

set +e
negative_output="$(rmmod ihk 2>&1)"
negative_status=$?
set -e
record "NEGATIVE operation=unload-provider-first status=$negative_status"
record "NEGATIVE_OUTPUT_BEGIN"
printf '%s\n' "$negative_output"
record "NEGATIVE_OUTPUT_END"
[ "$negative_status" -eq 1 ] || { fail provider-unload-negative-status; exit 1; }
case "$negative_output" in
*"Module ihk is in use"*) ;;
*) fail provider-unload-negative-diagnostic; exit 1 ;;
esac
loaded ihk && loaded ihk_smp_x86_64 && loaded mcctrl || {
	fail negative-test-changed-module-state
	exit 1
}
references="$(ihk_refcount)" || { fail missing-ihk-refcount-after-negative; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-negative; exit 1; }
record "REFCOUNT module=ihk phase=after-negative references=$references users=$users"
[ "$references" = 2 ] || { fail negative-test-changed-refcount; exit 1; }
case "$users" in
mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;
*) fail negative-test-changed-users; exit 1 ;;
esac
emit_state after-negative

rmmod mcctrl || { fail unload-mcctrl; exit 1; }
record "UNLOAD module=mcctrl status=ok"
references="$(ihk_refcount)" || { fail missing-ihk-after-mcctrl; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-mcctrl; exit 1; }
record "REFCOUNT module=ihk phase=after-mcctrl-unload references=$references users=$users"
[ "$references" = 1 ] || { fail wrong-refcount-after-mcctrl; exit 1; }
[ "$users" = 'ihk_smp_x86_64,' ] || { fail wrong-users-after-mcctrl; exit 1; }

rmmod ihk_smp_x86_64 || { fail unload-ihk-smp-x86-64; exit 1; }
record "UNLOAD module=ihk_smp_x86_64 status=ok"
[ ! -e /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {
	fail mcd0-node-remains-after-smp-unload
	exit 1
}
[ ! -e /sys/class/misc/mcd0 ] && [ ! -L /sys/class/misc/mcd0 ] || {
	fail mcd0-sysfs-remains-after-smp-unload
	exit 1
}
record "MCD0 NODE status=removed"
references="$(ihk_refcount)" || { fail missing-ihk-after-smp; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-smp; exit 1; }
record "REFCOUNT module=ihk phase=after-smp-unload references=$references users=$users"
[ "$references" = 0 ] || { fail wrong-refcount-after-smp; exit 1; }
[ "$users" = - ] || { fail wrong-users-after-smp; exit 1; }

rmmod ihk || { fail unload-ihk; exit 1; }
record "UNLOAD module=ihk status=ok"
if loaded ihk || loaded ihk_smp_x86_64 || loaded mcctrl; then
	fail dirty-first-cycle-module-state
	exit 1
fi
emit_state first-cycle-clean

record "RELOAD cycle=1 phase=begin"
insmod "$IHK" || { fail reload-ihk; exit 1; }
record "RELOAD_LOAD cycle=1 module=ihk status=ok"
insmod "$SMP" || { fail reload-ihk-smp-x86-64; exit 1; }
record "RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok"
insmod "$MCCTRL" || { fail reload-mcctrl; exit 1; }
record "RELOAD_LOAD cycle=1 module=mcctrl status=ok"
loaded ihk && loaded ihk_smp_x86_64 && loaded mcctrl || {
	fail reload-incomplete-module-state
	exit 1
}
references="$(ihk_refcount)" || { fail missing-ihk-refcount-after-reload; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-reload; exit 1; }
record "REFCOUNT module=ihk phase=reload-all-loaded references=$references users=$users"
[ "$references" = 2 ] || { fail wrong-provider-refcount-after-reload; exit 1; }
case "$users" in
mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;
*) fail wrong-provider-users-after-reload; exit 1 ;;
esac
[ -c /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {
	fail missing-or-linked-mcd0-node-after-reload
	exit 1
}
[ -e /sys/class/misc/mcd0/dev ] || { fail missing-mcd0-sysfs-after-reload; exit 1; }
IFS= read -r mcd0_reload_dev </sys/class/misc/mcd0/dev || {
	fail unreadable-mcd0-dev-after-reload
	exit 1
}
valid_mcd0_dev_identity "$mcd0_reload_dev" || {
	fail invalid-mcd0-dev-after-reload
	exit 1
}
mcd0_node_matches_identity "$mcd0_reload_dev" || {
	fail mcd0-node-sysfs-mismatch-after-reload
	exit 1
}
exec 8<>/dev/mcd0 || { fail mcd0-open-after-reload; exit 1; }
exec 8>&-
"$MCD0_IOCTL_NATIVE" || { fail mcd0-native-ioctl-after-reload; exit 1; }
"$MCD0_IOCTL_COMPAT" || { fail mcd0-compat-ioctl-after-reload; exit 1; }
record "MCD0 RELOAD cycle=1 dev=$mcd0_reload_dev open_close=1 ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok"
rmmod mcctrl || { fail unload-reloaded-mcctrl; exit 1; }
record "RELOAD_UNLOAD cycle=1 module=mcctrl status=ok"
rmmod ihk_smp_x86_64 || { fail unload-reloaded-ihk-smp-x86-64; exit 1; }
record "RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok"
[ ! -e /dev/mcd0 ] && [ ! -L /dev/mcd0 ] || {
	fail mcd0-node-remains-after-reload
	exit 1
}
[ ! -e /sys/class/misc/mcd0 ] && [ ! -L /sys/class/misc/mcd0 ] || {
	fail mcd0-sysfs-remains-after-reload
	exit 1
}
rmmod ihk || { fail unload-reloaded-ihk; exit 1; }
record "RELOAD_UNLOAD cycle=1 module=ihk status=ok"
if loaded ihk || loaded ihk_smp_x86_64 || loaded mcctrl; then
	fail dirty-final-module-state
	exit 1
fi
record "RELOAD cycle=1 status=ok"
emit_state final-clean

runtime_status=complete-unreviewed
runtime_reason=none
exit 0
