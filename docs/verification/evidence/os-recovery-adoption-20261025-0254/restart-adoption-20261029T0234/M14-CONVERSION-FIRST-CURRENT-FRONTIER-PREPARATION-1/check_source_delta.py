"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source-scope regression; no runtime guard, proc or capture.
"""
from pathlib import Path
import ast
D=Path(__file__).resolve().parent;old=D.parent/'CURRENT119-MATCHING-NATIVE-PREPARATION-1/CURRENT119-NATIVE-WEEKLY-GUARD-1/coherent-native-entry-source-4'
def funcs(path):return {n.name:n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef)}
a=funcs(old/'observe_current119_native_resources.py');b=funcs(D/'observe_conversion_frontier.py')
for n in ('frontier','validate_adoption','append_post68_stage','append_resource1'):
 assert ast.dump(a[n],include_attributes=False)==ast.dump(b[n],include_attributes=False),n
s=ast.unparse(b['observe']);assert s.index('append_post68_stage(')<s.index('append_resource1(')<s.index('physical.observe()')<s.index('validate_absence_reports([report], actors)')
assert 'historical_root68_ledger=' in s and 'historical_current119_free=' in s and 'current_free_candidate=True' in s and 'independent_acceptance=False' in s and 'current_physical_clearance_pending=True' in s
class StripStrings(ast.NodeTransformer):
 def visit_Constant(self,node):
  if isinstance(node.value,str):return ast.copy_location(ast.Constant(value='TEXT'),node)
  return node
x=funcs(old/'native_operation_guard.py');y=funcs(D/'readonly_operation_guard.py')
for n in ('confirmed_weekly_ceiling','validate_operation','_evaluate'):
 assert ast.dump(StripStrings().visit(x[n]),include_attributes=False)==ast.dump(StripStrings().visit(y[n]),include_attributes=False),n
assert "OPERATION='current-conversion-frontier-readonly'" in (D/'readonly_operation_guard.py').read_text()
parent=(D/'root_capture_parent.py').read_text();assert "'--bindings'" in parent and "'--release-sha256'" in parent and 'observe_conversion_frontier.py' in parent and 'positive_wait4_join' in parent
assert not (D/'ROOT-ACTUAL-FRONTIER-OBSERVER-BINDING.json').exists() and not (D/'RELEASE.ACTUAL.json').exists()
print('PASS original 207 actor/receipt predicates and live Q/effective-min logic preserved, readonly operation distinct, historical3fd explicit, direct wait4 parent; unbound/no runtime')
