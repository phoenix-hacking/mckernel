# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import ast,difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
B=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-remote-flush')
F=P/'fixture';C=P/'candidate';F.mkdir();C.mkdir()
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def fun(s,marker):
 a=s.index(marker);b=s.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
c=(R/'kernel/mem.c').read_text();rs=(R/'kernel/rust/mem_helpers.rs').read_text()
assert pin(R/'kernel/mem.c')['sha256']=='7498e7c930a55bdcde5ecd12f4498c47c5573d690355c8f09a7b9f957ffe00a2'
assert pin(R/'kernel/rust/mem_helpers.rs')['sha256']=='c0e7f8bd0b117c9b4e0a4e3690ef5ed5cb01bdc6b16f7225de973eba039d72d5'
original=fun(c,'void remote_flush_tlb_cpumask(')
assert c.count('void remote_flush_tlb_cpumask(')==1 and 'fn remote_flush_tlb_cpumask(' not in rs
newc=c.replace(original,'#ifndef MCKERNEL_RUST_MEM_HELPERS\n'+original+'\n#endif /* C fallback; default Rust single-address entry. */',1)
entry='''/// Preserve the original single-address stack-local handoff to the array entry.
///
/// # Safety
/// The caller retains vm under the original TLB contract. The initialized local
/// lives through the synchronous array call, just as the C unsigned-long local
/// did. The existing array/body completion and lock protocol must finish every
/// use before this local expires. This entry does not dereference vm or retain
/// an additional pointer; neither callback nor shared-vector ownership changes.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_cpumask(
    vm: *mut ProcessVm, addr: CULong, cpu_id: CInt,
) {
    let mut local_addr = addr;
    unsafe {
        remote_flush_tlb_array_cpumask(
            vm, core::ptr::addr_of_mut!(local_addr), 1, cpu_id,
        )
    }
}

'''
marker='/// Keep the original synchronous TLB request and callback ownership boundary.'
assert rs.count(marker)==1;newrs=rs.replace(marker,entry+marker,1)
array_marker='pub unsafe extern "C" fn remote_flush_tlb_array_cpumask('
body_marker='pub unsafe extern "C" fn mem_remote_flush_tlb_array_body_result('
assert fun(rs,array_marker)==fun(newrs,array_marker) and fun(rs,body_marker)==fun(newrs,body_marker)
assert newc.replace('#ifndef MCKERNEL_RUST_MEM_HELPERS\n'+original+'\n#endif /* C fallback; default Rust single-address entry. */',original,1)==c
write(C/'kernel/mem.c',newc);write(C/'kernel/rust/mem_helpers.rs',newrs)
patch=''
for key,old,new in [('kernel/mem.c',c,newc),('kernel/rust/mem_helpers.rs',rs,newrs)]:
 patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+key,tofile='b/'+key))
write(P/'PRIVATE-SINGLE-TLB-ENTRY.patch',patch)
shutil.copy2(R/'kernel/rust/abi.rs',F/'actual_abi.rs')
rust='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact candidate entry+actual ABI types. Callee is an explicit recorder stub;
// no target TLB/IRQ implementation is executed.
#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm};
unsafe extern "C" {
    fn remote_flush_tlb_array_cpumask(
        vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
    );
}
'''+entry+'''#[no_mangle]
pub static M14_RUST_SINGLE_ABI:[usize;5]=[
    core::mem::size_of::<CInt>(),core::mem::size_of::<CULong>(),
    core::mem::align_of::<CULong>(),core::mem::size_of::<*mut ProcessVm>(),
    core::mem::size_of::<*mut CULong>(),
];
'''
write(F/'actual_single_export.rs',rust)
# Actual production include block, no substituted ProcessVm model layout.
headers='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n'+c[c.index('#include <kmsg.h>'):c.index('static unsigned long pa_start')]
harness=headers+'''extern int printf(const char *, ...);
#define CHECK(c) do { if (!(c)) return __LINE__; } while (0)
struct snapshot {
    struct process_vm *vm;
    unsigned long value;
    int nr;
    int cpu;
    int aligned;
};
static struct snapshot seen;
static int calls, invalid, mutate;
static struct process_vm vm_storage;
/* Recorder reads only the initialized local while the actual caller is active.
 * It never dereferences vm or saves the pointer for use after caller return. */
void remote_flush_tlb_array_cpumask(struct process_vm *vm,
        unsigned long *addr, int nr_addr, int cpu_id)
{
    ++calls;
    if (!addr || nr_addr != 1) { invalid=1; return; }
    seen.vm=vm;seen.value=*addr;seen.nr=nr_addr;seen.cpu=cpu_id;
    seen.aligned=((unsigned long)addr % _Alignof(unsigned long))==0;
    if (mutate) *addr=~*addr; /* valid mutable-pointer fixture boundary case */
}
'''+original.replace('void remote_flush_tlb_cpumask(','void original_remote_flush_tlb_cpumask(',1)+'''
int main(void)
{
    unsigned long values[136]={0,1,4095,4096,~0UL,0x8000000000000000UL,0x12345,0xaaaaaaaaaaaaaaaaUL};
    int cpus[9]={-1,0,1,63,64,1023,1024,(-2147483647-1),2147483647};
    for (unsigned i=0;i<64;++i) { values[8+2*i]=1UL<<i;values[9+2*i]=~(1UL<<i); }
    unsigned long pairs=0;
    for(int v=0;v<2;++v)for(unsigned a=0;a<136;++a)for(unsigned cpu=0;cpu<9;++cpu)for(int m=0;m<2;++m){
        struct process_vm *vm=v?&vm_storage:0;
        unsigned long input=values[a], original_input=input;
        mutate=m;calls=invalid=0;
        original_remote_flush_tlb_cpumask(vm,input,cpus[cpu]);
        CHECK(calls==1 && !invalid && input==original_input);
        struct snapshot old=seen;
        calls=invalid=0;
        remote_flush_tlb_cpumask(vm,input,cpus[cpu]);
        CHECK(calls==1 && !invalid && input==original_input);
        CHECK(old.vm==seen.vm && old.value==seen.value && old.nr==seen.nr && old.cpu==seen.cpu && old.aligned==seen.aligned);
        CHECK(seen.vm==vm && seen.value==input && seen.nr==1 && seen.cpu==cpus[cpu] && seen.aligned);
        ++pairs;
    }
    CHECK(pairs==4896);
    printf("PASS actual_original_C_Rust_single_entry_pairs=%lu caller_args=3 callee_args=4 one_call=1 initialized_local_lifetime=1 caller_value_preserved=1 NO_TLB_IRQ_OR_NATIVE_EXECUTION\\n",pairs);
    return 0;
}
'''
write(F/'actual_original_vs_single.c',harness)
selected='#ifndef MCKERNEL_RUST_MEM_HELPERS\n'+original+'\n#endif /* C fallback; default Rust single-address entry. */\n'
assert selected in newc
write(F/'actual_single_selection.c',headers+selected)
abi=headers+'''_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_cpumask),void(*)(struct process_vm*,unsigned long,int)),"actual single-entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&remote_flush_tlb_array_cpumask),void(*)(struct process_vm*,unsigned long*,int,int)),"actual array-entry ABI");
_Static_assert(sizeof(unsigned long)==8 && _Alignof(unsigned long)==8 && sizeof(int)==4,"actual x86_64 scalar ABI");
const unsigned long M14_C_SINGLE_ABI[5]={
 sizeof(int),sizeof(unsigned long),_Alignof(unsigned long),sizeof(struct process_vm*),sizeof(unsigned long*)
};
'''
write(F/'actual_single_header_abi.c',abi)
# Reuse accepted object decoder as-is, not another bespoke ELF implementation.
decoder_file=B/'fixture/observe_actual_artifacts.py';tree=ast.parse(decoder_file.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='object_words');decoder=ast.get_source_segment(decoder_file.read_text(),fn)
observer='''# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,struct
P=Path(__file__).resolve().parent.parent;O=P/'output-1'
'''+decoder+'''
def rows(name):return [line.split() for line in (P/'actual-owned-capture-1'/name/'stdout').read_text().splitlines() if line.split()]
def selected(rs,n):return [r for r in rs if r[-1]==n]
r=rows('07-Rust-symbols');s=rows('08-selected-C-symbols');f=rows('09-fallback-C-symbols');p=rows('13-actual-consumer-partial-symbols')
single='remote_flush_tlb_cpumask';array='remote_flush_tlb_array_cpumask'
assert len(selected(r,single))==1 and selected(r,single)[0][-2]=='T'
assert len(selected(r,array))==1 and selected(r,array)[0][-2]=='U'
assert not selected(s,single)
assert len(selected(f,single))==1 and selected(f,single)[0][-2]=='T'
assert len(selected(f,array))==1 and selected(f,array)[0][-2]=='U'
assert len(selected(p,single))==1 and selected(p,single)[0][-2]=='T'
assert not any(x[-2]=='U' for x in selected(p,single))
assert len(selected(p,'x86_pt_split_flush_bridge'))==1
a=object_words(O/'header-abi.o','M14_C_SINGLE_ABI',5);b=object_words(O/'single-entry.o','M14_RUST_SINGLE_ABI',5);assert a==b==(4,8,8,8,8)
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_SINGLE_ENTRY_LEAF_ABI_FALLBACK_AND_RETAINED_ACTUAL_C_CONSUMER_PARTIAL_LINK_ONLY',actual_ABI_words=5,actual_ABI=a,Rust_entry_one_T=True,Rust_array_callee_U_expected_leaf_only=True,selected_C_entry_excluded=True,fallback_C_entry_preserved=True,actual_C_pt_split_consumer_scalar_U_resolved_by_Rust=True,whole_current_C_mem_TU=False,whole_production_Rust=False,default_kernel_link=False,native=False)
(P/'ACTUAL-ABI-CONSUMER-OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
'''
write(F/'observe_actual_artifacts.py',observer);ast.parse(observer)
prior=B/'SOURCE-AND-FIXTURE-PREPARATION.json';old=json.loads(prior.read_text());base=old['C_header_base']
T=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-top-log/selected-production-consumer-1');AR=T/'actual-owned-capture-1/ACTUAL-WHOLE-JOIN.json';accepted=json.loads(AR.read_text());obj=accepted['artifacts']['memory.c.o']
st=Path(obj['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(obj['device'],obj['inode'],obj['size'],obj['mtime_ns'],obj['ctime_ns'])
for pinfile in [T/'actual-owned-capture-1/4/stdout',T/'actual-owned-capture-1/5/stdout']:assert pinfile.is_file()
nmtext=(T/'actual-owned-capture-1/4/stdout').read_text();assert any(x.split()==['U','remote_flush_tlb_cpumask'] for x in nmtext.splitlines())
consumer=fun((R/'arch/x86_64/kernel/memory.c').read_text(),'static void x86_pt_split_flush_bridge(')
assert 'remote_flush_tlb_cpumask(vm, (intptr_t)addr, cpu_id);' in consumer
rustc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';O=P/'output-1';commands=[]
def cmd(name,argv):commands.append(dict(name=name,argv=argv,purpose='Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Focused wrapper ABI or inert ELF metadata only, never TLB/IRQ/kernel execution.'))
cmd('00-Rust-actual-single-export-compile',[rustc,'--edition=2021','--crate-type=lib','--emit=obj='+str(O/'single-entry.o'),'-C','opt-level=2','-C','panic=abort','-C','codegen-units=1',str(F/'actual_single_export.rs')])
cmd('01-C-original-single-recorder-compile',base+['-c',str(F/'actual_original_vs_single.c'),'-o',str(O/'recorder.o')])
cmd('02-single-C-Rust-recorder-link',[base[0],'-no-pie',str(O/'recorder.o'),str(O/'single-entry.o'),'-o',str(O/'fixture')])
cmd('03-functional-original-C-Rust-single-pairs',[str(O/'fixture')])
cmd('04-selected-C-single-region-compile',base+['-DMCKERNEL_RUST_MEM_HELPERS','-c',str(F/'actual_single_selection.c'),'-o',str(O/'selected-c.o')])
cmd('05-fallback-C-single-region-compile',base+['-c',str(F/'actual_single_selection.c'),'-o',str(O/'fallback-c.o')])
cmd('06-actual-single-header-ABI-compile',base+['-c',str(F/'actual_single_header_abi.c'),'-o',str(O/'header-abi.o')])
for num,name,file in [(7,'Rust-symbols','single-entry.o'),(8,'selected-C-symbols','selected-c.o'),(9,'fallback-C-symbols','fallback-c.o')]:cmd('%02d-'%num+name,['/usr/bin/nm','-a',str(O/file)])
cmd('10-Rust-entry-ELF',['/usr/bin/readelf','-SWrs',str(O/'single-entry.o')])
cmd('11-retained-actual-C-consumer-relocations',['/usr/bin/readelf','-rW',obj['path']])
cmd('12-actual-C-consumer-Rust-entry-partial-link',['/usr/bin/ld','-r',obj['path'],str(O/'single-entry.o'),'-o',str(O/'partial.o')])
cmd('13-actual-consumer-partial-symbols',['/usr/bin/nm','-a',str(O/'partial.o')])
cmd('14-actual-ABI-consumer-observer',['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'observe_actual_artifacts.py')])
record=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_SINGLE_TLB_ENTRY_SOURCE_READY_NOT_COMPILED',preimages={k:pin(R/k) for k in ['kernel/mem.c','kernel/rust/mem_helpers.rs']},postimages={k:pin(C/k) for k in ['kernel/mem.c','kernel/rust/mem_helpers.rs']},patch=pin(P/'PRIVATE-SINGLE-TLB-ENTRY.patch'),prior_root_array_integration_sha256='681464e66c5d316d34281eac34a577a5795b533dee8196312e265e549eb503cb',original_C_body=original,new_Rust_body=entry,existing_array_entry_unchanged_sha256=hashlib.sha256(fun(rs,array_marker).encode()).hexdigest(),existing_array_body_unchanged_sha256=hashlib.sha256(fun(rs,body_marker).encode()).hexdigest(),actual_default_selection=dict(path=pin(R/'kernel/CMakeLists.txt'),macro='MCKERNEL_RUST_MEM_HELPERS'),actual_header=pin(R/'lib/include/ihk/mm.h'),actual_Rust_ABI=pin(R/'kernel/rust/abi.rs'),actual_C_consumer=dict(source=pin(R/'arch/x86_64/kernel/memory.c'),body=consumer,line=2134,retained_complete_GCC9_receipt=pin(AR),retained_object_not_rehashed=obj,retained_NM=pin(T/'actual-owned-capture-1/4/stdout'),retained_relocations=pin(T/'actual-owned-capture-1/5/stdout')),fixture_sources={q.name:pin(q) for q in F.iterdir()},prior_accepted_header_profile=pin(prior),header_config_closure=old['header_config_closure'],proposed_profile=dict(CPU='ROOT_ASSIGN',jobs=1,AS=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152),tools={t:pin(Path(t)) for t in [rustc,base[0],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld','/home/holden/anaconda3/bin/python3']},commands=commands,planned_pairs=4896,planned_ABI_words=5,compiler_jobs=0,test_jobs=0,canonical_writes=0,source_profile_qualification='Reuses acceptedRust1.92/GCC9leaf+realheader profile. ExistingactualdefaultCconsumer object is reused statbound; not newwholeCmemTU/fullRust/GCC14/defaultkernel/native proof.',debt='All13nearbyCcallbacks/data unchanged and explicitCdebt. The Csinglewrapper fallback remainsreferenceonly; no fullfile or native retirement claim. Arrayentry/body/callbacklocks/order/completion unchanged.',failure_history='Newsingleentrycandidate source-only firstcandidate. Allprior remote-array captureimports/kernelmemset/ELFnamespace failures+expert corrections retained unchanged. Rootmanages onefailedcandidate+oneboundedcorrectionthenexpert; no familyreset.')
write(P/'EXACT-SINGLE-ENTRY-RECIPE.NOT-EXECUTED.json',json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(patch=pin(P/'PRIVATE-SINGLE-TLB-ENTRY.patch'),postimages=record['postimages'],recipe=pin(P/'EXACT-SINGLE-ENTRY-RECIPE.NOT-EXECUTED.json'),commands=len(commands))))
