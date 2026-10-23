"""Functional McKernel OS/apps only; no security testing.

Finite stdout oracle for the frozen fdf466 state app. Synthetic input parsing
executes no app, CPUID, register instruction, guest or privileged operation.
"""
import re

STATE_ORACLE = {"kind": "m07-private-used-state-fdf466-v1",
                "required_mask": "0000000000000218",
                "app_sha256": "fdf4661f2da7b1002327c26e3a8473b35e57288abd3d13c9b8f0ab5ca217d023"}


class StateOracleError(ValueError):
    pass


def validate_state_oracle(oracle):
    if type(oracle) is not dict or oracle != STATE_ORACLE:
        raise StateOracleError("state oracle identity")


def check_state_stdout(data, exit_code, oracle):
    """Check exact ordered producer grammar and recompute eligibility.

    Preserved markers attest only the frozen app's real seed/compare/restore
    checks; the parser cannot independently observe register bytes. Partial
    outcomes explicitly carry preservation_pass=False, even with valid rows.
    Failure exits never produce preservation credit.
    """
    validate_state_oracle(oracle)
    if type(data) is not bytes or not 0 < len(data) <= 16384:
        raise StateOracleError("state stdout size/type")
    if type(exit_code) is not int or exit_code not in (0, 77):
        raise StateOracleError("state app failure/nonterminal exit")
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise StateOracleError("state stdout ASCII") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise StateOracleError("state stdout framing")
    lines = iter(text.splitlines())

    def row(pattern):
        try:
            line = next(lines)
        except StopIteration as exc:
            raise StateOracleError("missing state row") from exc
        match = re.fullmatch(pattern, line)
        if match is None:
            raise StateOracleError("unexpected/malformed state row: " + line)
        return match.groups()

    h8 = r"([0-9a-f]{8})"
    h16 = r"([0-9a-f]{16})"
    # Exposure::default is also used for either pre-XGETBV early return.
    c1 = c7b = c7c = xcr0 = supported = extent = 0
    components = [(0, 0, 0, 0)] * 3
    first = next(lines)
    low = re.fullmatch(r"USED_STATE_CPUID maximum=" + h8 + r" insufficient", first)
    if low:
        if int(low[1], 16) >= 13:
            raise StateOracleError("false insufficient CPUID maximum")
    else:
        match = re.fullmatch(r"USED_STATE_CPUID1 ecx=" + h8, first)
        if not match:
            raise StateOracleError("missing CPUID1")
        c1 = int(match[1], 16)
        c7b, c7c = [int(v, 16) for v in row(r"USED_STATE_CPUID7 ebx=" + h8 + r" ecx=" + h8)]
        if c1 & (3 << 26) == 3 << 26:
            xcr0, lo, extent, unused_ecx, hi = [int(v, 16) for v in row(
                r"USED_STATE_XCR0=" + h16 + r" CPUIDD0 eax=" + h8 +
                r" ebx=" + h8 + r" ecx=" + h8 + r" edx=" + h8)]
            supported = (hi << 32) | lo
            components = []
            for component in (3, 4, 9):
                values = row(r"USED_STATE_COMPONENT id=" + str(component) +
                             r" size=(0|[1-9][0-9]*) offset=(0|[1-9][0-9]*) ecx=" + h8 + r" edx=" + h8)
                size, offset = [int(v) for v in values[:2]]
                if max(size, offset) > 0xffffffff:
                    raise StateOracleError("component u32 overflow")
                components.append((size, offset, int(values[2], 16), int(values[3], 16)))

    def layout(index, size):
        n, offset, ecx, edx = components[index]
        return (n == size and ecx & 1 == 0 and edx == 0 and offset >= 576 and
                offset + n <= 0xffffffff and offset + n <= extent and offset + n <= 4096)

    reasons = ["NOTEXECUTED osxsave-or-layout"] * 3
    selected = 0
    if c1 & (3 << 26) == 3 << 26 and 576 <= extent <= 4096:
        mpx = ("NOTEXECUTED mpx-cpuid-missing" if not c7b & (1 << 14) else
               "NOTEXECUTED mpx-xcr0-pair-missing" if (xcr0 & supported) & 0x18 != 0x18 else
               "NOTEXECUTED mpx-user-standard-layout" if not layout(0, 64) or not layout(1, 64) else
               "ELIGIBLE_PENDING")
        pkru = ("NOTEXECUTED pku-cpuid-missing" if not c7c & (1 << 3) else
                "NOTEXECUTED ospke-clear" if not c7c & (1 << 4) else
                "NOTEXECUTED pkru-xcr0-missing" if (xcr0 & supported) & 0x200 == 0 else
                "NOTEXECUTED pkru-user-standard-layout" if not layout(2, 8) else "ELIGIBLE_PENDING")
        reasons = [mpx, mpx, pkru]
        selected = (0x18 if mpx == "ELIGIBLE_PENDING" else 0) | (0x200 if pkru == "ELIGIBLE_PENDING" else 0)
        bits = (8, 16, 512)
        if any(selected & bits[i] and selected & bits[j] and
               components[i][1] < components[j][1] + components[j][0] and
               components[j][1] < components[i][1] + components[i][0]
               for i in range(3) for j in range(i + 1, 3)):
            reasons = ["NOTEXECUTED overlapping-layout"] * 3
            selected = 0
    for component, reason in zip((3, 4, 9), reasons):
        row(re.escape("USED_STATE_ELIGIBILITY id={} {}".format(component, reason)))
    row("USED_STATE_REQUIRED=0000000000000218 SELECTED={:016x}".format(selected))
    if selected == 0:
        row("USED_STATE_NOTEXECUTED no executable selected component")
    else:
        for suffix in ("SYSCALL_PRESERVED mask={:016x} original_restored=1",
                       "FUTEX_PRESERVED mask={:016x} waiter_and_distinct_waker_restored=1",
                       "SIGNAL_PRESERVED mask={:016x} distinct_handler_observed=1 original_restored=1"):
            row("USED_STATE_" + suffix.format(selected))
        for component in (3, 4, 9):
            if selected & (1 << component):
                row("USED_STATE_COMPONENT_PRESERVED id={} syscall=1 blocking_futex=1 signal=1 original_restore=1".format(component))
        if selected == 0x218:
            row("USED_STATE_ALL_SELECTED_PRESERVED mask=0000000000000218")
        else:
            row("USED_STATE_PARTIAL required=0000000000000218 notexecuted={:016x}".format(0x218 & ~selected))
    if list(lines):
        raise StateOracleError("extra/duplicate state rows")
    expected_exit = 0 if selected == 0x218 else 77
    if exit_code != expected_exit:
        raise StateOracleError("state completeness/exit mismatch")
    return {"status": "STATE_PRESERVATION_PASS" if exit_code == 0 else "STATE_PARTIAL_NOT_PASS",
            "preservation_pass": exit_code == 0, "required_mask": 0x218,
            "selected_mask": selected, "notexecuted_mask": 0x218 & ~selected,
            "component_reasons": dict(zip((3, 4, 9), reasons)), "exit_code": exit_code,
            "source_attestation_only": "Frozen app markers follow actual seed/compare/restore checks; no independent register-byte read by consumer."}
