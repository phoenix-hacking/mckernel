"""Ordinary selected known-fact binding only; no copies/root/Docker/cleanup."""
from pathlib import Path
import ast,hashlib,json,importlib.util,shutil,uuid
P=Path(__file__).resolve().parent;I=P.parent/'rust-clear-debugreg-image-preparation-20261018-1';H=I/'heavy-proposal-1';T=P.parent/'rust-scheduler-debug-terminal-preparation-20261018-1'
def load(name):
 s=importlib.util.spec_from_file_location(name.replace('.','_'),P/name);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,v):(P/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def pin(name,values):
 f=P/name;s=f.read_text();lines=s.splitlines(keepends=True)
 for n in reversed(ast.parse(s).body):
  if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:lines[n.lineno-1:n.end_lineno]=[n.targets[0].id+' = '+repr(values[n.targets[0].id])+'\n']
 f.write_text(''.join(lines))
B=P/'before-actual-known-bindings-1';B.mkdir(mode=0o700)
for f in P.iterdir():
 if f.is_file() and f.suffix in ('.py','.json','.md'):shutil.copy2(f,B/f.name)
m=load('cleanup.py');q=m.parse(m.read_bounded(I/'image-request.json'));release=json.loads((H/'image-execution-release.json').read_bytes());G=Path(release['guard_capture']);common=json.loads(m.read_bounded(m.ATTEMPT));owner=json.loads(m.read_bounded(m.TERMINAL));guard=json.loads(m.read_bounded(G/'guard-result.json'));post=json.loads(m.read_bounded(H/'image-guard-postjoin-readback.json'));inspect=json.loads(m.read_bounded(G/'inspect-terminal-fresh.json'))
assert sha(I/'image-request.json')=='aecf1e46390f1d3784b768692751d524ba958acf7079a3b90f8a4d8597eea07e'
assert owner['status']=='PASS' and owner['retired'] is True and owner['exit_code']==0 and post['guard_direct_joined'] is True and post['root27_4_reacquired_after_join'] is True and post['guard_result_sha256']==sha(G/'guard-result.json') and post['owner_receipt_sha256']==sha(m.TERMINAL)
target=dict(container_id=owner['container_id'],container_name=owner['container_name'],owner_nonce=owner['owner_nonce'],owner_pid=common['pid'],owner_starttime=common['starttime'])
ancestry=m.namespace_ancestry();ns={k:ancestry[-1][k] for k in ('device','inode','mode','uid','gid')}
pin('cleanup.py',dict(NAMESPACE_ANCESTRY=ancestry,NAMESPACE_BINDING=ns,KNOWN_TARGET=target,REQUEST_SHA=sha(I/'image-request.json'),IMAGE_CANDIDATE=q['candidate_sha']))
f=P/'cleanup.py';s=f.read_text().replace('native-rust-clear-debugreg-image-guard-PENDING',G.name)
# Restore exact reviewed production predicate body and bind actual typed source facts.
old=(T/'cleanup.py').read_text();n=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='typed_source_binding');body=''.join(old.splitlines(keepends=True)[n.lineno-1:n.end_lineno]);body=body.replace('50f1646c962e2f6a53fb8888a0c18936e410a765844397cc6ef788b0e93d767d',q['source_derivative_sha256']).replace('342b5c248d515b1677d38e8ca5af9938ba0b298af11867653c481fbbfaf17abf',q['materialization_sha256']).replace('08bc683d79365632cbdbe5d65260567b04f07f27f5c4aea14086ff6b09b156c7',sha(I/'thin-inputs.json')).replace('d612a016006d913a11b4d7349b9e63c723aecee9083c0da944061b7351ced869',sha(I/'materialization-receipt.json')).replace('47853510',str(q['source_identity']['inode']))
n=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='typed_source_binding');lines=s.splitlines(keepends=True);lines[n.lineno-1:n.end_lineno]=[body];f.write_text(''.join(lines))
m=load('cleanup.py');m.CANDIDATE=m.image_request_binding(q)
source_map=json.loads((H/'source-sha256.json').read_bytes());full=source_map['source_sha256'];assert len(full)==11 and q['host_owner_path'] in full
for path,h in full.items():assert sha(Path(path))==h,path
selected={str(p):m.observe_identity(p) for p in (I/'thin-inputs.json',I/'materialization-receipt.json')};obs=dict(candidate_root=m.observe_identity(m.CANDIDATE));m.typed_source_binding(q,obs,selected)
ledger=[]
for p in sorted(G.glob('command-*/status.json')):
 row=json.loads(p.read_bytes());assert row['state']=='exited' and row['exit_code']==0 and not row.get('client_retirement_unproven');ledger.append(dict(pid=row['pid'],status_path=str(p),status_sha256=sha(p)))
assert len(ledger)==8 and len({r['pid'] for r in ledger})==8
physical=dict(status='PASS_ORDINARY_PHYSICAL_RECORD_JOIN_ONLY',cleanup_authorized=False,target=target,namespace_ancestry=ancestry,namespace_binding=ns,client_count=len(ledger),client_ledger=ledger,lease_absent=not m.LEASE.exists(),request=m.observe_identity(m.REQUEST),owner=m.observe_identity(m.TERMINAL),guard=m.observe_identity(G/'guard-result.json'),postjoin=m.observe_identity(H/'image-guard-postjoin-readback.json'),terminal_inspection=m.observe_identity(G/'inspect-terminal-fresh.json'),common=m.observe_identity(m.ATTEMPT),shared=m.observe_identity(m.SHARED),image=m.observe_identity(m.OUTPUT/'output/build/kernel/mckernel.img'),published_image=m.observe_identity(m.OUTPUT/'evidence/artifacts/mckernel.img'))
assert physical['lease_absent'];physical['image_sha256']=physical['image']['sha256'];assert physical['published_image']['sha256']==physical['image_sha256'];write('actual-physical-bindings.json',physical)
write('actual-selected-source-bindings.json',dict(status='PASS_REAL_TYPED_SOURCE_AND_FULL11_12PUBLICATION_BYTES_ONLY',source_map=dict(path=str(H/'source-sha256.json'),sha256=sha(H/'source-sha256.json')),full_source_sha256=full,request_sha256=m.REQUEST_SHA,candidate_base_git=q['candidate_sha'],source_publication_commit='cf035407404dc17a89c8347c4d5a01f48627d385',tools_publication_commit='8cdcbf461744417e457b003b4cf8be0e1861acd5',materialization_receipt=selected[str(I/'materialization-receipt.json')],source_root=obs['candidate_root'],root=False,docker=False,cleanup=False))
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();nonce=uuid.uuid4().hex
f=P/'observe_reset_image_retirement.py';s=f.read_text().replace('native-rust-clear-debugreg-image-guard-PENDING',G.name).replace('clear-debugreg-observation-PENDING',nonce);f.write_text(s)
pin('observe_reset_image_retirement.py',dict(SOURCE_SHA=sha(P/'cleanup.py'),RETIREMENT_SHA=sha(P/'actual-physical-bindings.json'),BOOT=boot,PIDS=tuple(r['pid'] for r in ledger),PENDING_BINDINGS=('actual artifact review and object retained-copy descriptor authority','finite15 retention approval/execution and exact retained authority','source publication and exact independent observation release')))
for name in ('readback_observer.py','export_raw_five.py'):
 f=P/name;f.write_text(f.read_text().replace('clear-debugreg-observation-PENDING',nonce))
pin('export_raw_five.py',dict(SUMMARY_SHA=sha(P/'readback_observer.py')));pin('postjoin_readback.py',dict(ENGINE_SHA=sha(P/'cleanup.py'),OBSERVER_SHA=sha(P/'observe_reset_image_retirement.py')));pin('retention_observer.py',dict(BOOT=boot))
write('actual-known-binding-result.json',dict(status='PASS_ACTUAL_KNOWN_SOURCE_REQUEST_GUARD_CLIENT_BINDINGS_ONLY',full_source_count=11,publication_rows=12,client_count=8,candidate_base_git=q['candidate_sha'],typed_source_consumer=True,namespace_inode=ns['inode'],source_inode=q['source_identity']['inode'],root=False,docker=False,copy=False,cleanup=False,remaining=('four retained copy descriptors/artifact review','finite15 release and retained authority','publication/execution releases')))
print(json.dumps(dict(status='PASS_KNOWN_BINDINGS',source_rows=11,clients=8,source_inode=q['source_identity']['inode'],cleanup_sha256=sha(P/'cleanup.py'))))
