"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only allocator callback cutover and bounded original-C/Rust observer recipe.
"""
from pathlib import Path
import ast, copy, difflib, hashlib, json, re
B=Path(__file__).resolve().parent
BASE=B/'next-clear-logging-source-only-1/candidate'
P=B/'next-pt-alloc-source-only-1'
ROOT=Path('/home/holden/mckernel')
def ref(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as out:out.write(s)
def rec(p,d):put(p,json.dumps(d,indent=2,sort_keys=True)+'\n')
assert not P.exists()
cp=BASE/'arch/x86_64/kernel/memory.c';rp=BASE/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text()
assert ref(cp)['sha256']=='564f786adabfc9f0e6d3593ff734b19afc622e4d6c691f11c3995e061a83f220'
assert ref(rp)['sha256']=='2d96bc6a916387cbe896f4f80e64d2dab45047ba920c4a90c2fad993144a1d54'
old='''X86_MEMORY_PUBLIC_BRIDGE void *x86_pt_alloc_pages_bridge(int nr_pages, int ap_flag)
{
	return _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, (ihk_mc_ap_flag)ap_flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}'''
assert c.count(old)==1 and old in (ROOT/'arch/x86_64/kernel/memory.c').read_text()
line=c[:c.index(old)].count('\n')+1;call=line+2
assert (line,call)==(748,750)
selection=f'''#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
/* Original allocator trace callsite and real C geometry, data only. */
const char x86_pt_alloc_pages_file[] = __FILE__;
const int x86_pt_alloc_pages_line = {call};
const int x86_pt_alloc_pages_p2align = PAGE_P2ALIGN;
const int x86_pt_alloc_pages_is_user = IHK_MC_PG_KERNEL;
#else
#line {line}
{old}
#endif
#line @RESTORE@
'''.rstrip()
nc=c.replace(old,selection,1)
nc=nc.replace('@RESTORE@',str(nc[:nc.index('#line @RESTORE@')].count('\n')+2),1)
# Adding this earlier provider moves subsequent physical source lines. Preserve
# each already-source-bound fallback anchor, but rebase only post-#endif resume
# directives to the new physical position (including PTfree807/debug selectors).
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
# Resume directives end at the numeric token, not its following newline.
for m in re.finditer(r'(?m)#endif\n#line ([0-9]+)',nc):
    assert int(m.group(1))==nc[:m.end()].count('\n')+2
foreign='    fn x86_pt_alloc_pages_bridge(nr_pages: CInt, ap_flag: CInt) -> *mut c_void;\n'
assert r.count(foreign)==1
declarations='''    fn _ihk_mc_alloc_aligned_pages_node(npages: CInt, p2align: CInt, flag: CULong, node: CInt, is_user: CInt, virt_addr: CULong, file: *mut i8, line: CInt) -> *mut c_void;
    static x86_pt_alloc_pages_file: [i8; 1];
    static x86_pt_alloc_pages_line: CInt;
    static x86_pt_alloc_pages_p2align: CInt;
    static x86_pt_alloc_pages_is_user: CInt;
'''
nr=r.replace(foreign,declarations,1)
port='''#[no_mangle]
pub unsafe extern "C" fn x86_pt_alloc_pages_bridge(nr_pages: CInt, ap_flag: CInt) -> *mut c_void {
    unsafe {
        _ihk_mc_alloc_aligned_pages_node(
            nr_pages, x86_pt_alloc_pages_p2align, ap_flag as CULong,
            -1, x86_pt_alloc_pages_is_user, CULong::MAX,
            core::ptr::addr_of!(x86_pt_alloc_pages_file).cast::<i8>() as *mut i8,
            x86_pt_alloc_pages_line,
        )
    }
}
'''
nr+='\n// Retain the C int->unsigned-long conversion, tracked allocation, and raw result.\n'+port
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
    put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-PT-ALLOC-SOURCE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n')
abi=B/'passed-six-provider-current-union-production-preparation-1/source/kernel/rust/abi.rs'
fixture='''#![no_std]
#![allow(dead_code,unused_imports)]
'''+f'#[path="{abi}"] mod abi;\n'+'''use abi::{CInt,CULong};
use core::ffi::c_void;
unsafe extern "C" {
'''+declarations+'}\n'+port
put(P/'fixture.rs',fixture)
mm=(ROOT/'lib/include/ihk/mm.h').read_text();arch=(ROOT/'arch/x86_64/kernel/include/arch-memory.h').read_text()
types='\n'.join([next(x for x in mm.splitlines() if x=='typedef unsigned long ihk_mc_ap_flag;'),next(x for x in arch.splitlines() if x.startswith('#define PAGE_P2ALIGN ')),next(x for x in mm.splitlines() if x.startswith('#define IHK_MC_PG_KERNEL '))])+'\n'
put(P/'EXACT-REAL-HEADER-TYPE-CLOSURE.inc',types)
fc='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled downstream allocator endpoint proves the wrapper, not allocation.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "EXACT-REAL-HEADER-TYPE-CLOSURE.inc"
#define X86_MEMORY_PUBLIC_BRIDGE static
extern void *x86_pt_alloc_pages_bridge(int,int);
const char x86_pt_alloc_pages_file[] = __FILE__;
const int x86_pt_alloc_pages_line = 750;
const int x86_pt_alloc_pages_p2align = PAGE_P2ALIGN;
const int x86_pt_alloc_pages_is_user = IHK_MC_PG_KERNEL;
static struct observed { int pages,align; unsigned long flag; int node,user;
    uintptr_t virt; char *file; int line; } last;
static unsigned calls;
static void *backend_result;
void *_ihk_mc_alloc_aligned_pages_node(int n,int a,ihk_mc_ap_flag f,int node,
                                     int user,uintptr_t v,char *file,int line)
{
    ++calls; last=(struct observed){n,a,f,node,user,v,file,line}; return backend_result;
}
'''
fc+='#line '+str(line)+'\n'+old.replace('x86_pt_alloc_pages_bridge(', 'original_x86_pt_alloc_pages_bridge(',1)+'\n'
fc+='''static unsigned char owned_by_observer[8192] __attribute__((aligned(4096)));
int main(void)
{
    static const int pages[]={INT_MIN,-2,-1,0,1,2,8,511,INT_MAX};
    static const int flags[]={INT_MIN,-65536,-2,-1,0,1,2,4,0x1000,0x30000,0x40000,INT_MAX,0x5a5a5a5a};
    void *results[]={NULL,owned_by_observer,owned_by_observer+4096,(void*)(uintptr_t)UINTPTR_MAX};
    unsigned pairs=0;
    for(unsigned i=0;i<sizeof(pages)/sizeof(pages[0]);++i)
      for(unsigned j=0;j<sizeof(flags)/sizeof(flags[0]);++j)
        for(unsigned k=0;k<sizeof(results)/sizeof(results[0]);++k) {
            backend_result=results[k]; unsigned before=calls;
            void *old=original_x86_pt_alloc_pages_bridge(pages[i],flags[j]);
            struct observed expected=last;
            assert(calls==before+1);
            void *actual=x86_pt_alloc_pages_bridge(pages[i],flags[j]);
            assert(calls==before+2 && actual==old && actual==backend_result);
            assert(last.pages==expected.pages && last.align==expected.align);
            assert(last.flag==expected.flag && last.node==expected.node && last.user==expected.user);
            assert(last.virt==expected.virt && strcmp(last.file,expected.file)==0 && last.line==expected.line);
            assert(last.pages==pages[i] && last.align==0 && last.flag==(ihk_mc_ap_flag)flags[j]);
            assert(last.node==-1 && last.user==0 && last.virt==UINTPTR_MAX && last.line==750);
            assert(last.file==x86_pt_alloc_pages_file); ++pairs;
        }
    assert(pairs==468);
    puts("PASS PT allocator wrapper:468 actual-original-C/Rust pairs; flags, trace, NULL/raw result; downstream controlled");
    return 0;
}
'''
put(P/'fixture.c',fc)
realabi=f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_alloc_pages_bridge),x86_pt_alloc_pages_fn_t),"existing complete allocation callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),void*(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char*,int)),"real tracked allocator ABI");
_Static_assert(__builtin_types_compatible_p(ihk_mc_ap_flag,unsigned long) && sizeof(ihk_mc_ap_flag)==8,"C signed32 to unsigned64 conversion");
_Static_assert(PAGE_P2ALIGN==0 && IHK_MC_PG_KERNEL==0 && sizeof(int)==4 && sizeof(uintptr_t)==8,"actual geometry/constants");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(sizeof(x86_pt_alloc_pages_line)==4 && sizeof(x86_pt_alloc_pages_p2align)==4 && sizeof(x86_pt_alloc_pages_is_user)==4,"metadata ABI");
#endif
'''
put(P/'real-header-ABI.c',realabi)
leaf=json.loads((B/'batch-walkers-rss-flush-fixture-preparation-1/BATCH-FIXTURE-FINAL-RECIPE.NOT-EXECUTED.json').read_bytes())
rustc=leaf['commands'][0]['argv'][0]
commands=[dict(label='Rust-alloc',argv=[rustc,'--edition=2021','--crate-name','m14_pt_alloc_wrapper','--crate-type=lib','--emit=obj','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort','fixture.rs','-o','fixture-alloc.o'],cwd=str(P)),dict(label='GCC-link-alloc',argv=['/usr/bin/gcc-9','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections','fixture.c','fixture-alloc.o','-Wl,--gc-sections','-o','fixture-alloc'],cwd=str(P)),dict(label='execute-alloc',argv=[str(P/'fixture-alloc')],cwd=str(P)),dict(label='symbols-alloc',argv=['/usr/bin/nm','-a',str(P/'fixture-alloc')],cwd=str(P))]
for name,public in [('real-ABI-PUBLIC',True),('real-ABI-fallback',False)]:
    oldcmd=next(x for x in leaf['commands'] if x['label']==name)
    argv=oldcmd['argv'][:];argv[-1]=str(P/'real-header-ABI.c')
    commands.append(dict(label=name,argv=argv,cwd=str(P)))
for x in commands:x['purpose']=__doc__+' '+x['label']
sources=[ref(P/x) for x in ['fixture.rs','fixture.c','EXACT-REAL-HEADER-TYPE-CLOSURE.inc','real-header-ABI.c','EXACT-ORIGINAL-C-PROVIDER.inc','candidate/arch/x86_64/kernel/memory.c','candidate/kernel/rust/x86_memory_helpers.rs']]+[ref(abi),ref(ROOT/'lib/include/ihk/mm.h'),ref(ROOT/'arch/x86_64/kernel/include/arch-memory.h')]
# All inherited header pins are finite accepted dependencies, not a new tree census.
for row in leaf['reused67_header_pins'].values():
    assert ref(Path(row['path']))['sha256']==row['sha256'],row['path']
recipe=dict(scope=__doc__,commands=commands,profile=dict(leaf['profile'],OS_stack_bytes=2097152),sources=sources,reused67_header_pins=leaf['reused67_header_pins'],expected_stdout={'execute-alloc':'PASS PT allocator wrapper:468 actual-original-C/Rust pairs; flags, trace, NULL/raw result; downstream controlled\n'},expected_actual_pairs={'allocator_wrapper':468},expected_unique_ELF_Rust_T=['x86_pt_alloc_pages_bridge'],qualification='Exact extracted product function and actual ABI aliases; controlled downstream endpoint. Not the actual tracked allocator/fullcrate/physical ownership/default/native proof.',actual_outputs=None,execution_grant=None)
R=P/'ALLOCATOR-FIXTURE-RECIPE.NOT-EXECUTED.json';rec(R,recipe)
# Reuse the successful batch CWD correction/capture loop, not a new framework.
d=(B/'batch-walkers-rss-flush-fixture-preparation-1/run_actual_once.CWD-CORRECTION.NOT-RELEASED.py').read_text()
d=d.replace('BATCH-FIXTURE-FINAL-RECIPE.NOT-EXECUTED.json',R.name).replace('50eb9bf22f54bc3ecc08f4278befaef363285eb508df88b17a2309fba1e37805',ref(R)['sha256'])
d=d.replace(str(B/'batch-walkers-rss-flush-fixture-preparation-1'),str(P))
d=d.replace("r['sources'] + r['product_sources'] + r['actual_module_inputs'] + r['actual_header_inputs'] + list(r['reused67_header_pins'].values()) + [r['actual_debug_type_input']]","r['sources'] + list(r['reused67_header_pins'].values())")
d=d.replace("('fixture-on.o', 'fixture-off.o', 'fixture-on', 'fixture-off')","('fixture-alloc.o', 'fixture-alloc')").replace('actual-batch-attempt-2-cwd-correction-1','actual-allocator-attempt-1')
d=d.replace('PASS_ACTUAL_SIX_PROVIDER_C_RUST_BATCH_AND_REAL_ABI','PASS_ACTUAL_PT_ALLOCATOR_WRAPPER_468_PAIRS_AND_REAL_ABI')
d=d.replace('on_off_total_pairs=937','allocator_wrapper_pairs=468').replace("actual_tested_ports=['walkL1','walkL2','walkL3','RSS','memobjRSS','memobjFlush']","actual_tested_ports=['x86_pt_alloc_pages_bridge']")
d=d.replace("accounting_and_memobj_dispatch_bodies='Actual existing Rust modules; only two unrelated export names are fixture-namespaced, with original bodies preserved.',lower_C_provider_qualification=r['remaining_C_providers']","controlled_downstream_allocator=True,qualification=r['qualification']")
d=d.replace('ACTUAL-SIX-PROVIDER-BATCH-RECEIPT.json','ACTUAL-ALLOCATOR-WRAPPER-RECEIPT.json').replace('actual_pairs=937','actual_pairs=468')
ast.parse(d)
D=P/'run_actual_once.NOT-RELEASED.py';put(D,d)
info=dict(scope=__doc__,status='SOURCE_IMPLEMENTATION_AND_SINGLE_LEAF_RECIPE_READY_NOT_RELEASED',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-PT-ALLOC-SOURCE.patch'),recipe=ref(R),driver=ref(D),argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(D)],source_original_allocation_line=750,C_fallback_body_byte_identical=True,existing_PTfree_and_logging_trace_anchors_retained=True,subsequent_physical_resume_directives_rebased_only=True,actual_trace_file='C __FILE__ static metadata; no Rust file!()/line!() replacement',flag_conversion='CInt as CULong directly, including negative values modulo2^64; no intermediate u32/zero-extension',allocation_semantics='One existing Rust tracked-allocator ABI call. Exact count/alignment/flag/node-1/kernel0/virtULONG_MAX/file/line750. Propagate NULL and every raw return unchanged; no zeroing, free, rollback, refcount, second allocation, lock, validation or panic added.',ownership='Existing tracked allocator/provider chain retains allocation, tracking, early-allocation, failure and ownership policy. Wrapper returns ownership/result exactly as original; controlled leaf backend does not prove real allocation.',actual_fixture_outputs=None,actual_production_GCC14_default_native=None,execution_grant=None,CPU_reservation=None,failure_history='Retain first937CWD338e and successful bounded correction7b799; no replay of old tests; first unexpected new execution STOP/expert.',held_residuals='PTfree/logger sources still need executable proof; untested phys translator stays separate. Known next error callback: x86_pt_destroy_panic_bridge using existing Rust panic. Higher difficulty remains allocator backing/page ownership; logging selector and metadata verification moderate; translator/error wrapper narrower. No new inventory.',engineering_percentage=None)
rec(P/'SOURCE-ALLOCATOR-AND-EXECUTABLE-HANDOFF.NOT-RELEASED.json',info)
print(json.dumps(dict(handoff=ref(P/'SOURCE-ALLOCATOR-AND-EXECUTABLE-HANDOFF.NOT-RELEASED.json'),postimages=info['postimages'],patch=info['patch'],recipe=ref(R),driver=ref(D))))
