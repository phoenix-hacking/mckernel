"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only existing EBUSY logging callback; no second executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent
S=B/'next-destroy-helper-error-source-only-1/candidate'
P=B/'next-set-page-log-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text()
old='''static void x86_pt_set_page_log_bridge(unsigned long virt)
{
	kprintf("EBUSY: page table for 0x%lX is already set\\n", virt);
}'''
decl='static void x86_pt_set_page_log_bridge(unsigned long virt);'
assert c.count(old)==1 and c.count(decl)==1
nc=c.replace(decl,'X86_MEMORY_PUBLIC_BRIDGE void x86_pt_set_page_log_bridge(unsigned long virt);',1)
nc=nc.replace(old,'#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
assert 'fn x86_pt_set_page_log_bridge(' not in r
nr=r+'''
// This existing EBUSY event is unconditional; preserve uppercase %lX and the
// ignored CInt formatter result. The C orchestration owns its lock/error flow.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_page_log_bridge(virt: CULong) {
    unsafe {
        let _ = kprintf(b"EBUSY: page table for 0x%lX is already set\\n\\0".as_ptr().cast(), virt);
    }
}
'''
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SET-PAGE-LOG-SOURCE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n')
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_set_page_log_bridge),x86_pt_set_page_log_fn_t),"actual typed EBUSY callback ABI");
_Static_assert(sizeof(unsigned long)==8 && sizeof(int)==4,"existing log vararg widths");
''')
put(P/'FUTURE-EXACT-OUTPUT-FRAGMENT.NOT-QUEUED.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original C/Rust callback output comparison with a controlled host formatter;
 * no page-table locking, real EBUSY trigger, or native formatter claim.
 */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static unsigned log_calls;
static char log_text[128];
static int formatter_result;
int kprintf(const char *format,...)
{
    va_list ap;va_start(ap,format);++log_calls;
    int n=vsnprintf(log_text,sizeof(log_text),format,ap);va_end(ap);
    assert(n>=0 && (unsigned)n<sizeof(log_text));return formatter_result;
}
static void future_set_page_log_case(void (*original)(unsigned long),
                                     void (*rust)(unsigned long),unsigned long virt)
{
    unsigned before=log_calls;original(virt);char expected[128];strcpy(expected,log_text);
    assert(log_calls==before+1);rust(virt);
    assert(log_calls==before+2 && strcmp(log_text,expected)==0);
}
/* Values0,1,0x123456789abcdef0,1UL<<63,ULONG_MAX and formatter returns-7/0/17.
 * Use exact saved C and Rust bodies. Actual C allocated relocation from the
 * existing __set_pt_page callback argument to Rust must be observed later;
 * syntax/source relation alone does not prove default selection/link/native.
 */
''')
data=dict(scope=__doc__,status='COMPLETE_UNCONDITIONAL_SET_PAGE_EBUSY_LOG_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SET-PAGE-LOG-SOURCE.patch'),original_C_reference=ref(P/'EXACT-ORIGINAL-C-PROVIDER.inc'),real_consumer='Existing C __set_pt_page passes this typed callback to existing Rust x86_pt_set_page_body_result; outer init_pt_lock acquisition/unlock and ret unchanged.',semantics='Exactly one existing variadic Rust-owned kprintf call, byte-identical unconditional EBUSY message with uppercase %lX, unsigned64 value unchanged and CInt result ignored. No dynamic-debug selector or new error branch.',ownership='No page-table dereference, page allocation/free, reference/lock/accounting mutation, callback retention or borrowed reference introduced. Same logging call position within existing locked orchestration.',selection='PUBLIC forward declaration becomes the existing X86_MEMORY_PUBLIC_BRIDGE declaration pattern; original static C body retained byte-identical only in fallback. Future wholeTU must establish actual C function-pointer import/allocated relocation and unique Rust T; no linked/native credit yet.',prior_metadata='Allocation750/PTfree807/debug selector anchors retained; post-endif physical resume directives rebased only.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-EXACT-OUTPUT-FRAGMENT.NOT-QUEUED.c')],sole_executable_queue='passed-four-provider-union2-production-suffix-preparation-1/c03ce4ee',new_driver_CPU_reservation=None,actual_fixture_TU_partial_default_native=None,held_residuals='Four passed alloc/free/log ports await root-shared Rust+Cmem proof and C-only production suffix. Reason/helper-error and this EBUSY logger source ports remain untested; translator stays separate. Allocator/page-owner backing chains are the higher-uncertainty remaining runtime work.',engineering_percentage=None)
put(P/'SOURCE-SET-PAGE-LOG-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SET-PAGE-LOG-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
