"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Minimal fresh-profile successor of retained HOST19 runner; never replays its batch.
Root alone supplies exact reviewed profile and fresh ordinary CPU6 grant.
"""
import argparse,hashlib,importlib.util,json,os,re,resource,signal,time
from decimal import Decimal
from pathlib import Path
HERE=Path(__file__).resolve().parent
THREAD='01a17e6f-112f-7660-8771-85d15e07a26c'
CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]
CAPTURE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
CAPTURE_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
ADMISSION_SHA='7df167b39842976391b6461f831c1a1349e1f3880892c37268579378e8f15a76'
SCOPE=__doc__.splitlines()[0]
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(path):
 p=Path(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def verify(rows):
 for row in rows:need(ref(row['path'])==row,'sealed input drift: '+row['path'])
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate_profile(p):
 need(p['task_id'].startswith('NEW12H-ORDINARY-HOST-') and p['goal']==THREAD and p['fixed_cutoffs']==CUTOFFS,'new actual profile only; HOST19 prohibited')
 need(p['fixed_deadline_UTC']=='2026-10-28T05:36:09Z','fixed actual deadline')
 need(p['resources']==dict(cpu=6,jobs=1,AS_bytes=2**31,CPU_seconds_each=60,FSIZE_bytes=64*2**20,CORE_bytes=0,wall_seconds_each=90,aggregate_jobs=7,aggregate_GiB='21.6619'),'unchanged ordinary limits and actual aggregate ceiling')
 need(0<len(p['commands'])<=32 and p['host_growth_reserve_bytes']>=len(p['commands'])*128*2**20,'bounded commands and full growth reserve')
 need(p['capture_root'].startswith('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/'),'private fresh capture root')
 covered=[]
 for leaf in p['leaves']:
  need(0<=leaf['first']<=leaf['last']<len(p['commands']),'exact leaf range')
  covered.extend(range(leaf['first'],leaf['last']+1))
 need(covered==list(range(len(p['commands']))),'one exact leaf for every command')
 for command in p['commands']:
  need(command['purpose'].startswith('Functional') and 'no security testing' in command['purpose'],'functional OS purpose')
  need(command['argv'] and Path(command['argv'][0]).is_absolute() and Path(command['cwd']).is_absolute(),'literal absolute command')
  need(command['argv_compact_json_LF_sha256']==hashlib.sha256((json.dumps(command['argv'],separators=(',',':'))+'\n').encode()).hexdigest(),'exact argv binding')
def validate_grant(grant,p,profile_sha,runner_sha,now):
 required=dict(task_id=p['task_id'],profile_sha256=profile_sha,runner_sha256=runner_sha,goal=THREAD,
  fixed_deadline_UTC=p['fixed_deadline_UTC'],fixed_cutoffs=CUTOFFS,resources=p['resources'],authorized=True,
  authorized_by='Root',cpu6_exclusive=True,other_cpu6_jobs=0)
 need(all(grant.get(k)==v for k,v in required.items()),'exact fresh Root ordinary grant')
 need(isinstance(grant.get('nonce'),str) and re.fullmatch('[0-9a-f]{32}',grant['nonce']) is not None,'fresh Root operation nonce')
 need(0<=now-grant['issued_wall']<180 and now<grant['expires_wall']<=CUTOFFS[0],'fresh grant lifetime')
 need(type(grant['reserved_jobs_other']) is int and 0<=grant['reserved_jobs_other']<=6,'aggregate7jobs')
 need(Decimal(0)<=Decimal(str(grant['reserved_GiB_other']))<=Decimal('19.6619'),'aggregate21.6619GiB including ordinary2GiB')
 need(type(grant['heavy_jobs_current']) is int and 0<=grant['heavy_jobs_current']<=1,'one heavy only')
 observation=grant['cpu6_exclusion_observation'];verify([observation])
 data=json.loads(Path(observation['path']).read_bytes())
 need(data['goal']==THREAD and data['cpu']==6 and data['ordinary_jobs_live']==0
      and data['authorized_by']=='Root' and 0<=now-data['observed_wall']<180,'fresh Root CPU6 exclusion observation')
def limits():
 os.sched_setaffinity(0,{6})
 for kind,value in [(resource.RLIMIT_AS,2**31),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64*2**20),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('profile','profile-sha256','grant','grant-sha256'):parser.add_argument('--'+name,required=True)
 args=parser.parse_args(argv)
 profile_path=Path(args.profile);grant_path=Path(args.grant)
 need(ref(profile_path)['sha256']==args.profile_sha256,'reviewed profile bytes')
 need(ref(grant_path)['sha256']==args.grant_sha256,'reviewed Root grant bytes')
 p=json.loads(profile_path.read_bytes());grant=json.loads(grant_path.read_bytes());validate_profile(p)
 need(ref(HERE/'admission_new12h.py')['sha256']==ADMISSION_SHA and ref(CAPTURE)['sha256']==CAPTURE_SHA,'retained admission/capture source')
 verify(p['inputs']+[x['plan'] for x in p['leaves']])
 validate_grant(grant,p,args.profile_sha256,ref(__file__)['sha256'],time.time())
 os.sched_setaffinity(0,{6});admit=load(HERE/'admission_new12h.py','new12h_admission').admission
 cap=load(CAPTURE,'retained_h990_capture')
 for sig in cap.STOP_SIGNALS:signal.signal(sig,cap.stop)
 for leaf in p['leaves']:need(not os.path.lexists(leaf['output']),'fresh output required; no replay')
 need(not os.path.lexists(p['capture_root']),'fresh whole capture required; no replay')
 def guard():
  verify(p['inputs']+[x['plan'] for x in p['leaves']])
  need(ref(profile_path)['sha256']==args.profile_sha256 and ref(grant_path)['sha256']==args.grant_sha256,'profile/grant unchanged')
  need(time.time()<grant['expires_wall'],'grant remains live')
  return admit(p)
 initial=guard();out=Path(p['capture_root']);out.mkdir(mode=0o700)
 cap.write(out/'CONSUMED-GRANT.json',dict(nonce=grant['nonce'],profile=ref(profile_path),grant=ref(grant_path),admission=initial,source=ref(__file__)))
 results=[];os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',LC_ALL='C',RUST_BACKTRACE='0',PYTHONDONTWRITEBYTECODE='1')
 try:
  for i,command in enumerate(p['commands']):
   admission=guard();leaf=next(x for x in p['leaves'] if x['first']<=i<=x['last'])
   if i==leaf['first']:Path(leaf['output']).mkdir(mode=0o700)
   capture=out/('step'+str(i));capture.mkdir(mode=0o700)
   cap.write(capture/'command.json',command);cap.write(capture/'admission.json',admission)
   os.chdir(command['cwd']);joined=cap.owned_capture(command,capture,90,limits)
   cap.write(capture/'whole-join.json',joined);results.append(dict(index=i,leaf=command['leaf'],join=joined))
   (out/'RESULTS.json').write_text(json.dumps(dict(status='RUNNING',results=results),indent=2)+'\n')
   need(joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error'],'first HOST failure; preserve prefix')
   if i==leaf['last']:need((capture/'stdout').read_text()==leaf['expected_stdout'],'unchanged oracle output')
  (out/'RESULTS.json').write_text(json.dumps(dict(status='PASS_HOST_ONLY_READY_FOR_REVIEW',results=results,production_acceptance=False),indent=2)+'\n')
  print('PASS '+str(len(results))+' sequential ordinary HOST commands; default/native acceptance separate')
 except BaseException as error:
  cap.write(out/'FIRST-FAILURE.json',dict(error=repr(error),scope=SCOPE));raise
if __name__=='__main__':main()
