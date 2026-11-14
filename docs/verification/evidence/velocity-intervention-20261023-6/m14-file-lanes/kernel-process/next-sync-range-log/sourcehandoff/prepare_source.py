"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One next actual retained C logging body, source only and no second ready job.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parents[1];BASE=P.parent/'next-sync-one-page';SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def item(s,marker):
 start=s.index(marker);brace=s.index('{',start);end=brace+1;depth=1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]
def main():
 cpath=BASE/'candidate/kernel/process.c';rpath=BASE/'candidate/kernel/rust/process_helpers.rs';assert pin(cpath)['sha256']=='c5d0e24c22c6e66660221c6bc303237f02957b45ed74f196bcaf398a20d9cef2';assert pin(rpath)['sha256']=='268fe3e0120a587203aba50f55158646d8ca06282cf03d779d6b4eb437de10ad'
 c=cpath.read_text();r=rpath.read_text();original=item(c,'void process_sync_range_log_bridge(')
 decl='''    fn process_sync_range_log_bridge(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        start: CULong,
        end: CULong,
        error: CInt,
    );''';assert r.count(decl)==1
 body='''/// Existing synchronous range-sync failure notification. No pointer is
/// dereferenced or retained; caller lock/ref/notification ordering is unchanged.
#[no_mangle]
pub unsafe extern "C" fn process_sync_range_log_bridge(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
) {
    let _ = kprintf(
        b"sync_process_memory_range(%p,%p,%#lx,%#lx):visit failed%d\\n\\0".as_ptr().cast(),
        vm, range, start, end, error,
    );
}'''
 postc=c.replace(original,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original+'\n#endif',1)
 postr=r.replace(decl,'',1);postr=postr.replace('#[no_mangle]\npub unsafe extern "C" fn sync_one_page(',body+'\n\n#[no_mangle]\npub unsafe extern "C" fn sync_one_page(',1)
 assert postr.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 assert 'Some(process_sync_range_log_bridge)' in postr
 for directory in ('candidate/kernel/rust','fixture','patch'):(P/directory).mkdir(parents=True)
 (P/'candidate/kernel/process.c').write_text(postc);(P/'candidate/kernel/rust/process_helpers.rs').write_text(postr)
 (P/'fixture/original_log.ACTUAL-C.inc').write_text(original+'\n');(P/'fixture/log.ACTUAL-RUST.inc').write_text(body+'\n')
 caller=item(r,'pub unsafe extern "C" fn process_sync_memory_range_body_result(');assert caller.index('process_noirq_unlock_result')<caller.index('if error != 0')<caller.index('log(vm, range, start, end, error)')
 (P/'fixture/unchanged_actual_Rust_caller.ACTUAL.inc').write_text(caller+'\n')
 for rel,before,after in [('kernel/process.c',c,postc),('kernel/rust/process_helpers.rs',r,postr)]:
  (P/'patch'/((Path(rel).name)+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='sync-predecessor/'+rel,tofile='sync-log-successor/'+rel)))
 receipt=dict(scope=SCOPE,status='ACTUAL_NEXT_BODY_SOURCE_ONLY_NO_SECOND_EXECUTABLE_COHORT',chosen_body='process_sync_range_log_bridge complete retained unconditional C failure logger',predecessor={rel:pin(BASE/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},original_C=pin(P/'fixture/original_log.ACTUAL-C.inc'),actual_Rust=pin(P/'fixture/log.ACTUAL-RUST.inc'),unchanged_actual_Rust_caller=pin(P/'fixture/unchanged_actual_Rust_caller.ACTUAL.inc'),ABI='Existing ProcessSyncRangeLogFn unchanged: (ProcessVm*,VmRange*,unsigned long,unsigned long,int)->void. Exact LP64 pointer/UL/UL/signed-int varargs and original format/event; existing unconditional kprintf declaration reused once.',order='Existing helper finishes visit, decrements retained memobj ref and unlocks, then calls this callback only on nonzero error. Body logs once synchronously and ignores signed logger return, returning void as original C.',pointer_lifetimes='No dereference or reference creation; original borrowed pointer values exist only for synchronous variadic call.',original_C_fallback_exact=True,remaining_C_debt='No C compute for this bridge in selected profile; other process callbacks and two sync diagnostic metadata rows remain.',requires='Dump and sync predecessor acceptance/integration or exact root rebase before any canonical proposal; future real original-C/Rust logger parity/typed ABI and selected consumer compile, no commands prepared here.',compiler_jobs=0,test_jobs=0,CPU_reservations=0,executable_recipes=0,source_correctness_claim=False,default_native_file_credit=False)
 with (P/'sourcehandoff/SOURCE-NEXT-BODY.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],compiler_jobs=0,test_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
