#!/usr/bin/env python3
"""Functional OS provenance extraction only; no security testing or execution release."""
import hashlib,json,os,stat,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
REPO=Path('/home/holden/mckernel')
E=REPO/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
H=Path('/home/holden/mckernel-work/host-preparation')
P=E/'f05-v2-root-export-and-native-preparation-source-1'
A=H/'current68-native235-production-binding-20261022-1/launcher-successor-1'
D=A/'driver-hash-correction-1'
W=D/'pinned-launcher-attempt-1/owner-work'
N=H/'numa-allowed-mask-image-successor-preparation-20261021-1'
S=N/'source-materialization-1/materialized-source'
B=W/'output/build'
refs={}
def read(label,path,expected=None):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_size<=(72685013 if label=="toolchain_manifest" else 50_000_000)
  parts=[]
  while True:
   part=os.read(fd,1<<20)
   if not part:break
   parts.append(part)
  data=b"".join(parts)
  after=os.fstat(fd);keys=("st_dev","st_ino","st_mode","st_nlink","st_uid","st_gid","st_size","st_mtime_ns","st_ctime_ns");assert all(getattr(before,k)==getattr(after,k) for k in keys)
 finally:os.close(fd)
 digest=hashlib.sha256(data).hexdigest()
 if expected:assert digest==expected,(label,digest,expected)
 refs[label]={'path':str(path),'sha256':digest,'bytes':len(data)}
 return data

def j(label,path,expected=None):return json.loads(read(label,path,expected))
manifest=j('frozen_manifest',P/'root-adopted-stage-source-1/offline-materialization-1/manifest.HOST-STATIC.json')
selected=manifest['artifacts']['mcexec']; read('selected_launcher',selected['path'],selected['sha256'])
assert selected['sha256']=='dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954'
snapshot=j('snapshot_receipt',H/'p-m06-current68-native-stage-binding-20261022-1/fork-v3-matched-process-successor-1/launcher-runtime-snapshot-1/ACTUAL-LAUNCHER-SNAPSHOT-RECEIPT.json','652afc64ea5346e1e0e36959d2e9801e022c06f2fa501bbd53b24dbb243044ed')
accept=j('independent_artifact_acceptance',D/'INDEPENDENT-ACTUAL-LAUNCHER-PRODUCTION-ARTIFACT-ACCEPTANCE-1.json','5eeb7f2ea4aba4421d7d79ed935946506a12720d0c7711e01d30065cb14dda54')
r=j('actual_build_receipt',W/'evidence/receipt.json',accept['receipt']['sha256'])
assert r['status']=='PASS' and r['artifacts']['mcexec']['sha256']==selected['sha256']
for name,row in r['artifact_copies'].items():read('artifact_'+name,W/'evidence/artifacts'/name,row['sha256'])
plan=j('actual_build_plan',D/'bound-source-1/launcher-plan.json','3f86f9b3db382536f7ccce7cdccf596f65a2c68e67611e08cb6f7f7a92733162')
read('actual_build_driver',D/'bound-source-1/launcher_only_offline.py','af2b090105083607c2e986a1f936be7459f8221da01bc5617ede6731dd0aa883')
read('actual_source_review',plan['source_review']['path'],plan['source_review']['sha256'])
source=j('source_manifest',N/'thin-inputs.json',r['source_manifest_sha256'])
csha=source['materialized_repository_files']['executer/user/mcexec.c']
c=read('C_consumer_source',S/'executer/user/mcexec.c',csha).decode()
rs=read('actual_Rust_helper_source',plan['source_override']['path'],r['launcher_source_sha256']).decode()
base=j('inherited_base_build_receipt',N/'full-image-attempt-1/owner-work/evidence/receipt.json')
assert base['status']=='PASS' and base['source_manifest_sha256']==r['source_manifest_sha256']
for name,rel in [('C_object','executer/user/CMakeFiles/mcexec.dir/mcexec.c.o'),('archive','executer/user/libmcexec.a')]:
 expected=r['artifact_copies']['mcexec.c.o' if name=='C_object' else 'libmcexec.a']['sha256']
 read('inherited_base_'+name,N/'full-image-attempt-1/owner-work/output/build'/rel,expected)
 read('actual_build_'+name,B/rel,expected)
config={}
for name,rel in [('cache','CMakeCache.txt'),('C_flags','executer/user/CMakeFiles/mcexec.dir/flags.make'),('C_rule','executer/user/CMakeFiles/mcexec.dir/build.make'),('C_compiler','CMakeFiles/3.31.8/CMakeCCompiler.cmake')]:config[name]=read(name,B/rel).decode()
assert 'ENABLE_RUST_USER_TOOLS:BOOL=ON' in config['cache']
assert '-DMCEXEC_RUST_HELPERS' in config['C_flags']
assert 'mcexec_main_loop_thread_func_body' in c and '#define main_loop_thread_func mcexec_main_loop_thread_func_body' in c
assert 'fn mcexec_main_loop_thread_func_body' in rs
config['link']=read('link_rule',B/'executer/user/CMakeFiles/mcexec.dir/link.txt',r['artifact_copies']['mcexec-link.txt']['sha256']).decode()
config['Rust_rule']=read('Rust_rule',B/'executer/user/CMakeFiles/mcexec_rust_helpers.dir/build.make',r['artifact_copies']['mcexec-rust-build.make']['sha256']).decode()
tool=j('toolchain_manifest',H/'four-callback-affinity-image-preparation-20261019-1/image-toolchain.json',r['toolchain_manifest_sha256'])
rawlog=read('actual_build_stdout',W/'evidence/build.stdout.log',r['inventory']['build.stdout.log']['sha256']).decode()
read('actual_build_stderr',W/'evidence/build.stderr.log',r['inventory']['build.stderr.log']['sha256'])
notes=subprocess.run(['/usr/bin/readelf','-n',selected['path']],check=True,capture_output=True,text=True,timeout=5).stdout
buildid=next(z.split('Build ID: ',1)[1].strip() for z in notes.splitlines() if 'Build ID: ' in z)
assert buildid=='bb2874732ffa009613fec0254a5c87acef11b758'
consumer=manifest['cleanup_profile']['consumer'];host=read('selected_mcctrl_consumer',consumer['path'],consumer['sha256']).decode()
assert 'trace_budget: AtomicI32::new(64)' in host and 'let traced = number == 231 || self.trace();' in host
read('selected_mcctrl_module',manifest['modules'][2]['path'],manifest['modules'][2]['sha256'])
lwk=read('selected_LWK_debug_source',E/'current110-host19-production-preparation-source-1/rust-subtree/syscall_policy.rs','2ddde21dfcf32402d281d7ba70e62d765cb60e60bf225d7303b17221959a5477').decode()
assert 'const LOG_BUDGET_LIMIT: u32 = 128;' in lwk
publication=j('source_publication_rows',P/'source-publication-preparation-1/EXACT-SOURCE-PUBLICATION-ROWS.json')
assert len(publication['rows'])==155

def excerpts(text,needles,before=3,after=5):
 lines=text.splitlines(); found=[]
 for i,line in enumerate(lines):
  if any(z in line for z in needles):found.append({'line':i+1,'context':'\n'.join(lines[max(0,i-before):i+after+1])})
 return found
report={
 'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 'status':'EXACT_RETAINED_MIXED_C_CONSUMER_RUST_HELPER_LAUNCHER_JOIN_PASS_WITH_EXPLICIT_SCOPE_LIMITS',
 'selected_binary':dict(selected,build_id=buildid),
 'classification':'Existing working C-consumer launcher with default Rust helpers; not the newly installed all-Rust executor e5d18169 and not an all-C binary.',
 'references':refs,
 'compiler':{'C':tool['image_tools']['cc'],'Rust':tool['rustc'] if 'rustc' in tool else accept['compiler'],'linker':tool['image_tools']['ld']},
 'actual_build_commands':r['commands'],'inherited_base_configure':base['commands'][0],
 'actual_build_stdout':rawlog,
 'configuration':config,
 'source_object_chain':{'C_source_sha256':csha,'C_object_sha256':r['artifacts']['mcexec.c.o']['sha256'],'Rust_source_sha256':r['launcher_source_sha256'],'Rust_object_sha256':r['artifacts']['mcexec_helpers.o']['sha256'],'archive_sha256':r['artifacts']['libmcexec.a']['sha256'],'link_sha256':r['artifacts']['mcexec-link.txt']['sha256'],'C_object_rebuilt_in_successor':False,'inherited_C_object_equality_verified':True,'base_source_manifest_matches_actual_successor':True,'new_Rust_object_and_relink_in_actual_stdout':True},
 'C_Rust_dispatch_excerpts':excerpts(c,['#define main_loop_thread_func','int act_main_loop_body','int main_loop(']),
 'host_forward_trace':{'provider':'Rust mcctrl Registration, separate from launcher and LWK syscall debug','consumer_sha256':consumer['sha256'],'module_sha256':manifest['modules'][2]['sha256'],'initial_ordinary_budget':64,'scope':'Per Registration::acquire connection, atomic positive-count decrement per committed ordinary delivery. No PID-reset logic in this host counter.','admission':'After COPIED_SYSCALL invoke and user-copy success, number231 short-circuits sampling and is always traced. Other deliveries reserve self.trace(); delivery_trace is retained per HostWorker and controls matching route/return rows.','not_a_workload_quota':True,'excerpts':excerpts(host,['fn trace(&self)','trace_budget: AtomicI32::new(64)','let traced = number == 231','application_syscall=delivered','application_syscall=returned','application_syscall=return_route'])},
 'LWK_debug_trace':{'limit':128,'scope':'Separate ENTRY_LOG_BUDGET and RETURN_LOG_BUDGET packed atomic PID/count words. A changed current PID resets count and reserves record1. Diagnostic mcexec_v10 rows, not host delivery trace quota.','excerpts':excerpts(lwk,['const LOG_BUDGET_LIMIT','fn reserve_log_budget','if reserve_log_budget(&ENTRY_LOG_BUDGET','if reserve_log_budget(&RETURN_LOG_BUDGET'])},
 'source139_context':{'publication_rows':155,'retained_owner_source_rows':143,'actual_new_source_or_static_binding_rows':12,'original_139_owner_predicates':'Retained unchanged; distinct from155 exported publication rows','qualification':'Existing publication referenced unchanged; this bounded extraction does not reread or requalify all139 owner predicates.'},
 'unknowns_and_limits':['No fresh compilation or compiler execution performed. C object is genuinely inherited and byte-equal to retained configured-base object; successor stdout rebuilds only Rust helper and relinks.','No claim that current canonical Rust SDK source generated dca025; exact old C31030130 and Rust8f9fbe47 sources are named separately.','No new native/runtime acceptance or live holder observation performed.','The frozen manifest declares mcctrl consumer8bf30/module57546. This extraction verifies both files and exact existing declaration, not a new independent module compiler-source proof. Retained module acceptance remains authoritative.','LWK128 diagnostic counter does not prove128 host forward samples. Host ordinary budget64 can exhaust; lifecycle records and number231 exception are separate.','Observer claim that prerequisite child/write/wait rows occur within the budget is a separate actual native evidence predicate; this source extraction does not assert future sequence counts or gate success.'],
 'operations':{'compile':0,'Docker':0,'native':0,'guard':0,'resources':0,'canonical_writes':0,'Git':0},
 'next_check':'Independent reader verifies referenced hashes and exact declared source/object/config chain; causal supervisor must preserve ordinary64 sampling and number231 exception without depending on complete gate syscall traces.',
 'constraints':{'UTC_hard_cutoff':'2026-10-28T05:36:09Z','MONO_hard_cutoff':947874.5689514667,'BOOT_hard_cutoff':963213.6960030915,'credit_run':'7f4af94a83b14cc08f97401f5891d965','credit_ceiling':57774.852125,'prior_spent_floor':22812.3311,'all_holds_and_parent_exclusive_controls_preserved':True}}
report['extractor']={'path':str(Path(__file__).resolve()),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p=OUT/'READY.json'
with p.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'status':report['status'],'READY':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'references':len(refs),'BuildID':buildid}))
