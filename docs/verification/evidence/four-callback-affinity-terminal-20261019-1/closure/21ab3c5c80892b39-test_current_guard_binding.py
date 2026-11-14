"""Run exact selected actualconfigure guard branches; all unrelated effects omitted."""
from pathlib import Path
import types,ast,json,hashlib
T=Path(__file__).resolve().parent;F=T/'current-guard-fixture-1';F.mkdir()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def load(p):m=types.ModuleType(p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
config=json.loads((T/'actual-terminal-source-config.json').read_text());g=load(T/'configure_fourleaf_terminal.py');(T/'cleanup_fourleaf.py').write_text(g.configure_cleanup(config));(T/'observe_four_leaf_image_retirement.py').write_text(g.configure(config));source=(T/'cleanup_fourleaf.py').read_text();tree=ast.parse(source);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='configure');selected=[]
for node in function.body:
 text=ast.get_source_segment(source,node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['guard_capture','ROOT_TERMINAL','WAITER_PIDS'] for t in node.targets):selected.append(node)
 elif isinstance(node,ast.If) and any(x in text for x in ['complete-current-guard-client-ledger-required','image-guard-proof-path','duplicate-client-pid']):selected.append(node)
 elif isinstance(node,ast.For) and 'positive-client-status-required' in text:selected.append(node)
assert len(selected)==7
# Invoke configure with only these exact seven actualsource statements enabled.
function.body=ast.parse("global ROOT_TERMINAL,WAITER_PIDS\nobs=value\nclient_rows=obs['client_ledger']\nproof_key='guard_proof'\n").body+selected
module=load(T/'cleanup_fourleaf.py');exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(T/'cleanup_fourleaf.py'),'exec'),module.__dict__)
physical=json.loads((T/'actual-fourleaf-physical-bindings.json').read_text());obs=dict(client_ledger=physical['ledger'],guard_proof=physical['guard']);module.configure(obs);assert len(module.WAITER_PIDS)==8 and module.ROOT_TERMINAL==Path(physical['guard']['path']);negative=0
for kind in ['old-parent','missing-client']:
 bad=dict(obs)
 if kind=='old-parent':bad['guard_proof']=dict(path='/home/holden/mckernel-work/scratch/native-rust-fp-release-image-guard-20261018-9582bfa72e354a06810bed72e3e36a71/guard-result.json')
 else:bad['client_ledger']=physical['ledger'][:-1]
 try:module.configure(bad)
 except module.Refusal:negative+=1
 else:raise AssertionError(kind+' accepted')
(F/'summary.json').write_text(json.dumps(dict(status='PASS_EXACT_ACTUALCONFIGURE_SELECTED_GUARD_BRANCHES_EFFECTS_OMITTED',actual_statements=7,current_clients=8,positive=1,negative=negative,source=ref(T/'cleanup_fourleaf.py'),observer=ref(T/'observe_four_leaf_image_retirement.py'),configurator=ref(T/'configure_fourleaf_terminal.py'),root_or_tool_effects=0),indent=2)+'\n');print('PASS actualconfigure guardbranches7/currentclients8; positive1/refusals2; effects0')
