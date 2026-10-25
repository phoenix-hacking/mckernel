"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Parent metadata only. No launch/RPC/signal/queue/ledger write. New user window overrides old cutoff.
"""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import argparse,hashlib,importlib.util,json,math,time
D=Path(__file__).resolve().parent;C=D/'controller';M=D/'twenty-minute-steering'
THREAD='01a170fb-57c3-7ab3-862d-8005bef92a63'
BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/run-until-controller-2/finalize.py')
BASE_SHA='5805676857263bb2aa8aaea6521058251ffcb377dbbaa6792d8534c04de40852'
def need(ok,message):
 if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,j):
 with Path(p).open('x') as f:f.write(json.dumps(j,indent=2)+'\n')
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def utc(epoch):return datetime.fromtimestamp(epoch,timezone.utc).isoformat().replace('+00:00','Z')
def validate_window(w):
 need(isinstance(w.get('window_id'),str) and bool(w['window_id']),'actual fixed window identity')
 for start,end in [('start_epoch','deadline_epoch'),('start_boot','boot_deadline'),('start_monotonic','monotonic_deadline')]:
  need(type(w.get(start)) in (float,int) and type(w.get(end)) in (float,int) and math.isfinite(w[start]) and math.isfinite(w[end]) and w[start]>0 and w[end]==w[start]+64800,'fixed18h clock pair: '+start)
 need(datetime.fromisoformat(w['deadline_utc'].replace('Z','+00:00')).timestamp()==w['deadline_epoch'],'UTC epoch coherence')
 need(type(w['max_agents']) is int and 1<=w['max_agents']<=11 and w['build_jobs']==7,'actual admitted parallelism')
 return w

def manual_stop_eligible(state):
 return (state.get('phase')=='stopped' and (state.get('goal') or {}).get('status')=='paused'
         and not state.get('active_turns') and state.get('stop_reason') in ('signal_2','work_window')
         and (state.get('resume_instruction') or {}).get('status') in (None,'accepted_by_server'))

def remaining(w,wall,boot,mono):return min(w['deadline_epoch']-wall,w['boot_deadline']-boot,w['monotonic_deadline']-mono)
def render(s,w):
 return s.replace('__WINDOW_DEADLINE_EPOCH__',repr(w['deadline_epoch'])).replace('__WINDOW_DEADLINE_UTC__',w['deadline_utc']).replace('__WINDOW_START_UTC__',utc(w['start_epoch'])).replace('__WINDOW_ID__',w['window_id'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','bind'])
 for name in ['window','window-sha256','authority','authority-sha256','billing','billing-sha256','approved-source-pins','approved-source-pins-sha256','expected-thread']:p.add_argument('--'+name,required=True)
 x=p.parse_args();need(x.expected_thread==THREAD and sha(BASE)==BASE_SHA,'same thread and reviewed metadata API')
 for path,expected in [(x.window,x.window_sha256),(x.authority,x.authority_sha256),(x.billing,x.billing_sha256),(x.approved_source_pins,x.approved_source_pins_sha256)]:need(sha(path)==expected,'exact parent metadata SHA')
 w=validate_window(read(x.window));a=read(x.authority);billing=read(x.billing);pins=read(x.approved_source_pins)
 need(all(a.get(k) is True for k in ['explicit_new18h_override','explicit_same_thread_resume','old_triplet_and_controllers_retired','original_leases_free','fresh_account_valid','no_service_auth_billing_user_hold','reviewed_sources_applied']),'actual manual transition authority')
 need(a['boot_id']==w['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'same actual boot')
 b=load(BASE,'reviewed_controller2_metadata');b.DEADLINE=w['deadline_epoch'];b.D=C/'rendered-source'
 need(set(pins['canonical'])=={'run_os_goal.py','watch_os_goal.py','os_goal_credits.py'},'exact source set')
 for n,h in pins['canonical'].items():need(sha(b.SCRIPTS/n)==h,'reviewed canonical drift')
 for n,h in pins['private'].items():need(sha(D/n)==h,'reviewed private drift')
 need(0<=time.time()-billing['observed_at_epoch']<120,'fresh account snapshot')
 state=read(b.CAMPAIGN/'state.json');need(state['thread_id']==THREAD,'same goal UUID')
 need(not any(state.get(k) for k in ['service_hold','policy_hold','auth_hold','billing_hold']),'real hold veto')
 need((b.CAMPAIGN/'credit-runs'/(b.RUN+'.json')).is_file(),'existing credit ledger required')
 budget,ledger=b.credit_budget(billing['limits']);need(Decimal(budget)==b.AUTHORIZED,'same original budget, never reset spend')
 need(remaining(w,time.time(),time.clock_gettime(time.CLOCK_BOOTTIME),time.monotonic())>0,'new fixed window expired')
 if x.mode=='prepare':
  for start,now in [('start_epoch',time.time()),('start_boot',time.clock_gettime(time.CLOCK_BOOTTIME)),('start_monotonic',time.monotonic())]:need(0<=now-w[start]<=60,'actual launch boundary must be fresh')
  need(manual_stop_eligible(state),'manual checkpoint terminal and certain historicalresume required')
  need(not any((b.CAMPAIGN/'instructions'/'pending').glob('*.json')) and not any((b.CAMPAIGN/'instructions'/'sending').glob('*.json')),'exact old inbox reconciliation required; no replay')
  need(isinstance(a.get('old_processes'),list) and len(a['old_processes'])>=5,'actual old controller/triplet birth receipt required')
  for row in a['old_processes']:need(type(row['pid']) is int and bool(row['start']) and not Path('/proc/'+str(row['pid'])).exists(),'old recorded PID still present')
  b.D.mkdir(exist_ok=False)
  (b.D/'bridge.TEMPLATE.py').write_text(render((C/'bridge.TEMPLATE.py').read_text(),w))
  (b.D/'finite_launcher.py').write_bytes((C/'finite_launcher.py').read_bytes())
  (b.D/'test_bridge.py').write_text((C/'test_bridge.py').read_text().replace('2026-10-26T06:00:00Z',w['deadline_utc']))
  (b.D/'CURRENT-INVOCATION.txt').write_text(render((C/'CURRENT-INVOCATION.TEMPLATE.txt').read_text(),w))
  config=read(C/'CONFIG.TEMPLATE.json');config.update(deadline_utc=w['deadline_utc'],local_deadline=None,window=w,window_sha256=x.window_sha256,max_agents=w['max_agents'],build_jobs=w['build_jobs'],expected_thread='__PENDING_NEW_THREAD_DO_NOT_ARM__',previous_thread_id=THREAD,status='NEW18H_SAME_THREAD_BOOTSTRAP_NOT_ARMED',initial_credit_budget=budget,initial_boot_id=w['boot_id'],initial_boot_deadline=w['boot_deadline'])
  target=C/'bootstrap';packet=b.capsule(target,config['expected_thread'],budget,config,pins)
  argv=['/usr/bin/taskset','-c','0,2-7','/home/holden/anaconda3/bin/python3','-B',str(target/'finite_launcher.py'),'--deadline-utc',w['deadline_utc'],'--boot-deadline',str(w['boot_deadline']),'--monotonic-deadline',str(w['monotonic_deadline']),'--packet-sha256',packet,'--publish-initial-clock','--','--model','gpt-6.1-sol','--effort','medium','--profile','aggressive','--max-agents',str(w['max_agents']),'--build-jobs','7','--agent-windows','off','--stall-seconds','1800','--watchdog-seconds','180','--quiet','--grace-seconds','30','--credit-budget',budget,'--credit-run-id',b.RUN,'--startup-instruction-file',str(target/'CURRENT-INVOCATION.txt'),'--startup-instruction-sha256',sha(target/'CURRENT-INVOCATION.txt')]
  write(target/'INITIAL-LAUNCH.NOT-EXECUTED.json',dict(status='METADATA_ONLY_NOT_LAUNCHED',argv=argv,window=w,window_sha256=x.window_sha256,packet_sha256=packet,budget=budget,credit_run_id=b.RUN,retained_credit_ledger=ledger))
  (M/'steer_every_twenty_minutes.py').write_text(render((M/'steer_every_twenty_minutes.TEMPLATE.py').read_text(),w));print(json.dumps(dict(status='PREPARED_NO_LAUNCH',command_file=str(target/'INITIAL-LAUNCH.NOT-EXECUTED.json'))));return
 initial=read(C/'bootstrap/INITIAL-LAUNCH.NOT-EXECUTED.json');need(initial['window_sha256']==x.window_sha256 and initial['window']==w,'fixed consumed window cannot roll or change')
 bridge=load(C/'bootstrap/bridge.py','fixed_window_bridge');bridge.verify_packet(initial['packet_sha256'])
 need(state['phase']=='running' and state['goal']['status']=='active' and not state.get('stop_reason') and 0<=time.time()-datetime.fromisoformat(state['heartbeat_at'].replace('Z','+00:00')).timestamp()<120,'healthy same-thread arm only')
 chain=bridge.bind(state,read(b.CAMPAIGN/'watcher.json'));clock=read(C/'bootstrap/initial-watch-clock.json')
 need(clock['deadline']==w['deadline_epoch'] and clock['boot_deadline']==w['boot_deadline'] and clock['boot_id']==w['boot_id'] and clock['bootstrap_packet_sha256']==initial['packet_sha256'] and clock['watcher_pid']==chain['watcher']['pid'] and clock['watcher_start']==chain['watcher']['start'] and 0<=clock['watcher_cutoff_upper']-clock['watcher_cutoff_lower']<=1 and clock['watcher_cutoff_lower']<=w['monotonic_deadline'],'actual fixed finite clock/lineage')
 credit=state.get('credit_budget') or {};need(credit.get('id')==b.RUN and Decimal(str(credit.get('budget')))==Decimal(initial['budget']),'same actual debit guard')
 config=read(C/'bootstrap/CONFIG.json');config.update(expected_thread=THREAD,status='NEW18H_ACTUAL_SAME_THREAD_BOUND_NOT_ARMED',initial_watch_clock=clock,bootstrap_packet_sha256=initial['packet_sha256'])
 arm=C/'armed-controller';packet=b.capsule(arm,THREAD,initial['budget'],config,pins)
 write(arm/'ARM-COMMAND.NOT-EXECUTED.json',dict(status='METADATA_ONLY_NOT_ARMED',packet_sha256=packet,window_sha256=x.window_sha256,argv=['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(arm/'bridge.py'),'--run','--packet-sha256',packet]))
 binding=dict(status='FINALIZED_FOR_EXPLICIT_ARM',scope=config['scope'],thread_id=THREAD,campaign=str(b.CAMPAIGN),deadline=w['deadline_epoch'],deadline_utc=w['deadline_utc'],guardian_journal=str(arm/'journal.json'),guardian_packet_sha256=packet,boot_id=w['boot_id'],focus_path=str(arm/'CURRENT-INVOCATION.txt'),launcher_sha256=pins['canonical']['run_os_goal.py'],review_interval_seconds=1200,window_sha256=x.window_sha256)
 write(M/'ARM-BINDING.NOT-ARMED.json',binding);print(json.dumps(dict(status='BOUND_NO_ARM',guardian_command=str(arm/'ARM-COMMAND.NOT-EXECUTED.json'),monitor_binding=str(M/'ARM-BINDING.NOT-ARMED.json'))))
if __name__=='__main__':main()
