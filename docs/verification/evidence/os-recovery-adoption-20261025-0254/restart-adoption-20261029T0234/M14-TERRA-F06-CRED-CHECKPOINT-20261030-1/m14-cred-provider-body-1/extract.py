from pathlib import Path
import hashlib
p=Path('/home/holden/mckernel/executer/kernel/mcctrl/rust/mcctrl_helpers.rs');src=p.read_text();parts=[]
for name in ['mcctrl_control_fill_cred_values','mcctrl_control_getcred_body_result']:
 marker=('unsafe fn ' if name.endswith('values') else 'pub unsafe extern "C" fn ')+name+'('
 start=src.index(marker);i=src.index('{',start)+1;depth=1
 while depth:
  if src[i]=='{':depth+=1
  elif src[i]=='}':depth-=1
  i+=1
 parts.append(src[start:i])
Path('actual-bodies.rs').write_text('\n\n'.join(parts)+'\n')
print('source',str(p),hashlib.sha256(p.read_bytes()).hexdigest())
print('bodies',hashlib.sha256(Path('actual-bodies.rs').read_bytes()).hexdigest())
