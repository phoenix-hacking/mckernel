"""Functional OS source-only pure tests; no security testing or live effects."""
import ast,copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'guardian_guard.py')};exec(compile((D/'guardian_guard.py').read_text(),str(D/'guardian_guard.py'),'exec'),ns)
checks=[]
def reject(fn):
 try:fn()
 except (ValueError,TypeError,KeyError):return
 raise AssertionError('unexpected acceptance')
def row(reset=1793774133,used=30):return ns['weekly_row'](dict(limitId='codex',primary=dict(windowDurationMins=10080,resetsAt=reset,usedPercent=used)))
for reset in (1793774131,1793774132,1793774133,1793774134,1793774135):
 r=row(reset);assert ns['validate_confirmed_row'](r)==r;assert r['canonicalResetsAt']==1793774133
checks.append('same authorized interval corrections including beyond old jitter tolerance accepted, canonical unchanged')
for reset in (1793251609,1793251609+604801,None):reject(lambda:ns['validate_confirmed_row'](row(reset)))
for used in (100,None,float('nan'),-1,101):reject(lambda:ns['validate_confirmed_row'](row(used=used)))
checks.append('different authorized interval, unknown/exhausted/nonfinite usage refused')
reject(ns['require_live_binding']);checks.append('live binding explicitly refuses while unbound')
source=ast.parse((D/'guardian_guard.py').read_text());policy=ast.parse(Path(json.loads((D/'INPUTS.json').read_text())['policy']['path']).read_text())
def node(t,name):return next(n for n in t.body if isinstance(n,ast.FunctionDef)and n.name==name)
assert ast.dump(node(source,'weekly_row'),include_attributes=False)==ast.dump(node(policy,'weekly_row'),include_attributes=False)
checks.append('weekly_row AST exact reviewed policy copy')
old=ast.parse((D.parent/'guardian_guard.py').read_text());changed={'validate','validate_armed_metadata','weekly_row','validate_weekly_account','guard'}
for f in old.body:
 if isinstance(f,ast.FunctionDef)and f.name not in changed:assert ast.dump(f,include_attributes=False)==ast.dump(node(source,f.name),include_attributes=False),f.name
checks.append('all undeclared predecessor function ASTs exact')
shared={'__file__':str(D/'operation_window_guard.py')};exec(compile((D/'operation_window_guard.py').read_text(),str(D/'operation_window_guard.py'),'exec'),shared);reject(shared['bound'])
checks.append('shared operation guard unbound refuses before metadata IO')
(D/'PURE-TEST.json').write_text(json.dumps(dict(status='PASS_PURE_SOURCE_ONLY',checks=checks,live_effects=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',groups=len(checks))))
