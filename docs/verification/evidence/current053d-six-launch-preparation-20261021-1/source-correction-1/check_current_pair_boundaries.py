"""Finite actual changed tuple boundary + unchanged oracle source check; no staging.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,os
C=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-three-rounds-20261020-1/stage-preparation-1')
need=lambda x,s: None if x else (_ for _ in ()).throw(AssertionError(s))
need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 only')
spec=importlib.util.spec_from_file_location('_actual_current_pair_tuple',C/'current_image_authority.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=json.loads((C/'CURRENT-TUPLE-AUTHORITY.json').read_bytes())
actual=m.validate(a,a['runtime_image'],a['runtime_launcher'],a['runtime_modules'])
controls=[]
for name,key in [('wrong_kernel','runtime_image'),('wrong_launcher','runtime_launcher'),('wrong_module','runtime_modules'),('wrong_authority','consumer_contract')]:
 b=copy.deepcopy(a)
 if key=='runtime_modules':b[key][0]['sha256']='0'*64
 else:b[key]['sha256']='0'*64
 try:m.validate(b,b['runtime_image'],b['runtime_launcher'],b['runtime_modules'])
 except ValueError as error:controls.append(dict(name=name,message=str(error)))
 else:raise AssertionError('invalid tuple admitted '+name)
old=(OLD/'native_diagnostic.py').read_text();new=(C/'native_diagnostic.py').read_text()
def funcs(s):return [n for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
afunc=funcs(old);bfunc=funcs(new);need(len(afunc)==len(bfunc),'whole function inventory unchanged')
changed=[(n.name,n.lineno) for n,z in zip(afunc,bfunc) if ast.dump(n,include_attributes=False)!=ast.dump(z,include_attributes=False)]
need(len(changed)==1 and changed[0][0]=='_validate_manifest','only actual pair manifest gate changed; every evaluator/oracle/function intact')
original=json.loads((OLD/'stage-three-rounds-1/manifest.json').read_bytes())
need(original['pair_rounds']==3 and len(original['pair']['apps'])==2,'retained exact3x2')
need([len(bytes.fromhex(x['oracle']['stdout_hex'])) for x in original['pair']['apps']]==[387,254],'strict literal outputs unchanged')
need([x['oracle']['exit_code'] for x in original['pair']['apps']]==[0,0] and all(x['oracle']['stderr_hex']=='' and x['timeout_ms']==10000 for x in original['pair']['apps']),'strict exit/emptyerr/deadline unchanged')
need(not (C/'stage-current-six-launch-1').exists(),'no actual stage permitted in this check')
print(json.dumps(dict(status='PASS_ACTUAL_CURRENT_PAIR_TUPLE_AND_UNCHANGED_ORACLE_SOURCE_ONLY',positive_actual_authority_join=True,refusals=controls,refusal_count=len(controls),unchanged_complete_functions=len(afunc)-1,changed_functions=changed,rounds=3,apps=6,stage_executed=False,compiler_executed=False,guest_executed=False,root_executed=False,new_runtime_acceptance=False),sort_keys=True))
