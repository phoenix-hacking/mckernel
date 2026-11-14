"""Finite NEW205 failed-producer source/data specialization; no retention or root effect.

Run once to freeze the twelve original log authorities and retention helper.
The terminal generators are finalized only after genuine retained-pair output exists.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import stat

F = Path(__file__).resolve().parent
A = F.parent
H = A / 'heavy-proposal-1'
OLD_N = Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1')
OLD = OLD_N / 'terminal-preparation-1/failure-preparation-1'
GUARD = Path('/home/holden/mckernel-work/scratch/native-rust-four-callback-affinity-image-guard-bc32500028be40a09ce651f20ade82d4')
REVIEW = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-heavy-review-20261019-1/NEW205-ACTUAL-FAILED-BUILD-AND-CLIENT-RETIREMENT-REVIEW.json')
REVIEW_SHA = 'a55469e628dbec12ffefcec85f18770d89aa1a8383d3fb7d7104fbc4a9e1a8dc'
OWNER_SHA = '23de50fbe9d21cbbb16edfe0cafc270f635b6aa4298a8901f720d511ce235771'
CID = '6f490dad40bf7de8e293762c9933bc444db19ecf01c1c57be6bd390d2da7dc5c'
REQUEST_SHA = '902f482227f3510c86a2624fa9f255abb3d0c82996191f4e3ca4c227877765f8'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def ref(p):
    p = Path(p)
    return dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)

def identity(p, cap=16 << 20):
    p = Path(p)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        assert stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_uid == 1000 and a.st_size < cap
        with os.fdopen(os.dup(fd), 'rb') as stream:
            data = stream.read(a.st_size + 1)
        b, c = os.fstat(fd), p.lstat()
        attrs = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_nlink', 'st_mtime_ns', 'st_ctime_ns')
        assert len(data) == a.st_size and all(getattr(a, k) == getattr(b, k) == getattr(c, k) for k in attrs)
        return dict(path=str(p), device=a.st_dev, inode=a.st_ino, mode=oct(stat.S_IMODE(a.st_mode)), uid=a.st_uid, gid=a.st_gid, nlink=a.st_nlink, size=a.st_size, mtime_ns=a.st_mtime_ns, ctime_ns=a.st_ctime_ns, sha256=hashlib.sha256(data).hexdigest())
    finally:
        os.close(fd)

def put(name, data):
    with (F / name).open('x') as stream:
        json.dump(data, stream, sort_keys=True, indent=2)
        stream.write('\n')

def source(name, text):
    ast.parse(text)
    with (F / name).open('x') as stream:
        stream.write(text)

def once(text, before, after):
    assert text.count(before) == 1, (before, text.count(before))
    return text.replace(before, after, 1)

def rebind(text):
    return text.replace(str(OLD), str(F)).replace(str(OLD_N), str(A))

def replace_assignments(text, values):
    rows = text.splitlines(keepends=True)
    edits = []
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in values:
            key = node.targets[0].id
            value = values[key]
            literal = 'Path(' + repr(str(value)) + ')' if isinstance(value, Path) else repr(value)
            edits.append((node.lineno - 1, node.end_lineno, key + ' = ' + literal + '\n'))
    assert len(edits) == len(values), (len(edits), len(values))
    for start, end, value in sorted(edits, reverse=True):
        rows[start:end] = [value]
    return ''.join(rows)

def main():
    request = json.loads((A / 'image-request.json').read_bytes())
    owner = json.loads((A / 'owner-evidence/owner-receipt.json').read_bytes())
    assert sha(A / 'image-request.json') == REQUEST_SHA and sha(A / 'owner-evidence/owner-receipt.json') == OWNER_SHA
    assert sha(REVIEW) == REVIEW_SHA and owner['status'] == 'FAIL' and owner['exit_code'] == 1 and owner['retired'] is True and owner['container_id'] == CID
    paths = {'owner-receipt.json': A / 'owner-evidence/owner-receipt.json', 'owner-container.log': A / 'owner-evidence/attempt/container.log'}
    for name in ('tool-versions.txt', 'build.stderr.log', 'build.stdout.log', 'receipt.json', 'release-tid-production-checks.json', 'release-fp-regs-production-checks.json', 'clone-affinity-production-checks.json', 'production-abi-checks.json', 'modules-end-probe.json', 'progress.json'):
        paths['driver-' + name] = A / 'owner-work/evidence' / name
    rows = [dict(kind=kind, action='copy', original=identity(path), retained=str(F / 'retained-production-objects' / kind)) for kind, path in paths.items()]
    assert len(rows) == 12 and sum(row['original']['size'] for row in rows) <= 8 << 20
    put('failed-log-original-authorities.json', rows)
    inputs = {key: dict(path=request[key], sha256=request[hashkey]) for key, hashkey in [('driver_path', 'driver_sha256'), ('provenance_path', 'provenance_sha256'), ('host_owner_path', 'host_owner_sha256'), ('source_manifest', 'source_manifest_sha256'), ('toolchain_manifest', 'toolchain_manifest_sha256')]}
    put('failed-operation-source-references.json', dict(request=ref(A / 'image-request.json'), original_sources=inputs, materialization_receipt=ref(A / 'materialization-receipt.json'), source11=ref(H / 'source-sha256.json'), provenance=identity(A / 'owner-work/evidence/provenance.json'), source_inputs_copied=False))
    gate = rebind((OLD / 'failed_operation_authority.py').read_text())
    gate = once(gate, 'N=Path(__file__).resolve().parents[2]', 'N=Path(__file__).resolve().parent.parent')
    gate = replace_assignments(gate, dict(OWNER_SHA=OWNER_SHA, REVIEW_SHA=REVIEW_SHA, CID=CID))
    gate = once(gate, "MUTEX_SHA='58cd06564cf0936a2f345de30e48b7ad964a416baf3b85cd4f3ce3478d825f2c'\n", '')
    gate = once(gate, " and authority['mutex_postjoin']['sha256']==MUTEX_SHA", '')
    gate = once(gate, ";post=verify(authority['mutex_postjoin'],True)", '')
    old_start = gate.index(" need(review['decision']=='PASS_POSITIVE_CLIENT_OWNER_GUARD_RETIREMENT_WITH_FAILED_PRODUCER'")
    old_end = gate.index(" source=authority['source11'];", old_start)
    gate = gate[:old_start] + " validate_retirement_evidence(authority['current_retirement_review'])\n" + gate[old_end:]
    gate = once(gate, "=='e9497da4204aed95708bb0f2ceb062a88c45517c13e3c69e65510fb59334cec0'", '==' + repr(REQUEST_SHA))
    gate = once(gate, 'len(rows)==len(pairs)==11', 'len(rows)==len(pairs)==12')
    gate = once(gate, 'exact eleven copy-only failed logs', 'exact twelve copy-only failed logs')
    gate = once(gate, " need(source['additional_dispatcher']==source_wrapper['additional_dispatcher'],'actual additional dispatcher')", " need(source['additional_dispatcher']==source_wrapper['additional_dispatcher'],'actual additional dispatcher')\n verify(source['additional_dispatcher'])\n actual=dict(source_map);additional=source['additional_dispatcher'];need(additional['path'] not in actual,'additional dispatcher distinct');actual[additional['path']]=additional['sha256']\n need(len(actual)==12 and authority['actual_control_source12']==actual,'exact source11 plus actual additional dispatcher')")
    binding_source = (F / 'retirement_binding.py.in').read_text()
    gate += '\n' + binding_source
    source('failed_operation_authority.py', gate)
    retention = rebind((OLD / 'retain_failed_logs.py').read_text())
    retention = replace_assignments(retention, dict(ARTIFACT_PATHS={r['kind']: dict(action='copy', original=r['original']['path'], retained=r['retained']) for r in rows}))
    start = retention.index("    for ref in release['physical_join'].values():checked_json(ref)")
    end = retention.index("    state=json.loads(", start)
    check = "    need(release['physical_join']==PHYSICAL_JOIN,'exact actual failed joins')\n    need(sha(FAILED_GATE)==FAILED_GATE_SHA,'exact failure gate source')\n    gate=load(FAILED_GATE);gate.validate_retirement_evidence(RETIREMENT_REVIEW)\n"
    retention = retention[:start] + check + retention[end:]
    declarations = '\nFAILED_GATE = Path(' + repr(str(F / 'failed_operation_authority.py')) + ')\nFAILED_GATE_SHA = ' + repr(sha(F / 'failed_operation_authority.py')) + '\nRETIREMENT_REVIEW = ' + repr(ref(REVIEW)) + '\nPHYSICAL_JOIN = ' + repr(dict(owner=ref(A / 'owner-evidence/owner-receipt.json'), guard=ref(GUARD / 'guard-result.json'), retirement=ref(REVIEW), guard_status=ref(H / 'image-guard.status.json'), outer_status=ref(H / 'root-image-execution-1/status.json'))) + '\n'
    retention = once(retention, 'DEST=P/\'retained-production-objects\'\n', "DEST=P/'retained-production-objects'\n" + declarations)
    source('retain_failed_logs.py', retention)
    put('FAILED-CASE-INPUTS.json', dict(schema='mckernel.new205.failure-terminal-preparation.v1', author='/root/clone_thread_affinity_rust_repair', status='SOURCE_PREPARATION_ONLY_NOT_RELEASED', request=ref(A / 'image-request.json'), owner=ref(A / 'owner-evidence/owner-receipt.json'), guard=ref(GUARD / 'guard-result.json'), retirement=ref(REVIEW), guard_capture=str(GUARD), source11=ref(H / 'source-sha256.json'), actual_control_count=12, retained_log_count=12, fd_metadata_rows=24, successful_build=False, preserved_directories=[str(A / 'owner-work/output/build'), str(A / 'owner-work/evidence')], retention_source=ref(F / 'retain_failed_logs.py'), failure_gate_source=ref(F / 'failed_operation_authority.py'), postjoin_mutex_record=ref(H / 'failure-mutex-postjoin-readback-1.json'), original_dispatcher_success_postjoin_absence_preserved=True, cleanup_authority=False, physical_release=False))
    print('PREPARED_FAILURE_RETENTION_SOURCES pairs=12 fdrows=24 root=0 copies=0')

if __name__ == '__main__':
    main()
