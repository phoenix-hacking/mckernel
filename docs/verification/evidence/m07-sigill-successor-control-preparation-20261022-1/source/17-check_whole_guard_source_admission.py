#!/usr/bin/env python3
"""Ordinary whole guard source evidence join only; never execution authentication.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Requires a separate genuine root ordinary grant; this file does not grant itself.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
R = Path(__file__).resolve().parent
assert sys.executable == '/home/holden/anaconda3/bin/python3' and sys.version_info[:3] == (3, 9, 12)
assert sys.dont_write_bytecode
path = R / 'native_exact_current_optin_image_guard.py'
# Import the complete actual guard and its complete private current owner.
# There is no extraction, monkeypatch, stub or fake PASS review.
spec = importlib.util.spec_from_file_location('_actual_whole_current_guard', str(path))
g = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = g
spec.loader.exec_module(g)
assert g.image.__file__ == str(R / 'native_rust_exact_mckernel_image_container_owner.py')
assert g.image._HOST_OWNER.__file__ == str(Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/adapters/native_rust_exact_build_container_owner.py'))
assert g.image._HOST_OWNER.provenance.__file__ == '/home/holden/mckernel-work/host-preparation/m07-sigill-current-image-successor-preparation-20261022-1/native_rust_exact_build_offline.py'
assert g.BINDINGS is not None
assert sys.modules['native_rust_exact_build_container_owner'] is g.image._HOST_OWNER
assert sys.modules['native_rust_exact_build_offline'] is g.image._HOST_OWNER.provenance
assert sys.modules['native_rust_exact_mckernel_image_container_owner'] is g.image
basis_ref = g.BINDINGS['basis_ref']
request = g.bound(basis_ref)
assert request['native_fork_owned_transaction'] is True
assert request['disk_identity'] == request['source_identity']
ordinary = g.bound(g.VALIDATOR_CAPTURE_REF)
release = {'source_materialization_acceptance': g.SOURCE_REF,
    'whole_source_gate_acceptance': g.GATES_REF,
    'runtime_binding_acceptance': g.BINDINGS['runtime_ref'], 'bound_request_basis': basis_ref,
    'ordinary_result_acceptance': g.GATES_REF,
    'prerequisites': {'ordinary': g.VALIDATOR_CAPTURE_REF}}
# Match authenticate's actual acceptance argument exactly: this is the whole
# source-gate acceptance document, while require reads source acceptance internally.
acceptance = g.bound(release['ordinary_result_acceptance'])
# No PASS_EXECUTION_RELEASE, authenticate/findmnt/development lock/Docker/owner.run.
stat = os.lstat(request['source_root'])
identity = [stat.st_dev, stat.st_ino, stat.st_uid, stat.st_gid, stat.st_mode & 4095]
g.require_actual_ordinary(request, basis_ref['sha256'], release, ordinary, acceptance, identity)
controls = []
def refuse(name, req=None, rel=None, obs=None, ident=None):
    try:
        g.require_actual_ordinary(request if req is None else req, basis_ref['sha256'],
            release if rel is None else rel, ordinary if obs is None else obs, acceptance,
            identity if ident is None else ident)
    except RuntimeError as error:
        controls.append({'name': name, 'exception': type(error).__name__, 'message': str(error)})
    else: raise AssertionError('invalid source evidence admitted: ' + name)
r = copy.deepcopy(request); r['source_derivative_sha256'] = 'f783466fea0907a7a3e04b761c1e8cea9c61251c2d4b3d6f756920d90b89279c'; refuse('retired_source_fingerprint', req=r)
r = copy.deepcopy(request); r['source_root'] += '-absent'; refuse('different_source_path', req=r)
r = copy.deepcopy(request); r['source_identity']['inode'] += 1; refuse('different_source_inode', req=r)
r = copy.deepcopy(release); r['runtime_binding_acceptance'] = g.SOURCE_REF; refuse('wrong_runtime_authority', rel=r)
r = copy.deepcopy(release); r['whole_source_gate_acceptance'] = g.SOURCE_REF; refuse('wrong_whole_gate_authority', rel=r)
r = copy.deepcopy(ordinary); r['closed_streams'] = False; refuse('unclosed_whole_capture', obs=r)
r = list(identity); r[1] += 1; refuse('different_live_identity', ident=r)
r = copy.deepcopy(request); r['native_fork_owned_transaction'] = False; refuse('request_outside_late_identity_allowance', req=r)
print(json.dumps({'status': 'PASS_ACTUAL_WHOLE_GUARD_SOURCE_EVIDENCE_JOIN_ONLY',
    'guard_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'basis_ref': basis_ref, 'source_acceptance': g.SOURCE_REF, 'whole_source_gate_acceptance': g.GATES_REF,
    'whole_guard_import': True, 'actual_current_private_owner_import': True,
    'compiler_root_Docker_lock_lease_guest': False, 'rejection_controls': controls,
    'source_identity': identity}, sort_keys=True))

# Finite successor DATA schema closure; future observations remain explicit nulls.
T=Path("/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/terminal-consumer-preparation-1")
def data(name):return json.loads((R/name).read_text())
pairs=[("terminal-source-bindings.ACTUAL-SOURCE-FUTURE-TARGET-NULL.json","ACTUAL-CURRENT-SOURCE-BINDINGS.FOUR-DOCUMENTS-BOUND.json"),("terminal-case.ACTUAL-SOURCE-FUTURE-ARTIFACT-NULL.json","ACTUAL-CURRENT-CASE.FOUR-DOCUMENTS-BOUND.json"),("terminal-generator.ACTUAL-SOURCE-FUTURE-ARTIFACT-NULL.json","ACTUAL-CURRENT-TERMINAL-GENERATOR-BINDINGS.FOUR-DOCUMENTS-BOUND.json")]
for name,original in pairs:
 current=data(name);accepted=json.loads((T/original).read_text());assert set(current)==set(accepted),(name,"top keyset")
 for key,value in current.items():
  if isinstance(value,dict):assert isinstance(accepted[key],dict) and set(value)==set(accepted[key]),(name,key,"nested keyset")
bindings=data(pairs[0][0]);case=data(pairs[1][0]);generator=data(pairs[2][0])
assert bindings["current_typed_request"]==case["source_identity"]=={k:request[k] for k in bindings["current_typed_request"]}
assert set(bindings["target"])==set(case["target"]) and all(v is None for v in bindings["target"].values()) and all(v is None for v in case["target"].values())
assert all(bindings[k] is None for k in ["artifact_acceptance","logs","physical","source_edit_scope"])
assert case["artifact_acceptance"] is None and case["current_live_postjoin"] is None and case["physical"] is None
assert all(v is None for v in case["finite_roles"].values())
assert len(case["artifact_names"])==9 and case["execution_authorized"] is False
for key in ["driver_path","host_owner_path","provenance_path","source_manifest","toolchain_manifest","gitlink_manifest","image_owner","materialization"]:
 row=bindings["source_refs"][key];assert isinstance(row,dict) and set(row)=={"path","sha256","bytes"}
for key in ["driver_path","provenance_path","source_manifest","gitlink_manifest"]:
 row=bindings["source_refs"][key];payload=Path(row["path"]).read_bytes();assert len(payload)==row["bytes"] and hashlib.sha256(payload).hexdigest()==row["sha256"]
assert generator["artifact"]["source_derivative_sha256"]==request["source_derivative_sha256"] and generator["artifact"]["materialization_sha256"]==request["materialization_sha256"]
assert generator["artifact"]["acceptance"] is None and generator["artifact"]["image"] is None
print(json.dumps({"status":"PASS_COMPLETE_FINITE_TERMINAL_DATA_TOP_AND_NESTED_SCHEMA_CLOSURE_ONLY","terminal_documents":3,"future_targets_artifacts_authority_null":True,"actual_source_basis_and_fingerprints_bound":True},sort_keys=True))
