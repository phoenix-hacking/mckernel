"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure predecessor comparisons and exact Root template references; no live operations.
"""
from pathlib import Path
import ast,hashlib,json
D=Path(__file__).resolve().parent;old=D.parent
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for n in ('readonly_operation_guard.py','FIXED-READONLY-INPUTS.json','prepare_readonly_operation.py'):
 assert (old/n).read_bytes()==(D/n).read_bytes(),n
s=(old/'observe_conversion_frontier.py').read_text();t=(D/'observe_conversion_frontier.py').read_text();line=next(x for x in s.splitlines() if x.startswith('GUARD='));replacement='GUARD='+repr(ref(D/'readonly_operation_guard.py'));assert s.replace(line,replacement)==t
s=(old/'readonly_history_guard.py').read_text();t=(D/'readonly_history_guard.py').read_text();assert s.replace(str(old/'readonly_operation_guard.py'),str(D/'readonly_operation_guard.py'))==t
intent=json.loads((D/'ROOT-OPERATION-INTENT.TEMPLATE.NOT-AUTHORITY.json').read_bytes());closure=intent['context']['readonly_source_closure'];assert closure==dict(observer=ref(D/'observe_conversion_frontier.py'),physical_adapter=ref(D/'readonly_history_guard.py'),capture_parent=ref(D/'root_capture_parent.py'))
assert json.loads((D/'ROOT-GUARD-BINDING.TEMPLATE.NOT-AUTHORITY.json').read_bytes())['source']==ref(D/'readonly_operation_guard.py')
assert json.loads((D/'ROOT-OBSERVER-BINDING.TEMPLATE.NOT-AUTHORITY.json').read_bytes())['source']==ref(D/'observe_conversion_frontier.py')
assert json.loads((D/'RELEASE.TEMPLATE.NOT-AUTHORITY.json').read_bytes())['output']==str(D/'actual-frontier-1/OBSERVATION.json')
def argv(path):
 t=ast.parse(path.read_bytes());f=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='main');return ast.dump(next(x for x in f.body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='argv' for y in x.targets)),include_attributes=False)
assert argv(old/'root_capture_parent.py')==argv(D/'root_capture_parent.py'),'no capture command/profile change'
assert not (D/'ROOT-READONLY-GUARD-BINDING.ACTUAL.json').exists() and not (D/'RELEASE.ACTUAL.json').exists()
print('PASS byte-identical Q guard/formatter/fixed data, observer and adapter path-only retarget, exact updated source closure and unchanged parent capture argv; no runtime')
