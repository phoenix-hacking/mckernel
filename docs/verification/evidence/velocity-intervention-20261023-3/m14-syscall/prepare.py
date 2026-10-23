#!/usr/bin/env python3
"""Functional OS/Rust source preparation only; no security testing or execution."""
from pathlib import Path
import difflib, hashlib, json
P = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
S = P/'snapshot'
S.mkdir(exist_ok=True)
inputs = {}
for name in ['kernel/syscall.c', 'kernel/rust/syscall_policy.rs', 'kernel/rust/abi.rs', 'kernel/include/process.h']:
    src=R/name; dst=S/name; dst.parent.mkdir(parents=True,exist_ok=True)
    data=src.read_bytes(); dst.write_bytes(data)
    inputs[name]={'source':str(src),'snapshot':str(dst),'sha256':hashlib.sha256(data).hexdigest()}
c=(S/'kernel/syscall.c').read_text(); rs=(S/'kernel/rust/syscall_policy.rs').read_text()
def cut(text, a, b):
    assert text.count(a)==1, a
    start=text.index(a); end=text.index(b,start)
    return text[start:end]
old=cut(c,'long\nsyscall_signalfd_publish_bridge(', '\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_epoll_pwait')
(P/'original_body.c.inc').write_text(old)
new='#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+old+'#endif /* !MCKERNEL_RUST_SYSCALL_POLICY_HELPERS: retained C fallback */\n'
cc=c.replace(old,new,1)
extern=cut(rs,'    fn syscall_signalfd_publish_bridge(', '    fn syscall_do_kill_thread_bridge(')
assert extern.rstrip().endswith(') -> CLong;')
body=(P/'signalfd_publish.rs').read_text()
rr=rs.replace(extern,'',1)
anchor='#[no_mangle]\npub unsafe extern "C" fn signalfd4_body_result('
rr=rr.replace(anchor,body+'\n'+anchor,1)
patch=''.join(difflib.unified_diff(c.splitlines(True),cc.splitlines(True),fromfile='a/kernel/syscall.c',tofile='b/kernel/syscall.c'))
patch+=''.join(difflib.unified_diff(rs.splitlines(True),rr.splitlines(True),fromfile='a/kernel/rust/syscall_policy.rs',tofile='b/kernel/rust/syscall_policy.rs'))
(P/'candidate.patch').write_text(patch)
patched=P/'patched'; (patched/'kernel/rust').mkdir(parents=True,exist_ok=True)
(patched/'kernel/syscall.c').write_text(cc)
(patched/'kernel/rust/syscall_policy.rs').write_text(rr)
# Bound the function by Rust brace balance instead of copying its unrelated neighbor.
def function(text,start):
    a=text.index(start); brace=text.index('{',a); depth=1; i=brace+1
    while depth:
        depth += (text[i]=='{')-(text[i]=='}'); i+=1
    return text[a:i]+'\n'
consumer='\n'.join(function(rs,a) for a in [
 '#[no_mangle]\npub extern "C" fn signalfd4_sigsetsize_result(',
 '#[no_mangle]\npub extern "C" fn signalfd4_flags_result(',
 '#[no_mangle]\npub unsafe extern "C" fn signalfd4_body_result(',
 'unsafe fn current_thread_ptr()',
 '#[no_mangle]\npub unsafe extern "C" fn sys_signalfd4(',
])
(P/'existing_consumer.rs.inc').write_text(consumer)
# Struct views are fixture-only. C mckfd fields are copied from the real header;
# thread/proc views deliberately model only the fields used by unchanged C body.
h=(S/'kernel/include/process.h').read_text()
mckfd=cut(h,'struct mckfd {','\n#define SFD_CLOEXEC')
preamble='''/* Functional McKernel OS/Rust equivalence fixture; no security testing. */
#include <stddef.h>
#include <string.h>
#include <errno.h>
typedef void ihk_mc_user_context_t;
'''+mckfd+'''
struct process { unsigned int mckfd_lock; struct mckfd *mckfd; };
struct thread { struct process *proc; };
extern void *fixture_c_alloc(int, unsigned long, const char *, int);
extern long fixture_lock(void *);
extern void fixture_unlock(void *, long);
#define IHK_MC_AP_NOWAIT 2UL
#define kmalloc_tracked fixture_c_alloc
#define ihk_mc_spinlock_lock fixture_lock
#define ihk_mc_spinlock_unlock fixture_unlock
#define syscall_signalfd_publish_bridge original_c_signalfd_publish_bridge
'''
(P/'original_reference.c').write_text(preamble+old)
inputs['original_callback']={'sha256':hashlib.sha256(old.encode()).hexdigest(),'bytes':len(old.encode()),'same_as_inventory_materialized_source':None}
M=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/source-materialization-1/materialized-source')
mc=(M/'kernel/syscall.c').read_text()
inputs['original_callback']['same_as_inventory_materialized_source']=old==cut(mc,'long\nsyscall_signalfd_publish_bridge(', '\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nlong sys_epoll_pwait')
assert inputs['original_callback']['same_as_inventory_materialized_source']
inputs['existing_consumer']={'sha256':hashlib.sha256(consumer.encode()).hexdigest(),'bytes':len(consumer.encode())}
(P/'source-bindings.json').write_text(json.dumps(inputs,indent=2)+'\n')
print('Private source preparation complete; no compiler or fixture execution.')
