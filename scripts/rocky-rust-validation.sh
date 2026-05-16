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
  --boot-only           After install, boot McKernel and check kmsg; skip workloads.
  --boot-smoke          After install, boot McKernel and run mcexec smoke tests.
  --yes                 Allow boot validation without an interactive confirmation.
  --prefix PATH         Install prefix. Default: /opt/mckernel-rust
  --build-dir PATH      CMake build directory. Default: /tmp/mckernel-rocky-rust
  --jobs N              Parallel build jobs. Default: 2
  --boot-cpus LIST      CPU list passed to mcreboot.sh -c. Default: 1
  --boot-mem SPEC       Memory passed to mcreboot.sh -m. Default: 512M@0
  --trampoline-phys PA  Expert-only: pass pre-reserved PA to mcreboot.sh.
  -h, --help            Show this help.

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
INSTALL_DEPS=1
INSTALL_RUST=1
DO_INSTALL=1
BOOT_ONLY=0
BOOT_SMOKE=0
ASSUME_YES=0

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
		--boot-only)
			BOOT_ONLY=1
			BOOT_SMOKE=1
			shift
			;;
		--boot-smoke)
			BOOT_SMOKE=1
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
KERNEL_DIR="/lib/modules/$(uname -r)/build"

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
		gcc gcc-c++ make cmake git tar patch diffutils which curl \
		"kernel-devel-$(uname -r)" "kernel-headers-$(uname -r)" \
		elfutils-libelf-devel numactl-devel rpm-build binutils-devel systemd-devel \
		zlib-devel openssl-devel bc bison flex perl dwarves
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

	rustup toolchain install nightly
	rustup default nightly

	if ! rustc --version | grep -q nightly; then
		echo "error: rustc is not nightly after rustup setup." >&2
		rustc --version >&2 || true
		exit 1
	fi
	rustc --version
}

update_submodules() {
	say "Initializing submodules"
	git -C "$ROOT_DIR" submodule update --init --recursive

	local ihk_patch="$ROOT_DIR/scripts/patches/ihk-linux-compat.patch"
	if [ -f "$ihk_patch" ]; then
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
		-DBUILD_TARGET=smp-x86 \
		-DENABLE_RUST_KERNEL=ON \
		-DCMAKE_INSTALL_PREFIX="$PREFIX" \
		-DKERNEL_DIR="$KERNEL_DIR"

	say "Building McKernel, host modules, and smoke-test user tools"
	cmake --build "$BUILD_DIR" \
		--target mckernel.img ihk_ko ihk-smp-x86_64_ko mcctrl_ko \
		mcexec eclair mcinspect sched_yield ldump2mcdump mcstat \
		ihkconfig ihkosctl ihkmond \
		-j"$JOBS"
}

install_artifacts() {
	say "Installing into $PREFIX"
	sudo cmake --install "$BUILD_DIR"
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
}

confirm_boot_smoke() {
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

boot_smoke() {
	if [ "$(nproc)" -lt 2 ]; then
		echo "error: boot smoke needs at least 2 vCPUs; CPU 0 stays with Linux and CPU $BOOT_CPUS goes to McKernel." >&2
		exit 1
	fi

	confirm_boot_smoke
	ensure_selinux_permissive_for_boot

	say "Booting McKernel"
	if [ "$TRAMPOLINE_PHYS" != "" ]; then
		say "Using reserved IHK trampoline page at $TRAMPOLINE_PHYS"
		sudo IHK_TRAMPOLINE_PHYS="$TRAMPOLINE_PHYS" \
			"$PREFIX/sbin/mcreboot.sh" -c "$BOOT_CPUS" -m "$BOOT_MEM"
	else
		sudo "$PREFIX/sbin/mcreboot.sh" -c "$BOOT_CPUS" -m "$BOOT_MEM"
	fi

	shutdown_needed=1
	cleanup() {
		if [ "${shutdown_needed:-0}" -eq 1 ]; then
			sudo "$PREFIX/sbin/mcstop+release.sh" || true
		fi
	}
	trap cleanup EXIT

	say "Checking McKernel boot log"
	sudo "$PREFIX/sbin/ihkosctl" 0 kmsg | tee /tmp/mckernel.kmsg
	grep "IHK/McKernel booted" /tmp/mckernel.kmsg

	if [ "$BOOT_ONLY" -eq 1 ]; then
		say "Boot-only check requested; skipping mcexec workloads"
		sudo "$PREFIX/sbin/mcstop+release.sh"
		shutdown_needed=0
		trap - EXIT
		return
	fi

	say "Running mcexec smoke commands"
	"$PREFIX/bin/mcexec" /bin/true
	echo "mcexec /bin/true: OK"
	"$PREFIX/bin/mcexec" hostname
	"$PREFIX/bin/mcstat"

	say "Shutting down McKernel"
	sudo "$PREFIX/sbin/mcstop+release.sh"
	shutdown_needed=0
	trap - EXIT
}

need_cmd sudo
need_cmd uname

if [ "$INSTALL_DEPS" -eq 1 ]; then
	install_deps
fi

ensure_kernel_headers
ensure_libuedev

if [ "$INSTALL_RUST" -eq 1 ]; then
	ensure_rust
else
	need_cmd rustc
	rustc --version | grep -q nightly || {
		echo "error: ENABLE_RUST_KERNEL requires nightly rustc." >&2
		exit 1
	}
fi

update_submodules
configure_and_build

if [ "$DO_INSTALL" -eq 1 ]; then
	install_artifacts
fi

if [ "$BOOT_SMOKE" -eq 1 ]; then
	boot_smoke
else
	say "Build validation complete"
	echo "Install prefix: $PREFIX"
	echo "Run with --boot-smoke --yes after taking a VM snapshot to boot and run mcexec smoke tests."
fi
