"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source-only fixture preparation; no compiler/test."""
from pathlib import Path
import json,hashlib,shutil,ast
F=Path(__file__).resolve().parent;R=F.parent;L=R.parents[1]
E=L/'next-exception-stop-batch-source-1/bounded-error-alias-correction-1/expert-host-memory-adapter-1'
plan0=json.loads((E/'EXACT-REMAINING18.NOT-GRANTED.CANONICAL-BOUND.json').read_bytes())
def ref(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
for name in ['FUTURE-RECORDED-BOUNDARIES.c.inc','FUTURE-C-TYPE-ABI.c.inc','FUTURE-RUST-TYPE-ABI.inc','FUTURE-PRODUCTION-ABI.c.inc','ACTUAL-CPU-CONSTANTS.inc','ACTUAL-C-DECLARATIVE-DATA.inc','ORIGINAL-C-BODY.inc']:
 shutil.copyfile(R/name,F/name)
oldABI=L/'next-body-batch-source-1/fixture/actual_abi.rs';shutil.copyfile(oldABI,F/'actual_abi.rs')
leaf='#![no_std]\n#[path="actual_abi.rs"] mod abi;\nuse abi::{CInt,CULong};\ntype CUInt=u32;\nunsafe extern "C" {\n fn arch_delay(us:CInt);\n'+(R/'ACTUAL-RUST-DECLARATIONS.inc').read_text()+'}\n'+(R/'ACTUAL-RUST-BODY.rs').read_text()+'\ninclude!("FUTURE-RUST-TYPE-ABI.inc");\n'
(F/'actual_bodies.rs').write_text(leaf)
(F/'selected-real-ABI.c').write_text('/* '+plan0['scope']+' Compile only; never execute this kernel TU. */\n#include "'+str(R/'candidate/arch/x86_64/kernel/cpu.c')+'"\n#include "FUTURE-C-TYPE-ABI.c.inc"\n')
O=F/'output-1';commands=[]
def cmd(label,argv):commands.append({'label':label,'argv':argv,'cwd':str(F),'purpose':plan0['scope']+' '+label+'; only controlled recorder run; kernel/privileged hardware instructions never execute.'})
rustc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';gcc='/usr/bin/gcc-9'
cmd('00-actual-Rust-wakeup-body',[rustc,'--crate-name','m14_x86_wakeup','--crate-type','lib','--edition=2021','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','no-redzone=yes','--emit=obj='+str(O/'actual_bodies.o'),str(F/'actual_bodies.rs')])
cmd('01-original-C-controlled-recorders',[gcc,'-std=gnu11','-O2','-fno-builtin','-mno-red-zone','-Werror=incompatible-pointer-types','-c',str(F/'fixture.c'),'-o',str(O/'recorders.o')])
cmd('02-host-controlled-link',[gcc,str(O/'recorders.o'),str(O/'actual_bodies.o'),'-o',str(O/'fixture')])
cmd('03-controlled-wakeup-run',[str(O/'fixture')])
selected=list(plan0['commands'][13]['argv']);selected[selected.index('-c')+1]=str(F/'selected-real-ABI.c');selected[selected.index('-o')+1]=str(O/'selected-cpu-ABI.o');cmd('04-real-selected-complete-CPU-and-ABI',selected)
fallback=list(plan0['commands'][14]['argv']);fallback[fallback.index('-c')+1]=str(R/'candidate/arch/x86_64/kernel/cpu.c');fallback[fallback.index('-o')+1]=str(O/'fallback-cpu.o');cmd('05-literal-fallback-complete-CPU',fallback)
pre=list(fallback);at=pre.index('-c');pre[at:at+2]=['-E','-P',str(R/'candidate/arch/x86_64/kernel/cpu.c')];at=pre.index('-o');del pre[at:at+2];cmd('06-fallback-preprocess',pre)
cmd('07-Rust-NM',['/usr/bin/nm','-g','-S',str(O/'actual_bodies.o')])
cmd('08-selected-CPU-NM',['/usr/bin/nm','-a','-S',str(O/'selected-cpu-ABI.o')])
cmd('09-selected-CPU-RELA',['/usr/bin/readelf','-rW',str(O/'selected-cpu-ABI.o')])
cmd('10-selected-CPU-leaf-partial',['/usr/bin/ld','-r',str(O/'selected-cpu-ABI.o'),str(O/'actual_bodies.o'),'-o',str(O/'selected-partial.o')])
cmd('11-partial-NM',['/usr/bin/nm','-g','-S',str(O/'selected-partial.o')])
for p in [F/'elf_observer.py',F/'observe_results.py']:ast.parse(p.read_text())
root=R.parents[3]/'root-union-preparation-2/CANONICAL-INTEGRATION.json'
# Resolve authority from the current source handoff rather than guessing roots.
source=json.loads((R/'CURRENT-SOURCE-HANDOFF.json').read_bytes());root=Path(source['root_actual_integration']['path'])
canon=source['actual_two_preimages']
for row in canon.values():assert ref(Path(row['path']))['sha256']==row['sha256']
data=['x86_wakeup_lapic_write_slot','x86_wakeup_lapic_read_slot','x86_wakeup_wait_slot','x86_wakeup_first_page_slot','x86_wakeup_boot_status_slot','x86_wakeup_constants']
sources={str(p.relative_to(F)):ref(p) for p in F.rglob('*') if p.is_file() and p.name!='prepare_source_only.py'}
sources['actual_product_C']=ref(R/'candidate/arch/x86_64/kernel/cpu.c');sources['actual_product_Rust']=ref(R/'candidate/kernel/rust/x86_cpu_helpers.rs')
p={'scope':plan0['scope'],'status':'FIRST_WAKEUP_CONTROLLED_LEAF_EXECUTABLE_READY_NOT_GRANTED','source_parent':ref(R/'CURRENT-SOURCE-HANDOFF.json'),'candidate':source['candidate'],'commands':commands,'command_count':12,'profile':plan0['profile'],'fresh_output_directory':str(O),'source_inputs':sources,'header_closure':plan0['header_closure'],'tools':plan0['tools'],'retained_observer':ref(F/'observe_results.py'),'ELF_observer':ref(F/'elf_observer.py'),'operative_precondition':{'original_successor':ref(root),'canonical_base_required':canon,'private_parent_required':{'C':sources['actual_product_C'],'Rust':sources['actual_product_Rust'],'source_handoff':ref(R/'CURRENT-SOURCE-HANDOFF.json')},'candidate_required':source['candidate'],'canonical_equal_private_required':False},'expected_stdout':['M14 wakeup C/Rust: pairs=18000 ABI=22 failures=0','NOTEXECUTED: warmReset MMIO IPI delayISA APstartup NULLfreeze native'],'planned_pairs_NOT_ACCEPTANCE':18000,'planned_type_ABI_words':22,'declarative_data_symbols':data,'declarative_C_data_qualification':'five const descriptor pointers and one uint[5] originalmacro array explicit Cdebt; record actual allocated section flags; final linked readonly treatment OPEN','production_consumer':'actual existing selected C x86_wakeup_bridge emits allocated __x86_wakeup import after replacement; original C helper was inlined, no invented historical local T requirement','fallback_proof':'literal fallback preprocess retains original two static bodies; compiler may inline them, do not require nonexistent t symbols','partial':'actual new Rust entry T once/no U and actual C descriptor/IPI data resolved; existing kernel callback imports remain explicit debt; no recorder C object in production partial','known_UNEXECUTED':['native warm-reset/MMIO/IPI/actualdelay/AP startup','inherited NULLfreeze','defaultGCC14wholekernel/image/native'],'source_correction_family':'first wakeup candidate not compiled; previous exception E0609/HOST7fcb closed via differentexpertactualPASS and preserved separately; firstunexpectedSTOProot/no automatic retry','actual_result':None,'compiler_jobs':0,'CPU_reserved':False,'no_perlane_production_crate':True,'engineering_percentage':None}
write(F/'EXECUTABLE-READY.NOT-GRANTED.json',p)
print(json.dumps({'ready':ref(F/'EXECUTABLE-READY.NOT-GRANTED.json'),'commands':len(commands),'planned_pairs':18000,'source_only':True}))
