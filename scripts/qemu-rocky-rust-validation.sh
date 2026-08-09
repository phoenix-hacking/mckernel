#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'USAGE'
Usage:
  scripts/qemu-rocky-rust-validation.sh --image IMAGE [qemu options] [-- validation options]

Runs scripts/rocky-rust-validation.sh inside a disposable QEMU/KVM guest. This
is the recoverable path for McKernel boot validation: the backing image is not
modified, the host repo is staged into the guest overlay, serial output is
logged, and a host-side watchdog terminates QEMU if the guest wedges.

Default validation options:
  --boot-smoke --yes

Common examples:
  scripts/qemu-rocky-rust-validation.sh --image rocky8.qcow2
  scripts/qemu-rocky-rust-validation.sh --image rocky8.qcow2 -- --boot-smoke --skip-deps --skip-rust

QEMU options:
  --image PATH              Required qcow2 backing image. Must not be a /dev path.
  --source-dir PATH         Repository tree staged into the guest. Default: the
                            repository containing this trusted wrapper.
  --accel MODE              auto, kvm, or tcg. Default: auto
  --ssh-port PORT           Host port forwarded to guest SSH. Default: 2222
  --memory SIZE             QEMU memory. Default: 4096M
  --cpus N                  QEMU vCPU count. Default: 4
  --ssh-timeout SEC         Guest SSH wait timeout. Default: 300
  --guest-timeout SEC       Watchdog for the validation command. Default: 7200
  --log-dir PATH            QEMU log directory. Default: qemu runner default
  --pause-at-reset          Start QEMU paused at reset for first-instruction
                            GDB/monitor inspection. Use with --gdb PORT.
  --gdb PORT                Open a QEMU GDB stub on 127.0.0.1:PORT.
  --keep-overlay            Keep the temporary qcow2 overlay after exit.
  --keep-running            Leave QEMU running after the command completes.
  --dry-run                 Print the QEMU command without starting the guest.
  -h, --help                Show this help.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QEMU_RUNNER="$ROOT_DIR/scripts/qemu-mckernel-guest.sh"
SOURCE_DIR="$ROOT_DIR"

IMAGE=
ACCEL=auto
SSH_PORT=2222
MEMORY=4096M
CPUS=4
SSH_TIMEOUT=300
GUEST_TIMEOUT=7200
LOG_DIR=
PAUSE_AT_RESET=0
GDB_PORT=
KEEP_OVERLAY=0
KEEP_RUNNING=0
DRY_RUN=0
VALIDATION_ARGS=()

while [ "$#" -gt 0 ]; do
	case "$1" in
		--image)
			IMAGE="${2:?missing value for --image}"
			shift 2
			;;
		--source-dir)
			SOURCE_DIR="${2:?missing value for --source-dir}"
			shift 2
			;;
		--accel)
			ACCEL="${2:?missing value for --accel}"
			shift 2
			;;
		--ssh-port)
			SSH_PORT="${2:?missing value for --ssh-port}"
			shift 2
			;;
		--memory)
			MEMORY="${2:?missing value for --memory}"
			shift 2
			;;
		--cpus)
			CPUS="${2:?missing value for --cpus}"
			shift 2
			;;
		--ssh-timeout)
			SSH_TIMEOUT="${2:?missing value for --ssh-timeout}"
			shift 2
			;;
		--guest-timeout)
			GUEST_TIMEOUT="${2:?missing value for --guest-timeout}"
			shift 2
			;;
		--log-dir)
			LOG_DIR="${2:?missing value for --log-dir}"
			shift 2
			;;
		--pause-at-reset)
			PAUSE_AT_RESET=1
			shift
			;;
		--gdb)
			GDB_PORT="${2:?missing value for --gdb}"
			shift 2
			;;
		--keep-overlay)
			KEEP_OVERLAY=1
			shift
			;;
		--keep-running)
			KEEP_RUNNING=1
			shift
			;;
		--dry-run)
			DRY_RUN=1
			shift
			;;
		--)
			shift
			VALIDATION_ARGS=("$@")
			break
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "error: unknown QEMU option: $1" >&2
			echo "Pass rocky-rust-validation.sh options after --" >&2
			usage >&2
			exit 2
			;;
	esac
done

if [ -z "$IMAGE" ]; then
	echo "error: --image is required" >&2
	usage >&2
	exit 2
fi

if [ ! -d "$SOURCE_DIR" ]; then
	echo "error: --source-dir is not a directory: $SOURCE_DIR" >&2
	exit 2
fi
SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
if [ ! -x "$SOURCE_DIR/scripts/rocky-rust-validation.sh" ]; then
	echo "error: source tree is missing executable scripts/rocky-rust-validation.sh: $SOURCE_DIR" >&2
	exit 2
fi

if [ "${#VALIDATION_ARGS[@]}" -eq 0 ]; then
	VALIDATION_ARGS=(--boot-smoke --yes)
fi

quote_args() {
	local arg
	for arg in "$@"; do
		printf '%q ' "$arg"
	done
}

has_validation_arg() {
	local want="$1"
	local arg

	for arg in "${VALIDATION_ARGS[@]}"; do
		if [ "$arg" = "$want" ]; then
			return 0
		fi
	done
	return 1
}

if { has_validation_arg --boot-only || has_validation_arg --boot-smoke; } &&
	! has_validation_arg --unsafe-host-boot; then
	VALIDATION_ARGS+=(--unsafe-host-boot)
fi

if ! has_validation_arg --yes; then
	VALIDATION_ARGS+=(--yes)
fi

validation_cmd=$(
	printf 'cd /tmp/mckernel-hostshare && '
	printf './scripts/rocky-rust-validation.sh '
	quote_args "${VALIDATION_ARGS[@]}"
)

qemu_args=(
	--image "$IMAGE"
	--accel "$ACCEL"
	--ssh-port "$SSH_PORT"
	--memory "$MEMORY"
	--cpus "$CPUS"
	--timeout "$SSH_TIMEOUT"
	--guest-cmd-timeout "$GUEST_TIMEOUT"
	--guest-cleanup-timeout 30
	--stage-dir "$SOURCE_DIR:/tmp/mckernel-hostshare"
	--guest-cmd "$validation_cmd"
)

if [ -n "$LOG_DIR" ]; then
	qemu_args+=(--log-dir "$LOG_DIR")
fi
if [ "$PAUSE_AT_RESET" -eq 1 ]; then
	qemu_args+=(--pause-at-reset)
fi
if [ -n "$GDB_PORT" ]; then
	qemu_args+=(--gdb "$GDB_PORT")
fi
if [ "$KEEP_OVERLAY" -eq 1 ]; then
	qemu_args+=(--keep-overlay)
fi
if [ "$KEEP_RUNNING" -eq 1 ]; then
	qemu_args+=(--keep-running)
fi
if [ "$DRY_RUN" -eq 1 ]; then
	qemu_args+=(--dry-run)
fi

exec "$QEMU_RUNNER" "${qemu_args[@]}"
