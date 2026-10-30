"""Functional OS only: source-only default; explicit read-only reminder rebind preparation.
Never queues text, starts a reminder, mutates campaign state or grants control authority.
"""
import argparse
from datetime import datetime
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import sys
import time
import foreground_reminder as reminder
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'FOREGROUND-15MIN-PRIORITY-SOLMAX-20261030-3'
CONTROLLER=HERE.parent/'DISPATCHER-MAX-PREFERRED-20261030-1'
ORIGIN='01a18ac2-f20f-7992-828e-cd269dff983f'
REPO=Path('/home/holden/mckernel')
CAMPAIGN=REPO/'.git/os-autopilot'
SCOPE=reminder.SCOPE


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def finite(value):
    require(type(value) in (int,float) and math.isfinite(value) and value>0,'positive finite cadence/cap required')
    return value


def actual(row,observed):
    return (type(row) is dict and type(row.get('pid')) is int and row['pid']>0 and type(row.get('start')) is str and row['start'].isdigit() and int(row['start'])>0 and type(observed) is dict and (row['pid'],row['start'])==(observed.get('pid'),observed.get('start')) and observed.get('state') not in ('Z','X'))


def bind_config(old_config,old_status,old_actual,control,capacity,journal,state,observed,clocks,origin,launcher_sha,guardian_journal):
    """Pure consistency checks of supplied observations; no authentication or I/O.

    Only prepare() below obtains actual evidence through the controller interfaces.
    Synthetic calls to this function never establish real readiness or authority.
    """
    require(type(control) is dict and type(capacity) is dict,'both actual receipts required')
    require(capacity.get('status')=='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME','healthy actual capacity receipt required')
    require(control.get('native_release') is False and capacity.get('native_release') is False,'model controls grant no native release')
    env=journal['current_envelope'];thread=env['thread_id']
    require(thread==state.get('thread_id')==control.get('thread_id')==capacity.get('thread_id'),'actual receipt/current Root mismatch')
    require(journal.get('status')=='armed','current controller journal not armed')
    require(origin==ORIGIN==old_config.get('origin_window')==old_status.get('origin_window'),'actual foreground origin mismatch')
    require(old_status.get('phase')=='stopped','old reminder is not positively stopped')
    old_birth=old_status.get('owner')
    require(type(old_birth) is dict and (old_birth.get('pid'),old_birth.get('start'))==(old_actual.get('pid'),old_actual.get('start')),'old actual launch/status birth mismatch')
    require(observed['old_reminder'] is None or observed['old_reminder'].get('start')!=old_birth['start'],'old reminder birth still present')
    require(observed['old_lease_free'] is True,'old reminder lease is owned')
    require(type(old_status.get('deliveries')) is int and old_status['deliveries']>=old_config.get('previous_deliveries',0),'historical delivery count')
    require(old_status.get('sequence',old_status['deliveries'])==old_status['deliveries'],'unresolved predecessor queue sequence')
    require(old_config.get('interval_seconds')==reminder.INTERVAL==900,'literal15minute cadence changed')
    boot_id=clocks['boot_id'];caps=[]
    for candidate in (old_config['caps'],control['caps'],capacity['caps'],journal['caps']):
        require(candidate['boot_id']==boot_id and candidate['deadline']==1793774133,'original cap boot/reset mismatch');caps.append(candidate)
    new_caps=dict(boot_id=boot_id,deadline=min(x['deadline'] for x in caps),boot_deadline=min(finite(x['boot_deadline']) for x in caps),monotonic_deadline=min(finite(x['monotonic_deadline']) for x in caps))
    require(type(observed['locks_owned']) is dict and set(observed['locks_owned'])=={'run','watch','guardian','monitor','capacity'} and all(v is True for v in observed['locks_owned'].values()),'healthy actual controller leases required')
    for role in ('watcher','guardian','monitor'):
        retained=env['binding'][role]
        require(actual(retained,observed[role]),'live controller identity differs: '+role)
        for receipt in (control,capacity):
            require((receipt['binding'][role]['pid'],receipt['binding'][role]['start'])==(retained['pid'],retained['start']),'actual control receipt birth differs: '+role)
    require(actual(capacity['supervisor'],observed['capacity']),'live capacity supervisor differs')
    cp=observed['capacity_publication']
    require(cp.get('pid')==capacity['supervisor']['pid'] and cp.get('birth',{}).get('start')==capacity['supervisor']['start'] and cp.get('source_packet_sha256')==capacity['source_packet_sha256']==journal.get('source_packet_sha256'),'capacity publication/source packet differs')
    mp=observed['monitor_publication'];mj=observed['monitor_journal'];monitor=env['binding']['monitor']
    require(mp.get('pid')==monitor['pid'] and mp.get('start_ticks')==monitor['start'] and mp.get('thread_id')==thread and mp.get('arm_binding_sha256')==env['monitor_arm_sha256']==control['monitor_arm_sha256'] and mj.get('arm_binding_sha256')==env['monitor_arm_sha256'] and mj.get('status')=='queued' and mp.get('guardian_packet_sha256')==env['guardian_packet_sha256'],'monitor publication/cursor health differs')
    for role in ('worker','server'):
        require(actual(dict(pid=state[role+'_pid'],start=state[role+'_start']),observed[role]),'live model identity differs: '+role)
    require(observed['worker']['ppid']==observed['watcher']['pid'] and observed['server']['ppid']==observed['worker']['pid'],'live model ancestry differs')
    guardian=observed['guardian'];gj=observed['guardian_journal'];packet=env['guardian_packet_sha256']
    require(packet==control['guardian_packet_sha256']==gj.get('packet_sha256') and not gj.get('transition_hold') and not str(gj.get('last_action','')).startswith(('HOLD_','STOP_')),'actual guardian packet/health differs')
    require(clocks['boot']<finite(gj['boot_deadline']),'guardian cap reached')
    new_caps['boot_deadline']=min(new_caps['boot_deadline'],gj['boot_deadline'])
    cfg=dict(old_config)
    cfg.update(scope=SCOPE,target_thread=thread,caps=new_caps,guardian=guardian,guardian_journal=str(guardian_journal),guardian_packet_sha256=packet,launcher_sha256=launcher_sha,previous_reminder=str(PRIOR),previous_deliveries=old_status['deliveries'],carried_next_due_monotonic=finite(old_status['next_due_monotonic']),native_release=False)
    require(reminder.decision(state,cfg,clocks['wall'],clocks['boot'],clocks['mono'],boot_id)=='ready','current campaign is not actually reminder-ready')
    return cfg


def interfaces():
    # Import only definitions from the new reviewed controller source, never main.
    sys.path.insert(0,str(CONTROLLER));sys.path.insert(0,str(REPO/'scripts'))
    s=importlib.import_module('capacity_supervisor');p=importlib.import_module('prepare_resume');ready=importlib.import_module('readiness')
    require(s.HERE==CONTROLLER and Path(p.__file__).resolve().parent==CONTROLLER and Path(ready.__file__).resolve().parent==CONTROLLER,'new controller interfaces required')
    return s,p,ready


def create(name,value):
    raw=value if type(value) is bytes else (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    with (HERE/name).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return sha(raw)


def prepare():
    require(os.getuid()==os.geteuid()==1000,'ordinary UID1000 required')
    require(os.environ.get('CODEX_THREAD_ID')==ORIGIN,'Root foreground environment does not match literal origin window')
    require(not any((HERE/n).exists() for n in ('CONFIG.json','SOURCE-PACKET.json','status.json','HOLD.json','STOP.json')),'immutable reminder preparation/runtime already exists')
    # Missing actual receipts refuse before controller interface import or probes.
    required=[CONTROLLER/'ACTUAL-CONTROLS-ARMED.json',CONTROLLER/'ACTUAL-CAPACITY-FALLBACK-ARMED.json']
    require(all(p.is_file() for p in required),'actual healthy controls and capacity receipts required before reminder preparation')
    s,p,ready=interfaces()
    require(not any((PRIOR/n).exists() for n in ('HOLD.json','STOP.json')),'old reminder hold/cancellation must be preserved and separately resolved')
    inputs={str(path):path.read_bytes() for path in [PRIOR/'CONFIG.json',PRIOR/'status.json',PRIOR/'ACTUAL-LAUNCH.json',*required]}
    old_config,old_status,old_actual,control,capacity=[json.loads(raw) for raw in inputs.values()]
    old_packet_raw=(PRIOR/'SOURCE-PACKET.json').read_bytes();old_packet=json.loads(old_packet_raw)
    require(sha(old_packet_raw)==old_status['source_packet_sha256'],'old reminder sealed packet changed')
    inputs[str(PRIOR/'SOURCE-PACKET.json')]=old_packet_raw
    for name,digest in old_packet['sources'].items():
        require(Path(name).name==name,'old reminder source name differs')
        raw=(PRIOR/name).read_bytes();require(sha(raw)==digest,'old reminder source changed: '+name);inputs[str(PRIOR/name)]=raw
    journal=s.read(CONTROLLER/'journal.json');env=journal['current_envelope'];state=s.read(CAMPAIGN/'state.json')
    require(s.no_holds(state) and s.instructions_clear(),'held/uncertain account or instruction state')
    s.check_packet(CONTROLLER/'SOURCE-PACKET.json',capacity['source_packet_sha256'])
    binding=s.live_binding(env,state)
    expected={k:state.get(k) for k in ('worker_pid','worker_start','server_pid','server_start')}
    require(ready.fresh_heartbeat(state,journal['attempts'][0]['at'],time.time(),expected),'current-invocation actor-pinned heartbeat required')
    observed={role:s.birth(row['pid']) for role,row in binding.items()}
    observed['capacity']=s.birth(capacity['supervisor']['pid'])
    observed['capacity_publication']=s.read(CONTROLLER/'supervisor.json')
    observed['monitor_publication']=s.read(Path(env['monitor_dir'])/'supervisor.json')
    observed['monitor_journal']=s.read(Path(env['monitor_dir'])/'journal.json')
    observed['old_reminder']=s.birth(old_status['owner']['pid'])
    observed['old_lease_free']=p.lease_free(PRIOR/'reminder.lock')
    locks=dict(run=CAMPAIGN/'run.lock',watch=CAMPAIGN/'watch.lock',guardian=Path(env['guardian_dir'])/'bridge.lock',monitor=Path(env['monitor_dir'])/'supervisor.lock',capacity=CONTROLLER/'supervisor.lock')
    observed['locks_owned']={name:not p.lease_free(path) for name,path in locks.items()}
    gj_path=Path(env['guardian_dir'])/'journal.json';observed['guardian_journal']=s.read(gj_path)
    raw_launcher=reminder.LAUNCHER.read_bytes()
    wall,boot,mono=s.clocks();clocks=dict(wall=wall,boot=boot,mono=mono,boot_id=s.boot_id())
    cfg=bind_config(old_config,old_status,old_actual,control,capacity,journal,state,observed,clocks,os.environ['CODEX_THREAD_ID'],sha(raw_launcher),gj_path)
    baseline=REPO/cfg['baseline_function_queue'];baseline_raw=baseline.read_bytes()
    # Require a resolved last delivery receipt without replaying the old queue.
    if old_status['deliveries']>old_config['previous_deliveries']:
        last=PRIOR/('delivery-%05d.json'%old_status['deliveries']);raw=last.read_bytes();receipt=json.loads(raw)
        require(receipt['sequence']==old_status['deliveries'] and receipt['instruction_id']==old_status['last_instruction_id'],'old last delivery unresolved')
        inputs[str(last)]=raw
    require(all(Path(path).read_bytes()==raw for path,raw in inputs.items()),'old reminder/actual receipt changed during observation')
    fresh=s.read(CAMPAIGN/'state.json')
    require(all(fresh.get(k)==state.get(k) for k in ('thread_id','worker_pid','worker_start','server_pid','server_start')),'model binding changed during observation')
    require(reminder.decision(fresh,cfg,*s.clocks(),s.boot_id())=='ready','campaign changed before preparation publication')
    create('PREDECESSOR-STATUS.json',inputs[str(PRIOR/'status.json')])
    create('PREDECESSOR-CONFIG.json',inputs[str(PRIOR/'CONFIG.json')])
    create('PREPARATION-OBSERVATIONS.json',dict(scope=SCOPE,status='OBSERVED_ONLY_NO_REMINDER_STARTED',native_release=False,origin_window=os.environ['CODEX_THREAD_ID'],clocks=clocks,state=state,current_envelope=env,observed=observed,controller_journal=journal,control_receipt=control,capacity_receipt=capacity,external_hashes={path:sha(raw) for path,raw in inputs.items()},baseline_function_queue_sha256=sha(baseline_raw),canonical_launcher_sha256=sha(raw_launcher)))
    create('CONFIG.json',cfg)
    sources={path.name:sha(path.read_bytes()) for path in sorted(HERE.iterdir()) if path.is_file() and path.name!='SOURCE-PACKET.json'}
    digest=create('SOURCE-PACKET.json',dict(scope=SCOPE,sources=sources,native_release=False,reminder_started=False,authority=None))
    reminder.verify(digest)  # Exact source-only verification; no load_queue/run.
    print(json.dumps(dict(status='PREPARED_SOURCE_ONLY_NO_REMINDER_STARTED',source_packet_sha256=digest,target_thread=cfg['target_thread'],origin_window=cfg['origin_window'],native_release=False)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if not args.prepare:
        print('SOURCE_ONLY_UNSELECTED: Root may explicitly --prepare after actual healthy campaign receipts; no reminder started')
        return
    prepare()

if __name__=='__main__':main()
