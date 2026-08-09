#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'USAGE'
Usage:
  scripts/rocky-v11-prereqs.sh [options]

Builds the external Rocky V11 prerequisites that are intentionally not bundled
in this tree:
  - LTP installed under $HOME/ltp by default
  - XPMEM source/build under $HOME/xpmem by default
  - XPMEM install under $HOME/usr by default

Options:
  --skip-deps             Do not install Rocky/RHEL-family OS packages.
  --skip-ltp              Do not fetch or build LTP.
  --skip-xpmem            Do not fetch or build XPMEM.
  --ltp-only              Fetch/build only LTP.
  --xpmem-only            Fetch/build only XPMEM.
  --update                Fetch from origin before building existing repos.
  --validate-only         Only validate the expected output paths.
  --jobs N                Parallel build jobs. Default: nproc.
  --ltp-url URL           LTP git URL. Default: https://github.com/linux-test-project/ltp.git
  --ltp-src PATH          LTP source checkout. Default: $HOME/ltp-src
  --ltp-prefix PATH       LTP install prefix. Default: $HOME/ltp
  --xpmem-url URL         XPMEM git URL. Default: https://github.com/hpc/xpmem.git
  --xpmem-src PATH        XPMEM source/build checkout. Default: $HOME/xpmem
  --xpmem-prefix PATH     XPMEM install prefix. Default: $HOME/usr
  -h, --help              Show this help.

After this completes, rerun:
  scripts/rocky-v11-focused.sh --timeout 120
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOBS="$(nproc)"
INSTALL_DEPS=1
BUILD_LTP=1
BUILD_XPMEM=1
UPDATE_REPOS=0
VALIDATE_ONLY=0

LTP_URL="${LTP_URL:-https://github.com/linux-test-project/ltp.git}"
LTP_SRC="${LTP_SRC:-$HOME/ltp-src}"
LTP_PREFIX="${LTP_PREFIX:-${LTP:-$HOME/ltp}}"
XPMEM_URL="${XPMEM_URL:-https://github.com/hpc/xpmem.git}"
XPMEM_SRC="${XPMEM_SRC:-${XPMEM_BUILD_DIR:-$HOME/xpmem}}"
XPMEM_PREFIX="${XPMEM_PREFIX:-${XPMEM_DIR:-$HOME/usr}}"
KERNEL_DIR="${KERNEL_DIR:-/lib/modules/$(uname -r)/build}"

LTP_REQUIRED_TESTS="${LTP_REQUIRED_TESTS:-futex_wait01 futex_wait02 futex_wait03 futex_wait04 futex_wait_bitset01 futex_wait_bitset02 futex_wake01 futex_wake02 futex_wake03 process_vm01 time01 fork01}"

while [ "$#" -gt 0 ]; do
	case "$1" in
		--skip-deps)
			INSTALL_DEPS=0
			shift
			;;
		--skip-ltp)
			BUILD_LTP=0
			shift
			;;
		--skip-xpmem)
			BUILD_XPMEM=0
			shift
			;;
		--ltp-only)
			BUILD_LTP=1
			BUILD_XPMEM=0
			shift
			;;
		--xpmem-only)
			BUILD_LTP=0
			BUILD_XPMEM=1
			shift
			;;
		--update)
			UPDATE_REPOS=1
			shift
			;;
		--validate-only)
			VALIDATE_ONLY=1
			shift
			;;
		--jobs)
			JOBS="${2:?missing value for --jobs}"
			shift 2
			;;
		--ltp-url)
			LTP_URL="${2:?missing value for --ltp-url}"
			shift 2
			;;
		--ltp-src)
			LTP_SRC="${2:?missing value for --ltp-src}"
			shift 2
			;;
		--ltp-prefix)
			LTP_PREFIX="${2:?missing value for --ltp-prefix}"
			shift 2
			;;
		--xpmem-url)
			XPMEM_URL="${2:?missing value for --xpmem-url}"
			shift 2
			;;
		--xpmem-src)
			XPMEM_SRC="${2:?missing value for --xpmem-src}"
			shift 2
			;;
		--xpmem-prefix)
			XPMEM_PREFIX="${2:?missing value for --xpmem-prefix}"
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
	say "Installing Rocky/RHEL-family packages for LTP and XPMEM"
	sudo dnf install -y dnf-plugins-core
	sudo dnf config-manager --set-enabled powertools >/dev/null 2>&1 || \
		sudo dnf config-manager --set-enabled crb >/dev/null 2>&1 || true

	sudo dnf install -y \
		git gcc gcc-c++ make automake autoconf libtool m4 pkgconf-pkg-config \
		bison flex perl findutils file patch diffutils which \
		"kernel-devel-$(uname -r)" "kernel-headers-$(uname -r)"

	if ! sudo dnf install -y \
		acl-devel attr-devel libaio-devel libcap-devel keyutils-libs-devel \
		libtirpc-devel numactl-devel openssl-devel xfsprogs-devel quota-devel; then
		echo "warning: one or more optional LTP development packages were unavailable." >&2
		echo "LTP configure will disable tests that cannot be built in this environment." >&2
	fi
}

ensure_kernel_headers() {
	say "Checking matching kernel build directory"
	if [ ! -d "$KERNEL_DIR" ]; then
		echo "error: missing kernel build directory: $KERNEL_DIR" >&2
		echo "Install kernel-devel-$(uname -r) and kernel-headers-$(uname -r)." >&2
		exit 1
	fi
	if [ ! -f "$KERNEL_DIR/Makefile" ]; then
		echo "error: $KERNEL_DIR does not look like a kernel build tree." >&2
		exit 1
	fi
}

clone_or_update() {
	local url="$1"
	local dir="$2"

	if [ -d "$dir/.git" ]; then
		say "Using existing checkout $dir"
		if [ "$UPDATE_REPOS" -eq 1 ]; then
			git -C "$dir" fetch --tags origin
			git -C "$dir" pull --ff-only
		fi
		git -C "$dir" submodule update --init --recursive
		return
	fi

	if [ -e "$dir" ]; then
		echo "error: $dir exists but is not a git checkout." >&2
		exit 1
	fi

	mkdir -p "$(dirname "$dir")"
	git clone --recurse-submodules "$url" "$dir"
}

build_ltp() {
	say "Building LTP into $LTP_PREFIX"
	clone_or_update "$LTP_URL" "$LTP_SRC"
	(
		cd "$LTP_SRC"
		if [ ! -x ./configure ]; then
			make autotools
		fi
		./configure --prefix="$LTP_PREFIX"
		make -j"$JOBS"
		make install
	)
}

build_xpmem() {
	say "Building XPMEM into $XPMEM_PREFIX"
	clone_or_update "$XPMEM_URL" "$XPMEM_SRC"
	(
		cd "$XPMEM_SRC"
		if [ ! -x ./configure ]; then
			./autogen.sh
		fi

		local_args=(--prefix="$XPMEM_PREFIX" --with-module-prefix="$XPMEM_PREFIX")
		if ./configure --help | grep -q -- '--with-linux'; then
			local_args+=(--with-linux="$KERNEL_DIR")
		fi
		if ./configure --help | grep -q -- '--with-kernel'; then
			local_args+=(--with-kernel="$KERNEL_DIR")
		fi

		./configure "${local_args[@]}"
		make -j"$JOBS"
		make install
	)
}

validate_ltp() {
	local missing=0
	local tp

	say "Validating LTP install at $LTP_PREFIX"
	for tp in $LTP_REQUIRED_TESTS; do
		if [ ! -x "$LTP_PREFIX/testcases/bin/$tp" ]; then
			echo "missing LTP test: $LTP_PREFIX/testcases/bin/$tp" >&2
			missing=1
		fi
	done
	if [ "$missing" -ne 0 ]; then
		return 1
	fi
	echo "READY: LTP tests found in $LTP_PREFIX/testcases/bin"
}

validate_xpmem() {
	local missing=0
	local module="$XPMEM_PREFIX/lib/modules/$(uname -r)/xpmem.ko"

	say "Validating XPMEM install at $XPMEM_PREFIX"
	if [ ! -f "$module" ]; then
		echo "missing XPMEM module: $module" >&2
		missing=1
	fi
	if [ ! -f "$XPMEM_PREFIX/include/xpmem.h" ]; then
		echo "missing XPMEM header: $XPMEM_PREFIX/include/xpmem.h" >&2
		missing=1
	fi
	if [ ! -f "$XPMEM_PREFIX/lib/libxpmem.so" ] && [ ! -f "$XPMEM_PREFIX/lib64/libxpmem.so" ]; then
		echo "missing XPMEM shared library under $XPMEM_PREFIX/lib or $XPMEM_PREFIX/lib64" >&2
		missing=1
	fi
	if [ ! -d "$XPMEM_SRC/test" ]; then
		echo "missing XPMEM userspace tests: $XPMEM_SRC/test" >&2
		missing=1
	fi
	if [ "$missing" -ne 0 ]; then
		return 1
	fi
	echo "READY: XPMEM module, headers, library, and userspace tests found"
}

need_cmd sudo
need_cmd uname

if [ "$VALIDATE_ONLY" -eq 0 ] && [ "$INSTALL_DEPS" -eq 1 ]; then
	install_deps
fi

need_cmd git
need_cmd make
ensure_kernel_headers

if [ "$VALIDATE_ONLY" -eq 0 ] && [ "$BUILD_LTP" -eq 1 ]; then
	build_ltp
fi

if [ "$VALIDATE_ONLY" -eq 0 ] && [ "$BUILD_XPMEM" -eq 1 ]; then
	build_xpmem
fi

rc=0
if [ "$BUILD_LTP" -eq 1 ]; then
	validate_ltp || rc=1
fi
if [ "$BUILD_XPMEM" -eq 1 ]; then
	validate_xpmem || rc=1
fi

cat <<EOF

Rocky V11 prerequisite paths:
  LTP=$LTP_PREFIX
  LTPBIN=$LTP_PREFIX/testcases/bin
  XPMEM_DIR=$XPMEM_PREFIX
  XPMEM_BUILD_DIR=$XPMEM_SRC

Next gate:
  scripts/rocky-v11-focused.sh --timeout 120
EOF

exit "$rc"
