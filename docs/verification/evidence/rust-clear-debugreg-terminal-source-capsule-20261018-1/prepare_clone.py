from pathlib import Path
import ast,hashlib,json,os
P=Path(__file__).resolve().parent
T=P.parent/'rust-scheduler-debug-terminal-preparation-20261018-1'
case=P.parent/'rust-clear-debugreg-image-preparation-20261018-1'
oldcase=T.parent/'rust-scheduler-debug-materialization-final-20261018-1'
files=['cleanup.py','observe_reset_image_retirement.py','readback_observer.py','export_raw_five.py','consume_raw_five.py','postjoin_readback.py','retention_observer.py','retained_join.py','ordinary_readback.py','publication-cleanup-tests.py','test_readback.py','test_raw_five.py','test_ordinary_readback.py']
nonce='clear-debugreg-observation-PENDING'
guard='native-rust-clear-debugreg-image-guard-PENDING'
oldguard='native-rust-scheduler-debug-image-guard-20261018-1fdbb32eb93f4568999f6a1c8d2b06fb'
def rewrite_assign(text,values):
 lines=text.splitlines(keepends=True);tree=ast.parse(text)
 for n in reversed(tree.body):
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
   lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+repr(values[n.targets[0].id])+'\n']
 return ''.join(lines)
for name in files:
 text=(T/name).read_text().replace(str(T),str(P)).replace(str(oldcase),str(case)).replace(oldguard,guard).replace('9afeb6a7a451424cb8b606a92d5cd385',nonce)
 if name=='cleanup.py':
  text=text.replace("'author': None","'author': 'clear_debugreg_terminal_prepare_1726'")
  text=rewrite_assign(text,dict(PREFIX=P.name,NAMESPACE_ANCESTRY=None,NAMESPACE_BINDING=None,KNOWN_TARGET=None,REQUEST_SHA=None,IMAGE_CANDIDATE=None))
  # Typed materialization pins are future facts; no prior source identity is reusable.
  tree=ast.parse(text);n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='typed_source_binding');lines=text.splitlines(keepends=True)
  lines[n.lineno-1:n.end_lineno]=["def typed_source_binding(request, obs, selected_map):\n    raise Refusal('PENDING_EXACT_CLEAR_DEBUGREG_MATERIALIZATION_BINDING')\n"]
  text=''.join(lines)
 if name=='observe_reset_image_retirement.py':
  text=text.replace('rust-scheduler-debug-image-actual-review','rust-clear-debugreg-image-actual-review').replace('mckernel.independent-rust-scheduler-debug-image-actual-review.v1','mckernel.independent-rust-clear-debugreg-image-actual-review.v1')
  text=rewrite_assign(text,dict(RETIREMENT_SHA=None,OBJECT_AUTHORITY_SHA=None,NEW_OBJECT_AUTHORITY_SHA=None,ARTIFACT_AUTHORITY_SHA=None,TERMINAL_INSPECTION_SHA=None,ARTIFACT_EXPECTED_GUARD=None,ARTIFACT_EXPECTED_PINS=None,PIDS=(),PENDING_BINDINGS=('request/source materialization and full11 source closure','CID/owner/client/build and guard identities','artifact and fd identities','retention15 authority','publication/reviews'),BOOT=None))
 if name=='retention_observer.py':text=rewrite_assign(text,dict(BOOT=None))
 (P/name).write_text(text);(P/name).chmod(0o600)
# Retention uses an immutable exact accepted engine, independent of future publication.
raw=Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='f7a35968f510c60791ac6604cdaaa6a2abbd1a991d04f6afb4ad61c84cb76ef8'
(P/'retention-engine-frozen.py').write_bytes(raw);(P/'retention-engine-frozen.py').chmod(0o400)
# Consumers pin current private helper bytes; these are preparation source facts.
sha=lambda n:hashlib.sha256((P/n).read_bytes()).hexdigest()
p=P/'observe_reset_image_retirement.py';p.write_text(rewrite_assign(p.read_text(),dict(SOURCE_SHA=sha('cleanup.py'),TEST_SHA=sha('publication-cleanup-tests.py'))))
p=P/'export_raw_five.py';p.write_text(rewrite_assign(p.read_text(),dict(SUMMARY_SHA=sha('readback_observer.py'))))
p=P/'postjoin_readback.py';s=p.read_text().replace("ENGINE=Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py')","ENGINE=Path("+repr(str(P/'cleanup.py'))+")");p.write_text(rewrite_assign(s,dict(ENGINE_SHA=sha('cleanup.py'),OBSERVER_SHA=sha('observe_reset_image_retirement.py'))))
source_map={n:dict(path=str(P/n),sha256=sha(n),bytes=(P/n).stat().st_size) for n in files+['retention-engine-frozen.py']}
(P/'source-map.json').write_text(json.dumps(source_map,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(status='CLONED_PENDING_REAL_BINDINGS',files=len(source_map),cleanup_sha256=sha('cleanup.py'),retention_engine_sha256=sha('retention-engine-frozen.py'))))
