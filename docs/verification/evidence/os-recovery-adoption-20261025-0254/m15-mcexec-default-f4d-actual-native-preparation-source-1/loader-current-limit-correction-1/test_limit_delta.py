"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure current-ceiling delta controls; no wrapper/loader/guard/main execution.
"""
import ast,copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
checks=[]
def need(ok,why):
    if not ok:raise ValueError(why)
def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('bad reservation accepted')
old=json.loads((HERE.parent/'LOADER-THREE-COMMANDS.NOT-RELEASED.json').read_bytes());new=json.loads((HERE/'LOADER-THREE-COMMANDS.NOT-RELEASED.json').read_bytes());restored=copy.deepcopy(new);restored['profile']['aggregate_memory_ceiling_bytes']=23941543572;assert restored==old;checks.append('only_packet_field_current_ceiling_changed')
assert new['commands']==old['commands'] and len(new['inputs'])==14 and new['inputs']==old['inputs'];checks.append('all3argv14inputs_oracles_paths_profile_otherfields_exact')
s=HERE/'run_installed_loader_h990_once.py';tree=ast.parse(s.read_bytes());assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='reserved' for t in n.targets));index=tree.body.index(assignment);guard=tree.body[index+1]
assert isinstance(guard,ast.Expr) and isinstance(guard.value,ast.Call)
code=compile(ast.Module(body=[assignment,guard],type_ignores=[]),'literal_current_reservation_guard','exec')
for amount in (536870912,23259332608):exec(code,dict(actual_grant=dict(aggregate_reserved_memory_bytes=amount),p=new,need=need));checks.append('reservation_'+str(amount)+'_passes')
for amount in (None,True,536870911,23259332609,23941543572,'23259332608',23259332608.0):rejected(lambda:exec(code,dict(actual_grant=dict(aggregate_reserved_memory_bytes=amount),p=new,need=need)))
checks.append('missing_boolean_underreserved_overcurrent_oldceiling_string_float_rejected')
oldtree=ast.parse((HERE.parent/s.name).read_bytes())
for name in ('inputs','capacity'):
    get=lambda t:next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(get(oldtree),include_attributes=False)==ast.dump(get(tree),include_attributes=False)
checks.append('original_stableFD_and_capacity_AST_exact')
g=json.loads((HERE/'ROOT-LOADER-GRANT.TEMPLATE.NOT-AUTHORITY.json').read_bytes());assert g['profile']==new['profile'] and g['aggregate_reserved_memory_bytes'] is None
for key,file in [('packet',HERE/'LOADER-THREE-COMMANDS.NOT-RELEASED.json'),('source',s)]:assert g[key]==dict(path=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest())
checks.append('template_actual_new_packet_wrapper_profile_pins_exact_not_granted')
result=dict(status='PASS_PURE_CURRENT_INVOCATION_MEMORY_LIMIT_CORRECTION',scope=new['scope'],checks=checks,actual_runtime_guard_admission_loader=False,execution_authority=False)
(HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result,sort_keys=True))
