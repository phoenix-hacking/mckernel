"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,copy,json,runpy,tempfile
D=Path(__file__).resolve().parent
source=(D/'prepare.py').read_text(); tree=ast.parse(source)
ns=runpy.run_path(str(D/'prepare.py'),run_name='not_main')
oldtree=ast.parse((ns['OLD'].parent/'prepare.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name!='main':
  before=next(x for x in oldtree.body if isinstance(x,ast.FunctionDef) and x.name==n.name)
  assert ast.dump(n,include_attributes=False)==ast.dump(before,include_attributes=False),n.name
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
cut=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='E.mkdir')
prefix=ast.FunctionDef(name='check',args=main.args,body=main.body[:cut],decorator_list=[]);mod=ast.fix_missing_locations(ast.Module(body=[prefix],type_ignores=[]));exec(compile(mod,'<actual-pre-effect-prefix>','exec'),ns)
gate=json.loads((D/'SOURCE-ACCEPTANCE.INPUT.json').read_text())
results=[]
with tempfile.TemporaryDirectory(prefix='gate-fixtures-',dir=str(D)) as tmp:
 ns['E']=Path(tmp)/'metadata'; target=Path(tmp)/'SOURCE-ACCEPTANCE.INPUT.json'
 def check(label,value,positive=False):
  target.write_text(json.dumps(value)); ok=False
  try:ns['check']();ok=True
  except (AssertionError,KeyError,TypeError):pass
  assert ok==positive,label
  assert not ns['E'].exists() and not ns['H'].exists(),label
  results.append(dict(case=label,accepted=ok))
 check('actual accepted seven-map prefix',gate,True)
 for label,change in [('null status',lambda g:g.update(status=None)),('missing one candidate',lambda g:g['candidates'].pop('smp_service.rs')),('stale hash',lambda g:g['candidates']['smp_service.rs'].update(sha256='0'*64)),('changed set mismatch',lambda g:g.update(changed_relative_rows=[])),('missing review',lambda g:g.update(independent_source_review=None)),('wrong actual fixture',lambda g:g['actual_tests'].update(sha256='0'*64))]:
  v=copy.deepcopy(gate);change(v);check(label,v)
(D/'OFFLINE-GATE-CHECKS.RESULT.json').write_text(json.dumps(dict(scope=__doc__,status='PASS_ACTUAL_HELPER_PRE_EFFECT_CHECKS',cases=results,unchanged_non_main_function_bodies=True,sourcecopy_during_checks=False),indent=2)+'\n')
runpy.run_path(str(D/'prepare.py'),run_name='__main__')
