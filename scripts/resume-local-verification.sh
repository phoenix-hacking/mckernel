#!/usr/bin/env bash
# Restore this workstation's existing controls, then run bounded preflight checks.
# Uses the reviewed local setup and container launchers; never boots a guest.
set -euo pipefail

if [[ "$EUID" != 0 ]]; then
    printf '%s\n' 'Run with sudo in a local terminal; administrator authentication is required.' >&2
    exit 1
fi

recovery_work=/home/holden/mckernel-work
recovery_setup="$recovery_work/setup"
for recovery_required in setup-host.sh container-run.py check-isolation.py; do
    test -f "$recovery_setup/$recovery_required"
done

# setup-host.sh refuses to format an existing image and restores the established
# four-CPU, 12-GiB, 512-task controls and fixed-capacity scratch mount.
/usr/bin/bash "$recovery_setup/setup-host.sh"

recovery_directory=$(/usr/bin/mktemp -d "$recovery_work/scratch/recovery-XXXXXXXX")
/usr/bin/chown 1000:1000 "$recovery_directory"
/usr/bin/chmod 0700 "$recovery_directory"
recovery_container_directory="/work/${recovery_directory##*/}"
/usr/bin/install -m 0644 -o 1000 -g 1000 \
    "$recovery_setup/check-isolation.py" "$recovery_directory/check-isolation.py"

recovery_stage=initialization
recovery_finish() {
    recovery_result=$?
    trap - EXIT
    printf 'stage=%s\nexit_code=%s\n' "$recovery_stage" "$recovery_result" \
        > "$recovery_directory/result.txt"
    /usr/bin/chown 1000:1000 "$recovery_directory/result.txt"
    printf 'Recovery records: %s\n' "$recovery_directory"
    exit "$recovery_result"
}
trap recovery_finish EXIT

# Each launcher holds the existing global verification lock. Preserve individual
# logs and stop at the first failure instead of starting later checks.
for recovery_target in native compat; do
    recovery_stage="$recovery_target-isolation"
    /usr/bin/python3 "$recovery_setup/container-run.py" "$recovery_target" \
        python3 -B "$recovery_container_directory/check-isolation.py" \
        2>&1 | /usr/bin/tee "$recovery_directory/$recovery_stage.log"
done

recovery_stage=native-image-tests
/usr/bin/python3 "$recovery_setup/container-run.py" native \
    python3 -B -m unittest -v -f \
    scripts.tests.test_ihk_smp_image scripts.tests.test_ihk_os_runtime \
    2>&1 | /usr/bin/tee "$recovery_directory/$recovery_stage.log"

recovery_stage=preflight-complete
printf '%s\n' \
    'Environment restoration, container isolation and focused native tests passed.' \
    'Native Kbuild, staging integration and guest verification remain separate steps.'
