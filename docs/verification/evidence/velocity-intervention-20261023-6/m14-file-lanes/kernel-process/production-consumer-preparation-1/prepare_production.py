"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare the accepted dump body against the finite accepted 78-input closure only.
No compiler, test, CPU reservation, canonical mutation or fixture replay.
"""
from pathlib import Path
import hashlib,json,shutil
P=Path(__file__).resolve().parent;B=P.parent;ROOT=Path('/home/holden/mckernel');S=P/'source';O=P/'output-1'
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
 prior=OLD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json';assert pin(prior)['sha256']=='7a0191a235c29356ab48f25fd28e6e33b698ae1bd9a539ab84c795c52fc9993f'
 leaf=B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json';assert pin(leaf)['sha256']=='16fb6f066adb4783c8d5331bd715c5014b76bc555803b32d9ead161be2884859'
 oldr=json.loads((OLD/'EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json').read_text());oldc=json.loads((OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json').read_text())
 refresh={'kernel/rust/x86_cpu_helpers.rs':'26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9','kernel/rust/x86_memory_helpers.rs':'245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2'}
 S.mkdir();inputs={};changes=[]
 for key,row in sorted(oldr['source_inputs'].items()):
  canonical=pin(ROOT/key);expected=refresh.get(key,row['private']['sha256']);assert canonical['sha256']==expected,('unapproved canonical drift',key,canonical,expected)
  if canonical['sha256']!=row['private']['sha256']:changes.append(key)
  take=B/'candidate/kernel/rust/process_helpers.rs' if key=='kernel/rust/process_helpers.rs' else ROOT/key
  dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(take,dest)
  inputs[key]=dict(accepted_before=row['private'],canonical_before=canonical,private=pin(dest),modified_target=key=='kernel/rust/process_helpers.rs')
 assert changes==sorted(refresh) and len(inputs)==78
 assert inputs['kernel/rust/process_helpers.rs']['private']['sha256']=='70015d712c29e416881e2fbaccd67026ee15ac7eb915cb80e828485d6f34d71f'
 assert (S/'kernel/rust/process_helpers.rs').read_text().count('    fn kprintf(format: *const i8, ...) -> CInt;\n')==1
 identity_rows=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in inputs.items()];identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
 rows=[line.split() for line in (OLD/'actual-production-capture-1/01-current78-Rust-symbols/stdout').read_text().splitlines() if line.split()]
 oldT={row[-1] for row in rows if row[-2]=='T'};oldU={row[-1] for row in rows if row[-2]=='U'};assert len(oldT)==3044 and len(oldU)==577
 addT=['clear_range_l3','vm_range_insert_dump_bridge','x86_cpu_ulong_log_bridge'];addU=['process_dump_tree_enabled','x86_clear_l3_child_walk','x86_clear_l3_effect_log','x86_clear_l3_memobj_flush','x86_clear_l3_memobj_rss_sub','x86_clear_l3_range_log','x86_clear_l3_rss_sub','x86_clear_l3_use_1gb_page'];removeU=['vm_range_insert_dump_bridge']
 assert not (set(addT)&oldT) and not (set(addU)&oldU) and set(removeU)<=oldU
 r=dict(oldr);r.update(status='DUMP_CURRENT78_SOURCE_READY_NO_EXECUTION_GRANT',source_inputs=inputs,source_identity_rows=identity_rows,source_identity=identity,accepted_prior_whole_join=pin(prior),accepted_prior_Rust_recipe=pin(OLD/'EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json'),accepted_prior_Rust_symbols=pin(OLD/'actual-production-capture-1/01-current78-Rust-symbols/stdout'),canonical_refresh=refresh,only_private_override_from_current=['kernel/rust/process_helpers.rs'],argv=[arg.replace(str(OLD),str(P)) for arg in oldr['argv']],expected_T_delta=dict(removed=[],added=sorted(addT),before=len(oldT),after=len(oldT)+len(addT)),expected_U_delta=dict(removed=removeU,added=sorted(addU),before=len(oldU),after=len(oldU)-len(removeU)+len(addU)),target_callback='vm_range_insert_dump_bridge',target_selector='process_dump_tree_enabled',symbol_delta_source_basis='Accepted actual7a raw global NM sets: dump bridge U becomes T and new readonly gate U; canonical CPU logger adds T; canonical L3 adds T plus its seven explicit C data callback imports. Existing log bridge/debug selector/kprintf unchanged.',failure_history=dict(prior_E0428_failure=pin(OLD.parent/'PRODUCTION-FIRST-FAILURE-1.json'),prior_E0428_stderr=pin(OLD.parent/'actual-production-capture-1/00-current78-production-Rust-compile/stderr'),sole_correction_accepted=pin(prior),history_not_reset=True,dump_production_failed_candidates=0,next_unexpected_result='STOP preserve whole join; no automatic retry'),accepted_leaf=pin(leaf))
 assert [i for i,(a,b) in enumerate(zip(r['argv'],oldr['argv'])) if a!=b]==[46,47]
 r.pop('sole_source_delta',None);r.pop('private_changed_from_accepted_11a',None)
 write(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json',r)
 headers={};canonical_headers={}
 for key,row in oldc['canonical_headers'].items():
  now=pin(ROOT/key);assert now==row,('header drift',key)
  dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/key,dest);headers[str(dest)]=pin(dest);canonical_headers[key]=now
 for name,row in oldc['headers'].items():
  if not name.startswith(str(OLD/'source')+'/'):assert pin(Path(name))==row;headers[name]=row
 assert len(headers)==73
 assert pin(ROOT/'kernel/process.c')['sha256']=='08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45'
 shutil.copy2(B/'candidate/kernel/process.c',S/'kernel/process.c');assert pin(S/'kernel/process.c')['sha256']=='1ecbc287f2e704e738cc4e9fbe18289226b5aadadc9da88d226dc0ad0bb57234'
 witness=(OLD/'actual-process-debug-header-ABI.c').read_text()+'''extern void vm_range_insert_dump_bridge(struct process_vm *);
extern const int process_dump_tree_enabled;
_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert_dump_bridge),process_vm_range_insert_dump_fn_t),"exact existing dump callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(process_dump_tree_enabled),const int),"readonly original compile-time gate");
_Static_assert(sizeof(struct rb_node)==24 && __builtin_offsetof(struct rb_node,rb_left)==16 && __builtin_offsetof(struct rb_node,rb_right)==8,"real x86_64 rbnode ABI from accepted433 fixture");
'''
 (P/'actual-process-debug-header-ABI.c').write_text(witness)
 c=dict(oldc);c.update(status='DUMP_COMPLETE_SELECTED_GCC9_SOURCE_READY_NO_EXECUTION_GRANT',accepted_prior_complete_C_profile=pin(OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json'),accepted_prior_whole_join=pin(prior),selected_C_argv=[arg.replace(str(OLD),str(P)) for arg in oldc['selected_C_argv']],private_source=pin(S/'kernel/process.c'),canonical_preimage=pin(ROOT/'kernel/process.c'),headers=headers,canonical_headers=canonical_headers,ABI_witness=pin(P/'actual-process-debug-header-ABI.c'),commands=[dict(row,argv=[arg.replace(str(OLD),str(P)) for arg in row['argv']],cwd=str(O),purpose=SCOPE+' '+row['name']+'; dump whole selected GCC9/current78 proof, default GCC14 image/native remain open.') for row in oldc['commands']],expected_C_symbols={'vm_range_insert':'U exactly two unchanged add/split caller relocations','vm_range_insert_dump_bridge':'absent; Rust provides entry','dtree/dump_tree':'absent selected C compute bodies','process_dump_tree_enabled':'R size4 value0 current DEBUG_PRINT_PROCESS absent','process_vm_range_insert_debug':'D32 unchanged original file/function/line2086/flags0'},expected_partial={'vm_range_insert_dump_bridge':'unique Rust T','process_dump_tree_enabled':'unique C R4 value0','vm_range_insert':'unique Rust T; original two actual C caller relocations retained','kprintf':'existing unique fullRust T','other_whole_tree_U':'retained honestly, no raw two-U oracle'},expected_function_relocations={'Rust dump entry':['process_dump_tree_enabled','kprintf'],'Rust log entry':['process_vm_range_insert_debug','kprintf'],'C vm_range_insert callers':2},failure_history=r['failure_history'],predicates_unchanged=False,accepted_leaf=pin(leaf))
 write(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json',c)
 write(P/'COHERENT-CURRENT78-AND-REUSED-LEAF.json',dict(scope=SCOPE,status='SOURCE_READY_ONLY',source_identity=identity,canonical_refresh=refresh,canonical_process=pin(ROOT/'kernel/rust/process_helpers.rs'),private_process=inputs['kernel/rust/process_helpers.rs']['private'],current_scalar=pin(ROOT/'kernel/rust/mem_helpers.rs'),current_syscall=pin(ROOT/'kernel/rust/syscall_policy.rs'),actual433_leaf=pin(leaf),all20_leaf_commands_reused_without_replay=True,prior_full_production=pin(prior),source_count=78,headers=73,expected_T_delta=r['expected_T_delta'],expected_U_delta=r['expected_U_delta'],remaining_C_debt=['Readonly process_dump_tree_enabled data and original fallback only for this body','Other process.c compute bodies remain; next sync_one_page is separate source only'],compiler_jobs=0,CPU_reservations=0,default_image_native_credit=False))
 print(json.dumps(dict(scope=SCOPE,source_identity=identity,Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),expected_T_delta=r['expected_T_delta'],expected_U_delta=r['expected_U_delta']),indent=2))
if __name__=='__main__':main()
