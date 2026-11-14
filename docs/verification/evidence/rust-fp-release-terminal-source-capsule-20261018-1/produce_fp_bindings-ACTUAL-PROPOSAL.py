"""Exact input-join adapter; semantic postbuild observations remain independent-review inputs.

No compiler/binutils/root/guest execution and no source/helper population. A successful
receipt is a binding result only, never new artifact or native acceptance.
"""
from pathlib import Path
import argparse,hashlib,json,os,types
P=Path(__file__).resolve().parent
FP=P/'fp_authority-ACTUAL-PROPOSAL.py'
FP_SHA='fec6188e26337b77ef4bcb5e1a9c239c005d0081b544a4793415aea38890fc0c'
ENGINE=P/'retention-engine-frozen.py'
ENGINE_SHA='c6fdfc96dfcfd4c78888335625f68092cf39b1b6c3158dc367f8a1321cebd90b'
def need(ok,why):
 if not ok:raise RuntimeError(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path,expected):
 raw=path.read_bytes();need(sha(raw)==expected,'source helper hash differs')
 m=types.ModuleType(path.stem);m.__file__=str(path);exec(compile(raw,str(path),'exec'),m.__dict__);return m
f=load(FP,FP_SHA);engine=load(ENGINE,ENGINE_SHA)
def checked(ref,maximum=128<<20):
 need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'exact path/hash reference required')
 p=Path(ref['path']);before=engine.observe_identity(p);need(before['size']<=maximum and before['sha256']==ref['sha256'],'actual input hash/cap differs')
 raw=engine.read_bounded(p,maximum=maximum);need(sha(raw)==ref['sha256'] and engine.observe_identity(p)==before,'actual input changed during read');return raw
def doc(ref):return json.loads(checked(ref))
def pending(missing):return dict(status='PENDING_ACTUAL_FP_BINDING_INPUTS',missing=missing,typed_source=None,postbuild=None,artifact_acceptance=False,native_acceptance=False)
def produce(inputs):
 names=('request','manifest','materialization_receipt','retained_authority','source11','artifact_decision')
 missing=[k for k in names if not isinstance(inputs.get(k),dict)]
 if missing:return pending(missing)
 q=doc(inputs['request']);manifest=doc(inputs['manifest']);receipt=doc(inputs['materialization_receipt']);pairs=doc(inputs['retained_authority']);source11=doc(inputs['source11']);report=doc(inputs['artifact_decision'])
 # Exact actual report, not prebuild statusPASS or a renamed previous report.
 if report.get('schema')!='mckernel.independent-rust-fp-release-image-actual-review.v1' or not isinstance(report.get('fp_release_postbuild'),dict) or not isinstance(report.get('fp_release_typed_source'),dict):return pending(['independent finished FP artifact report with typed-source and postbuild groups'])
 need(report.get('decision')=='PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT' and report.get('implementation_ownership') is False and bool(report.get('reviewer')),'actual independent artifact decision required')
 byrole=f.authority_pairs(pairs,f.ARTIFACT_ROLES)
 # Keep complete29 role/file joins, no renamed or truncated subset authority.
 for pair in pairs:
  for key in ('original','retained'):
   bound=pair[key];fresh=engine.observe_identity(Path(bound['path']));need(all(fresh[k]==bound[k] for k in fresh),'actual retained role descriptor/hash differs')
 full=source11.get('source_sha256');need(isinstance(full,dict) and len(full)==11 and q.get('host_owner_path') in full and full[q['host_owner_path']]==q['host_owner_sha256'],'actual source11 host-owner closure required')
 for path,h in full.items():checked(dict(path=path,sha256=h))
 need(inputs['manifest']['path']==q['source_manifest'] and inputs['manifest']['sha256']==q['source_manifest_sha256'],'actual source manifest request path/hash differs')
 need(receipt.get('status')=='PASS_SOURCE_MATERIALIZATION_ONLY' and receipt.get('source')==q['source_root'] and receipt.get('source_derivative_sha256')==q['source_derivative_sha256'] and receipt.get('materialization_sha256')==q['materialization_sha256'],'actual materialization receipt differs')
 source=Path(q['source_root']);meta=source.lstat();identity=q['source_identity'];need((meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,meta.st_mode&0o7777)==(identity['dev'],identity['inode'],identity['uid'],identity['gid'],identity['mode']),'actual source five-tuple differs')
 cpu=source/'arch/x86_64/kernel/cpu.c';make=byrole['build.make']['original'];build=Path(make['path']).parents[3]
 typed=dict(request_path=inputs['request']['path'],request_sha256=inputs['request']['sha256'],source_derivative_sha256=q['source_derivative_sha256'],materialization_sha256=q['materialization_sha256'],source_inode=identity['inode'],manifest_path=inputs['manifest']['path'],manifest_sha256=inputs['manifest']['sha256'],receipt_path=inputs['materialization_receipt']['path'],receipt_sha256=inputs['materialization_receipt']['sha256'],cpu_source_sha256=engine.observe_identity(cpu)['sha256'],generated_rust_make_sha256=make['sha256'],build_root=str(build),container_build_root=str(Path(q['mounts']['work'])/build.relative_to(q['work_root'])))
 selected={inputs[k]['path']:dict(sha256=inputs[k]['sha256']) for k in ('manifest','materialization_receipt')};f.typed_source(q,dict(candidate_root=dict(inode=meta.st_ino)),selected,typed,lambda p:engine.read_bounded(Path(p),maximum=128<<20))
 need(all(report['fp_release_typed_source'].get(k)==v for k,v in typed.items() if k not in ('request_path','request_sha256')),'independent typed-source report join differs')
 bindings=report.get('source_request_bindings',{})
 need(all(bindings.get(k)==inputs[k] for k in ('request','manifest','materialization_receipt')),'independent source/request reference differs')
 evidence=report.get('fp_release_evidence')
 if not isinstance(evidence,list) or not {'default_consumer','release_body','descriptor'}<=set(row.get('group') for row in evidence if isinstance(row,dict)):return pending(['complete semantic capture/status evidence groups'])
 for row in evidence:
  status=doc(row['status']);out=checked(row['stdout'],64<<20);err=checked(row['stderr'],64<<20)
  need(status.get('returncode')==0 and status.get('direct_child_joined') is True and status.get('argv')==row['argv'],'actual evidence positive direct command join differs')
  need(status.get('stdout_bytes')==len(out) and status.get('stdout_sha256')==sha(out) and status.get('stderr_bytes')==len(err)==0 and status.get('stderr_sha256')==sha(err),'actual evidence original stream joins differ')
 def read_role(role):
  b=byrole[role]['original'];return checked(dict(path=b['path'],sha256=b['sha256']),64<<20)
 proof=json.loads(read_role('release-fp-regs-production-checks.json'));f.production(proof,byrole,read_role,typed,f.EXPECTED_ABI_HEADER_SHA256)
 postbuild=report['fp_release_postbuild'];f.postbuild(postbuild,postbuild,byrole)
 guard=report.get('guard_retirement',{});need(guard.get('retired') is True and guard.get('physical_client_terminal_count')==8 and isinstance(guard.get('container_id'),str) and len(guard['container_id'])==64,'actual positive guard/eight-client evidence required')
 for key,role in [('cpu','cpu.c.o'),('process','process.c.o'),('rust','mckernel_rust.o'),('image','mckernel.img')]:
  actual=report.get('actual_artifacts',{}).get(key,{});b=byrole[role]['original'];need(all(actual.get(k)==v for k,v in dict(path=b['path'],sha256=b['sha256'],bytes=b['size'],dev=b['device'],inode=b['inode'],uid=b['uid'],mode=int(b['mode'],8)).items()),'independent actual artifact role differs')
 return dict(status='PASS_EXACT_FP_BINDING_ADAPTER_ONLY',typed_source=typed,postbuild=postbuild,inputs=inputs,independent_artifact_decision=dict(reviewer=report['reviewer'],decision=report['decision'],reference=inputs['artifact_decision']),retained_pairs=29,artifact_acceptance=False,native_acceptance=False,source_helpers_populated=False)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',required=True);parser.add_argument('--inputs-sha256',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
 need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 adapter required');result=produce(doc(dict(path=args.inputs,sha256=args.inputs_sha256)));raw=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(raw)<=1<<20,'finite binding receipt cap')
 fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 print(json.dumps(dict(status=result['status'],output=args.output,sha256=sha(raw),artifact_acceptance=False)))
if __name__=='__main__':main()
