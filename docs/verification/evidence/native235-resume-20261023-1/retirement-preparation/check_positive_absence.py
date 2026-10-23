"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
from unittest.mock import patch
import ast,errno,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7}
S=D/'readonly_current_mutex_paths_positive.py';tree=ast.parse(S.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='require_absence');ns=dict(os=os,errno=errno);exec(compile(ast.Module(body=[fn],type_ignores=[]),str(S),'exec'),ns);check=ns['require_absence']
F=D/'positive-absence-fixtures-1';F.mkdir(mode=0o700);present=F/'present';present.write_text('present\n');link=F/'symlink';link.symlink_to(F/'missing-target');absent=F/'missing'
results=[]
check([absent]);results.append('actual ENOENT accepted')
for p in (present,link):
 try:check([p])
 except RuntimeError:results.append('actual '+p.name+' rejected')
 else:raise AssertionError('present entry accepted')
for number,kind in [(errno.EACCES,PermissionError),(errno.EIO,OSError),(errno.ENOTDIR,NotADirectoryError)]:
 exc=kind(number,'fixture')
 with patch.object(os,'lstat',side_effect=exc):
  try:check([absent])
  except OSError as got:assert got is exc;results.append(errno.errorcode[number]+' propagated unchanged')
  else:raise AssertionError('non-ENOENT accepted')
# Even a FileNotFoundError with an inconsistent errno cannot establish ENOENT.
exc=FileNotFoundError(errno.EIO,'fixture')
with patch.object(os,'lstat',side_effect=exc):
 try:check([absent])
 except FileNotFoundError as got:assert got is exc;results.append('FileNotFoundError EIO propagated unchanged')
 else:raise AssertionError('non-ENOENT FileNotFoundError accepted')
# Original acquisition/readback/release exact statements and eight paths preserved.
a=ast.parse((D/'readonly_current_mutex_paths.py').read_text());b=ast.parse(S.read_text())
ignore=lambda n:isinstance(n,(ast.Import,ast.FunctionDef)) or (isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='paths'for z in n.targets)) or (isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id in ('need','require_absence')and (n.value.func.id=='require_absence' or any(isinstance(x,ast.Constant)and x.value=='fresh exact current SDK/image/launcher ownership paths absent'for x in n.value.args)))
assert [ast.dump(n)for n in a.body if not ignore(n)]==[ast.dump(n)for n in b.body if not ignore(n)]
r=dict(scope=__doc__,status='PASS_7_ACTUAL_FUNCTION_OBSERVATIONS_AND_MUTEX_STATEMENT_PRESERVATION',observations=results,root_Docker_native_operations=0,physical_acceptance=False,family_findings=1,bounded_corrections=1,new_test_failures=0)
(D/'POSITIVE-ABSENCE-TEST-RECEIPT.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(status=r['status'],observations=len(results))))
