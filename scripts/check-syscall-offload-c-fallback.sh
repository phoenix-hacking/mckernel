#!/usr/bin/env bash
set -euo pipefail

# Compile-time test oracle for the retained C implementation of the x86_64
# syscall-offload seam.  This script never selects the fallback for production;
# it builds a separate image and proves that no Rust offload owner leaked into
# that image.

usage() {
	cat <<'USAGE'
Usage:
  scripts/check-syscall-offload-c-fallback.sh \
    --build-dir PATH [--kernel-dir PATH] [--jobs N] [--evidence PATH]

Options:
  --build-dir PATH  Dedicated C-fallback CMake build directory (required).
  --kernel-dir PATH Linux kernel build tree used while configuring McKernel.
                    Required unless --verify-only is selected.
  --jobs N          Parallel build jobs. Default: 2.
  --evidence PATH   Output report inside BUILD_DIR. Default: BUILD_DIR/kernel/
                    mckernel-syscall-offload-c-fallback.txt.
  --verify-only     Inspect an already-populated build directory without
                    invoking CMake. Intended for focused checker tests.
  -h, --help        Show this help.
USAGE
}

die() {
	echo "error: $*" >&2
	exit 1
}

need_cmd() {
	command -v "$1" >/dev/null 2>&1 ||
		die "required command not found: $1"
}

require_cache_bool() {
	local name=$1
	local expected=$2
	local cache=$3

	grep -Fxq "${name}:BOOL=${expected}" "$cache" ||
		die "$name is not exactly $expected in $cache"
}

require_exact_text_symbol() {
	local table=$1
	local symbol=$2
	local expected_type=$3
	local total
	local matching

	total="$(awk -v symbol="$symbol" '$1 == symbol { count++ } END { print count + 0 }' "$table")"
	matching="$(awk -v symbol="$symbol" -v type="$expected_type" \
		'$1 == symbol && $2 == type { count++ } END { print count + 0 }' "$table")"
	if [ "$total" -ne 1 ] || [ "$matching" -ne 1 ]; then
		die "expected exactly one $expected_type definition of $symbol in $table"
	fi
}

reject_symbol() {
	local table=$1
	local symbol=$2

	if awk -v symbol="$symbol" '$1 == symbol { found = 1 } END { exit found ? 0 : 1 }' "$table"; then
		die "forbidden Rust syscall-offload symbol leaked into fallback: $symbol"
	fi
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR=
KERNEL_DIR=
JOBS=2
EVIDENCE=
VERIFY_ONLY=0

while [ "$#" -gt 0 ]; do
	case "$1" in
		--build-dir)
			BUILD_DIR="${2:?missing value for --build-dir}"
			shift 2
			;;
		--kernel-dir)
			KERNEL_DIR="${2:?missing value for --kernel-dir}"
			shift 2
			;;
		--jobs)
			JOBS="${2:?missing value for --jobs}"
			shift 2
			;;
		--evidence)
			EVIDENCE="${2:?missing value for --evidence}"
			shift 2
			;;
		--verify-only)
			VERIFY_ONLY=1
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			die "unknown option: $1"
			;;
	esac
done

[ -n "$BUILD_DIR" ] || die "--build-dir is required"
case "$JOBS" in
	''|*[!0-9]*) die "--jobs must be a positive integer" ;;
esac
[ "$JOBS" -gt 0 ] || die "--jobs must be a positive integer"

need_cmd awk
need_cmd grep
need_cmd nm
need_cmd python3
need_cmd sha256sum
need_cmd strings

BUILD_DIR="$(python3 - "$BUILD_DIR" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)"
case "$BUILD_DIR" in
	/|"$ROOT_DIR"|"$ROOT_DIR"/*)
		die "refusing unsafe or in-source build directory: $BUILD_DIR"
		;;
esac

if [ "$VERIFY_ONLY" -eq 0 ]; then
	need_cmd cmake
	need_cmd make
	[ -n "$KERNEL_DIR" ] || die "--kernel-dir is required for a build"
	[ -f "$KERNEL_DIR/Makefile" ] ||
		die "$KERNEL_DIR is not a Linux kernel build tree"

	if [ -s "$KERNEL_DIR/include/config/kernel.release" ]; then
		KERNEL_RELEASE="$(tr -d '[:space:]' < \
			"$KERNEL_DIR/include/config/kernel.release")"
	else
		KERNEL_RELEASE="$(make -s -C "$KERNEL_DIR" kernelrelease)"
	fi
	case "$KERNEL_RELEASE" in
		[0-9]*.[0-9]*.[0-9]*) ;;
		*) die "could not derive a kernel release from $KERNEL_DIR" ;;
	esac

	cmake -S "$ROOT_DIR" \
		-B "$BUILD_DIR" \
		-Wno-dev \
		-DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
		-DBUILD_TARGET=smp-x86 \
		-DENABLE_RUST_KERNEL=OFF \
		-DENABLE_RUST_IHK_MODULE_HELPERS=OFF \
		-DENABLE_RUST_USER_TOOLS=OFF \
		-DCMAKE_INSTALL_PREFIX="$BUILD_DIR/install" \
		-DUNAME_R="$KERNEL_RELEASE" \
		-DKERNEL_DIR="$KERNEL_DIR"
	cmake --build "$BUILD_DIR" --target mckernel.img -j"$JOBS"
fi

CACHE="$BUILD_DIR/CMakeCache.txt"
COMPILE_DB="$BUILD_DIR/compile_commands.json"
SYSCALL_OBJECT="$BUILD_DIR/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o"
IMAGE="$BUILD_DIR/kernel/mckernel.img"
LINK_MAP="$BUILD_DIR/kernel/mckernel.img.map"

[ -s "$CACHE" ] || die "missing CMake cache: $CACHE"
[ -s "$COMPILE_DB" ] || die "missing compile database: $COMPILE_DB"
[ -s "$SYSCALL_OBJECT" ] || die "missing fallback syscall object: $SYSCALL_OBJECT"
[ -s "$IMAGE" ] || die "missing fallback image: $IMAGE"
[ -s "$LINK_MAP" ] || die "missing fallback link map: $LINK_MAP"

require_cache_bool ENABLE_RUST_KERNEL OFF "$CACHE"
require_cache_bool ENABLE_RUST_IHK_MODULE_HELPERS OFF "$CACHE"
require_cache_bool ENABLE_RUST_USER_TOOLS OFF "$CACHE"

python3 - "$COMPILE_DB" "$ROOT_DIR/kernel/syscall.c" <<'PY'
import json
import os
import shlex
import sys

database_path, source_path = sys.argv[1:]
with open(database_path, "r") as stream:
    database = json.load(stream)

source_path = os.path.realpath(source_path)
matches = []
for entry in database:
    candidate = entry.get("file", "")
    if not os.path.isabs(candidate):
        candidate = os.path.join(entry.get("directory", ""), candidate)
    if os.path.realpath(candidate) == source_path:
        matches.append(entry)

if len(matches) != 1:
    raise SystemExit(
        "error: expected exactly one kernel/syscall.c compile entry, found %d"
        % len(matches)
    )

entry = matches[0]
arguments = entry.get("arguments")
if arguments is None:
    arguments = shlex.split(entry.get("command", ""))

forbidden = (
    "MCKERNEL_RUST_SYSCALL_OFFLOAD",
    "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS",
)
for argument in arguments:
    if any(name in argument for name in forbidden):
        raise SystemExit(
            "error: forbidden Rust syscall-offload define in fallback compile: %s"
            % argument
        )
print("fallback syscall compile entry: C owners selected")
PY

grep -Fq 'CMakeFiles/mckernel.img.dir/syscall.c.o' "$LINK_MAP" ||
	die "fallback syscall object is absent from the final link map"
if grep -Fq 'mckernel_rust.o' "$LINK_MAP"; then
	die "Rust kernel object leaked into the fallback link map"
fi
if grep -Fq 'abi_checks.c.o' "$LINK_MAP"; then
	die "Rust ABI-check object leaked into the fallback link map"
fi

OBJECT_NM="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.object.nm"
IMAGE_NM="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.image.nm"
IMAGE_UNDEFINED="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.undefined.nm"
OBJECT_STRINGS="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.object.strings"

LC_ALL=C nm -a --format=posix "$SYSCALL_OBJECT" > "$OBJECT_NM"
LC_ALL=C nm -a --format=posix "$IMAGE" > "$IMAGE_NM"
LC_ALL=C nm -u --format=posix "$IMAGE" > "$IMAGE_UNDEFINED"
LC_ALL=C strings "$SYSCALL_OBJECT" > "$OBJECT_STRINGS"

require_exact_text_symbol "$OBJECT_NM" do_syscall T
require_exact_text_symbol "$OBJECT_NM" send_syscall t
require_exact_text_symbol "$OBJECT_NM" syscall_generic_forwarding T
reject_symbol "$OBJECT_NM" syscall_offload_wait_reply
reject_symbol "$OBJECT_NM" syscall_dispatch_context_bridge

require_exact_text_symbol "$IMAGE_NM" do_syscall T
require_exact_text_symbol "$IMAGE_NM" send_syscall t
require_exact_text_symbol "$IMAGE_NM" syscall_generic_forwarding T
reject_symbol "$IMAGE_NM" syscall_offload_wait_reply
reject_symbol "$IMAGE_NM" syscall_dispatch_context_bridge

if [ -s "$IMAGE_UNDEFINED" ]; then
	die "fallback image contains unresolved symbols"
fi
grep -Fq 'mcexec_v10: send_syscall cpu=' "$OBJECT_STRINGS" ||
	die "C syscall-offload marker is absent from the fallback object"
if grep -Fq 'owner=rust' "$OBJECT_STRINGS"; then
	die "Rust ownership marker leaked into the fallback object"
fi

if [ -z "$EVIDENCE" ]; then
	EVIDENCE="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.txt"
else
	EVIDENCE="$(python3 - "$EVIDENCE" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)"
fi
case "$EVIDENCE" in
	"$BUILD_DIR"/*) ;;
	*) die "--evidence must remain inside --build-dir" ;;
esac
mkdir -p "$(dirname "$EVIDENCE")"
EVIDENCE_TMP="${EVIDENCE}.tmp.$$"
trap 'rm -f "$EVIDENCE_TMP"' EXIT
{
	printf 'schema=mckernel-syscall-offload-c-fallback-v1\n'
	printf 'mode=test-oracle-only\n'
	printf 'production_selection=unchanged\n'
	printf 'enable_rust_kernel=OFF\n'
	printf 'enable_rust_ihk_module_helpers=OFF\n'
	printf 'enable_rust_user_tools=OFF\n'
	printf 'syscall_compile_owner=C\n'
	printf 'symbol.do_syscall=T\n'
	printf 'symbol.send_syscall=t\n'
	printf 'symbol.syscall_generic_forwarding=T\n'
	printf 'symbol.syscall_offload_wait_reply=absent\n'
	printf 'symbol.syscall_dispatch_context_bridge=absent\n'
	printf 'rust_kernel_object=absent\n'
	printf 'rust_owner_marker=absent\n'
	printf 'image_undefined_symbols=0\n'
	printf 'syscall_object_sha256=%s\n' \
		"$(sha256sum "$SYSCALL_OBJECT" | awk '{ print $1 }')"
	printf 'image_sha256=%s\n' \
		"$(sha256sum "$IMAGE" | awk '{ print $1 }')"
	printf 'link_map_sha256=%s\n' \
		"$(sha256sum "$LINK_MAP" | awk '{ print $1 }')"
	printf 'status=PASS\n'
} > "$EVIDENCE_TMP"
mv "$EVIDENCE_TMP" "$EVIDENCE"
trap - EXIT

cat "$EVIDENCE"
