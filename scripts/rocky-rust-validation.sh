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
  --verbose-smoke       Enable mcexec debug output and full smoke logs.
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
TRACE_SMOKE=0
VERBOSE_SMOKE=0
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
		--verbose-smoke)
			VERBOSE_SMOKE=1
			shift
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
	require_undefined_symbol "$mcexec_c" mcexec_finish_main_image_body

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
		return
	fi

	local mode
	mode="$(getenforce | tr '[:upper:]' '[:lower:]')"
	if [ "$mode" != "enforcing" ]; then
		return
	fi

	if ! command -v setenforce >/dev/null 2>&1; then
		echo "error: SELinux is enforcing and setenforce is unavailable." >&2
		echo "Temporarily set SELinux permissive before boot validation." >&2
		exit 1
	fi

	say "Temporarily setting SELinux permissive for McKernel boot validation"
	sudo setenforce 0
	BOOT_RESTORE_SELINUX=1
}

restore_selinux_after_boot() {
	if [ "$BOOT_RESTORE_SELINUX" -eq 1 ]; then
		say "Restoring SELinux enforcing mode"
		sudo setenforce 1
		BOOT_RESTORE_SELINUX=0
	fi
}

boot_cleanup() {
	if [ "$BOOT_SHUTDOWN_NEEDED" -eq 1 ]; then
		sudo "$PREFIX/sbin/mcstop+release.sh" -k || true
	fi
	restore_selinux_after_boot || true
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
		status="$(sudo "$PREFIX/sbin/ihkosctl" 0 get status 2>&1 || true)"
		sudo "$PREFIX/sbin/ihkosctl" 0 kmsg >/tmp/mckernel.kmsg 2>/dev/null || true
		if [ "$status" = RUNNING ] &&
			grep -Fq "IHK/McKernel started." /tmp/mckernel.kmsg 2>/dev/null &&
			grep -Fq "IHK/McKernel booted." /tmp/mckernel.kmsg 2>/dev/null
		then
			printf 'McKernel status: %s\n' "$status"
			grep -F "IHK/McKernel started." /tmp/mckernel.kmsg
			grep -F "IHK/McKernel booted." /tmp/mckernel.kmsg
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

boot_smoke() {
	BOOT_SHUTDOWN_NEEDED=0
	BOOT_RESTORE_SELINUX=0
	trap boot_cleanup EXIT

	if [ "$(nproc)" -lt 2 ]; then
		echo "error: boot smoke needs at least 2 vCPUs; CPU 0 stays with Linux and CPU $BOOT_CPUS goes to McKernel." >&2
		exit 1
	fi
	need_cmd setsid
	if [ "$TRACE_SMOKE" -eq 1 ]; then
		need_cmd strace
	fi

	confirm_boot_smoke
	ensure_selinux_permissive_for_boot

	say "Booting McKernel"
	say "Cleaning stale McKernel state before boot"
	if ! sudo "$PREFIX/sbin/mcstop+release.sh" -k; then
		echo "error: stale McKernel state could not be cleaned before boot." >&2
		echo "A previous V10 hang may still have an OS instance or module reference open." >&2
		echo "Safest recovery in the Rocky VM is a reboot, then rerun this script." >&2
		dump_boot_failure_state
		exit 1
	fi

	BOOT_SHUTDOWN_NEEDED=1
	if [ "$TRAMPOLINE_PHYS" != "" ]; then
		say "Using reserved IHK trampoline page at $TRAMPOLINE_PHYS"
		if ! sudo IHK_TRAMPOLINE_PHYS="$TRAMPOLINE_PHYS" \
			"$PREFIX/sbin/mcreboot.sh" -c "$BOOT_CPUS" -m "$BOOT_MEM" \
			-o "$BOOT_DEVICE_OWNER"; then
			dump_boot_failure_state
			exit 1
		fi
	else
		if ! sudo "$PREFIX/sbin/mcreboot.sh" -c "$BOOT_CPUS" -m "$BOOT_MEM" \
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

	if [ "$BOOT_ONLY" -eq 1 ]; then
		say "Boot-only check requested; skipping mcexec workloads"
		sudo "$PREFIX/sbin/mcstop+release.sh"
		BOOT_SHUTDOWN_NEEDED=0
		restore_selinux_after_boot
		trap - EXIT
		return
	fi

	local smoke_rc=0

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
	run_smoke_cmd "mcstat" "$PREFIX/bin/mcstat"

	say "Checking Rust userspace handoff and delegated-syscall markers"
	sudo "$PREFIX/sbin/ihkosctl" 0 kmsg >/tmp/mckernel-after-smoke.kmsg
	local marker
	for marker in \
		'mcexec_v10: prepared ' \
		'mcexec_v10: schedule_process queued ' \
		'mcexec_v10: enter_user ' \
		'mcexec_v10: send_syscall ' \
		'mcexec_v10: offload_return '
	do
		if ! grep -Fq "$marker" /tmp/mckernel-after-smoke.kmsg; then
			echo "error: missing Rust-path runtime marker: $marker" >&2
			dump_smoke_failure_state "rust-runtime-markers"
			return 1
		fi
	done

	say "Shutting down McKernel"
	sudo "$PREFIX/sbin/mcstop+release.sh"
	BOOT_SHUTDOWN_NEEDED=0
	restore_selinux_after_boot
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
		echo "diagnosis: relative hostname also fails with --disable-vdso; the failure is not isolated to VDSO." >&2
	fi
	if run_smoke_cmd "mcexec-hostname-absolute-novdso" "$PREFIX/bin/mcexec" --disable-vdso /usr/bin/hostname; then
		echo "diagnosis: absolute-path hostname also passes with --disable-vdso." >&2
	else
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
	local elapsed=0
	local cmd=("$@")

	if [ "$VERBOSE_SMOKE" -eq 1 ]; then
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
	"${cmd[@]}" >"$log" 2>&1 &
	pid=$!
	echo "watchdog: ${label} started as pid ${pid}; log=${log}" >&2

	while kill -0 "$pid" 2>/dev/null; do
		if [ "$elapsed" -ge "$SMOKE_TIMEOUT" ]; then
			echo "error: ${label} exceeded the ${SMOKE_TIMEOUT}s watchdog." >&2
			echo "Captured output from ${label}:" >&2
			print_smoke_log "$log" >&2 || true
			if [ "$TRACE_SMOKE" -eq 1 ]; then
				echo "Recent strace output for ${label}:" >&2
				tail -n "$STRACE_TAIL_LINES" "$trace_prefix"* >&2 || true
			fi
			dump_smoke_failure_state "$label"
			echo "Attempting to terminate ${label} pid ${pid} and direct children." >&2
			pkill -TERM -P "$pid" 2>/dev/null || true
			kill -TERM "$pid" 2>/dev/null || true
			sleep 2
			pkill -KILL -P "$pid" 2>/dev/null || true
			kill -KILL "$pid" 2>/dev/null || true
			disown "$pid" 2>/dev/null || true
			sudo "$PREFIX/sbin/mcstop+release.sh" -k 2>/dev/null || true
			return 124
		fi
		sleep 1
		elapsed=$((elapsed + 1))
	done

	wait "$pid" || rc=$?

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
	sudo dmesg --ctime | tail -n "$DMESG_TAIL_LINES" >&2 || true
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
		if command -v timeout >/dev/null 2>&1; then
			timeout 2s sudo cat "/proc/${pid}/stack" >&2 || true
		else
			sudo cat "/proc/${pid}/stack" >&2 || true
		fi
	done

	if [ "$dump_count" -eq 0 ]; then
		echo "Recent Linux dmesg:" >&2
		sudo dmesg --ctime | tail -n "$DMESG_TAIL_LINES" >&2 || true
		echo "Recent McKernel kmsg:" >&2
		if command -v timeout >/dev/null 2>&1; then
			timeout 5s sudo "$PREFIX/sbin/ihkosctl" 0 kmsg | tail -n "$KMSG_TAIL_LINES" >&2 || true
		else
			sudo "$PREFIX/sbin/ihkosctl" 0 kmsg | tail -n "$KMSG_TAIL_LINES" >&2 || true
		fi
	else
		echo "Skipping repeated Linux dmesg and McKernel kmsg dump for ${label}; see the first smoke failure above." >&2
	fi
	echo "McKernel V10 handoff markers:" >&2
	if command -v timeout >/dev/null 2>&1; then
		timeout 5s sudo "$PREFIX/sbin/ihkosctl" 0 kmsg | grep 'mcexec_v10: \(argenv\|auxv\|initial_stack\|prepared\|fatal\|signal_default\)' | tail -n "$V10_TAIL_LINES" >&2 || true
	else
		sudo "$PREFIX/sbin/ihkosctl" 0 kmsg | grep 'mcexec_v10: \(argenv\|auxv\|initial_stack\|prepared\|fatal\|signal_default\)' | tail -n "$V10_TAIL_LINES" >&2 || true
	fi
	SMOKE_FAILURE_DUMP_COUNT=$((dump_count + 1))
}

need_cmd sudo
need_cmd uname

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

if [ "$BOOT_SMOKE" -eq 1 ]; then
	boot_smoke
else
	say "Build validation complete"
	echo "Install prefix: $PREFIX"
	echo "Run with --module-load-smoke --yes to load/unload C IHK host modules plus Rust-linked mcctrl."
	echo "Run with --boot-smoke --yes after taking a VM snapshot to boot and run mcexec smoke tests."
fi
