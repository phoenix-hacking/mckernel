import ast,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
# Scalar contract replaces former CPU artifact with the full architecture syscall object.
f=P/'retention_observer.py';s=f.read_text().replace("'cpu.c.o'","'syscall.c.o'").replace('/arch/x86_64/kernel/cpu.c.o','/arch/x86_64/kernel/syscall.c.o').replace('/retained-artifacts/cpu.artifact','/retained-artifacts/syscall.artifact')
f.write_text(s)
f=P/'observe_reset_image_retirement.py';s=f.read_text().replace("def validate_artifact_authority(review):\n", "def validate_artifact_authority(review):\n    need(isinstance(ARTIFACT_EXPECTED_GUARD,dict) and isinstance(ARTIFACT_EXPECTED_PINS,dict) and set(ARTIFACT_EXPECTED_PINS)=={'syscall','process','rust','image'},'PENDING_EXACT_CLEAR_DEBUGREG_ARTIFACT_IDENTITIES')\n")
f.write_text(s)
# Rehash exact caller dependency, without creating publication/review authority.
f=P/'postjoin_readback.py';s=f.read_text();tree=ast.parse(s);lines=s.splitlines(keepends=True)
for n in reversed(tree.body):
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='OBSERVER_SHA':lines[n.lineno-1:n.end_lineno]=['OBSERVER_SHA = '+repr(hashlib.sha256((P/'observe_reset_image_retirement.py').read_bytes()).hexdigest())+'\n']
f.write_text(''.join(lines))
