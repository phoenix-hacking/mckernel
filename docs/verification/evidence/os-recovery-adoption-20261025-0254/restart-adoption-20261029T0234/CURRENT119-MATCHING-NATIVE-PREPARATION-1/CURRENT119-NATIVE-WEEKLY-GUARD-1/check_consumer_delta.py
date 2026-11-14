"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only comparison; candidate templates remain UNBOUND, never execute them.
"""
from pathlib import Path
import ast,hashlib,json
D=Path(__file__).resolve().parent;T=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/templates');p=D/'native_operation_guard.py';sha=hashlib.sha256(p.read_bytes()).hexdigest();oldsha='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0';oldguard='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py';oldcaps='(1793165769.0, 947874.5689514667, 963213.6960030915)';newcaps='(1793774133, 1556235.568922472, 1571573.6959699572)'
for name in ['root_once_startup_entry.py','capture_fresh_startup_resource.py','run_native_startup_capture.py','bind_startup_resource.py']:
 s=(T/name).read_text();actual=(D/'candidate-templates'/name).read_text()
 if name=='root_once_startup_entry.py':s=s.replace("GUARD = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'",'GUARD = Path('+repr(str(p))+')')
 if name=='capture_fresh_startup_resource.py':s=s.replace('GUARD=Path('+repr(oldguard)+')','GUARD=Path('+repr(str(p))+')')
 if name=='run_native_startup_capture.py':s=s.replace('policy=Path('+repr(oldguard)+')','policy=Path('+repr(str(p))+')').replace('de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024','759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31')
 if name!='bind_startup_resource.py':s=s.replace(oldsha,sha)
 if name in ('run_native_startup_capture.py','bind_startup_resource.py'):s=s.replace(oldcaps,newcaps)
 assert s==actual;ast.parse(actual)
old=ast.parse((T/'run_native_startup_capture.py').read_bytes());new=ast.parse((D/'candidate-templates/run_native_startup_capture.py').read_bytes());fn=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef)and x.name==n)
for n in ('cutoff_triplet','entry_clamps'):assert ast.dump(fn(old,n),include_attributes=False)==ast.dump(fn(new,n),include_attributes=False)
assert "physical['Root54']" in (D/'candidate-templates/capture_fresh_startup_resource.py').read_text(),'unbound historical consumer explicitly remains pending'
assert not (D/'ROOT-NATIVE-GUARD-BINDING.ACTUAL.json').exists()
print('PASS four exact guard/cap/image direct source substitutions; native entry clamps unchanged; Root54 consumer remains explicitly unresolved; no actual binding')
