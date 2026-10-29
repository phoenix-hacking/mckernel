"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only template and in-memory clamp regression; no runtime/process/host operation.
"""
from pathlib import Path
import ast,hashlib,json,math
D=Path(__file__).resolve().parent
names=['root_once_startup_entry.py','bind_startup_resource.py','capture_fresh_startup_resource.py','prepare_startup_bindings.py','run_native_startup_capture.py','run_startup_resource_once.py']
for n in names:ast.parse((D/n).read_bytes(),filename=n)
b=json.loads((D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes());assert b['author'] is b['nonce'] is b['source_authority'] is b['case_capability'] is b['nonce_reservation'] is None
assert b['expected_new_image_sha256']=='759fe1cb2dda4a87ab521b79b17e771514c4da042cbfcd3344b6c5d670b17a31'
assert b['root_ledger35']['sha256']=='d948ba50890c2e735bb92b541c997694154c9cf62963e748bf47f1a992b57022' and b['current_boundary']['sha256']=='acebac5fd5bc97597251bff18b97518a7bf3868ad28900e59d6d56aa0d2599e3' and b['latest_serial_operation_physical_acceptance']['sha256']=='3fd1a6facf34a9e6ac9259526da96ddee2dd22c6032ee47b37be97e56d0086e3'
assert b['offline_manifest']['sha256']=='25bb59f824698dc3141830ef7108984379399dc69684970e9b3a79e61d48ac8c' and b['artifact_acceptance']['sha256']=='3324128344411d3e8c0c87ce970b3fc851edc87507613b2186944f7be1158c6c'
assert b['current_observer_source']['sha256']=='ef342103d56978fb7656a2057b12ff90b653f55b4f2428ca902063910d561fa7' and b['current_observer_review'] is None
for flag in ['--attempt-parent','--nonce','--manifest','--manifest-sha256']:assert b['exact_argv'][b['exact_argv'].index(flag)+1].startswith('ROOT_UNBOUND_')
entry=(D/'root_once_startup_entry.py').read_text();helper=(D/'run_native_startup_capture.py').read_bytes();assert "HELPER_SHA = '"+hashlib.sha256(helper).hexdigest()+"'" in entry
assert "ROOT_FINAL_STATIC_SHA256" in entry and "ROOT_NEW_UNUSED_235_NONCE" in entry and "/ROOT_ACTUAL_STARTUP_DIRECTORY" in entry
profile=hashlib.sha256((json.dumps(b['profile'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest();assert "PROFILE_SHA = '"+profile+"'" in entry
for name in names:
 s=(D/name).read_text();assert 'de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024' not in s and '1793165769' not in s and "physical['Root54']" not in s
cap=(D/'capture_fresh_startup_resource.py').read_text();assert cap.index('validate_post119_route(st,context,review)')<cap.index('observer.observe()') and 'ef342103d56978fb7656a2057b12ff90b653f55b4f2428ca902063910d561fa7' in cap
prepare=(D/'prepare_startup_bindings.py').read_text();assert "==73 and ledger['current_physical_clearance_pending'] is False" in prepare and "boundary['nonce_ledger']==b['root_ledger35']" in prepare
# Existing consumer arithmetic is executed in isolation, never import its top-level native code.
def pure(path,selected):
 tree=ast.parse(path.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in selected or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUTHORIZED_FIXED_LIMITS' for t in n.targets)];ns={'math':math};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns);return ns
h=pure(D/'run_native_startup_capture.py',{'cutoff_triplet','entry_clamps'});caps=(1000.,2000.,3000.);now=(900.,1900.,2900.);observed=(899.,1899.,2899.)
assert h['entry_clamps'](now,observed,caps,caps,(999.,1999.,2999.))['effectiveCutoffs']==[999.,1999.,2999.]
for idx in range(3):
 c=list(now);c[idx]=caps[idx]
 try:h['entry_clamps'](c,observed,caps,caps,caps)
 except ValueError:pass
 else:raise AssertionError('deadline equality did not refuse')
print('PASS six source templates parse; 119/Root68/free/observer pins; no legacy cutoffs, nonce or image; helper/profile pin; three clock equality refusals; no execution')
