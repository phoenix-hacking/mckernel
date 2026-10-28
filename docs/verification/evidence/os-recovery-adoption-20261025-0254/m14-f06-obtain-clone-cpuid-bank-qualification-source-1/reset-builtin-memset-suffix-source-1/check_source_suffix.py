"""Functional OS only; no security testing. Read-only retainedprefix/suffix checks."""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent
p=D/'PROFILE.NOT-GRANTED.json';assert hashlib.sha256(p.read_bytes()).hexdigest()=='4bab567e4f7a181f23278a3345e20278ef99d6d0d968649aa059f6698fa215e7'
x=json.loads(p.read_bytes());runner=next(r for r in x['inputs'] if r['path'].endswith('/ordinary-host-new12h-runner-source-1/run_new12h_host.py'))
spec=importlib.util.spec_from_file_location('retained_ordinary_suffix_sourcevalidation_only',runner['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_profile(x);m.verify(x['inputs']+[z['plan'] for z in x['leaves']])
proof=json.loads((D/'CORRECTION-AND-RETAINED-PREFIX.json').read_bytes())
for r in proof['retained_artifacts']:
 a=Path(r['reference']['path']).lstat();assert all(getattr(a,k)==v for k,v in r['identity'].items())
old=Path(proof['original_source']['path']).read_text();new=(D/'compare_existing_full_body.c').read_text();assert new==old.replace('memset(&obs,0,sizeof obs);memset(cpus,0,sizeof cpus);','__builtin_memset(&obs,0,sizeof obs);__builtin_memset(cpus,0,sizeof cpus);')
assert len(x['commands'])==2 and all('--redefine-sym' not in r['argv'] and '--emit=obj' not in ' '.join(r['argv']) for r in x['commands'])
assert not Path(x['capture_root']).exists() and not Path(x['leaves'][0]['output']).exists()
print(json.dumps(dict(decision='PASS_SUFFIX_SOURCE_INPUTS_AND_FOUR_RETAINED_ARTIFACT_IDENTITIES',commands=2,passed_prefix_replays=0,changed_reset_calls=2,compiler_calls=0,workloads=0,runtime_authority=None)))
