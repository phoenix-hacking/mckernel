"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source regressions only; never execute kernel/Rust/ISA/native providers.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).parent
pre = (ROOT / "preimage/kernel/rust/syscall_policy.rs").read_text()
post = (ROOT / "postimage/kernel/rust/syscall_policy.rs").read_text()
constructor = (ROOT / "CONSTRUCTOR.FRAGMENT.rs").read_text()

def body(text):
    start = text.index('pub unsafe extern "C" fn arch_do_signal_trap_stop_result(')
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]

old = body(pre)
new = body(post)

def check_constructor(fragment):
    expected = [
        "let raw = info.cast::<u8>();",
        "while offset < size_of::<SigInfo>()",
        "raw.add(offset).write_volatile(0);",
        "let info_ref = &mut *info;",
        "info_ref.si_signo = SIGCHLD;",
        "info_ref.si_code = CLD_TRAPPED;",
        ".cast::<crate::abi::SigInfoChild>();",
        "core::ptr::addr_of_mut!((*sigchld).si_pid), (*thread).tid,",
        "core::ptr::addr_of_mut!((*sigchld).si_status),",
        "core::ptr::read_volatile(core::ptr::addr_of!((*thread).exit_status)),",
    ]
    positions = [fragment.index(part) for part in expected]
    assert positions == sorted(positions)
    assert "pending" not in re.sub(r"//[^\n]*", "", fragment)
    assert "<<" not in fragment and "assume_init" not in fragment

check_constructor(constructor)
assert new.replace(constructor, "", 1) == old
assert new.index("return 0;") < new.index("(*thread).exit_status = SIGTRAP;")
assert new.index("(*thread).status = PS_TRACED;") < new.index(constructor)
assert new.index(constructor) < new.index("if thread == unsafe { (*proc).main_thread }")
assert new.count("f06_signal_trap_notify(") == 2
for target in ("parent_pid", "report_pid"):
    assert f"f06_signal_trap_notify(thread, {target}, -1, SIGCHLD, info, 0);" in new
assert new.index("__mcs_rwlock_writer_unlock") < new.index("let parent_pid")
assert new.index("let report_pid") < new.index("f06_signal_trap_notify(thread, report_pid") < new.index("crate::waitq::waitq_wakeup") < new.index("unsafe { schedule() }")
# Detect the specific field mistakes rejected by the approved independent review.
mutations = {
    "partial_zero": constructor.replace("while offset < size_of::<SigInfo>()", "while offset < 12"),
    "wrong_signo": constructor.replace("si_signo = SIGCHLD", "si_signo = SIGTRAP"),
    "wrong_code": constructor.replace("si_code = CLD_TRAPPED", "si_code = CLD_STOPPED"),
    "process_pid": constructor.replace("(*thread).tid,", "(*proc).pid,"),
    "encoded_status": constructor.replace("(*thread).exit_status)),", "(*thread).exit_status)) << 8,"),
}
for name, mutant in mutations.items():
    try:
        check_constructor(mutant)
    except (AssertionError, ValueError):
        continue
    raise AssertionError("missed mutation: " + name)
# Apply exact unified hunks in memory. This verifies the actual saved patch
# applies to its retained parent-composition preimage and reproduces postimage.
lines = (ROOT / "PRIVATE-NOT-APPLIED.patch").read_text().splitlines(True)
source = pre.splitlines(True)
result = []
cursor = 0
index = 2
while index < len(lines):
    match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[index])
    assert match, lines[index]
    start = int(match[1]) - 1
    assert start >= cursor
    result += source[cursor:start]
    cursor = start
    index += 1
    while index < len(lines) and not lines[index].startswith("@@"):
        line = lines[index]
        if line[0] in " -":
            assert source[cursor] == line[1:]
            cursor += 1
        if line[0] in " +":
            result.append(line[1:])
        index += 1
result += source[cursor:]
assert "".join(result) == post
# All metadata records and selector guards are byte-identical to parent source.
record_pattern = r"static mut F06_SIGNAL_[A-Z_]+_DEBUG[^;]+;"
assert re.findall(record_pattern, pre) == re.findall(record_pattern, post)
assert pre.count("#[cfg(f06_do_signal_whole_candidate)]") == post.count("#[cfg(f06_do_signal_whole_candidate)]")
report = {
    "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
    "status": "PASS_SOURCE_ONLY",
    "checks": ["full-byte zero precedes references and approved field writes", "untraced return avoids storage", "SIGTRAP state precedes constructor", "all original helper effects unchanged after removing constructor", "both exact notification argument lists", "unlock/parent and report/notify/wake/schedule order", "five rejected field mutations", "saved unified patch reproduces postimage", "metadata and OFF selector guards retained"],
    "mutations_rejected": list(mutations),
    "limitations": "Source/order regression only: no Rust execution, compiler, actual layout, codegen, native lifetime or application acceptance proof.",
    "patch_sha256": hashlib.sha256((ROOT / "PRIVATE-NOT-APPLIED.patch").read_bytes()).hexdigest(),
    "postimage_sha256": hashlib.sha256(post.encode()).hexdigest(),
}
(ROOT / "SOURCE-CHECKS.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
