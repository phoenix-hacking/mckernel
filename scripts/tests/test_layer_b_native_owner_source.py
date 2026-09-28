"""Source-derived BPF interpreter and concrete finite ownership models.

No compilation, subprocesses, signals, forks, or seccomp installation. These
are Layer-A checks; syscall adapters and durable I/O still need native tests.
"""
import ast
import errno
import re
import unittest
from dataclasses import dataclass
from pathlib import Path

SOURCE = Path(__file__).with_name("layer_b_native_owner_v1.c")
ARCH, X32 = 0xC000003E, 0x40000000
ALLOW, KILL, DENY = 0x7FFF0000, 0x80000000, 0x00050001
CONSTANTS = {
    "AUDIT_ARCH_X86_64": ARCH, "__X32_SYSCALL_BIT": X32,
    "__NR_socket": 41, "__NR_connect": 42, "AF_INET": 2, "AF_INET6": 10,
    "EPERM": 1, "SECCOMP_RET_ALLOW": ALLOW, "SECCOMP_RET_KILL_PROCESS": KILL,
    "SECCOMP_RET_ERRNO": 0x50000, "SECCOMP_RET_DATA": 0xFFFF,
}


def strip_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def balanced(text, start, opening="(", closing=")"):
    assert text[start] == opening
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == opening:
            depth += 1
        elif text[pos] == closing:
            depth -= 1
            if depth == 0:
                return text[start + 1:pos], pos + 1
    raise ValueError("unbalanced source")


def split_arguments(text):
    depth, start, parts = 0, 0, []
    for pos, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:pos].strip())
            start = pos + 1
    return parts + [text[start:].strip()]


def expression(text, names):
    def visit(item):
        if isinstance(item, ast.Constant) and isinstance(item.value, int):
            return item.value
        if isinstance(item, ast.Name):
            return names[item.id]
        if isinstance(item, ast.BinOp):
            left, right = visit(item.left), visit(item.right)
            if isinstance(item.op, ast.BitOr):
                return left | right
            if isinstance(item.op, ast.BitAnd):
                return left & right
        raise ValueError(ast.dump(item))
    return visit(ast.parse(text, mode="eval").body)


def initializer(text, name):
    match = re.search(r"\b" + name + r"\s*(?:\[[^]]*\])+\s*=\s*\{", text)
    if match is None:
        raise ValueError(name)
    return balanced(text, match.end() - 1, "{", "}")[0]


def parse_bpf(text):
    text = strip_comments(text)
    names = dict(CONSTANTS)
    names["deny"] = expression(re.search(r"unsigned int deny\s*=\s*([^;]+);", text)[1], names)
    body = initializer(text, "program_code")
    instructions, cursor = [], 0
    while cursor < len(body):
        if body[cursor] in " ,\n\t\r":
            cursor += 1
            continue
        match = re.match(r"BPF_(STMT|JUMP)\s*\(", body[cursor:])
        if match is None:
            raise ValueError(body[cursor:])
        args, cursor = balanced(body, cursor + match.end() - 1)
        args = split_arguments(args)
        op = frozenset(part.strip() for part in args[0].split("|"))
        value = args[1]
        if value.startswith("offsetof("):
            value = {"arch": 4, "nr": 0, "args[0]": 16}[
                split_arguments(value[len("offsetof("):-1])[1]]
        else:
            value = expression(value, names)
        jumps = tuple(expression(arg, names) for arg in args[2:])
        if match[1] == "STMT" and jumps or match[1] == "JUMP" and len(jumps) != 2:
            raise ValueError("invalid BPF arity")
        instructions.append((op, value, jumps))
    return instructions


def run_bpf(instructions, arch, number, family=0):
    memory = {0: number & 0xFFFFFFFF, 4: arch, 16: family & 0xFFFFFFFF}
    pc, accumulator = 0, 0
    for _ in range(len(instructions) + 1):
        if not 0 <= pc < len(instructions):
            raise ValueError("branch outside actual program")
        op, value, jumps = instructions[pc]
        if op == frozenset(("BPF_LD", "BPF_W", "BPF_ABS")):
            accumulator = memory[value]
        elif op == frozenset(("BPF_RET", "BPF_K")):
            return value
        elif "BPF_JMP" in op:
            if op == frozenset(("BPF_JMP", "BPF_JEQ", "BPF_K")):
                yes = accumulator == value
            elif op == frozenset(("BPF_JMP", "BPF_JSET", "BPF_K")):
                yes = bool(accumulator & value)
            else:
                raise ValueError(op)
            pc += jumps[0 if yes else 1]
        else:
            raise ValueError(op)
        pc += 1
    raise ValueError("BPF failed to terminate")


def parse_table(text, name, columns=None):
    body = initializer(strip_comments(text), name)
    if columns is None:
        return re.findall(r"\b[A-Z][A-Z_]*\b", body)
    rows = re.findall(r"\{([^{}]+)\}", body)
    table = [re.findall(r"\b[A-Z][A-Z_]*\b", row) for row in rows]
    if any(len(row) != columns for row in table):
        raise ValueError("table width")
    return table


def enum_names(text, name):
    match = re.search(r"enum\s+" + name + r"\s*\{", strip_comments(text))
    body = balanced(strip_comments(text), match.end() - 1, "{", "}")[0]
    entries = tuple(item.strip() for item in body.split(",") if item.strip())
    if not all(re.fullmatch(r"[A-Z_]+", entry) for entry in entries):
        raise ValueError("model requires sequential enum without overrides")
    return entries


@dataclass
class Child:
    pid: int
    identity: int
    root: bool = False
    phase: str = "ACQUIRED"
    terminal: tuple = None


class OwnershipModel:
    """Adapter around actual C child/pass/scan tables, with scripted kernel events.

    Unreaped parentage pins PID identity. Tests model this Linux premise; they
    do not claim that pidfd, signal, or durable filesystem operations executed.
    """
    phases = ("ACQUIRED", "OWNED", "TERMINAL_RECORDED", "RETIRED")
    events = ("ACQUISITION_DURABLE", "TERMINAL_DURABLE", "REAP_SUCCEEDED",
              "NO_STATUS", "WAIT_ERROR", "RECORD_ERROR")
    scans = ("ERROR", "ECHILD", "LIVE", "KNOWN", "NEW", "FULL")

    def __init__(self, text, capacity=64):
        self.phases = enum_names(text, "child_phase")
        self.events = enum_names(text, "child_event")
        self.scans = tuple(name.removeprefix("SCAN_") for name in enum_names(text, "scan_event"))
        self.steps = parse_table(text, "child_steps", 6)
        self.passes = parse_table(text, "pass_actions")
        self.scan_actions = parse_table(text, "scan_actions")
        self.capacity = capacity
        self.children, self.records, self.reaps = [], [], []
        self.sequence, self.operations = 0, 0
        self.unknown_live = self.failed = self.empty = False

    def step(self, child, event):
        child.phase = self.steps[self.phases.index(child.phase)][self.events.index(event)]

    def acquire(self, pid, root=False):
        if any(child.pid == pid for child in self.children):
            raise ValueError("duplicate unreaped identity")
        if len(self.children) == self.capacity:
            raise ValueError("simultaneous capacity")
        self.sequence += 1
        child = Child(pid, self.sequence, root)
        self.children.append(child)
        return child

    def persist(self, child, success=True):
        if child.phase == "ACQUIRED":
            if not success:
                self.step(child, "RECORD_ERROR")
                return False
            self.records.append(("SPAWN" if child.root else "ADOPTED", child.identity))
            self.step(child, "ACQUISITION_DURABLE")
        return True

    def observe(self, child, event):
        self.operations += 1
        if not self.persist(child, event.get("acquire", True)):
            return -1
        if child.phase == "OWNED":
            status = event.get("status")
            if isinstance(status, int):
                self.step(child, "WAIT_ERROR")
                return -1
            if status is None:
                self.step(child, "NO_STATUS")
                return 0
            if not event.get("terminal_record", True):
                self.step(child, "RECORD_ERROR")
                return -1
            child.terminal = status
            self.records.append(("TERMINAL", child.identity))
            self.step(child, "TERMINAL_DURABLE")
        result = event.get("reap", "success")
        if isinstance(result, int):
            self.step(child, "WAIT_ERROR")
            return -1
        if result == "none":
            self.step(child, "NO_STATUS")
            return 0
        self.reaps.append(child.identity)
        self.step(child, "REAP_SUCCEEDED")
        if child.phase == "RETIRED":
            self.children.remove(child)
        return 1

    def scan(self, observation, acquire_record=True):
        self.operations += 1
        if isinstance(observation, int):
            event = "KNOWN" if any(c.pid == observation for c in self.children) else (
                "FULL" if len(self.children) == self.capacity else "NEW")
        else:
            event = observation
        action = self.scan_actions[self.scans.index(event)]
        if action == "CLEAR_PARENT":
            self.unknown_live = False
            if self.children:
                self.failed = True
                self.records.append(("FAILURE", "lost-child-status"))
                self.children.clear()
            self.empty = True
            return "EMPTY"
        if action == "KEEP_PARENT":
            if event == "LIVE" and not self.children:
                self.unknown_live = True
            return "PRESENT"
        if action == "FAIL_SCAN":
            return "ERROR"
        child = self.acquire(observation)
        return "PRESENT" if self.persist(child, acquire_record) else "ERROR"

    def collect(self, events, parent):
        slot, failed = 0, False
        before = self.operations
        while slot < len(self.children):
            if self.operations - before > self.capacity:
                raise ValueError("collection does not make bounded progress")
            result = self.observe(self.children[slot], events.get(self.children[slot].pid, {}))
            action = self.passes[result + 1]
            if action == "STOP_PASS":
                failed = self.failed = True
                break
            if action == "ADVANCE_SLOT":
                slot += 1
        result = self.scan(parent)
        return result if result == "EMPTY" or not failed else "ERROR"


class NativeOwnerSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.bpf = parse_bpf(cls.text)

    def model(self, capacity=64):
        return OwnershipModel(self.text, capacity)

    def test_actual_bpf_socket_and_ordinary_syscall_matrix(self):
        for number in range(550):
            for family in (0, 1, 2, 10, 17, 0x100000002):
                expected = DENY if number == 42 or number == 41 and (family & 0xFFFFFFFF) in (2, 10) else ALLOW
                self.assertEqual(run_bpf(self.bpf, ARCH, number, family), expected, (number, family))

    def test_actual_bpf_rejects_x32_and_non_x86_64(self):
        for number in (0, 41, 42, 59, 435, 0xFFFFFFFF):
            self.assertEqual(run_bpf(self.bpf, ARCH, number | X32, 1), KILL)
            for arch in (0, 0x40000003, 0xC00000B7):
                self.assertEqual(run_bpf(self.bpf, arch, number, 1), KILL)

    def test_original_socket_jump_counterexample(self):
        broken = list(self.bpf)
        index = next(i for i, (op, value, _) in enumerate(broken) if "BPF_JEQ" in op and value == 41)
        op, value, _ = broken[index]
        broken[index] = (op, value, (0, 5))
        self.assertEqual(run_bpf(broken, ARCH, 41, 2), ALLOW)
        self.assertEqual(run_bpf(broken, ARCH, 0), DENY)
        self.assertNotEqual(run_bpf(broken, ARCH, 41, 2), run_bpf(self.bpf, ARCH, 41, 2))

    def test_direct_exit_between_pidfd_check_and_parent_scan(self):
        model = self.model()
        root = model.acquire(42, True)
        model.persist(root)
        self.assertEqual(model.collect({42: {}}, 42), "PRESENT")
        self.assertEqual(len(model.children), 1)
        self.assertEqual(model.records, [("SPAWN", root.identity)])
        self.assertEqual(model.collect({42: {"status": (1, 37)}}, "ECHILD"), "EMPTY")
        self.assertEqual(model.reaps, [root.identity])
        self.assertEqual(model.records[-1], ("TERMINAL", root.identity))

    def test_original_duplicate_adoption_counterexample(self):
        model = self.model()
        model.persist(model.acquire(42, True))
        model.scan_actions[model.scans.index("KNOWN")] = "ACQUIRE_CHILD"
        with self.assertRaisesRegex(ValueError, "duplicate unreaped"):
            model.collect({42: {}}, 42)

    def test_every_wait_error_stops_pass_in_finite_steps(self):
        for failure in (errno.ECHILD, errno.EAGAIN, errno.EINTR, errno.EINVAL, errno.EBADF):
            model = self.model()
            child = model.acquire(42, True)
            model.persist(child)
            self.assertEqual(model.collect({42: {"status": failure}}, "LIVE"), "ERROR")
            self.assertEqual(model.operations, 2)
            self.assertEqual(child.phase, "OWNED")
            self.assertEqual(model.reaps, [])

    def test_original_nonadvancing_error_counterexample(self):
        model = self.model(capacity=2)
        model.persist(model.acquire(42, True))
        model.passes[0] = "COMPACTED_SLOT"
        with self.assertRaisesRegex(ValueError, "bounded progress"):
            model.collect({42: {"status": errno.ECHILD}}, "LIVE")

    def test_terminal_record_not_repeated_after_reap_error_or_no_status(self):
        for reap in (errno.EAGAIN, errno.ECHILD, errno.EINTR, "none"):
            model = self.model()
            child = model.acquire(42, True)
            model.collect({42: {"status": (1, 37), "reap": reap}}, 42)
            self.assertEqual(child.phase, "TERMINAL_RECORDED")
            model.collect({42: {"reap": "success"}}, "ECHILD")
            self.assertEqual(model.records.count(("TERMINAL", child.identity)), 1)
            self.assertEqual(model.reaps, [child.identity])

    def test_authoritative_echild_clears_prior_live_uncertainty(self):
        model = self.model()
        self.assertEqual(model.collect({}, "LIVE"), "PRESENT")
        self.assertTrue(model.unknown_live)
        self.assertEqual(model.scan(84), "PRESENT")
        self.assertEqual(model.records[0][0], "ADOPTED")
        self.assertEqual(model.collect({84: {"status": (1, 0)}}, "ECHILD"), "EMPTY")
        self.assertFalse(model.unknown_live)
        self.assertFalse(model.failed)

    def test_echild_after_lost_owned_status_exits_failed_without_second_reap(self):
        model = self.model()
        model.persist(model.acquire(42, True))
        self.assertEqual(model.collect({42: {"status": errno.ECHILD}}, "ECHILD"), "EMPTY")
        self.assertTrue(model.failed)
        self.assertEqual(model.reaps, [])
        self.assertEqual(model.children, [])

    def test_empty_prefork_or_cleaned_postfork_failure_needs_no_retention(self):
        for previously_spawned in (False, True):
            model = self.model()
            model.failed = True
            events = {}
            if previously_spawned:
                model.acquire(42, True)
                events[42] = {"status": (1, 127)}
            self.assertEqual(model.collect(events, "ECHILD"), "EMPTY")
            self.assertTrue(model.failed)

    def test_failed_records_preserve_ownership(self):
        model = self.model()
        child = model.acquire(42, True)
        self.assertEqual(model.collect({42: {"acquire": False}}, "LIVE"), "ERROR")
        self.assertEqual(child.phase, "ACQUIRED")
        self.assertEqual(model.records, [])
        self.assertEqual(model.collect({42: {"status": (1, 127), "terminal_record": False}}, 42), "ERROR")
        self.assertEqual(child.phase, "OWNED")
        self.assertEqual(model.reaps, [])
        self.assertEqual(model.collect({42: {"status": (1, 127)}}, "ECHILD"), "EMPTY")

    def test_adopted_record_failure_keeps_handle_without_reaping(self):
        model = self.model()
        self.assertEqual(model.scan(84, acquire_record=False), "ERROR")
        self.assertEqual(model.children[0].phase, "ACQUIRED")
        self.assertEqual(model.reaps, [])
        self.assertEqual(model.collect({84: {"status": (1, 0)}}, "ECHILD"), "EMPTY")
        self.assertEqual([entry[0] for entry in model.records], ["ADOPTED", "TERMINAL"])

    def test_known_child_at_capacity_is_not_a_new_acquisition(self):
        model = self.model(capacity=1)
        model.persist(model.acquire(42, True))
        self.assertEqual(model.scan(42), "PRESENT")
        self.assertEqual(model.scan(43), "ERROR")
        self.assertEqual(len(model.children), 1)

    def test_capacity_is_simultaneous_and_pid_reuse_gets_fresh_identity(self):
        model = self.model(capacity=2)
        previous = []
        for _ in range(10):
            child = model.acquire(42, True)
            previous.append(child.identity)
            model.acquire(43)
            self.assertEqual(model.scan(44), "ERROR")
            self.assertEqual(model.collect({42: {"status": (1, 0)}, 43: {"status": (1, 0)}}, "ECHILD"), "EMPTY")
        self.assertEqual(len(set(previous)), 10)
        self.assertEqual(len(model.reaps), 20)

    def test_actual_table_refuses_out_of_order_retirement(self):
        model = self.model()
        for phase in ("ACQUIRED", "OWNED"):
            child = Child(42, 1, phase=phase)
            model.step(child, "REAP_SUCCEEDED")
            self.assertEqual(child.phase, phase)
        for phase in model.phases:
            for event in ("WAIT_ERROR", "RECORD_ERROR", "NO_STATUS"):
                child = Child(42, 1, phase=phase)
                model.step(child, event)
                self.assertEqual(child.phase, phase)

    def test_structural_no_numeric_signal_handoff_shell_or_blocking_wait(self):
        text = strip_comments(self.text)
        for forbidden in (r"\bkill\s*\(", r"\bkillpg\s*\(", r"\bwaitpid\s*\(",
                          r"\bwait\s*\(", r"\bsystem\s*\(", r"\bpopen\s*\(",
                          r"\bexecvp\s*\(", r"acknowledgement", r"takeover"):
            self.assertIsNone(re.search(forbidden, text), forbidden)
        calls = re.findall(r"return waitid\([^;]+;|int rc = waitid\([^;]+;|if \(waitid_pidfd\([^\n]+", text)
        self.assertEqual(len(calls), 4)
        for call in calls:
            self.assertTrue("WNOHANG" in call or "flags" in call)


if __name__ == "__main__":
    unittest.main()
