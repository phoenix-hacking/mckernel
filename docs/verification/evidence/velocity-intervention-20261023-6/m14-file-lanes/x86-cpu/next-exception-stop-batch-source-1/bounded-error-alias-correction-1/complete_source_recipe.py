"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only merge/recipe preparation; no tool subprocess, compiler or runtime.
"""
from pathlib import Path
import hashlib,json,difflib,shutil,re,ast
R=Path(__file__).resolve().parent;L=R.parent;D=L/'next-body-batch-source-1';V=D/'bounded-volatile-copy-correction-1'
SCOPE=__doc__.splitlines()[0]
def need(b,m):
 if not b:raise ValueError(m)
def ref(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def text(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  need(p.read_text()==s,'preserve identical prior prepared bytes '+str(p));return
 with p.open('x') as f:f.write(s)
def write(p,d):text(p,json.dumps(d,sort_keys=True,indent=2)+'\n')
baseC=V/'candidate/arch/x86_64/kernel/cpu.c';baseR=V/'candidate/kernel/rust/x86_cpu_helpers.rs'
need(ref(baseC)['sha256']=='5574c151cef8d26fa14e3eac72d54b55703be153e4f147f831c5a9e9b63c70bc','accepted unchanged C5574')
need(ref(baseR)['sha256']=='a44a391c7eb461b82cb181089941f52e8845ae90b04d34319aff6437deebb3e4','accepted volatile Rust')
c=baseC.read_text();rust=baseR.read_text();decls='';rustbodies='';reuse={}
for short,name in [('gpe','next-gpe-handler-source-only-1'),('int3','next-int3-handler-source-only-1'),('debug','next-debug-handler-source-only-1')]:
 p=L/name;old=(p/'ORIGINAL-C-BODY.inc').read_text().rstrip();need(c.count(old)==1,'one live original body '+short)
 gate=(p/'DECLARATIVE-C-CONFIG-DATA.inc').read_text() if short!='gpe' else ''
 c=c.replace(old,'#ifdef MCKERNEL_RUST_X86_CPU_HELPERS\n'+gate+'void '+short+'_handler(struct x86_user_context *regs);\n#else\n'+old+'\n#endif')
 declarations=(p/'ACTUAL-RUST-PROVIDER-DECLARATIONS.inc').read_text();body=(p/'ACTUAL-RUST-BODY.rs').read_text()
 decls+=declarations;rustbodies+='\n'+body
 text(R/('original-'+short+'.inc'),(p/'ORIGINAL-C-BODY.inc').read_text())
 if short=='debug':text(R/'original-debug-controlled.inc',(p/'fixture-source-fragment/ORIGINAL-C-CONTROLLED-DR6.inc').read_text())
 text(R/(short+'-actual-Rust-ABI.inc'),(p/'fixture-source-fragment/actual-Rust-ABI.inc').read_text())
 text(R/(short+'-real-header-ABI.c.inc'),(p/'fixture-source-fragment/real-header-ABI.c').read_text())
 reuse[short]={'original_C':ref(p/'ORIGINAL-C-BODY.inc'),'Rust_body':ref(p/'ACTUAL-RUST-BODY.rs'),'declarations':ref(p/'ACTUAL-RUST-PROVIDER-DECLARATIONS.inc'),'source_handoff':ref(p/'SOURCE-IMPLEMENTATION-HANDOFF.json')}
p=L/'next-arch-cpu-stop-source-only-1';old=(p/'ORIGINAL-C-BODY.inc').read_text().rstrip();need(c.count(old)==1,'one live stop body')
c=c.replace(old,'#ifdef MCKERNEL_RUST_X86_CPU_HELPERS\nvoid arch_cpu_stop(void);\n#else\n'+old+'\n#endif')
text(R/'original-stop.inc',(p/'ORIGINAL-C-BODY.inc').read_text());stop=(p/'ACTUAL-RUST-BODY.inc').read_text();rustbodies+='\n'+stop
reuse['stop']={'source_handoff':ref(p/'SOURCE-HANDOFF.json'),'actual_Rust':ref(p/'ACTUAL-RUST-BODY.inc'),'original_C':ref(p/'ORIGINAL-C-BODY.inc')}
# The aliases are disjoint, and their actual existing provider link names match.
aliases=re.findall(r'\b(?:fn|static)\s+(x86_\w+|X86_\w+)',decls);need(len(aliases)==len(set(aliases)),'no overlapping extern aliases')
for a in aliases:need(not re.search(r'\b(?:fn|static)\s+'+re.escape(a)+r'\b',rust),'no canonical alias collision '+a)
merged=rust+'\nunsafe extern "C" {\n'+decls+'}\n'+rustbodies
for name in ['gpe_handler','int3_handler','debug_handler','arch_cpu_stop']:need(merged.count('pub unsafe extern "C" fn '+name+'(')==1,'unique selected export '+name)
text(R/'candidate/arch/x86_64/kernel/cpu.c',c);text(R/'candidate/kernel/rust/x86_cpu_helpers.rs',merged)
patch=''
for key,before,after in [('arch/x86_64/kernel/cpu.c',baseC.read_text(),c),('kernel/rust/x86_cpu_helpers.rs',rust,merged)]:patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+key,tofile='b/'+key))
text(R/'COHERENT-FOUR-BODY-CUTOVER.patch',patch)
# Reuse actual abi.rs and exact existing register-reader body; privileged export
# is compiled but ONLY actual_debug_controlled is called by the hosted fixture.
text(R/'actual_abi.rs',(D/'fixture/actual_abi.rs').read_text())
a=rust.index('trait DebugRegisterReader {');b=rust.index('\n#[inline(always)]\nunsafe fn save_debugreg_body',a);reader=rust[a:b]
leaf='#![no_std]\nuse core::ffi::c_void;\n#[path="actual_abi.rs"] mod abi;\nuse abi::{CInt,CULong,X86UserContext};\ntype CUInt=u32;\nunsafe extern "C" {\n fn kprintf(format:*const i8,...)->CInt;\n fn cpu_halt();\n'+decls+'}\n'+reader+'\n'+rustbodies
leaf+='\n'+(L/'next-debug-handler-source-only-1/fixture-source-fragment/CONTROLLED-RUST-READER.inc.rs').read_text()
for n in ['gpe','int3','debug']:leaf+='\ninclude!("'+n+'-actual-Rust-ABI.inc");\n'
text(R/'actual_bodies.rs',leaf)
abi='/* '+SCOPE+' */\n'
for n in ['gpe','int3','debug']:abi+='\n#include "'+n+'-real-header-ABI.c.inc"\n'
abi+='\nextern void arch_cpu_stop(void);\ntypedef void(*StopEntry)(void);\n_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_cpu_stop),StopEntry),"actual existing panic caller void(void) ABI");\n'
text(R/'real-header-ABI.c',abi)
# Preserve exact accepted header witness closure, including kmsg.h. No new
# generated layout, alternate header or copied historical evidence.
oldplan=json.loads((D/'PROPOSED-ORDINARY-BATCH-RECIPE.json').read_text());headers={}
for path,row in oldplan['header_closure'].items():
 src=Path(path);need(ref(src)['sha256']==row['sha256'],'accepted header bytes '+path)
 if not src.is_relative_to(D/'source'):
  headers[str(src)]=ref(src);continue
 rel=src.relative_to(D/'source');dst=R/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():need(dst.read_bytes()==src.read_bytes(),'preserve identical prepared header')
 else:shutil.copyfile(src,dst)
 headers[str(dst)]=ref(dst)
# GCC's actual flags and generated headers stay exactly those of accepted witness.
abi_argv=[]
for x in oldplan['commands'][3]['argv']:
 x=x.replace(str(D/'source'),str(R/'source')).replace(str(D/'fixture/real-header-ABI.c'),str(R/'real-header-ABI.c')).replace(str(D/'output-1/real-header-ABI.o'),str(R/'output-1/real-header-ABI.o'));abi_argv.append(x)
gcc=oldplan['commands'][1]['argv'][0];rustc=oldplan['commands'][0]['argv'][0]
inc=['-I'+str(R/'source/arch/x86_64/kernel/include'),'-I'+str(R/'source/lib/include')]
# recorder uses all real headers; reuse real-header witness include/define flags
# while keeping hosted code model and libc available (no target-kernel execution).
pre=abi_argv[1:abi_argv.index('-g')];pre=[x for x in pre if not x.startswith('-DKERNEL_RAM_VADDR') and not x.startswith('-DMAP_KERNEL_START')]
commands=[]
def cmd(label,argv):commands.append({'label':label,'argv':argv,'cwd':str(R),'purpose':SCOPE+' '+label+'; compile or controlled hosted fixture only.'})
O=R/'output-1'
cmd('00-actual-Rust-four-body-compile-only',[rustc,'--crate-name','m14_cpu_exception_stop','--crate-type','lib','--edition=2021','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','no-redzone=yes','--emit=obj='+str(O/'actual_bodies.o'),str(R/'actual_bodies.rs')])
cmd('01-real-header-ABI',abi_argv)
for variant,flags in [('undefined',[]),('defined-zero',['-DDEBUG_PRINT_CPU=0']),('defined-one',['-DDEBUG_PRINT_CPU=1'])]:
 cmd('02-'+variant+'-actual-original-and-recorders',[gcc,'-mno-red-zone','-std=gnu11','-O2','-fno-builtin','-Werror=incompatible-pointer-types']+pre+flags+['-c',str(R/'fixture.c'),'-o',str(O/('recorder-'+variant+'.o'))])
 cmd('03-'+variant+'-host-link',[gcc,str(O/('recorder-'+variant+'.o')),str(O/'actual_bodies.o'),str(O/'real-header-ABI.o'),'-o',str(O/('fixture-'+variant))])
 cmd('04-'+variant+'-controlled-run',[str(O/('fixture-'+variant))])
cmd('05-actual-Rust-symbols',['/usr/bin/nm','-g',str(O/'actual_bodies.o')])
cmd('06-actual-Rust-ELF',['/usr/bin/readelf','--wide','--syms',str(O/'actual_bodies.o')])
# Whole selected/fallback C consumers use same current accepted flags, replacing
# only the private source and output. No production/nightly fullcrate in this queue.
for idx,label in [(9,'07-selected-whole-CPU'),(12,'08-fallback-whole-CPU')]:
 argv=[x.replace(str(D/'source'),str(R/'source')).replace(str(R/'source/arch/x86_64/kernel/cpu.c'),str(R/'candidate/arch/x86_64/kernel/cpu.c')).replace(str(D/'output-1'),str(O)) for x in oldplan['commands'][idx]['argv']]
 cmd(label,argv)
for name in ['selected-cpu','fallback-cpu']:
 cmd('09-'+name+'-ownership',['/usr/bin/nm','-a','-S',str(O/(name+'.o'))])
cmd('10-selected-CPU-relocations',['/usr/bin/readelf','-rW',str(O/'selected-cpu.o')])
cmd('11-partial-link',['/usr/bin/ld','-r',str(O/'selected-cpu.o'),str(O/'actual_bodies.o'),'-o',str(O/'selected-leaf-partial.o')])
cmd('12-partial-ownership',['/usr/bin/nm','-a','-S',str(O/'selected-leaf-partial.o')])
# Remaining partial U are explicit retained providers, never proof whole kernel.
profile=oldplan['profile'];tools={}
for executable in set(x['argv'][0] for x in commands if x['argv'][0].startswith('/') and not x['argv'][0].startswith(str(O))):tools[executable]=ref(Path(executable))
sourcefiles={str(p.relative_to(R)):ref(p) for p in R.rglob('*') if p.is_file() and p.name!='prepare_source_only.py'}
observed={'C':ref(Path('/home/holden/mckernel/arch/x86_64/kernel/cpu.c')),'Rust':ref(Path('/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs'))}
plan={'scope':SCOPE,'status':'EXECUTABLE_SOURCE_BATCH_PREPARED_NO_GRANT_NO_CPU_RESERVATION','base_accepted_volatile':{'C':ref(baseC),'Rust':ref(baseR),'actual':ref(V/'ACTUAL-COMPACT-HANDOFF.json')},'current_canonical_observed_ONLY':observed,'preflight_required_canonical':{'C':ref(baseC)['sha256'],'Rust':ref(baseR)['sha256']},'if_canonical_not_integrated':'No child. Root must confirm exact accepted volatile successor; do not silently refresh or invent integration.','reuse_original_fragments':reuse,'new_C_runtime_functionality':False,'declarative_remaining_C_debt':['x86_int3_debug_print_enabled R4','x86_debug_handler_debug_print_enabled R4'],'candidate':{'C':ref(R/'candidate/arch/x86_64/kernel/cpu.c'),'Rust':ref(R/'candidate/kernel/rust/x86_cpu_helpers.rs')},'patch':ref(R/'COHERENT-FOUR-BODY-CUTOVER.patch'),'profile':profile,'tools':tools,'source_inputs':sourcefiles,'header_closure':headers,'commands':commands,'command_count':len(commands),'fresh_output_directory':str(O),'variants':{'undefined':0,'defined-zero':1,'defined-one':1},'expected_stdout':{v:['M14 CPU exception/stop batch: gate='+str(g)+' GPE=288 INT3=576 DEBUG=672 STOP=5 ABI=34 failures=0','NOTEXECUTED: rawDR6 HLT exception IRQ IRET NULLfreeze native'] for v,g in [('undefined',0),('defined-zero',1),('defined-one',1)]},'planned_pairs_per_variant':1541,'planned_total_pairs_not_accepted':4623,'planned_real_ABI_words':34,'oracles':{'leaf_T':['gpe_handler','int3_handler','debug_handler','actual_debug_controlled','arch_cpu_stop'],'selected_C_T_absent':['gpe_handler','int3_handler','debug_handler','arch_cpu_stop'],'fallback_C_T_present':['gpe_handler','int3_handler','debug_handler','arch_cpu_stop'],'default_assembly_caller_relocations':'actual selected C includes declarations; assembly entry producer remains separate whole-image/defaultlink proof','partial_T_once':['gpe_handler','int3_handler','debug_handler','arch_cpu_stop'],'partial_U_absent':['gpe_handler','int3_handler','debug_handler','arch_cpu_stop'],'config_datums':'exactly one R4 each in selected C, none in fallback; undefined0/definedincludingzero1 hosted variants','controlled_debug_reader':'exact existing actual generic body; only controlled reader executes, raw export never called','recorded_terminal':'GPE panic/stop _exit in isolated child, no longjmp/unwind; all children joined exactexit0/EOF','snapshot_and_independent_oracle':'actual C and Rust tape/full initialized real context each equal independent expected state; all SigInfo128 bytes initialized at signal callback'},'headroom_before_future_launch':oldplan['headroom_before_future_release'],'capture_release':'existing990807 dict API, explicitCWD, TERM/INT/ALRM, OS+Ruststack2M, durable object SHA once before observers, directjoined/groupgone/closed before CPU6release','actual_result':None,'compiler_jobs':0,'CPU_reserved':False,'failure_family':'new coherent four-body first candidate not executed; historical volatile/NULL/preflight/observer families preserved separately; first unexpected STOP root','default_GCC14_link_native':'OPEN','inherited_NULL_freeze_HOLD':'unchanged, no fabricated frame/guard/oracle relaxation','engineering_percentage':None,'difficulty':'bounded leaf orchestration and actual enum/SigInfo ABI; debug privileged instruction and exception/native integration remain harder separate work'}
write(R/'EXECUTABLE-READY.NOT-GRANTED.json',plan)
write(R/'SOURCE-HANDOFF.json',{'scope':SCOPE,'status':'ONE_FOUR_BODY_SOURCE_FIXTURE_QUEUE_ONLY_NO_EXECUTION','ready':ref(R/'EXECUTABLE-READY.NOT-GRANTED.json'),'candidate':plan['candidate'],'patch':plan['patch'],'held_input':'observed canonical c779/9891 pending actual accepted volatile C5574/Rusta44a confirmation','residual':'configuration datums and existing timing/signal/interrupt providers remain explicit C or mixed ownership debt; exception/DR6/HLT/native not run','reuse':'existing actual Rust context/SignalInfo/DebugRegisterReader/cpu_halt and prior actual header profile/fragments','next_grant':'one ordinary CPU6 job for declared commands after root admission; no second queue','defaultlink_native':'OPEN','engineering_percentage':None})
M=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu')/R.name
for p in R.rglob('*'):
 if p.is_file():q=M/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
print(json.dumps({'ready':ref(R/'EXECUTABLE-READY.NOT-GRANTED.json'),'handoff':ref(R/'SOURCE-HANDOFF.json'),'commands':len(commands),'candidate':plan['candidate'],'source_only':True}))
