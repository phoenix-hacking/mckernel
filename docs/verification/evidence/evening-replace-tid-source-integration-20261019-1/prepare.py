from pathlib import Path
import difflib,hashlib,json,re
O=Path(__file__).parent
R=Path('/home/holden/mckernel')
assert not (O/'candidate').exists()
files=['kernel/process.c','kernel/rust/process_helpers.rs','kernel/rust/abi.rs','kernel/rust/debug.rs','lib/include/ihk/debug.h']
for f in files:
 p=O/'original'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/f).read_bytes())
c=(R/files[0]).read_text();rs=(R/files[1]).read_text()
def cfun(s,n):
 a=s.index(n+'(');a=s.rfind('\n',0,a)+1;b=s.index('{',a);d=1;i=b+1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]+'\n'
def rfun(s,n):
 m=re.search(r'(?m)^(?:#\[no_mangle\]\n)?(?:pub )?(?:unsafe )?(?:extern "C" )?fn '+n+r'\(',s);assert m,n
 a=s.index('{',m.start());d=1;i=a+1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]+'\n'
leaf=cfun(c,'__find_and_replace_tid');logger=cfun(c,'process_replace_tid_log_bridge');consumer=cfun(c,'process_destroy_thread_replace_tid_bridge')
(O/'frozen-leaf.c').write_text(leaf);(O/'frozen-log.c').write_text(logger);(O/'frozen-consumer.c').write_text(consumer)
body=r'''
// Preserve the existing optional dynamic-debug event, including its format bytes.
#[used]
#[link_section = "__verbose"]
static mut REPLACE_TID_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"process_replace_tid_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

unsafe extern "C" fn process_replace_tid_log_bridge(
    tid: CInt, thread: *mut c_void, new_tid: CInt,
) {
    let flags = unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(REPLACE_TID_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid %d (thread %p) has been relaced with tid %d\n\0".as_ptr().cast(),
                b"__find_and_replace_tid\0".as_ptr().cast::<i8>(), tid, thread, new_tid,
            );
        }
    }
}

const _: () = {
    assert!(offset_of!(Process, tids) == 256);
    assert!(offset_of!(Process, nr_tids) == 264);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(size_of::<crate::abi::McexecTid>() == 16);
    assert!(offset_of!(crate::abi::McexecTid, tid) == 0);
    assert!(offset_of!(crate::abi::McexecTid, thread) == 8);
};

/// Replace the first slot owned by this live thread while threads_lock is held.
/// The caller keeps process, thread and its positive-count TID array live and
/// excludes concurrent or reentrant slot changes. Null tables are permitted.
/// The existing helper clears the matched pointer before writing the new numeric
/// TID, then logs; it never changes thread.tid or frees/references thread storage.
/// Unmatched entries, slot padding and later duplicate pointers are preserved.
#[no_mangle]
pub unsafe extern "C" fn __find_and_replace_tid(
    proc: *mut Process, thread: *mut Thread, new_tid: CInt,
) {
    let _ = unsafe {
        process_replace_tid_body_result(
            (*proc).tids, (*proc).nr_tids,
            size_of::<crate::abi::McexecTid>() as CULong,
            offset_of!(crate::abi::McexecTid, tid) as CULong,
            offset_of!(crate::abi::McexecTid, thread) as CULong,
            thread.cast(), (*thread).tid, new_tid, Some(process_replace_tid_log_bridge),
        )
    };
}
'''
(O/'replace-tid-body.rs').write_text(body)
assert '__find_and_replace_tid(' not in rs
cc=c.replace(logger,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+logger+'#endif\n',1)
cc=cc.replace(leaf,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nvoid __find_and_replace_tid(struct process *proc, struct thread *thread, int new_tid);\n#else\n'+leaf+'#endif\n',1)
for f,s in [(files[0],cc),(files[1],rs+body)]:
 p=O/'candidate'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=''.join(''.join(difflib.unified_diff((O/'original'/f).read_text().splitlines(True),(O/'candidate'/f).read_text().splitlines(True),fromfile='a/'+f,tofile='b/'+f)) for f in files[:2]);(O/'candidate.patch').write_text(patch)
names=['process_tid_index_for_thread_result','process_tid_index_found_result','checked_entry_addr','process_tid_replace_slot_result','process_tid_log_result','process_replace_tid_body_result']
(O/'unchanged-helper-bodies.rs').write_text(''.join(rfun(rs,n) for n in names))
(O/'source-bindings.json').write_text(json.dumps({f:hashlib.sha256((O/'original'/f).read_bytes()).hexdigest() for f in files},indent=2)+'\n')
print('Prepared one Rust replacement plus selected/fallback C patch; original bytes frozen; no compiler execution')
