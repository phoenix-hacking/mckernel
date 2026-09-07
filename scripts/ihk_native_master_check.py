#!/usr/bin/env python3
"""Fail-closed audit for the bounded native Rust IKC master substrate.

This checker binds the frozen legacy source bytes, reviewed Rust source, and a
Rust 1.92 compile/test fixture.  It cannot grant IHK-009 credit or attest any
kernel build, adapter side effect, or runtime result.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = Path("host-kernel/native-rust/ihk-ikc-master-contract-v1.json")
EXACT_RUSTC_VERSION = (
    "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
)
EXACT_ORACLE_COMMIT = "3114d9e7101ad52030eb3effa849a5c108972a1f"
EXACT_ORACLE_FILES = [
    {
        "path": "ihk/ikc/master.c",
        "sha256": "284f59f328f758e871c5013f7ba933c176bc8410a028a0ce043d6f8632faa97a",
    },
    {
        "path": "ihk/ikc/include/ikc/master.h",
        "sha256": "63fb24c40078b464fa751f1e564a7fa548e3047a91fd54c5cf9029fceb4eefbd",
    },
    {
        "path": "ihk/ikc/include/ikc/msg.h",
        "sha256": "3f88492d20e5177f11298e15401ae460bb7cc7173035b71dcf3074ee319bdf6f",
    },
    {
        "path": "ihk/ikc/include/ikc/queue.h",
        "sha256": "0acb85aee2d3b0b7620a0b222461815c6c96c530c5b7182fe60e8ae52ec4e461",
    },
    {
        "path": "ihk/ikc/linux.c",
        "sha256": "88ae8cebf698c73082cefe819d70e1f83def840fc24f76a2f3b0332445979e5d",
    },
    {
        "path": "ihk/ikc/queue.c",
        "sha256": "260a1582e81f3c1d60211edf6ebe4d5bfb498e8964c395a464f86b0949490eae",
    },
    {
        "path": "ihk/linux/core/mikc.c",
        "sha256": "0612a5b185c30c6c0fadf4e8a29284402517b6a4a131ee6cf8254154d326a0d1",
    },
]
EXPECTED_TESTS = [
    "registry_collision_generation_and_validation",
    "unregister_drains_live_accept_lease_before_reuse",
    "concurrent_lookups_finish_before_listener_reuse",
    "router_preserves_master_messages_errors_release_and_lease",
    "connect_transaction_maps_send_interrupt_error_and_success",
    "disconnect_has_one_initiator_and_preserves_non_status_flags",
]
EXPECTED_DELTAS = [
    "fixed slots own copied listener metadata instead of borrowing legacy listener pointers",
    "registration rejects zero owner and zero sizes instead of deferring a missing handler until accept",
    "generation tokens and explicit unregister prevent port reuse while an accept lease exists",
    "accept work occurs outside the registry transition instead of under the legacy listener spinlock",
    "channel flags use atomic transitions instead of the legacy unlocked DESTROYING read",
    "out-of-order and malformed transaction events fail closed with typed protocol errors",
    "outbound requests reject zero queue and channel cookies before adapter side effects",
    "routing returns typed actions and never allocates, frees, sends, wakes, sleeps, maps queues, or invokes callbacks",
]
EXPECTED_UNPROVEN = [
    "exact built ihk.ko incorporation and Linux Kbuild compilation",
    "kernel adapter ownership for OS-scoped registries and channel allocations",
    "listener callback invocation and packet-handler publication in IRQ context",
    "master send, notification, waiter, queue mapping, and channel free side effects",
    "disconnect timeout, remote failure, teardown, and OS shutdown behavior",
    "KCSAN, lockdep, model-checked ordering, generation exhaustion, and runtime stress",
    "IHK-009 gate completion or credit",
]


class ValidationError(Exception):
    """The contract, frozen oracle, source, or fixture is not acceptable."""


def _object_without_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result = {}  # type: Dict[str, Any]
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=_object_without_duplicates)
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError("cannot load {0}: {1}".format(path, error)) from error
    if not isinstance(value, dict):
        raise ValidationError("{0} must contain a JSON object".format(path))
    return value


def _require_keys(value: Any, expected: Set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError("{0} must be an object".format(label))
    actual = set(value)
    if actual != expected:
        raise ValidationError(
            "{0} keys differ: missing={1}, extra={2}".format(
                label, sorted(expected - actual), sorted(actual - expected)
            )
        )


def _repo_file(repo: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValidationError("{0} must be a non-empty POSIX path".format(label))
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationError("{0} escapes the repository".format(label))
    candidate = repo / path
    try:
        candidate.lstat()
    except OSError as error:
        raise ValidationError("{0} is unavailable: {1}".format(label, error)) from error
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError("{0} must be a regular non-symlink file".format(label))
    try:
        candidate.resolve().relative_to(repo.resolve())
    except ValueError as error:
        raise ValidationError("{0} resolves outside the repository".format(label)) from error
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValidationError("cannot hash {0}: {1}".format(path, error)) from error
    return digest.hexdigest()


def _text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError("cannot read {0}: {1}".format(label, error)) from error


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _require_compact(text: str, fragment: str, label: str) -> None:
    if _compact(fragment) not in _compact(text):
        raise ValidationError("missing {0}".format(label))


def _require_order(text: str, fragments: Iterable[str], label: str) -> None:
    position = -1
    for fragment in fragments:
        position = text.find(fragment, position + 1)
        if position < 0:
            raise ValidationError("{0} lacks ordered fragment: {1}".format(label, fragment))


def _function_body(text: str, name: str) -> str:
    matches = list(re.finditer(r"\bfn\s+{0}\s*\(".format(re.escape(name)), text))
    if len(matches) != 1:
        raise ValidationError("Rust source must define fn {0} exactly once".format(name))
    opening = text.find("{", matches[0].end())
    if opening < 0:
        raise ValidationError("fn {0} has no body".format(name))
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise ValidationError("fn {0} has an unterminated body".format(name))


def _c_function_body(text: str, name: str) -> str:
    pattern = re.compile(
        r"(?:^|\n)(?:static\s+)?(?:int|void)\s+{0}\s*\([^;]*?\)\s*\{{".format(
            re.escape(name)
        ),
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValidationError("legacy C oracle must define {0} exactly once".format(name))
    opening = matches[0].end() - 1
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    raise ValidationError("legacy C function {0} has an unterminated body".format(name))


def _validate_contract(contract: Dict[str, Any]) -> None:
    _require_keys(
        contract,
        {
            "canonical_abi",
            "compile_fixture",
            "configured_fixture",
            "evidence_policy",
            "foundation_status",
            "gate_id",
            "intentional_deltas",
            "legacy_behavior",
            "legacy_oracle",
            "production_source",
            "schema_version",
            "source_contract",
            "unproven",
        },
        "contract",
    )
    if contract["schema_version"] != 1 or contract["gate_id"] != "IHK-009":
        raise ValidationError("unsupported master contract identity")
    if contract["foundation_status"] != "source-only-bounded-master-registry":
        raise ValidationError("foundation status differs or overclaims integration")
    if contract["canonical_abi"] != {
        "path": "host-kernel/native-rust/abi/x86_64.rs",
        "sha256": "89e0f72e821cbef91ad4771f4b4b24515d89035d357dc9c23c935a313b7d12c3",
        "type": "IhkIkcMasterPacket",
    }:
        raise ValidationError("canonical master packet ABI binding differs")

    _require_keys(contract["production_source"], {"path", "sha256"}, "production_source")
    if contract["production_source"]["path"] != "host-kernel/native-rust/ikc_master.rs":
        raise ValidationError("production source path differs")
    _require_keys(
        contract["compile_fixture"],
        {"expected_test_count", "path", "sha256", "test_names"},
        "compile_fixture",
    )
    fixture = contract["compile_fixture"]
    if fixture["path"] != "scripts/tests/fixtures/ihk_native_master_compile.rs":
        raise ValidationError("compile fixture path differs")
    if fixture["expected_test_count"] != 6 or fixture["test_names"] != EXPECTED_TESTS:
        raise ValidationError("compile fixture inventory differs")
    for value, label in (
        (contract["production_source"]["sha256"], "production source"),
        (fixture["sha256"], "compile fixture"),
    ):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValidationError("{0} digest is malformed".format(label))

    _require_keys(contract["legacy_oracle"], {"files", "source_commit"}, "legacy_oracle")
    if contract["legacy_oracle"] != {
        "files": EXACT_ORACLE_FILES,
        "source_commit": EXACT_ORACLE_COMMIT,
    }:
        raise ValidationError("frozen legacy oracle identity differs")

    expected_behavior = {
        "accept_errors": {
            "bad_magic_or_missing_handler": -111,
            "channel_allocation_failure": -12,
            "negative_callback_status_is_positive_reply_errno": True,
            "packet_size_mismatch": -103,
        },
        "connect_errors": {
            "interrupted_wait": -4,
            "null_argument": -22,
            "send_failure": -16,
        },
        "disconnect": {
            "already_destroying": -16,
            "clear_enabled_before_destroying": True,
            "incoming_sets_destroy_acked": True,
            "null_channel": -22,
        },
        "execution_context": {
            "connect_disconnect_may_sleep": True,
            "linux_receive_direct_irq": True,
        },
        "listener": {"capacity": 512, "invalid_port": -22, "occupied_port": -16},
        "messages": {
            "connect": 0x20000001,
            "connect_reply": 0x20000002,
            "disconnect": 0x20000008,
            "packet_on_channel": 0x20000010,
        },
        "routing": {
            "connect_reply_errors_are_positive_errno": True,
            "null_channel_cookie": -2,
            "packet_release_count": 1,
            "reply_key": ["message", "reference"],
        },
    }
    if contract["legacy_behavior"] != expected_behavior:
        raise ValidationError("legacy behavior oracle differs")
    if contract["intentional_deltas"] != EXPECTED_DELTAS:
        raise ValidationError("intentional delta inventory differs")
    if contract["source_contract"] != {
        "allocates": False,
        "capacity": 512,
        "generation_bits": 62,
        "invokes_callbacks": False,
        "maps_queues": False,
        "preserves_negative_callback_status": True,
        "sends_packets": False,
        "sleeps_or_waits": False,
        "wakes_waiters": False,
    }:
        raise ValidationError("source side-effect contract differs or overclaims")
    _require_keys(
        contract["configured_fixture"],
        {
            "compile_arguments",
            "compiler_environment",
            "compiler_version_first_line",
            "run_arguments",
            "status_when_compiler_absent",
        },
        "configured_fixture",
    )
    if contract["configured_fixture"] != {
        "compile_arguments": [
            "--edition=2021",
            "--test",
            "-D",
            "warnings",
            "-C",
            "overflow-checks=yes",
        ],
        "compiler_environment": "IHK_NATIVE_MASTER_RUSTC",
        "compiler_version_first_line": EXACT_RUSTC_VERSION,
        "run_arguments": ["--nocapture", "--test-threads=1"],
        "status_when_compiler_absent": "SKIPPED_NO_CONFIGURED_RUSTC",
    }:
        raise ValidationError("configured Rust fixture contract differs")
    evidence = contract["evidence_policy"]
    _require_keys(
        evidence,
        {
            "built_into_ihk_validated",
            "exact_kernel_compile_validated",
            "gate_credit_eligible",
            "listener_callback_validated",
            "rocky_runtime_validated",
            "routing_side_effects_validated",
            "teardown_validated",
        },
        "evidence_policy",
    )
    if any(value is not False for value in evidence.values()):
        raise ValidationError("source contract cannot claim build, runtime, or gate credit")
    if contract["unproven"] != EXPECTED_UNPROVEN:
        raise ValidationError("unproven blocker inventory differs")


def _validate_oracle(repo: Path, oracle: Dict[str, Any]) -> None:
    files = {}
    for index, item in enumerate(oracle["files"]):
        path = _repo_file(repo, item["path"], "legacy_oracle.files[{0}]".format(index))
        actual = _sha256(path)
        if actual != item["sha256"]:
            raise ValidationError(
                "frozen legacy oracle digest differs for {0}: {1}".format(item["path"], actual)
            )
        files[item["path"]] = _text(path, item["path"])

    master = files["ihk/ikc/master.c"]
    for fragment, label in (
        ("port < 0 || port >= IHK_IKC_MAX_PORT", "listener port validation"),
        ("return -EBUSY;", "occupied listener error"),
        ("*p = param;", "borrowed listener registration"),
        ("!p || !p->handler", "missing listener/handler refusal"),
        ("p->magic != magic", "magic refusal"),
        ("packet_size != p->pkt_size", "packet-size abort"),
        ("newc->flag |= IKC_FLAG_DESTROY_ACKED", "disconnect acknowledgement"),
        ("wq->msg == packet->msg && wq->ref == packet->ref", "reply key"),
        ("ihk_ikc_release_packet((struct ihk_ikc_free_packet *)__packet);", "packet release"),
    ):
        _require_compact(master, fragment, "legacy {0}".format(label))
    if master.count("ihk_ikc_release_packet((struct ihk_ikc_free_packet *)__packet);") != 1:
        raise ValidationError("legacy route must release each master packet exactly once")
    accept = _c_function_body(master, "ihk_ikc_accept")
    _require_order(
        accept,
        [
            "!p || !p->handler",
            "p->magic != magic",
            "packet_size != p->pkt_size",
            "ihk_ikc_create_channel",
            "return -ENOMEM",
            "p->ikc_direction == IHK_IKC_DIRECTION_RECV",
            "ihk_ikc_channel_set_cpu",
            "ihk_ikc_set_regular_channel",
            "p->handler(&ci)",
            "ihk_ikc_free_channel(c)",
            "return r",
            "c->handler = ci.packet_handler",
            "c->remote_channel_va = remote_channel_va",
        ],
        "legacy accept validation/ownership ordering",
    )
    route = _c_function_body(master, "ihk_ikc_master_channel_packet_handler")
    for fragment, label in (
        ("case IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL", "packet-on-channel route"),
        ("ihk_ikc_channel_enabled(c)", "enabled channel guard"),
        ("!ihk_ikc_queue_is_empty(c->recv.queue)", "non-empty queue guard"),
        ("ihk_ikc_recv_handler(c, c->handler, os, 0)", "direct receive handler"),
        ("case IHK_IKC_MASTER_MSG_CONNECT", "connect route"),
        ("r = EINVAL", "positive invalid-port reply status"),
        ("ihk_ikc_spinlock_lock(lock)", "listener lock"),
        ("r = ihk_ikc_accept", "accept callback under legacy lock"),
        ("packet->ref, -r, 0, 0, 0, 0", "positive connect reply errno"),
        ("newc->remote_channel_id = packet->ref", "accepted channel reference"),
        ("ihk_ikc_enable_channel(newc)", "accepted channel enable"),
        ("packet->ref, 0, rq", "successful connect reply"),
        ("case IHK_IKC_MASTER_MSG_CONNECT_REPLY", "connect waiter route"),
        ("case IHK_IKC_MASTER_MSG_DISCONNECT", "disconnect route"),
        ("newc->flag |= IKC_FLAG_DESTROY_ACKED", "disconnect ack flag"),
        ("!(newc->flag & IKC_FLAG_DESTROYING)", "reciprocal disconnect guard"),
        ("ret = ihk_ikc_master_reply_handler(os, packet)", "disconnect waiter wake"),
        ("call_arch_master_packet_handler", "architecture fallback"),
    ):
        _require_compact(route, fragment, "legacy {0}".format(label))
    _require_order(
        _c_function_body(master, "ihk_ikc_connect"),
        [
            "ihk_ikc_wait_reply_prepare",
            "ihk_ikc_master_send",
            "ihk_ikc_wait_master",
            "ihk_ikc_wait_finish",
        ],
        "legacy connect waiter ordering",
    )
    connect = _c_function_body(master, "ihk_ikc_connect")
    for fragment, label in (
        ("return -EINVAL", "null connect error"),
        ("return -ENOMEM", "connect allocation error"),
        ("return -EINTR", "interrupted connect error"),
        ("return -wq.res.param[0]", "remote connect error"),
        ("wq.res.param[1]", "remote queue publication"),
        ("c->remote_channel_va = wq.res.param[3]", "remote channel cookie"),
        ("c->handler = p->handler", "packet handler publication"),
        ("c->send.intr_cpu = p->intr_cpu", "interrupt CPU publication"),
        ("ihk_ikc_enable_channel(c)", "connected channel enable"),
        ("return -EBUSY", "send failure"),
    ):
        _require_compact(connect, fragment, "legacy {0}".format(label))
    _require_order(
        _c_function_body(master, "ihk_ikc_disconnect"),
        [
            "c->flag &= ~IKC_FLAG_ENABLED",
            "c->flag & IKC_FLAG_DESTROYING",
            "c->flag |= IKC_FLAG_DESTROYING",
        ],
        "legacy disconnect ordering",
    )
    disconnect = _c_function_body(master, "ihk_ikc_disconnect")
    for fragment, label in (
        ("return -EINVAL", "null disconnect error"),
        ("return -EBUSY", "duplicate disconnect error"),
        ("__ihk_wait_for_disconnect_ack(c)", "disconnect waiter"),
        ("__ihk_send_disconnect(c)", "acked disconnect send"),
    ):
        _require_compact(disconnect, fragment, "legacy {0}".format(label))
    if "ihk_ikc_free_channel" in disconnect:
        raise ValidationError("legacy disconnect unexpectedly frees channel ownership")
    header = files["ihk/ikc/include/ikc/master.h"]
    _require_compact(header, "#define IHK_IKC_MAX_PORT 512", "legacy port capacity")
    messages = files["ihk/ikc/include/ikc/msg.h"]
    for name, value in (
        ("CONNECT", "0x20000001"),
        ("CONNECT_REPLY", "0x20000002"),
        ("DISCONNECT", "0x20000008"),
        ("PACKET_ON_CHANNEL", "0x20000010"),
    ):
        _require_compact(
            messages,
            "#define IHK_IKC_MASTER_MSG_{0} {1}".format(name, value),
            "legacy message {0}".format(name),
        )
    queue_header = files["ihk/ikc/include/ikc/queue.h"]
    for fragment, label in (
        ("IKC_FLAG_ENABLED = 1", "enabled flag"),
        ("IKC_FLAG_DESTROYING = 2", "destroying flag"),
        ("IKC_FLAG_DESTROY_ACKED = 4", "destroy-acked flag"),
        ("IKC_FLAG_STATUS_MASK = 7", "status mask"),
        ("IKC_FLAG_NO_COPY = 0x10", "no-copy flag"),
        ("(c->flag & IKC_FLAG_STATUS_MASK) == IKC_FLAG_ENABLED", "enabled predicate"),
    ):
        _require_compact(queue_header, fragment, "legacy {0}".format(label))
    queue_source = files["ihk/ikc/queue.c"]
    _require_compact(
        queue_source,
        "channel->flag |= IKC_FLAG_ENABLED",
        "legacy channel enable transition",
    )
    _require_compact(
        queue_source,
        "channel->flag &= ~IKC_FLAG_ENABLED",
        "legacy channel disable transition",
    )
    linux = files["ihk/ikc/linux.c"]
    for fragment, label in (
        ("Pass packets to mcexec threads directly from IRQ context.", "direct IRQ path"),
        ("cannot sleep on semaphores", "non-sleeping IRQ rule"),
        ("return wait_event_interruptible(ws->wait, ws->status);", "process waiter"),
        ("return kmalloc(size, GFP_ATOMIC);", "legacy atomic allocation"),
    ):
        if fragment not in linux:
            raise ValidationError("legacy Linux oracle lacks {0}".format(label))
    mikc = files["ihk/linux/core/mikc.c"]
    _require_compact(mikc, "return &(os->listeners[port]);", "OS-scoped listener table")


def _validate_source(text: str) -> None:
    for token in (
        "pub(crate) struct ListenerRegistry",
        "pub(crate) struct ListenerLease",
        "pub(crate) struct MasterRouter",
        "pub(crate) struct ConnectRequest",
        "pub(crate) struct ConnectTransaction",
        "pub(crate) struct ChannelLifecycle",
        "use super::abi::",
        "slots: [ListenerSlot; N]",
        "release_packet: true",
    ):
        if text.count(token) != 1:
            raise ValidationError("master source lacks unique substrate marker: {0}".format(token))
    if "IhkIkcMasterPacket" not in text:
        raise ValidationError("master source does not consume the canonical master packet")
    lowered = text.lower()
    for pattern, label in (
        (r"\bunsafe\b", "unsafe code"),
        (r"extern\s+\"c\"", "FFI"),
        (r"\bbox\s*::|\bvec\s*!|\bvec\s*<|\balloc\s*::", "allocation"),
        (r"\bkernel\s*::", "kernel side effect"),
        (r"\bthread\s*::", "thread creation"),
        (r"\b(?:sleep|schedule|wait_event|wake_up|kmalloc|kfree)\s*\(", "runtime side effect"),
    ):
        if re.search(pattern, lowered):
            raise ValidationError("master source contains forbidden {0}".format(label))

    register = _function_body(text, "register")
    _require_order(
        register,
        [
            "compare_exchange(observed, registering, Ordering::AcqRel, Ordering::Acquire)",
            "slot.packet_size.store",
            "pack_control(generation, SLOT_ACTIVE), Ordering::Release",
        ],
        "listener publication",
    )
    acquire = _function_body(text, "acquire")
    _require_order(
        acquire,
        [
            "slot.control.load(Ordering::Acquire)",
            "slot.readers.fetch_add(1, Ordering::AcqRel)",
            "slot.control.load(Ordering::Acquire) == control",
            "slot.snapshot(port)",
        ],
        "listener lease acquisition",
    )
    finish = _function_body(text, "finish_draining")
    _require_order(
        finish,
        [
            "slot.readers.load(Ordering::Acquire)",
            "slot.control.compare_exchange",
            "draining",
            "finalizing",
            "slot.clear()",
            "pack_control(generation, SLOT_EMPTY), Ordering::Release",
        ],
        "listener drain before reuse",
    )
    drop_body = _function_body(text, "drop")
    _require_compact(
        drop_body,
        "self.slot.readers.fetch_sub(1, Ordering::Release)",
        "release lease decrement",
    )
    route = _function_body(text, "route")
    for token in (
        "IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL",
        "IHK_IKC_MASTER_MSG_CONNECT",
        "IHK_IKC_MASTER_MSG_CONNECT_REPLY",
        "IHK_IKC_MASTER_MSG_DISCONNECT",
        "MasterError::ConnectionRefused",
        "MasterError::ConnectionAborted",
        "release_packet: true",
    ):
        if token not in route:
            raise ValidationError("route classifier lacks {0}".format(token))
    disconnect = _function_body(text, "begin_disconnect")
    _require_order(
        disconnect,
        [
            "current & IKC_FLAG_DESTROYING",
            "current & !IKC_FLAG_ENABLED",
            "| IKC_FLAG_DESTROYING",
            "compare_exchange_weak(current, next, Ordering::AcqRel, Ordering::Acquire)",
        ],
        "atomic disconnect transition",
    )
    observe = _function_body(text, "observe_disconnect")
    _require_compact(
        observe,
        "fetch_or(IKC_FLAG_DESTROY_ACKED, Ordering::AcqRel)",
        "incoming disconnect acknowledgement",
    )
    request = _function_body(text, "master_packet")
    _require_order(
        request,
        [
            "message: IHK_IKC_MASTER_MSG_CONNECT",
            "reference: self.reference",
            "u64::from(self.packet_size) << 32",
            "self.local_send_queue",
            "self.local_receive_queue",
            "self.local_channel_cookie",
            "self.interrupt_cpu as u32",
            "self.magic as u32",
        ],
        "outbound connect packet encoding",
    )
    reply = _function_body(text, "connect_reply")
    for token in (
        "status.checked_neg()",
        "errno == 0",
        "parameters[0]",
        "success.receive_queue",
        "self.offer.remote_channel_cookie",
        "success.accepted_channel_cookie",
    ):
        if token not in reply:
            raise ValidationError("accept reply lacks legacy callback/error mapping: {0}".format(token))


def _validate_fixture(text: str, expected: List[str]) -> None:
    actual = re.findall(r"#\[test\]\s*fn\s+([a-zA-Z0-9_]+)\s*\(", text)
    if actual != expected:
        raise ValidationError("fixture test definitions differ from the contract")
    for token in (
        "mod ikc_master;",
        "Arc::new(ListenerRegistry",
        "Barrier::new(9)",
        "thread::scope",
        "Err(MasterError::Stale)",
        "Ok(UnregisterState::Pending)",
        "IncomingDisconnectAction::WakeDisconnectWaiter",
        "assert!(result.release_packet)",
    ):
        if token not in text:
            raise ValidationError("fixture lacks concurrency/lifetime assertion: {0}".format(token))
    if text.count("thread::spawn") != 2:
        raise ValidationError("fixture concurrency/lifetime thread inventory differs")


def validate_repository(repo: Path = ROOT) -> Dict[str, Any]:
    repo = Path(repo)
    contract_path = _repo_file(repo, DEFAULT_CONTRACT.as_posix(), "contract")
    contract = _load_json(contract_path)
    _validate_contract(contract)
    _validate_oracle(repo, contract["legacy_oracle"])

    abi = _repo_file(repo, contract["canonical_abi"]["path"], "canonical ABI")
    if _sha256(abi) != contract["canonical_abi"]["sha256"]:
        raise ValidationError("canonical ABI digest differs")
    source = _repo_file(repo, contract["production_source"]["path"], "production source")
    if _sha256(source) != contract["production_source"]["sha256"]:
        raise ValidationError("production source digest differs")
    _validate_source(_text(source, "production source"))
    fixture = _repo_file(repo, contract["compile_fixture"]["path"], "compile fixture")
    if _sha256(fixture) != contract["compile_fixture"]["sha256"]:
        raise ValidationError("compile fixture digest differs")
    _validate_fixture(_text(fixture, "compile fixture"), EXPECTED_TESTS)
    return {
        "gate_id": "IHK-009",
        "source_contract_validated": True,
        **contract["evidence_policy"],
    }


def _compiler_path(configured: str) -> Path:
    path = Path(configured)
    try:
        info = path.lstat()
    except OSError as error:
        raise ValidationError("configured rustc is unavailable: {0}".format(error)) from error
    if path.is_symlink() or not path.is_file() or not os.access(str(path), os.X_OK):
        raise ValidationError("configured rustc must be an executable regular non-symlink file")
    return path.resolve()


def _run(
    command: List[str], label: str, env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=120,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError("{0} could not run: {1}".format(label, error)) from error


def validate_configured_fixture(
    repo: Path = ROOT,
    rustc: Optional[str] = None,
    require_rustc: bool = False,
) -> Dict[str, str]:
    repo = Path(repo)
    validate_repository(repo)
    contract = _load_json(repo / DEFAULT_CONTRACT)
    configured = rustc if rustc is not None else os.environ.get("IHK_NATIVE_MASTER_RUSTC", "")
    if not configured:
        if require_rustc:
            raise ValidationError("configured Rust 1.92 compiler is required but absent")
        return {
            "compiler_version": "NOT_CONFIGURED",
            "fixture_status": "SKIPPED_NO_CONFIGURED_RUSTC",
        }
    compiler = _compiler_path(configured)
    run_env = os.environ.copy()
    bundled_lib64 = compiler.parent.parent / "lib64"
    if bundled_lib64.is_dir() and list(bundled_lib64.glob("librustc_driver-*.so")):
        prior = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = str(bundled_lib64) + ((":" + prior) if prior else "")
    version = _run([str(compiler), "--version"], "configured rustc --version", run_env)
    if version.returncode != 0:
        raise ValidationError("configured rustc --version failed: {0}".format(version.stderr.strip()))
    first_line = version.stdout.splitlines()[0] if version.stdout.splitlines() else ""
    if first_line != EXACT_RUSTC_VERSION:
        raise ValidationError("configured rustc version differs: {0!r}".format(first_line))

    fixture = repo / contract["compile_fixture"]["path"]
    with tempfile.TemporaryDirectory(prefix="ihk-native-master-rustc-") as directory:
        binary = Path(directory) / "fixture"
        command = [str(compiler)] + contract["configured_fixture"]["compile_arguments"]
        command += [str(fixture), "-o", str(binary)]
        compiled = _run(command, "Rust 1.92 fixture compilation", run_env)
        if compiled.returncode != 0:
            raise ValidationError(
                "Rust 1.92 fixture compilation failed: {0}".format(compiled.stderr.strip())
            )
        executed = _run(
            [str(binary)] + contract["configured_fixture"]["run_arguments"],
            "Rust 1.92 fixture execution",
            run_env,
        )
        if executed.returncode != 0:
            raise ValidationError(
                "Rust 1.92 fixture execution failed: {0}".format(
                    (executed.stdout + "\n" + executed.stderr).strip()
                )
            )
        output = executed.stdout + "\n" + executed.stderr
        result = re.search(
            r"test result: ok\. (\d+) passed; 0 failed; 0 ignored; 0 measured; 0 filtered out",
            output,
        )
        if result is None or int(result.group(1)) != contract["compile_fixture"]["expected_test_count"]:
            raise ValidationError("fixture did not report the exact contracted test count")
    return {
        "compiler_version": first_line,
        "fixture_status": "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--rustc")
    parser.add_argument("--require-rustc", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        summary = validate_repository(arguments.repo)
        fixture = validate_configured_fixture(
            arguments.repo,
            rustc=arguments.rustc,
            require_rustc=arguments.require_rustc,
        )
    except ValidationError as error:
        print("IHK-009 SOURCE-CONTRACT-REJECTED: {0}".format(error), file=sys.stderr)
        return 1
    print(
        "IHK-009 SOURCE-CONTRACT-VERIFIED "
        "fixture={0} built_ihk=NOT_PROVEN kernel_compile=NOT_PROVEN "
        "listener_callback=NOT_PROVEN routing_side_effects=NOT_PROVEN "
        "rocky_runtime=NOT_PROVEN teardown=NOT_PROVEN gate_credit=FORBIDDEN".format(
            fixture["fixture_status"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
