#!/usr/bin/env bash
set -euo pipefail

build_dir="/tmp/mckernel-rocky-rust"
kmod_dir=""
smp_args=(ihk_ikc_irq_core=0)

usage() {
	cat <<'USAGE'
Usage: scripts/ihk-module-load-smoke.sh [--build-dir DIR] [--kmod-dir DIR] [--smp-arg ARG]

Loads and unloads C IHK host modules plus Rust-linked mcctrl in dependency order:
  ihk.ko, ihk-smp-x86_64.ko, mcctrl.ko

The script requires passwordless/cached sudo. It does not prompt for or store
sudo passwords.
USAGE
}

while [ "$#" -gt 0 ]; do
	case "$1" in
		--build-dir)
			build_dir="$2"
			shift 2
			;;
		--kmod-dir)
			kmod_dir="$2"
			shift 2
			;;
		--smp-arg)
			smp_args+=("$2")
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "error: unknown argument: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

find_module() {
	local name="$1"
	if [ -n "$kmod_dir" ] && [ -f "$kmod_dir/$name" ]; then
		printf '%s\n' "$kmod_dir/$name"
		return 0
	fi
	find "$build_dir" -type f -name "$name" -print -quit 2>/dev/null
}

require_file() {
	local path="$1"
	local label="$2"
	if [ -z "$path" ] || [ ! -f "$path" ]; then
		echo "error: missing $label under ${kmod_dir:-$build_dir}" >&2
		exit 1
	fi
}

module_loaded() {
	grep -q "^$1 " /proc/modules
}

cleanup() {
	local rc=$?
	sudo -n rmmod mcctrl 2>/dev/null || true
	sudo -n rmmod ihk_smp_x86_64 2>/dev/null || true
	sudo -n rmmod ihk 2>/dev/null || true
	exit "$rc"
}

sudo -n true

ihk_ko="$(find_module ihk.ko)"
smp_ko="$(find_module ihk-smp-x86_64.ko)"
mcctrl_ko="$(find_module mcctrl.ko)"

require_file "$ihk_ko" "ihk.ko"
require_file "$smp_ko" "ihk-smp-x86_64.ko"
require_file "$mcctrl_ko" "mcctrl.ko"

if module_loaded mcctrl || module_loaded ihk_smp_x86_64 || module_loaded ihk; then
	echo "error: IHK modules are already loaded; unload them before smoke." >&2
	lsmod | grep -E '^(ihk|ihk_smp_x86_64|mcctrl)\b' >&2 || true
	exit 1
fi

dmesg_lines_before="$(sudo -n dmesg | wc -l)"
trap cleanup EXIT

sudo -n insmod "$ihk_ko"
sudo -n insmod "$smp_ko" "${smp_args[@]}"
sudo -n insmod "$mcctrl_ko"

module_loaded ihk
module_loaded ihk_smp_x86_64
module_loaded mcctrl

dmesg_delta="$(sudo -n dmesg | tail -n +"$((dmesg_lines_before + 1))")"
suspicious_dmesg="$(
	printf '%s\n' "$dmesg_delta" |
		grep -Eiv "IHK-SMP: warning: allocating trampoline_page failed, using Linux'?" |
		grep -Ei 'Unknown symbol|unresolved symbol|BUG:|Oops|kernel NULL pointer|WARNING:|warning:' || true
)"
if [ -n "$suspicious_dmesg" ]; then
	echo "error: suspicious dmesg output after IHK module load:" >&2
	printf '%s\n' "$suspicious_dmesg" >&2
	exit 1
fi

sudo -n rmmod mcctrl
sudo -n rmmod ihk_smp_x86_64
sudo -n rmmod ihk
trap - EXIT

if module_loaded mcctrl || module_loaded ihk_smp_x86_64 || module_loaded ihk; then
	echo "error: IHK module unload left loaded modules behind." >&2
	lsmod | grep -E '^(ihk|ihk_smp_x86_64|mcctrl)\b' >&2 || true
	exit 1
fi

echo "ihk-module-load-smoke: OK"
