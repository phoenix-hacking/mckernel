"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap AST/literal actual-metadata regression for only two reported observer defects.
"""
from pathlib import Path
import ast,copy,hashlib,json,unittest
D=Path(__file__).resolve().parent;T=D/'validator-templates';EXPECTED=json.loads((D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text());P=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text())
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
clone=ast.parse((T/'qualify_clone_pointer_and_warning_suffix.py').read_text());expr=next(k.value for n in ast.walk(clone) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' for k in n.keywords if k.arg=='new_process_object')
provider=ast.parse((T/'qualify_next_providers.py').read_text());checks={}
for node in ast.walk(provider):
 if isinstance(node,ast.Assert) and isinstance(node.msg,ast.Constant) and isinstance(node.msg.value,str):
  if node.msg.value in ['actual predecessor reference differs from prepublished baseline','prepublished baseline C object bytes changed','actual remaining C functions differ from prepublished exact set']:checks[node.msg.value]=node
assert len(checks)==3

def execute_check(message,ns):exec(compile(ast.fix_missing_locations(ast.Module(body=[checks[message]],type_ignores=[])),'corrected exact contract assertion','exec'),ns)
class OnlyTwoCorrections(unittest.TestCase):
 def test_report_uses_authenticated_retained_process_not_host_placeholder(self):
  actual=eval(compile(ast.Expression(expr),'retained process report expression','eval'),dict(Path=Path,ref=ref,P=P,B=Path('/must-never-read-output-placeholder')))
  expected=next(r['source'] for r in P['inputs']['objects'] if r['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o');self.assertEqual(actual,expected);self.assertEqual(actual['bytes'],73408);self.assertEqual(actual['sha256'],'b8168c1f52369f7909bf174fe1c926a4a4a3be4a63cd0667741841680b0ca289')
 def test_exact_bound_actual_baseline_bytes(self):
  for token,row in EXPECTED['baseline_C_objects'].items():
   baseline=row['object'];ns=dict(Path=Path,ref=ref,row=dict(source=baseline),baseline_ref=baseline)
   execute_check('actual predecessor reference differs from prepublished baseline',ns);execute_check('prepublished baseline C object bytes changed',ns)
 def test_changed_predecessor_profile_reference_rejected(self):
  baseline=next(iter(EXPECTED['baseline_C_objects'].values()))['object'];ns=dict(row=dict(source=dict(baseline,sha256='0'*64)),baseline_ref=baseline)
  with self.assertRaises(AssertionError):execute_check('actual predecessor reference differs from prepublished baseline',ns)
 def test_changed_baseline_bytes_binding_rejected(self):
  baseline=dict(next(iter(EXPECTED['baseline_C_objects'].values()))['object'],sha256='0'*64)
  with self.assertRaises(AssertionError):execute_check('prepublished baseline C object bytes changed',dict(Path=Path,ref=ref,baseline_ref=baseline))
 def test_exact_remaining_names_and_both_missing_extra_rejected(self):
  for token,contract in EXPECTED['expected_C_function_sets'].items():
   names=contract['expected_remaining_names'];ns=dict(EXPECTED=EXPECTED,token=token,after=dict.fromkeys(names));execute_check('actual remaining C functions differ from prepublished exact set',ns)
   for altered in [names[:-1],names+['unexpected_allocated_C_function']]:
    with self.subTest(token=token,n=len(altered)),self.assertRaises(AssertionError):execute_check('actual remaining C functions differ from prepublished exact set',dict(ns,after=dict.fromkeys(altered)))
if __name__=='__main__':unittest.main(verbosity=2)
