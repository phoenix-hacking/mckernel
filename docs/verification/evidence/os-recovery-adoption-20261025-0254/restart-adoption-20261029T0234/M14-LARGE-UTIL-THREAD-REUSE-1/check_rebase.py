"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source projection only; no compiler, preprocessor, host/native or runtime operation.
"""
from pathlib import Path
import hashlib,re
OLD='next-util-thread-whole-owned-source-1';ORIG='ACTUAL-ORIGINAL-C.inc';SELECTOR='MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE';AFTER='#line 28400\n';EXPORT='mod f03_util_thread_whole_v1';REQ_UNINIT=1
D=Path(__file__).resolve().parent;C=Path('/home/holden/mckernel/kernel/syscall.c');R=Path('/home/holden/mckernel/kernel/rust/syscall_policy.rs')
BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(C)=='7b33e5de55ddba41036a57ddba3694c51afe7153ca7d779ceec0206734a15fd0'
assert digest(R)=='07cb4bff5a0a9a0d582ebc18e344e5cf06ccd6fc37005292c757ef0501ea50eb'
c=C.read_text();r=R.read_text();candidate=(D/'syscall.PRIVATE.c').read_text();newrust=(D/'syscall_policy.PRIVATE.rs').read_text();frag=(D/'RUST-BODY.REUSED.rs.inc').read_text();orig=(BASE/OLD/ORIG).read_text()
assert c.count(orig)==candidate.count(orig)==1 and newrust==r+'\n'+frag
start=candidate.index('#ifdef '+SELECTOR+'\n');body=candidate.index(orig,start);end=body+len(orig)
tail=candidate.index(AFTER,end)+len(AFTER);assert candidate[:start]+orig+candidate[tail:]==c,'exact original C projection'
assert frag.count(EXPORT)==1 and frag.count('MaybeUninit::<SyscallRequest>::uninit()')==REQ_UNINIT
assert c.count(EXPORT)==0 and r.count(EXPORT)==0
assert '#line 28299\n'+orig in candidate and AFTER=='#line 28400\n'
assert c.splitlines()[28871]=='#line 28297'
assert '28890,28899,28945,28948,28971,28972' not in candidate
assert '28314,28323,28369,28372,28395,28396' in candidate
assert [28935-576,28943-576,28953-576,28958-576]==[28359,28367,28377,28382]
assert all(f'.line={n}' in candidate for n in [28359,28367,28377,28382])
assert frag.count('write_volatile(addr_of_mut!((*request).args[5]), 0);')==1 and 'MaybeUninit::<SyscallRequest>::zeroed' not in frag
assert frag.index('write_volatile(addr_of_mut!((*thread).uti_state), *constants.add(3)')<frag.index('write_volatile(addr_of_mut!((*request).args[5]), 0);')<frag.index('existing_do_syscall(request,')
assert 'save_uctx(context.cast::<u8>().add((*layout).context).cast(), null_mut())' in frag
assert frag.index('read_volatile(field_ptr::<CInt>(context.cast(), (*layout).refill_tid))')<frag.index('release(context, (*origins).context_free)')
assert 'copy_nonoverlapping(arg.cast::<u8>()' in frag and 'f03_util_thread_descriptor_slot_v1' in frag
print('PASS exact C fallback/projection, logical metadata/line restoration, sole Root-approved args5=0, partial objects and saved context/refill order; no compiler')
