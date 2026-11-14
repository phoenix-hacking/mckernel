"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only: no subprocess/compiler/ELF/object read or hash.
"""
from pathlib import Path
import copy,difflib,hashlib,json,os,shutil
R=Path(__file__).resolve().parent;D=R.parent;P=D/'production-consumer-preparation-1'
SCOPE=__doc__.splitlines()[0]
def need(x,m):
 if not x:raise ValueError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return {'path':str(p),'sha256':sha(b),'bytes':len(b)}
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n')
def text(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
old1='let value = unsafe { words.add(i + 5).read() };'
new1='let value = unsafe { core::ptr::read_volatile(words.add(i + 5)) };'
old2='unsafe { words.add(i).write(value); }'
new2='unsafe { core::ptr::write_volatile(words.add(i), value); }'
product=P/'source/kernel/rust/x86_cpu_helpers.rs';original=product.read_text()
need(sha(original.encode())=='a32331e70c67da87aedc801e38ee4c557c821f4977afe088bfa8e15ec93ccf9b','failed source retained')
start=original.index('pub unsafe extern "C" fn mod_nmi_ctx(');end=original.index('\n}\n',start)+3
body=original[start:end];need(body.count(old1)==body.count(old2)==1,'one product loop pair')
changed=body.replace(old1,new1).replace(old2,new2)
corrected=original[:start]+changed+original[end:]
need(corrected.replace(new1,old1).replace(new2,old2)==original,'only pair changed')
text(R/'candidate/kernel/rust/x86_cpu_helpers.rs',corrected)
shutil.copyfile(D/'candidate/arch/x86_64/kernel/cpu.c',R/'candidate/arch/x86_64/kernel/cpu.c') if (R/'candidate/arch/x86_64/kernel').mkdir(parents=True,exist_ok=True) is None else None
text(R/'VOLATILE-ONLY-FROM-FAILED-a323.patch',''.join(difflib.unified_diff(original.splitlines(True),corrected.splitlines(True),fromfile='a/kernel/rust/x86_cpu_helpers.rs',tofile='b/kernel/rust/x86_cpu_helpers.rs')))
canonical=Path('/home/holden/mckernel')
full=''
for key in ['arch/x86_64/kernel/cpu.c','kernel/rust/x86_cpu_helpers.rs']:
 before=(canonical/key).read_text();after=(R/'candidate'/key).read_text();full+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+key,tofile='b/'+key))
text(R/'COHERENT-THREE-BODY-CUTOVER.patch',full)
fixture=(D/'fixture/actual_bodies.rs').read_text();need(fixture.count(old1)==fixture.count(old2)==2,'raw/pure shared loop pairs')
text(R/'fixture/actual_bodies.rs',fixture.replace(old1,new1).replace(old2,new2))
shutil.copyfile(D/'fixture/actual_abi.rs',R/'fixture/actual_abi.rs')
# Retain all 77 real current inputs exactly. No original snapshot is modified.
rust=json.loads((P/'EXACT-CURRENT78-PRODUCTION-RUST.NOT-EXECUTED.json').read_bytes())
for key,row in rust['source_inputs'].items():
 old=Path(row['private']['path']);need(ref(old)['sha256']==row['private']['sha256'],'retained source '+key)
 for authority in ['canonical','accepted_actual_union_source']:
  need(ref(Path(row[authority]['path']))['sha256']==row[authority]['sha256'],'unchanged authority '+key)
 dest=R/'source'/key;dest.parent.mkdir(parents=True,exist_ok=True)
 if key=='kernel/rust/x86_cpu_helpers.rs':dest.write_text(corrected)
 else:shutil.copyfile(old,dest)
 row['private']=ref(dest)
rust['source_identity_rows']=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in sorted(rust['source_inputs'].items())]
rust['source_identity']=sha(json.dumps(rust['source_identity_rows'],separators=(',',':'),ensure_ascii=True).encode())
rust['argv']=[x.replace(str(P/'output-1'),str(R/'output-1')).replace(str(P/'source'),str(R/'source')) for x in rust['argv']]
rust['status']='BOUNDED_VOLATILE_COPY_CORRECTION_CURRENT78_NOT_EXECUTED'
rust['actual_leaf']=None;rust['bounded_correction_to_failed_actual']=ref(P/'actual-production-1/FIRST-UNEXPECTED-READY.json')
write(R/'EXACT-CURRENT78-PRODUCTION-RUST.NOT-EXECUTED.json',rust)
oldplan=json.loads((P/'PRODUCTION-CONSUMER-READY.NOT-GRANTED.json').read_bytes())
plan=copy.deepcopy(oldplan)
plan.update(status='READY_SOURCE_ONLY_BOUNDED_VOLATILE_COPY_LEAF5_PRODUCTION7_NO_GRANT',Rust_recipe=ref(R/'EXACT-CURRENT78-PRODUCTION-RUST.NOT-EXECUTED.json'),source_identity=rust['source_identity'],fresh_output_directory=str(R/'output-1'),fresh_leaf_output_directory=str(R/'leaf-output-1'),actual_current_C_source=ref(R/'candidate/arch/x86_64/kernel/cpu.c'),actual_production_result=None,compiler_jobs=2,test_jobs=1,CPU_slots_held=0)
leafplan=json.loads((D/'PROPOSED-ORDINARY-BATCH-RECIPE.json').read_bytes())
leaf=[]
for idx in [0,5,6,7,8]:
 c=copy.deepcopy(leafplan['commands'][idx]);c['argv']=[x.replace(str(D/'output-1/actual_bodies.o'),str(R/'leaf-output-1/actual_bodies.o')).replace(str(D/'output-1/fixture'),str(R/'leaf-output-1/fixture')).replace(str(D/'fixture/actual_bodies.rs'),str(R/'fixture/actual_bodies.rs')) for x in c['argv']];c['label']='leaf-'+c['label'];c['cwd']=str(R);leaf.append(c)
production=copy.deepcopy(oldplan['commands'])
for c in production:
 c['argv']=[x.replace(str(P/'output-1'),str(R/'output-1')).replace(str(P/'source'),str(R/'source')) for x in c['argv']];c['cwd']=str(R)
q=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/production-consumer-preparation-1/REUSED-WHOLE-GCC9-TU-REAL-ABI.NOT-GRANTED.json')
provider=json.loads(q.read_bytes());pr=provider['retained_C_object'];production[4]['argv'].insert(3,pr['path'])
plan['commands']=leaf+production;plan['command_count']=12;plan['production_command_count']=7;plan['leaf_command_count']=5
plan['changed_source_leaf_expected_stdout']=leafplan['expected_fixture_stdout'];plan['expected_unchanged_8000_counts']={'pureNMI':6528,'stackNoWalk':1360,'interruptExit':112,'classifier':136,'ABI':19}
leafjoin=json.loads((D/'actual-retained-continuation-1/ACTUAL-WHOLE-JOIN.json').read_bytes())
plan['retained_leaf_C_objects_not_rehashed']=[leafjoin['durable_objects_hashed_once'][key] for key in ['original_bodies.o','nmi_pure_fixture.o','real-header-ABI.o','batch_fixture.o']]
plan['genuine_check_signal_provider']={'authority':ref(q),'object_NOT_rehashed':pr,'actual_C_source':provider['source'],'canonical_current_C_source':ref(canonical/'kernel/syscall.c'),'actual_root_union_partial_NM':ref(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-1/actual-six-C-partial-1/2/stdout')),'prototype':'void check_signal(unsigned long, void *, int)','partial_requirement':'exactly one global T check_signal; no U check_signal; genuine retained complete selected syscall C provider, no new C or stub'}
plan['preserved_actual_C_providers']=list(dict.fromkeys(oldplan['preserved_actual_C_providers']+['check_signal']))
plan['allocated_memmove_oracle']=ref(R/'allocated_memmove_oracle.py')
plan['exact_symbol_oracle']=oldplan['exact_symbol_oracle']
plan['expected_partial']={'objects':['actual complete GCC9 CPU','actual complete GCC9 syscall check_signal provider','new corrected production78 Rust'],'newentry_U_absent':['__print_stack','mod_nmi_ctx','interrupt_exit'],'check_signal':'one genuine T/no U','memmove':'no U/no allocated references; no provider added'}
plan['failure_history']={'original_preflight':'89ea retained; positive PF_KTHREAD+PPid2 exemption unchanged','original_emit_parser':'0460/e40 retained; firsthashNOW f155 honest','actual_production_U_failure':ref(P/'actual-production-1/FIRST-UNEXPECTED-READY.json'),'independent_correction':ref(P/'actual-production-1/INDEPENDENT-MEMMOVE-OBSERVATION-CORRECTION-1.json'),'bounded_product_correction_count':1,'first_unexpected_future_failure':'STOP expert; no automatic correction or family reset'}
plan['proof_limits']=['Changed-source controlled full8000 only; raw NMI flags/IRQenable/IRET/kernel stack/native NOTEXECUTED','Inherited NULL freeze remains targeted HOLD, no semantics repair or callee guard','Full current production Rust and retained GCC9 ABI/C consumers/partial only; no GCC14/default kernel/native proof','GPE/int3/debug sources excluded/UNTESTED']
plan['correction_inputs']={str(p.relative_to(R)):ref(p) for p in [R/'candidate/kernel/rust/x86_cpu_helpers.rs',R/'candidate/arch/x86_64/kernel/cpu.c',R/'fixture/actual_bodies.rs',R/'fixture/actual_abi.rs',R/'VOLATILE-ONLY-FROM-FAILED-a323.patch',R/'COHERENT-THREE-BODY-CUTOVER.patch',R/'allocated_memmove_oracle.py']}
write(R/'EXECUTABLE-READY.NOT-GRANTED.json',plan)
# Source-only finite change proof. No object was opened or hashed.
write(R/'SOURCE-CORRECTION-IDENTITY.json',{'scope':SCOPE,'status':'SOURCE_PREPARED_NOT_COMPILED_OR_TESTED','failed_a323':ref(product),'corrected_product':ref(R/'candidate/kernel/rust/x86_cpu_helpers.rs'),'C_unchanged':ref(R/'candidate/arch/x86_64/kernel/cpu.c'),'source_identity':rust['source_identity'],'77_others_unchanged':True,'only_product_changes':2,'final_five_stores_ABI_Cfallback_NULL_qualification':'byte-preserved','leaf_raw_and_pure_copy_operations':'same volatile primitive replacement; all original oracles unchanged','ready':ref(R/'EXECUTABLE-READY.NOT-GRANTED.json'),'no_object_read_hash_compile_or_test':True,'CPU_slot_held':False,'engineering_percentage':None})
print(json.dumps({'corrected':ref(R/'candidate/kernel/rust/x86_cpu_helpers.rs'),'ready':ref(R/'EXECUTABLE-READY.NOT-GRANTED.json'),'source_identity':rust['source_identity']}))
