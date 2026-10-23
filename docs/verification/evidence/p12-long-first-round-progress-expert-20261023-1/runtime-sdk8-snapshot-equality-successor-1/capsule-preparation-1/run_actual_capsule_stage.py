"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,shutil,signal,sys,time
D=Path(__file__).resolve().parent
E=D/'evidence-copy-1'
assert sys.version.startswith('3.9.12 ')
mem_available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem_available>=19<<30
usage=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert usage<100
helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw,str(helper));end=next(i for i,x in enumerate(tree.body) if isinstance(x,ast.FunctionDef) and x.name=='owned_capture');ns={'__file__':str(helper)};exec(compile(ast.Module(body=tree.body[:end+1],type_ignores=[]),str(helper),'exec'),ns)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
assert hashlib.sha256((D/'stage_long_session.py').read_bytes()).hexdigest()=='b37c545987bc7643db063575b6de5b4dbb1e83e176b178762b05a57044b0eb0f'
profile=json.loads((D/'ROOT-ORDINARY-STAGE-GRANT.json').read_text());binding=json.loads((D/'CAPSULE-BINDING.READY.json').read_text());assert profile['status']=='ROOT_ORDINARY_GRANTED' and binding['status']=='READY_FOR_REVIEWED_HOST_STAGE'
for label in ('producer_review','application_review','reviewed_stage_profile','diagnostic_source','baseline_manifest','baseline_overlay_manifest'):
 row=binding[label];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
# Reuse the selected positive budget arithmetic conservatively, including the
# entire backing length as a bound on sparse growth (never a smaller estimate).
budgetpath=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/final-budget-and-smoke-preparation-1/EXACT-POSITIVE-BUDGET.PROPOSED.json')
budget=json.loads(budgetpath.read_text());host=shutil.disk_usage(D);scratch=shutil.disk_usage('/home/holden/mckernel-work/scratch');backing=Path('/home/holden/mckernel-work/scratch.ext4');st=backing.stat();selected=budget['capacity_admission_proposal']
assert st.st_size==118111600640 and st.st_size==selected['remaining_backing_growth_bytes']
gap=max(0,st.st_size-st.st_blocks*512)
host_required=selected['host_floor_bytes']+st.st_size+budget['HOST_capture_reservation_bytes']+selected['emergency_bytes']+selected['campaign_bytes']
scratch_required=selected['scratch_floor_bytes']+selected['scratch_input_growth_bytes']+selected['emergency_bytes']+selected['campaign_bytes']
capacity={'scope':__doc__,'measured_unix_ns':time.time_ns(),'HOST_free_bytes':host.free,'scratch_free_bytes':scratch.free,'backing_path':str(backing),'backing_size':st.st_size,'backing_allocated':st.st_blocks*512,'actual_sparse_gap':gap,'conservative_growth_allowance':st.st_size,'HOST_required_bytes':host_required,'scratch_required_bytes':scratch_required,'emergency_bytes':selected['emergency_bytes'],'campaign_bytes':selected['campaign_bytes'],'HOST_capture_reservation':budget['HOST_capture_reservation_bytes'],'stage_output_in_campaign_cap':128<<20,'budget_source_sha256':hashlib.sha256(budgetpath.read_bytes()).hexdigest(),'PASS':host.free>=host_required and scratch.free>=scratch_required,'runtime_admission':False,'fresh_UUID_or_loop_identity_claimed':False}
ns['write'](D/'ACTUAL-CAPACITY-BEFORE-STAGE.json',capacity)
result={'scope':__doc__,'status':'REFUSED_CAPACITY_BEFORE_CHILD','capacity':capacity,'whole_join':None,'actual_stage':None,'error':None,'CPU6_released':True,'runtime_acceptance':False}
if capacity['PASS']:
 cap=D/'actual-capsule-stage-1';cap.mkdir();command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'stage_long_session.py'),'--binding',str(D/'CAPSULE-BINDING.READY.json')],'cwd':str(D),'purpose':__doc__,'shell':False,'source_sha256':'b37c545987bc7643db063575b6de5b4dbb1e83e176b178762b05a57044b0eb0f'}
 ns['write'](cap/'command.json',command);joined=ns['owned_capture'](command,cap,90,lambda:None);ns['write'](cap/'whole-join.json',joined);result['whole_join']=joined
 ok=joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and not joined['error'] and not joined['retirement_error']
 result['status']='PASS_ACTUAL_CAPSULE_STAGE_AND_STRICT_LOADER' if ok else 'FAIL_FIRST_STAGE_CAPTURE_RETAINED';result['CPU6_released']=joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams']
 if ok:
  out=D/'actual-stage-1';stage=json.loads((out/'stage-result.json').read_text());old=json.loads(Path(binding['baseline_overlay_manifest']['path']).read_text())['final_map'];new=json.loads((out/'overlay-manifest.json').read_text())['final_map'];delta=[name for name in old if old[name]!=new[name]]
  assert set(new)==set(old) and len(old)==62 and delta==['init'],'exact1init/61unchanged'
  result['actual_stage']=stage;result['actual_changed_members']=delta;result['actual_unchanged_members']=61;result['strict_loader']='Original unchanged builder load_manifest returned successfully'
ns['write'](D/'ACTUAL-CAPSULE-STAGE-WHOLE-JOIN.json',result)
files=[D/'ACTUAL-CAPACITY-BEFORE-STAGE.json',D/'ACTUAL-CAPSULE-STAGE-WHOLE-JOIN.json']
if (D/'actual-capsule-stage-1').exists():files+=list((D/'actual-capsule-stage-1').iterdir())
if (D/'actual-stage-1').exists():files += [p for p in (D/'actual-stage-1').iterdir() if p.name in ('manifest.json','overlay-manifest.json','stage-result.json')]
for p in files:
 target=E/p.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(p.read_bytes())
print(json.dumps({'status':result['status'],'capacity':capacity,'join':result['whole_join'],'actual_stage':result['actual_stage'],'CPU6_released':result['CPU6_released']}))
