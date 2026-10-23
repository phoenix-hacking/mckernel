"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing C41 freeze/attach/capture recipe, SDK8 literal successor only. Never execute embedded commands or mint a clock/review/release.
"""
from pathlib import Path
import ast,json,hashlib,difflib
D=Path(__file__).resolve().parent;B=D.parent/'runtime-settlement-successor-1';P=D/'finalization-preparation-1';R=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-successor-1');P.mkdir(mode=0o700);(R/P.name).mkdir(mode=0o700)
def ref(p):p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(name,raw):
 for root in [D,R]:
  with (root/'finalization-preparation-1'/name).open('xb') as f:f.write(raw)
def emit(name,x):write(name,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
n=json.loads((D/'ROOT-SUCCESSOR-NAMESPACE.json').read_bytes());cohort=json.loads((D/'COHORT-BINDINGS.json').read_bytes());selected={name:cohort[name] for name in json.loads((B/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes())['source_sha256']}
replacements={str(B):str(D),'221b6d10cca3426096dce479aba205b0':n['nonce'],'/home/holden/mckernel-work/native-runs/l12e1/p':n['host_parent'],'/home/holden/mckernel-work/scratch/p12s6l2/m.json':n['manifest_path'],'/home/holden/mckernel-work/scratch/p12s6l2/r.json':n['release_path'],'33eb6e9a08be55651d60e4fb786ac2ccd5dfc476ef611b7fe0be804477403390':n['actual_manifest']['sha256'],'ROOT-CANONICAL-SETTLEMENT-LONG-PAYLOAD':'ROOT-CANONICAL-SDK8-LONG-PAYLOAD'}
for name in ['capture_root_LONG.NOT-RELEASED.py','controller_pre_effect_consumer.py','source/long_transport.py','source/native_diagnostic_container_owner.py']:replacements[ref(B/name)['sha256']]=ref(D/name)['sha256']
def text(s):
 for old,new in replacements.items():s=s.replace(old,new)
 return s
def data(x):
 if isinstance(x,str):return text(x)
 if isinstance(x,list):return [data(v) for v in x]
 if isinstance(x,dict):return {k:data(v) for k,v in x.items()}
 return x
for name in ['FREEZE-ROOT-CANONICAL-PAYLOAD.COMMAND.NOT-EXECUTED.json','FINAL-ATTACH-APPROVED-REVIEW.COMMAND.NOT-EXECUTED.json','ROOT-ARGV.PROTOTYPE.NOT-EXECUTABLE.json','TERMINAL-THREE-CATS.NOT-RELEASED.json']:
 original=json.loads((B/'finalization-preparation-1'/name).read_bytes());v=data(original)
 if isinstance(v,dict):
  if 'source9' in v:v['source9']=selected
  for key,file in [('source_guard_transport','source/long_transport.py'),('selected_TRANSPORT','source/long_transport.py'),('controller','capture_root_LONG.NOT-RELEASED.py'),('owner','source/native_diagnostic_container_owner.py'),('mandatory_final_published_request_consumer','controller_pre_effect_consumer.py')]:
   if key in v:v[key]=ref(D/file)
  if 'argv' in v and v['argv'][3]=='-c':
   code=v['argv'][4];ast.parse(code);assert all(n.value==b'\n' for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Constant) and isinstance(n.value,bytes));assert code==text(original['argv'][4])
 emit(name,v)
for name in ['run_outer_once.py','read_started_once.py']:
 old=(B/'finalization-preparation-1'/name).read_text();new=text(old);ast.parse(new);write(name,new.encode());write(name+'.data-only.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='acceptedsettlement/'+name,tofile='SDK8/'+name)).encode())
v=data(json.loads((B/'finalization-preparation-1/OUTER-AND-STARTED-COMMANDS.NOT-RELEASED.json').read_bytes()));v['helpers']={name:ref(P/name) for name in ['run_outer_once.py','read_started_once.py']};emit('OUTER-AND-STARTED-COMMANDS.NOT-RELEASED.json',v)
files={p.name:ref(p) for p in P.iterdir() if p.is_file()};emit('SDK8-FINALIZATION-PREPARATION-RECEIPT.json',dict(scope=__doc__,status='FROZEN_DATA_ONLY_TEMPLATE_FRESH_QUERY_PAYLOAD_REVIEW_CLOCK_ROOT_RELEASE_NULL',files=files,selectedsource9=selected,actual_cohort_fixture=ref(D/'ACTUAL-SDK8-COHORT-FIXTURE-RECEIPT.json'),actualpublishedrequestconsumer=ref(D/'controller_pre_effect_consumer.py'),late_sequence=['Static publication and source/profile review','Genuine fresh authenticated LONG admission PASS and continuity','Root freeze selected g.canonical LF payload excludingreview, now+590','Genuine exact4keyreview','Attach5args O_EXCL release/full unmodified realclock g.validate_release','O_EXCL final CAPTURE-REQUEST bytes/hash then actual selected callable main','OnlybothconsumerPASS produce ROOTargv then independentlyreleasedrootinvokeonce'],future_actual_admission=None,future_payload=None,future_payload_sha256=None,future_review=None,future_expiry=None,root_execution_release=None,native_acceptance=False))
print(json.dumps(ref(P/'SDK8-FINALIZATION-PREPARATION-RECEIPT.json'),sort_keys=True))
