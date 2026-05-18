#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'USAGE'
Usage:
  scripts/rocky-v11-focused.sh [options]

Runs the focused Rocky Linux V11 regression slice that is runnable on a small
Rocky 8.x VM. External suites that need LTP, XPMEM, a larger VM, or missing
x86_64 tests are classified instead of silently using old hardcoded paths.

Options:
  --prefix PATH         Installed McKernel prefix. Default: /opt/mckernel-rust
  --boot-cpus LIST      CPU list passed to mcreboot.sh -c. Default: 1,2
  --boot-mem SPEC       Memory passed to mcreboot.sh -m. Default: 1536M@0
  --classify-only       Only report external prerequisite availability.
  --build-only          Classify prerequisites and build focused test binaries.
  --skip-boot           Assume McKernel is already booted.
  --skip-external       Do not run LTP/XPMEM even if available.
  --require-external    Fail if LTP or XPMEM prerequisites are missing.
  --require-ltp         Fail if LTP prerequisites are missing.
  --require-xpmem       Fail if XPMEM prerequisites are missing.
  --ltp-tests LIST      Space-separated LTP tests to run when available.
  --keep-running        Leave McKernel running after the focused slice.
  --timeout SEC         Per-test timeout. Default: 90
  --log-dir PATH        Directory for logs. Default: /tmp/mckernel-v11-focused-<timestamp>
  -h, --help            Show this help.
USAGE
}

PREFIX=/opt/mckernel-rust
BOOT_CPUS=1,2
BOOT_MEM=1536M@0
SKIP_BOOT=0
KEEP_RUNNING=0
CLASSIFY_ONLY=0
BUILD_ONLY=0
RUN_EXTERNAL=1
REQUIRE_LTP=0
REQUIRE_XPMEM=0
TEST_TIMEOUT=90
LOG_DIR="/tmp/mckernel-v11-focused-$(date +%Y%m%d-%H%M%S)"
LTP_TESTS="${LTP_TESTS:-futex_wait01 futex_wait02 futex_wait03 futex_wait04 futex_wait_bitset01 futex_wait_bitset02 futex_wake01 futex_wake02 futex_wake03 process_vm01 time01 fork01}"

while [ "$#" -gt 0 ]; do
	case "$1" in
		--prefix)
			PREFIX="${2:?missing value for --prefix}"
			shift 2
			;;
		--boot-cpus)
			BOOT_CPUS="${2:?missing value for --boot-cpus}"
			shift 2
			;;
		--boot-mem)
			BOOT_MEM="${2:?missing value for --boot-mem}"
			shift 2
			;;
		--classify-only)
			CLASSIFY_ONLY=1
			shift
			;;
		--build-only)
			BUILD_ONLY=1
			shift
			;;
		--skip-boot)
			SKIP_BOOT=1
			shift
			;;
		--skip-external)
			RUN_EXTERNAL=0
			shift
			;;
		--require-external)
			REQUIRE_LTP=1
			REQUIRE_XPMEM=1
			shift
			;;
		--require-ltp)
			REQUIRE_LTP=1
			shift
			;;
		--require-xpmem)
			REQUIRE_XPMEM=1
			shift
			;;
		--ltp-tests)
			LTP_TESTS="${2:?missing value for --ltp-tests}"
			shift 2
			;;
		--keep-running)
			KEEP_RUNNING=1
			shift
			;;
		--timeout)
			TEST_TIMEOUT="${2:?missing value for --timeout}"
			shift 2
			;;
		--log-dir)
			LOG_DIR="${2:?missing value for --log-dir}"
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "error: unknown option: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$PREFIX/bin"
SBIN="$PREFIX/sbin"
MCEXEC="$BIN/mcexec"
IHKOSCTL="$SBIN/ihkosctl"
MCREBOOT="$SBIN/mcreboot.sh"
MCSTOP="$SBIN/mcstop+release.sh"
shutdown_needed=0

say() {
	printf '\n==> %s\n' "$*"
}

need_exec() {
	if [ ! -x "$1" ]; then
		echo "error: required executable not found: $1" >&2
		exit 1
	fi
}

cleanup() {
	if [ "$shutdown_needed" -eq 1 ] && [ "$KEEP_RUNNING" -ne 1 ]; then
		sudo "$MCSTOP" -k || true
	fi
}
trap cleanup EXIT

run_logged() {
	local label="$1"
	shift
	local log="$LOG_DIR/${label}.log"

	say "$label"
	(
		cd "$ROOT_DIR"
		timeout "$TEST_TIMEOUT" "$@"
	) >"$log" 2>&1
	cat "$log"
}

run_in_dir_logged() {
	local label="$1"
	local dir="$2"
	shift 2
	local log="$LOG_DIR/${label}.log"

	say "$label"
	(
		cd "$ROOT_DIR/$dir"
		timeout "$TEST_TIMEOUT" "$@"
	) >"$log" 2>&1
	cat "$log"
}

ltp_bin_dir() {
	printf '%s\n' "${LTPBIN:-${LTP:-$HOME/ltp}/testcases/bin}"
}

ltp_root_dir() {
	local ltpbin
	ltpbin="$(ltp_bin_dir)"
	cd "$ltpbin/../.." 2>/dev/null && pwd || printf '%s\n' "${LTP:-$HOME/ltp}"
}

missing_ltp_tests() {
	local ltpbin="$1"
	local tp

	for tp in $LTP_TESTS; do
		if [ ! -x "$ltpbin/$tp" ]; then
			printf '%s\n' "$tp"
		fi
	done
}

ltp_ready() {
	local ltpbin
	ltpbin="$(ltp_bin_dir)"
	[ -d "$ltpbin" ] && [ -z "$(missing_ltp_tests "$ltpbin")" ]
}

xpmem_install_dir() {
	printf '%s\n' "${XPMEM_DIR:-$HOME/usr}"
}

xpmem_build_dir() {
	printf '%s\n' "${XPMEM_BUILD_DIR:-$HOME/xpmem}"
}

xpmem_library_found() {
	local xpmem_dir="$1"
	[ -f "$xpmem_dir/lib/libxpmem.so" ] || [ -f "$xpmem_dir/lib64/libxpmem.so" ]
}

xpmem_ready() {
	local xpmem_dir
	local xpmem_src_dir
	xpmem_dir="$(xpmem_install_dir)"
	xpmem_src_dir="$(xpmem_build_dir)"

	[ -f "$xpmem_dir/lib/modules/$(uname -r)/xpmem.ko" ] &&
		[ -f "$xpmem_dir/include/xpmem.h" ] &&
		xpmem_library_found "$xpmem_dir" &&
		[ -d "$xpmem_src_dir/test" ]
}

classify_prerequisites() {
	say "Classifying external V11 prerequisites"

	local ltpbin
	local missing_ltp
	ltpbin="$(ltp_bin_dir)"
	missing_ltp="$(missing_ltp_tests "$ltpbin")"
	if [ "$missing_ltp" != "" ]; then
		local tp
		for tp in $missing_ltp; do
			echo "SKIP: LTP missing $ltpbin/$tp"
		done
	else
		echo "READY: LTP prerequisites found in $ltpbin"
	fi

	local xpmem_dir
	local xpmem_src_dir
	xpmem_dir="$(xpmem_install_dir)"
	xpmem_src_dir="$(xpmem_build_dir)"
	if [ ! -f "$xpmem_dir/lib/modules/$(uname -r)/xpmem.ko" ]; then
		echo "SKIP: XPMEM module missing $xpmem_dir/lib/modules/$(uname -r)/xpmem.ko"
	fi
	if [ ! -f "$xpmem_dir/include/xpmem.h" ]; then
		echo "SKIP: XPMEM header missing $xpmem_dir/include/xpmem.h"
	fi
	if ! xpmem_library_found "$xpmem_dir"; then
		echo "SKIP: XPMEM library missing under $xpmem_dir/lib or $xpmem_dir/lib64"
	fi
	if [ ! -d "$xpmem_src_dir/test" ]; then
		echo "SKIP: XPMEM userspace tests missing $xpmem_src_dir/test"
	fi
	if xpmem_ready; then
		if [ -e /dev/xpmem ]; then
			echo "READY: XPMEM prerequisites found and /dev/xpmem is present"
		else
			echo "READY: XPMEM prerequisites found; /dev/xpmem will be created by insmod during the test"
		fi
	fi

	if [ ! -d "$ROOT_DIR/test/mcexec_options/x86_64" ]; then
		echo "SKIP: x86_64 mcexec_options suite is not present in this checkout"
	fi

	local mem_kb
	mem_kb="$(awk '/MemTotal:/ { print $2; exit }' /proc/meminfo)"
	if [ "${mem_kb:-0}" -lt $((28 * 1024 * 1024)) ]; then
		echo "SKIP: stock large_page runtime wants a much larger VM; MemTotal=${mem_kb}kB"
	fi
}

enforce_required_prerequisites() {
	if [ "$REQUIRE_LTP" -eq 1 ] && ! ltp_ready; then
		echo "error: --require-ltp was set but LTP prerequisites are missing." >&2
		exit 1
	fi
	if [ "$REQUIRE_XPMEM" -eq 1 ] && ! xpmem_ready; then
		echo "error: --require-xpmem was set but XPMEM prerequisites are missing." >&2
		exit 1
	fi
}

build_large_page_binaries() {
	local cfg_home="$LOG_DIR/large-page-home"
	local cfg="$cfg_home/.mck_test_config.mk"

	mkdir -p "$cfg_home"
	{
		printf 'MCK_DIR := %s\n' "$PREFIX"
		printf 'BIN := %s\n' "$BIN"
		printf 'SBIN := %s\n' "$SBIN"
		printf 'MCEXEC := %s\n' "$MCEXEC"
		printf 'TESTSET :=\n'
	} >"$cfg"

	make -C "$ROOT_DIR/test/large_page/x86_64" HOME="$cfg_home" all
}

build_test_binaries() {
	say "Building focused V11 test binaries"
	make -C "$ROOT_DIR/test/strace/issue" clean all
	make -C "$ROOT_DIR/test/issues/1176" all
	make -C "$ROOT_DIR/test/issues/1399" all
	make -C "$ROOT_DIR/test/issues/1036" all
	make -C "$ROOT_DIR/test/issues/1324" all
	make -C "$ROOT_DIR/test/portability" futex_wake_op MCEXEC="$MCEXEC"
	build_large_page_binaries

	if xpmem_ready; then
		make -C "$ROOT_DIR/test/xpmem" clean all XPMEM_DIR="$(xpmem_install_dir)"
	else
		echo "SKIP: not building XPMEM McKernel tests because XPMEM prerequisites are incomplete"
	fi
}

boot_mckernel() {
	if [ "$SKIP_BOOT" -eq 1 ]; then
		say "Using already booted McKernel"
		return
	fi

	if [ "$(nproc)" -lt 3 ]; then
		echo "error: focused V11 defaults need at least 3 vCPUs; CPU 0 stays with Linux and $BOOT_CPUS go to McKernel." >&2
		exit 1
	fi

	say "Booting McKernel for focused V11"
	sudo "$MCSTOP" -k
	sudo "$MCREBOOT" -c "$BOOT_CPUS" -m "$BOOT_MEM"
	shutdown_needed=1

	sudo "$IHKOSCTL" 0 kmsg >"$LOG_DIR/boot.kmsg"
	grep "IHK/McKernel booted" "$LOG_DIR/boot.kmsg"
}

run_strace_slice() {
	say "Running focused strace slice"
	local issue
	for issue in 943 944 945 946 960 961; do
		run_in_dir_logged "strace-issue-${issue}" "test/strace/issue" "$MCEXEC" "./$issue"
	done

	run_in_dir_logged "strace-test1" "test/strace/strace" env MCEXEC="$MCEXEC" ./test1.sh
	run_in_dir_logged "strace-test2" "test/strace/strace" env MCEXEC="$MCEXEC" ./test2.sh

	local bundle
	for bundle in ptrace_setoptions qual_syscall stat strace-f; do
		run_in_dir_logged "strace-bundle-${bundle}" "test/strace/strace-bundle" \
			env MCEXEC="$MCEXEC" srcdir=. "./$bundle"
	done
}

run_local_probes() {
	say "Running local Rocky V11 probes"
	run_in_dir_logged "issue-1176-C1176T03" "test/issues/1176" "$MCEXEC" ./C1176T03
	run_in_dir_logged "issue-1176-C1176T04" "test/issues/1176" "$MCEXEC" ./C1176T04
	run_in_dir_logged "futex-wake-op" "test/portability" "$MCEXEC" ./futex_wake_op
	run_in_dir_logged "issue-1399-C1399T01" "test/issues/1399" "$MCEXEC" ./C1399T01

	run_in_dir_logged "issue-1036-CT001" "test/issues/1036" "$MCEXEC" ./CT_001
	run_in_dir_logged "issue-1036-CT001-host-strace" "test/issues/1036" \
		strace -f -c -o "$LOG_DIR/issue-1036-CT001.strace" "$MCEXEC" ./CT_001
	if grep -E '[[:space:]]time$' "$LOG_DIR/issue-1036-CT001.strace" >/dev/null; then
		cat "$LOG_DIR/issue-1036-CT001.strace"
		echo "error: CT_001 delegated time syscall to Linux mcexec path" >&2
		exit 1
	fi
	cat "$LOG_DIR/issue-1036-CT001.strace"

	run_in_dir_logged "issue-1324-C1324T03" "test/issues/1324" "$MCEXEC" ./C1324T03
	run_in_dir_logged "issue-1324-C1324T02" "test/issues/1324" "$MCEXEC" ./C1324T02

	local t01_log="$LOG_DIR/issue-1324-C1324T01.log"
	say "issue-1324-C1324T01 capacity classification"
	if (
		cd "$ROOT_DIR/test/issues/1324"
		timeout "$TEST_TIMEOUT" "$MCEXEC" ./C1324T01
	) >"$t01_log" 2>&1; then
		cat "$t01_log"
		echo "C1324T01: PASS"
	elif grep -q "Cannot allocate memory" "$t01_log"; then
		cat "$t01_log"
		echo "C1324T01: SKIP on this VM, fork hit ENOMEM before ptrace"
	else
		cat "$t01_log"
		echo "error: C1324T01 failed for a reason other than classified VM memory capacity" >&2
		exit 1
	fi
}

run_ltp_slice() {
	if [ "$RUN_EXTERNAL" -ne 1 ]; then
		say "Skipping external LTP slice by request"
		return
	fi
	if ! ltp_ready; then
		say "Skipping external LTP slice; prerequisites are incomplete"
		return
	fi

	local ltpbin
	local ltproot
	local tp
	ltpbin="$(ltp_bin_dir)"
	ltproot="$(ltp_root_dir)"

	say "Running LTP-backed Rocky V11 slice"
	for tp in $LTP_TESTS; do
		local label="ltp-${tp}"
		local log="$LOG_DIR/${label}.log"
		if [ "${LTP_USE_SUDO:-1}" -eq 1 ]; then
			run_logged "$label" sudo env "LTPROOT=$ltproot" "PATH=$PATH:$ltpbin" "$MCEXEC" "$ltpbin/$tp"
		else
			run_logged "$label" env "LTPROOT=$ltproot" "PATH=$PATH:$ltpbin" "$MCEXEC" "$ltpbin/$tp"
		fi
		if grep -E '(^|[[:space:]])T(FAIL|BROK)([[:space:]]|:)' "$log" >/dev/null; then
			echo "error: LTP reported failure markers in $log" >&2
			exit 1
		fi
	done
}

run_xpmem_slice() {
	if [ "$RUN_EXTERNAL" -ne 1 ]; then
		say "Skipping external XPMEM slice by request"
		return
	fi
	if ! xpmem_ready; then
		say "Skipping external XPMEM slice; prerequisites are incomplete"
		return
	fi

	say "Running XPMEM Rocky V11 slice"
	run_in_dir_logged "xpmem-basic" "test/xpmem" \
		env MCSTOP=0 MCREBOOT=0 MCK_DIR="$PREFIX" \
		XPMEM_DIR="$(xpmem_install_dir)" XPMEM_BUILD_DIR="$(xpmem_build_dir)" \
		./go_test.sh
}

mkdir -p "$LOG_DIR"
need_exec "$MCEXEC"
need_exec "$IHKOSCTL"
need_exec "$MCREBOOT"
need_exec "$MCSTOP"
command -v timeout >/dev/null 2>&1 || { echo "error: timeout is required" >&2; exit 1; }
command -v strace >/dev/null 2>&1 || { echo "error: strace is required" >&2; exit 1; }

echo "Rocky focused V11 log directory: $LOG_DIR"
classify_prerequisites | tee "$LOG_DIR/prerequisites.log"
enforce_required_prerequisites
if [ "$CLASSIFY_ONLY" -eq 1 ]; then
	say "Prerequisite classification complete"
	echo "Logs: $LOG_DIR"
	exit 0
fi
build_test_binaries | tee "$LOG_DIR/build.log"
if [ "$BUILD_ONLY" -eq 1 ]; then
	say "Focused V11 test binary build complete"
	echo "Logs: $LOG_DIR"
	exit 0
fi
boot_mckernel
run_strace_slice
run_local_probes
run_ltp_slice
run_xpmem_slice

say "Focused Rocky V11 slice passed"
echo "Logs: $LOG_DIR"
