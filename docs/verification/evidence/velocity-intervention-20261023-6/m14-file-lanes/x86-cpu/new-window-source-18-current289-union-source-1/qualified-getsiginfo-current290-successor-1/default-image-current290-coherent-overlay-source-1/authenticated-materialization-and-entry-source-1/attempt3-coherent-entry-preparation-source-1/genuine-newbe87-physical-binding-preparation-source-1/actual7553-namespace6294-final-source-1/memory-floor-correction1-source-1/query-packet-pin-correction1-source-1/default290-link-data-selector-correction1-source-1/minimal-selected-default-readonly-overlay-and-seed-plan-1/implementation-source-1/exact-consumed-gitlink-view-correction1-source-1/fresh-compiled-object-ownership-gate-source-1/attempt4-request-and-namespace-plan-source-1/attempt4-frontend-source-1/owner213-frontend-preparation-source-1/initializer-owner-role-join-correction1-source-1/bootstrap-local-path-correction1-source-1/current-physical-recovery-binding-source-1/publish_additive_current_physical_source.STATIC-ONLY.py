"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static additive publication and local-reference inventory, no imports of candidate modules/tests.
"""
import ast,hashlib,json,re,stat
from pathlib import Path
Z=Path(__file__).parent;Y=Z.parent;PUB=Z/'publication-preparation'
def ref(p):p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,o):p.write_text(json.dumps(o,sort_keys=True,indent=2)+'\n');return ref(p)
R=json.loads((Z/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json').read_bytes())
hashmap={ref(p)['sha256']:ref(Z/p.name)['sha256'] for p in Y.iterdir() if p.is_file() and (Z/p.name).is_file()}
paths={str(p):str(Z/p.name) for p in Y.iterdir() if p.is_file() and (Z/p.name).is_file()};paths[str(Y)]=str(Z)
combined=dict(paths);combined.update(hashmap);pattern=re.compile('|'.join(re.escape(k) for k in sorted(combined,key=len,reverse=True)))
def string(s):return pattern.sub(lambda m:combined[m.group()],s)
def update(o):
 if isinstance(o,list):return [update(v) for v in o]
 if isinstance(o,str):return string(o)
 if not isinstance(o,dict):return o
 if set(o)=={'path','sha256','bytes'}:
  if o['sha256']=='08860bb3032cbdf974c88d0fc417fc960aaa2c6f87783b9c4bb21835077c1f2c':return R['physical']
  if o['sha256']=='578a242c6af1ae01a4ae10d016cd2460a67b1ec8bb36998f00bfb939a67edf7c':return json.loads((Z/'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT4.READONLY-SEED.json').read_bytes())['postjoin']
  q=Path(string(o['path']))
  if q!=Path(o['path']) and q.is_file():return ref(q)
 return {k:update(v) for k,v in o.items()}
for n in ['ROOT-OWNER213-ROLEJOIN-PRECLOCK-CONTEXT.TEMPLATE.PENDING-ROOT.json','ROOT-OWNER213-ROLEJOIN-STATIC-PREPARATION-GRANT.TEMPLATE.PENDING-ROOT.json','EXACT-OWNER213-ROLEJOIN-CALLER-CENSUS-GRANT-CLEANUP-COMMANDS.NOT-GRANTED.json']:
 o=update(json.loads((Y/'publication-preparation'/n).read_bytes()))
 if 'PRECLOCK' in n:o['root_must_complete']='Exact468813/11b6 recovered boundary only. Record fresh current model/watch ancestry and service/credit/guardian facts, then current no-heavy continuity, held27:4, source publication/retirement/aggregate/clock facts; no grants supplied by this template.'
 put(PUB/n,o)
checks=[];errors=[];paths_observed=[]
def walk(o,label):
 if isinstance(o,dict):
  if set(o)=={'path','sha256','bytes'} and str(o['path']).startswith(str(Z)+'/'):
   p=Path(o['path']);ok=p.is_file() and ref(p)==o
   checks.append(dict(label=label,reference=o,exact=ok))
   if not ok:errors.append(label)
  for k,v in o.items():walk(v,label+'.'+k)
 elif isinstance(o,list):
  for i,v in enumerate(o):walk(v,label+'['+str(i)+']')
 elif isinstance(o,str) and o.startswith(str(Z)+'/'):paths_observed.append(dict(label=label,path=o,exists=Path(o).exists()))
for p in list(Z.glob('*.json'))+list(PUB.glob('*.json')):
 if 'STATIC-ONLY' not in p.name and 'MANIFEST' not in p.name:walk(json.loads(p.read_bytes()),p.name)
for p in Z.glob('*.py'):
 if p.name.startswith(('construct_','publish_')):continue
 tree=ast.parse(p.read_text())
 for n in ast.walk(tree):
  if isinstance(n,ast.Dict):
   try:o=ast.literal_eval(n)
   except (ValueError,TypeError,SyntaxError):continue
   if isinstance(o,dict) and set(o)=={'path','sha256','bytes'}:walk(o,p.name+':dict:'+str(n.lineno))
  elif isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith(str(Z)+'/'):paths_observed.append(dict(label=p.name+':str:'+str(n.lineno),path=n.value,exists=Path(n.value).exists()))
# Preserve the exact old 43-reference inventory as coverage lineage, remapped to each corresponding new source label.
old_audit=Y/'publication-preparation/EXACT-ALL-LOCAL-PATHS-AND-REFERENCE-PINS.STATIC-ONLY.json'
oldrows=json.loads(old_audit.read_bytes())['authenticated_local_reference_checks']
coverage=[]
for row in oldrows:
 label=row['label'];old=row['reference'];newpath=Path(string(old['path']))
 if label.startswith('EXACT-INITIALIZER15-RUNTIME213-THREE-PURE-CONTROLS.NOT-GRANTED.json.'):
  mapping={'fixture':Z/'EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json','role_join':Z/'EXACT-INITIALIZER15-TO-RUNTIME213-ACCEPTED-VALIDATOR-ROLE-JOIN.SOURCE-ONLY.json','source_ready':Z/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json','test':Z/'test_exact_recovered_physical_and_producer.PURE.NOT-RUN.py'};newpath=mapping[label.rsplit('.',1)[-1]]
 coverage.append(dict(predecessor_label=label,predecessor_reference=old,successor_reference=ref(newpath)))
duplicates=[]
for p in Z.glob('*.py'):
 if p.name.startswith(('construct_','publish_')):continue
 if '/current-physical-recovery-binding-source-1/current-physical-recovery-binding-source-1/' in p.read_text():duplicates.append(str(p))
audit=dict(scope=R['scope'],status='PASS_STATIC_LOCAL_REFERENCE_AND_PATH_COVERAGE' if not errors and not duplicates else 'FAIL_STATIC_LOCAL_REFERENCE_AND_PATH_COVERAGE',controls_executed=False,module_imports=0,queries=0,predecessor_audit=ref(old_audit),predecessor_reference_count=len(oldrows),predecessor_43_reference_successors=coverage,authenticated_local_reference_checks=checks,local_reference_count=len(checks),reference_failures=errors,duplicate_segment_occurrences=duplicates,observed_local_paths=paths_observed,all_actual_admission_grants_pending=True)
put(PUB/'EXACT-ALL-LOCAL-PATHS-AND-REFERENCE-PINS.STATIC-ONLY.json',audit)
files=[p for p in Z.rglob('*') if p.is_file() and p.name!='EXACT-RECOVERED-PHYSICAL-SOURCE-PUBLICATION-MANIFEST.PENDING-CONTROLS.json']
repo=Path('/home/holden/mckernel')
rows=[dict(source=str(p),repository=str(p.relative_to(repo)),sha256=ref(p)['sha256'],bytes=p.stat().st_size,mode=oct(stat.S_IMODE(p.stat().st_mode)),git_mode='100644',kind='functional-current-physical-source-not-granted') for p in sorted(files)]
put(PUB/'EXACT-RECOVERED-PHYSICAL-SOURCE-PUBLICATION-MANIFEST.PENDING-CONTROLS.json',dict(scope=R['scope'],status='SOURCE_READY_PENDING_ACTUAL_PURE_CONTROLS_AND_INDEPENDENT_REVIEW',source_READY=ref(Z/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),files=rows,stage_paths=[r['repository'] for r in rows],actual_control_result=None,independent_control_review=None,independent_source_review=None,future_root_grant=None,future_current_physical=None,all_actual_grants_census_and_live_clock_pending=True))
print(json.dumps(dict(scope=R['scope'],status=audit['status'],local_refs=len(checks),predecessor_refs=len(coverage),errors=errors,duplicates=duplicates,files=len(rows)),indent=2))
