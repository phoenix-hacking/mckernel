"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only PTfree provider with the original C tracing callsite retained exactly.
No second executable cohort or compiler invocation.
"""
from pathlib import Path
import difflib, hashlib, json
B=Path(__file__).resolve().parent
S=B/'next-memobj-flush-source-only-1/candidate'
P=B/'next-pt-free-source-only-1'
ROOT=Path('/home/holden/mckernel')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p): return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as out: out.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
assert sha(cp)=='ceed123214cd293f5afefd21dd071e39aa824cf3424cc6355a841c1ae5467f39'
assert sha(rp)=='087240006b3f1b99c844c77c1c645118710bf34f53546637eb12d54215822092'
c=cp.read_text();r=rp.read_text()
old='''X86_MEMORY_PUBLIC_BRIDGE void x86_pt_free_pages_bridge(void *pt, int nr_pages)
{
	_ihk_mc_free_pages(pt, nr_pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}'''
assert c.count(old)==1
canonical=(ROOT/'arch/x86_64/kernel/memory.c').read_text()
assert old in canonical
line=c[:c.index(old)].count('\n')+1
call_line=line+2
assert line==805 and call_line==807
# Existing user-free callback already uses immutable C file/int metadata for
# the same Rust tracked allocator. PTfree must retain its own callsite instead.
# Numeric-only #line changes no __FILE__ bytes. Fallback gets its exact prior
# callsite; the following source resumes its actual physical line number.
selection=f'''#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
/* Original PTfree tracking callsite; data only, no C runtime provider. */
const char x86_pt_free_pages_file[] = __FILE__;
const int x86_pt_free_pages_line = {call_line};
const int x86_pt_free_pages_flag = IHK_MC_PG_KERNEL;
#else
#line {line}
{old}
#endif
#line @RESTORE_PHYSICAL_LINE@'''
nc=c.replace(old,selection,1)
token='#line @RESTORE_PHYSICAL_LINE@'
restore=nc[:nc.index(token)].count('\n')+2
nc=nc.replace('@RESTORE_PHYSICAL_LINE@',str(restore),1)
assert nc.splitlines()[restore-2]=='#line '+str(restore)
foreign='    fn x86_pt_free_pages_bridge(pt: *mut c_void, nr_pages: CInt);\n'
assert r.count(foreign)==1
nr=r.replace(foreign,'''    static x86_pt_free_pages_file: [i8; 1];
    static x86_pt_free_pages_line: CInt;
    static x86_pt_free_pages_flag: CInt;
''',1)
nr+='''
// Same tracked allocator used by the C provider. Static C callsite data keeps
// its original file/line/flag; no Rust file!()/line!() substitution or new policy.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_free_pages_bridge(pt: *mut c_void, nr_pages: CInt) {
    unsafe {
        _ihk_mc_free_pages(
            pt, nr_pages, x86_pt_free_pages_flag,
            core::ptr::addr_of!(x86_pt_free_pages_file).cast::<i8>() as *mut i8,
            x86_pt_free_pages_line,
        );
    }
}
'''
assert nr.count('fn x86_pt_free_pages_bridge(')==1
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
    put(P/'candidate'/rel,after)
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-PT-FREE-SOURCE.patch',patch)
put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n')
put(P/'FUTURE-REAL-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Fragment only: include the actual complete candidate C TU using accepted
 * PUBLIC flags. No new driver, argv or executable cohort.
 */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_free_pages_bridge),x86_pt_free_pages_fn_t),"exact existing PTfree callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void(*)(void*,int,int,char*,int)),"actual tracked allocator ABI");
_Static_assert(sizeof(int)==4 && sizeof(void*)==8 && IHK_MC_PG_KERNEL==0,"actual page flag and argument widths");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(sizeof(x86_pt_free_pages_line)==4 && sizeof(x86_pt_free_pages_flag)==4,"immutable tracing integer ABI");
_Static_assert(sizeof(x86_pt_free_pages_file)>1,"actual C compilation-unit path bytes");
#endif
''')
put(P/'FUTURE-CALL-TRACE-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Wrapper-only downstream recorder: explicitly does not prove actual freeing,
 * allocator locks, tracking/accounting, or physical-page ownership. The existing
 * full Rust _ihk_mc_free_pages remains the real production provider.
 * Link the exact Rust wrapper and source-derived metadata into a future isolated
 * observer (its other support modules must not also define this recorder symbol).
 */
#include <assert.h>
#include <string.h>
extern void x86_pt_free_pages_bridge(void *, int);
extern const char x86_pt_free_pages_file[];
extern const int x86_pt_free_pages_line, x86_pt_free_pages_flag;
static struct {{ void *ptr; int pages, flag; char *file; int line; }} seen;
static unsigned calls;
void _ihk_mc_free_pages(void *ptr,int pages,int flag,char *file,int line)
{{
    ++calls;
    seen.ptr=ptr; seen.pages=pages; seen.flag=flag; seen.file=file; seen.line=line;
}}
static void future_forwarding_case(void *ptr, int pages)
{{
    unsigned before=calls;
    x86_pt_free_pages_bridge(ptr,pages);
    assert(calls==before+1 && seen.ptr==ptr && seen.pages==pages);
    assert(seen.flag==x86_pt_free_pages_flag && seen.flag==0);
    assert(seen.file==x86_pt_free_pages_file && seen.line=={call_line});
    assert(x86_pt_free_pages_line=={call_line});
}}
/* Also extract original C provider using its numeric source-line anchor and
 * same C filename; compare recorder events for original and Rust. No free occurs
 * in this observer, so negative/zero count bit-forwarding is not allocator input
 * qualification. Real allocator/provider-chain proof requires the full current
 * crate/selected TU/partial link and its already-established allocator contracts.
 */
''')
info=dict(scope=__doc__,status='COMPLETE_PT_FREE_SOURCE_ONLY_NOT_TESTED',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-PT-FREE-SOURCE.patch'),original_provider=ref(P/'EXACT-ORIGINAL-C-PROVIDER.inc'),original_start_line=line,original_tracked_free_call_line=call_line,following_physical_source_line_restored=restore,metadata_ABI='Private const char[] file, const int line/flag; same established immutable data pattern as user-free. New PTfree fields have no previous compiled ABI proof. Numeric-only #line anchors preserve fallback __LINE__807 and do not change __FILE__; line control then resumes actual physical source position.',fallback_body_byte_identical=True,existing_actual_Rust_provider=dict(path=str(ROOT/'kernel/rust/mem_helpers.rs'),entry='_ihk_mc_free_pages -> pagealloc_track_free_result',authority='Current-union full78 actual six-provider production receipt859b1cb6; kernel tracked allocator implementation unchanged by this source port.'),consumer_invariants=dict(arguments='Raw ptr and signed32 page count unchanged, kernel flag from actual C macro0; no count conversion, null guard, validation, saturation or ignored-return change.',trace='C compilation-unit filename retains static lifetime; exact original line807 retained PUBLIC and fallback. No Rust file!()/line!() or private absolute filename literal in product.',order_lifetime='One synchronous call to existing tracked Rust allocator; no references, retained callback, temporary data, lock, page reference or free-operation reordering; no extra free or accounting call.',selection='PUBLIC C body absent; Rust unique global T and no self-U required. Existing Rust allocator unique T is reused; C import must be proven from actual retained callers/relocs and is not assumed.',new_data_proof='Future real-header ABI and compiler PP must establish four-byte line/flag, readonly file array, fallback anchored callsite, and matching Rust metadata U/partial providers.'),fragments=[ref(P/'FUTURE-REAL-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-CALL-TRACE-FRAGMENT.NOT-QUEUED.c')],new_driver_queue_reservation=None,actual_fixture_full78_selected_TU_partial_default_native=None,remaining_already_held_bodies=[dict(body='x86_clear_range_log_bridge / x86_clear_effect_log_bridge',reuse='existing Rust kprintf/debug descriptor ABI; exact per-event strings/dynamic-debug flags still need source port',state='C; next substantive body'),dict(body='x86_pt_phys_to_virt_bridge',reuse='existing Rust phys_to_virt',state='separate a914/3fc source only; excluded here'),dict(body='x86_pt_alloc_pages_bridge',reuse='existing allocator helpers; exact ownership/error/flag boundary remains C',state='C'),dict(body='x86_pt_destroy_panic_bridge',reuse='existing Rust panic and reason constants',state='C')],whole_file_complete=False,engineering_percentage=None,default_link_native_blockers='This PTfree port has no fixture/TU/partial proof. Passed six-provider batch has current78/GCC9/partial only; GCC14 default image and native acceptance remain OPEN.',canonical_Git_sharedABI_P12_changes=False)
put(P/'SOURCE-PT-FREE-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json',json.dumps(info,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-PT-FREE-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json'),postimages=info['postimages'],patch=info['patch'],callsite_line=call_line,restore_line=restore)))
