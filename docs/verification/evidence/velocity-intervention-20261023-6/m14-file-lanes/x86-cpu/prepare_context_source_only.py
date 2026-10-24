"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source only, no compiler/test."""
from pathlib import Path
import re,json,hashlib,difflib,shutil
ROOT=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;F=P/'fixture';F.mkdir();O=P/'output-1'
BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-cpu-log-next')
def pin(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def write(p,s):
 with p.open('x') as f:f.write(s)
def function(text,name,prefix):
 start=text.index(prefix+name+'(');brace=text.index('{',start);depth=1;i=brace+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
C=BASE/'candidate/arch/x86_64/kernel/cpu.c';R=BASE/'candidate/kernel/rust/x86_cpu_helpers.rs';cs=C.read_text();rs=R.read_text()
assert pin(C)['sha256']=='2d29bca555936a213f0a7296a302ec57b55c575536c33a58285b07b203390eca'
assert pin(R)['sha256']=='26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9'
original=function(cs,'x86_context_line_log_bridge','void ')
assert cs.count('void x86_context_line_log_bridge(')==1 and 'pub unsafe extern "C" fn x86_context_line_log_bridge(' not in rs
declaration='void x86_context_line_log_bridge(int event, unsigned long a,\n\t\tunsigned long b, unsigned long c, unsigned long d);'
# Existing #ifdef includes unchanged lock/unlock providers above this body.
# Keep it selected for those providers plus extern; original complete body is
# the new #else branch, followed by the existing #endif at its original site.
newC=cs.replace(original,declaration+'\n#else\n'+original,1)
rustdecl='    fn x86_context_line_log_bridge(event: CInt, a: CULong, b: CULong, c: CULong, d: CULong);\n'
assert rs.count(rustdecl)==1
newR=rs.replace(rustdecl,'',1)
kdecl='    fn kprintf(format: *const i8, ...) -> CInt;\n';assert newR.count(kdecl)==1 and 'fn __kprintf(' not in newR
newR=newR.replace(kdecl,kdecl+'    fn __kprintf(format: *const i8, ...) -> CInt;\n',1)
parts=re.findall(r'\tcase (\d+):\n(.*?)\t\tbreak;',original,re.S);assert [int(e) for e,b in parts]==[1,2,3,4,5,6,20,21,22]
match=[]
for event,body in parts:
 calls=re.findall(r'(__kprintf|kprintf)\("((?:\\.|[^"\\])*)"(?:,\s*([abcd](?:,\s*[abcd])*))?\);',body)
 assert len(calls)==(2 if int(event) in range(2,7) else 1),(event,body)
 lines=['        '+event+' => unsafe {']
 for provider,fmt,args in calls:
  assert provider==('__kprintf' if int(event)<=6 else 'kprintf')
  actualargs=(', '+', '.join(args.replace(' ','').split(','))) if args else ''
  lines.append('            '+provider+'(b"'+fmt+r'\0".as_ptr().cast()'+actualargs+');')
 lines.append('        },');match.extend(lines)
rust='''/// Preserve complete context diagnostics using the existing Rust print providers.
/// The caller owns any outer print lock. Events 1..6 use __kprintf without
/// acquiring that lock again; 20..22 retain the original kprintf calls. All
/// arguments are integer values, no context pointer or callback is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_context_line_log_bridge(
    event: CInt, a: CULong, b: CULong, c: CULong, d: CULong,
) {
    match event {
'''+ '\n'.join(match)+'''
        _ => {},
    }
}
'''
newR+='\n'+rust
for key,text in [('arch/x86_64/kernel/cpu.c',newC),('kernel/rust/x86_cpu_helpers.rs',newR)]:
 p=P/'candidate'/key;p.parent.mkdir(parents=True,exist_ok=True);write(p,text)
patch=''.join(difflib.unified_diff(cs.splitlines(True),newC.splitlines(True),fromfile='a/arch/x86_64/kernel/cpu.c',tofile='b/arch/x86_64/kernel/cpu.c'))+''.join(difflib.unified_diff(rs.splitlines(True),newR.splitlines(True),fromfile='a/kernel/rust/x86_cpu_helpers.rs',tofile='b/kernel/rust/x86_cpu_helpers.rs'))
write(P/'PRIVATE-COMPLETE-CONTEXT-LOGGER.patch',patch)
write(F/'original-body.inc',original.replace('x86_context_line_log_bridge','original_context_log',1))
write(F/'selected-body.inc','#ifdef MCKERNEL_RUST_X86_CPU_HELPERS\n'+declaration+'\n#else\n'+original+'\n#endif\n')
shutil.copy2(ROOT/'kernel/rust/abi.rs',F/'actual_abi.rs')
userbody=function(rs,'x86_print_user_context_body_result','pub unsafe extern "C" fn ')
intbody=function(rs,'x86_arch_show_interrupt_context_body_result','pub unsafe extern "C" fn ')
fixtureRust='''#![no_std]
use abi::{CInt,CULong,X86UserContext,X86BasicRegs};
#[path="actual_abi.rs"] mod abi;
type X86ContextLogFn=unsafe extern "C" fn(CInt,CULong,CULong,CULong,CULong);
type X86KprintfLockFn=unsafe extern "C" fn()->CULong;
type X86KprintfUnlockFn=unsafe extern "C" fn(CULong);
const EINVAL:CInt=22;
extern "C" {
 fn kprintf(format:*const i8,...) -> CInt;
 fn __kprintf(format:*const i8,...) -> CInt;
}
'''+rust+'\n#[no_mangle]\n'+userbody+'\n#[no_mangle]\n'+intbody+r'''
// Fixture-only construction from real ABI types, not a model of their layout.
#[no_mangle]
pub unsafe extern "C" fn fixture_run_context(
    which:CInt, values:*const CULong, log:Option<X86ContextLogFn>,
    lock:Option<X86KprintfLockFn>, unlock:Option<X86KprintfUnlockFn>,
)->CInt {
 let mut ctx:X86UserContext=unsafe{core::mem::zeroed()};
 macro_rules! v {($n:expr)=>{unsafe{*values.add($n)}}}
 ctx.gpr=X86BasicRegs{
 r15:v!(0),r14:v!(1),r13:v!(2),r12:v!(3),rbp:v!(4),rbx:v!(5),
 r11:v!(6),r10:v!(7),r9:v!(8),r8:v!(9),rax:v!(10),rcx:v!(11),
 rdx:v!(12),rsi:v!(13),rdi:v!(14),orig_rax:v!(15),rip:v!(16),
 cs:v!(17),rflags:v!(18),rsp:v!(19),ss:v!(20)};
 if which==0 {unsafe{x86_print_user_context_body_result(&ctx,log)}}
 else {unsafe{x86_arch_show_interrupt_context_body_result(&ctx,lock,unlock,log)}}
}
'''
write(F/'actual_context_logger.rs',fixtureRust)
write(F/'compare_context_tapes.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdarg.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
typedef void(*Log)(int,unsigned long,unsigned long,unsigned long,unsigned long);
struct event{unsigned provider,depth,nargs;unsigned long args[4];char format[96];};
struct trace{unsigned n;struct event events[16];};
static struct trace *active;static unsigned depth,eval[5];static int return_value,mode;static unsigned long lock_flags;
static void need(int b,const char*s){if(!b){fprintf(stderr,"FAIL %s\n",s);exit(1);}}
static struct event* next(unsigned p){need(active&&active->n<16,"bounded synchronous tape");struct event*e=&active->events[active->n++];e->provider=p;e->depth=depth;return e;}
static int record(unsigned p,const char*fmt,va_list ap){
 struct event*e=next(p);unsigned i=0;for(;fmt[i];i++){need(i+1<96,"bounded exact format");e->format[i]=fmt[i];}e->format[i]=0;
 for(i=0;fmt[i];i++)if(fmt[i]=='%'){i++;while(fmt[i]>='0'&&fmt[i]<='9')i++;need(fmt[i]=='l'&&fmt[i+1]=='x',"exact unsigned-long conversion");need(e->nargs<4,"at most four arguments");e->args[e->nargs++]=va_arg(ap,unsigned long);i++;}
 if(mode==1)need(p==1&&depth==1,"interrupt context uses unlocked print within outer lock");
 if(mode==0)need(p==2&&depth==0,"user context uses ordinary print without outer lock");
 return return_value;
}
int __kprintf(const char*f,...){va_list ap;va_start(ap,f);int r=record(1,f,ap);va_end(ap);return r;}
int kprintf(const char*f,...){va_list ap;va_start(ap,f);int r=record(2,f,ap);va_end(ap);return r;}
#include "original-body.inc"
extern void x86_context_line_log_bridge(int,unsigned long,unsigned long,unsigned long,unsigned long);
extern int fixture_run_context(int,const unsigned long*,Log,unsigned long(*)(void),void(*)(unsigned long));
static unsigned long lock_spy(void){need(depth==0,"outer lock enters once");next(3);depth++;return lock_flags;}
static void unlock_spy(unsigned long f){need(depth==1&&f==lock_flags,"outer unlock exact saved flags");struct event*e=next(4);e->nargs=1;e->args[0]=f;depth--;}
static int evarg(int e){eval[0]++;return e;}
static unsigned long arg(unsigned i,unsigned long v){eval[i]++;return v;}
static int same(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static void compare(struct trace*a,struct trace*b){
 need(a->n==b->n,"exact call count");for(unsigned i=0;i<a->n;i++){struct event*x=&a->events[i],*y=&b->events[i];need(x->provider==y->provider&&x->depth==y->depth&&x->nargs==y->nargs&&same(x->format,y->format),"exact provider/order/depth/format/vararg count");for(unsigned j=0;j<x->nargs;j++)need(x->args[j]==y->args[j],"full-width ordered vararg bits");}
}
static void direct(Log fn,int e,unsigned long*a,struct trace*t){
 active=t;depth=0;mode=-1;for(unsigned i=0;i<5;i++)eval[i]=0;
 fn(evarg(e),arg(1,a[0]),arg(2,a[1]),arg(3,a[2]),arg(4,a[3]));
 for(unsigned i=0;i<5;i++)need(eval[i]==1,"five caller arguments evaluate once");need(depth==0,"logger does not change lock depth");active=NULL;
}
static void context(Log fn,int which,unsigned long*a,struct trace*t){
 active=t;depth=0;mode=which;int r=fixture_run_context(which,a,fn,lock_spy,unlock_spy);need(r==0&&depth==0,"actual context body completes and unlocks");
 if(which==0)need(t->n==3,"three user context prints");
 else {need(t->n==13&&t->events[0].provider==3&&t->events[12].provider==4,"one outer span brackets eleven prints");}
 active=NULL;
}
int main(void){
 _Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"real x86_64 widths");
 unsigned long values[136]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0xaaaaaaaaaaaaaaaaUL,0x5555555555555555UL,0x0123456789abcdefUL};unsigned n=8;
 for(unsigned b=0;b<64;b++){values[n++]=1UL<<b;values[n++]=~(1UL<<b);}need(n==136,"136 long boundaries");
 const int events[]={INT_MIN,-1,0,1,2,3,4,5,6,7,19,20,21,22,23,INT_MAX};
 const int returns[]={INT_MIN,-1,0,1,INT_MAX};unsigned directpairs=0,contextpairs=0;
 for(unsigned i=0;i<n;i++)for(unsigned r=0;r<5;r++){
  unsigned long args[21];for(unsigned j=0;j<21;j++)args[j]=values[(i+j)%n];return_value=returns[r];lock_flags=values[i];
  for(unsigned e=0;e<16;e++){
   struct trace a={0},b={0};direct(original_context_log,events[e],args,&a);direct(x86_context_line_log_bridge,events[e],args,&b);compare(&a,&b);
   unsigned expected=(events[e]>=2&&events[e]<=6)?2:((events[e]==1||events[e]==20||events[e]==21||events[e]==22)?1:0);need(a.n==expected,"all nine defined events and unknown no-op");directpairs++;
  }
  for(int which=0;which<2;which++){struct trace a={0},b={0};context(original_context_log,which,args,&a);context(x86_context_line_log_bridge,which,args,&b);compare(&a,&b);contextpairs++;}
 }
 need(directpairs==10880&&contextpairs==1360,"exact finite pair coverage");
 printf("PASS actual_C_Rust_context_logger_direct_pairs=%u actual_Rust_caller_lock_span_pairs=%u total=12240 exact_events=9 provider_channels=2 return_values=5\n",directpairs,contextpairs);return 0;
}
''')
write(F/'actual_header_selection.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <ihk/debug.h>
#include "selected-body.inc"
typedef void(*M14ContextLogFn)(int,unsigned long,unsigned long,unsigned long,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_context_line_log_bridge),M14ContextLogFn),"exact five-argument context callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int(*)(const char*,...)),"existing ordinary variadic provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__kprintf),int(*)(const char*,...)),"existing unlocked variadic provider ABI");
_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8&&sizeof(void*)==8,"actual int/long/pointer widths");
M14ContextLogFn M14_CONTEXT_LOG_CONSUMER=x86_context_line_log_bridge;
''')
write(F/'observe_artifacts.py',r'''# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json
P=Path(__file__).resolve().parent.parent;A=P/'actual-owned-capture-1'
def rows(n):return [x.split() for x in (A/n/'stdout').read_text().splitlines() if x.split()]
def unique(rs,n,k):
 a=[x for x in rs if x[-1]==n];assert len(a)==1 and a[0][-2]==k,(n,a)
target='x86_context_line_log_bridge'
r=rows('06-Rust-symbols');s=rows('07-selected-C-symbols');f=rows('08-fallback-C-symbols');p=rows('11-partial-symbols')
unique(r,target,'T');unique(r,'kprintf','U');unique(r,'__kprintf','U')
unique(s,target,'U');unique(f,target,'T');unique(f,'kprintf','U');unique(f,'__kprintf','U')
unique(p,target,'T');unique(p,'kprintf','U');unique(p,'__kprintf','U')
assert target in (A/'09-selected-C-relocations/stdout').read_text()
out=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_COMPLETE_CONTEXT_LOG_LEAF_REAL_HEADER_SELECTED_FALLBACK_PROVIDER_CHANNELS_AND_PARTIAL_ONLY',Rust_unique_T=True,C_selected_U=True,C_fallback_original_T=True,actual_formatters_executed=False,production_fullcrate_wholeCPU_TU_defaultlink_native=False)
(P/'ACTUAL-LEAF-SYMBOL-OBSERVATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
''')
old=BASE/'EXECUTABLE-READY.NOT-EXECUTED.json';baseline=json.loads(old.read_bytes());rustc=baseline['commands'][0]['argv'][0];gcc='/usr/bin/gcc-9'
h=baseline['commands'][4]['argv'][:];h=h[:h.index('-c')]
cmds=[
 ('00-actual-Rust-context-log-and-caller-compile',[rustc,'--edition=2021','--crate-type=lib','--emit=obj='+str(O/'context-logger.o'),'-C','opt-level=2','-C','panic=abort','-C','codegen-units=1',str(F/'actual_context_logger.rs')]),
 ('01-original-C-context-tape-compile',[gcc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-c',str(F/'compare_context_tapes.c'),'-o',str(O/'context-tape.o')]),
 ('02-original-C-Rust-context-tape-link',[gcc,'-no-pie',str(O/'context-tape.o'),str(O/'context-logger.o'),'-o',str(O/'fixture')]),
 ('03-actual-C-Rust-context-pairs',[str(O/'fixture')]),
 ('04-real-header-selected-C-compile',h+['-c',str(F/'actual_header_selection.c'),'-o',str(O/'selected.o')]),
 ('05-real-header-fallback-C-compile',[a for a in h if a!='-DMCKERNEL_RUST_X86_CPU_HELPERS']+['-c',str(F/'actual_header_selection.c'),'-o',str(O/'fallback.o')]),
 ('06-Rust-symbols',['/usr/bin/nm','-a',str(O/'context-logger.o')]),
 ('07-selected-C-symbols',['/usr/bin/nm','-a',str(O/'selected.o')]),
 ('08-fallback-C-symbols',['/usr/bin/nm','-a',str(O/'fallback.o')]),
 ('09-selected-C-relocations',['/usr/bin/readelf','-rW',str(O/'selected.o')]),
 ('10-selected-C-Rust-partial-link',['/usr/bin/ld','-r',str(O/'selected.o'),str(O/'context-logger.o'),'-o',str(O/'partial.o')]),
 ('11-partial-symbols',['/usr/bin/nm','-a',str(O/'partial.o')]),
 ('12-artifact-observer',['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'observe_artifacts.py')]),
]
headerpaths=[ROOT/'lib/include/types.h',ROOT/'arch/x86_64/kernel/include/ihk/types.h',ROOT/'lib/include/ihk/debug.h',ROOT/'kernel/include/lwk/compiler.h',ROOT/'kernel/include/lwk/compiler-gcc.h']
headers={str(p):pin(p) for p in headerpaths}
scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
recipe=dict(scope=scope,status='SOURCE_READY_PRIVATE_SUCCESSOR_NOT_CANONICAL_NO_GRANT_NOT_EXECUTED',accepted_private_base=dict(C=pin(C),Rust=pin(R),actual_CPUlog_consumer=pin(BASE/'production-consumer-preparation-1/bounded-header-transport-correction-1/FINAL-ACTUAL-PRODUCTION-HANDOFF.json')),observed_canonical=dict(C=pin(ROOT/'arch/x86_64/kernel/cpu.c'),Rust=pin(ROOT/'kernel/rust/x86_cpu_helpers.rs')),root_CPUlog_integration_notice_received=False,postimages={k:pin(P/'candidate'/k) for k in ['arch/x86_64/kernel/cpu.c','kernel/rust/x86_cpu_helpers.rs']},patch=pin(P/'PRIVATE-COMPLETE-CONTEXT-LOGGER.patch'),actual_original_C_body=original,actual_Rust_body=rust,unchanged_actual_Rust_context_bodies=[userbody,intbody],fixture_sources={p.name:pin(p) for p in F.iterdir()},profile_derivation=pin(old),profile=baseline['proposed_profile'],tools={t:pin(Path(t)) for t in [rustc,gcc,'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld','/home/holden/anaconda3/bin/python3']},actual_witness_header_closure=headers,actual_witness_include_graph={'fixture':['types.h','ihk/debug.h','selected-body.inc'],'types.h':['ihk/types.h'],'ihk/debug.h':['lwk/compiler.h'],'lwk/compiler.h':['types.h','lwk/compiler-gcc.h under __KERNEL__+GCC9'],'lwk/compiler-gcc.h':[]},excluded_compiler_headers='compiler-intel.h/clang.h inactive under exactGCC9 profile; no fakeheaders. Prior kmsg.h failure aa036 retained separately; witness uses actual production ihk/debug.h and explicit5header closure.',commands=[dict(name=n,argv=a,purpose=scope+' Actual originalC/Rust context logger plus actual Rust context caller and controlled print/lock tape; no target register/IRQ instructions or native execution.') for n,a in cmds],planned_direct_pairs_NOT_ACTUAL=10880,planned_actual_Rust_context_caller_pairs_NOT_ACTUAL=1360,planned_total_pairs_NOT_ACTUAL=12240,planned_known_events=9,planned_provider_channels=2,planned_values=136,planned_kprintf_returns=5,known_event_ids=[1,2,3,4,5,6,20,21,22],unknown_events_noop=True,lock_span='Actual unchanged Rustinterruptcontext body takes one controlled lock, executes11__kprintf taps, unlocks exactflags once; actual usercontext body retains3kprintf taps. New logger does not add locks or retain contextpointers.',Rust_declaration_change='Remove existing extern x86_context_line_log_bridge to avoid E0428; add existing-provider __kprintf variadic declaration; reuse existing kprintf declaration/debug.rs exports.',debug_provider=pin(ROOT/'kernel/rust/debug.rs'),canonical_mutations=0,compiler_jobs=0,test_jobs=0,CPU_slots_held=0,production_full78_wholeCPU_TU_defaultlink_native='OPEN',no_stack_logger_change=True,failure_family='Newboundedcompletecontextlogger slice, firstcandidate notexecuted; rootmanagedoneboundedcorrection thenexpert. All priorCPUlogkmsg failure histories remain preserved separately.',qualifications=['Actual complete C logger vs actual Rust logger typed variadic tape; no Rustformatter execution.','Actual existing Rust context caller bodies use actual abi.rs X86UserContext types; C lock/unlock are controlled synchronous endpoints, no model structs/layout.','Leaf symbol/selected/fallback/ABI/partial consumer only; not wholeCPU TU/fullcrate/defaultELF/native retirement.','Private successor currently based acceptedCPUlogger2d29/26180; wait rootactualcanonical integration notice before finalproductionrecipe/canonicalpreimage refresh.'])
write(P/'EXECUTABLE-READY.NOT-EXECUTED.json',json.dumps(recipe,indent=2)+'\n')
print(json.dumps({'recipe':pin(P/'EXECUTABLE-READY.NOT-EXECUTED.json'),'patch':recipe['patch'],'postimages':recipe['postimages'],'commands':13,'planned_pairs_not_acceptance':12240,'CPU_slots_held':0}))
