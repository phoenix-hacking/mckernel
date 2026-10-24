"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One actual remap callback retirement, private source only; no executable cohort.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parents[1];BASE=P.parent/'next-sync-range-log';ROOT=Path('/home/holden/mckernel');SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def item(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def lineno(text,marker):return text[:text.index(marker)].count('\n')+1
def main():
 cpath=BASE/'candidate/kernel/process.c';rpath=BASE/'candidate/kernel/rust/process_helpers.rs';assert pin(cpath)['sha256']=='225fa1d28cbb2d7d5d2e1fdab9ff7435362c0b21661a64188e09c02f3eba08af';assert pin(rpath)['sha256']=='6ecdafee1c6d6817ca0242149f67983871d545768f4873fa19c47e7d5ad6f7f8'
 c=cpath.read_text();r=rpath.read_text();original=item(c,'int remap_one_page(')
 entry_line=lineno(c,'dkprintf("remap_one_page(');free_line=lineno(c,'_ihk_mc_free_pages(phys_to_virt(phys), pgsize/PAGE_SIZE, IHK_MC_PG_USER, __FILE__, __LINE__);');rss_line=lineno(c,'dkprintf("%lx-,%s: calling memory_stat_rss_sub()');exit_line=lineno(c,'dkprintf("remap_one_page(%p,%p,%p %#lx,%p,%d): %d')
 selectors='''/* Preserve displaced remap diagnostics and tracked-free source identity as
 * static C ABI data only. Rust owns the complete callback computation. */
const char *const process_remap_free_file = __FILE__;
const int process_remap_free_line = FREE_LINE;
'''.replace('FREE_LINE',str(free_line))
 for name,line in [('entry',entry_line),('rss',rss_line),('exit',exit_line)]:
  selectors+='''struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_remap_one_page_NAME_debug = {
    .file = __FILE__, .func = "remap_one_page",
    .line = LINE, .flags = DDEBUG_DEFAULT,
};
'''.replace('NAME',name).replace('LINE',str(line))
 olddecl='''    fn remap_one_page(
        arg0: *mut c_void,
        page_table: *mut c_void,
        ptep: *mut c_void,
        pgaddr: *mut c_void,
        pgshift: CInt,
    ) -> CInt;''';assert r.count(olddecl)==1 and '    fn phys_to_page(' not in r
 externs='''    static mut process_remap_one_page_entry_debug: crate::debug::Ddebug;
    static mut process_remap_one_page_rss_debug: crate::debug::Ddebug;
    static mut process_remap_one_page_exit_debug: crate::debug::Ddebug;
    static process_remap_free_file: *const i8;
    static process_remap_free_line: CInt;
    fn phys_to_page(phys: CULong) -> *mut crate::page_helpers::Page;'''
 body='''/// Replace the actual former C remap visitor. The existing outer caller
/// keeps its page-table exclusion and memobj reference for the synchronous
/// visit; page_unmap owns its existing mapped-page/hash accounting. No new
/// lock, reference, ownership transfer or error policy is introduced.
#[no_mangle]
pub unsafe extern "C" fn remap_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let args = arg0.cast::<ProcessRemapArgs>();
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut old_pte: CULong = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_entry_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d)\\n\\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    // Preserve C's unsigned uintptr_t arithmetic and LP64 off_t conversion.
    // Both argument loads occur after the entry logger, as in the C body.
    let off = ((*args).off as CULong)
        .wrapping_add((pgaddr as CULong).wrapping_sub((*args).start)) as OffT;
    crate::pte_helpers::pte_make_fileoff(off, 0, pgsize, &raw mut old_pte);
    crate::pte_helpers::pte_xchg(pte, &raw mut old_pte);
    crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);

    // All mapping-release decisions use the exchanged snapshot, never a PTE
    // subsequently published at ptep by the existing TLB/flush boundaries.
    if crate::pte_helpers::pte_is_null(&raw const old_pte) == 0
        && crate::pte_helpers::pte_is_fileoff(&raw const old_pte, pgsize) == 0
    {
        let phys = crate::pte_helpers::pte_get_phys(&raw const old_pte);
        if crate::pte_helpers::pte_is_dirty(&raw const old_pte, pgsize) != 0 {
            // The original remap visitor deliberately ignores this result.
            let _ = crate::object_helpers::memobj_flush_page((*args).memobj, phys, pgsize);
        }
        // Existing public phys_to_page provider retains its C forwarding
        // wrapper and Rust lookup implementation; it is explicit provider debt.
        let page = phys_to_page(phys);
        if !page.is_null() && crate::page_helpers::page_unmap(page) != 0 {
            let address = crate::x86_memory_helpers::phys_to_virt(phys);
            crate::mem_helpers::_ihk_mc_free_pages(
                address,
                (pgsize / PAGE_SIZE as SizeT) as CInt,
                1, // existing IHK_MC_PG_USER, checked against actual mm.h
                process_remap_free_file as *mut i8,
                process_remap_free_line,
            );
            if core::ptr::read_volatile(core::ptr::addr_of!(
                process_remap_one_page_rss_debug.line_flags
            )) >> 24 != 0 {
                // Original %ld payloads are the unsigned size_t values.
                let _ = kprintf(
                    b"%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\\n\\0".as_ptr().cast(),
                    phys, b"remap_one_page\\0".as_ptr().cast::<i8>(), pgsize, pgsize,
                );
            }
            // Reload args->memobj after free/log callbacks, and retain C's
            // narrowing conversion from size_t to the provider's int pgsize.
            crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize, pgsize as CInt);
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_exit_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d): %d\\n\\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, 0 as CInt,
        );
    }
    0
}'''
 postc=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+selectors+'#else\n'+original+'\n#endif',1)
 postr=r.replace(olddecl,externs,1);sync=item(postr,'pub unsafe extern "C" fn sync_one_page(');postr=postr.replace(sync,sync+'\n\n'+body,1)
 assert postr.count('pub unsafe extern "C" fn remap_one_page(')==1 and postr.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 assert 'remap_one_page as *mut c_void' in postr
 for directory in ('candidate/kernel/rust','fixture','patch'):(P/directory).mkdir(parents=True)
 (P/'candidate/kernel/process.c').write_text(postc);(P/'candidate/kernel/rust/process_helpers.rs').write_text(postr)
 (P/'fixture/original_remap.ACTUAL-C.inc').write_text(original+'\n');(P/'fixture/remap.ACTUAL-RUST.inc').write_text(body+'\n');(P/'fixture/remap.ACTUAL-C-METADATA.inc').write_text(selectors)
 (P/'fixture/actual_args.ACTUAL-RUST.inc').write_text('#[repr(C)]\n'+item(r,'struct ProcessRemapArgs')+'\n')
 caller=item(r,'pub unsafe extern "C" fn remap_process_memory_range(');helper=item(r,'pub unsafe extern "C" fn process_remap_memory_range_body_result(')
 assert 'remap_one_page as *mut c_void' in caller and helper.index('process_noirq_lock_result')<helper.index('process_memobj_ref_direct_result')<helper.index('compare_exchange')<helper.index('let error = visit(')<helper.index('process_memobj_unref_direct_result')<helper.index('process_noirq_unlock_result')
 (P/'fixture/unchanged_actual_Rust_caller.ACTUAL.inc').write_text(caller+'\n');(P/'fixture/unchanged_actual_Rust_owner.ACTUAL.inc').write_text(helper+'\n')
 for rel,before,after in [('kernel/process.c',c,postc),('kernel/rust/process_helpers.rs',r,postr)]:
  (P/'patch'/(Path(rel).name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='sync-log-predecessor/'+rel,tofile='remap-successor/'+rel)))
 mm=(ROOT/'lib/include/ihk/mm.h').read_text();assert '#define IHK_MC_PG_USER         1' in mm
 providers=['kernel/rust/pte_helpers.rs','kernel/rust/object_helpers.rs','kernel/rust/page_helpers.rs','kernel/rust/x86_memory_helpers.rs','kernel/rust/mem_helpers.rs','kernel/rust/abi.rs','kernel/include/page.h','kernel/include/rusage_private.h','lib/include/ihk/mm.h','lib/include/ihk/debug.h']
 mem=(ROOT/'kernel/mem.c').read_text();physical=item(mem,'struct page *phys_to_page(');assert 'phys_to_page_lookup_body_result' in physical
 (P/'fixture/existing_phys_to_page_C_PROVIDER_DEBT.inc').write_text(physical+'\n')
 receipt=dict(scope=SCOPE,status='SUBSTANTIVE_ACTUAL_REMAP_BODY_SOURCE_IMPLEMENTED_NOT_EXECUTABLE_READY',chosen_body='Complete actual remap_one_page PTE replacement/dirty flush/page-unmap/free/RSS visitor',predecessor={rel:pin(BASE/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},original_C=pin(P/'fixture/original_remap.ACTUAL-C.inc'),actual_Rust=pin(P/'fixture/remap.ACTUAL-RUST.inc'),C_metadata=pin(P/'fixture/remap.ACTUAL-C-METADATA.inc'),actual_caller=pin(P/'fixture/unchanged_actual_Rust_caller.ACTUAL.inc'),actual_owner=pin(P/'fixture/unchanged_actual_Rust_owner.ACTUAL.inc'),provider_pins={rel:pin(ROOT/rel) for rel in providers},existing_C_provider_debt=pin(P/'fixture/existing_phys_to_page_C_PROVIDER_DEBT.inc'),metadata_lines=dict(entry=entry_line,tracked_free=free_line,free_RSS_debug=rss_line,exit=exit_line),existing_Rust_reused=['PTE fileoff encoding, atomic exchange and captured-PTE predicates','typed memobj_flush_page operation dispatch','existing reviewed x86 flush_tlb_single/phys_to_virt','page_helpers::page_unmap existing hash/mapped accounting','mem_helpers::_ihk_mc_free_pages tracking+free and rusage_memory_stat_sub'],precise_caller_invariant='Actual Rust remap_process_memory_range constructs reprC ProcessRemapArgs and passes remap_one_page directly to existing Rust process_remap_memory_range_body_result. That owner acquires the same VM page_table_lock, retains memobj, atomically maps pgshift0 to12 and accepts12, rejects other nonzero shifts with -E2BIG before visit, synchronously visits, then unrefs and unlocks. No new lock/ref or ACK is introduced.',algorithm_invariant='Entry log before args loads; exact wrapping uintptr_t/off_t calculation; encode fileoff then atomically exchange live PTE; TLB before captured-PTE tests. Snapshot null/fileoff skip remaining release work. Dirty snapshot flush result ignored. Lookup then page_unmap; only nonnull page and nonzero unmap trigger phys_to_virt/free, then optional debug, reload args.memobj and RSS subtraction. Exit logs current live PTE and returns0 always as original.',ABI='Original five-argument callback and signed CInt return; existing reprC ProcessRemapArgs24B asserts reused; no Page field access. Exact UL varargs even for original %ld formats; pagecount/RSS provider CInt narrowing preserved. IHK_MC_PG_USER1 verified actual mm.h. kprintf declaration reused once.',lifetimes='Caller-owned args, memobj and live PTE remain borrowed for synchronous visit; captured old PTE stack storage is not retained. No page access after unmap/free. Free source filename remains C-owned static __FILE__ string with recorded original __LINE__; Ddebug file/function/line/flags rows have static lifetime.',original_C_fallback_exact=True,remaining_C_debt=['Existing public phys_to_page C forwarding provider plus its existing C lock callbacks; Rust lookup reused underneath','Existing page_unmap lock/log callbacks and tracked-free backend callbacks retain their own debt','Three displaced diagnostic selector rows and two tracked-free identity data rows only for this body; no new C computation','Other process.c compute bodies'],future_fixture_contract=['Actual original C callback and actual Rust callback with real PTE fileoff/xchg helpers; explicit HOST TLB adapter only, never invlpg on host','Snapshot null/fileoff/clean/dirty; old/new physical values and PTE mutation at TLB/flush/lookup/page-unmap/free/debug/exit boundaries','Flush0/positive/negative ignored results; page absent and page-unmap0/nonzero; exact free/RSS/exit ordering and no duplicate release','Actual callback ABI, ProcessRemapArgs field layout, existing Page type/phys_to_page declaration and tracked-free source file/line static lifetime','Original three independent dynamic-debug gates, exact formats and pointer/UL/int varargs; free metadata identity and CInt narrowings','Original C fallback bytes and actual selected Rust remap_process_memory_range pointer relocation to this Rust entry'],failure_history='All prior E0428/retained-GOT/source-extraction failures remain; this source-only family has no compiler/test attempt.',requires='Private dump/sync/log predecessor acceptance and root coherent rebase; no source correctness/default/native credit from this preparation.',compiler_jobs=0,test_jobs=0,CPU_reservations=0,executable_recipes=0,canonical_or_shared_mutations=0,source_correctness_claim=False,default_native_file_credit=False)
 with (P/'sourcehandoff/SOURCE-NEXT-BODY.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],metadata_lines=receipt['metadata_lines'],compiler_jobs=0,test_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
