"""Join native-resource-release-v2 and fresh strict5 helper captures offline.

V3 distinguishes the helper write PRI6 from Linux LOG_USER snapshot PRI14.
V2 requires OS CPU/memory inventories explicitly unavailable after successful
shutdown: both public queries return EBUSY under closed admission. No empty
OS inventories or query capability are inferred.

Caller must supply captures from separate private pipes and a kmsg cursor range
opened immediately before the second invocation. First boot/workload/strict stop,
same-guest ownership and final guest retirement require independent evaluation.
This consumer does not launch helpers or grant native/full-cycle acceptance.
"""
import re

from native_resource_release_capture import evaluate as evaluate_release

BOOT_STDOUT = (
    b"NATIVE_MCCTRL_PREREADY x86_64 PASS rejected=2\n"
    b"NATIVE_BOOT_SERVICE x86_64 boot_errno=0\n"
    b"NATIVE_BOOT_STATUS x86_64 observed=5 expected=5\n"
    b"NATIVE_BOOT_CAPTURE x86_64 ready\n"
    b"NATIVE_SYSFS_SERVICE x86_64 PASS read_checks=66 store_checks=64 rounds=32\n"
    b"NATIVE_BOOT_CAPTURE x86_64 ready\n"
    b"NATIVE_BOOT_START x86_64 CAPTURED ready=1 resources_retained=1\n"
    b"NATIVE_OS_SYSFS x86_64 PASS checks=2 setup_completed=1\n"
)
# /dev/kmsg write<6> has facility0; Linux enforces LOG_USER(1),
# so klogctl syslog serialization emits (1 << 3) | 6 == 14.
PROTOCOL_VERSION = 3
BOOT_WRITE_KMSG = b"<6>NATIVE_BOOT_STATUS x86_64 observed=5 expected=5\n"
BOOT_KMSG = b"<14>NATIVE_BOOT_STATUS x86_64 observed=5 expected=5\n"


def second_boot_status(kernel_before, kernel_after):
    """Extract one fresh status marker from append-only bounded klog snapshots.

    Capture before immediately before invocation and after immediately after it.
    Ring rollover, partial records and non-prefix snapshots fail closed. Both raw
    snapshots must be retained, and their full errors evaluated independently.
    """
    if any(type(value) is not bytes or len(value) >= 262144
           or (value and not value.endswith(b"\n")) or b"\r" in value
           for value in (kernel_before, kernel_after)):
        raise ValueError("bounded kernel snapshots")
    if not kernel_after.startswith(kernel_before):
        raise ValueError("kernel ring changed/wrapped")
    delta = kernel_after[len(kernel_before):]
    records = [line for line in delta.splitlines(keepends=True)
               if b"NATIVE_BOOT_STATUS" in line]
    if len(records) != 1 or re.fullmatch(
            rb"<14>(?:\[\s*[0-9]+\.[0-9]+\]\s*)?"
            rb"NATIVE_BOOT_STATUS x86_64 observed=5 expected=5\n", records[0]) is None:
        raise ValueError("fresh strict5 kernel status")
    return BOOT_KMSG


def evaluate(resource_stdout, resource_stderr, resource_status,
             reboot_stdout, reboot_stderr, reboot_status, reboot_status_kmsg,
             resource_finished_ns, reboot_started_ns, reboot_finished_ns):
    """Require ordered per-invocation raw wait statuses and exact helper output.

    reboot_status_kmsg is the extracted NATIVE_BOOT_STATUS records from the
    second helper's bounded kmsg cursor range, including their original LF.
    Evaluate the full kernel capture separately for all error markers.
    """
    for value in (resource_finished_ns, reboot_started_ns, reboot_finished_ns):
        if type(value) is not int or not 0 < value < (1 << 64):
            raise ValueError("invalid sequence timestamp")
    if not resource_finished_ns < reboot_started_ns < reboot_finished_ns:
        raise ValueError("release/reboot order")
    evaluate_release(resource_stdout, resource_stderr, resource_status)
    if type(reboot_status) is not int or reboot_status != 0:
        raise ValueError("second helper raw status")
    if any(type(value) is not bytes for value in (reboot_stdout, reboot_stderr, reboot_status_kmsg)):
        raise ValueError("second helper capture types")
    if reboot_stderr or reboot_stdout != BOOT_STDOUT:
        raise ValueError("second strict5 boot output")
    if reboot_status_kmsg != BOOT_KMSG:
        raise ValueError("second strict5 boot status kmsg")
    return {"public_release_then_strict5_boot_protocol": "PASS",
            "native_execution_verified": False, "full_cycle_verified": False}
