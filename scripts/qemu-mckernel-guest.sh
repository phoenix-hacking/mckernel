#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'USAGE'
Usage:
  scripts/qemu-mckernel-guest.sh --image IMAGE [options]

Boots a disposable QEMU/KVM guest from an existing Rocky/RHEL-family qcow2
image. The backing image is never modified: the guest runs from a temporary
qcow2 overlay and writes logs under /tmp by default.

This runner is only a safe guest boundary. It does not run host mcreboot.sh,
load host IHK modules, or pass host McKernel devices into the guest. Any
McKernel boot/regression command must be passed with --guest-cmd and will run
inside the guest over SSH after cloud-init brings it up.

Options:
  --image PATH          Required qcow2 backing image. Must not be a /dev path.
  --user USER           Cloud-init/SSH user. Default: mcktest
  --ssh-port PORT       Host port forwarded to guest SSH. Default: 2222
  --memory SIZE         QEMU memory. Default: 4096M
  --cpus N              QEMU vCPU count. Default: 4
  --disk-size SIZE      Expand the disposable overlay before boot, for example
                        24G. Default: keep the backing image virtual size.
  --accel MODE          auto, kvm, or tcg. Default: auto
  --timeout SEC         Guest SSH wait timeout. Default: 300
  --runtime SEC         Max time to let QEMU run after SSH/command. Default: 0
  --guest-cmd CMD       Command to run inside the guest after SSH is ready.
  --guest-cmd-timeout SEC
                        Watchdog for --guest-cmd. Default: 0 (disabled)
  --guest-cleanup-cmd CMD
                        Cleanup command to attempt inside the guest before
                        QEMU exits. Default: stop McKernel if installed.
  --guest-cleanup-timeout SEC
                        Watchdog for guest cleanup. Default: 30
  --guest-evidence-dir PATH
                        Copy this guest /tmp child into LOG_DIR/guest-evidence
                        after --guest-cmd, including on command failure.
  --ssh-key PATH        Existing private key to use for guest SSH. Default:
                        generate a temporary key in the log directory.
  --kernel PATH         Optional external kernel image to boot with QEMU.
  --initrd PATH         Optional external initramfs image to boot with QEMU.
  --append CMDLINE      Kernel command line used with --kernel.
  --pause-at-reset      Start QEMU with CPUs paused at reset for first-instruction
                        GDB/monitor inspection. Use with --gdb PORT.
  --gdb PORT            Open a QEMU GDB stub on 127.0.0.1:PORT.
  --no-guest-cleanup    Do not attempt the guest cleanup command.
  --shared-dir PATH     Expose PATH read-only as 9p tag hostshare.
  --stage-dir HOST:GUEST
                        Copy HOST directory into GUEST after SSH is ready.
                        May be specified more than once.
  --log-dir PATH        Log directory. Default: /tmp/mckernel-qemu-<timestamp>
  --keep-overlay        Keep the temporary qcow2 overlay after exit.
  --keep-running        Leave QEMU running after the command completes.
  --dry-run             Print the QEMU command without starting the guest.
  -h, --help            Show this help.

Examples:
  scripts/qemu-mckernel-guest.sh --image /var/lib/libvirt/images/rocky8.qcow2
  scripts/qemu-mckernel-guest.sh --image rocky8.qcow2 --shared-dir "$PWD" \
    --guest-cmd 'sudo /opt/mckernel-rust/sbin/mcreboot.sh -c 1 -m 512M@0'
USAGE
}

IMAGE=
USER_NAME=mcktest
SSH_PORT=2222
MEMORY=4096M
CPUS=4
DISK_SIZE=
ACCEL_REQUEST=auto
TIMEOUT=300
RUNTIME=0
GUEST_CMD=
GUEST_CMD_TIMEOUT=0
GUEST_CLEANUP=1
GUEST_CLEANUP_CMD='if [ -x /opt/mckernel-rust/sbin/mcstop+release.sh ]; then sudo /opt/mckernel-rust/sbin/mcstop+release.sh -k || true; fi'
GUEST_CLEANUP_TIMEOUT=30
GUEST_EVIDENCE_DIR=
SHARED_DIR=
STAGE_DIRS=()
LOG_DIR="/tmp/mckernel-qemu-$(date +%Y%m%d-%H%M%S)"
KEEP_OVERLAY=0
KEEP_RUNNING=0
DRY_RUN=0
SSH_READY=0
SSH_ARGS=()
SSH_KEY_INPUT=
KERNEL_IMAGE=
INITRD_IMAGE=
KERNEL_APPEND=
PAUSE_AT_RESET=0
GDB_PORT=

while [ "$#" -gt 0 ]; do
	case "$1" in
		--image)
			IMAGE="${2:?missing value for --image}"
			shift 2
			;;
		--user)
			USER_NAME="${2:?missing value for --user}"
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
		--disk-size)
			DISK_SIZE="${2:?missing value for --disk-size}"
			shift 2
			;;
		--accel)
			ACCEL_REQUEST="${2:?missing value for --accel}"
			shift 2
			;;
		--timeout)
			TIMEOUT="${2:?missing value for --timeout}"
			shift 2
			;;
		--runtime)
			RUNTIME="${2:?missing value for --runtime}"
			shift 2
			;;
		--guest-cmd)
			GUEST_CMD="${2:?missing value for --guest-cmd}"
			shift 2
			;;
		--guest-cmd-timeout)
			GUEST_CMD_TIMEOUT="${2:?missing value for --guest-cmd-timeout}"
			shift 2
			;;
		--guest-cleanup-cmd)
			GUEST_CLEANUP_CMD="${2:?missing value for --guest-cleanup-cmd}"
			shift 2
			;;
		--guest-cleanup-timeout)
			GUEST_CLEANUP_TIMEOUT="${2:?missing value for --guest-cleanup-timeout}"
			shift 2
			;;
		--guest-evidence-dir)
			GUEST_EVIDENCE_DIR="${2:?missing value for --guest-evidence-dir}"
			shift 2
			;;
		--ssh-key)
			SSH_KEY_INPUT="${2:?missing value for --ssh-key}"
			shift 2
			;;
		--kernel)
			KERNEL_IMAGE="${2:?missing value for --kernel}"
			shift 2
			;;
		--initrd)
			INITRD_IMAGE="${2:?missing value for --initrd}"
			shift 2
			;;
		--append)
			KERNEL_APPEND="${2:?missing value for --append}"
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
		--no-guest-cleanup)
			GUEST_CLEANUP=0
			shift
			;;
		--shared-dir)
			SHARED_DIR="${2:?missing value for --shared-dir}"
			shift 2
			;;
		--stage-dir)
			STAGE_DIRS+=("${2:?missing value for --stage-dir}")
			shift 2
			;;
		--log-dir)
			LOG_DIR="${2:?missing value for --log-dir}"
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

quote_cmd() {
	local arg
	for arg in "$@"; do
		printf '%q ' "$arg"
	done
	printf '\n'
}

if [ -z "$IMAGE" ]; then
	echo "error: --image is required" >&2
	usage >&2
	exit 2
fi

case "$IMAGE" in
	/dev/*)
		echo "error: refusing to use host device path as a guest image: $IMAGE" >&2
		exit 2
		;;
esac

if [ -n "$DISK_SIZE" ] && [[ ! "$DISK_SIZE" =~ ^[1-9][0-9]*[KMGT]?$ ]]; then
	echo "error: --disk-size must be a positive byte count with an optional K, M, G, or T suffix" >&2
	exit 2
fi

if [ -n "$GUEST_EVIDENCE_DIR" ]; then
	if [[ ! "$GUEST_EVIDENCE_DIR" =~ ^/tmp/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
		echo 'error: --guest-evidence-dir must be one safe directory directly under /tmp' >&2
		exit 2
	fi
fi

if [ ! -f "$IMAGE" ]; then
	echo "error: image not found: $IMAGE" >&2
	exit 1
fi
IMAGE="$(cd "$(dirname "$IMAGE")" && pwd)/$(basename "$IMAGE")"

if [ -n "$SHARED_DIR" ] && [ ! -d "$SHARED_DIR" ]; then
	echo "error: shared directory not found: $SHARED_DIR" >&2
	exit 1
fi

for stage_spec in "${STAGE_DIRS[@]}"; do
	host_stage="${stage_spec%%:*}"
	guest_stage="${stage_spec#*:}"
	if [ "$host_stage" = "$stage_spec" ] || [ -z "$host_stage" ] ||
		[ -z "$guest_stage" ]; then
		echo "error: --stage-dir must be HOST:GUEST" >&2
		exit 2
	fi
	if [ ! -d "$host_stage" ]; then
		echo "error: staged host directory not found: $host_stage" >&2
		exit 1
	fi
done

if [ -n "$KERNEL_IMAGE" ] && [ ! -f "$KERNEL_IMAGE" ]; then
	echo "error: kernel image not found: $KERNEL_IMAGE" >&2
	exit 1
fi

if [ -n "$INITRD_IMAGE" ] && [ ! -f "$INITRD_IMAGE" ]; then
	echo "error: initrd image not found: $INITRD_IMAGE" >&2
	exit 1
fi

if [ -z "$KERNEL_IMAGE" ] && { [ -n "$INITRD_IMAGE" ] || [ -n "$KERNEL_APPEND" ]; }; then
	echo "error: --initrd/--append require --kernel" >&2
	exit 2
fi

need_cmd qemu-system-x86_64
need_cmd qemu-img
need_cmd cloud-localds
need_cmd ssh
need_cmd tar
need_cmd timeout
if [ -z "$SSH_KEY_INPUT" ]; then
	need_cmd ssh-keygen
fi

case "$ACCEL_REQUEST" in
	auto|kvm|tcg)
		;;
	*)
		echo "error: --accel must be auto, kvm, or tcg" >&2
		exit 2
		;;
esac

require_uint() {
	local name="$1"
	local value="$2"

	case "$value" in
		''|*[!0-9]*)
			echo "error: --${name} must be a non-negative integer number of seconds" >&2
			exit 2
			;;
	esac
}

require_uint timeout "$TIMEOUT"
require_uint runtime "$RUNTIME"
require_uint guest-cmd-timeout "$GUEST_CMD_TIMEOUT"
require_uint guest-cleanup-timeout "$GUEST_CLEANUP_TIMEOUT"
if [ -n "$GDB_PORT" ]; then
	require_uint gdb "$GDB_PORT"
fi
mkdir -p "$LOG_DIR"

BASE_FORMAT="$(LC_ALL=C qemu-img info "$IMAGE" |
	sed -n 's/^file format: //p' | head -n1)"
if [ -z "$BASE_FORMAT" ]; then
	echo "error: could not determine backing image format: $IMAGE" >&2
	exit 1
fi

OVERLAY="$LOG_DIR/guest-overlay.qcow2"
SEED="$LOG_DIR/seed.iso"
SSH_KEY="$LOG_DIR/id_ed25519"
PIDFILE="$LOG_DIR/qemu.pid"
STARTED_PIDFILE="$LOG_DIR/qemu-started.pid"
SERIAL_LOG="$LOG_DIR/serial.log"
DEBUGCON_LOG="$LOG_DIR/debugcon.log"
STARTUP_LOG="$LOG_DIR/qemu-startup.log"
QMP_SOCKET="$LOG_DIR/qmp.sock"
QMP_LOG="$LOG_DIR/qmp-status.jsonl"
GUEST_CMD_LOG="$LOG_DIR/guest-command.log"
GUEST_CLEANUP_LOG="$LOG_DIR/guest-cleanup.log"
GUEST_EVIDENCE_ARCHIVE="$LOG_DIR/guest-evidence.tar"
GUEST_EVIDENCE_ARCHIVE_SHA256="$LOG_DIR/guest-evidence.tar.sha256"
GUEST_EVIDENCE_HOST_DIR="$LOG_DIR/guest-evidence"
CPU_MODEL_FILE="$LOG_DIR/qemu-cpu-model.txt"

print_serial_tail() {
	local crash_end
	local crash_line
	local crash_match
	local crash_start

	if [ -f "$SERIAL_LOG" ]; then
		# A kdump reboot can put hundreds of recovery-kernel lines after the
		# original panic. Prefer the panic endpoint so the preceding BUG, RIP,
		# and call trace remain visible in the CI log.
		crash_match="$(LC_ALL=C grep -a -n -m1 -E \
			'Kernel panic|not syncing:' "$SERIAL_LOG" 2>/dev/null || true)"
		if [ -z "$crash_match" ]; then
			crash_match="$(LC_ALL=C grep -a -n -m1 -F \
				'IHK: OS does not become ready, kernel msg:' \
				"$SERIAL_LOG" 2>/dev/null || true)"
		fi
		if [ -z "$crash_match" ]; then
			crash_match="$(LC_ALL=C grep -a -n -m1 -E \
				'BUG:|Oops:|general protection fault|Unable to handle kernel|#PF:|RIP:|Call Trace:' \
				"$SERIAL_LOG" 2>/dev/null || true)"
		fi
		crash_line="${crash_match%%:*}"
		case "$crash_line" in
			''|*[!0-9]*)
				;;
			*)
				crash_start=$((crash_line > 300 ? crash_line - 300 : 1))
				crash_end=$((crash_line + 500))
				echo "serial failure context (lines ${crash_start}-${crash_end}, marker at ${crash_line}):" >&2
				LC_ALL=C sed -n "${crash_start},${crash_end}p" "$SERIAL_LOG" >&2 || true
				;;
		esac
		echo "recent serial log:" >&2
		tail -n 80 "$SERIAL_LOG" >&2 || true
	fi
	if [ -s "$DEBUGCON_LOG" ]; then
		echo "McKernel early debugcon phases:" >&2
		tail -c 4096 "$DEBUGCON_LOG" >&2 || true
		echo >&2
	else
		echo "McKernel early debugcon phases: empty" >&2
	fi
}

qemu_pid_is_owned() {
	local pid="$1"
	local qemu_exe
	local pidfile_verified=0
	local i
	local -a qemu_argv=()

	if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
		return 1
	fi
	qemu_exe="$(basename "$(readlink "/proc/$pid/exe" 2>/dev/null || true)")"
	if [[ "$qemu_exe" != qemu-system-x86_64* ]]; then
		return 1
	fi
	mapfile -d '' -t qemu_argv <"/proc/$pid/cmdline" || return 1
	for ((i = 0; i + 1 < ${#qemu_argv[@]}; i++)); do
		if [ "${qemu_argv[$i]}" = -pidfile ] &&
			[ "${qemu_argv[$((i + 1))]}" = "$PIDFILE" ]; then
			pidfile_verified=1
			break
		fi
	done
	[ "$pidfile_verified" -eq 1 ]
}

qemu_is_running() {
	local pid

	if [ ! -f "$PIDFILE" ]; then
		return 1
	fi
	pid="$(cat "$PIDFILE" 2>/dev/null || true)"
	if [ -z "$pid" ]; then
		return 1
	fi
	qemu_pid_is_owned "$pid"
}

record_qemu_process_sample() {
	local label="$1"
	local pid="$2"
	local process_state
	local process_ticks
	local serial_bytes=0

	if [ -f "$SERIAL_LOG" ]; then
		serial_bytes="$(stat -c %s "$SERIAL_LOG")"
	fi
	if ! qemu_pid_is_owned "$pid"; then
		printf '%s pid=%s owned=no serial_bytes=%s\n' \
			"$label" "$pid" "$serial_bytes" >>"$STARTUP_LOG"
		return 1
	fi
	read -r process_state process_ticks < <(
		awk '{ print $3, ($14 + $15) }' "/proc/$pid/stat"
	)
	printf '%s pid=%s owned=yes state=%s ticks=%s serial_bytes=%s\n' \
		"$label" "$pid" "$process_state" "$process_ticks" "$serial_bytes" \
		>>"$STARTUP_LOG"
}

record_qmp_status() {
	local label="$1"

	if ! command -v python3 >/dev/null 2>&1 || [ ! -S "$QMP_SOCKET" ]; then
		printf '{"label":"%s","error":"QMP unavailable"}\n' "$label" \
			>>"$QMP_LOG"
		return 0
	fi
	python3 - "$QMP_SOCKET" "$label" >>"$QMP_LOG" 2>&1 <<'PY' || true
import json
import socket
import sys

socket_path, label = sys.argv[1:]
try:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    client.connect(socket_path)
    stream = client.makefile("rwb", buffering=0)

    def read_response():
        while True:
            line = stream.readline()
            if not line:
                raise RuntimeError("QMP socket closed")
            message = json.loads(line)
            if "event" not in message:
                return message

    greeting = read_response()
    print(json.dumps({"label": label, "greeting": greeting}, sort_keys=True))
    for command in ("qmp_capabilities", "query-status", "query-cpus-fast"):
        stream.write((json.dumps({"execute": command}) + "\r\n").encode())
        print(json.dumps({
            "label": label,
            "command": command,
            "response": read_response(),
        }, sort_keys=True))
except Exception as error:
    print(json.dumps({
        "label": label,
        "error": f"{type(error).__name__}: {error}",
    }, sort_keys=True))
PY
}

collect_guest_evidence() {
	local archive_sha
	local file_count
	local remote_cmd

	if [ -z "$GUEST_EVIDENCE_DIR" ]; then
		return
	fi
	remote_cmd="$(printf 'test -d %q && test ! -L %q && tar -C %q -cf - .' \
		"$GUEST_EVIDENCE_DIR" "$GUEST_EVIDENCE_DIR" \
		"$GUEST_EVIDENCE_DIR")"
	if ! timeout --signal=TERM --kill-after=5s "$GUEST_CLEANUP_TIMEOUT" \
		ssh "${SSH_ARGS[@]}" "$remote_cmd" >"$GUEST_EVIDENCE_ARCHIVE"
	then
		echo "error: could not collect guest evidence directory: $GUEST_EVIDENCE_DIR" >&2
		return 1
	fi
	if [ ! -s "$GUEST_EVIDENCE_ARCHIVE" ]; then
		echo 'error: collected guest evidence archive is empty' >&2
		return 1
	fi
	if ! mkdir -p "$GUEST_EVIDENCE_HOST_DIR"; then
		echo 'error: could not create the host guest-evidence directory' >&2
		return 1
	fi
	if ! tar --no-same-owner --no-same-permissions \
		-C "$GUEST_EVIDENCE_HOST_DIR" -xf "$GUEST_EVIDENCE_ARCHIVE"
	then
		echo 'error: could not extract the guest evidence archive' >&2
		return 1
	fi
	if [ ! -s "$GUEST_EVIDENCE_HOST_DIR/SHA256SUMS" ]; then
		echo 'error: guest evidence is missing SHA256SUMS' >&2
		return 1
	fi
	if ! (
		cd "$GUEST_EVIDENCE_HOST_DIR"
		sha256sum -c SHA256SUMS
	); then
		echo 'error: guest evidence SHA256SUMS verification failed' >&2
		return 1
	fi
	if ! (
		cd "$LOG_DIR"
		sha256sum "$(basename "$GUEST_EVIDENCE_ARCHIVE")" \
			>"$(basename "$GUEST_EVIDENCE_ARCHIVE_SHA256")"
	)
	then
		echo 'error: could not hash the guest evidence archive' >&2
		return 1
	fi
	file_count="$(find "$GUEST_EVIDENCE_HOST_DIR" -type f | wc -l)" || return 1
	archive_sha="$(awk '{ print $1 }' "$GUEST_EVIDENCE_ARCHIVE_SHA256")" || return 1
	if [[ ! "$file_count" =~ ^[1-9][0-9]*$ ]] ||
		[[ ! "$archive_sha" =~ ^[0-9a-f]{64}$ ]]
	then
		echo 'error: invalid guest evidence count or archive digest' >&2
		return 1
	fi
	printf 'guest-evidence: collected files=%s archive_sha256=%s\n' \
		"$file_count" "$archive_sha"
}

cleanup() {
	local pid

	if [ "$KEEP_RUNNING" -eq 0 ] && [ "$SSH_READY" -eq 1 ] &&
		[ "$GUEST_CLEANUP" -eq 1 ]; then
		timeout --signal=TERM --kill-after=5s "$GUEST_CLEANUP_TIMEOUT" \
			ssh "${SSH_ARGS[@]}" "$GUEST_CLEANUP_CMD" \
			>>"$GUEST_CLEANUP_LOG" 2>&1 || true
	fi

	if [ "$KEEP_RUNNING" -eq 0 ]; then
		pid="$(cat "$PIDFILE" 2>/dev/null || true)"
		if [ -z "$pid" ]; then
			pid="$(cat "$STARTED_PIDFILE" 2>/dev/null || true)"
		fi
		if qemu_pid_is_owned "$pid"; then
			kill "$pid" 2>/dev/null || true
			for _ in $(seq 1 20); do
				qemu_pid_is_owned "$pid" || break
				sleep 0.2
			done
			if qemu_pid_is_owned "$pid"; then
				kill -9 "$pid" 2>/dev/null || true
			elif [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
				echo "refusing to SIGKILL reused PID $pid" >&2
			fi
		elif [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
			echo "refusing to kill PID $pid because QEMU identity did not verify" >&2
		fi
	fi

	if [ "$KEEP_RUNNING" -eq 0 ] && [ "$KEEP_OVERLAY" -eq 0 ]; then
		rm -f "$OVERLAY"
	fi
}
trap cleanup EXIT

say "Preparing disposable guest overlay"
qemu-img create -f qcow2 -F "$BASE_FORMAT" -b "$IMAGE" "$OVERLAY" >/dev/null
if [ -n "$DISK_SIZE" ]; then
	qemu-img resize "$OVERLAY" "$DISK_SIZE" >/dev/null
fi

if [ -n "$SSH_KEY_INPUT" ]; then
	if [ ! -f "$SSH_KEY_INPUT" ]; then
		echo "error: SSH key not found: $SSH_KEY_INPUT" >&2
		exit 1
	fi
	SSH_KEY="$SSH_KEY_INPUT"
	if [ -f "$SSH_KEY_INPUT.pub" ]; then
		PUBKEY="$(cat "$SSH_KEY_INPUT.pub")"
	else
		need_cmd ssh-keygen
		PUBKEY="$(ssh-keygen -y -f "$SSH_KEY_INPUT")"
	fi
else
	ssh-keygen -q -t ed25519 -N '' -f "$SSH_KEY" -C "mckernel-qemu-guest" >/dev/null
	PUBKEY="$(cat "$SSH_KEY.pub")"
fi

cat >"$LOG_DIR/user-data" <<EOF
#cloud-config
users:
  - default
  - name: ${USER_NAME}
    groups: wheel
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ${PUBKEY}
ssh_pwauth: false
disable_root: false
package_update: false
final_message: "mckernel qemu guest ready"
EOF

cat >"$LOG_DIR/meta-data" <<EOF
instance-id: mckernel-qemu-$(date +%s)
local-hostname: mckernel-qemu
EOF

cloud-localds "$SEED" "$LOG_DIR/user-data" "$LOG_DIR/meta-data"

ACCEL=tcg
if [ "$ACCEL_REQUEST" = "kvm" ]; then
	if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
		echo "error: --accel kvm requested, but /dev/kvm is not accessible" >&2
		exit 1
	fi
	ACCEL=kvm
elif [ "$ACCEL_REQUEST" = "tcg" ]; then
	ACCEL=tcg
elif [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
	ACCEL=kvm
fi

# McKernel's x86_64 boot path uses four-level page tables. Keep that invariant
# under both emulation and host passthrough so accelerator selection cannot
# expose LA57 merely because the runner or QEMU model supports it.
CPU_MODEL=max,la57=off
if [ "$ACCEL" = "kvm" ]; then
	CPU_MODEL=host,la57=off
fi

QEMU_ARGS=(
	qemu-system-x86_64
	-accel "$ACCEL"
	# With graphics disabled SeaBIOS redirects its own output to ttyS0, so an
	# empty serial log proves failure before the Rocky kernel console starts.
	-machine q35,graphics=off
	-cpu "$CPU_MODEL"
	-smp "$CPUS"
	-m "$MEMORY"
	-no-reboot
	-display none
	-serial "file:$SERIAL_LOG"
	-chardev "file,id=mckdebug,path=$DEBUGCON_LOG"
	-device "isa-debugcon,iobase=0xe9,chardev=mckdebug"
	-qmp "unix:$QMP_SOCKET,server=on,wait=off"
	-pidfile "$PIDFILE"
	-daemonize
	-drive "if=none,id=rocky_os,file=$OVERLAY,format=qcow2,cache=unsafe"
	-device "virtio-blk-pci,drive=rocky_os,bootindex=1"
	# NoCloud only needs a CIDATA-labelled block device.  virtio-blk does not
	# support non-disk devices, so expose the read-only seed as a disk rather
	# than requesting an unsupported virtio CD-ROM.
	-drive "if=none,id=cloud_seed,file=$SEED,format=raw,readonly=on"
	-device "virtio-blk-pci,drive=cloud_seed,bootindex=2"
	-nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
)

if [ "$PAUSE_AT_RESET" -eq 1 ]; then
	QEMU_ARGS+=(-S)
fi
if [ -n "$GDB_PORT" ]; then
	QEMU_ARGS+=(-gdb "tcp:127.0.0.1:${GDB_PORT}")
fi

if [ -n "$SHARED_DIR" ]; then
	QEMU_ARGS+=(
		-virtfs "local,path=$SHARED_DIR,mount_tag=hostshare,security_model=none,readonly=on"
	)
fi

if [ -n "$KERNEL_IMAGE" ]; then
	QEMU_ARGS+=(-kernel "$KERNEL_IMAGE")
	if [ -n "$INITRD_IMAGE" ]; then
		QEMU_ARGS+=(-initrd "$INITRD_IMAGE")
	fi
	if [ -n "$KERNEL_APPEND" ]; then
		QEMU_ARGS+=(-append "$KERNEL_APPEND")
	fi
fi

printf '%s\n' "Log directory: $LOG_DIR"
printf '%s\n' "Serial log: $SERIAL_LOG"
printf '%s\n' "Debugcon log: $DEBUGCON_LOG"
printf '%s\n' "QEMU startup log: $STARTUP_LOG"
printf '%s\n' "QMP status log: $QMP_LOG"
printf '%s\n' "Overlay: $OVERLAY"
printf '%s\n' "Backing image format: $BASE_FORMAT"
if [ -n "$DISK_SIZE" ]; then
	printf '%s\n' "Overlay virtual size: $DISK_SIZE"
fi
printf '%s\n' "QEMU accel: $ACCEL"
printf '%s\n' "QEMU cpu model: $CPU_MODEL"
printf '%s\n' "$CPU_MODEL" > "$CPU_MODEL_FILE"
if [ "$PAUSE_AT_RESET" -eq 1 ]; then
	printf '%s\n' "QEMU pause-at-reset: enabled"
fi
if [ -n "$GDB_PORT" ]; then
	printf '%s\n' "QEMU GDB stub: 127.0.0.1:$GDB_PORT"
fi
printf '%s' "QEMU command: "
quote_cmd "${QEMU_ARGS[@]}"

if [ "$DRY_RUN" -eq 1 ]; then
	exit 0
fi

say "Starting guest"
"${QEMU_ARGS[@]}"

if [ ! -s "$PIDFILE" ]; then
	echo "error: QEMU did not create a nonempty pidfile: $PIDFILE" >&2
	exit 1
fi
qemu_started_pid="$(cat "$PIDFILE")"
case "$qemu_started_pid" in
	''|*[!0-9]*)
		echo "error: QEMU wrote an invalid PID: $qemu_started_pid" >&2
		exit 1
		;;
esac
if ! qemu_pid_is_owned "$qemu_started_pid"; then
	echo "error: started QEMU PID $qemu_started_pid failed identity verification" >&2
	exit 1
fi
printf '%s\n' "$qemu_started_pid" >"$STARTED_PIDFILE"
printf 'Verified QEMU startup PID: %s\n' "$qemu_started_pid"

if [ "$PAUSE_AT_RESET" -eq 0 ]; then
	record_qemu_process_sample start "$qemu_started_pid"
	record_qmp_status start
	for _ in $(seq 1 12); do
		sleep 5
		if ! qemu_pid_is_owned "$qemu_started_pid"; then
			record_qemu_process_sample exited "$qemu_started_pid" || true
			record_qmp_status exited
			echo "error: guest exited before producing firmware serial output" >&2
			print_serial_tail
			exit 1
		fi
		if [ -s "$SERIAL_LOG" ]; then
			break
		fi
	done
	record_qemu_process_sample preflight "$qemu_started_pid"
	record_qmp_status preflight
	if [ ! -s "$SERIAL_LOG" ]; then
		echo "error: guest produced no SeaBIOS/Rocky serial output within 60s" >&2
		echo "startup diagnostics: $STARTUP_LOG" >&2
		echo "QMP diagnostics: $QMP_LOG" >&2
		exit 1
	fi
	printf 'QEMU firmware serial preflight: PASS\n'
else
	printf 'QEMU firmware serial preflight: skipped (pause-at-reset)\n'
fi

SSH_ARGS=(
	-F /dev/null
	-i "$SSH_KEY"
	-o BatchMode=yes
	-o StrictHostKeyChecking=no
	-o UserKnownHostsFile=/dev/null
	-o ConnectTimeout=5
	-o LogLevel=ERROR
	-o NumberOfPasswordPrompts=0
	-o PreferredAuthentications=publickey
	-p "$SSH_PORT"
	"${USER_NAME}@127.0.0.1"
)

say "Waiting for guest SSH"
deadline=$((SECONDS + TIMEOUT))
until ssh "${SSH_ARGS[@]}" true >/dev/null 2>&1; do
	if ! qemu_is_running; then
		echo "error: QEMU exited before guest SSH became ready" >&2
		echo "serial log: $SERIAL_LOG" >&2
		print_serial_tail
		exit 1
	fi
	if grep -Fq 'No bootable device.' "$SERIAL_LOG" 2>/dev/null; then
		record_qemu_process_sample firmware-boot-failure "$qemu_started_pid" || true
		record_qmp_status firmware-boot-failure
		echo 'error: guest firmware reported that no bootable device exists' >&2
		echo "serial log: $SERIAL_LOG" >&2
		print_serial_tail
		exit 1
	fi
	if [ "$SECONDS" -ge "$deadline" ]; then
		record_qemu_process_sample ssh-timeout "$qemu_started_pid" || true
		record_qmp_status ssh-timeout
		echo "error: guest SSH did not become ready within ${TIMEOUT}s" >&2
		echo "serial log: $SERIAL_LOG" >&2
		print_serial_tail
		exit 1
	fi
	sleep 2
done

say "Guest SSH ready"
SSH_READY=1

for stage_spec in "${STAGE_DIRS[@]}"; do
	host_stage="${stage_spec%%:*}"
	guest_stage="${stage_spec#*:}"
	remote_cmd="$(printf 'rm -rf %q && mkdir -p %q && tar -C %q -xf -' \
		"$guest_stage" "$guest_stage" "$guest_stage")"

	say "Staging $host_stage into guest:$guest_stage"
	tar -C "$host_stage" -cf - . | ssh "${SSH_ARGS[@]}" "$remote_cmd"
done

if [ -n "$GUEST_CMD" ]; then
	say "Running guest command"
	set +e
	if [ "$GUEST_CMD_TIMEOUT" -gt 0 ]; then
		timeout --signal=TERM --kill-after=5s "$GUEST_CMD_TIMEOUT" \
			ssh "${SSH_ARGS[@]}" "$GUEST_CMD" >"$GUEST_CMD_LOG" 2>&1
	else
		ssh "${SSH_ARGS[@]}" "$GUEST_CMD" >"$GUEST_CMD_LOG" 2>&1
	fi
	rc=$?
	set -e
	cat "$GUEST_CMD_LOG"
	evidence_rc=0
	collect_guest_evidence || evidence_rc=$?
	if { [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; } &&
		[ "$GUEST_CMD_TIMEOUT" -gt 0 ]
	then
		echo "error: guest command exceeded the ${GUEST_CMD_TIMEOUT}s watchdog (status ${rc})" >&2
		echo "serial log: $SERIAL_LOG" >&2
		print_serial_tail
		exit "$rc"
	fi
	if [ "$rc" -ne 0 ]; then
		echo "error: guest command failed with status $rc" >&2
		echo "serial log: $SERIAL_LOG" >&2
		print_serial_tail
		exit "$rc"
	fi
	if [ "$evidence_rc" -ne 0 ]; then
		echo "error: guest command passed but evidence collection failed with status $evidence_rc" >&2
		exit "$evidence_rc"
	fi
fi

if [ "$RUNTIME" -gt 0 ]; then
	say "Keeping guest alive for ${RUNTIME}s"
	sleep "$RUNTIME"
fi

if [ "$KEEP_RUNNING" -eq 1 ]; then
	say "Guest left running"
	printf 'PID file: %s\n' "$PIDFILE"
else
	say "Guest run complete"
fi
