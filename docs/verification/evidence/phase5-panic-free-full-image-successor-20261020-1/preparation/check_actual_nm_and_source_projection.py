"""Exact helper/source projection and saved failed-object metadata only."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,resource,signal,stat
N=Path(__file__).resolve().parent;P=N.parent/'gitlink-nine-copy-observer-correction-1'
driver=N/'native_rust_exact_mckernel_image_offline.py';assert hashlib.sha256(driver.read_bytes()).hexdigest()=='319790fd648ea82c7ef3adc129cc9cc329c08ea23beed105fdfeeb6770f09d9a'
tree=ast.parse(driver.read_text());wanted={'ImageBuildError','_fail','_no_core_panic_undefined'};nodes=[x for x in tree.body if isinstance(x,(ast.ClassDef,ast.FunctionDef)) and x.name in wanted];assert len(nodes)==3
ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(driver), 'exec'),ns);oracle=ns['_no_core_panic_undefined'];Error=ns['ImageBuildError']
positive=oracle('U clone_thread\nw optional_weak_function\nv optional_weak_data\nU ordinary_external\n')
negatives={}
def refused(name,text,expected):
 try:oracle(text)
 except Error as error:
  assert expected in str(error),(name,str(error));negatives[name]=str(error)
 else:raise AssertionError('oracle accepted '+name)
for function in ['panic_bounds_check','unwrap_failed']:
 for representation,symbol in [('demangled','core::panicking::'+function),('raw','_RNvNtCsFAKEFIXTURE_4core9panicking'+str(len(function))+function)]:
  refused(function+'_'+representation,'U clone_thread\nU '+symbol+'\n','unsupported production Rust core panic references')
for name,text in [('empty',''),('missing_provider','U ordinary_external\n'),('duplicate_provider','U clone_thread\nU clone_thread\n')]:refused(name,text,'production Rust undefined provider witness')
for name,text in [('malformed','U\n'),('defined','T clone_thread\n')]:refused(name,text,'production Rust nm row format')
# Read the genuine saved failed production object with actual host nm; no adoption or compiler effects.
obj=P/'full-image-attempt-1/owner-work/output/build/kernel/rust/mckernel_rust.o';before=obj.stat();assert stat.S_ISREG(before.st_mode) and not obj.is_symlink()
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py');sp=importlib.util.spec_from_file_location('accepted_saved_nm_capture',S);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
for number in h.STOP_SIGNALS:signal.signal(number,h.stop)
cap=N/'saved-failed-production-nm-capture-1';cap.mkdir(mode=0o700)
command={'argv':['/usr/bin/nm','--undefined-only','--demangle',str(obj)]}
def limits():
 for kind,value in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_AS,1<<30)]:resource.setrlimit(kind,(value,value))
r=h.owned_capture(command,cap,10,limits);h.write(cap/'closed-record.json',r)
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None
assert Path(r['captures']['stderr']['path']).stat().st_size==0
text=Path(r['captures']['stdout']['path']).read_text();after=obj.stat();fields=['st_dev','st_ino','st_mode','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'];assert all(getattr(before,k)==getattr(after,k) for k in fields)
actual_forbidden=[line for line in text.splitlines() if 'panic_bounds_check' in line or 'unwrap_failed' in line];assert len(actual_forbidden)==2
refused('genuine_saved_failed_production_object',text,'unsupported production Rust core panic references')
stripped='\n'.join(line for line in text.splitlines() if line not in actual_forbidden)+'\n';stripped_control=oracle(stripped)
# Actual deterministic request crossrefs and exact canonical source projection, never owner.validate/run.
sp=importlib.util.spec_from_file_location('actual_successor_owner',N/'native_rust_exact_mckernel_image_container_owner.py');owner=importlib.util.module_from_spec(sp);sp.loader.exec_module(owner)
q=json.loads((N/'source-materialization-1/image-request-SOURCE-BOUND-PROPOSAL.json').read_text());source_positive=owner.preflight_request_crossrefs(q)
old=json.loads((P/'image-request-SOURCE-BOUND-PROPOSAL.json').read_text());stale=dict(q)
for key in ['gitlink_manifest','gitlink_manifest_sha256']:stale[key]=old[key]
try:owner.preflight_request_crossrefs(stale)
except owner.OwnerError as error:assert 'gitlink base manifest hash differs' in str(error);stale_refusal=str(error)
else:raise AssertionError('old supplement accepted')
sp=importlib.util.spec_from_file_location('actual_successor_thin_contract',N/'thin_source_contract.py');thin=importlib.util.module_from_spec(sp);sp.loader.exec_module(thin)
doc=json.loads((N/'thin-inputs.json').read_text());files,metadata=thin.validate_thin_document(doc,q['candidate_sha'],q['ihk_sha']);assert len(files)+len(metadata)==6959
result={'status':'PASS_ACTUAL_HELPER_AND_SAVED_FAILURE_METADATA_PROBE','actual_source_projection':source_positive,'actual_source_entries':len(files)+len(metadata),'source_stale_supplement_refusal':stale_refusal,'parser_positive_U_w_v':positive,'refusals':negatives,'saved_failed_object':{'path':str(obj),'stable_fd_metadata':{k:getattr(after,k) for k in fields},'nm_capture':r,'targeted_panic_rows':actual_forbidden,'unaccepted_old_object':True},'filtered_saved_metadata_positive_control':stripped_control,'filtered_control_is_new_compiler_evidence':False,'actual_repaired_production_object':None,'actual_repaired_final_link':None,'no_compiler_Docker_owner_or_lock_effects':True}
with (N/'ACTUAL-NM-AND-SOURCE-PROJECTION-RESULT.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps({'status':result['status'],'pure_refusals':len(negatives),'saved_targeted_panic_rows':len(actual_forbidden),'source_entries':6959,'new_production_object_proof':False},sort_keys=True))
