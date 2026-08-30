#!/usr/bin/env bash
set -euo pipefail

# Compile-time oracle for the retained C implementation of the x86_64
# syscall-offload seam.  The production build stays Rust-enabled.  This script
# replays only kernel/syscall.c's exact production compiler argv after removing
# the single MCKERNEL_RUST_SYSCALL_OFFLOAD selection define, then inspects the
# resulting standalone object.  It does not build or select an all-C kernel.

usage() {
	cat <<'USAGE'
Usage:
  scripts/check-syscall-offload-c-fallback.sh \
    --build-dir PATH --production-build-dir PATH [--evidence PATH]

Options:
  --build-dir PATH             Dedicated output directory for the standalone
                               C-fallback object and evidence (required).
  --production-build-dir PATH  Completed Rust production build whose exact
                               kernel/syscall.c compiler argv is replayed.
                               Required unless --verify-only is selected.
  --evidence PATH              Output report inside BUILD_DIR. Default:
                               BUILD_DIR/kernel/
                               mckernel-syscall-offload-c-fallback.txt.
  --verify-only                Inspect an already-populated fixture without
                               invoking the compiler.
  -h, --help                   Show this help.
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
PRODUCTION_BUILD_DIR=
EVIDENCE=
VERIFY_ONLY=0

while [ "$#" -gt 0 ]; do
	case "$1" in
		--build-dir)
			BUILD_DIR="${2:?missing value for --build-dir}"
			shift 2
			;;
		--production-build-dir)
			PRODUCTION_BUILD_DIR="${2:?missing value for --production-build-dir}"
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
		die "refusing unsafe or in-source output directory: $BUILD_DIR"
		;;
esac

if [ "$VERIFY_ONLY" -eq 1 ]; then
	[ -n "$PRODUCTION_BUILD_DIR" ] ||
		PRODUCTION_BUILD_DIR="$BUILD_DIR"
else
	[ -n "$PRODUCTION_BUILD_DIR" ] ||
		die "--production-build-dir is required"
fi
PRODUCTION_BUILD_DIR="$(python3 - "$PRODUCTION_BUILD_DIR" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)"

PRODUCTION_CACHE="$PRODUCTION_BUILD_DIR/CMakeCache.txt"
PRODUCTION_COMPILE_DB="$PRODUCTION_BUILD_DIR/compile_commands.json"
SYSCALL_OBJECT="$BUILD_DIR/kernel/syscall.c-fallback.o"
COMPILE_METADATA="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.compile.json"

[ -s "$PRODUCTION_CACHE" ] ||
	die "missing production CMake cache: $PRODUCTION_CACHE"
[ -s "$PRODUCTION_COMPILE_DB" ] ||
	die "missing production compile database: $PRODUCTION_COMPILE_DB"
require_cache_bool ENABLE_RUST_KERNEL ON "$PRODUCTION_CACHE"

if [ "$VERIFY_ONLY" -eq 0 ]; then
	mkdir -p "$BUILD_DIR/kernel"
	python3 - \
		"$PRODUCTION_COMPILE_DB" \
		"$ROOT_DIR/kernel/syscall.c" \
		"$SYSCALL_OBJECT" \
		"$COMPILE_METADATA" <<'PY'
import json
import os
import shlex
import subprocess
import sys

database_path, source_path, object_path, metadata_path = sys.argv[1:]
source_path = os.path.realpath(source_path)
with open(database_path, "r") as stream:
    database = json.load(stream)

matches = []
for entry in database:
    candidate = entry.get("file", "")
    if not os.path.isabs(candidate):
        candidate = os.path.join(entry.get("directory", ""), candidate)
    if os.path.realpath(candidate) == source_path:
        matches.append(entry)
if len(matches) != 1:
    raise SystemExit(
        "error: expected exactly one production kernel/syscall.c compile "
        "entry, found %d" % len(matches)
    )

entry = matches[0]
production_arguments = entry.get("arguments")
if production_arguments is None:
    production_arguments = shlex.split(entry.get("command", ""))
production_arguments = list(production_arguments)
if not production_arguments:
    raise SystemExit("error: production compile argv is empty")
directory = entry.get("directory") or os.getcwd()
source_arguments = 0
for argument in production_arguments:
    if argument.startswith("-"):
        continue
    candidate = argument
    if not os.path.isabs(candidate):
        candidate = os.path.join(directory, candidate)
    if os.path.realpath(candidate) == source_path:
        source_arguments += 1
if source_arguments != 1:
    raise SystemExit(
        "error: expected exactly one kernel/syscall.c source argument, "
        "found %d" % source_arguments
    )

offload = "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
policy = "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS"
offload_count = sum(
    argument == offload or argument.startswith(offload + "=")
    for argument in production_arguments
)
policy_count = sum(
    argument == policy or argument.startswith(policy + "=")
    for argument in production_arguments
)
if offload_count != 1:
    raise SystemExit(
        "error: expected exactly one production syscall-offload define, "
        "found %d" % offload_count
    )
if policy_count != 1:
    raise SystemExit(
        "error: expected exactly one retained syscall-policy-helper define, "
        "found %d" % policy_count
    )

fallback_arguments = []
output_count = 0
index = 0
while index < len(production_arguments):
    argument = production_arguments[index]
    if argument == offload or argument.startswith(offload + "="):
        index += 1
        continue
    if argument in ("-MD", "-MMD", "-MP"):
        index += 1
        continue
    if argument in ("-MF", "-MT", "-MQ"):
        if index + 1 >= len(production_arguments):
            raise SystemExit("error: truncated dependency option: %s" % argument)
        index += 2
        continue
    if (
        argument.startswith("-MF")
        or argument.startswith("-MT")
        or argument.startswith("-MQ")
    ) and len(argument) > 3:
        index += 1
        continue
    if argument == "-o":
        if index + 1 >= len(production_arguments):
            raise SystemExit("error: truncated compiler output option")
        fallback_arguments.extend(["-o", object_path])
        output_count += 1
        index += 2
        continue
    if argument.startswith("-o") and len(argument) > 2:
        fallback_arguments.append("-o" + object_path)
        output_count += 1
        index += 1
        continue
    fallback_arguments.append(argument)
    index += 1

if output_count != 1:
    raise SystemExit(
        "error: expected exactly one production compiler output, found %d"
        % output_count
    )
if any(
    argument == offload or argument.startswith(offload + "=")
    for argument in fallback_arguments
):
    raise SystemExit("error: syscall-offload define survived fallback replay")
if not any(
    argument == policy or argument.startswith(policy + "=")
    for argument in fallback_arguments
):
    raise SystemExit("error: syscall-policy-helper define was not retained")

os.makedirs(os.path.dirname(object_path), exist_ok=True)
print("fallback compiler argv: %s" % " ".join(
    shlex.quote(argument) for argument in fallback_arguments
))
result = subprocess.call(fallback_arguments, cwd=directory)
if result != 0:
    raise SystemExit(result)

metadata = {
    "schema": "mckernel-syscall-offload-c-fallback-compile-v2",
    "source": source_path,
    "production_directory": os.path.realpath(directory),
    "production_arguments": production_arguments,
    "fallback_arguments": fallback_arguments,
    "removed_defines": ["MCKERNEL_RUST_SYSCALL_OFFLOAD"],
    "retained_defines": ["MCKERNEL_RUST_SYSCALL_POLICY_HELPERS"],
}
with open(metadata_path, "w") as stream:
    json.dump(metadata, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
fi

[ -s "$SYSCALL_OBJECT" ] ||
	die "missing standalone fallback syscall object: $SYSCALL_OBJECT"
[ -s "$COMPILE_METADATA" ] ||
	die "missing fallback compile metadata: $COMPILE_METADATA"

python3 - "$COMPILE_METADATA" "$ROOT_DIR/kernel/syscall.c" <<'PY'
import json
import os
import sys

metadata_path, source_path = sys.argv[1:]
with open(metadata_path, "r") as stream:
    metadata = json.load(stream)
if metadata.get("schema") != "mckernel-syscall-offload-c-fallback-compile-v2":
    raise SystemExit("error: fallback compile metadata schema mismatch")
if os.path.realpath(metadata.get("source", "")) != os.path.realpath(source_path):
    raise SystemExit("error: fallback compile source mismatch")
if metadata.get("removed_defines") != ["MCKERNEL_RUST_SYSCALL_OFFLOAD"]:
    raise SystemExit("error: fallback did not remove exactly the offload define")
if metadata.get("retained_defines") != [
    "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS"
]:
    raise SystemExit("error: fallback policy-helper retention mismatch")

offload = "-DMCKERNEL_RUST_SYSCALL_OFFLOAD"
policy = "-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS"
production = metadata.get("production_arguments", [])
fallback = metadata.get("fallback_arguments", [])
if sum(arg == offload or arg.startswith(offload + "=") for arg in production) != 1:
    raise SystemExit("error: production compile selection is not Rust offload")
if any(arg == offload or arg.startswith(offload + "=") for arg in fallback):
    raise SystemExit("error: forbidden Rust syscall-offload define in fallback compile")
if not any(arg == policy or arg.startswith(policy + "=") for arg in fallback):
    raise SystemExit("error: syscall-policy-helper define missing from fallback compile")
print("fallback syscall compile entry: C offload owners selected in one object")
PY

OBJECT_NM="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.object.nm"
OBJECT_STRINGS="$BUILD_DIR/kernel/mckernel-syscall-offload-c-fallback.object.strings"
LC_ALL=C nm -a --format=posix "$SYSCALL_OBJECT" > "$OBJECT_NM"
LC_ALL=C strings "$SYSCALL_OBJECT" > "$OBJECT_STRINGS"

require_exact_text_symbol "$OBJECT_NM" do_syscall T
require_exact_text_symbol "$OBJECT_NM" send_syscall t
require_exact_text_symbol "$OBJECT_NM" syscall_generic_forwarding T
reject_symbol "$OBJECT_NM" syscall_offload_wait_reply
reject_symbol "$OBJECT_NM" syscall_dispatch_context_bridge

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
	printf 'schema=mckernel-syscall-offload-c-fallback-v2\n'
	printf 'mode=compile-object-oracle-only\n'
	printf 'production_selection=unchanged\n'
	printf 'production_rust_kernel=ON\n'
	printf 'replayed_from_production_compile=true\n'
	printf 'fallback_scope=kernel/syscall.c-only\n'
	printf 'removed_define=MCKERNEL_RUST_SYSCALL_OFFLOAD\n'
	printf 'retained_define=MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'
	printf 'rust_policy_helpers=enabled\n'
	printf 'final_image_link_claimed=false\n'
	printf 'runtime_equivalence_claimed=false\n'
	printf 'symbol.do_syscall=T\n'
	printf 'symbol.send_syscall=t\n'
	printf 'symbol.syscall_generic_forwarding=T\n'
	printf 'symbol.syscall_offload_wait_reply=absent\n'
	printf 'symbol.syscall_dispatch_context_bridge=absent\n'
	printf 'rust_owner_marker=absent\n'
	printf 'source_sha256=%s\n' \
		"$(sha256sum "$ROOT_DIR/kernel/syscall.c" | awk '{ print $1 }')"
	printf 'production_compile_database_sha256=%s\n' \
		"$(sha256sum "$PRODUCTION_COMPILE_DB" | awk '{ print $1 }')"
	printf 'fallback_compile_metadata_sha256=%s\n' \
		"$(sha256sum "$COMPILE_METADATA" | awk '{ print $1 }')"
	printf 'syscall_object_sha256=%s\n' \
		"$(sha256sum "$SYSCALL_OBJECT" | awk '{ print $1 }')"
	printf 'status=PASS\n'
} > "$EVIDENCE_TMP"
mv "$EVIDENCE_TMP" "$EVIDENCE"
trap - EXIT

cat "$EVIDENCE"
