"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only destroy error callback; no second executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent
S=B/'next-pt-alloc-source-only-1/candidate'
P=B/'next-destroy-error-source-only-1'
def ref(f):
 b=f.read_bytes();return dict(path=str(f),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(f,s):
 f.parent.mkdir(parents=True,exist_ok=True)
 with f.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text()
old='''X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_panic_bridge(int reason)
{
	if (reason == X86_PT_DESTROY_PANIC_LEVEL) {
		panic("destroy_page_table: level is out of range");
	}
	if (reason == X86_PT_DESTROY_PANIC_NULL) {
		panic("destroy_page_table: pt is NULL");
	}
}'''
assert c.count(old)==1
nc=c.replace(old,'#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
foreign='    fn x86_pt_destroy_panic_bridge(reason: CInt);\n';assert r.count(foreign)==1
nr=r.replace(foreign,'''    // Exact existing C declaration; production symbol is the current Rust panic.
    #[link_name = "panic"]
    fn x86_memory_existing_panic(message: *const i8);
''',1)
nr+='''
// Preserve both original tests, exact diagnostic bytes, and void C panic ABI.
// The actual existing Rust panic never returns. No new unwind/panic policy is
// imposed here; if a C-ABI reference recorder returns, control matches C too.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_destroy_panic_bridge(reason: CInt) {
    unsafe {
        if reason == X86_PT_DESTROY_PANIC_LEVEL {
            x86_memory_existing_panic(b"destroy_page_table: level is out of range\\0".as_ptr().cast());
        }
        if reason == X86_PT_DESTROY_PANIC_NULL {
            x86_memory_existing_panic(b"destroy_page_table: pt is NULL\\0".as_ptr().cast());
        }
    }
}
'''
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-DESTROY-ERROR-SOURCE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n')
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_destroy_panic_bridge),x86_pt_destroy_panic_fn_t),"existing destroy error callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&panic),void(*)(const char*)),"exact existing C panic declaration");
_Static_assert(X86_PT_DESTROY_PANIC_LEVEL==1 && X86_PT_DESTROY_PANIC_NULL==2 && sizeof(int)==4,"real reason/width closure");
''')
put(P/'FUTURE-MESSAGE-RECORDER-FRAGMENT.NOT-QUEUED.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Returning endpoint is permitted by the actual void C declaration. It tests
 * callback reason/message choice only, never real panic termination/unwinding.
 */
#include <assert.h>
#include <string.h>
static unsigned panic_calls;
static const char *panic_message;
void panic(const char *s) { ++panic_calls; panic_message=s; }
static void future_reason_case(void (*original)(int),void (*rust)(int),int reason)
{
    unsigned start=panic_calls; original(reason);
    unsigned count=panic_calls-start; const char *expected=panic_message;
    rust(reason); assert(panic_calls==start+2*count);
    if(count)assert(strcmp(panic_message,expected)==0);
    assert(count==(unsigned)(reason==1 || reason==2));
}
/* Reason vectors: INT_MIN,-1,0,1,2,3,INT_MAX. Both known messages are static
 * strings; unknown reasons perform no endpoint call. Use the exact original C
 * body and exact Rust callback body; no driver/second queue is prepared here.
 */
''')
d=dict(scope=__doc__,status='COMPLETE_DESTROY_ERROR_CALLBACK_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-DESTROY-ERROR-SOURCE.patch'),fallback_byte_identical=True,existing_Rust_reuse='Production panic symbol already owned by kernel/rust/abort.rs. Existing x86_pt_destroy_table_inner supplies typed CInt reasons1/2. No new C endpoint/getter.',semantics='Two original independent equality tests and byte-identical diagnostic strings. Unknown reasons return silently. Exact void(const char*) C declaration used, no ! assumption/unreachable in new bridge; actual Rust panic terminates via its existing path unchanged.',ownership='No page/lock/reference/accounting mutation, free, callback retention, new null guard or additional diagnostic. Static strings live for the program; raw const byte pointers across the synchronous endpoint only.',selection='PUBLIC C definition excluded, original global forward declaration retained; Rust unique T/no self-U required later. No C U callback is asserted: actual consumer is existing Rust destroy orchestration.',metadata='Previous allocation750,PTfree807 and logging-selector anchors retained; subsequent physical resume directives rebased only.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-MESSAGE-RECORDER-FRAGMENT.NOT-QUEUED.c')],one_executable_queue='ptfree-logger-fixture-preparation-1/be03f105',new_driver_queue_CPU_grant=None,actual_fixture_production_default_native=None,held_residual='PTfree/loggers pending fixture; allocation wrapper468 passed but its full coherent production proof pending; separate translator source untested. Destroy helper-failed panic and other backing providers remain C.',engineering_percentage=None)
put(P/'SOURCE-DESTROY-ERROR-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json',json.dumps(d,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-DESTROY-ERROR-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json'),postimages=d['postimages'],patch=d['patch'])))
