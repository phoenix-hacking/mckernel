"""Exact call() AST regressions; every client, birth read and wait is a mock."""
import ast
import copy
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
OUTPUT = HERE / "output-1"
BASELINE = pathlib.Path("/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1/terminate-exit-incremental-1/compiler-correction-1/run_root_once.py")
CANDIDATE = pathlib.Path("/home/holden/mckernel-work/m14-blocker-resolution-20261110/joint-provider-operation-sdk-max-1/capture-correction-1/call_capture.py")
SOURCE_HASHES = {
    BASELINE: "e6091bb418f619222f7a51ddef718ceeb75bb449f5abd10d62b40018b623db38",
    CANDIDATE: "e088b7ecbc27598e450395eb9c18672da2696c8c4da8bc1c8e4b492b8f2037b4",
}
ARGV = ["/mock/owned-client"]
PID = 450001
BIRTH = "900001"


def source_function(path):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SOURCE_HASHES[path]
    tree = ast.parse(data.decode(), filename=str(path))
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "call"]
    assert len(functions) == 1
    # Only the actual unchanged FunctionDef is compiled, never the driver body.
    return ast.Module(body=functions, type_ignores=[])


class Scenario:
    def __init__(self, path, name, mode):
        self.directory = OUTPUT / name
        self.directory.mkdir()
        self.path = path
        self.mode = mode
        self.clients = []
        self.pending = {}
        self.snapshots = []
        self.forbidden = []
        self.waits = []
        self.kwargs = None
        self.popen_calls = 0
        self.attempt_before_popen = False
        self.returned_before_birth = False
        self.returncode = None
        self.pid = PID
        self.birth_error = ProcessLookupError("mock birth read failed after Popen")
        self.timeout_error = subprocess.TimeoutExpired(ARGV, 30)
        self.secondary_timeout = subprocess.TimeoutExpired(ARGV, 6)
        self.primary = self.birth_error if mode == "birth" else self.timeout_error
        self.diagnostic = io.StringIO()

    def receipt(self):
        path = self.directory / "CLIENTS.json"
        return json.loads(path.read_text()) if path.exists() else None

    def save(self, name, data):
        assert name == "CLIENTS.json"
        snapshot = copy.deepcopy(data)
        (self.directory / name).write_text(json.dumps(snapshot, sort_keys=True) + "\n")
        assert self.receipt() == snapshot
        self.snapshots.append(snapshot)

    def denied(self, *args, **kwargs):
        self.forbidden.append("forbidden process or permission fallback")
        raise AssertionError("no real process control is available in this fixture")

    def popen(self, argv, **kwargs):
        assert argv == ARGV and self.popen_calls == 0
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["env"] == {"MOCK_CAPTURE_ONLY": "1"}
        assert kwargs["cwd"] == "/mock/source-root"
        assert kwargs["start_new_session"] is True
        self.popen_calls += 1
        self.kwargs = kwargs
        before = self.receipt()
        self.attempt_before_popen = bool(before and len(before) == 1 and
            before[0].get("creation_attempted") is True and
            before[0].get("popen_returned") is False)
        assert not kwargs["stdout"].closed and not kwargs["stderr"].closed
        kwargs["stdout"].write(b"mock client stdout; no command ran\n")
        return self

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.mode == "birth":
            assert timeout == 6 and len(self.waits) == 1
            self.returncode = 0
            return 0
        if len(self.waits) == 1:
            assert timeout == 30
            raise self.timeout_error
        assert timeout == 6 and len(self.waits) == 2
        if self.mode == "unresolved":
            raise self.secondary_timeout
        self.returncode = 0
        return 0

    def stat_path(self, path):
        assert str(path) == "/proc/%d/stat" % PID
        scenario = self

        class StatPath:
            def read_text(self):
                before = scenario.receipt()
                scenario.returned_before_birth = bool(before and len(before) == 1 and
                    before[0].get("popen_returned") is True and
                    before[0].get("pid") == PID and
                    before[0].get("creation_attempted") is True)
                if scenario.mode == "birth":
                    raise scenario.birth_error
                # Actual /proc stat parser field19 after the closing comm token.
                return "%d (mock-client) S %s" % (PID, " ".join(["0"] * 18 + [BIRTH]))

        return StatPath()

    def invoke(self):
        fake_subprocess = types.SimpleNamespace(
            Popen=self.popen, DEVNULL=subprocess.DEVNULL,
            TimeoutExpired=subprocess.TimeoutExpired, run=self.denied,
            call=self.denied, check_call=self.denied, check_output=self.denied)
        namespace = {
            "OUT": self.directory, "ROOT": pathlib.Path("/mock/source-root"),
            "ENV": {"MOCK_CAPTURE_ONLY": "1"}, "clients": self.clients,
            "pending_calls": self.pending, "save": self.save,
            "pathlib": types.SimpleNamespace(Path=self.stat_path),
            "subprocess": fake_subprocess,
            "os": types.SimpleNamespace(killpg=self.denied, kill=self.denied,
                                         system=self.denied),
            "sys": types.SimpleNamespace(stderr=self.diagnostic),
        }
        # The actual baseline's bound namespace lacks signal, as frozen NO_GO2720.
        # Candidate source uses neither signal nor killpg; no real Popen is exposed.
        exec(compile(source_function(self.path), str(self.path), "exec"), namespace)
        caught = None
        try:
            namespace["call"]("mock-client", ARGV, timeout=30)
        except BaseException as error:
            caught = error
        assert self.popen_calls == 1 and self.kwargs is not None
        closed = self.kwargs["stdout"].closed and self.kwargs["stderr"].closed
        durable = self.receipt()
        assert not self.forbidden
        if self.clients:
            assert len(self.clients) == 1 and durable == self.clients
            rec = self.clients[0]
            assert rec["attempt_id"] == 0
            assert all(s[0]["attempt_id"] == 0 for s in self.snapshots)
            assert rec["pid"] == PID and rec["label"] == "mock-client" and rec["argv"] == ARGV
            assert rec["streams_closed"] == closed
            assert rec["primary_error"].startswith(type(self.primary).__name__ + ": ")
            if rec["secondary_errors"]:
                assert len(rec["secondary_errors"]) == 1
                assert rec["secondary_errors"][0].startswith("bounded direct wait: TimeoutExpired: ")
            record = {key: rec[key] for key in (
                "attempt_id", "creation_attempted", "popen_returned", "pid", "birth", "exit",
                "direct_wait_joined", "streams_closed", "receipt_persisted",
                "lifecycle_UNKNOWN", "resource_charge_retained")}
            record["secondary_wait_errors"] = len(rec["secondary_errors"])
        else:
            assert durable is None
            record = None
        retained = bool(self.pending)
        if retained:
            assert self.pending == {0: self}
        return {
            "exception": type(caught).__name__ if caught is not None else None,
            "same_primary_exception_object": caught is self.primary,
            "popen_calls": self.popen_calls, "wait_timeouts": self.waits,
            "streams_closed": closed, "durable_receipt": durable is not None,
            "durable_attempt_before_Popen": self.attempt_before_popen,
            "durable_returned_client_before_birth": self.returned_before_birth,
            "record": record, "pending_same_handle_retained": retained,
            "forbidden_actions": self.forbidden,
        }


def main():
    assert OUTPUT.is_dir() and (OUTPUT / "tmp").is_dir()
    rows = [
        {"id": "post-Popen-birth-read-failure",
         "baseline": Scenario(BASELINE, "birth-baseline", "birth").invoke(),
         "candidate": Scenario(CANDIDATE, "birth-candidate", "birth").invoke()},
        {"id": "timeout-primary-terminal-bounded-wait",
         "baseline": Scenario(BASELINE, "timeout-baseline", "terminal").invoke(),
         "candidate": Scenario(CANDIDATE, "timeout-terminal-candidate", "terminal").invoke()},
        {"id": "timeout-unresolved-client-control",
         "candidate": Scenario(CANDIDATE, "timeout-unresolved-candidate", "unresolved").invoke()},
    ]
    print(json.dumps({"status": "PASS_MOCKED_CHANGED_CAPTURE_CALL_CASES", "case_count": 3,
        "actual_OS_clients": 0, "actual_helper_Docker_network_or_native": False,
        "actual_call_AST_invocations": 5, "cases": rows}, sort_keys=True))


if __name__ == "__main__":
    main()
