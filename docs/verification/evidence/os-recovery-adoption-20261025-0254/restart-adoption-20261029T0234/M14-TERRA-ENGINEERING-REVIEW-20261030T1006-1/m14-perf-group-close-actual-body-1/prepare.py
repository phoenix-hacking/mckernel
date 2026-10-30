from pathlib import Path
import hashlib,json
p=Path(__file__).parent;prev=p.parent/'m14-perf-group-actual-body-rust-correction-1';source=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/syscall_policy.rs')
def block(s,start):
 i=s.index(start);j=s.index('{',i);n=0
 for k in range(j,len(s)):
  if s[k]=='{':n+=1
  elif s[k]=='}':
   n-=1
   if n==0:return s[i:k+1]
 raise ValueError(start)
old=(prev/'main.rs').read_text();prefix=old[:old.index('fn main(){')];prefix=prefix.replace('type SyscallCopyFromUserFn=', 'type SyscallMckfdFreeFn=unsafe extern "C" fn(*mut c_void);\ntype SyscallCopyFromUserFn=');prefix=prefix.replace('nr:i32,_pad:i32,status:u64}', 'nr:i32,_pad:i32,status:u64,extra_reg:i32,extra_idx:i32}')
(p/'main.rs').write_text(prefix+(p/'main-suffix.txt').read_text());(p/'rust_actual.rs').write_text((prev/'rust_actual.rs').read_text()+'\n'+block(source.read_text(),'pub unsafe extern "C" fn perf_close_body_result(')+'\n');sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();(p/'INPUTS.json').write_text(json.dumps({str(x):sha(x) for x in (source,prev/'main.rs',prev/'rust_actual.rs',p.parent/'m14-perf-group-actual-body-correction-1/c_actual.o')},indent=2)+'\n')
