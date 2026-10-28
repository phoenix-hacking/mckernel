"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-retained-key/response provenance audit; never runs a full observer.
"""
from pathlib import Path
import ast,datetime,hashlib,importlib.util,json,resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
HERE=Path(__file__).resolve().parent
PACKET=HERE.parent.parent/'m14-next118-recursive-fixture-expert-20261028-1'
def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path):return json.loads(Path(path).read_bytes())
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
packet=read(PACKET/'CLASSIFIER-REVIEW-PACKET.json')
for value in packet.values():
 if isinstance(value,dict) and set(value)=={'path','bytes','sha256'}:assert ref(value['path'])==value
assert packet['source']['sha256']=='9e6ef78fb3b2e56429194c76bf16f92f5871be254573c09fdc539facd50eead8'
source=Path(packet['source']['path']).read_text();tree=ast.parse(source)
assert not any(isinstance(node,(ast.Import,ast.ImportFrom)) and any(alias.name in ['subprocess','os'] for alias in node.names) for node in ast.walk(tree))
# The proposed change is classifier-only; all other AST function bodies are exact.
prior=ast.parse((PACKET/'EXPERT-FIRST-retained_effect_oracle.py').read_text())
def bodies(t):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a,b=bodies(prior),bodies(tree);assert set(a)==set(b) and [name for name in a if a[name]!=b[name]]==['query']
physical=load(HERE.parent.parent/'new-window-physical-history-successor-source-20261028-1/physical_history_successor.py','pure_classifier_physical_source_chain')
oracle_module=load(packet['source']['path'],'pure_classifier_retained_oracle')
oracle=oracle_module.RetainedEffectOracle(physical.source_chain())
actual=oracle.manifest();expected=read(packet['retained_query_manifest']['path']);assert actual==expected
assert len(actual['inputs'])==54 and len(actual['rows'])==94
inputs={r['path']:r for r in actual['inputs']};documents={}
for row in actual['inputs']:
 assert ref(row['path'])==row
 documents[row['path']]=read(row['path'])
prefix_counts={};derived=0;raw=0;alias=0
for row in actual['rows']:
 key=row['argv'];response=row['response'];provenance=row['provenance'];origin=provenance['input']
 assert origin==inputs[origin['path']]
 assert oracle.get(key)==response
 assert oracle_module.query(key)
 prefix=' '.join(key[:4]);prefix_counts[prefix]=prefix_counts.get(prefix,0)+1
 value=documents[origin['path']]
 if provenance['derived']:
  derived+=1;assert provenance['pointer']=='/container+state'
  assert value['container']==key[-1] and key[4]=='inspect' and value['state']['Running'] is False and value['state']['Pid']==0
  assert response==dict(returncode=0,stdout=json.dumps([dict(Id=value['container'],State=value['state'])]),stderr='')
 else:
  raw+=1
  for component in provenance['pointer'].split('/')[1:]:value=value[int(component)] if isinstance(value,list) else value[component]
  assert response=={k:value[k] for k in ['returncode','stdout','stderr']}
  if provenance['sudo_spelling_alias']:
   alias+=1;alternate=list(value['argv']);alternate[0]='/usr/bin/sudo' if alternate[0]=='sudo' else 'sudo';assert key==alternate
  else:assert key==value['argv']
  assert key[2:]==value['argv'][2:], 'Docker/options/socket spelling must remain recorded'
assert len(prefix_counts)==4 and sorted(prefix_counts.values())==[9,9,38,38]
# All source-accepted qualifier shapes still need exact retained tuple membership.
# These are classifier checks only; no executable argv is ever dispatched.
misses=[]
for sudo in ['sudo','/usr/bin/sudo']:
 for docker in ['docker','/usr/bin/docker']:
  pre=[sudo,'-A',docker,'--host=unix:///var/run/docker.sock']
  misses.extend([pre+['ps','--UNRECORDED_CLASSIFIER_ONLY'],pre+['inspect','f'*64],pre+['rm','classifier-only']])
misses.extend([['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///wrong.sock','ps','-q'],['sudo','-n','docker','--host=unix:///var/run/docker.sock','ps','-q']])
for key in misses:
 assert tuple(key) not in oracle.rows
 try:oracle.get(key)
 except AssertionError as error:assert str(error).startswith('UNSUPPORTED_RETAINED_EFFECT_ARGV ')
 else:raise AssertionError('unrecorded key admitted')
report=dict(scope=__doc__.splitlines()[0],at=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision='PASS_CLASSIFIER_ONLY_COMPLETE_EXACT_RETAINED_KEYS_AND_RECEIPT_BOUND_RESPONSES',packet=ref(PACKET/'CLASSIFIER-REVIEW-PACKET.json'),oracle_source=packet['source'],query_manifest=packet['retained_query_manifest'],authenticated_inputs=54,exact_keys=94,exact_prefix_counts=prefix_counts,raw_response_keys=raw,terminal_receipt_projection_keys=derived,sudo_spelling_alias_keys=alias,Docker_spelling_aliases_generated=0,unsupported_exact_keys_rejected=len(misses),conflicting_historical_reply_records_retained=len(actual['conflicts']),only_changed_AST_function='query',actual_subprocess_commands=0,actual_guard_account_observation_calls=0,full_recursive_fixture_runs=0,CPU=0,jobs=1,AS_bytes=2*1024**3,runtime_authority=None)
(HERE/'CLASSIFIER-CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
