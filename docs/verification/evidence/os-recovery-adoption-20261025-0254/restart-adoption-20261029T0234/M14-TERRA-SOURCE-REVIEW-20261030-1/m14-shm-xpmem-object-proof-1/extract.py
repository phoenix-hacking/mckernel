from pathlib import Path
import hashlib
root=Path('/home/holden/mckernel')
process=root/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-COMBINED-BATCH-1/full-cutover-successor-1/complete-input-integration-1/final-profile-1/postimage/kernel/rust/process_helpers.rs'
obj=root/'kernel/rust/object_helpers.rs'
policy=root/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-COMBINED-BATCH-1/full-cutover-successor-1/complete-input-integration-1/final-profile-1/uti-desc-rust-owner-successor-1/postimage/kernel/rust/syscall_policy.rs'
parts=[]
for p, names in [(process,['process_add_range_mark_xpmem_bridge']), (obj,['shmobj_initial_flags_result','shmobj_indexed_flags_result']), (policy,['mmap_is_shared'])]:
 raw=p.read_bytes(); s=raw.decode(); print(p, hashlib.sha256(raw).hexdigest())
 for name in names:
  prefix=('pub unsafe extern "C" fn ' if name.startswith('process_') else 'pub extern "C" fn ')+name+'('
  a=s.index(prefix); b=s.index('{',a); depth=1;i=b+1
  while depth:
   if s[i]=='{':depth+=1
   elif s[i]=='}':depth-=1
   i+=1
  parts.append(s[a:i])
Path('actual-bodies.rs').write_text('\n\n'.join(parts)+'\n')
print('actual-bodies',hashlib.sha256(Path('actual-bodies.rs').read_bytes()).hexdigest())
