"""Finalize six failure-only terminal helper literals after actual retention.

No observer, Docker command, cleanup, or export runs here. Independent authority,
publication and execution release remain mandatory external inputs.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import stat

_preparer = Path(__file__).resolve().parent / 'prepare_failure_case.py'
_spec = importlib.util.spec_from_file_location('_new205_failure_source_preparer', _preparer)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
for _name in ('F', 'A', 'H', 'OLD', 'GUARD', 'REVIEW', 'REVIEW_SHA', 'sha', 'ref', 'identity', 'put', 'source', 'once', 'rebind', 'replace_assignments'):
    globals()[_name] = getattr(_module, _name)

NONCE = 'new205-failed-observation-1'

def source_once(name, text):
    if (F / name).exists():
        assert (F / name).read_text() == text, 'frozen source differs: ' + name
    else:
        source(name, text)

def put_once(name, data):
    if (F / name).exists():
        assert json.loads((F / name).read_bytes()) == data, 'frozen data differs: ' + name
    else:
        put(name, data)

def main(cleanup_source_only=False):
    inputs = json.loads((F / 'FAILED-CASE-INPUTS.json').read_bytes())
    assert inputs['retirement']['sha256'] == REVIEW_SHA
    owner = json.loads((A / 'owner-evidence/owner-receipt.json').read_bytes())
    common = A / 'common-exclusion.json'
    cr = json.loads(common.read_bytes())
    shared = Path(owner['shared_heavy_operation']['path'])
    namespace_ancestry = []
    for path in reversed((A, *A.parents)):
        st = path.lstat()
        assert stat.S_ISDIR(st.st_mode)
        namespace_ancestry.append(dict(path=str(path), device=st.st_dev, inode=st.st_ino, mode=st.st_mode, uid=st.st_uid, gid=st.st_gid))
    st = A.stat()
    namespace_binding = dict(device=st.st_dev, inode=st.st_ino, mode=st.st_mode, uid=st.st_uid, gid=st.st_gid)
    target = dict(container_id=owner['container_id'], container_name=owner['container_name'], owner_nonce=owner['owner_nonce'], owner_pid=cr['pid'], owner_starttime=cr['starttime'])
    ledger = []
    for path in sorted(GUARD.glob('command-*/status.json')):
        row = json.loads(path.read_bytes())
        assert row['state'] == 'exited' and row['exit_code'] == 0
        ledger.append(dict(pid=row['pid'], status_path=str(path), status_sha256=sha(path)))
    assert len(ledger) == len({x['pid'] for x in ledger}) == 8
    inspection = F / 'failed-owner-terminal-inspection.json'
    put_once(inspection.name, owner['terminal_container_info'])
    physical = dict(status='PASS_ORDINARY_PHYSICAL_RECORD_JOIN_ONLY', cleanup_authorized=False, physical_release=False, client_count=8, common=identity(common), shared=identity(shared), guard=ref(GUARD / 'guard-result.json'), owner=ref(A / 'owner-evidence/owner-receipt.json'), request=ref(A / 'image-request.json'), current_retirement_review=ref(REVIEW), mutex_postjoin=ref(H / 'failure-mutex-postjoin-readback-1.json'), outer_join=ref(H / 'root-image-execution-1/status.json'), lease_absent=not (A / 'image-lease.json').exists(), ledger=ledger, namespace_ancestry=namespace_ancestry, namespace_binding=namespace_binding, target=target, terminal_inspection=ref(inspection), original_dispatcher_success_postjoin=None)
    put_once('actual-failed-physical-bindings.json', physical)
    cleanup = rebind((OLD / 'cleanup_failed.py').read_text())
    values = dict(NAMESPACE=A, NAMESPACE_ANCESTRY=namespace_ancestry, NAMESPACE_BINDING=namespace_binding, PREFIX='new205-failed-terminal-20261019-1', ATTEMPT=common, REQUEST=A / 'image-request.json', LEASE=A / 'image-lease.json', OUTPUT=A / 'owner-work', EVIDENCE=A / 'owner-evidence', KNOWN_TARGET=target, REQUEST_SHA=sha(A / 'image-request.json'), PUBLISHED_SCRIPT='docs/verification/evidence/new205-failed-terminal-20261019-1/cleanup_failed.py', IMAGE_CANDIDATE=json.loads((A / 'image-request.json').read_bytes())['candidate_sha'], FAILED_GATE=ref(F / 'failed_operation_authority.py'), FAILED_AUTHORITY=F / 'FAILED-BUILD-PRESERVATION-AUTHORITY.json')
    cleanup = replace_assignments(cleanup, values)
    # The accepted cleanup binds the original exact guard directory twice.
    import ast
    literals = {n.value for n in ast.walk(ast.parse(cleanup)) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith('native-rust-') and 'guard-' in n.value}
    assert len(literals) == 1, literals
    guard_literal = literals.pop()
    assert cleanup.count(guard_literal) == 2
    cleanup = cleanup.replace(guard_literal, GUARD.name)
    cleanup = cleanup.replace("'author': '/root/next_live_process_rust_batch'", "'author': '/root/clone_thread_affinity_rust_repair'")
    source_once('cleanup_failed.py', cleanup)
    if cleanup_source_only:
        print('PREPARED_CLEANUP_SOURCE_ONLY retained_pairs=NOT_YET_OBSERVED root=0')
        return
    pairs_path = F / 'retained-production-objects/retained-objects.json'
    pairs = json.loads(pairs_path.read_bytes())
    rows = json.loads((F / 'failed-log-original-authorities.json').read_bytes())
    assert len(pairs) == len(rows) == 12
    assert {(x['original']['path'], x['retained']['path']) for x in pairs} == {(x['original']['path'], x['retained']) for x in rows}
    roles = {Path(x['retained']['path']).name: dict(original=x['original']['path'], retained=x['retained']['path']) for x in pairs}
    observer = rebind((OLD / 'observe_failed_retirement.py').read_text())
    full = json.loads((H / 'source-sha256.json').read_bytes())
    values = dict(FOURLEAF_ROLES=roles, PREP=F, CASE=A, CAPTURE=GUARD, SOURCE=F / 'cleanup_failed.py', SOURCE_SHA=sha(F / 'cleanup_failed.py'), RETIREMENT=F / 'actual-failed-physical-bindings.json', RETIREMENT_SHA=sha(F / 'actual-failed-physical-bindings.json'), NONCE=NONCE, PIDS=tuple(x['pid'] for x in ledger), NEW_OBJECT_AUTHORITY=pairs_path, NEW_OBJECT_AUTHORITY_SHA=sha(pairs_path), ARTIFACT_AUTHORITY=F / 'FAILED-BUILD-PRESERVATION-AUTHORITY.json', ARTIFACT_AUTHORITY_SHA='RUNTIME_RELEASE_BOUND', TERMINAL_INSPECTION_SHA=sha(inspection), FULL_SOURCE_SHA256=full['source_sha256'], FULL_SOURCE_MAP_PATH=H / 'source-sha256.json', FULL_SOURCE_MAP_SHA=sha(H / 'source-sha256.json'), FAILED_GATE=ref(F / 'failed_operation_authority.py'), FAILED_AUTHORITY=F / 'FAILED-BUILD-PRESERVATION-AUTHORITY.json')
    observer = replace_assignments(observer, values)
    observer = once(observer, "retirement=dict(retirement,outer_join=retirement['postjoin'],common_record_sha256=retirement['common']['sha256'],shared_record_sha256=retirement['shared']['sha256'])", "retirement=dict(retirement,common_record_sha256=retirement['common']['sha256'],shared_record_sha256=retirement['shared']['sha256'])")
    # Runtime CLI still supplies the independent failure-authority hash. This
    # selected-map addition exposes actual12 while retaining source11 semantics.
    observer = once(observer, "selected_paths.update(Path(failed['source11'][key]['path']) for key in ('request','materialization','fullsource','additional_dispatcher','toolchain','provenance'))", "selected_paths.update(Path(failed['source11'][key]['path']) for key in ('request','materialization','fullsource','additional_dispatcher','toolchain','provenance'))\n        need(len(failed['actual_control_source12'])==12,'exact actual12 control closure')\n        selected_paths.update(Path(path) for path in failed['actual_control_source12'])")
    source('observe_failed_retirement.py', observer)
    for name in ('readback_observer.py', 'read_original_five_metadata.py', 'export_raw_five.py', 'postjoin_readback.py'):
        text = rebind((OLD / name).read_text())
        if name == 'readback_observer.py':
            values = dict(OUTPUT=F / ('root-observation-' + NONCE), NONCE=NONCE)
        elif name == 'read_original_five_metadata.py':
            values = dict(SUMMARY_SHA=sha(F / 'readback_observer.py'))
        elif name == 'export_raw_five.py':
            values = dict(SUMMARY_SHA=sha(F / 'readback_observer.py'), OUTPUT=F / ('root-observation-' + NONCE))
        else:
            values = dict(ENGINE=F / 'cleanup_failed.py', ENGINE_SHA=sha(F / 'cleanup_failed.py'), OBSERVER=F / 'observe_failed_retirement.py', OBSERVER_SHA=sha(F / 'observe_failed_retirement.py'))
        text = replace_assignments(text, values)
        source(name, text)
    helpers = ('failed_operation_authority.py', 'retain_failed_logs.py', 'cleanup_failed.py', 'observe_failed_retirement.py', 'readback_observer.py', 'read_original_five_metadata.py', 'export_raw_five.py', 'postjoin_readback.py')
    put('failure-helper-source-pins.json', {name: ref(F / name) for name in helpers})
    print('PREPARED_FAILURE_TERMINAL_HELPERS helpers=8 pairs=12 fdrows=24 root=0')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cleanup-source-only', action='store_true')
    main(parser.parse_args().cleanup_source_only)
