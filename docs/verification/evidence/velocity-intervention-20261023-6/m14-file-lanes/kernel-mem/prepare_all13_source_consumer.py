"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source preparation only, no tests or compilers."""
from pathlib import Path
import hashlib,json,re,shutil
D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');N=D/'all-thirteen-consumer-preparation-1';N.mkdir(exist_ok=False);F=N/'fixture';F.mkdir();sha=lambda b:hashlib.sha256(b).hexdigest()
C=D/'all-thirteen-callback-source-only-1/candidate';mem=(C/'kernel/rust/mem_helpers.rs').read_text();oldc=(R/'kernel/mem.c').read_text()
# Complete function extraction is byte-bound, never an algorithm mirror.
def extract(s,name,marker=None):
 if marker is None:marker='pub unsafe extern "C" fn '+name+'('
 a=s.index(marker);start=s.index('{',a);i=start+1;depth=1
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 # Include no_mangle when present immediately before Rust function.
 if s[max(0,a-13):a]=='#[no_mangle]\n':a-=13
 return s[a:i]+'\n'
names=['mem_tlb_rdtsc_bridge','mem_tlb_current_cpu_bridge','mem_tlb_get_vector_bridge','mem_tlb_interrupt_cpu_bridge','mem_tlb_noirq_lock_bridge','mem_tlb_noirq_unlock_bridge','mem_tlb_atomic_set_bridge','mem_tlb_atomic_inc_bridge','mem_tlb_atomic_dec_bridge','mem_tlb_atomic_read_bridge','mem_tlb_flush_single_bridge','mem_tlb_flush_all_bridge','mem_tlb_pause_bridge']
for k in ['actual_abi.rs','actual_kernel_declarations.h','host_inline_memset_adapter.c']:shutil.copyfile(D/'fixture'/k,F/k)
for k in ['atomic_helpers.rs','spinlock_helpers.rs']:shutil.copyfile(R/'kernel/rust'/k,F/k)
oldclosure=(D/'fixture/actual_rust_closure.rs').read_text();prefix=oldclosure[:oldclosure.index('unsafe extern "C" {')]
prefix=prefix.replace('use abi::{CInt,CULong,ProcessVm,AddressSpace,TlbFlushEntry,CPU_SET_WORDS};','use abi::{CInt,CULong,ProcessVm,AddressSpace,TlbFlushEntry,CPU_SET_WORDS};\nmod atomic_helpers;\nmod spinlock_helpers;')
ffi='''unsafe extern "C" {
 fn ihk_mc_get_processor_id()->CInt;
 fn ihk_mc_get_vector(type_:CInt)->CInt;
 fn ihk_mc_interrupt_cpu(cpu:CInt,vector:CInt)->CInt;
 fn rdtsc()->CULong;
 fn flush_tlb_single(addr:CULong);
 fn flush_tlb();
 fn cpu_pause();
 #[link_name="tlb_flush_vector"] static mut MEM_TLB_FLUSH_VECTOR_FIRST:TlbFlushEntry;
 static mem_remote_tlb_geometry:[CInt;3];
}
'''
funcs=names+['remote_flush_tlb_array_cpumask','mem_remote_flush_tlb_array_body_result','mem_tlb_flush_handler_body_result'];bindings=[];rust=prefix+ffi
for name in funcs:
 body=extract(mem,name);rust+='\n'+body;bindings.append({'name':name,'source_sha256':sha(mem.encode()),'exact_function_sha256':sha(body.encode()),'bytes':len(body.encode())})
rust+='\n'+oldclosure[oldclosure.index('#[no_mangle]\npub static F01_ACTUAL_LAYOUT'):]
(F/'actual_all13_closure.rs').write_text(rust);(F/'EXACT-FUNCTION-EXTRACTIONS.json').write_text(json.dumps(bindings,indent=2)+'\n')
original=''
for name in names:
 p=oldc.index(name+'(');a=oldc.rfind('\n',0,p)+1;marker=oldc[a:p]+name+'(';body=extract(oldc,name,marker);body=body.replace('MEM_TLB_PUBLIC_BRIDGE ','').replace('static void ','void ',1).replace(name,'original_'+name,1);original+=body+'\n'
(F/'original-all13-providers.inc').write_text(original)
arr=(D/'fixture/original-array-entry.inc').read_text()
for name in sorted(names,key=len,reverse=True):arr=re.sub(r'(?<!original_)\b'+name+r'\b','original_'+name,arr)
(F/'original-array-entry.inc').write_text(arr)
c=(D/'fixture/fixture.c').read_text();c=c.replace('Three exact original C providers','All13 exact original C providers').replace('CPU/interrupt ISA endpoints are controlled.','CPU/interrupt/timestamp/flush/pause ISA endpoints controlled; real Rust atomic/spinlock modules.');c=c.replace('static int consumer_mode,current_cpu,provider_return,delay_delivery,lock_depth;','static int consumer_mode,current_cpu,provider_return,delay_delivery,lock_depth,original_mode;')
# Replace all controlled adapter implementations with controlled real endpoint bodies.
a=c.index('static void mem_tlb_atomic_dec_bridge(');b=c.index('static void deliver(',a)
c=c[:a]+'''extern unsigned long mem_tlb_rdtsc_bridge(void);
extern void mem_tlb_noirq_lock_bridge(unsigned long);
extern void mem_tlb_noirq_unlock_bridge(unsigned long);
extern void mem_tlb_atomic_set_bridge(unsigned long,int);
extern void mem_tlb_atomic_inc_bridge(unsigned long);
extern void mem_tlb_atomic_dec_bridge(unsigned long);
extern int mem_tlb_atomic_read_bridge(unsigned long);
extern void mem_tlb_flush_single_bridge(unsigned long);
extern void mem_tlb_flush_all_bridge(void);
extern void mem_tlb_pause_bridge(void);
void preempt_disable(void){++lock_depth;event(5,lock_depth,0,0,0);}
void preempt_enable(void){event(6,lock_depth,0,0,0);--lock_depth;if(lock_depth<0)abort();}
void flush_tlb_single(unsigned long addr){event(10,addr,0,0,0);}
void flush_tlb(void){event(11,0,0,0,0);}
#include "original-all13-providers.inc"
'''+c[b:]
a=c.index(' ++handlers;int ret=');b=c.index('\n}',a)
c=c[:a]+''' int slot=vector-IHK_TLB_FLUSH_IRQ_VECTOR_START;
 if(slot<0||slot>=IHK_TLB_FLUSH_IRQ_VECTOR_SIZE)abort();
 int before=ihk_atomic_read(&tlb_flush_vector[slot].pending);++handlers;
 int ret=mem_tlb_flush_handler_body_result(vector,tlb_flush_vector,IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,irq_save,irq_restore,
  original_mode?original_mem_tlb_flush_single_bridge:mem_tlb_flush_single_bridge,
  original_mode?original_mem_tlb_flush_all_bridge:mem_tlb_flush_all_bridge,
  original_mode?original_mem_tlb_atomic_dec_bridge:mem_tlb_atomic_dec_bridge);
 if(ret||before<=0||ihk_atomic_read(&tlb_flush_vector[slot].pending)!=before-1)abort();++decrements;'''+c[b:]
a=c.index('unsigned long mem_tlb_rdtsc_bridge(void){');b=c.index('#include "original-array-entry.inc"',a)
c=c[:a]+'''unsigned long rdtsc(void){event(4,17,0,0,0);return 17;}
void cpu_pause(void){++pauses;event(15,done,queued,0,0);if(done>=queued)abort();deliver(queue[done++]);}
'''+c[b:]
c=c.replace(' n=0;memset(trace,0,sizeof trace);memset(tlb_flush_vector,0,sizeof tlb_flush_vector);',' n=0;memset(trace,0,sizeof trace);memset(tlb_flush_vector,0,sizeof tlb_flush_vector);memset(&aspace.cpu_set_lock,0,sizeof aspace.cpu_set_lock);')
c=c.replace('reset();original_remote_flush_tlb_array_cpumask','reset();original_mode=1;original_remote_flush_tlb_array_cpumask').replace('reset();remote_flush_tlb_array_cpumask','reset();original_mode=0;remote_flush_tlb_array_cpumask')
# Additional direct tests cover real atomic wrapping and ticket/preemption behavior.
needle=' const unsigned long firsts[]='
idx=c.index(needle)
extra=''' unsigned atomics=0,locks=0,endpoints=0;
 for(unsigned i=0;i<9;i++){
  ihk_atomic_t a,b;
  original_mem_tlb_atomic_set_bridge((unsigned long)&a,values[i]);mem_tlb_atomic_set_bridge((unsigned long)&b,values[i]);
  require(original_mem_tlb_atomic_read_bridge((unsigned long)&a)==mem_tlb_atomic_read_bridge((unsigned long)&b));atomics++;
  original_mem_tlb_atomic_inc_bridge((unsigned long)&a);mem_tlb_atomic_inc_bridge((unsigned long)&b);
  require((unsigned)ihk_atomic_read(&a)==(unsigned)values[i]+1U&&(unsigned)ihk_atomic_read(&a)==(unsigned)ihk_atomic_read(&b));atomics++;
  original_mem_tlb_atomic_dec_bridge((unsigned long)&a);mem_tlb_atomic_dec_bridge((unsigned long)&b);
  require(ihk_atomic_read(&a)==values[i]&&ihk_atomic_read(&a)==ihk_atomic_read(&b));atomics++;
 }
 for(unsigned i=0;i<3;i++){
  ihk_spinlock_t a,b;unsigned short v=(unsigned short)(i==0?0:i==1?65534:65535);a.head_tail=b.head_tail=(unsigned)v|((unsigned)v<<16);
  reset();original_mem_tlb_noirq_lock_bridge((unsigned long)&a);require(lock_depth==1);original_mem_tlb_noirq_unlock_bridge((unsigned long)&a);require(!lock_depth);unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();mem_tlb_noirq_lock_bridge((unsigned long)&b);require(lock_depth==1);mem_tlb_noirq_unlock_bridge((unsigned long)&b);require(!lock_depth&&a.head_tail==b.head_tail&&a.tickets.head==(unsigned short)(v+2)&&a.tickets.head==a.tickets.tail&&len==n&&!memcmp(saved,trace,sizeof trace));locks++;
 }
 for(unsigned i=0;i<9;i++){
  reset();unsigned long a=original_mem_tlb_rdtsc_bridge();original_mem_tlb_flush_single_bridge((unsigned long)(long)values[i]);original_mem_tlb_flush_all_bridge();unsigned len=n;memcpy(saved,trace,sizeof trace);
  reset();unsigned long b=mem_tlb_rdtsc_bridge();mem_tlb_flush_single_bridge((unsigned long)(long)values[i]);mem_tlb_flush_all_bridge();require(a==b&&n==len&&!memcmp(saved,trace,sizeof trace));endpoints++;
 }
'''
c=c[:idx]+extra+c[idx:]
c=c.replace('printf("PASS direct=%u actual-array-handler=%u invalid=%u original-C/Rust provider pairs; no completion except real handler decrement\\n",direct,protocol,invalid);','require(atomics==27&&locks==3&&endpoints==9);\n printf("PASS all13 direct=%u actual-array-handler=%u invalid=%u atomics=%u locks=%u endpoints=%u; actual atomic/spin providers; completion only real handler decrement\\n",direct,protocol,invalid,atomics,locks,endpoints);')
(F/'fixture.c').write_text(c)
abi=(D/'fixture/actual-header-ABI.c').read_text().replace('#include "../candidate/kernel/mem.c"','#include "'+str(C/'kernel/mem.c')+'"')
for ty,name,args,call in [('unsigned long','mem_tlb_rdtsc_bridge','void',''),('void','mem_tlb_noirq_lock_bridge','unsigned long',''),('void','mem_tlb_noirq_unlock_bridge','unsigned long',''),('void','mem_tlb_atomic_set_bridge','unsigned long,int',''),('void','mem_tlb_atomic_inc_bridge','unsigned long',''),('void','mem_tlb_atomic_dec_bridge','unsigned long',''),('int','mem_tlb_atomic_read_bridge','unsigned long',''),('void','mem_tlb_flush_single_bridge','unsigned long',''),('void','mem_tlb_flush_all_bridge','void',''),('void','mem_tlb_pause_bridge','void','')]:
 abi+='_Static_assert(__builtin_types_compatible_p(__typeof__(&'+name+'),'+ty+'(*)('+args+')),"'+name+' actualcallback ABI");\n'
abi+='_Static_assert(sizeof(ihk_spinlock_t)==4 && __alignof__(ihk_spinlock_t)==4 && __builtin_offsetof(ihk_spinlock_t,head_tail)==0,"actual4B ticketlock ABI");\n'
(F/'actual-header-ABI.c').write_text(abi)
plan=json.loads((D/'expert-fixture-import-correction-1/CORRECTED-RECIPE.NOT-EXECUTED.json').read_bytes());commands=plan['commands']
for x in commands:
 x['argv']=[arg.replace(str(D/'fixture'),str(F)).replace(str(D/'output-1'),str(N/'output-1')).replace(str(D/'candidate/kernel/mem.c'),str(C/'kernel/mem.c')).replace('actual_rust_closure.rs','actual_all13_closure.rs') for arg in x['argv']];x['cwd']=str(N)
commands[0]['label']='actual-all13-Rust-with-real-atomic-spinlock';commands[4]['label']='actual-combined-all13-original-C-Rust-consumer'
sources=[]
for p in sorted(F.iterdir()):sources.append({'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size})
a={'scope':__doc__,'status':'ALL13_COMBINED_CONSUMER_SOURCE_AND_COMMANDS_PREPARED_NOT_EXECUTED','candidate':str(C),'candidate_C_sha256':'9d53106e7228b5a7654f4250bab58e20e7bc47a28f8ad9675b1c9ac92599b976','candidate_Rust_sha256':'6a527f7a55930d72d6d72c775ee0261c3550e2bd0094fe01031f3aa3238aefd6','sources':sources,'commands':commands,'profile':plan['profile'],'actual':None,'expected_cases_NOT_ACTUAL':1983,'case_breakdown_NOT_ACTUAL':{'combined_original819provider_patterns':819,'array_real_handler':1120,'invalid':5,'atomic':27,'ticket_wrap':3,'timestamp_flush':9},'qualified':'Privileged flush/timestamp/pause and CPU/IPI endpoints controlled; actual unmodified Rust atomic_helpers and spinlock_helpers modules linked. OriginalC13callbacks call same actual providers. Handler pending decrement audited before/after, never fakeACK. Old1944 evidence reused as baseline; 1944 repeated here only for changed all13 combined consumer, no new countcredit yet.','history':['de3d9 prechild pin STOP','59d29 missingc_void STOP','actual fixture3 first3 PASS1944; no reset'],'production':'Current exact78 closure/current canonical union must be refreshed before compile; selected complete mem.c67header recipe reuse with all13 Cbody exclusion and Rust13 unique exports/relocations/fullpartial. Actual objects/hashesNULL until execution.','execution_grant':None,'CPU_reservation':None}
(N/'SOURCE-CONSUMER-AND-COMMANDS.NOT-EXECUTED.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'root':str(N),'receipt_sha256':sha((N/'SOURCE-CONSUMER-AND-COMMANDS.NOT-EXECUTED.json').read_bytes()),'fixture_sha256':sha((F/'fixture.c').read_bytes()),'Rust_closure_sha256':sha((F/'actual_all13_closure.rs').read_bytes())},indent=2))
