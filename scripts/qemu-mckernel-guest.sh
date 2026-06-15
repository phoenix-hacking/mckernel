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
  --accel MODE          auto, kvm, or tcg. Default: auto
  --timeout SEC         Guest SSH wait timeout. Default: 300
  --runtime SEC         Max time to let QEMU run after SSH/command. Default: 0
  --guest-cmd CMD       Command to run inside the guest after SSH is ready.
  --guest-cleanup-cmd CMD
                        Cleanup command to attempt inside the guest before
                        QEMU exits. Default: stop McKernel if installed.
  --ssh-key PATH        Existing private key to use for guest SSH. Default:
                        generate a temporary key in the log directory.
  --kernel PATH         Optional external kernel image to boot with QEMU.
  --initrd PATH         Optional external initramfs image to boot with QEMU.
  --append CMDLINE      Kernel command line used with --kernel.
  --no-guest-cleanup    Do not attempt the guest cleanup command.
  --shared-dir PATH     Expose PATH read-only as 9p tag hostshare.
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
ACCEL_REQUEST=auto
TIMEOUT=300
RUNTIME=0
GUEST_CMD=
GUEST_CLEANUP=1
GUEST_CLEANUP_CMD='if [ -x /opt/mckernel-rust/sbin/mcstop+release.sh ]; then sudo /opt/mckernel-rust/sbin/mcstop+release.sh -k || true; fi'
SHARED_DIR=
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
		--guest-cleanup-cmd)
			GUEST_CLEANUP_CMD="${2:?missing value for --guest-cleanup-cmd}"
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
		--no-guest-cleanup)
			GUEST_CLEANUP=0
			shift
			;;
		--shared-dir)
			SHARED_DIR="${2:?missing value for --shared-dir}"
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

if [ ! -f "$IMAGE" ]; then
	echo "error: image not found: $IMAGE" >&2
	exit 1
fi

if [ -n "$SHARED_DIR" ] && [ ! -d "$SHARED_DIR" ]; then
	echo "error: shared directory not found: $SHARED_DIR" >&2
	exit 1
fi

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

mkdir -p "$LOG_DIR"

BASE_FORMAT="$(qemu-img info --output=json "$IMAGE" |
	sed -n 's/.*"format": *"\([^"]*\)".*/\1/p' | head -n1)"
if [ -z "$BASE_FORMAT" ]; then
	BASE_FORMAT=qcow2
fi

OVERLAY="$LOG_DIR/guest-overlay.qcow2"
SEED="$LOG_DIR/seed.iso"
SSH_KEY="$LOG_DIR/id_ed25519"
PIDFILE="$LOG_DIR/qemu.pid"
SERIAL_LOG="$LOG_DIR/serial.log"
GUEST_CMD_LOG="$LOG_DIR/guest-command.log"
GUEST_CLEANUP_LOG="$LOG_DIR/guest-cleanup.log"

cleanup() {
	local pid

	if [ "$KEEP_RUNNING" -eq 0 ] && [ "$SSH_READY" -eq 1 ] &&
		[ "$GUEST_CLEANUP" -eq 1 ]; then
		ssh "${SSH_ARGS[@]}" "$GUEST_CLEANUP_CMD" >>"$GUEST_CLEANUP_LOG" 2>&1 || true
	fi

	if [ "$KEEP_RUNNING" -eq 0 ] && [ -f "$PIDFILE" ]; then
		pid="$(cat "$PIDFILE" 2>/dev/null || true)"
		if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
			kill "$pid" 2>/dev/null || true
			for _ in $(seq 1 20); do
				kill -0 "$pid" 2>/dev/null || break
				sleep 0.2
			done
			kill -9 "$pid" 2>/dev/null || true
		fi
	fi

	if [ "$KEEP_RUNNING" -eq 0 ] && [ "$KEEP_OVERLAY" -eq 0 ]; then
		rm -f "$OVERLAY"
	fi
}
trap cleanup EXIT

say "Preparing disposable guest overlay"
qemu-img create -f qcow2 -F "$BASE_FORMAT" -b "$IMAGE" "$OVERLAY" >/dev/null

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

CPU_MODEL=max
if [ "$ACCEL" = "kvm" ]; then
	CPU_MODEL=host
fi

QEMU_ARGS=(
	qemu-system-x86_64
	-accel "$ACCEL"
	-machine q35
	-cpu "$CPU_MODEL"
	-smp "$CPUS"
	-m "$MEMORY"
	-no-reboot
	-display none
	-serial "file:$SERIAL_LOG"
	-pidfile "$PIDFILE"
	-daemonize
	-drive "if=virtio,file=$OVERLAY,format=qcow2,cache=unsafe"
	-drive "if=virtio,file=$SEED,format=raw,media=cdrom,readonly=on"
	-nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22"
)

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
printf '%s\n' "Overlay: $OVERLAY"
printf '%s\n' "QEMU accel: $ACCEL"
printf '%s' "QEMU command: "
quote_cmd "${QEMU_ARGS[@]}"

if [ "$DRY_RUN" -eq 1 ]; then
	exit 0
fi

say "Starting guest"
"${QEMU_ARGS[@]}"

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
	if [ "$SECONDS" -ge "$deadline" ]; then
		echo "error: guest SSH did not become ready within ${TIMEOUT}s" >&2
		echo "serial log: $SERIAL_LOG" >&2
		exit 1
	fi
	sleep 2
done

say "Guest SSH ready"
SSH_READY=1

if [ -n "$GUEST_CMD" ]; then
	say "Running guest command"
	set +e
	ssh "${SSH_ARGS[@]}" "$GUEST_CMD" >"$GUEST_CMD_LOG" 2>&1
	rc=$?
	set -e
	cat "$GUEST_CMD_LOG"
	if [ "$rc" -ne 0 ]; then
		echo "error: guest command failed with status $rc" >&2
		exit "$rc"
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
