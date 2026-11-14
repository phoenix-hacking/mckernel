import os
import tempfile
import unittest
from pathlib import Path

from run_layer_b_root13 import Root13Runner, ROOT, State, submission_argv


class Fake:
    def __init__(self, *, pre=True, submit=True, writer=True, stop=True, resolved=True, auth=True):
        self.pre, self.submit, self.writer, self.stop_ok = pre, submit, writer, stop
        self.resolved_ok, self.auth_ok = resolved, auth; self.calls = []; self.files = set()
        self.n = 0
    def uuid(self): return "11111111-1111-4111-8111-111111111111"
    def exists(self, p): return p in self.files
    def unit_exists(self, u): return False
    def authenticate(self, *a): return self.auth_ok
    def mkdir_tree(self, root, names, mode): self.files.update([root] + [root + "/" + n for n in names])
    def mkfifo(self, p, mode): self.files.add(p)
    def write_token(self, p, data, mode): self.files.add(p)
    def fsync_record(self, x): pass
    def run(self, argv, timeout):
        self.calls.append(tuple(argv)); exe = argv[0]
        if any("systemd-run" in x for x in argv): return {"status": 0 if self.submit else 1}
        if any(x.endswith("/dd") for x in argv): return {"status": 0 if self.writer else 1}
        if "stop" in argv: return {"status": 0 if self.stop_ok else 1}
        if "kill" in argv: return {"status": 0}
        if any(x in argv for x in ("journalctl", "sync", "reset-failed")) or any("journalctl" in x for x in argv): return {"status": 0}
        if "show" in argv:
            self.n += 1
            if self.n == 1 and not self.pre: return {"status": 1}
            return {"status": 0, "properties": {"Id": argv[3], "InvocationID": "i",
                    "ControlGroup": "/user.slice/u.service", "ActiveState": "active", "SubState": "exited",
                    "Result": "success", "ExecMainCode": "CLD_EXITED", "ExecMainStatus": "0",
                    "ExecMainExitTimestampMonotonic": "3"}}
        return {"status": 0}
    def show_argv(self, u): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "3s", "/usr/bin/systemctl", "--user", "show", u)
    def sync_argv(self, p): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "2s", "/usr/bin/sync", "-f", p)
    def writer_argv(self, t, f): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "2s", "/usr/bin/dd", "if=" + t, "of=" + f, "bs=1", "count=1", "status=none")
    def stop_argv(self, u): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "6s", "/usr/bin/systemctl", "--user", "stop", u)
    def kill_argv(self, u): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "3s", "/usr/bin/systemctl", "--user", "--signal=SIGKILL", "--kill-who=all", "kill", u)
    def reset_argv(self, u): return ("/usr/bin/systemctl", "--user", "reset-failed", u)
    def journal_argv(self, u): return ("/usr/bin/timeout", "--signal=TERM", "--kill-after=1s", "6s", "/usr/bin/journalctl", "--user", "-u", u)
    def valid_pre_ack(self, r, u): return bool(self.pre and r.get("properties", r).get("ControlGroup"))
    def valid_success(self, r, u): return r.get("properties", r).get("Result") == "success"
    def resolved(self, r, u): return self.resolved_ok
    def reset_eligible(self, r, u): return False
    def inventory(self, root): return {"root": root}


class Root13Tests(unittest.TestCase):
    def test_local_token_is_exclusive_and_durable_shape(self):
        from run_layer_b_root13 import LocalBackend
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "token")
            LocalBackend().write_token(p, b"A", 0o600)
            self.assertEqual(Path(p).read_bytes(), b"A")
            with self.assertRaises(FileExistsError):
                LocalBackend().write_token(p, b"A", 0o600)

    def test_cleanup_operation_exception_is_unresolved(self):
        b = Fake()
        original = b.stop_argv
        b.stop_argv = lambda u: (_ for _ in ()).throw(RuntimeError("stop transport"))
        r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "FAIL_UNRESOLVED")
        b.stop_argv = original

    def test_success_has_one_submission_writer_then_stop_and_journal(self):
        b = Fake(); r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "PASS_COMPILE_ONLY")
        self.assertEqual(sum(any("systemd-run" in a for a in x) for x in b.calls), 1)
        self.assertTrue(any(any("/dd" in a for a in x) for x in b.calls))
        self.assertTrue(any(any("journalctl" in a for a in x) for x in b.calls))

    def test_preack_failure_queries_before_stop_and_never_writes(self):
        b = Fake(pre=False); r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "FAIL"); self.assertFalse(any(any("/dd" in a for a in x) for x in b.calls))
        self.assertLess(next(i for i,x in enumerate(b.calls) if "show" in x), next(i for i,x in enumerate(b.calls) if "stop" in x))

    def test_writer_failure_is_not_retried(self):
        b = Fake(writer=False); r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "FAIL"); self.assertEqual(sum(any("/dd" in a for a in x) for x in b.calls), 1)

    def test_stop_failure_uses_manager_kill(self):
        b = Fake(stop=False); r = Root13Runner(b).run()
        self.assertTrue(r.killed); self.assertTrue(any("--kill-who=all" in x for x in b.calls))

    def test_unresolved_residual_is_distinct(self):
        b = Fake(resolved=False); r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "FAIL_UNRESOLVED")

    def test_stale_root_refused_without_commands(self):
        b = Fake(); b.files.add(ROOT); r = Root13Runner(b).run()
        self.assertEqual(r.terminal, "FAIL"); self.assertFalse(b.calls)

    def test_observer_rejection_is_fail_closed(self):
        b = Fake(); r = Root13Runner(b, observer=lambda _: False).run()
        self.assertEqual(r.terminal, "FAIL"); self.assertFalse(any(any("/dd" in a for a in x) for x in b.calls))

    def test_argv_has_exact_limits_and_no_shell(self):
        a = submission_argv(ROOT, "layer-b-native-owner-bootstrap-root13-20260928-28-11111111-1111-4111-8111-111111111111.service")
        self.assertIn("--property=TimeoutStartSec=120s", a); self.assertIn("--property=ExecStartPre=/usr/bin/cat " + ROOT + "/logs/identity.fifo", a)
        self.assertNotIn("/bin/sh", a); self.assertEqual(a.count("/usr/bin/gcc"), 1)


if __name__ == "__main__": unittest.main()
