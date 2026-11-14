# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,difflib,shutil,re
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');C=P/'candidate';F=P/'fixture';C.mkdir();F.mkdir()

def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def function(src,marker):
 a=src.index(marker);b=src.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(src[i]=='{')-(src[i]=='}');i+=1
 return src[a:i]
c=(R/'kernel/mem.c').read_text();rs=(R/'kernel/rust/mem_helpers.rs').read_text();abi=R/'kernel/rust/abi.rs'
original=function(c,'void remote_flush_tlb_array_cpumask(');body=function(rs,'pub unsafe extern "C" fn mem_remote_flush_tlb_array_body_result(')
assert c.count('void remote_flush_tlb_array_cpumask(')==1 and 'fn remote_flush_tlb_array_cpumask(' not in rs
assert '(void)mem_remote_flush_tlb_array_body_result(' in original
callbacks=['rdtsc','current_cpu','get_vector','interrupt_cpu','noirq_lock','noirq_unlock','atomic_set','atomic_inc','atomic_read','flush_single','flush_all','pause'];names=['mem_tlb_'+n+'_bridge' for n in callbacks];assert len(names)==12
start=c.index('static unsigned long mem_tlb_rdtsc_bridge(void)');finish=c.index('\nvoid remote_flush_tlb_cpumask(',start);oldregion=c[start:finish]
region=oldregion
for name in names:
 pattern=r'static ((?:unsigned long|int|void) '+name+r'\()';region,n=re.subn(pattern,r'MEM_TLB_PUBLIC_BRIDGE \1',region);assert n==1,(name,n)
assert 'static void mem_tlb_atomic_dec_bridge' in region
prefix='''/* Immutable source-header geometry; no new C runtime implementation. */
#ifdef MCKERNEL_RUST_MEM_HELPERS
const int mem_remote_tlb_geometry[3] = {
	IHK_TLB_FLUSH_IRQ_VECTOR_SIZE, IHK_TLB_FLUSH_IRQ_VECTOR_START, CPU_SETSIZE
};
#define MEM_TLB_PUBLIC_BRIDGE
#else
#define MEM_TLB_PUBLIC_BRIDGE static
#endif

'''
newc=c[:start]+prefix+region+'\n#undef MEM_TLB_PUBLIC_BRIDGE\n'+c[finish:]
assert newc.count(original)==1;newc=newc.replace(original,'#ifndef MCKERNEL_RUST_MEM_HELPERS\n'+original+'\n#endif /* C fallback; default Rust entry owns this symbol. */',1)
extern='''
    // C owns the complete vector array; this names its first element only.
    // No array extent is invented: the immutable header geometry supplies it.
    #[link_name = "tlb_flush_vector"]
    static mut MEM_TLB_FLUSH_VECTOR_FIRST: TlbFlushEntry;
    static mem_remote_tlb_geometry: [CInt; 3];
    fn mem_tlb_rdtsc_bridge() -> CULong;
    fn mem_tlb_current_cpu_bridge() -> CInt;
    fn mem_tlb_get_vector_bridge(type_: CInt) -> CInt;
    fn mem_tlb_interrupt_cpu_bridge(cpu: CInt, vector: CInt);
    fn mem_tlb_noirq_lock_bridge(lock_addr: CULong);
    fn mem_tlb_noirq_unlock_bridge(lock_addr: CULong);
    fn mem_tlb_atomic_set_bridge(atomic_addr: CULong, value: CInt);
    fn mem_tlb_atomic_inc_bridge(atomic_addr: CULong);
    fn mem_tlb_atomic_read_bridge(atomic_addr: CULong) -> CInt;
    fn mem_tlb_flush_single_bridge(addr: CULong);
    fn mem_tlb_flush_all_bridge();
    fn mem_tlb_pause_bridge();
'''
entry='''/// Keep the original synchronous TLB request and callback ownership boundary.
///
/// # Safety
/// The caller retains vm and the address array until the existing body returns.
/// Existing callbacks preserve current-CPU, vector, IRQ and lock semantics. C
/// owns the shared vector and immutable geometry; no pointer is retained by this
/// entry beyond the original body, and its integer return remains ignored.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_array_cpumask(
    vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
) {
    let geometry = unsafe { core::ptr::read(core::ptr::addr_of!(mem_remote_tlb_geometry)) };
    let _ = unsafe {
        mem_remote_flush_tlb_array_body_result(
            vm, addr, nr_addr, cpu_id,
            core::ptr::addr_of_mut!(MEM_TLB_FLUSH_VECTOR_FIRST),
            geometry[0], geometry[1], geometry[2],
            Some(mem_tlb_rdtsc_bridge), Some(mem_tlb_current_cpu_bridge),
            Some(mem_tlb_get_vector_bridge), Some(mem_tlb_interrupt_cpu_bridge),
            Some(mem_tlb_noirq_lock_bridge), Some(mem_tlb_noirq_unlock_bridge),
            Some(mem_tlb_atomic_set_bridge), Some(mem_tlb_atomic_inc_bridge),
            Some(mem_tlb_atomic_read_bridge), Some(mem_tlb_flush_single_bridge),
            Some(mem_tlb_flush_all_bridge), Some(mem_tlb_pause_bridge),
        )
    };
}

'''
newrs=rs.replace('unsafe extern "C" {','unsafe extern "C" {'+extern,1);marker='#[no_mangle]\n'+body;assert marker in newrs;newrs=newrs.replace(marker,entry+marker,1)
assert function(newrs,'pub unsafe extern "C" fn mem_remote_flush_tlb_array_body_result(')==body
write(C/'kernel/mem.c',newc);write(C/'kernel/rust/mem_helpers.rs',newrs)
patch=''
for key,a,b in [('kernel/mem.c',c,newc),('kernel/rust/mem_helpers.rs',rs,newrs)]:patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+key,tofile='b/'+key))
write(P/'PRIVATE-REMOTE-FLUSH.patch',patch)
# Actual production ABI module and exact callback aliases/body signature; no
# new model ProcessVm/TlbFlushEntry layout is introduced into this fixture.
shutil.copy2(abi,F/'actual_abi.rs')
aliasnames=['MemRdtscFn','MemCurrentCpuFn','MemGetVectorFn','MemInterruptCpuFn','MemNoirqLockFn','MemAtomicSetFn','MemAtomicIncFn','MemAtomicReadFn','MemFlushTlbSingleFn','MemFlushTlbAllFn','MemPauseFn'];aliases=[]
for name in aliasnames:
 a=rs.index('type '+name+' =');aliases.append(rs[a:rs.index(';',a)+1])
bodydecl=body[:body.index('{')].replace('pub unsafe extern "C" fn','fn',1).rstrip()+';'
rust='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact proposed export + production ABI types; underlying body is a full-
// signature C recorder stub, not a claim of TLB algorithm/native execution.
#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm,TlbFlushEntry};
'''+ '\n'.join(aliases)+'\nunsafe extern "C" {\n'+extern+'\n'+bodydecl+'\n}\n'+entry
rust+='''#[no_mangle]
pub static M14_RUST_TLB_LAYOUT:[usize;15]=[
 core::mem::size_of::<CInt>(),core::mem::align_of::<CInt>(),
 core::mem::size_of::<CULong>(),core::mem::size_of::<*mut ProcessVm>(),
 core::mem::size_of::<[CInt;3]>(),core::mem::align_of::<[CInt;3]>(),
 core::mem::size_of::<TlbFlushEntry>(),core::mem::align_of::<TlbFlushEntry>(),
 core::mem::offset_of!(TlbFlushEntry,vm),core::mem::offset_of!(TlbFlushEntry,addr),
 core::mem::offset_of!(TlbFlushEntry,nr_addr),core::mem::offset_of!(TlbFlushEntry,pending),
 core::mem::offset_of!(TlbFlushEntry,lock),abi::CPU_SET_WORDS*64,
 core::mem::size_of::<Option<MemRdtscFn>>()];
'''
write(F/'actual_export.rs',rust)
# C ABI typedefs and original wrapper are extracted verbatim.
aliaslines=[]
for name in ['mem_rdtsc_fn_t','mem_current_cpu_fn_t','mem_get_vector_fn_t','mem_interrupt_cpu_fn_t','mem_noirq_lock_fn_t','mem_atomic_set_fn_t','mem_atomic_inc_fn_t','mem_atomic_read_fn_t','mem_flush_tlb_single_fn_t','mem_flush_tlb_all_fn_t','mem_pause_fn_t']:
 line=next(x for x in c.splitlines() if x.startswith('typedef ') and '(*'+name+')' in x);aliaslines.append(line)
a=c.index('int mem_remote_flush_tlb_array_body_result(',c.index('#else\nvoid *mem_pa_alloc_aligned_pages_node_result'));b=c.index('{',a);cdecl=c[a:b].strip()+';'
headers='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <ihk/mm.h>
#include <ihk/cpu.h>
#include <affinity.h>
'''+ '\n'.join(aliaslines)+'\n'+cdecl+'\n'
write(F/'actual_declarations.h',headers)
fixture=headers+'''#include <assert.h>
#include <stdio.h>
#include <string.h>
unsigned long recorded[20]; static int body_calls, body_return,callback_calls;
'''
# C recorder callbacks never execute target instructions; each has production ABI.
for name in names:
 sig=function(c,('static unsigned long ' if name=='mem_tlb_rdtsc_bridge' else 'static int ' if name in ['mem_tlb_current_cpu_bridge','mem_tlb_atomic_read_bridge','mem_tlb_get_vector_bridge'] else 'static void ')+name+'(').split('{',1)[0].strip().replace('static ','',1)
 fixture+=sig+' { ++callback_calls;'+(' return 0;' if sig.startswith(('unsigned long ','int ')) else '')+' }\n'
fixture+='''struct tlb_flush_entry tlb_flush_vector[IHK_TLB_FLUSH_IRQ_VECTOR_SIZE];
const int mem_remote_tlb_geometry[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};
'''
fixture+=cdecl[:-1]+''' {
 ++body_calls;
 recorded[0]=(unsigned long)vm;recorded[1]=(unsigned long)addr;
 recorded[2]=(unsigned long)(long)nr_addr;recorded[3]=(unsigned long)(long)cpu_id;
 recorded[4]=(unsigned long)tlb_flush_vector;recorded[5]=(unsigned long)(long)vector_size;
 recorded[6]=(unsigned long)(long)vector_start;recorded[7]=(unsigned long)(long)cpu_set_bits;
'''
params=['rdtsc_fn','current_cpu_fn','get_vector_fn','interrupt_cpu_fn','lock_fn','unlock_fn','atomic_set_fn','atomic_inc_fn','atomic_read_fn','flush_single_fn','flush_all_fn','pause_fn']
for i,p in enumerate(params,8):fixture+=' recorded['+str(i)+']=(unsigned long)'+p+';\n'
fixture+=' return body_return;\n}\n'+original.replace('void remote_flush_tlb_array_cpumask(','void original_remote_flush_tlb_array_cpumask(',1)+'\n'
fixture+='''static struct process_vm vm_storage;
static unsigned long addresses[8]={0,1,4095,4096,~0UL,0x8000000000000000UL,0x12345,0};
int main(void){
 unsigned long saved[20];unsigned long pairs=0;
 int counts[]={-3,-1,0,1,2,8,(-2147483647-1),2147483647};
 int cpus[]={-1,0,1,1023,1024,(-2147483647-1),2147483647};
 int returns[]={(-2147483647-1),-22,-1,0,1,63,64,2147483647};
 for(int v=0;v<2;v++)for(int a=0;a<2;a++)for(unsigned n=0;n<8;n++)for(unsigned cpu=0;cpu<7;cpu++)for(unsigned ret=0;ret<8;ret++){
 struct process_vm *vm=v?&vm_storage:0;unsigned long *addr=a?addresses:0;body_return=returns[ret];
 body_calls=callback_calls=0;memset(recorded,0,sizeof(recorded));
 original_remote_flush_tlb_array_cpumask(vm,addr,counts[n],cpus[cpu]);assert(body_calls==1&&callback_calls==0);memcpy(saved,recorded,sizeof(saved));
 body_calls=callback_calls=0;memset(recorded,0,sizeof(recorded));
 remote_flush_tlb_array_cpumask(vm,addr,counts[n],cpus[cpu]);assert(body_calls==1&&callback_calls==0);assert(memcmp(saved,recorded,sizeof(saved))==0);
 assert(recorded[4]==(unsigned long)tlb_flush_vector);assert(recorded[5]==IHK_TLB_FLUSH_IRQ_VECTOR_SIZE);assert(recorded[6]==IHK_TLB_FLUSH_IRQ_VECTOR_START);assert(recorded[7]==CPU_SETSIZE);
'''
for i,name in enumerate(names,8):fixture+=' assert(recorded['+str(i)+']==(unsigned long)'+name+');\n'
fixture+=''' ++pairs;
 }
 assert(pairs==1792);printf("PASS actual_original_C_Rust_entry_pairs=%lu full_signature_arguments=20 callback_identities=12 ignored_returns=8 NO_TLB_ALGORITHM_OR_NATIVE_EXECUTION\\n",pairs);return 0;
}
'''
write(F/'actual_original_vs_export.c',fixture)
# Exact source-selected callback/entry region is compiled only, never executed.
select_start=newc.index('/* Immutable source-header geometry;');select_end=newc.index('\nvoid tlb_flush_handler(',select_start)
write(F/'actual_selected_region.c',headers+newc[select_start:select_end]+'\n')
# Header and immutable data ABI witness, not a whole mem.c TU replacement.
abi_c=headers+'''extern const int mem_remote_tlb_geometry[3];
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(mem_remote_tlb_geometry),const int[3]),"immutable C int geometry ABI");
_Static_assert(sizeof(int)==4&&_Alignof(int)==4&&sizeof(unsigned long)==8,"actual x86_64 scalar ABI");
const unsigned long M14_C_TLB_LAYOUT[15]={
 sizeof(int),_Alignof(int),sizeof(unsigned long),sizeof(struct process_vm*),
 sizeof(const int[3]),_Alignof(const int[3]),sizeof(struct tlb_flush_entry),_Alignof(struct tlb_flush_entry),
 __builtin_offsetof(struct tlb_flush_entry,vm),__builtin_offsetof(struct tlb_flush_entry,addr),
 __builtin_offsetof(struct tlb_flush_entry,nr_addr),__builtin_offsetof(struct tlb_flush_entry,pending),
 __builtin_offsetof(struct tlb_flush_entry,lock),CPU_SETSIZE,sizeof(mem_rdtsc_fn_t)};
const int M14_C_TLB_GEOMETRY[3]={IHK_TLB_FLUSH_IRQ_VECTOR_SIZE,IHK_TLB_FLUSH_IRQ_VECTOR_START,CPU_SETSIZE};
'''
write(F/'actual_header_abi.c',abi_c)
# Reuse the accepted ordinary realheader profile; explicit finite changes only.
prior=Path('/home/holden/mckernel-work/host-preparation/compute-process-next-body-cutover-20261023-1/next-slice-1/production-abi-layout-1/EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json');pr=json.loads(prior.read_text());args=pr['C_argv'];base=args[:args.index('-c')];base=[x for x in base if x not in ['-mno-sse','-mcmodel=large','-nostdinc','-ffreestanding']]
# Runtime recorder needs libc includes and normal host code model. The realheader
# ABI/selection objects keep the prior freestanding flags unchanged.
header_base=args[:args.index('-c')];header_base=[x for x in header_base if x!='-DMCKERNEL_RUST_PROCESS_HELPERS']
record_base=[x for x in base if x!='-DMCKERNEL_RUST_PROCESS_HELPERS']
# Preserve exact accepted header closure and explicitly pin changed current
# relevant headers, whose selected ABI content must match before execution.
relevant=['lib/include/ihk/mm.h','lib/include/ihk/cpu.h','kernel/include/affinity.h','kernel/include/process.h','kernel/rust/abi.rs','kernel/CMakeLists.txt']
record=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_SOURCE_AND_FIXTURE_READY_NOT_COMPILED',preimages={k:pin(R/k) for k in ['kernel/mem.c','kernel/rust/mem_helpers.rs']},postimages={k:pin(C/k) for k in ['kernel/mem.c','kernel/rust/mem_helpers.rs']},patch=pin(P/'PRIVATE-REMOTE-FLUSH.patch'),existing_body_unchanged_sha256=hashlib.sha256(body.encode()).hexdigest(),exact_original_C_body=original,callbacks_passed=12,nearby_C_callbacks_retained=13,existing_default_selection=dict(path=pin(R/'kernel/CMakeLists.txt'),define='MCKERNEL_RUST_MEM_HELPERS',line=314),ABI_inputs={k:pin(R/k) for k in relevant},fixture_sources={q.name:pin(q) for q in F.iterdir()},prior_accepted_header_profile=pin(prior),header_config_closure=pr['actual_header_config_closure'],C_header_base=header_base,C_recorder_base=record_base,Rust_leaf_compiler='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc',profile_proposed=dict(CPU='ROOT_ASSIGN',jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,owned_capture_sha256='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'),planned_pairs=1792,planned_layout_words=15,planned_geometry_words=3,production_expectation='RustoneTremote_flush_tlb_array_cpumask; selectedCnoTentry/Uentryfromexistingremote_flush_tlb_cpumask;12existingCcallbackT+immutablegeometryR+existingvectorB;Rust14Cimports plus unchangedbodyproviderT in realfullcrate. FallbackCentryTandstaticcallbackspreserved.',qualifications=['Source-only candidate; planned test counts are not acceptance.','Leafrecorder stubs existing underlying body to compare actual20arg ABI/callbackidentity/ignoredreturns. It does not execute target TLB/IRQ instructions or prove flushalgorithm.','ExistingRustbody bytesunchanged; all13nearbyCcallbackimplementations remainexplicitcomputeCdebt,12madeexternallyvisibleunderexistingselecteddefineonly.','Immutable Cgeometry is declarative data, not new runtime Cfunctionality. No extra C/header/CMake edits required.','ExactproductionGCC14wholememTU/defaultkernel/link/native remainOPEN; wholeproductionRustconsumer requiresseparategrant.'],canonical_writes=0,compiler_jobs=0)
write(P/'SOURCE-AND-FIXTURE-PREPARATION.json',json.dumps(record,indent=2)+'\n');print(json.dumps(dict(patch=pin(P/'PRIVATE-REMOTE-FLUSH.patch'),postimages=record['postimages'],fixture_sources=len(record['fixture_sources']))))
