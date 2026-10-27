"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure AST/control-prefix checks only; no observation, process, flock or Docker call.
"""
from pathlib import Path
import ast,hashlib,json,types
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parents[2]/'ROOT-F03-F06-RUSTMM-STRICT235-NATIVE-ADMISSION-1/check_postnative_current.py'

def node(path,name):
 return next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name)
def probe_prefix(function,body,guard=None,uid=1000):
 events=[]
 def barrier():events.append('observation-start')
 namespace=dict(os=types.SimpleNamespace(getuid=lambda:uid,geteuid=lambda:uid),time=types.SimpleNamespace(time=lambda:1793122569),current_window_guard=guard,barrier=barrier)
 fn=ast.FunctionDef(name='control',args=function.args,body=body+[ast.Expr(value=ast.Call(func=ast.Name(id='barrier',ctx=ast.Load()),args=[],keywords=[]))],decorator_list=[])
 tree=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));exec(compile(tree,'pure-control-prefix','exec'),namespace)
 error=None
 try:namespace['control']()
 except (AssertionError,ValueError) as exc:error=type(exc).__name__
 return events,error

def main():
 original=ORIGINAL;successor=HERE/'check_postnative_current_new12h.py'
 assert hashlib.sha256(original.read_bytes()).hexdigest()=='9891cf1816c8639a8ca4a55e8ace130c049bd5ef65f1e126ef347353904be6fc'
 old=node(original,'observe');new=node(successor,'observe');checks=[]
 assert [ast.dump(n,include_attributes=False) for n in old.body[1:]]==[ast.dump(n,include_attributes=False) for n in new.body[2:]]
 checks.append('entire observation/probe/census/postcondition body AST unchanged after admission prefix')
 before={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name!='observe'}
 after={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(successor.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name in before}
 assert before==after;checks.append('all preexisting helper functions AST unchanged')
 events,error=probe_prefix(old,old.body[:1]);assert events==[] and error=='AssertionError';checks.append('original cutoff deterministically expires before observation')
 calls=[]
 def fail():calls.append('guard');raise ValueError('actual guard refused')
 events,error=probe_prefix(new,new.body[:2],fail);assert events==[] and error=='ValueError' and calls==['guard'];checks.append('current guard failure propagates before observation')
 calls=[]
 def passed():calls.append('guard');return [1793122569,904675.0,920013.0]
 events,error=probe_prefix(new,new.body[:2],passed);assert events==['observation-start'] and error is None and calls==['guard'];checks.append('passing current guard reaches observation barrier exactly once')
 calls=[];events,error=probe_prefix(new,new.body[:2],passed,uid=0);assert events==[] and error=='AssertionError' and calls==[];checks.append('ordinary UID requirement retained before guard')
 tree=ast.parse(successor.read_bytes());here=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='HERE' for t in n.targets));assert ast.literal_eval(here.value.args[0])==str(original.parent);checks.append('observer HERE/EVIDENCE preserve original retained roots')
 caller=ast.parse((HERE/'ROOT_capture_final_resource_new12h.py').read_bytes());assign=next(n for n in caller.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='A' for t in n.targets));assert ast.literal_eval(assign.value.args[0])==str(HERE.parent);checks.append('resource writer A preserves existing staged request/output namespace')
 report=dict(status='PASS_PURE_CONTROLS_ONLY',scope=__doc__.splitlines()[0],checks=checks,checks_count=len(checks),observe_calls=0,process_calls=0,flock_calls=0,Docker_calls=0,compiler_calls=0,workload_calls=0)
 (HERE/'PURE-TEST-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
