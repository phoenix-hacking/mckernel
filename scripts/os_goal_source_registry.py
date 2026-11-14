"""Read the original Root's current source/ownership records, without releasing.

Functional McKernel OS/Rust only; no security testing. ``Campaign`` installs this
adapter normally. Its input is ``<campaign directory>/source-work-registry.json``
(or the explicit --source-work-registry-file), supplied by the original Root
compositor and original Popen/custody owners. No discovery, process launch, new
queue, account read, admission or resource retirement occurs in this module.

Producer contract (all refs are exact {path, bytes, sha256} objects)::

  {schema: RECORD_SCHEMA, owner: <current account-control owner>,
   observed_utc_ns: <int>, observed_mono_ns: <int>,
   allowed_roots: [<absolute source roots>], hold_fields: [<held lane fields>],
   process_roots: [{pid, start, role: "controller"|"worker"}],
   operations: [{id, admission: <ref>, custody: <ref>,
                 exclusive_scope: {scope: "operation",
                   source_access: "disjoint_paths", protected_paths: [...]}}],
   review: <ref>}

The peer review has schema REVIEW_SCHEMA, the SAME owner, decision
   PASS_SOURCE_COORDINATION_ONLY, records_sha256 (the record excluding ``review``
   and the two observation clocks),
the ordered operation_ids, and reviewer_thread_id/reviewer_turn_id. The current
controller authenticates that direct canonical review child and completed turn;
its actual completed agentMessage must contain exactly
{schema: ATTESTATION_SCHEMA, records_sha256, review_sha256, operation_ids} while
that same observed review turn is active. Only this original controller's event
stream can supply that memory-only attestation. A local review JSON or a completed
turn by itself cannot prove which inventory the peer reviewed. The review
must cover the full original operation inventory, including every UNKNOWN and
source/lease exclusion, not only the attachments proposed for dispatch.

Admissions are parsed using the two actual current publisher/action formats.
The action's execution ADMISSION must pin its external Root grant; a file named
UNISSUED alone is insufficient. Custody is the original call-capture CLIENTS list
or keeper RESULT's clients, pinning that admission in the original argv. It can
only retain a charge. Missing original ledger/capture/peer proof closes dispatch
and names its supplying owner; narrative incident requests cannot substitute.
"""

import copy
import hashlib
import json
from pathlib import Path
import time

from os_goal_source_work import (_digest, _fresh, _integer, _path, _read_bytes,
                                 _require, _sha, _text, LANE_HOLDS)


RECORD_SCHEMA = "mckernel-source-work-records-v1"
REVIEW_SCHEMA = "mckernel-source-work-review-v1"
ATTESTATION_SCHEMA = "mckernel-source-work-peer-output-v1"
PUBLISHER_SCHEMA = "mckernel.Root-exact-reporting-normal-publisher-admission.v1"
ACTION_SCHEMA = "mckernel.Root-current-HOST-admission.current-4296-one-parent-nine.v1"
CANONICAL_SLOTS = frozenset({
    "native_current_binding", "native_binding_review", "time_functional_source",
    "proc_vm_index_fix", "m15_installed_leaf_review", "functional_delta_review"})
REVIEW_SLOTS = frozenset({"native_binding_review", "m15_installed_leaf_review",
                          "functional_delta_review"})
MAX_REGISTRY_BYTES = 512 * 1024
MAX_OPERATIONS = 128
TERMINAL = frozenset({"completed", "failed", "interrupted"})


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "Duplicate original registry key")
        value[key] = item
    return value


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ValueError("Nonfinite original registry value")))


def _reference(ref):
    _require(isinstance(ref, dict) and set(ref) == {"path", "bytes", "sha256"},
             "Exact original admission/custody/review reference is required")
    raw = _read_bytes(_path(ref["path"]), MAX_REGISTRY_BYTES)
    _require(len(raw) == _integer(ref["bytes"], "original record bytes", 1)
             and hashlib.sha256(raw).hexdigest() == _sha(ref["sha256"]),
             "Original admission/custody/review bytes changed")
    return _json(raw)


def _admission(ref, owner):
    """Read actual original admission operands; never treat them as a new GO."""
    actual = grant = _reference(ref)
    _require(isinstance(actual, dict), "Original Root admission must be an object")
    if actual.get("schema") == PUBLISHER_SCHEMA:
        root = actual.get("saved_Root")
        charge = {"planning_bytes": actual["new_current_family_bytes"],
                  "jobs": actual["new_current_jobs"]}
        review = actual["operation_review"]
        argv_record = _reference(actual["approved_argv"])
        argv = argv_record.get("producer_argv") if isinstance(argv_record, dict) else None
        _require(isinstance(argv, list) and argv and all(isinstance(arg, str) for arg in argv),
                 "Original approved publisher argv is unavailable")
        call_pin = {"argv": argv}
    else:
        # This is the genuine execution ADMISSION, not the proposed external
        # grant or a retrospective operator request. Join all of its pins.
        _require(actual.get("external_charge_used_not_reissued") is True
                 and actual.get("accepted_account_method") == "account/rateLimits/read"
                 and actual.get("accepted_account_source") == "read",
                 "Original action execution ADMISSION is missing; supplier: original Popen owner")
        grant_ref = actual["external_grant_reference"]
        # Actual old refs may include source stat metadata. Keep their exact
        # identity operands; do not require that historical metadata be live.
        grant = _reference({key: grant_ref[key] for key in ("path", "bytes", "sha256")})
        _require(grant.get("schema") == ACTION_SCHEMA
                 and actual.get("operation_review_reference") == grant.get("runtime_operation_review"),
                 "Original action execution/grant/peer review join differs")
        root, charge, review = grant.get("Root_thread_id"), grant["charge"], grant["runtime_operation_review"]
        call_pin = {"reference": grant_ref}
    _require(root == owner["thread_id"]
             and grant.get("invocation") == Path(owner["log_dir"]).name
             and grant.get("same_Root_finite_credit_run_id") == owner["credit_run_id"],
             "Original admission Root/invocation/finite credit run differs")
    # Positive exact review bytes are necessary even though current source
    # dispatch receives no operation permission from this historical admission.
    original_review = _reference(review)
    _require(isinstance(original_review, dict), "Original operation review is unavailable")
    if actual.get("schema") == PUBLISHER_SCHEMA:
        _require(original_review.get("status") == "PASS_ACTUAL_INSTALL_ONLY"
                 and original_review.get("scope") == "ROOT_CODE_INSTALL_ONLY",
                 "Original publisher review is not a positive exact install-only receipt")
    else:
        _require(original_review.get("schema") ==
                 "mckernel.current-4296-one-parent-nine-independent-operation-review.v1"
                 and isinstance(original_review.get("decision"), str)
                 and original_review["decision"].startswith("GO_")
                 and original_review.get("request_sha256") == grant.get("request_sha256"),
                 "Original action peer review/request join differs")
    return ({"planning_bytes": _integer(charge["planning_bytes"], "original planning bytes", 1),
             "jobs": _integer(charge["jobs"], "original jobs", 1)}, call_pin)


def _custody(ref, call_pin):
    value = _reference(ref)
    clients = value.get("clients") if isinstance(value, dict) else value
    _require(isinstance(clients, list) and 1 <= len(clients) <= 128,
             "Original Popen CLIENTS/keeper clients missing; supplier: original owning runtime")
    roots, unknown = [], False
    for row in clients:
        _require(isinstance(row, dict) and row.get("creation_attempted") is True
                 and row.get("popen_returned") is True,
                 "Original Popen creation identity is incomplete")
        argv = row.get("argv")
        # The original capture record must identify this exact admitted call.
        # Merely naming a PID or session in an operator report is insufficient.
        pinned = call_pin.get("reference")
        _require(isinstance(argv, list) and
                 ((pinned is not None and pinned["path"] in argv and pinned["sha256"] in argv)
                  or (pinned is None and argv == call_pin["argv"])),
                 "Original custody argv does not pin the admitted operation")
        pid = _integer(row["pid"], "original Popen pid", 1)
        start = _text(row["birth"], "original Popen birth")
        _require(start.isascii() and start.isdigit(), "Original Popen birth missing")
        _require(type(row.get("direct_wait_joined")) is bool
                 and type(row.get("lifecycle_UNKNOWN")) is bool,
                 "Original owning wait/custody state is missing")
        _require(not row["direct_wait_joined"] or type(row.get("exit")) is int,
                 "Original positive owning wait has no terminal exit receipt")
        unknown |= row["lifecycle_UNKNOWN"] or not row["direct_wait_joined"]
        if not row["direct_wait_joined"]:
            roots.append({"pid": pid, "start": start})
    _require(len({row["pid"] for row in roots}) == len(roots), "Duplicate original custody process")
    # Even a positive wait cannot release leases or the planning charge here.
    return roots, "UNKNOWN" if unknown else "RETAINED"


class SourceWorkRegistry:
    """One normal Campaign adapter; provenance remains in memory this run only."""

    def __init__(self, campaign, path=None, *, clock=None):
        self.campaign = campaign
        self.path = _path(path if path is not None else campaign.directory / "source-work-registry.json")
        self.clock = clock or (lambda: (time.time_ns(), time.monotonic_ns()))
        self.children, self.turns, self.peer_attestations = {}, {}, {}
        # Observed retained operation coverage cannot shrink through a new file
        # or another model turn. This adapter has no physical release operation.
        self.expected_operation_ids = set()

    def observe_child(self, data):
        c, item = self.campaign, data.get("item") or {}
        root, child = c.state.get("thread_id"), item.get("agentThreadId")
        path = item.get("agentPath")
        slot = path[len("/root/"):] if isinstance(path, str) and path.startswith("/root/") else None
        if (slot not in CANONICAL_SLOTS or item.get("type") != "subAgentActivity"
                or item.get("kind") not in {"started", "interacted"} or data.get("threadId") != root
                or not c.active.get(root) or data.get("turnId") != c.active[root]
                or not isinstance(child, str) or not 0 < len(child) <= 128 or child == root):
            return
        prior = self.children.get(child)
        if prior is not None and prior["slot"] != slot:
            prior["ambiguous"] = True
            return
        conflicting = [row for key, row in self.children.items() if row["slot"] == slot and key != child]
        if conflicting:
            # A second thread cannot silently take a canonical saved owner slot.
            for row in conflicting:
                row["ambiguous"] = True
            return
        self.children.setdefault(child, {"root_thread_id": root, "invocation": str(c.log_dir),
            "root_turn_id": data["turnId"], "thread_id": child, "slot": slot,
            "worker_pid": c.state.get("worker_pid"), "worker_start": c.state.get("worker_start"),
            "credit_run_id": getattr(c.credit_guard, "identifier", None), "ambiguous": False})

    def observe_turn(self, thread, turn):
        if thread not in self.children or not isinstance(turn, dict):
            return
        ident, status = turn.get("id"), turn.get("status")
        if not isinstance(ident, str) or not 0 < len(ident) <= 128:
            return
        key = (thread, ident)
        if status == "inProgress":
            self.turns.setdefault(key, {"started": True, "status": status})
        elif status in TERMINAL and key in self.turns:
            self.turns[key]["status"] = status

    def observe_peer_output(self, data):
        """Called only for original-RPC item/completed, never renderer/saved data."""
        c, item = self.campaign, data.get("item") or {}
        thread, turn = data.get("threadId"), data.get("turnId")
        provenance, observed = self.children.get(thread), self.turns.get((thread, turn))
        if (provenance is None or provenance["ambiguous"] or provenance["slot"] not in REVIEW_SLOTS
                or provenance["invocation"] != str(c.log_dir) or observed is None
                or observed["status"] != "inProgress" or c.active.get(thread) != turn
                or item.get("type") != "agentMessage" or not isinstance(item.get("id"), str)):
            return
        text = item.get("text")
        if not isinstance(text, str) or not 0 < len(text) <= 8192:
            return
        try:
            proof = _json(text)
            _require(isinstance(proof, dict) and set(proof) == {
                "schema", "records_sha256", "review_sha256", "operation_ids"}
                and proof["schema"] == ATTESTATION_SCHEMA, "Exact peer output attestation required")
            _sha(proof["records_sha256"])
            _sha(proof["review_sha256"])
            ids = proof["operation_ids"]
            _require(isinstance(ids, list) and 1 <= len(ids) <= MAX_OPERATIONS
                     and all(_text(ident, "peer operation id") for ident in ids)
                     and len(set(ids)) == len(ids), "Peer must name its complete operation inventory")
        except (ValueError, TypeError, KeyError):
            return  # Ordinary peer prose/other JSON never becomes an attestation.
        key = (thread, turn)
        if key in self.peer_attestations:
            prior = self.peer_attestations[key]
            if prior is None or prior["attestation"] != proof:
                self.peer_attestations[key] = None  # Conflicting output stays ambiguous.
            return
        self.peer_attestations[key] = {"attestation": proof, "item_id": item["id"],
            "message_sha256": hashlib.sha256(text.encode()).hexdigest()}
        self.expected_operation_ids.update(ids)

    def terminal(self, thread, turn, owner):
        c = self.campaign
        _require(thread not in c.active and not c.state.get("transport_uncertain"),
                 "An active/uncertain model turn cannot free a logical owner slot")
        provenance = None
        if thread != owner["thread_id"]:
            provenance, observed = self.children.get(thread), self.turns.get((thread, turn))
            _require(provenance is not None and not provenance["ambiguous"]
                     and provenance["root_thread_id"] == owner["thread_id"]
                     and provenance["invocation"] == owner["log_dir"]
                     and all(provenance[key] == owner[key] for key in
                             ("worker_pid", "worker_start", "credit_run_id"))
                     and observed is not None and observed["started"] and observed["status"] in TERMINAL,
                     "No current observed direct canonical child/terminal provenance")
        page = c.rpc.call("thread/turns/list", {"threadId": thread, "limit": 100,
                          "sortDirection": "desc", "itemsView": "notLoaded"})
        rows = page.get("data")
        _require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
                 and not any(row.get("status") not in TERMINAL for row in rows),
                 "Original child/Root has active or uncertain model-turn state")
        _require(thread not in c.active and not c.state.get("transport_uncertain"),
                 "Original model turn changed during its terminal observation")
        matches = [row for row in rows if row.get("id") == turn]
        _require(len(matches) == 1 and matches[0].get("status") in TERMINAL,
                 "Exact original terminal model turn is unavailable")
        if provenance is not None:
            _require(matches[0]["status"] == observed["status"], "Observed child terminal receipt changed")
        result = {"root_thread_id": owner["thread_id"], "invocation": owner["log_dir"],
                  "thread_id": thread, "turn_id": turn, "status": matches[0]["status"]}
        if provenance is not None:
            result.update(slot=provenance["slot"], provenance_sha256=_digest(provenance))
        return result

    def __call__(self, owner):
        try:
            record = _json(_read_bytes(self.path, MAX_REGISTRY_BYTES, private=True))
        except FileNotFoundError as error:
            raise ValueError("Missing current original Root source/operation registry: " + str(self.path)
                + "; suppliers: Root compositor (full operation inventory/exclusive source paths), "
                  "original Popen owners (admission-pinned custody), canonical peer reviewer (exact records proof)") from error
        try:
            _require(isinstance(record, dict) and set(record) == {"schema", "owner", "observed_utc_ns",
                     "observed_mono_ns", "allowed_roots", "hold_fields", "process_roots", "operations", "review"}
                     and record["schema"] == RECORD_SCHEMA and record["owner"] == owner,
                     "Current source/ownership record owner or schema differs")
            _fresh((record["observed_utc_ns"], record["observed_mono_ns"]), self.clock(), 25_000_000_000)
            rows = record["operations"]
            _require(isinstance(rows, list) and 1 <= len(rows) <= MAX_OPERATIONS,
                     "Original Root operation inventory is missing; an empty registry cannot cover retained owners")
            identifiers = [_text(row["id"], "original operation id") for row in rows]
            _require(len(set(identifiers)) == len(identifiers), "Duplicate original operation identity")
            review = _reference(record["review"])
            _require(isinstance(review, dict) and set(review) == {"schema", "owner", "decision", "records_sha256",
                     "operation_ids", "reviewer_thread_id", "reviewer_turn_id"}
                     and review["schema"] == REVIEW_SCHEMA and review["owner"] == owner
                     and review["decision"] == "PASS_SOURCE_COORDINATION_ONLY"
                     and review["records_sha256"] == _digest({k: v for k, v in record.items()
                         if k not in {"review", "observed_utc_ns", "observed_mono_ns"}})
                     and review["operation_ids"] == identifiers,
                     "Exact current full-inventory peer review proof is missing or changed")
            peer = self.terminal(review["reviewer_thread_id"], review["reviewer_turn_id"], owner)
            _require(peer.get("slot") in REVIEW_SLOTS and peer["status"] == "completed",
                     "Full-inventory review must come from an observed completed canonical peer")
            output = self.peer_attestations.get((review["reviewer_thread_id"], review["reviewer_turn_id"]))
            _require(output is not None and output["attestation"] == {
                "schema": ATTESTATION_SCHEMA, "records_sha256": review["records_sha256"],
                "review_sha256": record["review"]["sha256"], "operation_ids": identifiers},
                "Exact inventory/review bytes have no original controller-observed peer output; "
                "supplier: canonical peer reviewing the full original operation inventory")
            _require(self.expected_operation_ids.issubset(identifiers),
                     "Current inventory omits independently observed retained operations; "
                     "supplier: original Root/Popen owners; no physical release is authorized here")
            fields = record["hold_fields"]
            _require(isinstance(fields, list) and fields == sorted(set(fields))
                     and fields and set(fields).issubset(LANE_HOLDS)
                     and set(fields) == {key for key in LANE_HOLDS if self.campaign.state.get(key)},
                     "Current original source/operation lane coverage differs")
            roots = record["allowed_roots"]
            _require(isinstance(roots, list) and roots and str(_path(owner["repo"])) in roots
                     and all(str(_path(root)) == root for root in roots), "Exact current source roots missing")
            retained, scopes = [], []
            for row in rows:
                _require(set(row) == {"id", "admission", "custody", "exclusive_scope"},
                         "Every original operation needs exact admission/custody/source scope")
                charge, call_pin = _admission(row["admission"], owner)
                processes, status = _custody(row["custody"], call_pin)
                retained.append(dict(charge, owner=owner["thread_id"], state=status, process_roots=processes))
                scope = row["exclusive_scope"]
                _require(isinstance(scope, dict) and set(scope) == {"scope", "source_access", "protected_paths"}
                         and scope["scope"] == "operation" and scope["source_access"] == "disjoint_paths"
                         and isinstance(scope["protected_paths"], list) and scope["protected_paths"]
                         and all(str(_path(path)) == path for path in scope["protected_paths"]),
                         "Original operation source exclusivity missing; supplier: Root/source owner")
                scopes.append(copy.deepcopy(scope))
            result = {"allowed_roots": list(roots), "process_roots": copy.deepcopy(record["process_roots"]),
                      "retained_charges": retained, "exclusive_scopes": scopes}
            return dict(result, owner=copy.deepcopy(owner), hold_fields=list(fields),
                        observed_utc_ns=record["observed_utc_ns"], observed_mono_ns=record["observed_mono_ns"],
                        records_sha256=_digest(result), proof_sha256=_digest({"record": record, "peer_output": output}))
        except (KeyError, TypeError) as error:
            raise ValueError("Incomplete original Root record; supplier: original admission/custody/source owner: "
                             + str(error)) from error
        except OSError as error:
            raise ValueError("Missing original admission/custody/source proof " + str(error.filename)
                             + "; supplier: original Root compositor/Popen owning runtime") from error
