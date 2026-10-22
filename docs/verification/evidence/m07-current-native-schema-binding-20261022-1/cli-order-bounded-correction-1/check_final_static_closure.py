"""Actual final-only pure control/hash/FD joins; no clocks, snapshot or runtime.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os,socket,stat,subprocess,sys
D=Path(__file__).resolve().parent;Q=D/'native-packet-1'
REVIEW=None
REVIEW_SHA=None
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:os.fchmod(f.fileno(),0o600);f.write(json.dumps(v,sort_keys=True,indent=2)+'\n')
def need(v,s):
 if not v:raise AssertionError(s)
def forbidden(*a,**k):raise AssertionError('pure final static closure prohibits process/socket/backend/root')
def main():
 subprocess.Popen=forbidden;subprocess.run=forbidden;socket.socket=forbidden;os.execve=forbidden
 need(len(sys.argv)==4,'usage: check_final_static_closure.py GENUINE_PENDING_REVIEW SHA256 BYTES')
 review=ref(sys.argv[1]);need(review['sha256']==sys.argv[2] and review['bytes']==int(sys.argv[3]),'whole genuine independent pending review descriptor')
 authority=load(sys.argv[1]);need(authority['implementation_ownership'] is False and authority['reviewer'] and authority['decision']=='PASS_CURRENT_NATIVE_SCHEMA_PENDING19_SOURCE_DATA_BINDING_ONLY' and authority['findings']==[],'independent passing source/data review')
 pending=load(D/'actual-whole-caller-result.json')['actual_pending_outputs']
 outputs={}
 for row in pending:
  assert ref(row['path'])==row
  p=Path(row['path']);name=p.name.removesuffix('.PENDING-STATIC-CORRECTED')
  # Python3.9 has no str.removesuffix dependency outside this interpreter.
  target=p.with_name(name);assert target!=p and target.exists()
  outputs[target]=target.read_bytes()
 assert len(outputs)==19
 packet=load(Q/'NATIVE-COHERENT-REVIEW-PACKET.json');cfg=load(Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json');seven=load(Q/'FINAL-SEVEN-ROOT-CALL-DATA.json');b=load(D/'fresh-snapshot-bindings.json');c=load(D/'STATIC-NONTEMPORAL-INPUTS.json')
 assert packet['static_decision']==cfg['static_review']==b['static_review']==review
 assert packet['status']=='BOUND_NON_TEMPORAL_PENDING_ROOT_ADMISSION' and packet['actual_guest_runs']==0 and packet['native_runtime_authority'] is False
 assert packet['root_executor']==ref(Q/'root-execute-seven-1.py') and packet['root_caller']==ref(Q/'root-run-exact-readonly-stage.py') and packet['final_guard_source']==ref(Q/'review_final_threads_release.py')
 assert cfg['snapshot_bindings']==ref(D/'fresh-snapshot-bindings.json') and cfg['snapshot_adapter']==ref(D/'root_manual_snapshot_threads.py')
 assert cfg['machine_base']==ref(Q/'machine-base.json') and cfg['machine_base_object']==load(Q/'machine-base.json')
 base=cfg['machine_base_object'];assert base['runtime_release'] is False and base['fresh_live_preflight'] is None
 for k in ('snapshot_output','final_machine_output','final_guard_output'):assert not os.path.lexists(seven[k])
 assert all(not os.path.lexists(p) for p in seven['fresh_capture_and_actual_command_paths'])
 assert packet['current_heavy_released_record']==cfg['current_heavy_released_record']==b['current_heavy_released_record']
 assert packet['legacy_reference_scope']==cfg['legacy_reference_scope']==b['legacy_reference_scope']=='NATIVE_TERMINAL_ANCESTRY_ONLY_C9_RELEASED_BUILD_ANCESTRY'
 assert packet['external_latest_native_physical_review']==cfg['external_latest_native_physical_review']==b['external_latest_native_physical_review']
 # Run exactly the selected binder's pure final 19-output/7-step/49-path function.
 tree=ast.parse((D/'bind_numa_native_packet.py').read_text());names={'derive_current_readbacks','validate_current_path_join'}
 selected=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
 assert len(selected.body)==2
 namespace=dict(Path=Path,json=json,hashlib=hashlib,need=need)
 exec(compile(selected,str(D/'bind_numa_native_packet.py'),'exec'),namespace)
 binding=load(c['actual_binding_result']['path']);pre=load(c['actual_full_preflight']['path'])
 namespace['validate_current_path_join'](outputs,D,binding,pre)
 # Execute the actual final guard's static source/FD consumer only, no main/live fields.
 source=Q/'review_final_threads_release.py';spec=importlib.util.spec_from_file_location('actual_final_guard_static_sources',source);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 guard_count=guard.check_runtime_sources(cfg)
 # Final17 sources use the actual new unsuffixed executor object, never its pending FD.
 prior=load(D/'ACTUAL-COMPLETE-CONTROL-AND-FD-CLOSURE.json')
 code=[ref(Q/'root-execute-seven-1.py') if row['path'].endswith('/root-execute-seven-1.py.PENDING-STATIC-CORRECTED') else row for row in prior['code']]
 assert len(code)==len({row['path'] for row in code})==17
 identities={}
 objects=code+[prior['descriptor'],prior['external_qualified_caller_helper']]
 for row in objects:
  p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
  try:
   a=os.fstat(fd);raw=b''
   while True:
    chunk=os.read(fd,1<<20)
    if not chunk:break
    raw+=chunk
   z=os.fstat(fd);named=p.lstat()
   assert stat.S_ISREG(a.st_mode) and all(getattr(a,k)==getattr(z,k)==getattr(named,k) for k in FIELDS)
   assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes']
   identities[str(p)]={k:getattr(a,k) for k in FIELDS}
  finally:os.close(fd)
 expected_map=load(cfg['runtime_source_fd_identity_map']['path'])['identities']
 assert len(expected_map)==12 and {p:identities[p] for p in expected_map}==expected_map
 assert identities[str(Q/'root-execute-seven-1.py')]['st_ino']!=prior['full_nine_field_identities'][str(Q/'root-execute-seven-1.py.PENDING-STATIC-CORRECTED')]['st_ino']
 publication=[]
 for i,row in enumerate(objects):
  publication.append(dict(source=row,repository_path='docs/verification/evidence/m07-diagnostic-final-source-20261022-1/%02d-%s'%(i,Path(row['path']).name),kind='python' if i<17 else ('descriptor' if i==17 else 'qualified_caller_helper')))
 result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_FINAL_REVIEW19_CONTROL7_STEPS49_PATHS_AND17_SOURCE19_FD12_RUNTIME_JOINS_ONLY',actual_review=review,actual_final_outputs=[ref(p) for p in sorted(outputs)],actual_final_code=code,descriptor=prior['descriptor'],qualified_caller_helper=prior['external_qualified_caller_helper'],full_nine_field_identities=identities,runtime12_FD_map=cfg['runtime_source_fd_identity_map'],guard_runtime_rows=guard_count,root_code_paths=[row['path'] for row in code],source_publication_map=publication,final_executor=ref(Q/'root-execute-seven-1.py'),pending_originals_preserved=True,final_guard_main_executed=False,source_publication_fetched_proof=None,fresh_runtime_grant=None,snapshot=None,runtime_release=None,guest_runs=0,root_operations=0)
 write(D/'ACTUAL-FINAL-CONTROL-SOURCE-FD-CLOSURE.json',result)
 print(json.dumps(dict(status=result['status'],final_outputs=19,code=17,FD_objects=19,runtime_python=12,steps=7,fresh_paths=49,source_publication_fetched_proof=None,snapshot=None,runtime_release=None),sort_keys=True))
if __name__=='__main__':main()
