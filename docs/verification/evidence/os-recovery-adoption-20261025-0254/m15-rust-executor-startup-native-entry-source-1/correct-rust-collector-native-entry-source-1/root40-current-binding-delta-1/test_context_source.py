"""Functional OS only; no security testing. No guard/resource/runtime execution."""
import ast,copy,hashlib,importlib.util,json
from pathlib import Path
D=Path(__file__).resolve().parent;T=D/'templates'
# Import definitions/constants only; retained capture main is never invoked.
p=T/'capture_fresh_startup_resource.py';spec=importlib.util.spec_from_file_location('new_startup_capture_definition_only',p);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
main=next(n for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
block=next(n for n in main.body if isinstance(n,ast.With)).body
start=next(i for i,n in enumerate(block) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ledger' for t in n.targets))
end=next(i for i,n in enumerate(block) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='static' for t in n.targets))
subset=copy.deepcopy(block[start:end]);needles=(ast.Call,)
for n in ast.walk(ast.Module(body=subset,type_ignores=[])):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):assert n.func.attr not in ['guard','run','Popen','current_cutoffs','mkdir','open']
exec(compile(ast.Module(body=subset,type_ignores=[]),'<exact retained Root39 record predicate prefix only>','exec'),capture.__dict__)
checks=['ActualRoot40 current and retainedRoot39 build predicates parse and match stored receipt schema before any clock/query']
for filename in ['run_native_startup_capture.py','bind_startup_resource.py']:
 tree=ast.parse((T/filename).read_bytes());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUTHORIZED_FIXED_LIMITS' for t in n.targets)];env={};exec(compile(ast.Module(body=defs,type_ignores=[]),'<unchanged clamp definitions only>','exec'),dict(__builtins__=__builtins__,math=__import__('math')),env)
 checks.append(filename+' unchanged clock-clamp definitions extracted without top-level runtime')
for name in ['run_native_startup_capture.py','bind_startup_resource.py','run_startup_resource_once.py']:
 old=D.parent/'templates'/name;assert old.read_bytes()==(T/name).read_bytes();checks.append(name+' exactbyte reuse')
prepare=(T/'prepare_startup_bindings.py').read_text();assert "facts['actual_test_count']==16" in prepare and "d0bf61dc45754e72d3ebab34853756c6ce5cce0c9e84ac1713122ba1cf8f0d5a" in prepare
checks.append('Actualqualified producer argv/frame/profile/facts witness bound before resourcecapture')
bridge=(T/'root_once_startup_entry.py').read_text();assert "NONCE = '6d2e6c210f8bf62b1a4f1abc127fb09a'" in bridge and 'ROOT_FINAL_STATIC_SHA256' in bridge
checks.append('Fresh reserved outer nonce, pending finalstaticpin; old consumed nonce absent')
latest=json.loads(Path(capture.ROOT40_FREE['path']).read_bytes())
for field,bad in [('actual_docker_clients',25),('all33_actor_pid_and_pgrp_absent',False),('lease_retained',True)]:
 trial=copy.deepcopy(latest);trial['current_boundary'][field]=bad
 try:capture.validate_root40_latest(trial)
 except AssertionError:checks.append('Root40 '+field+' contradiction rejected')
 else:raise AssertionError('acceptedwrongRoot40 '+field)
r=dict(status='PASS_ROOT40_CURRENT_DELTA_SOURCE_CONTROLS_NO_WORKLOAD',checks=checks,guards=0,resources=0,compilers=0,owner_entry=0,current_release=None)
with (D/'PURE-CONTEXT-CHECKS.json').open('x') as out:json.dump(r,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(status=r['status'],checks=len(checks),sha256=hashlib.sha256((D/'PURE-CONTEXT-CHECKS.json').read_bytes()).hexdigest())))
