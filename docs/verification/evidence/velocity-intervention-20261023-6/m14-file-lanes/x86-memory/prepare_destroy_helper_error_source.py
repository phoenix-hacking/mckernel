"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only remaining helper-failure callback; no second executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent
S=B/'next-destroy-error-source-only-1/candidate'
P=B/'next-destroy-helper-error-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text()
assert ref(cp)['sha256']=='ec79469424c08d2cf58d69ebad5223ccbbbd618a1a66c7367400e32c6ba3e073'
assert ref(rp)['sha256']=='8e9e2ec34ccafe2b86fe6e1b17a74d64f399e25f96194a162eb0c4e2efe0a202'
old='''X86_MEMORY_PUBLIC_BRIDGE void x86_pt_destroy_helper_failed_panic_bridge(void)
{
	panic("destroy_page_table: helper failed");
}'''
assert c.count(old)==1
nc=c.replace(old,'#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
foreign='    fn x86_pt_destroy_helper_failed_panic_bridge();\n';assert r.count(foreign)==1
nr=r.replace(foreign,'',1)+'''
// Preserve the existing helper-failure diagnostic and the exact void C ABI.
// x86_memory_existing_panic resolves to the already Rust-owned production panic.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_destroy_helper_failed_panic_bridge() {
    unsafe {
        x86_memory_existing_panic(b"destroy_page_table: helper failed\\0".as_ptr().cast());
    }
}
'''
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-DESTROY-HELPER-ERROR-SOURCE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n')
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_destroy_helper_failed_panic_bridge),void(*)(void)),"exact helper-failure callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&panic),void(*)(const char*)),"existing Rust panic C declaration");
''')
put(P/'FUTURE-HELPER-MESSAGE-FRAGMENT.NOT-QUEUED.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Endpoint records and returns according to its actual C declaration. It does
 * not test production panic termination, CPU stop, monitor publication or unwind.
 */
#include <assert.h>
#include <string.h>
static unsigned endpoint_calls;
static const char *endpoint_message;
void panic(const char *message) { ++endpoint_calls;endpoint_message=message; }
static void future_helper_message_case(void (*original)(void),void (*rust)(void))
{
    unsigned before=endpoint_calls;original();
    assert(endpoint_calls==before+1);
    assert(strcmp(endpoint_message,"destroy_page_table: helper failed")==0);
    const char *expected=endpoint_message;rust();
    assert(endpoint_calls==before+2 && strcmp(endpoint_message,expected)==0);
}
/* Use the exact saved original body and exact Rust body. Existing destroy
 * orchestration's ret!=0 branch must retain its same call position. This is a
 * source fragment only, not an extra driver or executable queue.
 */
''')
data=dict(scope=__doc__,status='COMPLETE_HELPER_FAILURE_CALLBACK_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-DESTROY-HELPER-ERROR-SOURCE.patch'),original_C_reference=ref(P/'EXACT-ORIGINAL-C-PROVIDER.inc'),semantics='One synchronous call to existing production Rust panic with exact static NUL-terminated diagnostic. Exact void(void) callback and void(const char*) endpoint ABI. No !/unreachable assumption added; reference recorder may return, real existing Rust panic does not.',error_orchestration='Existing Rust x86_pt_destroy_public_bridge still checks ret!=0 then invokes this same callback. No change to table traversal, lower-child/free ordering, reason callbacks, error values or subsequent control policy.',ownership='No page/lock/refcount/accounting/CPU mutation in the new callback, no extra free/allocation or callback retention; static byte string lifetime. Existing production panic owns its monitor/IRQ/stack/CPU-stop behavior unchanged.',selection='PUBLIC C definition excluded and foreign self-import removed; future Rust global T/no self-U and real header/type/partial proof required. No invented C U/direct caller; real caller is existing Rust destroy orchestration.',fallback_C_byte_identical=True,prior_trace_callsite_anchors_preserved=True,new_C_function_getter=False,fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-HELPER-MESSAGE-FRAGMENT.NOT-QUEUED.c')],untested_reason_callback='e011c531 source retained separately as predecessor, not duplicated or credited',sole_pending_production_queue='passed-four-provider-union2-production-suffix-preparation-1/c03ce4ee',new_queue_driver_CPU_reservation=None,actual_fixture_fullcrate_selected_C_partial_default_native=None,known_next_body='x86_pt_set_page_log_bridge: exact existing C format/debug selector, reuse Rust debug/kprintf; source lookup remains finite and implementation not yet claimed.',engineering_percentage=None)
put(P/'SOURCE-DESTROY-HELPER-ERROR-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-DESTROY-HELPER-ERROR-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
