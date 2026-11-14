from pathlib import Path
import json,hashlib,importlib.util,ast,shutil
P=Path(__file__).resolve().parent;I=P.parent/'rust-clear-debugreg-image-preparation-20261018-1';D=I/'heavy-proposal-1/postbuild-readonly-1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def module(n):
 s=importlib.util.spec_from_file_location(n.replace('.','_'),P/n);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def write(n,v):(P/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def pin(name,values):
 f=P/name;s=f.read_text();lines=s.splitlines(keepends=True)
 for n in reversed(ast.parse(s).body):
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+repr(values[n.targets[0].id])+'\n']
 f.write_text(''.join(lines))
B=P/'before-four-copy-bindings-1';B.mkdir(mode=0o700)
for f in P.iterdir():
 if f.is_file() and f.suffix in ('.py','.json','.md'):shutil.copy2(f,B/f.name)
r=module('retention_observer.py');j=module('retained_join.py');engine=r.load(r.ENGINE);copy=json.loads((D/'retained-artifacts/retention-result.json').read_bytes());observation=json.loads((D/'root-observation-result.json').read_bytes());assert observation['status']=='PASS_EXACT_POSTBUILD_14_AND_FOUR_COPIES' and observation['all_returncode_zero'] is True and observation['direct_waits']==15
actual=json.loads((P/'retention-fifteen-actual-inputs.json').read_bytes());draft=json.loads((P/'retention-execution-release-DRAFT.json').read_bytes());names={'syscall.c.o':'syscall','process.c.o':'process','mckernel_rust.o':'rust','mckernel.img':'image'};pairs=[]
for row in draft['artifacts']:
 if row['action']!='reuse':continue
 key=names[row['kind']];observed=copy['artifacts'][key];assert row['original']['path']==observed['source']['path'] and row['retained']==observed['retained_path']
 fresh=engine.observe_identity(Path(row['retained']));assert (fresh['device'],fresh['inode'],fresh['size'],fresh['sha256'])==(observed['retained_dev'],observed['retained_inode'],observed['bytes'],observed['sha256'])
 row['retained_authority']=j.join_one(engine,fresh);pairs.append(dict(original=row['original'],retained=row['retained_authority'],outside_generic_receipt_inventory=True))
assert len(pairs)==4;j.join_pairs(engine,pairs);r.validate_artifact_rows(draft['artifacts'])
write('actual-four-retained-pairs.json',pairs)
process=next(p for p in pairs if p['original']['path'].endswith('/process.c.o'));write('actual-process-object-authority.json',dict(schema='mckernel.clear-debugreg.process-object-authority.v1',source=process['original'],retained_destination=process['retained'],outside_generic_receipt_inventory=True,acceptance=False))
actual.update(status='PASS_ORIGINALS15_AND_FOUR_EXISTING_REUSE_DESCRIPTORS_PENDING_RETENTION_RELEASE',artifacts=draft['artifacts'],pending_reused_authority=[],actual_four_copy_result=ref(D/'retained-artifacts/retention-result.json'),actual_postbuild_result=ref(D/'root-observation-result.json'));write('retention-fifteen-actual-inputs.json',actual);write('retention-execution-release-DRAFT.json',draft)
pin('observe_reset_image_retirement.py',dict(OBJECT_AUTHORITY_SHA=sha(P/'actual-process-object-authority.json'),PENDING_BINDINGS=('artifact review authority report','finite15 retention approval/execution and exact retained authority','source publication and exact independent observation release')));pin('postjoin_readback.py',dict(OBSERVER_SHA=sha(P/'observe_reset_image_retirement.py')))
# Only changed actual consumer checks; no unrelated16-check or canonical39 rerun.
refusals=0
for pair in pairs:
 bad=json.loads(json.dumps(pair));bad['retained']['sha256']='0'*64
 try:j.join_pairs(engine,[bad])
 except RuntimeError:refusals+=1
 else:raise AssertionError('bad retained descriptor accepted')
try:r.validate(draft)
except RuntimeError as e:assert str(e)=='finite retention not released';refusals+=1
else:raise AssertionError('draft authorized')
write('actual-four-copy-consumer-result.json',dict(status='PASS_ACTUAL_FOUR_REUSE_AND_FINITE15_CONSUMERS_ONLY',pairs=4,originals=15,reuse=4,new_copies=11,new_copy_bytes=actual['new_copy_bytes'],targeted_refusals=refusals,frozen_engine_sha256=sha(r.ENGINE),root=False,copy_executed=False,cleanup=False,artifact_review='PENDING_REAL_INDEPENDENT_REPORT'))
print(json.dumps(dict(status='PASS_FOUR_ACTUAL_REUSE_DESCRIPTORS',pairs=4,originals=15,new_copy_bytes=actual['new_copy_bytes'],targeted_refusals=refusals)))
