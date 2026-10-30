"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only changed-artifact inventory, using frozen selected ELF readers.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('context.py').read_text(),str(Path(__file__).with_name('context.py')),'exec'))
base=read(A/'M14-CURRENT119-ACTUAL-ARTIFACT-QUALIFICATION-1/independent-review-1/INDEPENDENT-ACTUAL-CURRENT119-ARTIFACT-ACCEPTANCE.json')
baserust=elf(auth(base['tuple']['Rust']));basekc=elf(auth(base['tuple']['generic_C']));baseimg=Final(auth(base['tuple']['image']))
removed=sorted(set(allocated(basekc,2))-set(allocated(kc,2)));added=sorted(set(allocated(kc,2))-set(allocated(basekc,2)))
print('CDELTA',removed,added)
print('RUSTGLOBALnew',sorted(set(allocated(new,2))-set(allocated(baserust,2))))
changed=[]
for n in sorted(set(allocated(new,2))&set(allocated(baserust,2))):
 a=own(baserust,n);b=own(new,n)
 try:
  _,ab,ar,_=relocated_function(baserust,n);_,bb,br,_=relocated_function(new,n)
  if (a['type'],a['bind'],a['size'],ab,ar)!=(b['type'],b['bind'],b['size'],bb,br):changed.append(n)
 except Exception as e: changed.append((n,repr(e)))
print('RUSTCHANGED',changed)
(D/'CHANGE-SCAN.ACTUAL.json').write_text(json.dumps(dict(removed_C=removed,added_C=added,Rust_new=sorted(set(allocated(new,2))-set(allocated(baserust,2))),Rust_changed=changed),indent=2)+'\n')
