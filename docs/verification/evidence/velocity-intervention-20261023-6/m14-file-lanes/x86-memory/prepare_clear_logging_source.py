"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only range/effect logging providers over private PTfree. No executable queue.
"""
from pathlib import Path
import difflib, hashlib, json, re
B=Path(__file__).resolve().parent
S=B/'next-pt-free-source-only-1/candidate'
ACCEPTED=B/'passed-six-provider-current-union-production-preparation-1/source'
P=B/'next-clear-logging-source-only-1'
def ref(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as out:out.write(s)
def body(s,name):
    m=re.search(r'(?m)^static void '+name+r'\([^;]+?\)\s*\{',s);assert m
    i=s.index('{',m.start())+1;depth=1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[m.start():i]
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text();accepted=(ACCEPTED/'arch/x86_64/kernel/memory.c').read_text()
assert ref(cp)['sha256']=='63d13923395767d80b0d219140bd97f28b6feec84fad02554760de51f5d07c5c'
assert ref(rp)['sha256']=='6e8e21f3dae7ef5f3e02bd2df486ccb10e244856ec860572d73289cbd21f2e5d'
effect='x86_clear_effect_log_bridge';ran='x86_clear_range_log_bridge'
e=body(c,effect);rr=body(c,ran)
assert e==body(accepted,effect) and rr==body(accepted,ran)
events=[('free_anon','X86_CLEAR_EFFECT_FREE_ANON'),('xpmem_keep','X86_CLEAR_EFFECT_XPMEM_KEEP'),('free_unmapped','X86_CLEAR_EFFECT_FREE_UNMAPPED'),('child_free','X86_CLEAR_EFFECT_CHILD_FREE')]
line_data={};declarations=[]
for fn,old,spec in [(effect,e,events),(ran,rr,[('large_phys','X86_CLEAR_RANGE_LOG_LARGE_PHYS')])]:
    start=accepted[:accepted.index(old)].count('\n')+1
    decl=[]
    for suffix,event in spec:
        # Every selected event has exactly one original dkprintf macro site.
        pos=old.index('dkprintf(',old.index('case '+event+':'))
        line=start+old[:pos].count('\n')
        name=('x86_clear_effect_' if fn==effect else 'x86_clear_range_')+suffix+'_debug'
        line_data[name]=dict(function=fn,event=event,line=line,function_start=start)
        decl.append(f'''struct ddebug __aligned(8) __attribute__((section("__verbose")))
{name} = {{
    .file = __FILE__, .func = "{fn}", .fmt = NULL,
    .line = {line}, .flags = DDEBUG_DEFAULT,
}};
''')
        declarations.append('    static mut '+name+': crate::debug::Ddebug;\n')
    signature=old[:old.index('\n{')].replace('static void','extern void',1)+';'
    selection='#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+signature+'\n'+''.join(decl)+'#else\n#line '+str(start)+'\n'+old+'\n#endif\n#line @RESTORE@'
    assert c.count(old)==1;c=c.replace(old,selection,1)
    restore=c[:c.index('#line @RESTORE@')].count('\n')+2
    c=c.replace('@RESTORE@',str(restore),1)
# The first inserted source-only provider precedes the second. Its saved numeric
# restore directive still names its actual physical following line; both sites
# are anchored independently to the accepted complete GCC9 source callsites.
anchor='    fn kprintf(format: *const i8, ...) -> CInt;\n'
assert r.count(anchor)==1;r=r.replace(anchor,anchor+''.join(declarations),1)
r+='''
// Declarative C debug selectors keep the original file/function/line ABI. The
// flag byte may be changed through the existing debug control path; any nonzero
// byte enables its own original callsite, matching dkprintf (not just bit 0).
#[no_mangle]
pub unsafe extern "C" fn x86_clear_effect_log_bridge(
    event: CInt, base: CULong, phys: CULong, pgsize: SizeT,
) {
    unsafe {
        match event {
            X86_CLEAR_EFFECT_FREE_ANON => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_free_anon_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx-,%s: freed anonymous page,base=%lx,size=%ld,pgsize=%ld\\n\\0".as_ptr().cast(),
                        phys, b"x86_clear_effect_log_bridge\\0".as_ptr().cast::<i8>(), base, pgsize, pgsize,
                    );
                }
            }
            X86_CLEAR_EFFECT_XPMEM_KEEP => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_xpmem_keep_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: XPMEM attach,phys=%lx\\n\\0".as_ptr().cast(),
                        b"x86_clear_effect_log_bridge\\0".as_ptr().cast::<i8>(), phys);
                }
            }
            X86_CLEAR_EFFECT_FREE_UNMAPPED => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_free_unmapped_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx-,%s: freed unmapped memobj page,base=%lx,size=%ld,pgsize=%ld\\n\\0".as_ptr().cast(),
                        phys, b"x86_clear_effect_log_bridge\\0".as_ptr().cast::<i8>(), base, pgsize, pgsize,
                    );
                }
            }
            X86_CLEAR_EFFECT_CHILD_FREE => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_child_free_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: freed child page table at base=%lx,size=%ld\\n\\0".as_ptr().cast(),
                        b"x86_clear_effect_log_bridge\\0".as_ptr().cast::<i8>(), base, pgsize);
                }
            }
            _ => {}
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_log_bridge(
    event: CInt, args: *mut c_void, ptep: *mut CULong, base: CULong,
    start: CULong, end: CULong, error: CInt, level_shift: CInt, phys: CULong,
) {
    let name = match level_shift {
        PTL2_SHIFT => b"clear_range_l2\\0".as_ptr().cast::<i8>(),
        PTL3_SHIFT => b"clear_range_l3\\0".as_ptr().cast::<i8>(),
        _ => b"clear_range_l4\\0".as_ptr().cast::<i8>(),
    };
    unsafe {
        match event {
            X86_CLEAR_RANGE_LOG_SPLIT => {
                let _ = kprintf(b"%s(%p,%p,%lx,%lx,%lx):split page. %d\\n\\0".as_ptr().cast(),
                    name, args, ptep, base, start, end, error);
            }
            X86_CLEAR_RANGE_LOG_LARGE_PHYS => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_range_large_phys_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: phys=%ld, pte_get_phys(&old),PTL3_SIZE\\n\\0".as_ptr().cast(), name, phys);
                }
            }
            _ => {}
        }
    }
}
'''
for name in [effect,ran]:assert r.count('fn '+name+'(')==1
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',cp.read_text(),c),('kernel/rust/x86_memory_helpers.rs',rp.read_text(),r)]:
    put(P/'candidate'/rel,after)
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-CLEAR-LOGGING-SOURCE.patch',patch)
put(P/'EXACT-ORIGINAL-EFFECT-LOG.inc',e+'\n')
put(P/'EXACT-ORIGINAL-RANGE-LOG.inc',rr+'\n')
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only. Existing complete selected GCC9 header/config flags.
 */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&{effect}),x86_clear_effect_log_fn_t),"actual complete effect logger ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&{ran}),x86_clear_range_log_fn_t),"actual complete range logger ABI");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual descriptor ABI");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"actual debug pointer fields");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"retained immutable effect identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"retained immutable range identity");
#endif
''')
# Concrete host-reference recorder fragment; the original C bodies may retain
# their C names/__FUNCTION__ using prior static declarations with distinct asm
# labels. This does not create a driver, recipe or runnable cohort.
put(P/'FUTURE-VARARG-RECORDER-FRAGMENT.NOT-QUEUED.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source only: actual original C provider vs exact Rust provider; same formatter.
 */
#include <stdarg.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
static unsigned record_calls;
static char record_text[1024];
int kprintf(const char *format,...)
{
    va_list ap; va_start(ap,format);
    ++record_calls;
    int ret=vsnprintf(record_text,sizeof(record_text),format,ap);
    va_end(ap); assert(ret>=0 && (unsigned)ret<sizeof(record_text)); return ret;
}
/* Exact original static C definitions keep their __FUNCTION__ spelling; asm
 * label changes only the object symbol, allowing Rust globals in the same ELF.
 */
static void x86_clear_effect_log_bridge(int,unsigned long,unsigned long,size_t)
    __asm__("original_C_effect_log");
static void x86_clear_range_log_bridge(int,void*,unsigned long*,unsigned long,
    unsigned long,unsigned long,int,int,unsigned long)
    __asm__("original_C_range_log");
/* Include the two source-bound original-body .inc files using numeric #line
 * anchors before their definitions. Reference calls from this translation unit
 * name the original static C functions; exported fixture callers can select the
 * Rust globals through their distinct symbol names in a second translation unit.
 * Iterate actual __verbose entries by real file/function/line; set each original
 * and displaced descriptor's flag byte together for 0,1,2,128,255. Compare the
 * calls and exact record_text. Also vary each unrelated selector independently.
 * Cover every known/unknown event; levels21/30/other, signed32 errors, raw pointer
 * bits and high unsigned64 base/phys/size bits. No page or object is dereferenced.
 * This recorder proves logger argument/string/selection behavior, not the native
 * kernel formatter or debug-control synchronization.
 */
''')
info=dict(scope=__doc__,status='COMPLETE_TWO_LOGGING_PROVIDER_SOURCE_ONLY_NOT_TESTED',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-CLEAR-LOGGING-SOURCE.patch'),descriptor_callsite_basis=ref(ACCEPTED/'arch/x86_64/kernel/memory.c'),five_original_descriptor_sites=line_data,descriptor_semantics='Actual mutable32B/align8 C ddebug objects in __verbose: file __FILE__, original function spelling, original accepted macro line, fmt NULL, flags DDEBUG_DEFAULT. No new C function/getter. Each Rust event reads only its own flags byte via established volatile32 line_flags >>24; any nonzero byte enables it.',format_and_vararg_semantics='Exact literal bytes/argument order, CInt error/event, raw args/ptep, unsigned64 base/start/end/phys and SizeT pgsize preserved. Original signed-format/unsigned-argument bit behavior preserved; no printf counter or return propagation. Split always prints; large-phys/effect sites obey separate selectors; unknown events no output.',fallback='Both original C function bodies are byte-identical. Numeric-only #line anchors retain accepted callsite selector lines, then resume actual following physical lines. __FILE__ remains compilation-unit source path, never a baked private path.',lifetime='No pointer dereference, lock, page free/accounting, page reference, callback retention or borrowed reference crosses the logger call; strings have static lifetime. Existing effect and traversal order untouched.',Rust_reuse='Existing kprintf production ABI and crate::debug::Ddebug; no logging model in product.',callback_identity='Existing typed const x86_clear_l3_effect_log/range_log remain byte-identical; future whole-TU allocated section-aware relocations must target the new unique Rust globals, not local C bodies.',PTfree_state='Prior816af238 source-only fields/line807 retained; no PTfree fixture/TU credit.',new_driver_queue_CPU_reservation=None,actual_fixture_TU_partial_default_native=None,already_held_residuals_ranked_with_uncertainty=[dict(rank='highest ownership uncertainty',body='PTfree/allocator backing providers',reuse='Existing Rust tracked allocator; private wrapper source prepared, metadata/real allocation-chain proof pending'),dict(rank='moderate tracing/ABI uncertainty',body='range/effect log providers',reuse='Existing Rust logger/debug descriptor ABI; these complete source ports need actual output/selector/vararg/relocation proof'),dict(rank='small wrapper, untested',body='PT physical translator',reuse='Existing actual Rust phys_to_virt; separate a914/3fc source excluded'),dict(rank='separate allocator/error boundary',body='x86_pt_alloc_pages_bridge and destroy panic callbacks',reuse='Existing allocator helpers and Rust panic; C bodies still live')],engineering_percentage=None,defaultlink_native='Six passed provider batch has current78/GCC9/partial proof only; defaultGCC14/finalimage/native remain OPEN. New PTfree/logging ports have SOURCE proof only.',next_body='x86_pt_alloc_pages_bridge: retain actual allocation flags/error/page ownership; no new inventory required.',canonical_Git_sharedABI_P12_changes=False)
put(P/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json',json.dumps(info,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-CLEAR-LOGGING-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json'),postimages=info['postimages'],patch=info['patch'],original_descriptor_sites=line_data)))
