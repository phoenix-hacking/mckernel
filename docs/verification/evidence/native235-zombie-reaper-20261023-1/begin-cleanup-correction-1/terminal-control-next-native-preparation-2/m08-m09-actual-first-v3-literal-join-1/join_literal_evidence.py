"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite existing-evidence join; no compiler, tests, probes or runtime operation.
"""
from pathlib import Path
import difflib,hashlib,json,re
D=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2')
E=N/'m08-m09-actual-first-v3-literal-join-1';E.mkdir()
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw))
def load(p,sha=None):
 raw=p.read_bytes()
 if sha:assert hashlib.sha256(raw).hexdigest()==sha
 return json.loads(raw)
def write(name,value):
 raw=(json.dumps(value,indent=2)+'\n').encode();(D/name).write_bytes(raw);(E/name).write_bytes(raw);return ref(D/name)
ledger=Path('/home/holden/mckernel/docs/verification/os-milestones-20260914/practical-milestones.json');lv=load(ledger)
found={}
def find(v):
 if isinstance(v,dict):
  if v.get('id') in ('M08','M09'):found[v['id']]=v
  for x in v.values():find(x)
 elif isinstance(v,list):
  for x in v:find(x)
find(lv)
active={k:{name:v[name] for name in ('id','title','exit_condition','completion_status','current_evidence_summary')} for k,v in found.items()}
for k in active:
 active[k]['checks']=[{name:c[name] for name in ('id','description','status','assessment_note')} for c in found[k]['checks']]
active['M09']['scope_separation_20261023']=found['M09']['scope_separation_20261023']
oldmap=N/'m05-readiness-runtime-failure-2/next-batch-binding-preparation-1/M08-M09-OBSERVATION-MAP.PENDING-FIRST-V3.json';ov=load(oldmap)
assert ref(oldmap)['sha256'].startswith('b8bb0fb6')
P=N/'m05-readiness-runtime-failure-2/coherent-successor-preparation-1/next-native-preparation-1/actual-post-physical-1'
formal=P/'INDEPENDENT-FORMAL-FIRST-V3-RESTORATION-AND-APPLICATION-ACCEPTANCE.json';fv=load(formal,'12a05b2ddd7b3628511f7b5a6e414e08e1d6a4a3e462b1a51228e8a668ec5b5b')
physical=Path(fv['physical_acceptance']['path']);pv=load(physical,fv['physical_acceptance']['sha256'])
inner=P/'authenticated-owner-export/inner-result.json';iv=load(inner,fv['actual_inner_sha256']);lines=iv['observation']['serial'].splitlines()
strict235=N/'INDEPENDENT-FORMAL-STRICT235-APPLICATION-ACCEPTANCE.json';s235=load(strict235)
strict227=N/'INDEPENDENT-FORMAL-STRICT227-ADDITIVE-APPLICATION-ACCEPTANCE.json';s227=load(strict227)
SDK=N.parent/'terminal-control-sdk-preparation-5/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json';sv=load(SDK)
actual=Path(sv['actual_reads']['path']);av=load(actual,sv['actual_reads']['sha256'])
owner=Path(sv['owner_receipt']['path']);so=load(owner,sv['owner_receipt']['sha256']);driver=so['driver_receipt']
IM=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/INDEPENDENT-ACTUAL-MATCHED-IMAGE-ARTIFACT-REVIEW-1.json');im=load(IM);ir=Path(im['producer_receipt']['path']);irv=load(ir,im['producer_receipt']['sha256'])
LA=Path('/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/INDEPENDENT-ACTUAL-LAUNCHER-PRODUCTION-ARTIFACT-ACCEPTANCE-1.json');la=load(LA);lr=Path(la['receipt']['path']);lrv=load(lr,la['receipt']['sha256'])
M=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-readiness-runtime-failure-2/coherent-successor-preparation-1/actual-stage-successor-1/manifest.json');mv=load(M,fv['manifest_sha256'])
assert mv['artifacts']['mckernel_image']['sha256']==fv['image_sha256']==im['artifacts']['mckernel.img']['sha256']
assert mv['artifacts']['mcexec']['sha256']==fv['launcher_sha256']==la['elf']['sha256']
assert {Path(row['path']).name:row['sha256'] for row in mv['modules']}=={name:row['sha256'] for name,row in sv['artifacts'].items()}
for name,sha in [('smp_application.rs','f5c56d83'),('smp_service.rs','ffefabad')]:assert driver['source_sha256'][name].startswith(sha)
PREP=Path('/home/holden/mckernel-work/host-preparation/native235-procfs-delete-sdk-preparation-20261023-5/prepared-sdk/preparation.json');new=load(PREP)
MAP=Path(new['current_closure_ref']['path']);mp=load(MAP,new['current_closure_ref']['sha256']);OLD=Path(mp['predecessor_preparation']['path']);old=load(OLD,mp['predecessor_preparation']['sha256'])
oldrows={r['path']:r for r in old['closure']};newrows={r['path']:r for r in new['closure']}
changed=sorted(k for k in newrows if oldrows[k]['sha256']!=newrows[k]['sha256']);assert changed==['smp_application.rs','smp_service.rs'] and len(newrows)==len(oldrows)==68
assert all(driver['source_sha256'][k]==v['sha256'] for k,v in newrows.items())
source_diffs={}
for name in changed:
 a=Path(oldrows[name]['origin']).read_text().splitlines();b=Path(newrows[name]['origin']).read_text().splitlines()
 source_diffs[name]='\n'.join(difflib.unified_diff(a,b,fromfile='SDK4/'+name,tofile='SDK5/'+name,n=3))+'\n'
# Literal factual rows from the already adjudicated inner capture, not a new oracle.
trace=[]
for index,line in enumerate(lines,1):
 if 'host_mapping=invalidated os=0 generation=' in line or ('application ' in line and any(mark in line for mark in ('cleanup ACK ','procfs deleted ','retirement ','SCHEDULE '))):trace.append({'serial_line':index,'raw':line})
def stream_rows(prefix):
 chunks=[]
 for line in lines:
  if line.startswith(prefix+' '):
   row=json.loads(line[len(prefix)+1:])
   if row['name']=='stdout':chunks.append(row)
 data=b''.join(bytes.fromhex(row['hex']) for row in sorted(chunks,key=lambda row:row['offset']))
 return [json.loads(line) for line in data.splitlines()]
resources={name:stream_rows(marker) for name,marker in [('first','ND_RESOURCE_CHUNK'),('second','ND_SECOND_RESOURCE_CHUNK')]}
for name,rows in resources.items():
 assert any(r.get('stage')=='destroy_os' and r.get('linux_result')==0 for r in rows)
 assert any(r.get('stage')=='reserved_mem_final' and r.get('linux_result')==0 for r in rows)
assert len([r for r in trace if 'host_mapping=' in r['raw']])==2
contract=write('ACTIVE-LITERAL-CONTRACT-AND-STALE-MAP-COMPARISON.json',{'scope':__doc__,'ledger':ref(ledger),'active':active,'old_pending_map':ref(oldmap),'old_map_bytes_preserved':True,'scope_resolution':{'current_M08':'Used boot/resource/process/mapping/shutdown ABI paths and changed unsafe boundaries; no universal unconsumed-path mapping matrix is stated.','current_M09':'Changed consumed Rust/C/assembly boundaries in final artifact set; preserve existing Rust consumers and explicit host compatibility exceptions.','superseded_nested_M09_retirement_wording':'Historical preserved scope_alignment completion_requirement is explicitly superseded by M14 separation; it is not an additional M09 gate.','old_exhaustive_mapping_beyond_consumed_selected_paths':'Extra breadth in pending observation map, not an active check clause; retain as deferred qualification, not invented optional acceptance gate.','old_first_V3_null_slots':'Now bind accepted formal12a05b2d, physical1f3c1830 and inner532aeb25 without rewriting old map.','ten_cycles_LONG':'P-M05-03/P12 repetition/work requirements remain separate; current M08/M09 clauses do not require10cycles or an hour workload.'}})
observations=write('ACTUAL-USED-ABI-CLAUSE-OBSERVATIONS.json',{'scope':__doc__,'first_V3_formal':ref(formal),'physical':ref(physical),'actual_inner':ref(inner),'actual_manifest':ref(M),'strict235':ref(strict235),'strict227':ref(strict227),'clauses':[
 {'clause':'boot','observed':'Matched SDK5 three modules load; strict status5 initial boot and reboot, exact unchanged10972 image/dca launcher, actual generations1 and2.','evidence':[ref(formal),ref(M)],'literal_observed':True},
 {'clause':'resource','observed':'Actual public destroy/release after both stops; CPUs/hardware/NUMA identities1,2 and exact134217728-byte memory extent restored, final reserved memory0 and resource ownership cleared.','evidence':[ref(formal),ref(inner)],'literal_observed':True},
 {'clause':'process','observed':'Strict235 actual fork/exec/wait/ENOENT/reap/ECHILD and parent retirement; preserved227 original cancellation/recovery stdout/exit37 routes and parent retirement; V3 both application EOF/reap/procfs-empty, real BEGIN ACK then actual final0 before shutdown.','evidence':[ref(strict235),ref(strict227),ref(formal)],'literal_observed':True,'not_inferred':'Universal child-credit0, recovery child261 final0, broader fork/COW/exhaustive syscalls are not claimed.'},
 {'clause':'mapping','observed':'Actual application execution/bytes in both generations plus explicit host_mapping=invalidated os0 gen1 pid255 and gen2 pid264; retained current module MM-provider ABI/unique-link proof and CPU/memory geometry readbacks.','evidence':[ref(inner),ref(SDK),ref(owner)],'literal_observed':True,'not_inferred':'Unconsumed negative MM error-injection, all mapping variants, universal unsafe-branch oracles are deferred and not made active by this join.'},
 {'clause':'shutdown/lifetime','observed':'Normal BEGIN ACK +procfs deletion+final retirement0 both epochs; second epoch observes pending-11 token42 then distincttoken43/0 before shutdown; strict5→0, public destroy/release, reboot and second stop, QMP shutdown and independent physical retirement.','evidence':[ref(formal),ref(physical),ref(inner)],'literal_observed':True}
 ],'selected_actual_serial_rows':trace,'decoded_actual_public_resource_stdout':resources,'formal_facts':{k:fv[k] for k in ('actual_generations','actual_apps','CPU_hardware_NUMA_identities_restored','memory_extent_bytes','memory_extent_start','resource_ownership_cleared','destroy_success','final_reserved_memory','strict_status5_reboot','second_stop_release','QMP_shutdown_supported')},'raw_protocol_false_flags_rewritten':False,'new_runtime_runs':0})
mm=driver['artifacts']['mcctrl']['actual_mm_provider']
boundaries=write('CHANGED-CONSUMED-SOURCE-BOUNDARY-JOIN.json',{'scope':__doc__,'actual_SDK5_acceptance':ref(SDK),'actual_SDK5_reads':ref(actual),'actual_owner_driver_receipt':ref(owner),'current_source_map':ref(MAP),'predecessor_accepted_source_preparation':ref(OLD),'source_map_comparison':'Exact existing68-row maps compared; no new source-tree census or module/image hashing.','only_changed_sources_over_SDK4':[{**{k:newrows[name][k] for k in ('path','origin','sha256','bytes')},'predecessor_sha256':oldrows[name]['sha256']} for name in changed],'unchanged_source_rows':66,'actual_source_compiler_match':True,'actual_changed_body_diffs':source_diffs,'changed_boundary_coverage':[
 {'path':'smp_application.rs','change':'Add safe Rust retained Arc<ProcfsProcess> lookup for DELETE after terminal intent/revoke, retaining exact-generation Entry/Remote ownership; reject quarantine/invalidcpu; no guest-memory/MM/backend admission or cleanup authority granted.','ABI':'Internal pub(crate) method only; no exported ABI layout/FFI signature added or changed.','native_consumed':'Actual first-V3 gen1 andgen2 real procfs deleted rows after cleanup ACK, including gen2 pending retirement→deletion→final0; strict235/227 accepted lifecycle routes retain independent process evidence.'},
 {'path':'smp_service.rs','change':'Dispatch existing procfs CREATE0x44 through normal admission, existing DELETE through retained lookup so actual destructor can drain ledger after MM/backend admission closes.','ABI':'Existing service message/envelope and pending-ledger protocol preserved; no C/assembly source delta.','native_consumed':'Actual DELETE/procfs-empty and final retirement/physical resource release both generations; normal ACK and abandoned1 second-generation branch are observed.'}
 ],'unchanged_final_kernel':{'acceptance':ref(IM),'actual_receipt':ref(ir),'image':im['artifacts']['mckernel.img'],'named_import_unique_link_observations':im['observations'],'compiler_ABI_phases':[{'phase':r['phase'],'exit_code':r['exit_code']} for r in irv['commands'] if any(k in r['phase'] for k in ('abi','release','affinity','build'))],'scope':'Reuse accepted source/compiler/C assertions/layout/full-crate and named fork/exec/NUMA/scheduler final-image proof; unchanged10972 actually executes in strict235 andfirstV3. No additional canonical/M14 source is imputed to this frozen image.'},'unchanged_actual_launcher':{'acceptance':ref(LA),'receipt':ref(lr),'elf':la['elf'],'Rust_object':la['rust_object'],'verified_actual_scope':la['verified_actual_scope'],'native_consumed':'Actual dca launcher selected in strict235/227 andfirstV3; no build-produced689d launcher substitution.'},'explicit_host_C_exception':{'source':'mcctrl_vm_write_compat.c','sha256':driver['source_sha256']['mcctrl_vm_write_compat.c'],'purpose':'Existing Linux control-plane mmap_write_lock/unlock/vma_start_write wrappers, permitted host compatibility C. No new compute-kernel C.','actual_final_module_symbol_proof':mm['artifacts']['mcctrl.ko']['symbols'],'actual_Rust_object_emitted_references':mm['artifacts']['mcctrl_rust.o']['symbols'],'compiler_members':mm['artifacts']['command_bindings']['members']},'assembly':'No new/changed SDK5 assembly relative to SDK4; retained source/compiler/ABI proof reused. No new hardware qualification claim.','canonical_M14_not_consumed':'Later canonical/private Rust retirement edits are not linked into unchanged10972 and do not become M08/M09 prerequisites. M14 remains separately open.','raw_failed_DWARF_and_old_acceptance_flags':'Unchanged; this join relies on accepted actual successful compiler/C assertion/layout receipts and native supported paths, never relabels oldfailed DWARF as pass.'})
result=write('LITERAL-M08-M09-REVIEW-READY.json',{'scope':__doc__,'status':'REVIEW_READY_LITERAL_USED_ABI_AND_CHANGED_CONSUMED_FINAL_BOUNDARY_CLOSURE','contract':contract,'actual_used_ABI_clauses':observations,'changed_consumed_source_boundary_join':boundaries,'proposed_literal_check_outcomes':{'P-M08-02':'All stated used boot/resource/process/mapping/shutdown ABI and changed consumed unsafe/lifetime boundaries have finite existing evidence; independent literal closure review ready.','M08':'P-M08-01 remains accepted; P-M08-02 review-ready completes stated matched module build/load+used ABI/lifetime exit if independently accepted.','P-M09-02':'Actual compiled/linked selected current image+launcher/SDK5 source set and only two newly changed consumed provider paths now have source/compiler/ABI+native supported-path evidence; independent literal closure review ready.','M09':'Existing Rust consumers remain active through actual Rust image/launcher/module consumers; explicit host C exception and unchanged assembly retained. M14 whole C retirement remains separate.'},'concrete_unproven_active_clause_identified':None,'no_new_runtime_observation_required_by_current_literal_clause':'No ten-cycle/LONG result is required solely to fill the now-observed first-V3 slot; those remain real separate M05/P12 obligations. Independent reviewer may identify a specific contradictory active clause, but no unbounded remaining-coverage gate is invented.','preserved_limits':['227 recovery child261 final retirement0 unobserved; no all-child-credit claim','No exhaustive mapping/error-injection/unused ABI or hardware/fallback/legacy qualification newly claimed','Whole supported compute-C retirement remains active M14, unclosed','Ten cycles and actual LONG launch/work quotas remain open; no accepted count change from this join','Old observation-map/raw protocol false flags, source-only preparation NULLs, failed evidence and all historical scores retained'], 'canonical_ledger_status_changes':False,'independent_literal_verdict':None,'operations':{'new_guest_runs':0,'tests':0,'compiler':0,'probes':0,'root':0,'Docker':0,'big_artifact_hashes':0,'whole_kernel_census':0},'next':'Focused independent literal review of these exact three joins; dispatcher alone records any practical check/milestone closure.'})
for p in D.iterdir():
 if p.is_file() and p.suffix=='.py':(E/p.name).write_bytes(p.read_bytes())
print(json.dumps(result))
