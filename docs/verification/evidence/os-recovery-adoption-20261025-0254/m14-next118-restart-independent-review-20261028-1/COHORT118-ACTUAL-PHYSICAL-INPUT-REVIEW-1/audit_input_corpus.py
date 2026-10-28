"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent input/corpus/dispatch checks only; no observer or actual command calls.
"""
from pathlib import Path
import ast,copy,datetime,hashlib,importlib.util,json,resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
HERE=Path(__file__).resolve().parent
PACKET=HERE.parent.parent/'m14-next118-recursive-fixture-expert-20261028-1/actual-bfd-physical-input-supplement-1'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
checked={}
def authrow(row):
 assert ref(row['path'])==row,row['path'];checked[row['path']]=row
 raw=Path(row['path']).read_bytes();return json.loads(raw) if str(row['path']).endswith('.json') else raw
packet=read(PACKET/'SOURCE-INPUT-REVIEW-PACKET.json')
for value in packet.values():
 if isinstance(value,dict) and set(value)=={'path','bytes','sha256'}:authrow(value)
assert packet['source']['sha256']=='3ff77a9c681a6a733ed9a86a5d669302d954b6002522b5cde0ff5d6fe36f29b4'
s=load(PACKET/'retained_effect_oracle.py','independent_actual_physical_supplement')
assert s.query is s._base.query and s.RetainedEffectOracle.get is s._base.RetainedEffectOracle.get
capture,used=s.authenticate_actual_proof()
for row in used.values():authrow(row)
for name in ['root61_ledger','root61_latest_free']:authrow(s.BINDINGS[name])
# Independently reconstruct both exact five-row receipt paths and raw responses.
independent={};pointers={}
for path in s.PATHS:
 rows=capture
 for part in path:rows=rows[part]
 assert len(rows)==5
 for index,row in enumerate(rows):
  assert row['positive_wait'] is True and row['streams_closed'] is True
  key=tuple(row['argv']);reply={k:row[k] for k in ['returncode','stdout','stderr']}
  if key in independent:assert independent[key]==reply
  independent[key]=reply;pointers.setdefault(key,[]).append('/'+'/'.join(path)+'/'+str(index))
assert len(independent)==5 and all(len(v)==2 for v in pointers.values())
physical=load(HERE.parent.parent/'new-window-physical-history-successor-source-20261028-1/physical_history_successor.py','independent_input_only_source_chain')
oracle=s.RetainedEffectOracle(physical.source_chain());base=s._base.RetainedEffectOracle(physical.source_chain())
new=set(oracle.rows)-set(base.rows)
assert len(base.rows)==94 and len(oracle.rows)==97 and len(new)==3
assert new==set(independent)-set(base.rows)
assert all(oracle.rows[k]==v for k,v in base.rows.items())
assert all(oracle.get(list(k))==v for k,v in independent.items())
assert oracle.manifest()==read(PACKET/'SUPPLEMENT-CORPUS-MANIFEST.json')
for key in new:
 assert key[:7]==('/usr/bin/sudo','-A','/usr/bin/docker','ps','-aq','--no-trunc','--filter')
 assert not s.query(list(key)), 'the original classifier remains unchanged'
 prov=oracle.provenance[key]
 assert prov['input']==s.BINDINGS['inputs']['capture'] and prov['all_duplicate_pointers']==pointers[key]
 assert prov['derived'] is False and prov['sudo_spelling_alias'] is False
 assert oracle.get(list(key))==dict(returncode=0,stdout='',stderr='') # Exact actual bytes above, never guessed.
# Pure negative malformed/colliding DATA fixtures only; no filesystem mutation.
bad=copy.deepcopy(capture);rows=bad
for key in s.PATHS[1]:rows=rows[key]
rows[0]['stdout']='NEGATIVE_DUPLICATE_ONLY'
try:s.exact_corpus(bad)
except ValueError as error:assert str(error).startswith('CONFLICTING_AUTHENTICATED_SUPPLEMENT_DUPLICATE ')
else:raise AssertionError('conflicting duplicate accepted')
original_corpus=s.exact_corpus
try:
 def conflicting_base(c):
  corpus,where=original_corpus(c);corpus=copy.deepcopy(corpus)
  k=next(k for k in corpus if k in base.rows);corpus[k]['stderr']='NEGATIVE_BASE_CONFLICT_ONLY';return corpus,where
 s.exact_corpus=conflicting_base
 try:s.RetainedEffectOracle(physical.source_chain())
 except ValueError as error:assert str(error).startswith('CONFLICTING_BASE_SUPPLEMENT_REPLY ')
 else:raise AssertionError('conflicting base reply accepted')
finally:s.exact_corpus=original_corpus
unsupported=[]
for key in sorted(new):
 for at,value in [(0,'sudo'),(2,'docker')]:
  alias=list(key);alias[at]=value;unsupported.append(alias)
unsupported.append(['/usr/bin/sudo','-A','/usr/bin/docker','ps','-aq','--no-trunc','--filter','id='+'f'*64])
for key in unsupported:
 try:oracle.get(key)
 except AssertionError as error:assert str(error).startswith('UNSUPPORTED_RETAINED_EFFECT_ARGV ')
 else:raise AssertionError('unrecorded key/alias accepted')
report=dict(scope=__doc__.splitlines()[0],at=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision='PASS_EXACT_AUTHENTICATED_ACTUAL_BFD_PHYSICAL_INPUT_CORRECTION_ONLY',packet=ref(PACKET/'SOURCE-INPUT-REVIEW-PACKET.json'),source=ref(PACKET/'retained_effect_oracle.py'),inputs=ref(PACKET/'INPUT-BINDINGS.json'),manifest=ref(PACKET/'SUPPLEMENT-CORPUS-MANIFEST.json'),lineage_refs=list(checked.values()),base_keys=94,total_keys=97,new_exact_keys=[list(k) for k in sorted(new)],unchanged_base_responses=94,raw_receipt_rows=10,unique_receipt_queries=5,identical_existing_queries=2,duplicate_conflict_refuses=True,base_conflict_refuses=True,unsupported_and_alias_refusals=len(unsupported),unchanged_classifier_and_exact_get=True,new_aliases=0,observer_function_calls=0,full_recursive_fixture_runs=0,actual_commands_guard_account_native=0,CPU=0,jobs=1,AS_bytes=2*1024**3,runtime_authority=None)
(HERE/'INPUT-CORPUS-CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='lineage_refs'},indent=2))
