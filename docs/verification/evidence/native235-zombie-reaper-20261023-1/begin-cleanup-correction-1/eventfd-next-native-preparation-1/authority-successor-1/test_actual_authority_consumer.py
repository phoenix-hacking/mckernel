"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Controlled TESTONLY future-authority graph, actual composite/read/artifact functions.
No real module/launcher hashes or native/SDK6 acceptance are fabricated.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys
D=Path(__file__).resolve().parent
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load(D/'composite_module_binding.py','actual_sdk6_composite');a=m.authority();selected=a.links();assert selected['proofs']['SDK6_acceptance'] is None
rows=[]
def refused(name,call):
 try:call()
 except (ValueError,KeyError,TypeError,FileNotFoundError) as exc:rows.append(dict(name=name,result='REFUSED',reason=str(exc)))
 else:raise AssertionError('accepted '+name)
refused('real_pending_SDK6_acceptance_NULL',lambda:m.validate_module_binding({}))
T=D/'TESTONLY-authority-graphs';T.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
SOURCE='2093e464dd2dfb976016a71197a120929e16bfd830f4d643126b96ea1ea0a2e8';nonce='TESTONLY_NO_NATIVE_NONCE'
def graph(name,mutate=None):
 p=T/name;p.mkdir()
 def put(n,v):
  raw=(json.dumps(v,sort_keys=True)+'\n').encode();f=p/n
  with f.open('xb') as out:out.write(raw)
  return dict(path=str(f),sha256=sha(raw),bytes=len(raw))
 def artifact(n):
  f=p/n;raw=('TESTONLY controlled artifact '+n).encode()
  with f.open('xb') as out:out.write(raw)
  f.chmod(0o600);st=f.stat();return dict(path=str(f),sha256=sha(raw),size=len(raw),mode=st.st_mode)
 modules=[artifact(n) for n in m.NAMES];launcher=artifact('mcexec');accepted={n:dict(path=r['path'],sha256=r['sha256'],bytes=r['size']) for n,r in zip(m.NAMES,modules)}
 driver=dict(status='BUILD_ARTIFACT_CHECKS_PASS',make_returncode=0,source_candidate_sha=SOURCE,artifacts={Path(n).stem:dict(sha256=r['sha256'],bytes=r['size'],modinfo=dict(vermagic='6.12.0-211.44.1.el10_2.mckernel1.x86_64 SMP preempt mod_unload ')) for n,r in zip(m.NAMES,modules)})
 owner=dict(status='PASS',build_status='PASS',cleanup_status='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE',retired=True,wait_exit_code=0,owner_nonce=nonce,driver_receipt=driver)
 actual=dict(source_identity=SOURCE,nonce=nonce,artifacts=copy.deepcopy(accepted))
 sdk=dict(status='PASS',decision='PASS_ACTUAL_SDK6_ARTIFACT_AND_PHYSICAL_ACCEPTANCE',physical_acceptance=True,native_acceptance=False,source_identity=SOURCE,observed=dict(required_exports_vermagic_MM_unique_linkage=True),nonce=nonce,artifacts=accepted)
 build=dict(decision='PASS_ACTUAL_M06_LAUNCHER_PRODUCTION_ARTIFACT_ONLY',native_acceptance=False,launcher_source_sha256='TESTONLY_LAUNCHER_SOURCE',elf=dict(path=launcher['path'],sha256=launcher['sha256'],bytes=launcher['size']))
 lreceipt=dict(status='PASS',launcher_source_sha256='TESTONLY_LAUNCHER_SOURCE');links=copy.deepcopy(selected);base=dict(modules=modules,artifacts=dict(mcexec=launcher))
 values=dict(sdk=sdk,actual=actual,owner=owner,driver=driver,build=build,lreceipt=lreceipt,links=links,base=base)
 if mutate:mutate(values)
 sdk['actual_reads']=put('actual.json',actual);sdk['owner_receipt']=put('owner.json',owner);links['proofs']['SDK6_acceptance']=put('sdk.json',sdk);build['receipt']=put('launcher-receipt.json',lreceipt);links['proofs']['launcher_build_acceptance']=put('launcher-build.json',build)
 return links,base,p
# Only links() is a controlled authority boundary; read() and artifact() consume
# exclusive real files with exact hashes/modes. All actual consumer joins run.
def invoke(name,mutate=None,negative=False,after=None):
 links,base,p=graph(name,mutate);a.links=lambda:links;m.authority=lambda:a
 if after:after(links,base,p)
 if negative:refused(name,lambda:m.validate_module_binding(base))
 else:m.validate_module_binding(base);rows.append(dict(name=name,result='PASS_CONTROLLED_FULL_CONSUMED_GRAPH_NOT_NATIVE'))
 return links,base,p
invoke('coherent_TESTONLY_SDK6_graph')
invoke('SDK5_receipt_rejected',lambda v:v['sdk'].update(decision='PASS_ACTUAL_SDK5_ARTIFACT_AND_PHYSICAL_ACCEPTANCE'),True)
invoke('stale_SDK5_source_rejected',lambda v:v['sdk'].update(source_identity='ba0e1be79e6cd6b06fe0b7cbd1c2c3c689e86579439e13deea9b3f3776069120'),True)
invoke('wrong_selected_source2093_rejected',lambda v:v['links'].update(SDK6_source_identity='0'*64),True)
invoke('read_nonce_mismatch_rejected',lambda v:v['actual'].update(nonce='TESTONLY_STALE_NONCE'),True)
invoke('owner_not_retired_rejected',lambda v:v['owner'].update(retired=False),True)
invoke('driver_source_mismatch_rejected',lambda v:v['driver'].update(source_candidate_sha='0'*64),True)
invoke('driver_artifact_bytes_mismatch_rejected',lambda v:v['driver']['artifacts']['ihk-smp-x86_64'].update(bytes=1),True)
invoke('vermagic_mismatch_rejected',lambda v:v['driver']['artifacts']['ihk'].update(modinfo=dict(vermagic='TESTONLY_WRONG')),True)
invoke('reordered_inventory_rejected',lambda v:v['base']['modules'].reverse(),True)
invoke('native_flag_not_artifact_only_rejected',lambda v:v['sdk'].update(native_acceptance=True),True)
invoke('launcher_source_join_mismatch_rejected',lambda v:v['lreceipt'].update(launcher_source_sha256='TESTONLY_WRONG'),True)
invoke('proof_hash_mutation_rejected',negative=True,after=lambda l,b,p:l['proofs']['SDK6_acceptance'].update(sha256='0'*64))
def drift(l,b,p):
 f=Path(b['modules'][1]['path']);f.write_bytes(b'TESTONLY alteredartifact')
invoke('artifact_bytes_mutation_rejected',negative=True,after=drift)
def changed_source_proof(l,b,p):
 row=copy.deepcopy(a.read(selected['proofs']['SDK6_source_preparation']));row['source_deltas'][0]['new']='0'*64;raw=(json.dumps(row,sort_keys=True)+'\n').encode();f=p/'bad-source.json';f.write_bytes(raw);l['proofs']['SDK6_source_preparation']=dict(path=str(f),sha256=sha(raw),bytes=len(raw))
invoke('selected_f439_source_delta_rejected',negative=True,after=changed_source_proof)
def changed_review(l,b,p):
 row=copy.deepcopy(a.read(selected['proofs']['EVENTFD_source_and_nine_fixture_review']));row['tests']=8;raw=(json.dumps(row,sort_keys=True)+'\n').encode();f=p/'bad-review.json';f.write_bytes(raw);l['proofs']['EVENTFD_source_and_nine_fixture_review']=dict(path=str(f),sha256=sha(raw),bytes=len(raw))
invoke('nine_fixture_review_guard_rejected',negative=True,after=changed_review)
oldproof=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-sdk-preparation-5/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json');oldraw=oldproof.read_bytes();assert sha(oldraw)=='8614e3e2bbf9e07c01f396079fc83fedbbb4119a3c37b5e311bdcc6cb6099623'
invoke('genuine_previous_SDK5_receipt_rejected',negative=True,after=lambda l,b,p:l['proofs'].update(SDK6_acceptance=dict(path=str(oldproof),sha256=sha(oldraw),bytes=len(oldraw))))
# Selected real source/fixture pins are read via unmodified real proof reader.
assert a.read(selected['proofs']['SDK6_source_preparation'])['source_identity']==SOURCE
assert a.read(selected['proofs']['EVENTFD_source_and_nine_fixture_review'])['tests']==9
result=dict(scope=__doc__,status='PASS_ACTUAL_SDK6_AUTHORITY_CONSUMER_CONTROLLED_GRAPH_FIXTURES',cases=len(rows),rows=rows,real_source_preparation_and_nine_fixture_proofs_read=True,controlled_boundary='links() only for TESTONLY graph; unmodified read()/artifact() and actual composite consumer body executed',actual_future_SDK6_acceptance=None,actual_SMP_artifact=None,native_acceptance=False,source_refusals_preserved=True)
with (D/'ACTUAL-AUTHORITY-CONSUMER-RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(result,sort_keys=True))
