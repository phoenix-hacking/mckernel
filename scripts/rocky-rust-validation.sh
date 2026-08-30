#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'USAGE'
Usage:
  scripts/rocky-rust-validation.sh [options]

Default action:
  Install Rocky/RHEL-family build dependencies for the running kernel, ensure
  Rust nightly, initialize submodules, build the Rust-enabled x86_64 McKernel
  targets, and install them under /opt/mckernel-rust.

Options:
  --build-only          Configure/build only; skip install.
  --skip-deps           Do not install OS packages.
  --skip-rust           Do not install or switch Rust nightly.
  --skip-ihk-patch      Do not apply the local IHK compatibility patch.
  --module-load-smoke   After build, load/unload the C IHK host modules and
                        Rust-linked mcctrl module.
  --skip-source-retirement-audit
                        Skip the active rust-source-retirement.txt coverage gate.
  --source-retirement-final
                        Enforce final C/header retirement gates after build.
  --boot-only           After install, boot McKernel and check kmsg; skip workloads.
                        Requires --unsafe-host-boot on the current host.
  --boot-smoke          After install, boot McKernel and run mcexec smoke tests.
                        Requires --unsafe-host-boot on the current host.
  --unsafe-host-boot    Allow boot validation on the current host. Prefer
                        scripts/qemu-rocky-rust-validation.sh for recoverable
                        early-boot validation.
  --yes                 Allow boot validation without an interactive confirmation.
  --prefix PATH         Install prefix. Default: /opt/mckernel-rust
  --build-dir PATH      CMake build directory. Default: /tmp/mckernel-rocky-rust
  --jobs N              Parallel build jobs. Default: 2
  --boot-cpus LIST      CPU list passed to mcreboot.sh -c. Default: 1
  --boot-mem SPEC       Memory passed to mcreboot.sh -m. Default: 512M@0
  --trampoline-phys PA  Expert-only: pass pre-reserved PA to mcreboot.sh.
  --boot-timeout SEC    Wait for RUNNING state and Rust boot markers. Default: 60
  --smoke-timeout SEC   Watchdog for each V10 smoke command. Default: 8
  --trace-smoke         Run V10 smoke commands under strace when available.
  --debug-mcexec-smoke  Add --debug-mcexec to mcexec smoke commands.
  --verbose-smoke       Print full smoke logs without changing tested commands.
  --fp0006-negative-dispatch-capture
                        Capture the two noncrediting FP-0006 negative device
                        vectors while /dev/mcd0 is live. Hosted disposable
                        QEMU only; requires the four identity options below.
  --fp0006-capture-head SHA
  --fp0006-capture-repository OWNER/REPO
  --fp0006-capture-run-id ID
  --fp0006-capture-run-attempt N
  --fp0006-capture-event-name NAME
  --fp0006-capture-ref REF
  --fp0006-capture-github-sha SHA
  --fp0006-capture-workflow-sha SHA
  --fp0006-capture-base-sha SHA
                        Bind the temporary capture to one GitHub run observation.
  -h, --help            Show this help.

Environment overrides:
  KERNEL_DIR            Host kernel build tree. Defaults to the running
                        kernel's /lib/modules/.../build directory.
  RUST_TOOLCHAIN        rustup name for the pinned compiler. Default:
                        nightly-2026-02-19 (rustc c04308580).

Examples:
  scripts/rocky-rust-validation.sh
  scripts/rocky-rust-validation.sh --build-only
  scripts/rocky-rust-validation.sh --boot-only --yes
  scripts/rocky-rust-validation.sh --boot-smoke --yes
USAGE
}

PREFIX=/opt/mckernel-rust
BUILD_DIR=/tmp/mckernel-rocky-rust
JOBS=2
BOOT_CPUS=1
BOOT_MEM=512M@0
TRAMPOLINE_PHYS="${IHK_TRAMPOLINE_PHYS:-}"
SMOKE_TIMEOUT=8
BOOT_TIMEOUT=60
TIMEOUT_KILL_AFTER=5s
TRACE_SMOKE=0
DEBUG_MCEXEC=0
VERBOSE_SMOKE=0
FP0006_NEGATIVE_CAPTURE=0
FP0006_CAPTURE_HEAD=
FP0006_CAPTURE_REPOSITORY=
FP0006_CAPTURE_RUN_ID=
FP0006_CAPTURE_RUN_ATTEMPT=
FP0006_CAPTURE_EVENT_NAME=
FP0006_CAPTURE_REF=
FP0006_CAPTURE_GITHUB_SHA=
FP0006_CAPTURE_WORKFLOW_SHA=
FP0006_CAPTURE_BASE_SHA=
FP0006_PREFLIGHT_DIR=
FP0006_PREFLIGHT_MANIFEST=
FP0006_PREFLIGHT_MANIFEST_SHA256=
FP0006_PRODUCER_BINARY=
FP0006_PRODUCER_BINARY_SHA256=
FP0006_COMPILER_REPORT_SHA256=
RUST_TOOLCHAIN="${RUST_TOOLCHAIN:-nightly-2026-02-19}"
EXPECTED_RUSTC_VERSION='rustc 1.95.0-nightly (c04308580 2026-02-18)'
SMOKE_LOG_TAIL_LINES="${SMOKE_LOG_TAIL_LINES:-80}"
STRACE_TAIL_LINES="${STRACE_TAIL_LINES:-40}"
DMESG_TAIL_LINES="${DMESG_TAIL_LINES:-40}"
KMSG_TAIL_LINES="${KMSG_TAIL_LINES:-40}"
V10_TAIL_LINES="${V10_TAIL_LINES:-30}"
INSTALL_DEPS=1
INSTALL_RUST=1
APPLY_IHK_PATCH=1
DO_INSTALL=1
BOOT_ONLY=0
BOOT_SMOKE=0
MODULE_LOAD_SMOKE=0
SOURCE_RETIREMENT_AUDIT=1
SOURCE_RETIREMENT_FINAL=0
ASSUME_YES=0
UNSAFE_HOST_BOOT=0
BOOT_SHUTDOWN_NEEDED=0
BOOT_RESTORE_SELINUX=0
BOOT_RESTORE_ENVIRONMENT=0
BOOT_INITIAL_SELINUX_MODE=unavailable
BOOT_INITIAL_CPU_ONLINE=unavailable
BOOT_INITIAL_SWAPPINESS=unavailable
BOOT_INITIAL_IRQBALANCE=unavailable
BOOT_DMESG_BASELINE_LINES=0
BOOT_EVIDENCE_DIR=
BOOT_DMESG_BEFORE=
BOOT_DMESG_AFTER=
BOOT_DMESG_DELTA=
BOOT_KMSG=
BOOT_BEFORE_WORKLOAD_KMSG=
BOOT_AFTER_WORKLOAD_KMSG=
BOOT_WORKLOAD_KMSG_DELTA=
BOOT_FINAL_KMSG=
BOOT_IRQ_AFFINITY_BEFORE=
RUNTIME_EVIDENCE_DIR="${MCKERNEL_RUNTIME_EVIDENCE_DIR:-}"

while [ "$#" -gt 0 ]; do
	case "$1" in
		--build-only)
			DO_INSTALL=0
			shift
			;;
		--skip-deps)
			INSTALL_DEPS=0
			shift
			;;
		--skip-rust)
			INSTALL_RUST=0
			shift
			;;
		--skip-ihk-patch)
			APPLY_IHK_PATCH=0
			shift
			;;
		--module-load-smoke)
			MODULE_LOAD_SMOKE=1
			shift
			;;
		--skip-source-retirement-audit)
			SOURCE_RETIREMENT_AUDIT=0
			shift
			;;
		--source-retirement-final)
			SOURCE_RETIREMENT_AUDIT=1
			SOURCE_RETIREMENT_FINAL=1
			shift
			;;
		--boot-only)
			BOOT_ONLY=1
			BOOT_SMOKE=1
			shift
			;;
		--boot-smoke)
			BOOT_SMOKE=1
			shift
			;;
		--unsafe-host-boot)
			UNSAFE_HOST_BOOT=1
			shift
			;;
		--yes)
			ASSUME_YES=1
			shift
			;;
		--prefix)
			PREFIX="${2:?missing value for --prefix}"
			shift 2
			;;
		--build-dir)
			BUILD_DIR="${2:?missing value for --build-dir}"
			shift 2
			;;
		--jobs)
			JOBS="${2:?missing value for --jobs}"
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
		--trampoline-phys)
			TRAMPOLINE_PHYS="${2:?missing value for --trampoline-phys}"
			shift 2
			;;
		--boot-timeout)
			BOOT_TIMEOUT="${2:?missing value for --boot-timeout}"
			shift 2
			;;
		--smoke-timeout)
			SMOKE_TIMEOUT="${2:?missing value for --smoke-timeout}"
			shift 2
			;;
		--trace-smoke)
			TRACE_SMOKE=1
			shift
			;;
		--debug-mcexec-smoke)
			DEBUG_MCEXEC=1
			shift
			;;
		--verbose-smoke)
			VERBOSE_SMOKE=1
			shift
			;;
		--fp0006-negative-dispatch-capture)
			FP0006_NEGATIVE_CAPTURE=1
			shift
			;;
		--fp0006-capture-head)
			FP0006_CAPTURE_HEAD="${2:?missing value for --fp0006-capture-head}"
			shift 2
			;;
		--fp0006-capture-repository)
			FP0006_CAPTURE_REPOSITORY="${2:?missing value for --fp0006-capture-repository}"
			shift 2
			;;
		--fp0006-capture-run-id)
			FP0006_CAPTURE_RUN_ID="${2:?missing value for --fp0006-capture-run-id}"
			shift 2
			;;
		--fp0006-capture-run-attempt)
			FP0006_CAPTURE_RUN_ATTEMPT="${2:?missing value for --fp0006-capture-run-attempt}"
			shift 2
			;;
		--fp0006-capture-event-name)
			FP0006_CAPTURE_EVENT_NAME="${2:?missing value for --fp0006-capture-event-name}"
			shift 2
			;;
		--fp0006-capture-ref)
			FP0006_CAPTURE_REF="${2:?missing value for --fp0006-capture-ref}"
			shift 2
			;;
		--fp0006-capture-github-sha)
			FP0006_CAPTURE_GITHUB_SHA="${2:?missing value for --fp0006-capture-github-sha}"
			shift 2
			;;
		--fp0006-capture-workflow-sha)
			FP0006_CAPTURE_WORKFLOW_SHA="${2:?missing value for --fp0006-capture-workflow-sha}"
			shift 2
			;;
		--fp0006-capture-base-sha)
			FP0006_CAPTURE_BASE_SHA="${2:?missing value for --fp0006-capture-base-sha}"
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

for numeric_option in "$JOBS" "$BOOT_TIMEOUT" "$SMOKE_TIMEOUT"; do
	if [[ ! "$numeric_option" =~ ^[1-9][0-9]*$ ]]; then
		echo "error: --jobs, --boot-timeout, and --smoke-timeout require positive integers." >&2
		exit 2
	fi
done

if [ "$(id -u)" -eq 0 ]; then
	echo "error: run this script as a normal user, not root." >&2
	echo "It uses sudo only for package install, cmake install, and boot commands." >&2
	exit 1
fi

if [ "$DO_INSTALL" -eq 0 ] && [ "$BOOT_SMOKE" -eq 1 ]; then
	echo "error: boot validation requires install; remove --build-only." >&2
	exit 1
fi

if [ "$FP0006_NEGATIVE_CAPTURE" -eq 1 ]; then
	if [ "$BOOT_SMOKE" -ne 1 ] || [ -z "$RUNTIME_EVIDENCE_DIR" ]; then
		echo 'error: FP-0006 capture requires boot smoke and a runtime evidence directory.' >&2
		exit 2
	fi
	if [[ ! "$FP0006_CAPTURE_HEAD" =~ ^[0-9a-f]{40}$ ]] ||
		[[ ! "$FP0006_CAPTURE_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] ||
		[[ ! "$FP0006_CAPTURE_RUN_ID" =~ ^[1-9][0-9]*$ ]] ||
		[[ ! "$FP0006_CAPTURE_RUN_ATTEMPT" =~ ^[1-9][0-9]*$ ]] ||
		[ "$FP0006_CAPTURE_EVENT_NAME" != pull_request ] ||
		[[ ! "$FP0006_CAPTURE_REF" =~ ^refs/pull/[1-9][0-9]*/merge$ ]] ||
		[[ ! "$FP0006_CAPTURE_GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]] ||
		[[ ! "$FP0006_CAPTURE_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]] ||
		[[ ! "$FP0006_CAPTURE_BASE_SHA" =~ ^[0-9a-f]{40}$ ]]
	then
		echo 'error: FP-0006 capture requires exact head/repository/run identity arguments.' >&2
		exit 2
	fi
elif [ -n "$FP0006_CAPTURE_HEAD$FP0006_CAPTURE_REPOSITORY$FP0006_CAPTURE_RUN_ID$FP0006_CAPTURE_RUN_ATTEMPT$FP0006_CAPTURE_EVENT_NAME$FP0006_CAPTURE_REF$FP0006_CAPTURE_GITHUB_SHA$FP0006_CAPTURE_WORKFLOW_SHA$FP0006_CAPTURE_BASE_SHA" ]; then
	echo 'error: FP-0006 capture identity arguments require the capture opt-in.' >&2
	exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL_DIR="${KERNEL_DIR:-/lib/modules/$(uname -r)/build}"
KERNEL_RELEASE=
BOOT_DEVICE_OWNER="$(id -un)"

say() {
	printf '\n==> %s\n' "$*"
}

need_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		echo "error: required command not found: $1" >&2
		exit 1
	fi
}

install_deps() {
	say "Installing Rocky/RHEL-family dependencies for the running kernel"
	sudo dnf install -y dnf-plugins-core
	sudo dnf config-manager --set-enabled powertools >/dev/null 2>&1 || \
		sudo dnf config-manager --set-enabled crb >/dev/null 2>&1 || true

	sudo dnf install -y \
		gcc gcc-c++ make cmake git tar patch diffutils which curl file findutils \
		"kernel-devel-$(uname -r)" "kernel-headers-$(uname -r)" \
		elfutils-libelf-devel numactl-devel rpm-build binutils-devel systemd-devel \
		zlib-devel openssl-devel bc bison flex perl dwarves lsof gzip xz \
		python3 pkgconf-pkg-config util-linux kmod procps-ng hostname \
		libselinux-utils shadow-utils sudo
}

ensure_kernel_headers() {
	say "Checking matching kernel build directory"
	if [ ! -d "$KERNEL_DIR" ]; then
		echo "error: missing $KERNEL_DIR" >&2
		echo "Install the exact matching package for this running kernel:" >&2
		echo "  sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)" >&2
		echo "This validation path is meant to adapt McKernel to the current Rocky kernel, not require a kernel upgrade." >&2
		exit 1
	fi
	if [ ! -f "$KERNEL_DIR/Makefile" ]; then
		echo "error: $KERNEL_DIR does not look like a kernel build tree." >&2
		exit 1
	fi

	if [ -s "$KERNEL_DIR/include/config/kernel.release" ]; then
		KERNEL_RELEASE="$(tr -d '[:space:]' <"$KERNEL_DIR/include/config/kernel.release")"
	else
		KERNEL_RELEASE="$(make -s -C "$KERNEL_DIR" kernelrelease)"
	fi
	if [[ ! "$KERNEL_RELEASE" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
		echo "error: could not derive a valid kernel release from $KERNEL_DIR: $KERNEL_RELEASE" >&2
		exit 1
	fi
	echo "Kernel build release: $KERNEL_RELEASE"
}

ensure_libuedev() {
	say "Checking libudev development files"
	if [ ! -e /usr/include/libudev.h ]; then
		echo "error: missing /usr/include/libudev.h" >&2
		echo "Install the Rocky/RHEL systemd-devel package and retry." >&2
		exit 1
	fi

	local found=0
	local libdir
	for libdir in /usr/lib64 /usr/lib /lib64 /lib; do
		if [ -e "$libdir/libudev.so" ]; then
			found=1
			break
		fi
	done
	if [ "$found" -ne 1 ]; then
		echo "error: missing unversioned libudev.so development symlink" >&2
		echo "Install the Rocky/RHEL systemd-devel package and retry." >&2
		exit 1
	fi
}

ensure_rust() {
	say "Checking Rust nightly"
	if ! command -v rustup >/dev/null 2>&1; then
		curl https://sh.rustup.rs -sSf | sh -s -- -y
	fi

	# shellcheck disable=SC1091
	[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"

	rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal
	export RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN"

	verify_rustc
}

verify_rustc() {
	local actual
	actual="$(rustc --version)"
	if [ "$actual" != "$EXPECTED_RUSTC_VERSION" ]; then
		echo "error: Rust validation requires the pinned compiler." >&2
		echo "expected: $EXPECTED_RUSTC_VERSION" >&2
		echo "actual:   $actual" >&2
		exit 1
	fi
	echo "$actual"
}

record_environment() {
	say "Recording Rocky/RHEL-family validation provenance"
	cat /etc/os-release
	uname -a
	rustc -Vv
	printf 'kernel_dir=%s\n' "$KERNEL_DIR"
	printf 'kernel_release=%s\n' "$KERNEL_RELEASE"
	printf 'boot_device_owner=%s\n' "$BOOT_DEVICE_OWNER"
	if command -v rpm >/dev/null 2>&1; then
		rpm -qf "$KERNEL_DIR/Makefile" ||
			echo "Kernel build tree is not owned by an installed RPM: $KERNEL_DIR"
	fi
	git -C "$ROOT_DIR" rev-parse HEAD
	git -C "$ROOT_DIR" submodule status --recursive
}

update_submodules() {
	say "Initializing submodules"
	local git_probe="$ROOT_DIR/.git/.mckernel-write-test.$$"
	local can_update_git=0

	if (: >"$git_probe") >/dev/null 2>&1; then
		rm -f "$git_probe"
		can_update_git=1
	fi

	if [ "$can_update_git" -eq 1 ]; then
		git -C "$ROOT_DIR" submodule update --init --recursive
	elif git -C "$ROOT_DIR" submodule status --recursive |
			awk 'NF && substr($1, 1, 1) == "-" { missing = 1 }
			     END { exit missing ? 1 : 0 }'; then
		echo "Git metadata is read-only; submodules are already initialized, skipping update."
	else
		echo "error: Git metadata is read-only and at least one submodule is missing." >&2
		echo "Run submodule initialization from a writable checkout before Rocky validation." >&2
		exit 1
	fi

	local ihk_patch="$ROOT_DIR/scripts/patches/ihk-linux-compat.patch"
	if [ "$APPLY_IHK_PATCH" -eq 0 ]; then
		echo "Skipping local IHK compatibility patch by request."
	elif [ -f "$ihk_patch" ]; then
		say "Applying local IHK compatibility patch"
		if git -C "$ROOT_DIR/ihk" apply --check "$ihk_patch" >/dev/null 2>&1; then
			git -C "$ROOT_DIR/ihk" apply "$ihk_patch"
		elif git -C "$ROOT_DIR/ihk" apply --reverse --check "$ihk_patch" >/dev/null 2>&1; then
			echo "IHK compatibility patch already applied."
		else
			git -C "$ROOT_DIR/ihk" apply --check "$ihk_patch" || true
			echo "error: unable to apply $ihk_patch to ihk submodule." >&2
			echo "Check for unexpected local changes in $ROOT_DIR/ihk." >&2
			exit 1
		fi
	fi
}

configure_and_build() {
	say "Configuring Rust-enabled McKernel"
	rm -rf "$BUILD_DIR"
	cmake -S "$ROOT_DIR" \
		-B "$BUILD_DIR" \
		-Wno-dev \
		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
		-DBUILD_TARGET=smp-x86 \
		-DENABLE_RUST_KERNEL=ON \
		-DENABLE_RUST_IHK_MODULE_HELPERS=ON \
		-DENABLE_RUST_USER_TOOLS=ON \
		-DCMAKE_INSTALL_PREFIX="$PREFIX" \
		-DUNAME_R="$KERNEL_RELEASE" \
		-DKERNEL_DIR="$KERNEL_DIR"

	local cache_uname
	local cache_kernel_dir
	cache_uname="$(awk -F= '$1 ~ /^UNAME_R:/ { value = $2 } END { print value }' \
		"$BUILD_DIR/CMakeCache.txt")"
	cache_kernel_dir="$(awk -F= '$1 ~ /^KERNEL_DIR:/ { value = $2 } END { print value }' \
		"$BUILD_DIR/CMakeCache.txt")"
	if [ "$cache_uname" != "$KERNEL_RELEASE" ] ||
		[ "$cache_kernel_dir" != "$KERNEL_DIR" ]
	then
		echo "error: CMake kernel provenance does not match the selected build tree." >&2
		echo "expected UNAME_R=$KERNEL_RELEASE KERNEL_DIR=$KERNEL_DIR" >&2
		echo "cached   UNAME_R=$cache_uname KERNEL_DIR=$cache_kernel_dir" >&2
		exit 1
	fi

	say "Building McKernel, host modules, and smoke-test user tools"
	cmake --build "$BUILD_DIR" \
		--target mckernel.img ihk_ko ihk-smp-x86_64_ko mcctrl_ko \
		mcexec eclair mcinspect sched_yield ldump2mcdump mcstat \
		ihkconfig ihkosctl ihkmond \
		-j"$JOBS"

	say "Building deterministic mcexec userspace workload"
	"${CC:-cc}" -O2 -std=c11 -Wall -Wextra -Werror \
		"$ROOT_DIR/scripts/smoke/mcexec-rust-smoke.c" \
		-o "$BUILD_DIR/mcexec-rust-smoke"

	check_rust_kernel_context_no_simd
	check_rust_artifact_linkage
	record_mckernel_conversion_evidence
}

source_retirement_audit() {
	say "Auditing Rust-selected tree with exact pinned-IHK C profile exemptions"

	local args=(
		--repo "$ROOT_DIR"
		--tracker "$ROOT_DIR/rust-source-retirement.txt"
		--build-dir "$BUILD_DIR"
		--fail-on-retired-compiled-c
		--fail-on-stale-tracker-row
		--allow-stale-tracker-row ihk/linux/core/abi_checks.c
		--allow-compiled-source ihk/ikc/linux.c
		--allow-compiled-source ihk/ikc/master.c
		--allow-compiled-source ihk/ikc/queue.c
		--allow-compiled-source ihk/linux/core/mem_alloc.c
		--allow-compiled-source ihk/linux/core/mikc.c
		--allow-compiled-source ihk/linux/core/mm.c
		# The recorded IHK submodule is the intentionally C host boundary for
		# this parent-repository validation profile.  Its standalone user tools
		# do not contain the later, uncommitted Rust full-body sources recorded
		# by the parent retirement tracker, so keep these exact paths visible as
		# profile exemptions.  The audit rejects missing, unused, or additional
		# compiled retired sources.
		--allow-compiled-source ihk/linux/user/ihkconfig.c
		--allow-compiled-source ihk/linux/user/ihkmond.c
		--allow-compiled-source ihk/linux/user/ihkosctl.c
	)

	if [ "$SOURCE_RETIREMENT_FINAL" -eq 1 ]; then
		args+=(
			--fail-on-unretired
			--fail-on-executable-headers
			--fail-on-compiled-c
			--fail-on-unjustified-allowlist
		)
	fi

	"$ROOT_DIR/scripts/rust-source-retirement-audit.py" "${args[@]}"
}

check_rust_kernel_context_no_simd() {
	say "Checking recorded Rust kernel/module-context objects for SIMD instructions"
	need_cmd objdump

	local obj
	for obj in \
		"$BUILD_DIR/kernel/rust/mckernel_rust.o" \
		"$BUILD_DIR/executer/kernel/mcctrl/rust/mcctrl_helpers.o"
	do
		if [ ! -f "$obj" ]; then
			echo "error: missing Rust kernel-context object: $obj" >&2
			exit 1
		fi

		local hits
		hits="$(objdump -d "$obj" |
			grep -Ei '%(xmm|ymm|zmm|mm)[0-9]|[[:space:]](movaps|movups|movdqa|movdqu|xorps|xorpd|pshuf[^[:space:]]*|padd[^[:space:]]*|pand[^[:space:]]*|pxor|popcnt|xsave[^[:space:]]*|fxsave[^[:space:]]*)[[:space:]]' || true)"
		if [ -n "$hits" ]; then
			echo "error: SIMD-like instructions found in Rust kernel-context object: $obj" >&2
			printf '%s\n' "$hits" | awk 'NR <= 20' >&2
			exit 1
		fi
	done

	local source_obj
	for source_obj in \
		"ihk/linux/core/rust/core_helpers.rs|ihk/linux/core/rust/core_helpers.o" \
		"ihk/linux/driver/smp/rust/smp_driver_helpers.rs|ihk/linux/driver/smp/rust/smp_driver_helpers.o"
	do
		local source_rel="${source_obj%%|*}"
		local obj_rel="${source_obj#*|}"
		if [ -f "$ROOT_DIR/$source_rel" ]; then
			obj="$BUILD_DIR/$obj_rel"
			if [ ! -f "$obj" ]; then
				echo "error: Rust IHK source exists but its object is missing: $obj" >&2
				exit 1
			fi
			local hits
			hits="$(objdump -d "$obj" |
				grep -Ei '%(xmm|ymm|zmm|mm)[0-9]|[[:space:]](movaps|movups|movdqa|movdqu|xorps|xorpd|pshuf[^[:space:]]*|padd[^[:space:]]*|pand[^[:space:]]*|pxor|popcnt|xsave[^[:space:]]*|fxsave[^[:space:]]*)[[:space:]]' || true)"
			if [ -n "$hits" ]; then
				echo "error: SIMD-like instructions found in Rust kernel-context object: $obj" >&2
				printf '%s\n' "$hits" | awk 'NR <= 20' >&2
				exit 1
			fi
		else
			echo "Recorded pinned-IHK boundary is C: $source_rel is not present."
		fi
	done
}

require_defined_symbol() {
	local file="$1"
	local symbol="$2"

	if [ ! -f "$file" ]; then
		echo "error: missing artifact for symbol check: $file" >&2
		exit 1
	fi
	if ! nm -g --defined-only "$file" |
		awk -v want="$symbol" '$NF == want { found = 1 } END { exit found ? 0 : 1 }'
	then
		echo "error: $file does not define required Rust-path symbol: $symbol" >&2
		exit 1
	fi
}

require_undefined_symbol() {
	local file="$1"
	local symbol="$2"

	if [ ! -f "$file" ]; then
		echo "error: missing C shim object for import check: $file" >&2
		exit 1
	fi
	if ! nm -g "$file" |
		awk -v want="$symbol" '$(NF - 1) == "U" && $NF == want { found = 1 } END { exit found ? 0 : 1 }'
	then
		echo "error: $file does not import required Rust-path symbol: $symbol" >&2
		exit 1
	fi
}

reject_undefined_symbol() {
	local file="$1"
	local symbol="$2"

	if [ ! -f "$file" ]; then
		echo "error: missing final artifact for resolved-symbol check: $file" >&2
		exit 1
	fi
	if nm -g "$file" |
		awk -v want="$symbol" '$(NF - 1) == "U" && $NF == want { found = 1 } END { exit found ? 0 : 1 }'
	then
		echo "error: $file retains forbidden unresolved symbol: $symbol" >&2
		exit 1
	fi
}

normalize_hex() {
	local value="${1#0x}"
	value="$(printf '%s' "$value" | sed 's/^0*//')"
	printf '0x%s\n' "${value:-0}"
}

check_rust_artifact_linkage() {
	say "Checking Rust entry/linkage across McKernel, mcctrl, and mcexec"
	need_cmd nm
	need_cmd readelf

	local rust_kernel="$BUILD_DIR/kernel/rust/mckernel_rust.o"
	local image="$BUILD_DIR/kernel/mckernel.img"
	local mcctrl_rust="$BUILD_DIR/executer/kernel/mcctrl/rust/mcctrl_helpers.o"
	local mcctrl_ko="$BUILD_DIR/executer/kernel/mcctrl/mcctrl.ko"
	local mcctrl_driver="$BUILD_DIR/executer/kernel/mcctrl/driver.o"
	local mcctrl_control="$BUILD_DIR/executer/kernel/mcctrl/control.o"
	local mcexec_rust="$BUILD_DIR/executer/user/rust/mcexec_helpers.o"
	local mcexec_bin="$BUILD_DIR/executer/user/mcexec"
	local mcexec_c="$BUILD_DIR/executer/user/CMakeFiles/mcexec.dir/mcexec.c.o"

	local symbol
	for symbol in arch_start main monitor_init \
		init_host_ikc2linux init_host_ikc2mckernel \
		prepare_process_ranges_args_envs mcexec_v10_trace_enter_user
	do
		require_defined_symbol "$rust_kernel" "$symbol"
		require_defined_symbol "$image" "$symbol"
	done
	for symbol in mcctrl_driver_boot_notifier_body_result \
		mcctrl_driver_init_body_result mcctrl_driver_exit_body_result \
		mcctrl_control_dispatch_body_result \
		mcctrl_control_transfer_image_body_result \
		mcctrl_control_start_image_body_result \
		mcctrl_control_ret_syscall_body_result prepare_ikc_channels
	do
		require_defined_symbol "$mcctrl_rust" "$symbol"
		require_defined_symbol "$mcctrl_ko" "$symbol"
	done
	for symbol in mcexec_main_body mcexec_finish_main_image_body \
		act_main_loop_body act_generic_syscall do_syscall_return
	do
		require_defined_symbol "$mcexec_rust" "$symbol"
		require_defined_symbol "$mcexec_bin" "$symbol"
	done

	for symbol in mcctrl_driver_init_body_result mcctrl_driver_exit_body_result \
		mcctrl_driver_boot_notifier_body_result prepare_ikc_channels
	do
		require_undefined_symbol "$mcctrl_driver" "$symbol"
	done
	for symbol in mcctrl_control_dispatch_body_result \
		mcctrl_control_transfer_image_body_result \
		mcctrl_control_start_image_body_result \
		mcctrl_control_ret_syscall_body_result
	do
		require_undefined_symbol "$mcctrl_control" "$symbol"
	done
	require_undefined_symbol "$mcexec_c" mcexec_main_body
	require_undefined_symbol "$mcctrl_rust" ihk_ikc_get_processor_id
	require_defined_symbol "$mcctrl_driver" ihk_ikc_get_processor_id
	require_defined_symbol "$mcctrl_ko" ihk_ikc_get_processor_id
	reject_undefined_symbol "$mcctrl_ko" ihk_ikc_get_processor_id

	local elf_entry
	local rust_entry
	elf_entry="$(readelf -h "$image" |
		awk '/Entry point address:/ { value = tolower($4) } END { if (value != "") print value }')"
	rust_entry="$(nm -n "$image" |
		awk '$NF == "arch_start" { value = "0x" tolower($1) } END { if (value != "") print value }')"
	if [[ ! "$elf_entry" =~ ^0x[[:xdigit:]]+$ ]] ||
		[[ ! "$rust_entry" =~ ^0x[[:xdigit:]]+$ ]]
	then
		echo "error: could not resolve McKernel ELF entry or Rust arch_start" >&2
		exit 1
	fi
	elf_entry="$(normalize_hex "$elf_entry")"
	rust_entry="$(normalize_hex "$rust_entry")"
	if [ "$elf_entry" != "$rust_entry" ]; then
		echo "error: McKernel ELF entry $elf_entry does not match Rust arch_start $rust_entry" >&2
		exit 1
	fi

	local forbidden_source
	for forbidden_source in kernel/init.c kernel/host.c kernel/host_helpers.c
	do
		if grep -Fq "$forbidden_source" "$BUILD_DIR/compile_commands.json"; then
			echo "error: strict Rust image unexpectedly compiles $forbidden_source" >&2
			exit 1
		fi
	done

	echo "Rust linkage check: ELF arch_start, Rust main/host handoff, mcctrl, and mcexec bodies are linked."
}

record_mckernel_conversion_evidence() {
	say "Recording production syscall ownership and linked-text evidence"
	need_cmd python3
	need_cmd nm
	need_cmd addr2line

	local source_commit
	local image="$BUILD_DIR/kernel/mckernel.img"
	local link_map="$BUILD_DIR/kernel/mckernel.img.map"
	local rust_object="$BUILD_DIR/kernel/rust/mckernel_rust.o"
	local composition_report="$BUILD_DIR/kernel/mckernel-syscall-offload-composition.json"
	local linked_report="$BUILD_DIR/kernel/mckernel-linked-text-ownership.json"
	local source_report="$BUILD_DIR/kernel/mckernel-symbol-source-attribution.json"

	source_commit="$(git -C "$ROOT_DIR" rev-parse HEAD)"
	if [[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]; then
		echo 'error: cannot bind conversion evidence to an exact source commit.' >&2
		exit 1
	fi

	python3 "$ROOT_DIR/scripts/mckernel_syscall_offload_check.py" \
		--build-dir "$BUILD_DIR" \
		--source-commit "$source_commit" \
		--output "$composition_report" >/dev/null
	python3 "$ROOT_DIR/scripts/mckernel_linked_text_ownership.py" \
		--image "$image" \
		--link-map "$link_map" \
		--rust-object "$rust_object" \
		--source-commit "$source_commit" \
		--output "$linked_report" >/dev/null
	python3 "$ROOT_DIR/scripts/mckernel_text_ownership.py" \
		--image "$image" \
		--repo "$ROOT_DIR" \
		--output "$source_report" >/dev/null

	python3 - "$composition_report" "$linked_report" "$source_report" <<'PY'
import json
import sys
from pathlib import Path

composition = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
linked = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
source = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
if composition.get("result") != "PASS":
    raise SystemExit("syscall-offload composition report did not pass")
print("Syscall-offload production composition: PASS")
print(
    "McKernel linked executable-text ownership: rust={}/{} bytes ({}%)".format(
        linked["rust_executable_text_bytes"],
        linked["total_executable_text_bytes"],
        linked["rust_executable_text_percent"],
    )
)
print(
    "McKernel symbol-source attribution: rust={} c={} scored={} bytes ({:.6f}%)".format(
        source["language_bytes"]["rust"],
        source["language_bytes"]["c"],
        source["scored_bytes"],
        source["rust_percent"],
    )
)
PY
}

install_artifacts() {
	say "Installing into $PREFIX"
	sudo cmake --install "$BUILD_DIR"
}

confirm_module_load_smoke() {
	cat <<EOF

About to load and unload C IHK host modules plus Rust-linked mcctrl from the build tree:
  ihk.ko, ihk-smp-x86_64.ko, mcctrl.ko

This does not boot McKernel or reserve CPUs/memory, but it does execute kernel
module init/exit paths. Make sure no McKernel OS instance is running and no IHK
modules are already loaded.

EOF
	if [ "$ASSUME_YES" -eq 1 ]; then
		return
	fi

	cat <<EOF
Type 'yes' to continue:
EOF
	read -r answer
	if [ "$answer" != "yes" ]; then
		echo "Skipping module-load smoke test."
		exit 0
	fi
}

module_load_smoke() {
	confirm_module_load_smoke
	say "Running IHK module-load smoke"
	"$ROOT_DIR/scripts/ihk-module-load-smoke.sh" --build-dir "$BUILD_DIR"
}

ensure_selinux_permissive_for_boot() {
	if ! command -v getenforce >/dev/null 2>&1; then
		BOOT_INITIAL_SELINUX_MODE=unavailable
		return
	fi

	local mode
	mode="$(getenforce | tr '[:upper:]' '[:lower:]')"
	case "$mode" in
		enforcing|permissive|disabled)
			;;
		*)
			echo "error: unexpected SELinux mode before boot: $mode" >&2
			exit 1
			;;
	esac
	BOOT_INITIAL_SELINUX_MODE="$mode"
	printf 'SELinux mode before boot: %s\n' "$mode"
	if [ "$mode" != "enforcing" ]; then
		return
	fi

	if ! command -v setenforce >/dev/null 2>&1; then
		echo "error: SELinux is enforcing and setenforce is unavailable." >&2
		echo "Temporarily set SELinux permissive before boot validation." >&2
		exit 1
	fi

	say "Temporarily setting SELinux permissive for McKernel boot validation"
	BOOT_RESTORE_SELINUX=1
	run_privileged_lifecycle_cmd 'SELinux permissive transition' setenforce 0
	mode="$(getenforce | tr '[:upper:]' '[:lower:]')"
	if [ "$mode" != "permissive" ]; then
		echo "error: SELinux did not enter permissive mode: $mode" >&2
		return 1
	fi
}

restore_selinux_after_boot() {
	if [ "$BOOT_RESTORE_SELINUX" -eq 1 ]; then
		say "Restoring SELinux enforcing mode"
		if ! run_privileged_lifecycle_cmd \
			'SELinux enforcing restoration' setenforce 1
		then
			return 1
		fi
		BOOT_RESTORE_SELINUX=0
	fi
}

is_timeout_status() {
	[ "$1" -eq 124 ] || [ "$1" -eq 137 ]
}

run_privileged_timed_capture() {
	local label="$1"
	local limit="$2"
	local output_name="$3"
	shift 3
	local output
	local rc=0

	output="$(sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$limit" "$@")" || rc=$?
	if [ "$rc" -ne 0 ]; then
		if is_timeout_status "$rc"; then
			echo "error: ${label} exceeded its ${limit}s watchdog (status ${rc})." >&2
		else
			echo "error: ${label} failed with status ${rc}." >&2
		fi
		return "$rc"
	fi
	printf -v "$output_name" '%s' "$output"
}

run_privileged_timed_to_file() {
	local label="$1"
	local limit="$2"
	local output_file="$3"
	shift 3
	local rc=0

	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$limit" "$@" >"$output_file" || rc=$?
	if [ "$rc" -ne 0 ]; then
		if is_timeout_status "$rc"; then
			echo "error: ${label} exceeded its ${limit}s watchdog (status ${rc})." >&2
		else
			echo "error: ${label} failed with status ${rc}." >&2
		fi
		return "$rc"
	fi
}

run_privileged_lifecycle_cmd() {
	local label="$1"
	shift
	local rc=0

	echo "watchdog: ${label} has a ${BOOT_TIMEOUT}s limit" >&2
	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$BOOT_TIMEOUT" "$@" || rc=$?
	if [ "$rc" -ne 0 ] && is_timeout_status "$rc"; then
		echo "error: ${label} exceeded the ${BOOT_TIMEOUT}s lifecycle watchdog (status ${rc})." >&2
	fi
	return "$rc"
}

cleanup_boot_evidence() {
	local path

	if [ -z "$BOOT_EVIDENCE_DIR" ]; then
		return
	fi
	for path in "$BOOT_DMESG_BEFORE" "$BOOT_DMESG_AFTER" \
		"$BOOT_DMESG_DELTA" "$BOOT_KMSG" "$BOOT_BEFORE_WORKLOAD_KMSG" \
		"$BOOT_AFTER_WORKLOAD_KMSG" "$BOOT_WORKLOAD_KMSG_DELTA" \
		"$BOOT_FINAL_KMSG" "$BOOT_IRQ_AFFINITY_BEFORE"
	do
		if [ -n "$path" ]; then
			rm -f -- "$path"
		fi
	done
	rmdir -- "$BOOT_EVIDENCE_DIR" 2>/dev/null || true
	BOOT_EVIDENCE_DIR=
	BOOT_DMESG_BEFORE=
	BOOT_DMESG_AFTER=
	BOOT_DMESG_DELTA=
	BOOT_KMSG=
	BOOT_BEFORE_WORKLOAD_KMSG=
	BOOT_AFTER_WORKLOAD_KMSG=
	BOOT_WORKLOAD_KMSG_DELTA=
	BOOT_FINAL_KMSG=
	BOOT_IRQ_AFFINITY_BEFORE=
}

initialize_runtime_evidence() {
	if [ -z "$RUNTIME_EVIDENCE_DIR" ]; then
		return
	fi
	if [[ ! "$RUNTIME_EVIDENCE_DIR" =~ ^/tmp/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
		echo 'error: MCKERNEL_RUNTIME_EVIDENCE_DIR must be one safe directory directly under /tmp.' >&2
		exit 2
	fi
	if [ -L "$RUNTIME_EVIDENCE_DIR" ]; then
		echo "error: runtime evidence path must not be a symlink: $RUNTIME_EVIDENCE_DIR" >&2
		exit 2
	fi
	if [ -e "$RUNTIME_EVIDENCE_DIR" ]; then
		if [ ! -d "$RUNTIME_EVIDENCE_DIR" ] ||
			find "$RUNTIME_EVIDENCE_DIR" -mindepth 1 -print -quit | grep -q .
		then
			echo "error: runtime evidence directory is not empty: $RUNTIME_EVIDENCE_DIR" >&2
			exit 2
		fi
		chmod 700 "$RUNTIME_EVIDENCE_DIR"
	else
		mkdir -m 700 -p "$RUNTIME_EVIDENCE_DIR"
	fi
}

refresh_runtime_evidence_manifest() {
	if [ -z "$RUNTIME_EVIDENCE_DIR" ]; then
		return
	fi
	if ! (
		cd "$RUNTIME_EVIDENCE_DIR"
		find . -type f ! -name SHA256SUMS -print0 | sort -z | \
			xargs -0 -r sha256sum
	) >"$RUNTIME_EVIDENCE_DIR/SHA256SUMS"
	then
		echo 'error: could not refresh the runtime evidence manifest.' >&2
		return 1
	fi
}

record_runtime_provenance() {
	local arch
	local conversion_evidence
	local file_count
	local manifest_sha
	local os_id
	local os_version
	local product
	local source_commit
	local -a matches=()

	if [ -z "$RUNTIME_EVIDENCE_DIR" ]; then
		return
	fi
	if [ ! -r /etc/os-release ]; then
		echo 'error: cannot read /etc/os-release for runtime provenance.' >&2
		return 1
	fi
	# shellcheck disable=SC1091
	. /etc/os-release
	os_id="${ID:-}"
	os_version="${VERSION_ID:-}"
	arch="$(uname -m)" || return 1
	source_commit="$(git -C "$ROOT_DIR" rev-parse HEAD)" || return 1
	if [ -z "$os_id" ] || [ -z "$os_version" ] || [ -z "$arch" ] ||
		[[ ! "$source_commit" =~ ^[0-9a-f]{40}$ ]]
	then
		echo 'error: incomplete runtime provenance identity.' >&2
		return 1
	fi
	if ! {
		printf 'source_commit=%s\n' "$source_commit"
		printf 'os_id=%s\n' "$os_id"
		printf 'os_version=%s\n' "$os_version"
		printf 'arch=%s\n' "$arch"
		cat /etc/os-release
		uname -a
		rustc -Vv
		printf 'kernel_dir=%s\n' "$KERNEL_DIR"
		printf 'kernel_release=%s\n' "$KERNEL_RELEASE"
		git -C "$ROOT_DIR" submodule status --recursive
	} >"$RUNTIME_EVIDENCE_DIR/runtime-environment.txt"
	then
		echo 'error: could not record the runtime environment.' >&2
		return 1
	fi
	if ! rpm -qa \
		--qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | sort \
		>"$RUNTIME_EVIDENCE_DIR/runtime-rpms.txt"
	then
		echo 'error: could not record the runtime RPM manifest.' >&2
		return 1
	fi
	if ! dnf repolist -v \
		>"$RUNTIME_EVIDENCE_DIR/runtime-repositories.txt"
	then
		echo 'error: could not record the runtime repository manifest.' >&2
		return 1
	fi
	: >"$RUNTIME_EVIDENCE_DIR/runtime-artifacts.sha256"
	for product in mckernel.img ihk.ko ihk-smp-x86_64.ko mcctrl.ko \
		mcexec mcexec-rust-smoke
	do
		mapfile -d '' -t matches < <(
			find "$BUILD_DIR" -type f -name "$product" -print0
		)
		if [ "${#matches[@]}" -ne 1 ]; then
			echo "error: expected one runtime artifact named $product, found ${#matches[@]}." >&2
			return 1
		fi
		if ! sha256sum "${matches[0]}" \
			>>"$RUNTIME_EVIDENCE_DIR/runtime-artifacts.sha256"
		then
			echo "error: could not hash runtime artifact: ${matches[0]}" >&2
			return 1
		fi
	done
	for conversion_evidence in \
		mckernel.img.map \
		mckernel-linked-text-ownership.json \
		mckernel-symbol-source-attribution.json \
		mckernel-syscall-offload-composition.json
	do
		if [ ! -s "$BUILD_DIR/kernel/$conversion_evidence" ]; then
			echo "error: missing conversion evidence: $conversion_evidence" >&2
			return 1
		fi
		if ! cp -- "$BUILD_DIR/kernel/$conversion_evidence" \
			"$RUNTIME_EVIDENCE_DIR/$conversion_evidence"
		then
			echo "error: could not preserve conversion evidence: $conversion_evidence" >&2
			return 1
		fi
	done
	refresh_runtime_evidence_manifest || return 1
	file_count="$(find "$RUNTIME_EVIDENCE_DIR" \
		-type f ! -name SHA256SUMS | wc -l)" || return 1
	manifest_sha="$(sha256sum "$RUNTIME_EVIDENCE_DIR/SHA256SUMS" | \
		awk '{ print $1 }')" || return 1
	if [[ ! "$file_count" =~ ^[1-9][0-9]*$ ]] ||
		[[ ! "$manifest_sha" =~ ^[0-9a-f]{64}$ ]]
	then
		echo 'error: invalid runtime provenance count or manifest digest.' >&2
		return 1
	fi
	printf 'Runtime provenance manifest: files=%s sha256=%s\n' \
		"$file_count" "$manifest_sha"
}

preserve_boot_evidence() {
	local source
	local destination
	local file_count
	local manifest_sha

	if [ -z "$RUNTIME_EVIDENCE_DIR" ] || [ -z "$BOOT_EVIDENCE_DIR" ]; then
		return
	fi
	for source in "$BOOT_DMESG_BEFORE" "$BOOT_DMESG_AFTER" \
		"$BOOT_DMESG_DELTA" "$BOOT_KMSG" "$BOOT_BEFORE_WORKLOAD_KMSG" \
		"$BOOT_AFTER_WORKLOAD_KMSG" "$BOOT_WORKLOAD_KMSG_DELTA" \
		"$BOOT_FINAL_KMSG" "$BOOT_IRQ_AFFINITY_BEFORE"
	do
		if [ ! -f "$source" ]; then
			continue
		fi
		destination="$RUNTIME_EVIDENCE_DIR/$(basename "$source")"
		if ! cp -- "$source" "$destination"; then
			echo "error: could not preserve runtime evidence: $source" >&2
			return 1
		fi
	done
	refresh_runtime_evidence_manifest || return 1
	file_count="$(find "$RUNTIME_EVIDENCE_DIR" \
		-type f ! -name SHA256SUMS | wc -l)" || return 1
	manifest_sha="$(sha256sum "$RUNTIME_EVIDENCE_DIR/SHA256SUMS" | \
		awk '{ print $1 }')" || return 1
	if [[ ! "$file_count" =~ ^[1-9][0-9]*$ ]] ||
		[[ ! "$manifest_sha" =~ ^[0-9a-f]{64}$ ]]
	then
		echo 'error: invalid runtime evidence count or manifest digest.' >&2
		return 1
	fi
	printf 'Runtime raw evidence preserved: files=%s manifest_sha256=%s\n' \
		"$file_count" "$manifest_sha"
}

capture_boot_environment() {
	local affinity_path
	local affinity_value
	local affinity_count=0
	local irqbalance_load_state
	local irqbalance_active_state
	local dmesg_rc=0

	if [ ! -r /sys/devices/system/cpu/online ]; then
		echo 'error: cannot record the pre-boot CPU online mask.' >&2
		return 1
	fi
	if [ ! -r /proc/sys/vm/swappiness ]; then
		echo 'error: cannot record the pre-boot vm.swappiness value.' >&2
		return 1
	fi

	BOOT_INITIAL_CPU_ONLINE="$(cat /sys/devices/system/cpu/online)"
	BOOT_INITIAL_SWAPPINESS="$(cat /proc/sys/vm/swappiness)"
	BOOT_INITIAL_IRQBALANCE=unavailable
	if command -v systemctl >/dev/null 2>&1; then
		irqbalance_load_state="$(systemctl show -p LoadState --value \
			irqbalance.service 2>/dev/null)" || {
			echo 'error: cannot determine the pre-boot irqbalance unit load state.' >&2
			return 1
		}
		case "$irqbalance_load_state" in
		loaded)
			irqbalance_active_state="$(systemctl show -p ActiveState --value \
				irqbalance.service 2>/dev/null)" || {
				echo 'error: cannot determine the pre-boot irqbalance active state.' >&2
				return 1
			}
			case "$irqbalance_active_state" in
			active|inactive)
				BOOT_INITIAL_IRQBALANCE="$irqbalance_active_state"
				;;
			*)
				echo "error: irqbalance has unsupported pre-boot state: $irqbalance_active_state" >&2
				echo 'Wait for it to become active or inactive before boot validation.' >&2
				return 1
				;;
			esac
			;;
		not-found)
			;;
		*)
			echo "error: irqbalance has unsupported load state: $irqbalance_load_state" >&2
			return 1
			;;
		esac
	fi

	printf 'CPU online mask before boot: %s\n' "$BOOT_INITIAL_CPU_ONLINE"
	printf 'vm.swappiness before boot: %s\n' "$BOOT_INITIAL_SWAPPINESS"
	printf 'irqbalance state before boot: %s\n' "$BOOT_INITIAL_IRQBALANCE"
	: >"$BOOT_IRQ_AFFINITY_BEFORE"
	for affinity_path in /proc/irq/[0-9]*/smp_affinity; do
		if [ ! -r "$affinity_path" ]; then
			continue
		fi
		affinity_value="$(cat "$affinity_path")"
		printf '%s\t%s\n' "$affinity_path" "$affinity_value" \
			>>"$BOOT_IRQ_AFFINITY_BEFORE"
		affinity_count=$((affinity_count + 1))
	done
	if [ "$affinity_count" -eq 0 ]; then
		echo 'error: could not record any pre-boot IRQ affinity entries.' >&2
		return 1
	fi
	printf 'IRQ affinity baseline entries: %s\n' "$affinity_count"

	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$SMOKE_TIMEOUT" dmesg --color=never >"$BOOT_DMESG_BEFORE" || dmesg_rc=$?
	if [ "$dmesg_rc" -ne 0 ]; then
		echo "error: pre-boot Linux dmesg capture failed with status ${dmesg_rc}." >&2
		return "$dmesg_rc"
	fi
	BOOT_DMESG_BASELINE_LINES="$(wc -l <"$BOOT_DMESG_BEFORE")"
	printf 'Linux dmesg baseline lines: %s\n' "$BOOT_DMESG_BASELINE_LINES"
}

restore_boot_environment() {
	local current_swappiness

	if [ "$BOOT_RESTORE_ENVIRONMENT" -ne 1 ]; then
		return
	fi
	if [ "$BOOT_INITIAL_SWAPPINESS" != unavailable ]; then
		current_swappiness="$(cat /proc/sys/vm/swappiness)"
		if [ "$current_swappiness" != "$BOOT_INITIAL_SWAPPINESS" ]; then
			if ! run_privileged_lifecycle_cmd 'vm.swappiness restoration' \
				sysctl -q -w "vm.swappiness=$BOOT_INITIAL_SWAPPINESS"
			then
				return 1
			fi
		fi
	fi

	case "$BOOT_INITIAL_IRQBALANCE" in
	active)
		if ! run_privileged_lifecycle_cmd \
			'irqbalance active-state restoration' \
			systemctl restart irqbalance.service
		then
			return 1
		fi
		;;
	inactive)
		if ! run_privileged_lifecycle_cmd \
			'irqbalance inactive-state restoration' \
			systemctl stop irqbalance.service
		then
			return 1
		fi
		;;
	unavailable)
		;;
	*)
		echo "error: invalid recorded irqbalance state: $BOOT_INITIAL_IRQBALANCE" >&2
		return 1
		;;
	esac
	BOOT_RESTORE_ENVIRONMENT=0
}

verify_boot_dmesg() {
	local after_lines
	local delta_lines
	local delta_sha
	local dmesg_rc=0

	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$SMOKE_TIMEOUT" dmesg --color=never >"$BOOT_DMESG_AFTER" || dmesg_rc=$?
	if [ "$dmesg_rc" -ne 0 ]; then
		echo "error: post-boot Linux dmesg capture failed with status ${dmesg_rc}." >&2
		return "$dmesg_rc"
	fi
	after_lines="$(wc -l <"$BOOT_DMESG_AFTER")"
	if [ "$after_lines" -lt "$BOOT_DMESG_BASELINE_LINES" ]; then
		echo 'error: Linux dmesg ring changed before a complete delta could be verified.' >&2
		return 1
	fi
	if ! cmp -s "$BOOT_DMESG_BEFORE" \
		<(head -n "$BOOT_DMESG_BASELINE_LINES" "$BOOT_DMESG_AFTER")
	then
		echo 'error: Linux dmesg baseline is no longer the prefix of the final ring buffer.' >&2
		echo 'The ring may have rolled over, so a complete fatal-signature scan is impossible.' >&2
		return 1
	fi
	sed -n "$((BOOT_DMESG_BASELINE_LINES + 1)),\$p" \
		"$BOOT_DMESG_AFTER" >"$BOOT_DMESG_DELTA"
	delta_lines="$(wc -l <"$BOOT_DMESG_DELTA")"
	if grep -Ei \
		'BUG:|Oops:|general protection fault|Kernel panic|panic - not syncing|WARNING: CPU:|Unable to handle kernel' \
		"$BOOT_DMESG_DELTA"
	then
		echo 'error: fatal Linux kernel signature found in the boot-validation dmesg delta.' >&2
		return 1
	fi
	delta_sha="$(sha256sum "$BOOT_DMESG_DELTA" | awk '{ print $1 }')"
	printf 'Linux dmesg delta fatal scan: clean lines=%s sha256=%s\n' \
		"$delta_lines" "$delta_sha"
}

normalize_cpu_list() {
	local spec="$1"
	local part
	local first
	local last
	local cpu
	local -a values=()
	local -a parts=()

	IFS=, read -r -a parts <<<"$spec"
	for part in "${parts[@]}"; do
		if [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
			first="${BASH_REMATCH[1]}"
			last="${BASH_REMATCH[2]}"
			if [ "$first" -gt "$last" ]; then
				return 1
			fi
			for ((cpu = first; cpu <= last; cpu++)); do
				values+=("$cpu")
			done
		elif [[ "$part" =~ ^[0-9]+$ ]]; then
			values+=("$part")
		else
			return 1
		fi
	done
	printf '%s\n' "${values[@]}" | sort -n -u | paste -sd, -
}

normalize_mem_list() {
	local spec="$1"
	local part
	local size
	local node
	local bytes
	local current
	local -a parts=()
	local -A totals=()

	[ -n "$spec" ] || return 1
	IFS=, read -r -a parts <<<"$spec"
	for part in "${parts[@]}"; do
		if [[ ! "$part" =~ ^([0-9]+)([KMGT]?)@([0-9]+)$ ]]; then
			return 1
		fi
		size="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
		node="$((10#${BASH_REMATCH[3]}))"
		bytes="$(numfmt --from=iec "$size")" || return 1
		if [[ ! "$bytes" =~ ^[0-9]+$ ]]; then
			return 1
		fi
		current="${totals[$node]:-0}"
		totals["$node"]="$((current + bytes))"
	done
	for node in "${!totals[@]}"; do
		printf '%s@%s\n' "${totals[$node]}" "$node"
	done | \
		sort -t@ -k2,2n -k1,1n | paste -sd, -
}

record_live_boot_evidence() {
	local module
	local module_line
	local remaining_cpu
	local remaining_mem
	local assigned_cpu
	local assigned_mem
	local free_mem
	local expected_cpu
	local actual_cpu
	local expected_mem
	local actual_mem
	local normalized_free_mem
	local free_chunk
	local expected_chunk
	local node
	local free_bytes
	local assigned_bytes
	local -a free_chunks=()
	local -a expected_chunks=()
	local -A free_by_node=()
	local -A assigned_by_node=()

	for module in ihk ihk_smp_x86_64 mcctrl; do
		module_line="$(grep -E "^${module} " /proc/modules || true)"
		if [ -z "$module_line" ]; then
			echo "error: required live module is missing after McKernel boot: $module" >&2
			return 1
		fi
		printf 'live-module: %s\n' "$module_line"
	done

	run_privileged_timed_capture 'IHK remaining CPU query' "$SMOKE_TIMEOUT" \
		remaining_cpu "$PREFIX/sbin/ihkconfig" 0 query cpu || return
	run_privileged_timed_capture 'IHK remaining memory query' "$SMOKE_TIMEOUT" \
		remaining_mem "$PREFIX/sbin/ihkconfig" 0 query mem || return
	run_privileged_timed_capture 'McKernel assigned CPU query' "$SMOKE_TIMEOUT" \
		assigned_cpu "$PREFIX/sbin/ihkosctl" 0 query cpu || return
	run_privileged_timed_capture 'McKernel assigned memory query' "$SMOKE_TIMEOUT" \
		assigned_mem "$PREFIX/sbin/ihkosctl" 0 query mem || return
	run_privileged_timed_capture 'McKernel free-memory query' "$SMOKE_TIMEOUT" \
		free_mem "$PREFIX/sbin/ihkosctl" 0 query_free_mem || return

	printf 'IHK remaining unassigned CPU reserves: %s\n' "${remaining_cpu:-none}"
	printf 'IHK remaining unassigned memory reserves: %s\n' "${remaining_mem:-none}"
	if [ -n "$remaining_cpu" ]; then
		echo "error: requested CPUs were not fully assigned to McKernel: $remaining_cpu" >&2
		return 1
	fi
	if [ -n "$remaining_mem" ]; then
		echo "error: requested memory was not fully assigned to McKernel: $remaining_mem" >&2
		return 1
	fi
	expected_cpu="$(normalize_cpu_list "$BOOT_CPUS")" || {
		echo "error: cannot normalize requested CPU list: $BOOT_CPUS" >&2
		return 1
	}
	actual_cpu="$(normalize_cpu_list "$assigned_cpu")" || {
		echo "error: cannot normalize McKernel assigned CPU output: $assigned_cpu" >&2
		return 1
	}
	if [ "$actual_cpu" != "$expected_cpu" ]; then
		echo 'error: McKernel CPU assignment does not match the request.' >&2
		echo "requested=$expected_cpu assigned=$actual_cpu" >&2
		return 1
	fi
	expected_mem="$(normalize_mem_list "$BOOT_MEM")" || {
		echo "error: cannot normalize requested memory list: $BOOT_MEM" >&2
		return 1
	}
	actual_mem="$(normalize_mem_list "$assigned_mem")" || {
		echo "error: cannot normalize McKernel assigned memory output: $assigned_mem" >&2
		return 1
	}
	if [ "$actual_mem" != "$expected_mem" ]; then
		echo 'error: McKernel memory assignment does not match the request.' >&2
		echo "requested=$expected_mem assigned=$actual_mem" >&2
		return 1
	fi
	normalized_free_mem="$(normalize_mem_list "$free_mem")" || {
		echo "error: cannot normalize McKernel free-memory output: $free_mem" >&2
		return 1
	}
	IFS=, read -r -a free_chunks <<<"$normalized_free_mem"
	if [ "${#free_chunks[@]}" -eq 0 ]; then
		echo 'error: McKernel free-memory query returned no data.' >&2
		return 1
	fi
	for free_chunk in "${free_chunks[@]}"; do
		node="${free_chunk#*@}"
		free_bytes="${free_chunk%@*}"
		free_by_node["$node"]="$free_bytes"
	done
	IFS=, read -r -a expected_chunks <<<"$expected_mem"
	for expected_chunk in "${expected_chunks[@]}"; do
		node="${expected_chunk#*@}"
		assigned_bytes="${expected_chunk%@*}"
		assigned_by_node["$node"]="$assigned_bytes"
		if [ -z "${free_by_node[$node]+present}" ]; then
			echo "error: McKernel free-memory output omitted assigned NUMA node $node." >&2
			return 1
		fi
		free_bytes="${free_by_node[$node]}"
		if [ "$free_bytes" -le 0 ] || [ "$free_bytes" -gt "$assigned_bytes" ]; then
			echo "error: invalid McKernel free memory for NUMA node $node." >&2
			echo "assigned=$assigned_bytes free=$free_bytes" >&2
			return 1
		fi
	done
	for node in "${!free_by_node[@]}"; do
		if [ -z "${assigned_by_node[$node]+present}" ]; then
			echo "error: McKernel reported free memory on unassigned NUMA node $node." >&2
			return 1
		fi
	done
	printf 'McKernel assigned CPU evidence: %s\n' "$assigned_cpu"
	printf 'McKernel assigned memory evidence: %s\n' "$assigned_mem"
	printf 'McKernel free-memory evidence: %s\n' "$free_mem"
	printf 'McKernel requested CPU assignment: verified %s\n' "$expected_cpu"
	printf 'McKernel requested memory assignment: verified %s\n' "$expected_mem"
}

capture_workload_kmsg_baseline() {
	if ! run_privileged_timed_to_file 'pre-workload ihkosctl kmsg' \
		"$SMOKE_TIMEOUT" "$BOOT_BEFORE_WORKLOAD_KMSG" \
		"$PREFIX/sbin/ihkosctl" 0 kmsg
	then
		return 1
	fi
	if ! normalize_ihkosctl_kmsg_file "$BOOT_BEFORE_WORKLOAD_KMSG"; then
		return 1
	fi
	printf 'McKernel pre-workload kmsg baseline: bytes=%s sha256=%s\n' \
		"$(wc -c <"$BOOT_BEFORE_WORKLOAD_KMSG")" \
		"$(sha256sum "$BOOT_BEFORE_WORKLOAD_KMSG" | awk '{ print $1 }')"
}

verify_workload_runtime_markers() {
	local before_bytes
	local after_bytes
	local delta_lines
	local delta_sha
	local marker
	local owner_marker

	if ! run_privileged_timed_to_file 'post-workload ihkosctl kmsg' \
		"$SMOKE_TIMEOUT" "$BOOT_AFTER_WORKLOAD_KMSG" \
		"$PREFIX/sbin/ihkosctl" 0 kmsg
	then
		return 1
	fi
	if ! normalize_ihkosctl_kmsg_file "$BOOT_AFTER_WORKLOAD_KMSG"; then
		return 1
	fi
	before_bytes="$(wc -c <"$BOOT_BEFORE_WORKLOAD_KMSG")"
	after_bytes="$(wc -c <"$BOOT_AFTER_WORKLOAD_KMSG")"
	if [ "$after_bytes" -lt "$before_bytes" ]; then
		echo 'error: McKernel kmsg became shorter during the deterministic workload.' >&2
		return 1
	fi
	if ! cmp -s "$BOOT_BEFORE_WORKLOAD_KMSG" \
		<(head -c "$before_bytes" "$BOOT_AFTER_WORKLOAD_KMSG")
	then
		echo 'error: pre-workload McKernel kmsg is not a prefix of the post-workload log.' >&2
		echo 'A complete deterministic-workload marker delta cannot be proven.' >&2
		return 1
	fi
	tail -c "+$((before_bytes + 1))" "$BOOT_AFTER_WORKLOAD_KMSG" \
		>"$BOOT_WORKLOAD_KMSG_DELTA"

	for marker in \
		'mcexec_v10: prepared ' \
		'mcexec_v10: schedule_process queued ' \
		'mcexec_v10: enter_user ' \
		'mcexec_v10: send_syscall ' \
		'mcexec_v10: offload_return '
	do
		if ! grep -Fq "$marker" "$BOOT_WORKLOAD_KMSG_DELTA"; then
			echo "error: deterministic workload is missing Rust-path runtime marker: $marker" >&2
			return 1
		fi
		grep -Fm1 "$marker" "$BOOT_WORKLOAD_KMSG_DELTA"
	done
	for owner_marker in \
		'mcexec_v10: send_syscall owner=rust ' \
		'mcexec_v10: generic_forwarding owner=rust ' \
		'mcexec_v10: offload_wait owner=rust '
	do
		if ! grep -Fq "$owner_marker" "$BOOT_WORKLOAD_KMSG_DELTA"; then
			echo "error: deterministic workload is missing Rust syscall-owner marker: $owner_marker" >&2
			return 1
		fi
		grep -Fm1 "$owner_marker" "$BOOT_WORKLOAD_KMSG_DELTA"
	done
	echo 'syscall-offload owner=rust send+forward+wait markers: OK'
	delta_lines="$(wc -l <"$BOOT_WORKLOAD_KMSG_DELTA")"
	delta_sha="$(sha256sum "$BOOT_WORKLOAD_KMSG_DELTA" | awk '{ print $1 }')"
	printf 'McKernel deterministic-workload kmsg delta: lines=%s sha256=%s\n' \
		"$delta_lines" "$delta_sha"
}

normalize_ihkosctl_kmsg_file() {
	local kmsg_file="$1"

	if [ ! -s "$kmsg_file" ]; then
		echo "error: ihkosctl kmsg produced an empty capture: $kmsg_file" >&2
		return 1
	fi
	if ! tail -c 1 "$kmsg_file" | grep -q '^$'; then
		echo 'error: ihkosctl kmsg capture lacks its expected CLI-added newline.' >&2
		return 1
	fi
	# ihkosctl prints the kernel buffer with printf("%s\n", buf), so remove
	# exactly that final CLI byte before comparing two snapshots.
	truncate -s -1 "$kmsg_file"
}

verify_post_workload_health() {
	local previous_bytes
	local final_bytes
	local final_lines
	local final_sha
	local initial_status
	local final_status

	if ! run_privileged_timed_capture 'post-workload ihkosctl status' \
		"$SMOKE_TIMEOUT" initial_status "$PREFIX/sbin/ihkosctl" 0 get status
	then
		return 1
	fi
	if [ "$initial_status" != RUNNING ]; then
		echo "error: McKernel is not RUNNING after the userspace workloads: $initial_status" >&2
		return 1
	fi
	printf 'McKernel post-workload initial status: %s\n' "$initial_status"
	if ! run_privileged_timed_to_file 'post-workload final ihkosctl kmsg' \
		"$SMOKE_TIMEOUT" "$BOOT_FINAL_KMSG" \
		"$PREFIX/sbin/ihkosctl" 0 kmsg
	then
		return 1
	fi
	if ! normalize_ihkosctl_kmsg_file "$BOOT_FINAL_KMSG"; then
		return 1
	fi
	previous_bytes="$(wc -c <"$BOOT_AFTER_WORKLOAD_KMSG")"
	final_bytes="$(wc -c <"$BOOT_FINAL_KMSG")"
	if [ "$final_bytes" -lt "$previous_bytes" ] ||
		! cmp -s "$BOOT_AFTER_WORKLOAD_KMSG" \
			<(head -c "$previous_bytes" "$BOOT_FINAL_KMSG")
	then
		echo 'error: McKernel kmsg changed before a complete final health scan could be verified.' >&2
		return 1
	fi
	if grep -Ei \
		'mcexec_v10: fatal|(^|[[:space:]])PANIC([:[:space:]]|$)|(^|[[:space:]])panic:|BUG:|Oops:|general protection fault|unhandled page fault|assert(ion)? failed|stack (smashing|corruption)' \
		"$BOOT_FINAL_KMSG"
	then
		echo 'error: McKernel kmsg contains a fatal signature after the userspace workloads.' >&2
		return 1
	fi
	final_lines="$(wc -l <"$BOOT_FINAL_KMSG")"
	final_sha="$(sha256sum "$BOOT_FINAL_KMSG" | awk '{ print $1 }')"
	if ! run_privileged_timed_capture 'post-kmsg ihkosctl status' \
		"$SMOKE_TIMEOUT" final_status "$PREFIX/sbin/ihkosctl" 0 get status
	then
		return 1
	fi
	if [ "$final_status" != RUNNING ]; then
		echo "error: McKernel left RUNNING while final kmsg was checked: $final_status" >&2
		return 1
	fi
	printf 'McKernel post-workload status: %s\n' "$final_status"
	printf 'McKernel post-workload fatal scan: clean lines=%s sha256=%s\n' \
		"$final_lines" "$final_sha"
}

emit_raw_boot_evidence() {
	local kmsg_file="$BOOT_KMSG"

	if [ -s "$BOOT_FINAL_KMSG" ]; then
		kmsg_file="$BOOT_FINAL_KMSG"
	elif [ -s "$BOOT_AFTER_WORKLOAD_KMSG" ]; then
		kmsg_file="$BOOT_AFTER_WORKLOAD_KMSG"
	fi

	echo '===== BEGIN raw McKernel kmsg ====='
	cat "$kmsg_file"
	printf '\n===== END raw McKernel kmsg =====\n'
	echo '===== BEGIN raw Linux dmesg delta ====='
	cat "$BOOT_DMESG_DELTA"
	printf '\n===== END raw Linux dmesg delta =====\n'
}

verify_boot_cleanup() {
	local affinity_path
	local expected_affinity
	local actual_affinity
	local affinity_count=0
	local state_path
	local process_name
	local current_selinux=unavailable
	local current_irqbalance=unavailable
	local modules_present=0
	local devices_present=0
	local attempt

	if command -v getenforce >/dev/null 2>&1; then
		current_selinux="$(getenforce | tr '[:upper:]' '[:lower:]')"
	fi
	if [ "$current_selinux" != "$BOOT_INITIAL_SELINUX_MODE" ]; then
		echo "error: SELinux mode was not restored after boot validation." >&2
		echo "initial=$BOOT_INITIAL_SELINUX_MODE current=$current_selinux" >&2
		return 1
	fi
	printf 'SELinux mode restored: %s\n' "$current_selinux"
	if [ "$(cat /sys/devices/system/cpu/online)" != "$BOOT_INITIAL_CPU_ONLINE" ]; then
		echo 'error: CPU online mask was not restored after boot validation.' >&2
		echo "initial=$BOOT_INITIAL_CPU_ONLINE current=$(cat /sys/devices/system/cpu/online)" >&2
		return 1
	fi
	printf 'CPU online mask restored: %s\n' "$BOOT_INITIAL_CPU_ONLINE"
	if [ "$(cat /proc/sys/vm/swappiness)" != "$BOOT_INITIAL_SWAPPINESS" ]; then
		echo 'error: vm.swappiness was not restored after boot validation.' >&2
		echo "initial=$BOOT_INITIAL_SWAPPINESS current=$(cat /proc/sys/vm/swappiness)" >&2
		return 1
	fi
	printf 'vm.swappiness restored: %s\n' "$BOOT_INITIAL_SWAPPINESS"
	case "$BOOT_INITIAL_IRQBALANCE" in
	active|inactive)
		current_irqbalance="$(systemctl show -p ActiveState --value \
			irqbalance.service 2>/dev/null)" || {
			echo 'error: cannot determine the post-boot irqbalance active state.' >&2
			return 1
		}
		if [ "$current_irqbalance" != "$BOOT_INITIAL_IRQBALANCE" ]; then
			echo 'error: irqbalance active state was not restored after boot validation.' >&2
			echo "initial=$BOOT_INITIAL_IRQBALANCE current=$current_irqbalance" >&2
			return 1
		fi
		;;
	unavailable)
		;;
	esac
	printf 'irqbalance state restored: %s\n' "$BOOT_INITIAL_IRQBALANCE"
	while IFS=$'\t' read -r affinity_path expected_affinity; do
		if [ ! -r "$affinity_path" ]; then
			echo "error: baseline IRQ affinity path disappeared: $affinity_path" >&2
			return 1
		fi
		actual_affinity="$(cat "$affinity_path")"
		if [ "$actual_affinity" != "$expected_affinity" ]; then
			echo "error: IRQ affinity was not restored: $affinity_path" >&2
			echo "initial=$expected_affinity current=$actual_affinity" >&2
			return 1
		fi
		affinity_count=$((affinity_count + 1))
	done <"$BOOT_IRQ_AFFINITY_BEFORE"
	if [ "$affinity_count" -eq 0 ]; then
		echo 'error: IRQ affinity baseline is empty during cleanup verification.' >&2
		return 1
	fi
	printf 'IRQ affinity baseline restored: entries=%s\n' "$affinity_count"
	for state_path in \
		/run/systemd/system/irqbalance.service.d/mckernel.conf \
		/run/sysconfig/irqbalance_mck \
		/run/sysconfig/irqbalance_mck_affinities
	do
		if [ -e "$state_path" ] || [ -L "$state_path" ]; then
			echo "error: temporary McKernel irqbalance state remains: $state_path" >&2
			return 1
		fi
	done
	echo 'McKernel temporary irqbalance state after shutdown: none'
	for process_name in ihkmond mcexec; do
		if pgrep -x "$process_name" >/dev/null 2>&1; then
			echo "error: McKernel validation process remains after shutdown: $process_name" >&2
			pgrep -a -x "$process_name" >&2 || true
			return 1
		fi
	done
	echo 'McKernel validation processes after shutdown: none'
	if [ ! -r /proc/modules ]; then
		echo 'error: cannot verify unloaded modules because /proc/modules is unreadable.' >&2
		return 1
	fi

	if command -v udevadm >/dev/null 2>&1; then
		sudo udevadm settle --timeout=10 || true
	fi
	for attempt in {1..20}; do
		modules_present=0
		devices_present=0
		if grep -Eq '^(ihk|ihk_smp_x86_64|mcctrl) ' /proc/modules; then
			modules_present=1
		fi
		if compgen -G '/dev/mcd*' >/dev/null ||
			compgen -G '/dev/mcos*' >/dev/null
		then
			devices_present=1
		fi
		if [ "$modules_present" -eq 0 ] && [ "$devices_present" -eq 0 ]; then
			break
		fi
		sleep 0.25
	done

	if [ "$modules_present" -ne 0 ]; then
		echo 'error: IHK/McKernel modules remain loaded after mcstop+release.' >&2
		grep -E '^(ihk|ihk_smp_x86_64|mcctrl) ' /proc/modules >&2 || true
		return 1
	fi
	echo 'IHK/McKernel modules after shutdown: none'
	if [ "$devices_present" -ne 0 ]; then
		echo 'error: McKernel device nodes remain after mcstop+release.' >&2
		ls -l /dev/mcd* /dev/mcos* 2>/dev/null >&2 || true
		return 1
	fi
	echo 'McKernel device nodes after shutdown: none'

	echo 'guest-cleanup: OK'
}

boot_cleanup() {
	if [ "$BOOT_SHUTDOWN_NEEDED" -eq 1 ]; then
		run_privileged_lifecycle_cmd 'EXIT mcstop+release cleanup' \
			"$PREFIX/sbin/mcstop+release.sh" -k || true
	fi
	restore_selinux_after_boot || true
	restore_boot_environment || true
	preserve_boot_evidence || true
	cleanup_boot_evidence
}

confirm_boot_smoke() {
	if [ "$UNSAFE_HOST_BOOT" -ne 1 ]; then
		cat >&2 <<EOF
error: refusing to boot McKernel on the current host.

This path loads kernel modules, reserves CPU/memory, and can freeze or reboot
the machine if early boot fails. Use the recoverable QEMU/KVM wrapper instead:

  scripts/qemu-rocky-rust-validation.sh --image /path/to/rocky.qcow2 -- --boot-only

To intentionally run this unsafe path on the current host, add --unsafe-host-boot.
EOF
		exit 2
	fi

	cat <<EOF

About to load kernel modules, reserve CPU/memory, and boot McKernel inside this VM.
Take a VirtualBox snapshot first. If the VM hangs, power it off and restore the snapshot.
If SELinux is enforcing, this script will temporarily run 'setenforce 0' for
this boot only. It does not permanently edit /etc/selinux/config.

EOF
	if [ "$TRAMPOLINE_PHYS" != "" ]; then
		cat <<EOF
WARNING: --trampoline-phys assumes $TRAMPOLINE_PHYS was safely pre-reserved before boot.
Do not create that reservation with persistent grubby --update-kernel=ALL memmap arguments
on a validation VM. A bad low-memory reservation can stop the VM from booting.

EOF
	fi
	if [ "$ASSUME_YES" -eq 1 ]; then
		return
	fi

	cat <<EOF
Type 'yes' to continue:
EOF
	read -r answer
	if [ "$answer" != "yes" ]; then
		echo "Skipping boot smoke test."
		exit 0
	fi
}

wait_for_mckernel_boot() {
	local deadline=$((SECONDS + BOOT_TIMEOUT))
	local status=UNKNOWN

	while [ "$SECONDS" -lt "$deadline" ]; do
		local status_rc=0
		status="$(sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
			"$SMOKE_TIMEOUT" \
			"$PREFIX/sbin/ihkosctl" 0 get status 2>&1)" || status_rc=$?
		if is_timeout_status "$status_rc"; then
			echo "error: ihkosctl status exceeded the ${SMOKE_TIMEOUT}s watchdog (status ${status_rc})." >&2
			return 1
		fi
		status_rc=0
		sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
			"$SMOKE_TIMEOUT" \
			"$PREFIX/sbin/ihkosctl" 0 kmsg \
			>"$BOOT_KMSG" 2>/dev/null || status_rc=$?
		if is_timeout_status "$status_rc"; then
			echo "error: ihkosctl kmsg exceeded the ${SMOKE_TIMEOUT}s watchdog (status ${status_rc})." >&2
			return 1
		fi
		if [ "$status" = RUNNING ] &&
			grep -Fq "IHK/McKernel started." "$BOOT_KMSG" 2>/dev/null &&
			grep -Fq "IHK/McKernel booted." "$BOOT_KMSG" 2>/dev/null
		then
			printf 'McKernel status: %s\n' "$status"
			grep -F "IHK/McKernel started." "$BOOT_KMSG"
			grep -F "IHK/McKernel booted." "$BOOT_KMSG"
			return 0
		fi
		case "$status" in
			PANIC|HUNGUP|SHUTDOWN)
				echo "error: McKernel entered terminal status before boot completed: $status" >&2
				return 1
				;;
		esac
		sleep 1
	done

	echo "error: McKernel did not reach RUNNING with both Rust boot markers within ${BOOT_TIMEOUT}s; last status: $status" >&2
	return 1
}

preflight_fp0006_legacy_negative_dispatch() {
	local compile_rc=0
	local compiler_output
	local compiler_report
	local manifest
	local producer
	local resolved_head

	if [ "$FP0006_NEGATIVE_CAPTURE" -ne 1 ]; then
		return
	fi
	need_cmd git
	need_cmd sha256sum
	need_cmd python3
	if [ ! -x /usr/bin/gcc ] || [ -L /usr/bin/gcc ] ||
		[ "$(/usr/bin/rpm -qf --qf '%{NAME}\n' /usr/bin/gcc)" != gcc ] ||
		[ ! -x /usr/bin/timeout ] || [ -L /usr/bin/timeout ] ||
		[ "$(/usr/bin/rpm -qf --qf '%{NAME}\n' /usr/bin/timeout)" != coreutils ]
	then
		echo 'error: FP-0006 legacy producer requires the Rocky /usr/bin/gcc package binary.' >&2
		return 1
	fi
	resolved_head="$(git -C "$ROOT_DIR" rev-parse HEAD)"
	if [ "$resolved_head" != "$FP0006_CAPTURE_HEAD" ]; then
		echo 'error: FP-0006 preflight checkout differs from the requested exact head.' >&2
		return 1
	fi
	python3 "$ROOT_DIR/scripts/fp0006_runtime_capture_integration.py" \
		check-contract --repo "$ROOT_DIR"

	FP0006_PREFLIGHT_DIR="$(mktemp -d /tmp/fp0006-legacy-preflight.XXXXXX)"
	chmod 700 "$FP0006_PREFLIGHT_DIR"
	producer="$FP0006_PREFLIGHT_DIR/fp0006-legacy-producer"
	compiler_output="$FP0006_PREFLIGHT_DIR/compiler-output.log"
	compiler_report="$FP0006_PREFLIGHT_DIR/compiler-observation.txt"
	manifest="$RUNTIME_EVIDENCE_DIR/fp0006-legacy-preflight.json"
	test ! -e "$manifest"
	: >"$compiler_output"
	if /usr/bin/env -i HOME=/nonexistent LANG=C LC_ALL=C PATH=/usr/bin:/bin \
		/usr/bin/gcc -O2 -std=c11 -Wall -Wextra -Werror \
		"$ROOT_DIR/scripts/smoke/fp0006-ihk-device-negative-dispatch.c" \
		-o "$producer" >"$compiler_output" 2>&1
	then
		compile_rc=0
	else
		compile_rc=$?
	fi
	if [ "$compile_rc" -ne 0 ] || [ -s "$compiler_output" ]; then
		cat "$compiler_output" >&2
		echo "error: FP-0006 legacy producer compilation failed or emitted output (status $compile_rc)." >&2
		return 1
	fi
	{
		/usr/bin/rpm -q --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' gcc coreutils
		/usr/bin/sha256sum /usr/bin/gcc /usr/bin/timeout
		/usr/bin/gcc --version
		/usr/bin/timeout --version
	} >"$compiler_report"
	python3 "$ROOT_DIR/scripts/fp0006_runtime_capture_integration.py" \
		preflight-legacy \
		--repo "$ROOT_DIR" \
		--producer-binary "$producer" \
		--compiler-report "$compiler_report" \
		--compiler-output "$compiler_output" \
		--output-manifest "$manifest" \
		--head "$FP0006_CAPTURE_HEAD" \
		--github-repository "$FP0006_CAPTURE_REPOSITORY" \
		--github-run-id "$FP0006_CAPTURE_RUN_ID" \
		--github-run-attempt "$FP0006_CAPTURE_RUN_ATTEMPT" \
		--github-event-name "$FP0006_CAPTURE_EVENT_NAME" \
		--github-ref "$FP0006_CAPTURE_REF" \
		--github-sha "$FP0006_CAPTURE_GITHUB_SHA" \
		--github-workflow-sha "$FP0006_CAPTURE_WORKFLOW_SHA" \
		--github-base-sha "$FP0006_CAPTURE_BASE_SHA"
	FP0006_PREFLIGHT_MANIFEST="$manifest"
	FP0006_PREFLIGHT_MANIFEST_SHA256="$(sha256sum "$manifest" | awk '{ print $1 }')"
	FP0006_PRODUCER_BINARY="$producer"
	FP0006_PRODUCER_BINARY_SHA256="$(sha256sum "$producer" | awk '{ print $1 }')"
	FP0006_COMPILER_REPORT_SHA256="$(sha256sum "$compiler_report" | awk '{ print $1 }')"
	readonly FP0006_PREFLIGHT_DIR FP0006_PREFLIGHT_MANIFEST
	readonly FP0006_PREFLIGHT_MANIFEST_SHA256 FP0006_PRODUCER_BINARY
	readonly FP0006_PRODUCER_BINARY_SHA256 FP0006_COMPILER_REPORT_SHA256
	refresh_runtime_evidence_manifest
}

capture_fp0006_legacy_negative_dispatch() {
	local capture_rc=0
	local observation
	local overlay_host_driver_sha256
	local producer_log
	local producer_output
	local stage
	local workflow_candidate_aligned=false

	if [ "$FP0006_NEGATIVE_CAPTURE" -ne 1 ]; then
		return
	fi
	if [ "$(sha256sum "$FP0006_PREFLIGHT_MANIFEST" | awk '{ print $1 }')" !=
		"$FP0006_PREFLIGHT_MANIFEST_SHA256" ] ||
		[ "$(sha256sum "$FP0006_PRODUCER_BINARY" | awk '{ print $1 }')" !=
		"$FP0006_PRODUCER_BINARY_SHA256" ]
	then
		echo 'error: FP-0006 preflight authority or producer changed before live execution.' >&2
		return 1
	fi
	if [ ! -c /dev/mcd0 ]; then
		echo 'error: FP-0006 live capture requires the literal /dev/mcd0 character device.' >&2
		return 1
	fi
	overlay_host_driver_sha256="$(sha256sum \
		"$ROOT_DIR/ihk/linux/core/host_driver.c" | awk '{ print $1 }')"
	if [ "$overlay_host_driver_sha256" !=
		f677c7dde6de2160fd9062fa998cb2c4aa14ba9eafdac8b86b592b78776bcd2e ]
	then
		echo 'error: FP-0006 live compatibility-overlay observation digest differs.' >&2
		return 1
	fi
	stage="$FP0006_PREFLIGHT_DIR/capture-stage"
	producer_output="$FP0006_PREFLIGHT_DIR/producer-output.log"
	producer_log="$FP0006_PREFLIGHT_DIR/producer.log"
	observation="$RUNTIME_EVIDENCE_DIR/fp0006-legacy-observation"
	test ! -e "$stage"
	test ! -e "$observation"
	mkdir -m 700 "$stage"
	: >"$producer_output"
	if [ "$FP0006_CAPTURE_GITHUB_SHA" = "$FP0006_CAPTURE_HEAD" ] &&
		[ "$FP0006_CAPTURE_WORKFLOW_SHA" = "$FP0006_CAPTURE_HEAD" ]
	then
		workflow_candidate_aligned=true
	fi
	printf '{"base_sha":"%s","binary_sha256":"%s","device":"/dev/mcd0","event":"producer-start","event_name":"%s","github_sha":"%s","head_sha":"%s","normalized_command":["/usr/bin/env","-i","HOME=/nonexistent","LANG=C","LC_ALL=C","PATH=/usr/bin:/bin","/usr/bin/timeout","--signal=TERM","--kill-after=5s","30s","<producer-by-sha256>","/dev/mcd0","<capture-stage>"],"overlay_host_driver_sha256":"%s","preflight_sha256":"%s","ref":"%s","repository":"%s","run_attempt":%s,"run_id":%s,"surface":"legacy-live-ioctl","timeout_seconds":30,"tool_report_sha256":"%s","workflow_candidate_aligned":%s,"workflow_sha":"%s"}\n' \
		"$FP0006_CAPTURE_BASE_SHA" "$FP0006_PRODUCER_BINARY_SHA256" \
		"$FP0006_CAPTURE_EVENT_NAME" "$FP0006_CAPTURE_GITHUB_SHA" \
		"$FP0006_CAPTURE_HEAD" \
		"$overlay_host_driver_sha256" "$FP0006_PREFLIGHT_MANIFEST_SHA256" \
		"$FP0006_CAPTURE_REF" "$FP0006_CAPTURE_REPOSITORY" \
		"$FP0006_CAPTURE_RUN_ATTEMPT" "$FP0006_CAPTURE_RUN_ID" \
		"$FP0006_COMPILER_REPORT_SHA256" "$workflow_candidate_aligned" \
		"$FP0006_CAPTURE_WORKFLOW_SHA" >"$producer_log"
	/usr/bin/env -i HOME=/nonexistent LANG=C LC_ALL=C PATH=/usr/bin:/bin \
		/usr/bin/timeout --signal=TERM --kill-after=5s 30s \
		"$FP0006_PRODUCER_BINARY" /dev/mcd0 "$stage" \
		>"$producer_output" 2>&1 || capture_rc=$?
	{
		printf '{"event":"producer-output","output_bytes":%s,"output_sha256":"%s","surface":"legacy-live-ioctl"}\n' \
			"$(wc -c <"$producer_output")" \
			"$(sha256sum "$producer_output" | awk '{ print $1 }')"
		printf '{"event":"producer-exit","status":%s,"surface":"legacy-live-ioctl"}\n' \
			"$capture_rc"
	} >>"$producer_log"
	if [ "$capture_rc" -ne 0 ] || [ -s "$producer_output" ]; then
		cat "$producer_output" >&2
		echo "error: FP-0006 legacy producer failed or emitted unexpected output (status $capture_rc)." >&2
		return 1
	fi
	mkdir -m 700 "$observation"
	/usr/bin/tar --format=ustar --sort=name --owner=0 --group=0 \
		--numeric-owner --mtime=@0 --mode=0444 \
		-C "$stage" -cf "$observation/capture.tar" \
		raw.jsonl result.jsonl state-ledger.jsonl
	cp -- "$FP0006_PREFLIGHT_MANIFEST" "$observation/preflight.json"
	cp -- "$producer_log" "$observation/producer.log"
	cp -- "$FP0006_PREFLIGHT_DIR/compiler-observation.txt" \
		"$observation/tool-report.txt"
	cp -- "$FP0006_PREFLIGHT_DIR/compiler-output.log" \
		"$observation/compiler.log"
	cp -- "$producer_output" "$observation/producer-output.log"
	(
		cd "$observation"
		sha256sum capture.tar compiler.log preflight.json producer-output.log \
			producer.log tool-report.txt > SHA256SUMS
		chmod 0444 capture.tar compiler.log preflight.json producer-output.log \
			producer.log tool-report.txt SHA256SUMS
	)
	rm -f -- "$stage/raw.jsonl" "$stage/result.jsonl" \
		"$stage/state-ledger.jsonl" "$producer_output" "$producer_log" \
		"$FP0006_PREFLIGHT_DIR/compiler-output.log" \
		"$FP0006_PREFLIGHT_DIR/compiler-observation.txt" \
		"$FP0006_PRODUCER_BINARY"
	rmdir -- "$stage" "$FP0006_PREFLIGHT_DIR"
	refresh_runtime_evidence_manifest
	echo 'FP-0006 legacy negative-dispatch observation: captured-unreviewed-noncrediting'
}

boot_smoke() {
	BOOT_SHUTDOWN_NEEDED=0
	BOOT_RESTORE_SELINUX=0
	BOOT_RESTORE_ENVIRONMENT=0
	BOOT_INITIAL_SELINUX_MODE=unavailable
	BOOT_INITIAL_CPU_ONLINE=unavailable
	BOOT_INITIAL_SWAPPINESS=unavailable
	BOOT_INITIAL_IRQBALANCE=unavailable
	BOOT_DMESG_BASELINE_LINES=0
	BOOT_EVIDENCE_DIR=
	BOOT_DMESG_BEFORE=
	BOOT_DMESG_AFTER=
	BOOT_DMESG_DELTA=
	BOOT_KMSG=
	BOOT_BEFORE_WORKLOAD_KMSG=
	BOOT_AFTER_WORKLOAD_KMSG=
	BOOT_WORKLOAD_KMSG_DELTA=
	BOOT_FINAL_KMSG=
	BOOT_IRQ_AFFINITY_BEFORE=
	trap boot_cleanup EXIT

	if [ "$(nproc)" -lt 2 ]; then
		echo "error: boot smoke needs at least 2 vCPUs; CPU 0 stays with Linux and CPU $BOOT_CPUS goes to McKernel." >&2
		exit 1
	fi
	need_cmd getenforce
	need_cmd timeout
	need_cmd cmp
	need_cmd mktemp
	need_cmd numfmt
	need_cmd truncate
	if [ "$TRACE_SMOKE" -eq 1 ]; then
		need_cmd strace
	fi
	BOOT_EVIDENCE_DIR="$(mktemp -d /tmp/mckernel-boot-validation.XXXXXX)"
	chmod 700 "$BOOT_EVIDENCE_DIR"
	BOOT_DMESG_BEFORE="$BOOT_EVIDENCE_DIR/linux-dmesg-before.log"
	BOOT_DMESG_AFTER="$BOOT_EVIDENCE_DIR/linux-dmesg-after.log"
	BOOT_DMESG_DELTA="$BOOT_EVIDENCE_DIR/linux-dmesg-delta.log"
	BOOT_KMSG="$BOOT_EVIDENCE_DIR/mckernel-boot.kmsg"
	BOOT_BEFORE_WORKLOAD_KMSG="$BOOT_EVIDENCE_DIR/mckernel-before-workload.kmsg"
	BOOT_AFTER_WORKLOAD_KMSG="$BOOT_EVIDENCE_DIR/mckernel-after-workload.kmsg"
	BOOT_WORKLOAD_KMSG_DELTA="$BOOT_EVIDENCE_DIR/mckernel-workload-delta.kmsg"
	BOOT_FINAL_KMSG="$BOOT_EVIDENCE_DIR/mckernel-final.kmsg"
	BOOT_IRQ_AFFINITY_BEFORE="$BOOT_EVIDENCE_DIR/linux-irq-affinity-before.tsv"

	confirm_boot_smoke
	capture_boot_environment
	ensure_selinux_permissive_for_boot

	say "Booting McKernel"
	say "Cleaning stale McKernel state before boot"
	BOOT_RESTORE_ENVIRONMENT=1
	if ! run_privileged_lifecycle_cmd "stale-state cleanup" \
		"$PREFIX/sbin/mcstop+release.sh" -k
	then
		echo "error: stale McKernel state could not be cleaned before boot." >&2
		echo "A previous V10 hang may still have an OS instance or module reference open." >&2
		echo "Safest recovery in the Rocky VM is a reboot, then rerun this script." >&2
		dump_boot_failure_state
		exit 1
	fi

	BOOT_SHUTDOWN_NEEDED=1
	say "Using safe_kernel_map for bounded validation memory mapping"
	if [ "$TRAMPOLINE_PHYS" != "" ]; then
		say "Using reserved IHK trampoline page at $TRAMPOLINE_PHYS"
		if ! run_privileged_lifecycle_cmd "mcreboot" \
			env IHK_TRAMPOLINE_PHYS="$TRAMPOLINE_PHYS" \
			"$PREFIX/sbin/mcreboot.sh" -s -c "$BOOT_CPUS" -m "$BOOT_MEM" \
			-o "$BOOT_DEVICE_OWNER"; then
			dump_boot_failure_state
			exit 1
		fi
	else
		if ! run_privileged_lifecycle_cmd "mcreboot" \
			"$PREFIX/sbin/mcreboot.sh" -s -c "$BOOT_CPUS" -m "$BOOT_MEM" \
			-o "$BOOT_DEVICE_OWNER"; then
			dump_boot_failure_state
			exit 1
		fi
	fi

	say "Checking McKernel boot log"
	if ! wait_for_mckernel_boot; then
		dump_boot_failure_state
		exit 1
	fi
	if ! record_live_boot_evidence; then
		dump_boot_failure_state
		exit 1
	fi
	capture_fp0006_legacy_negative_dispatch

	if [ "$BOOT_ONLY" -eq 1 ]; then
		say "Boot-only check requested; skipping mcexec workloads"
		run_privileged_lifecycle_cmd "mcstop+release" \
			"$PREFIX/sbin/mcstop+release.sh"
		echo 'mcstop+release: OK'
		restore_selinux_after_boot
		restore_boot_environment
		verify_boot_cleanup
		verify_boot_dmesg
		emit_raw_boot_evidence
		preserve_boot_evidence
		BOOT_SHUTDOWN_NEEDED=0
		cleanup_boot_evidence
		trap - EXIT
		return
	fi

	local smoke_rc=0

	if ! capture_workload_kmsg_baseline; then
		dump_smoke_failure_state 'pre-workload-kmsg'
		return 1
	fi
	say "Running mcexec smoke commands"
	run_smoke_cmd "mcexec-true" "$PREFIX/bin/mcexec" /bin/true
	run_hostname_smoke || smoke_rc=$?
	if [ "$smoke_rc" -eq 124 ]; then
		return "$smoke_rc"
	fi
	run_smoke_cmd "mcexec-rust-workload" \
		"$PREFIX/bin/mcexec" "$BUILD_DIR/mcexec-rust-smoke"
	if ! grep -Fxq \
		'mckernel-rust-smoke: OK bytes=1048576 sum=133693440' \
		/tmp/mckernel-mcexec-rust-workload.out; then
		echo "error: deterministic mcexec workload output did not match." >&2
		dump_smoke_failure_state "mcexec-rust-workload"
		return 1
	fi
	say "Checking deterministic-workload Rust-path and delegated-syscall markers"
	if ! verify_workload_runtime_markers; then
		dump_smoke_failure_state 'rust-runtime-markers'
		return 1
	fi
	run_smoke_cmd "mcstat" "$PREFIX/bin/mcstat"
	if ! verify_post_workload_health; then
		dump_smoke_failure_state 'post-workload-health'
		return 1
	fi

	say "Shutting down McKernel"
	run_privileged_lifecycle_cmd "mcstop+release" \
		"$PREFIX/sbin/mcstop+release.sh"
	echo 'mcstop+release: OK'
	restore_selinux_after_boot
	restore_boot_environment
	verify_boot_cleanup
	verify_boot_dmesg
	emit_raw_boot_evidence
	preserve_boot_evidence
	BOOT_SHUTDOWN_NEEDED=0
	cleanup_boot_evidence
	trap - EXIT

	if [ "$smoke_rc" -ne 0 ]; then
		echo "error: V10 smoke completed with diagnostics, but the VDSO-enabled hostname check failed with status ${smoke_rc}." >&2
		return "$smoke_rc"
	fi
}

run_hostname_smoke() {
	local rc=0

	if run_smoke_cmd "mcexec-hostname" "$PREFIX/bin/mcexec" hostname; then
		if run_smoke_cmd "mcexec-hostname-absolute" "$PREFIX/bin/mcexec" /usr/bin/hostname; then
			return 0
		else
			rc=$?
		fi
	else
		rc=$?
	fi

	if [ "$rc" -eq 124 ]; then
		return "$rc"
	fi

	say "Retrying mcexec-hostname with VDSO disabled"
	if run_smoke_cmd "mcexec-hostname-novdso" "$PREFIX/bin/mcexec" --disable-vdso hostname; then
		echo "diagnosis: relative hostname passes with --disable-vdso; VDSO remains implicated for argv0=hostname." >&2
	else
		local retry_rc=$?
		if [ "$retry_rc" -eq 124 ]; then
			return "$retry_rc"
		fi
		echo "diagnosis: relative hostname also fails with --disable-vdso; the failure is not isolated to VDSO." >&2
	fi
	if run_smoke_cmd "mcexec-hostname-absolute-novdso" "$PREFIX/bin/mcexec" --disable-vdso /usr/bin/hostname; then
		echo "diagnosis: absolute-path hostname also passes with --disable-vdso." >&2
	else
		local retry_rc=$?
		if [ "$retry_rc" -eq 124 ]; then
			return "$retry_rc"
		fi
		echo "diagnosis: absolute-path hostname still fails with --disable-vdso; argv0/path-sensitive loader or stack setup is also implicated." >&2
	fi

	return "$rc"
}

print_smoke_log() {
	local log="$1"

	if [ "$VERBOSE_SMOKE" -eq 1 ]; then
		cat "$log"
	else
		tail -n "$SMOKE_LOG_TAIL_LINES" "$log"
	fi
}

run_smoke_cmd() {
	local label="$1"
	shift
	local log="/tmp/mckernel-${label}.out"
	local trace_prefix="/tmp/mckernel-${label}.strace"
	local rc=0
	local pid
	local cmd=("$@")

	if [ "$DEBUG_MCEXEC" -eq 1 ]; then
		case "${cmd[0]}" in
			*/mcexec|mcexec)
				cmd=("${cmd[0]}" --debug-mcexec "${cmd[@]:1}")
				;;
		esac
	fi

	rm -f "$trace_prefix" "$trace_prefix".*
	if [ "$TRACE_SMOKE" -eq 1 ]; then
		cmd=(strace -ff -tt -s 200 -o "$trace_prefix" "${cmd[@]}")
	fi

	say "Running ${label} with ${SMOKE_TIMEOUT}s watchdog"
	timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" \
		"$SMOKE_TIMEOUT" "${cmd[@]}" >"$log" 2>&1 &
	pid=$!
	echo "watchdog: ${label} timeout wrapper started as pid ${pid}; log=${log}" >&2
	wait "$pid" || rc=$?
	if is_timeout_status "$rc"; then
		echo "error: ${label} exceeded the ${SMOKE_TIMEOUT}s watchdog (status ${rc})." >&2
		echo "Captured output from ${label}:" >&2
		print_smoke_log "$log" >&2 || true
		if [ "$TRACE_SMOKE" -eq 1 ]; then
			echo "Recent strace output for ${label}:" >&2
			tail -n "$STRACE_TAIL_LINES" "$trace_prefix"* >&2 || true
		fi
		dump_smoke_failure_state "$label"
		run_privileged_lifecycle_cmd 'smoke-timeout mcstop+release cleanup' \
			"$PREFIX/sbin/mcstop+release.sh" -k 2>/dev/null || true
		return 124
	fi

	if [ "$rc" -eq 0 ]; then
		if [ -s "$log" ]; then
			cat "$log"
		fi
		echo "${label}: OK"
		return 0
	fi

	echo "error: ${label} failed or timed out with status ${rc}." >&2
	echo "Captured output from ${label}:" >&2
	print_smoke_log "$log" >&2 || true
	if [ "$TRACE_SMOKE" -eq 1 ]; then
		echo "Recent strace output for ${label}:" >&2
		tail -n "$STRACE_TAIL_LINES" "$trace_prefix"* >&2 || true
	fi
	dump_smoke_failure_state "$label"
	return "$rc"
}

dump_boot_failure_state() {
	echo "Linux process state after boot failure:" >&2
	ps -eo pid,ppid,stat,wchan:32,comm,args | grep -E 'mcexec|mcstat|strace|ihkmond' | grep -v grep >&2 || true
	echo "Loaded McKernel/IHK modules:" >&2
	lsmod | grep -E '^(ihk|ihk_smp_x86_64|mcctrl)\b' >&2 || true
	echo "McKernel device nodes:" >&2
	ls -l /dev/mcd* /dev/mcos* 2>/dev/null >&2 || true
	echo "Recent Linux dmesg:" >&2
	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" 5s \
		dmesg --ctime | tail -n "$DMESG_TAIL_LINES" >&2 || true
}

dump_smoke_failure_state() {
	local label="$1"
	local dump_count="${SMOKE_FAILURE_DUMP_COUNT:-0}"

	echo "Linux process state after ${label} failure:" >&2
	ps -eo pid,ppid,stat,wchan:32,comm,args | grep -E 'mcexec|mcstat|timeout|strace' | grep -v grep >&2 || true

	local pids
	pids="$(pgrep -x mcexec 2>/dev/null || true)"
	for pid in $pids; do
		echo "--- /proc/${pid}/status ---" >&2
		sed -n '1,80p' "/proc/${pid}/status" >&2 || true
		echo "--- /proc/${pid}/wchan ---" >&2
		cat "/proc/${pid}/wchan" >&2 || true
		echo "--- /proc/${pid}/stack ---" >&2
		sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" 2s \
			cat "/proc/${pid}/stack" >&2 || true
	done

	if [ "$dump_count" -eq 0 ]; then
		echo "Recent Linux dmesg:" >&2
		sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" 5s \
			dmesg --ctime | tail -n "$DMESG_TAIL_LINES" >&2 || true
		echo "Recent McKernel kmsg:" >&2
		sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" 5s \
			"$PREFIX/sbin/ihkosctl" 0 kmsg | tail -n "$KMSG_TAIL_LINES" >&2 || true
	else
		echo "Skipping repeated Linux dmesg and McKernel kmsg dump for ${label}; see the first smoke failure above." >&2
	fi
	echo "McKernel V10 handoff markers:" >&2
	sudo timeout --signal=TERM --kill-after="$TIMEOUT_KILL_AFTER" 5s \
		"$PREFIX/sbin/ihkosctl" 0 kmsg | \
		grep 'mcexec_v10: \(argenv\|auxv\|initial_stack\|prepared\|fatal\|signal_default\)' | \
		tail -n "$V10_TAIL_LINES" >&2 || true
	SMOKE_FAILURE_DUMP_COUNT=$((dump_count + 1))
}

need_cmd sudo
need_cmd uname
initialize_runtime_evidence

if [ "$INSTALL_DEPS" -eq 1 ]; then
	install_deps
fi

ensure_kernel_headers
ensure_libuedev

# Make a rustup-managed compiler visible even when --skip-rust forbids changing
# the installed toolchains or default.
# shellcheck disable=SC1091
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"

if [ "$INSTALL_RUST" -eq 1 ]; then
	ensure_rust
else
	need_cmd rustc
	export RUSTUP_TOOLCHAIN="$RUST_TOOLCHAIN"
	verify_rustc
fi

preflight_fp0006_legacy_negative_dispatch
update_submodules
record_environment
configure_and_build

if [ "$SOURCE_RETIREMENT_AUDIT" -eq 1 ]; then
	source_retirement_audit
fi

if [ "$MODULE_LOAD_SMOKE" -eq 1 ]; then
	module_load_smoke
fi

if [ "$DO_INSTALL" -eq 1 ]; then
	install_artifacts
fi

record_runtime_provenance

if [ "$BOOT_SMOKE" -eq 1 ]; then
	boot_smoke
else
	say "Build validation complete"
	echo "Install prefix: $PREFIX"
	echo "Run with --module-load-smoke --yes to load/unload C IHK host modules plus Rust-linked mcctrl."
	echo "Run with --boot-smoke --yes after taking a VM snapshot to boot and run mcexec smoke tests."
fi
