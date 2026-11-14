"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Controlled derivative of real bridge output; no additional actual/runtime launches.
"""
from pathlib import Path
import copy,importlib.util,json,os,re,sys
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/source')
def load(name):
 s=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
native=load('native_diagnostic');checker=load('p12_long_session')
seed=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/stage-launches-1/manifest.json')
manifest=json.loads(seed.read_text());manifest['pair_long_session']=checker.PROFILE
# Exact accepted current BEGIN descriptor, never synthetic lifecycle rows.
m05=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/sdk5-successor-1/actual-stage-1/manifest.json')
manifest['cleanup_profile']=json.loads(m05.read_text())['cleanup_profile']
work=D/os.environ.get('REAL_ATTEMPT','attempt-1')/'bridge-0-work'
report=json.loads((work/'full-report').read_text()[len('ND_PAIR '):]);trace=(work/'full-trace').read_text()
assert native._pair_body(manifest,{'serial':(work/'full-report').read_text()+trace})['status']=='PROTOCOL_PASS'
if sys.argv[1]=='prepare':
 out=D/os.environ.get('REAL_ATTEMPT','attempt-1')/'controlled-full-frames';out.mkdir()
 for round_id in range(360):
  r=copy.deepcopy(report);t=trace
  pid_map={a['pid']:round_id*2+i+1 for i,a in enumerate(r['apps'])}
  t=re.sub(r'(?<=[pt]id=)\d+\b',lambda m:str(pid_map.get(int(m.group()),int(m.group()))),t)
  for i,a in enumerate(r['apps']):
   newpid=round_id*2+i+1
   a['pid']=newpid;a['started_ns']=1_000_000+round_id*10_000_000_000+i
   a['reaped_ns']=1_000_000+(round_id+1)*10_000_000_000-1+i
   a['finished_ns']=1_000_000+(round_id+1)*10_000_000_000
   for stream in a['streams'].values():stream['eof_ns']=a['finished_ns']
  # Every controlled derivative retirement/ACK token is identity-distinct.
  t=re.sub(r'token=(\d+)',lambda m:'token='+str(int(m.group(1))+round_id*10000),t)
  if round_id:t=''.join(line for line in t.splitlines(keepends=True) if not line.startswith(('NATIVE_PAIR_CPU ','control accepted ')))
  (out/(str(round_id)+'.report')).write_text('ND_PAIR '+json.dumps(r,separators=(',',':'))+'\n')
  (out/(str(round_id)+'.trace')).write_text(t)
 print(json.dumps({'status':'PASS_ACTUAL_BRIDGE_FULL_PAIR_CONSUMER_AND_PREPARED_CONTROLLED_DERIVATIVES','actual_linux_launches':2,'controlled_derivative_rounds':360}))
else:
 results=[]
 for mode in [0,1,2,3,4,5,6,7,9,10]:
  serial=(D/os.environ.get('REAL_ATTEMPT','attempt-1')/('wire-final-'+str(mode))).read_text()
  if mode==0:
   metrics=checker.check_long_session(manifest,{'serial':serial},pair_check=native._pair_body)
   assert metrics['successful_launches']==720
   results.append({'mode':mode,'unchanged_full_LONG':'PASS','successful_launches':720,'native_acceptance':False})
  else:
   assert 'ND_PAIR_LONG_COMPLETE ' not in serial
   try:checker.check_long_session(manifest,{'serial':serial},pair_check=native._pair_body)
   except (ValueError,RuntimeError) as error:results.append({'mode':mode,'unchanged_full_LONG':'REJECTED','error':str(error),'complete_present':False})
   else:raise AssertionError('accepted failed actual final gate/workspace '+str(mode))
 print(json.dumps({'status':'PASS_ACTUAL_FINAL_GATE_AND_DEFAULT_WORKSPACE_FULL_LONG_CONSUMER','results':results,'controlled_derivatives_only':True,'native_acceptance':False}))
