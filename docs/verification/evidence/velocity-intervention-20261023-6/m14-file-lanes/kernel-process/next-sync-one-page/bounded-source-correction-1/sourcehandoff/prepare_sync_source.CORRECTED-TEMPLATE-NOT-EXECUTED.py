"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Next substantive independent source body only; no executable grant/reservation.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parents[1];B=P.parent;R=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def item(s,marker):
 start=s.index(marker);brace=s.index('{',start);end=brace+1;depth=1
 while depth:
  if s[end]=='{':depth+=1
  if s[end]=='}':depth-=1
  end+=1
 return s[start:end]
def main():
 # This is an explicitly dependent private successor, never a stale canonical
 # whole-file replacement: root must accept/rebase the dump predecessor first.
 cpath=B/'candidate/kernel/process.c';rpath=B/'candidate/kernel/rust/process_helpers.rs'
 assert pin(cpath)['sha256']=='1ecbc287f2e704e738cc4e9fbe18289226b5aadadc9da88d226dc0ad0bb57234'
 assert pin(rpath)['sha256']=='70015d712c29e416881e2fbaccd67026ee15ac7eb915cb80e828485d6f34d71f'
 c=cpath.read_text();rust=rpath.read_text();original=item(c,'int sync_one_page(')
 line_entry=c[:c.index('dkprintf("sync_one_page(')].count('\n')+1
 line_exit=c[:c.index('dkprintf("sync_one_page(%p,%p,%p %#lx,%p,%d):%d')].count('\n')+1
 selectors='''/* Displaced sync callback dynamic-debug selectors: declarative data only. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_entry_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = ENTRY_LINE, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_exit_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = EXIT_LINE, .flags = DDEBUG_DEFAULT,
};'''.replace('ENTRY_LINE',str(line_entry)).replace('EXIT_LINE',str(line_exit))
 postc=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+selectors+'\n#else\n'+original+'\n#endif',1)
 oldextern='''    fn sync_one_page(
        arg0: *mut c_void,
        page_table: *mut c_void,
        ptep: *mut c_void,
        pgaddr: *mut c_void,
        pgshift: CInt,
    ) -> CInt;'''
 assert rust.count(oldextern)==1 and rust.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 postrust=rust.replace(oldextern,'''    static mut process_sync_one_page_entry_debug: crate::debug::Ddebug;
    static mut process_sync_one_page_exit_debug: crate::debug::Ddebug;''',1)
 body='''/// Own the actual former C sync callback. The caller retains the live PTE,
/// args/memobj and existing page-table exclusion for the synchronous visit.
/// Valid pgshift is the original supported 0..63 domain. No new error policy,
/// ownership transfer, allocation or lock is introduced.
#[no_mangle]
pub unsafe extern "C" fn sync_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut error = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_entry_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d)\\n\\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    if crate::pte_helpers::pte_is_null(pte) == 0
        && crate::pte_helpers::pte_is_fileoff(pte, pgsize) == 0
        && crate::pte_helpers::pte_is_dirty(pte, pgsize) != 0
    {
        crate::pte_helpers::pte_clear_dirty(pte, pgsize);
        crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);
        // Original ordering: read physical PTE after the TLB-effect callback,
        // then inspect zero-fill flags before the existing memobj operation.
        let phys = crate::pte_helpers::pte_get_phys(pte);
        let memobj = (*arg0.cast::<ProcessSyncArgs>()).memobj;
        if (*memobj).flags & MF_ZEROFILL == 0 {
            error = crate::object_helpers::memobj_flush_page(memobj, phys, pgsize);
            if error != 0 {
                let _ = kprintf(
                    b"sync_one_page(%p,%p,%p %#lx,%p,%d):flush failed. %d\\n\\0".as_ptr().cast(),
                    arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
                );
                crate::pte_helpers::pte_set_dirty(pte, pgsize);
            }
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_exit_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d):%d\\n\\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
        );
    }
    error
}
'''
 marker='#[no_mangle]\npub unsafe extern "C" fn process_sync_memory_range_body_result('
 assert postrust.count(marker)==1;postrust=postrust.replace(marker,body+'\n'+marker,1)
 assert postrust.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 for before,after,key in [(c,postc,'kernel/process.c'),(rust,postrust,'kernel/rust/process_helpers.rs')]:
  target=P/'candidate'/key;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(after)
  (P/'patch'/(Path(key).name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='dump-predecessor/'+key,tofile='sync-successor/'+key)))
 (P/'fixture/original_sync.ACTUAL-C-BODY.inc').write_text(original+'\n')
 (P/'fixture/sync.ACTUAL-RUST-BODY.inc').write_text(body)
 (P/'fixture/sync.ACTUAL-C-SELECTORS.inc').write_text(selectors+'\n')
 recipe=dict(scope=SCOPE,status='SOURCE_IMPLEMENTED_NOT_EXECUTABLE_READY_PENDING_DUMP_PREDECESSOR_ACCEPTANCE_AND_COHERENT_BINDING',chosen_body='sync_one_page complete actual C dirty-page synchronization/error-redirty callback',base_private_dump_predecessor={key:pin(B/'candidate'/key) for key in ['kernel/process.c','kernel/rust/process_helpers.rs']},actual_dump_leaf=pin(B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),postimages={key:pin(P/'candidate'/key) for key in ['kernel/process.c','kernel/rust/process_helpers.rs']},source_provider_bindings={key:pin(R/key) for key in ['kernel/rust/pte_helpers.rs','kernel/rust/object_helpers.rs','kernel/rust/x86_memory_helpers.rs','kernel/rust/abi.rs','lib/include/ihk/debug.h']},existing_Rust_providers=['pte_helpers::pte_is_null/pte_is_fileoff/pte_is_dirty/pte_clear_dirty/pte_get_phys/pte_set_dirty','x86_memory_helpers::flush_tlb_single existing reviewed architecture operation','object_helpers::memobj_flush_page existing typed operation dispatch','existing unconditional kprintf declaration exactly once'],original_entry_line=line_entry,original_exit_line=line_exit,algorithm='Entry diagnostic; shortcircuit null/fileoff/clean; atomic dirty clear; TLB flush; physical read; zero-fill bypass; original memobj flush; error diagnostic before atomic dirty restore; exit diagnostic and exact signed result.',remaining_C_debt='Only two declarative existing-debug selector data rows for this slice; exact C fallback retained. Existing memobj callback operation may be C or Rust according to its provider, no claim of whole object subsystem retirement.',fixture_contract=dict(next_actual_observation='Real original C callback + actual Rust callback with actual pure Rust PTE and memobj dispatch providers, controlled functional TLB-effect callback only; never invoke real invlpg on host.',cases=['NULL/fileoff/clean skip with no args/memobj read when debug disabled','Dirty supported4KiB/2MiB/1GiB page success and zero-fill skip after clear+flush','Positive/negative memobj error; failure logger sees cleared state before dirty restoration; exact error retained','TLB-effect callback updates PTE physical bits before physical read','Entry/exit flags independent and high8bits, exact variadic formats/UL/int payloads','Memobj callback absent/defaultsuccess and present path; no pointer retained after synchronous visit'],required_ABI=['ProcessSyncArgs.memobj and Memobj.flags/ops real structures','real PTE width/alignment and supported page-shift masks','Ddebug bitfield and actual C function/callback signatures']),prior_E0428_duplicate_failure='2fb3/e9a preserved, no duplicate kprintf added',compile_or_test_jobs=0,CPU_reservations=0,canonical_or_shared_writes=0,cutover_credit=False)
 (P/'sourcehandoff/SOURCE-NEXT-BODY.json').write_text(json.dumps(recipe,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=recipe['postimages'],predecessor_required=True,compile_jobs=0),indent=2))
if __name__=='__main__':main()
