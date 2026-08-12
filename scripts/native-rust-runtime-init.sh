#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Initramfs PID 1 for credit-forbidden native Rust host-module evidence.

set -uo pipefail

readonly PROTOCOL=MCKERNEL_NATIVE_RUST_RUNTIME_V1
readonly EXPECTED_KERNEL_RELEASE=@EXPECTED_KERNEL_RELEASE@
readonly IHK=/modules/ihk.ko
readonly SMP=/modules/ihk-smp-x86_64.ko
readonly MCCTRL=/modules/mcctrl.ko

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
case ",$users," in
*,ihk_smp_x86_64,*) ;;
*) fail missing-smp-provider-user; exit 1 ;;
esac
case ",$users," in
*,mcctrl,*) ;;
*) fail missing-mcctrl-provider-user; exit 1 ;;
esac

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
case ",$users," in
*,ihk_smp_x86_64,*) ;;
*) fail negative-test-lost-smp-user; exit 1 ;;
esac
case ",$users," in
*,mcctrl,*) ;;
*) fail negative-test-lost-mcctrl-user; exit 1 ;;
esac
emit_state after-negative

rmmod mcctrl || { fail unload-mcctrl; exit 1; }
record "UNLOAD module=mcctrl status=ok"
references="$(ihk_refcount)" || { fail missing-ihk-after-mcctrl; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-mcctrl; exit 1; }
record "REFCOUNT module=ihk phase=after-mcctrl-unload references=$references users=$users"
[ "$references" = 1 ] || { fail wrong-refcount-after-mcctrl; exit 1; }
[ "$users" = ihk_smp_x86_64 ] || { fail wrong-users-after-mcctrl; exit 1; }

rmmod ihk_smp_x86_64 || { fail unload-ihk-smp-x86-64; exit 1; }
record "UNLOAD module=ihk_smp_x86_64 status=ok"
references="$(ihk_refcount)" || { fail missing-ihk-after-smp; exit 1; }
users="$(ihk_users)" || { fail missing-ihk-users-after-smp; exit 1; }
record "REFCOUNT module=ihk phase=after-smp-unload references=$references users=$users"
[ "$references" = 0 ] || { fail wrong-refcount-after-smp; exit 1; }
[ "$users" = - ] || { fail wrong-users-after-smp; exit 1; }

rmmod ihk || { fail unload-ihk; exit 1; }
record "UNLOAD module=ihk status=ok"
if loaded ihk || loaded ihk_smp_x86_64 || loaded mcctrl; then
	fail dirty-final-module-state
	exit 1
fi
emit_state final-clean

runtime_status=complete-unreviewed
runtime_reason=none
exit 0
