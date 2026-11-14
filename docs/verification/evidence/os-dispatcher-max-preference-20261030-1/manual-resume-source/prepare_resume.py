"""Functional OS only; explicit read-only observation and immutable preparation.
No inference, goal/state mutation, native work or process signal. Default is source only.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'DISPATCHER-SOL-MAX-20261030-1'
REPO=Path('/home/holden/mckernel')
CAMPAIGN=REPO/'.git/os-autopilot'
sys.path.insert(0,str(HERE))
import capacity_supervisor as source
from capacity_rules import worker_routing
from manual_policy import ROOT, HELD, manual_blocked_ready, manual_saved_blocked_ready, tightest_caps, phone_matches, require
sys.path.insert(0,str(REPO/'scripts'))
from run_os_goal import RPC, OBJECTIVE, dispatcher_candidates
SCOPE=source.SCOPE


def sha(raw):return hashlib.sha256(raw).hexdigest()


def create(name,value):return source.create(HERE/name,value)


def lease_free(path):
    # Do not create missing locks or unlink any ownership object.
    with path.open('rb') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        fcntl.flock(stream,fcntl.LOCK_UN)
    return True


def lease_paths(old):
    return [CAMPAIGN/'run.lock',CAMPAIGN/'watch.lock',PRIOR/'supervisor.lock',Path(old['guardian_dir'])/'bridge.lock',Path(old['monitor_dir'])/'supervisor.lock']


def select_routing(catalog):
    exclusions=[]
    for pair in dispatcher_candidates(catalog):
        try:routing=worker_routing(catalog,pair['model'],pair['effort'])
        except ValueError as error:
            exclusions.append(dict(model=pair['model'],reason=str(error)));continue
        return pair,routing,exclusions
    raise ValueError('no advertised dispatcher with required independent lower worker efforts')


def inherited_sources():
    journal=source.read(PRIOR/'journal.json');old=journal['current_envelope']
    require(old['thread_id']==ROOT,'current predecessor envelope must match technical Root')
    # Never substitute previous_monitor_dir: current cursor is authoritative.
    directory=Path(old['directory']);guardian=Path(old['guardian_dir']);monitor=Path(old['monitor_dir'])
    paths=[PRIOR/'journal.json',PRIOR/'CONFIG.json',guardian/'journal.json',guardian/'CONFIG.json',monitor/'journal.json',directory/'bootstrap/initial-watch-clock.json',directory/'bootstrap/CONFIG.json']
    snapshots={str(p):p.read_bytes() for p in paths}
    records=[json.loads(raw) for raw in snapshots.values()]
    caps=tightest_caps(records)
    return old,caps,snapshots


def source_packet():
    # Complete prepared source/observation inventory; runtime output is not present.
    private={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='RESUME-SOURCE-PACKET.json'}
    return create('RESUME-SOURCE-PACKET.json',dict(scope=SCOPE,status='PREPARED_MANUAL_BLOCKED_ROOT_SOURCE_ONLY',authority=None,private=private))


def prepare():
    require(source.HERE==HERE,'local reviewed supervisor must own imports')
    require(os.getuid()==os.geteuid()==1000,'ordinary UID1000 required')
    require(not (HERE/'PREPARED-RESUME.json').exists() and not (HERE/'readonly-preflight').exists(),'immutable one-shot preparation already exists; preserve it')
    state_raw=(CAMPAIGN/'state.json').read_bytes();state=json.loads(state_raw)
    # Saved shape/hold check only; actual terminal turn is read below.
    manual_saved_blocked_ready(state)
    require(state['goal'].get('objective')==OBJECTIVE,'saved objective differs')
    old,caps,cap_snapshots=inherited_sources()
    actors={name:row for name,row in old['binding'].items() if not row.get('not_started')}
    require(set(actors)=={'watcher','worker','server','guardian','monitor'},'complete predecessor envelope required')
    actors['manual_supervisor']=source.read(PRIOR/'MANUAL-SUPERVISOR-ACTUAL-LAUNCH.json')
    actors['capacity_supervisor']=source.read(PRIOR/'supervisor.json')['birth']
    observations={}
    for name,row in actors.items():
        actual=source.birth(row['pid'])
        require(actual is None or actual['start']!=row['start'],'old actor identity still present: '+name)
        observations[name]=dict(retained=row,observed=actual,original_identity_absent=True)
    leases=lease_paths(old)
    require(all(lease_free(p) for p in leases),'predecessor/core lease owned')
    require(source.instructions_clear(),'pending or uncertain instructions need reconciliation')
    require(source.remaining(caps,*source.clocks(),source.boot_id())>120,'tightest inherited weekly ceiling reached')
    prior_config=source.read(PRIOR/'CONFIG.json')
    require(sha(Path(prior_config['window_path']).read_bytes())==prior_config['window_sha256'],'weekly window changed')
    require(sha(Path(prior_config['weekly_authorization_path']).read_bytes())==prior_config['weekly_authorization_sha256'],'weekly authorization changed')
    phone=source.read(CAMPAIGN/'phone-control/watch-status.json');phone_birth=source.birth(phone['owner']['pid'])
    phone_matches(phone,phone_birth,prior_config)
    protocol=HERE/'readonly-preflight';protocol.mkdir()
    rpc=RPC([prior_config['codex'],'-C',str(REPO),'app-server','--stdio'],protocol,lambda event:None)
    try:
        rpc.call('initialize',{'clientInfo':{'name':'mckernel-manual-blocked-resume-preflight','version':'1.0'},'capabilities':{'experimentalApi':True}},timeout=15)
        rpc.send({'method':'initialized','params':{}})
        account=rpc.call('account/read',{'refreshToken':False},timeout=15).get('account') or {}
        limits=rpc.call('account/rateLimits/read',{},timeout=15)['rateLimits'];weekly=limits.get('primary') or {}
        require(account.get('type')=='chatgpt' and limits.get('limitId')=='codex' and not limits.get('spendControlReached') and not limits.get('rateLimitReachedType'),'included account/hold check failed')
        require(weekly.get('windowDurationMins')==10080 and weekly.get('resetsAt')==source.DEADLINE and type(weekly.get('usedPercent')) in (int,float) and 0<=weekly['usedPercent']<100,'original weekly allowance unavailable')
        goal=rpc.call('thread/goal/get',{'threadId':ROOT},timeout=15)['goal']
        turns=rpc.call('thread/turns/list',{'threadId':ROOT,'limit':1,'sortDirection':'desc','itemsView':'notLoaded'},timeout=15)['data']
        manual_blocked_ready(state,goal,turns)
        held=rpc.call('thread/turns/list',{'threadId':HELD,'limit':1,'sortDirection':'desc','itemsView':'notLoaded'},timeout=15)['data']
        require(type(held) is list and held and held[0].get('status') in {'completed','failed','interrupted'},'held child latest turn must remain terminal')
        from catalog_probe import model_rows
        catalog=dict(models=model_rows(rpc.call('model/list',{},timeout=15)['data']),observed_at=time.time(),read_only=True)
    finally:rpc.close()
    require((CAMPAIGN/'state.json').read_bytes()==state_raw,'saved stopped state changed during observation')
    require(source.instructions_clear(),'instructions changed during observation')
    require(all(lease_free(p) for p in leases),'ownership changed during observation')
    require(all(Path(p).read_bytes()==raw for p,raw in cap_snapshots.items()),'inherited caps/cursor changed during observation')
    for name,row in actors.items():
        actual=source.birth(row['pid'])
        require(actual is None or actual['start']!=row['start'],'old actor reappeared during observation: '+name)
    create('STOPPED-STATE.json',state_raw);create('PRIOR-ENVELOPE.json',old)
    create('RETIRED-CONTROLLER-OBSERVATIONS.json',observations)
    create('RETAINED-CREDIT-LEDGER.json',(CAMPAIGN/'credit-runs'/(source.CREDIT+'.json')).read_bytes())
    create('REJECTED-REQUEST.json',dict(thread_id=HELD,turns=held,held=True,replay_authorized=False,equivalent_reassignment_authorized=False,prior_record=source.read(PRIOR/'REJECTED-REQUEST.json'),execve_related_holds_preserved=True))
    create('MODEL-CATALOG.json',catalog)
    (HERE/'inherited-receipts').mkdir()
    refs={}
    for i,(p,raw) in enumerate(cap_snapshots.items()):
        name='inherited-receipts/'+str(i)+'-'+Path(p).name;create(name,raw);refs[p]=sha(raw)
    create('INHERITED-SOURCE-REFS.json',refs)
    create('PHONE-OBSERVATION.json',dict(state=phone,identity=phone_birth,observed_at=time.time(),cursor=source.read(CAMPAIGN/'phone-control/status.json')))
    create('PREFLIGHT.json',dict(scope=SCOPE,at=time.time(),state_sha256=sha(state_raw),goal=goal,turns=turns,quota=limits,caps=caps,account_type='chatgpt',leases=[str(p) for p in leases],native_clearance_claimed=False))
    pair,routing,exclusions=select_routing(catalog);model,effort=pair['model'],pair['effort']
    agents=dict(state['settings']['agents']);agents.update(max_concurrent_threads_per_session=10,default_subagent_model=model,default_subagent_reasoning_effort='medium')
    config=dict(scope=SCOPE,launch_kind='initial_weekly_handoff',selected_model=model,selected_effort=effort,initial_model=model,initial_effort=effort,initial_routing=routing,initial_root_thread=ROOT,initial_agent_settings=agents,explicit_dispatcher_model_override=True,advertised_models=[r['model'] for r in catalog['models']],advertised_efforts={r['model']:r['efforts'] for r in catalog['models']},capacity_predecessor=None,billing_mode='included_only',allow_prepaid_fallback=False,caps=caps,credit_run_id=source.CREDIT,credit_ceiling=str(source.CEILING))
    note=(SCOPE+'\nResume SAME technical blocked Root '+ROOT+' under standing explicit manual user authorization; this is not capacity recovery. Dispatcher '+model+'/'+effort+'. Advertisement proves neither capacity nor entitlement. Workers: default medium, complex/reviewer high, auditor low.\n'+(HERE/'ENGINEERING-HANDOFF.md').read_text()+'\nRead '+str(HERE/'ENGINEERING-HANDOFF.md')+' before assignments.\n').encode()
    require(len(note)<=8192,'bounded startup note exceeded')
    bootstrap=HERE/'bootstrap';bootstrap.mkdir()
    for n,value in [('CONFIG.json',config),('CURRENT-INVOCATION.txt',note),('bridge.py',(HERE/'guardian_template.py').read_bytes()),('finite_launcher.py',source.finite_source()),('weekly_policy.py',(HERE/'weekly_policy.py').read_bytes())]:source.create(bootstrap/n,value)
    canonical={n:sha((REPO/'scripts'/n).read_bytes()) for n in source.CORE}
    support={p.name:sha(p.read_bytes()) for p in sorted((REPO/'scripts').glob('os_goal_*.py')) if p.name not in canonical}
    bsha=source.packet_for(bootstrap,canonical,('bridge.py','finite_launcher.py','weekly_policy.py','CONFIG.json','CURRENT-INVOCATION.txt'),model)
    argv=['/usr/bin/taskset','-c','0,2-7',source.PYTHON,'-B',str(bootstrap/'finite_launcher.py'),'--deadline-utc',source.UTC,'--boot-deadline',str(caps['boot_deadline']),'--monotonic-deadline',str(caps['monotonic_deadline']),'--packet-sha256',bsha,'--publish-initial-clock','--','--codex',prior_config['codex'],'--model',model,'--effort',effort,'--profile','aggressive','--max-agents','10','--build-jobs','7','--agent-windows','off','--stall-seconds','1800','--watchdog-seconds','180','--quiet','--grace-seconds','30','--startup-instruction-file',str(bootstrap/'CURRENT-INVOCATION.txt'),'--startup-instruction-sha256',sha(note)]
    create('PREPARED-RESUME.json',dict(scope=SCOPE,root=ROOT,argv=argv,caps=caps,bootstrap_sha256=bsha,canonical=canonical,canonical_support=support,note_sha256=sha(note),target_model=model,target_effort=effort,initial_routing=routing,initial_agent_settings=agents,selection_capability_exclusions=exclusions,prior_config=prior_config,runtime_started=False))
    source_sha=source_packet()
    print(json.dumps(dict(status='SOURCE_PREPARED_NO_CAMPAIGN_START',root=ROOT,path=str(HERE),source_packet_sha256=source_sha,weekly_used_percent=weekly['usedPercent'])))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');a=p.parse_args()
    if not a.prepare:
        print('SOURCE_ONLY_UNSELECTED: explicit --prepare performs read-only observations and immutable preparation; never starts campaign')
        return
    prepare()

if __name__=='__main__':main()
