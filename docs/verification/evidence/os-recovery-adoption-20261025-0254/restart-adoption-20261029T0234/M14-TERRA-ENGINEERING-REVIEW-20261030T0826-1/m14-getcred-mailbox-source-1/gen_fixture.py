# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
p=Path('postimage/smp_application_syscall.rs').read_text(); q=Path('postimage/sysfs_memory.rs').read_text()
def extract(s, needle):
 start=s.index(needle); i=s.index('{',start); depth=0
 for j in range(i,len(s)):
  if s[j]=='{':depth+=1
  if s[j]=='}':
   depth-=1
   if depth==0:return s[start:j+1]
 raise ValueError(needle)
parts=[extract(p,'fn credential_request('),extract(p,'pub(crate) fn write_credentials('),extract(p,'pub(crate) fn return_value('),extract(p,'fn cancel_call('),extract(q,'pub(crate) fn copy_credentials(')]
Path('actual-methods.rs').write_text(parts[0]+'\nimpl<M> Mailbox<M> {\n'+ '\n'.join(parts[1:4])+'\n}\nimpl FakeMemory {\n'+parts[4]+'\n}\n')
