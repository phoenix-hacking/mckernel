"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only exact-region extraction; bounded correction of draft newline reconstruction.
"""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parents[1];F=P/'fixture'
def item(text,marker):
 start=text.index(marker);pos=text.index('{',start);end=pos+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def main():
 c=(P/'candidate/kernel/process.c').read_text();start=c.index('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n/* Displaced sync callback dynamic-debug selectors:');end=c.index('\n#endif',start)+len('\n#endif');block=c[start:end]
 assert (F/'original_sync.ACTUAL-C-BODY.inc').read_text().rstrip() in block and (F/'sync.ACTUAL-C-SELECTORS.inc').read_text().rstrip() in block
 consumer='/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */\n#include <process.h>\n#include <process_helpers.h>\n#include <memobj.h>\n#include <ihk/debug.h>\n'+(F/'original_sync_args.ACTUAL-C.inc').read_text()+'\n'+block+'\n'
 (F/'actual_default_and_fallback_consumer.c').write_text(consumer)
 r=(P/'candidate/kernel/rust/process_helpers.rs').read_text();caller='#[no_mangle]\n'+item(r,'pub unsafe extern "C" fn sync_process_memory_range(')+'\n';assert 'sync_one_page as *mut c_void' in caller
 (F/'actual_selected_Rust_caller.ACTUAL.inc').write_text(caller)
 witness='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
extern int sync_one_page(void *,page_table_t,pte_t *,void *,int);
typedef int (*actual_visit_step_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&sync_one_page),actual_visit_step_t),"exact original callback signature");
_Static_assert(sizeof(pte_t)==8 && sizeof(size_t)==8 && sizeof(uintptr_t)==8 && sizeof(int)==4,"supported x86_64 full signedness/width ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj *)0)->flags),uint32_t),"memobj flags unsigned32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj_ops *)0)->flush_page),memobj_flush_page_func_t *),"actual memobj operation ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"exact existing variadic logger ABI");
_Static_assert(sizeof(struct ddebug)==32 && __builtin_offsetof(struct ddebug,fmt)==16,"actual ddebug lifetime/layout ABI");
'''
 (F/'actual_sync_header_ABI.c').write_text(witness)
 receipt=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='SOURCE_ONLY_ACTUAL_SELECTED_AND_FALLBACK_CONSUMER_NOT_EXECUTABLE_READY',C_consumer=pin(F/'actual_default_and_fallback_consumer.c'),real_selected_Rust_caller=pin(F/'actual_selected_Rust_caller.ACTUAL.inc'),actual_header_ABI=pin(F/'actual_sync_header_ABI.c'),sourcefixture=pin(P/'sourcehandoff/FIXTURE-SOURCE-ONLY-CURRENT.json'),source_preparation_history=pin(P/'sourcehandoff/SOURCE-EXTRACTION-PREPARATION-FAILURE-1.json'),defaultconsumer='Existing actual Rust sync_process_memory_range passes the real sync_one_page pointer to existing Rust visit helper; full selected process.c declares only displaced debug selector data, original C function remains exact fallback.',compiler_jobs=0,test_jobs=0,CPU_reservations=0,executable_recipes=0,cutover_credit=False)
 with (P/'sourcehandoff/ACTUAL-CONSUMER-SOURCE-ONLY.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(pin(P/'sourcehandoff/ACTUAL-CONSUMER-SOURCE-ONLY.json')))
if __name__=='__main__':main()
