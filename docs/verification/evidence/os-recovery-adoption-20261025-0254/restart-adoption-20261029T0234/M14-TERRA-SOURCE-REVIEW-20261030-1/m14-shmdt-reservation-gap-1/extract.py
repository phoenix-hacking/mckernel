from pathlib import Path
import hashlib
p=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-REMAINING23-COMBINED-BATCH-1/full-cutover-successor-1/complete-input-integration-1/final-profile-1/uti-desc-rust-owner-successor-1/postimage/kernel/rust/syscall_policy.rs')
s=p.read_text()
expected='d1151a64f122d75816f039481dfe19540825a0cc2f4b5bf69123f182241b60b4'
assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
parts=[]
for name in ('field_ptr','memlock_range_ulong','memlock_range_ptr','shmdt_log','shmdt_body_result'):
 token=('pub unsafe extern "C" fn ' if name == 'shmdt_body_result' else 'unsafe fn ')+name+'('
 if name=='field_ptr': token='unsafe fn field_ptr<T>('
 a=s.index(token); b=s.index('{',a); i=b+1; depth=1
 while depth:
  if s[i]=='{': depth+=1
  elif s[i]=='}': depth-=1
  i+=1
 parts.append(s[a:i])
Path('actual-bodies.rs').write_text('\n\n'.join(parts)+'\n')
print('source',expected,str(p))
print('actual-bodies',hashlib.sha256(Path('actual-bodies.rs').read_bytes()).hexdigest())
