"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source graph regression; no process or physical operation.
"""
from pathlib import Path
import ast
old=Path('../post119-resource-successor-source-1/accepted-current-physical-source-1/observe_current119_native_resources.py');new=Path(__file__).with_name('observe_current119_native_resources.py')
a=ast.parse(old.read_bytes());b=ast.parse(new.read_bytes())
def get(t):return {n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
x,y=get(a),get(b)
for k in x:
 if k!='observe':assert x[k]==y[k],k
f=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='observe');s=ast.unparse(f)
assert s.index('validate_adoption(')<s.index('append_post68_stage(')<s.index('physical.observe()')<s.index('validate_absence_reports([report], actors)')
assert 'for a in actors:' in s and "Path('/proc', str(a['pid']))" in s and "r['pgrp'] == a['group']" in s
print('PASS original retained metadata/route functions unchanged; appended actors precede original physical/census/PID/FD/group checks')
