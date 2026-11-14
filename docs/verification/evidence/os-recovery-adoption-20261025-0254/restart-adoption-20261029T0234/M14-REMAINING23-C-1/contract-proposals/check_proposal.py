from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent
root=here.parent.parent
src=root/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/syscall.c'
policy=root/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/rust/syscall_policy.rs'
c=src.read_text().splitlines();p=policy.read_text();leaf=(here/'ptrace_wakeup_log.UNSELECTED.rs.inc').read_text()
assert c[24878]=='#line 24424' and c[24884].strip()=='dkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\\n",'
assert 24424+24885-24880==24429
assert '#define PTRACE_CONTROL_LOG_WAKEUP_ENTER 4' in '\n'.join(c)
assert 'log(PTRACE_CONTROL_LOG_WAKEUP_ENTER, pid, data as CInt)' in p
assert 'fn ptrace_wakeup_log_bridge(event: CInt, value: CInt, result: CInt)' in leaf
assert 'if event == 4' in leaf and 'value, result as u32' in leaf
assert 'func: b"ptrace_wakeup_log_bridge\\0"' in leaf and 'line_flags: 24429' in leaf
assert 'f03_ptrace_wakeup_log_defined_u32_candidate' in leaf and 'f03_ptrace_wakeup_log_origin_profile_119' in leaf
vectors={str(x):format(x & 0xffffffff,'08x') for x in (-2147483648,-1,0,1,2147483647)}
assert vectors=={'-2147483648':'80000000','-1':'ffffffff','0':'00000000','1':'00000001','2147483647':'7fffffff'}
def info(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PROPOSED_UNSELECTED_REQUIRES_ROOT_CONTRACT','checks':['event 4 and C callback signature','modeled retained C file/function/line 24429','Rust proposed unsigned-int vararg formatting and writable descriptor','pure arithmetic examples only, not C parity or runtime'], 'u32_hex_examples':vectors,'proposal':info(here/'ptrace_wakeup_log.UNSELECTED.rs.inc'),'limitations':'No C selector or production integration. Actual source file/metadata, flags, vararg contract, compiler/link and functional proof remain open.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
