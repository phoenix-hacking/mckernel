# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,ast
C=Path(__file__).resolve().parent;P=C.parent

def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert pin(C/'source/smp_service.rs')['sha256']=='7d4948d7b0a5139048cf8085863ffcca43cbfff53024c34b5fd4281caed6f639'
assert pin(C/'PRIVATE-OMITTED-CALLER-CORRECTION.patch')['sha256']=='955a8e11b92a250f81b95d86a96202cb0ae9d64a67c0c9c850b0e581b9db8f33'
q=C/'check_actual_fail_callers.py';s=q.read_text();s=s.replace(chr(92)*2,chr(92));ast.parse(s);q.write_text(s)
old=json.loads((C/'SOURCE-BINDINGS.json').read_text());old['fixture_sources']={q.name:pin(q) for q in (C/'fixture').iterdir()};old['observer_only_correction']=dict(authority='Root directed one coherent observer-only correction after no-effect preflight failure. Pin failedSDK7postimages, fix doubledcheckerregex. Product frozen unchanged.',preserved_failure=pin(C/'observer-preflight-failure-1/FAILURE.json'),preserved_binding=pin(C/'observer-preflight-failure-1/SOURCE-BINDINGS.json'));B=C/'CURRENT-SOURCE-BINDINGS.json';B.write_text(json.dumps(old,indent=2)+'\n')
r=json.loads((C/'EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json').read_text());r['source_bindings']=pin(B);r['source_files'][str(q)]=pin(q);r['observer_only_correction']=old['observer_only_correction'];R=C/'EXACT-ORDINARY-FIXTURE-RECIPE.OBSERVER-CORRECTED.GRANTED.json';R.write_text(json.dumps(r,indent=2)+'\n')
d=(C/'run_fixture_owned.py').read_text().replace('EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json',R.name).replace('145317cc1767e220366a49e72d2386bf36de2feee5f09c08069644f6d4c7982a',pin(R)['sha256'])
a="for row in bindings['changes'].values():assert pin(Path(row['selected_original']['path']))==row['selected_original'] and pin(Path(row['canonical_preimage']['path']))==row['canonical_preimage']"
z="""assert pin(P.parent/'SOURCE-BINDINGS.json')['sha256']=='0fc72271dc63446af24a19d4ff50fa0e7122e7ff5f6a11b415cb890e857ee945'
for row in bindings['changes'].values():
 assert pin(Path(row['selected_original']['path']))==row['selected_original']
 observed=pin(Path(row['canonical_preimage']['path']));expected=row['private_postimage']
 assert observed['sha256']==expected['sha256'] and observed['bytes']==expected['bytes']"""
assert a in d;d=d.replace(a,z)
d=d.replace("canonical_inputs_unchanged=all(pin(Path(row['canonical_preimage']['path']))==row['canonical_preimage'] for row in bindings['changes'].values())", "canonical_failed_SDK7_postimages_unchanged=all(pin(Path(row['canonical_preimage']['path']))['sha256']==row['private_postimage']['sha256'] for row in bindings['changes'].values())")
d=d.replace("source_bindings=pin(P/'SOURCE-BINDINGS.json')", "source_bindings=pin(P/'CURRENT-SOURCE-BINDINGS.json')")
d=d.replace("SDK7_module_compile_or_native=None,", "SDK7_module_compile_or_native=None,observer_failure_preserved=recipe['observer_only_correction'],")
ast.parse(d);D=C/'run_fixture_owned_observer_corrected.py';D.write_text(d)
print(json.dumps(dict(recipe=pin(R),driver=pin(D),checker=pin(q),source_binding=pin(B))))
