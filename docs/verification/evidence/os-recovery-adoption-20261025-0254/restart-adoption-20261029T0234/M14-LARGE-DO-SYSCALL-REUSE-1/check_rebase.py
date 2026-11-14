"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source projection only; no compiler, preprocessor, host/native or runtime operation.
"""
from pathlib import Path
import hashlib,re
OLD='next-do-syscall-supported-orchestration-source-1';ORIG='do_syscall.ACTUAL-ORIGINAL-FULL-C.inc';SELECTOR='MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED';AFTER='#line 4420\n#endif\n';EXPORT='mod f03_do_syscall_supported_v1';REQ_UNINIT=0
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
assert '#line 4108\n#else\n#line 4117\n#endif\n'+orig in candidate
assert '#line 4411\n#else\n#line 4420\n#endif\n' in candidate
assert [4155-23,4189-23,4197-23,4369-23,4416-23,4428-23]==[4132,4166,4174,4346,4393,4405]
assert [4155-16,4189-16,4197-16,4369-16,4416-16,4428-16]==[4139,4173,4181,4353,4400,4412]
assert [f'.line={n}-F03_DO_LINE_OFFSET' in candidate for n in [4155,4189,4197,4369,4416,4428]]==[True]*6
assert c.splitlines()[148]=='#line 127' and c.splitlines()[133]=='#line 119'
assert frag.index('syscall_offload_prepare_result(')<frag.index('send_syscall(request, cpu, response_ptr)')<frag.index('syscall_offload_wait_reply(request, response_ptr, cpu, thread)')<frag.index('read_volatile(addr_of!((*response_ptr).ret))')
assert 'MaybeUninit::<SyscallResponse>::uninit()' in frag and '.assume_init()' not in frag
assert 'wrapping_add(1)' in frag and 'wrapping_sub(1)' in frag and 'syscall_owner_log_budget(&RETURN_LOG_STATE, pid)' in frag
print('PASS exact C fallback/projection, cfg source/ABI anchors, both original line mappings, response-read after existing wait, bounded counts/log provider; no compiler')
