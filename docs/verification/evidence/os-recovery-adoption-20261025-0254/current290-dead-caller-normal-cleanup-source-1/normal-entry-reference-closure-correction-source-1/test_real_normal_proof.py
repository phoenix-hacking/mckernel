"""Functional retained normal-owner/source proof regression; no security testing.
No root/process/Docker/guest/build queries. Use actual immutable source/evidence.
"""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=next(ROOT.glob('produce*.py'))
spec=importlib.util.spec_from_file_location('closure_producer',SOURCE);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
p,e=a.bootstrap();protocol=e.current230_contract();c=protocol.contract()
request=protocol.parse(a.pinned(c['static']['request']))
receipt=protocol.parse(a.pinned(p['owner_receipt']))
join=protocol.parse(a.pinned(p['join']))
item=receipt['terminal_container_info']
target=p['target']
paths={str(e.REQUEST),str(e.TERMINAL),p['join']['path'],str(e.EVIDENCE/'attempt/container.log'),str(e.OUTPUT/'evidence/receipt.json')}
paths.update(row['path'] for row in protocol.required_static_references())
paths.update(protocol.required_runtime_references(request,receipt))
paths.update(str(Path(c['caller_capture_root'])/name) for name in ('owner.PROCESS.json','ACTUAL-OWNER-ENTRY.json','ROOT-NORMAL-CLEANUP-COMPLETION-READY.json','owner.stdout','owner.stderr'))
paths.update(row['path'] for row in p['dead_caller_new_ofd']['references'].values())
paths.update(request[k] for k in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest','gitlink_manifest'))
selected={path:e.observe_identity(Path(path)) for path in sorted(paths)}
obs=dict(boot_id=p['dead_caller_new_ofd']['boot_id'],retained_exclusions=[e.observe_identity(path) for path in (e.ATTEMPT,e.SHARED)],normal_owner_join=selected[p['join']['path']],ownership_case='FAIL_COMMON_AND_SHARED',shared_record_already_absent=False,
         candidate_root=e.observe_identity(Path(request['source_root'])),namespace_binding=e.NAMESPACE_BINDING)
try:
 protocol.normal_owner_join_binding(receipt,join,target,item,p['owner_receipt']['sha256'],request,obs,selected)
except RuntimeError as exc:
 assert 'complete selected identity row:' in str(exc) and '/ROOT-EXECUTION-GRANT.json' in str(exc),str(exc)
 (ROOT/'original-missing-grant-reproduction.txt').write_text(str(exc)+'\n')
else:raise AssertionError('original missing grant failure not reproduced')
refs=a.normal_entry_references(p)
assert len(refs)==4
for row in refs:
 selected[row['path']]=e.observe_identity(Path(row['path']))
 raw=protocol.selected_bytes(row['path'],selected,row)
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
assert protocol.normal_owner_join_binding(receipt,join,target,item,p['owner_receipt']['sha256'],request,obs,selected) is True
assert protocol.typed_source_binding(request,obs,selected) is True
print(json.dumps(dict(status='PASS_ACTUAL_RETAINED_NORMAL_OWNER_JOIN_AND_TYPED_SOURCE_PROOFS',selected_paths=len(selected),normal_entry_references=refs,original_missing_grant_reproduced=True,scope='source/evidence proof regression only; no root/native/cleanup acceptance'),indent=2))
