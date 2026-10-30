from pathlib import Path
import hashlib
p=Path('postimage/kernel/rust/syscall_policy.rs');s=p.read_text();parts=[]
for name in ['getcred_body_result','syscall_refresh_cred_fields_body_result']:
 marker='pub unsafe extern "C" fn '+name+'(';a=s.index(marker);b=s.index('{',a);i=b+1;depth=1
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 parts.append(s[a:i])
Path('actual-bodies.rs').write_text('\n\n'.join(parts)+'\n')
print('policy',hashlib.sha256(p.read_bytes()).hexdigest(),'bodies',hashlib.sha256(Path('actual-bodies.rs').read_bytes()).hexdigest())
