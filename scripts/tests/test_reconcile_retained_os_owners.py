"""Offline cancellation/metadata contracts; no live /proc, sockets or signals.

Functional McKernel OS/Rust only; no security testing. Run in hosted CI only.
"""
import copy
import importlib.util
from pathlib import Path
import select
import signal
import socket
import stat
import struct
import sys
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "reconcile_retained_os_owners.py"
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location("retained_cleanup", SOURCE)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class MemoryJournal:
    def __init__(self):
        self.rows = []

    def append(self, state, **data):
        self.rows.append(dict(data, state=state))


class CancellationTests(unittest.TestCase):
    def fixture(self, terminal):
        scope = {"schema": "mckernel-old-owner-cancellation-plan-v1",
                 "origin_invocation": cleanup.ORIGIN, "root_thread_id": cleanup.ROOT_THREAD,
                 "credit_run": cleanup.CREDIT_RUN, "boot_id": "boot",
                 "observed_monotonic_ns": 1, "actors": [{"pid": 101, "start": "10"}]}
        review = {"schema": "mckernel-old-owner-cancellation-review-v1",
                  "decision": "GO_EXACT_CANCELLATION_ONLY", "plan_sha256": cleanup.sha(cleanup.canonical(scope)),
                  "helper_sha256": cleanup.sha(SOURCE.read_bytes()), "root_thread_id": cleanup.ROOT_THREAD,
                  "allow_sigkill": False, "no_resource_release": True}
        poller = unittest.mock.Mock()
        poller.poll.return_value = [(51, select.POLLIN)] if terminal else []
        return scope, review, poller

    def run_cancel(self, scope, review, poller, *, table=None, actor_error=None):
        journal = MemoryJournal()
        with patch.object(cleanup, "read", return_value=b"boot\n"), \
             patch.object(cleanup.time, "monotonic_ns", return_value=2), \
             patch.object(cleanup, "same_actor", side_effect=actor_error), \
             patch.object(cleanup, "process_table", return_value=table or {101: {"parent": 1}}), \
             patch.object(cleanup.pidfd_compat, "open_pidfd", return_value=51), \
             patch.object(cleanup.pidfd_compat, "send_signal") as send, \
             patch.object(cleanup.select, "poll", return_value=poller), \
             patch.object(cleanup.os, "close"), \
             patch.object(cleanup.time, "monotonic", side_effect=[0, 10]):
            try:
                cleanup.cancel(scope, review, journal)
            except ValueError:
                pass
        return journal, send

    def test_changed_identity_never_signals(self):
        scope, review, poller = self.fixture(False)
        journal, send = self.run_cancel(scope, review, poller, actor_error=ValueError("changed birth"))
        send.assert_not_called()
        self.assertEqual(journal.rows[-1]["state"], "CANCELLATION_UNKNOWN_RETAINED")

    def test_unlisted_descendant_never_signals(self):
        scope, review, poller = self.fixture(False)
        journal, send = self.run_cancel(scope, review, poller,
                                        table={101: {"parent": 1}, 102: {"parent": 101}})
        send.assert_not_called()
        self.assertEqual(journal.rows[-1]["state"], "CANCELLATION_UNKNOWN_RETAINED")

    def test_term_uses_exact_pidfd_and_bounded_unknown_checkpoint(self):
        scope, review, poller = self.fixture(False)
        journal, send = self.run_cancel(scope, review, poller)
        send.assert_called_once_with(51, signal.SIGTERM)
        self.assertEqual([row["state"] for row in journal.rows], [
            "CANCELLATION_REQUESTED", "BEFORE_SIGNAL", "SIGNAL_RETURNED",
            "CANCELLATION_BOUNDED_CHECKPOINT_UNRESOLVED"])

    def test_terminal_pidfd_never_creates_historical_wait(self):
        scope, review, poller = self.fixture(True)
        # A terminal target still checkpoints pending resource proof; it does
        # not fabricate a waitpid or release. Give the bounded loop one pass.
        journal = MemoryJournal()
        with patch.object(cleanup, "read", return_value=b"boot\n"), \
             patch.object(cleanup.time, "monotonic_ns", return_value=2), \
             patch.object(cleanup, "same_actor"), \
             patch.object(cleanup, "process_table", return_value={101: {"parent": 1}}), \
             patch.object(cleanup.pidfd_compat, "open_pidfd", return_value=51), \
             patch.object(cleanup.pidfd_compat, "send_signal") as send, \
             patch.object(cleanup.select, "poll", return_value=poller), \
             patch.object(cleanup.os, "close"), \
             patch.object(cleanup.time, "monotonic", side_effect=[0, 1]):
            cleanup.cancel(scope, review, journal)
        send.assert_not_called()
        self.assertEqual(journal.rows[-1]["state"], "ALL_PINNED_PIDFDS_TERMINAL_RESOURCE_PROOF_PENDING")

    def test_review_cannot_enable_unreviewed_sigkill(self):
        scope, review, poller = self.fixture(False)
        with self.assertRaisesRegex(ValueError, "review"):
            cleanup.cancel(scope, review, MemoryJournal(), kill_after_term=True)


class UnixDiagnosticTests(unittest.TestCase):
    def message(self, inode=10, peer=11, flags=0):
        payload = struct.pack("=BBBBIII", socket.AF_UNIX, socket.SOCK_SEQPACKET, 1, 0, inode, 0, 0)
        payload += struct.pack("=HHI", 8, 2, peer)
        return struct.pack("=IHHII", 16 + len(payload), 20, flags, 1, 0) + payload

    def test_kernel_peer_metadata_decodes_without_socket_payload(self):
        rows, done = cleanup.decode_unix_diag(self.message(), 1)
        self.assertFalse(done)
        self.assertEqual((rows[0]["inode"], rows[0]["peer"]), (10, 11))

    def test_truncated_or_interrupted_census_refuses(self):
        for raw in (self.message()[:-1], self.message(flags=0x10), self.message()[:10]):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                cleanup.decode_unix_diag(raw, 1)

    def test_kernel_error_refuses(self):
        payload = struct.pack("=i", -1)
        raw = struct.pack("=IHHII", 20, 2, 0, 1, 0) + payload
        with self.assertRaises(ValueError):
            cleanup.decode_unix_diag(raw, 1)

    def test_scoped_channels_include_both_peers_and_pending_connections(self):
        actors = [{"namespaces": {"net": "net:[1]"}, "fds": [{"mode": stat.S_IFSOCK, "inode": 10}]}]
        graph = {10: {"inode": 10, "peer": 11, "pending_connection_inodes": []},
                 11: {"inode": 11, "peer": 10, "pending_connection_inodes": [12]},
                 12: {"inode": 12, "peer": None, "pending_connection_inodes": []}}
        with patch.object(cleanup.os, "readlink", return_value="net:[1]"):
            result = cleanup.scoped_unix_graph(actors, graph)
        self.assertEqual(result["socket_inodes"], [10, 11, 12])
        self.assertEqual(result["missing_socket_inodes"], [])

    def test_missing_peer_preserves_incomplete_scope(self):
        actors = [{"namespaces": {"net": "net:[1]"}, "fds": [{"mode": stat.S_IFSOCK, "inode": 10}]}]
        graph = {10: {"inode": 10, "peer": 11, "pending_connection_inodes": []}}
        with patch.object(cleanup.os, "readlink", return_value="net:[1]"):
            self.assertEqual(cleanup.scoped_unix_graph(actors, graph)["missing_socket_inodes"], [11])


if __name__ == "__main__":
    unittest.main()
