"""Functional OS only; pure manual technical-block admission, no capacity retry."""
import math
from capacity_rules import no_holds, DEADLINE
ROOT='01a18bc3-e072-7810-9426-75101b0856c0'
HELD='01a18a76-b017-76b3-9755-b812d0f923ed'
MAX_BOOT=1571568.6959155537
MAX_MONO=1556230.5688700147
BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'


def require(ok, message):
    if not ok:raise ValueError(message)


def manual_saved_blocked_ready(state):
    require(state.get('thread_id')==ROOT and state.get('phase')=='stopped', 'exact technical Root must be stopped')
    require(not state.get('stop_reason') and state.get('last_error') is None and state.get('last_failure') is None, 'manual resume never overrides a recorded stop or failure')
    require(no_holds(state), 'held or uncertain account/instruction record')
    require(type(state.get('goal')) is dict and state['goal'].get('status')=='blocked' and state['goal'].get('threadId',ROOT)==ROOT, 'saved technical blocked goal required')
    return True


def manual_blocked_ready(state, live_goal, turns):
    manual_saved_blocked_ready(state)
    require(type(live_goal) is dict and live_goal==state.get('goal') and live_goal.get('status')=='blocked' and live_goal.get('threadId',ROOT)==ROOT, 'exact saved blocked goal required')
    require(type(turns) is list and turns and type(turns[0]) is dict and turns[0].get('status') in {'completed','interrupted','failed'} and type(turns[0].get('id')) is str and turns[0]['id'], 'terminal latest turn required')
    require(not any(t.get('status')=='inProgress' for t in turns) and turns[0].get('willRetry') is not True and turns[0].get('error') is None, 'live turn failure or retry requires separate review')
    return True


def finite_number(value):
    require(type(value) in (int,float) and math.isfinite(value) and value>0, 'positive finite inherited cap')
    return value


def tightest_caps(records):
    """Carry every recognized ceiling; absence is never a fresh allowance."""
    boot=[MAX_BOOT];mono=[MAX_MONO];seen={'boot':False,'mono':False}
    def walk(d):
        if type(d) is not dict:return
        if 'boot_id' in d:require(d['boot_id']==BOOT_ID,'inherited boot identity changed')
        for k,v in d.items():
            if k in ('deadline','deadline_epoch'):
                require(finite_number(v)==DEADLINE,'weekly absolute deadline changed')
            elif k=='boot_deadline':boot.append(finite_number(v));seen['boot']=True
            elif k in ('monotonic_deadline','operational_monotonic_deadline','watcher_cutoff_lower'):
                mono.append(finite_number(v));seen['mono']=True
            elif k in ('caps','initial_watch_clock'):walk(v)
    require(type(records) is list and records,'cap receipts required')
    for record in records:walk(record)
    require(all(seen.values()),'BOOT and MONO evidence both required')
    return dict(deadline=DEADLINE,boot_deadline=min(boot),monotonic_deadline=min(mono),boot_id=BOOT_ID)


def phone_matches(phone, observed, config, retained=None):
    owner=phone.get('owner') or {};start=owner.get('starttime')
    require(type(owner.get('pid')) is int and owner['pid']>0 and ((type(start) is int and start>0) or (type(start) is str and start.isdigit() and int(start)>0)), 'phone birth required')
    require(type(observed) is dict and (observed.get('pid'),observed.get('start'))==(owner['pid'],str(start)) and observed.get('state') not in ('Z','X'), 'phone poller not positively live')
    require(phone.get('phase')=='running' and phone.get('boot_id')==BOOT_ID and phone.get('deadline_epoch')==DEADLINE and phone.get('window_path')==config['window_path'] and phone.get('window_sha256')==config['window_sha256'], 'phone window mismatch')
    if retained is not None:require(owner==retained['owner'], 'phone owner changed since preparation')
    return True
