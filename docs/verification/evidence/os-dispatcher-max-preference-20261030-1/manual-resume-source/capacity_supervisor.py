#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Cold, explicit-arm capacity fallback. This never performs native cleanup. Only a
typed terminal capacity failure can authorize another finite model envelope.
An unknown launch or queue result requires reconciliation, never blind replay.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from capacity_rules import (BOOT_CAP, CEILING, CREDIT, DEADLINE, MONO_CAP, budget_ok,
                            canonical, child_capacity, choose_model, digest,
                            effort_for, worker_routing, live_root_matches, no_holds, remaining, retired,
                            root_capacity, submission_action, terminal_child_hint, tighten)

HERE = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
CAMPAIGN = REPO/'.git/os-autopilot'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
UTC = '2026-11-04T06:35:33+00:00'
PYTHON = '/home/holden/anaconda3/bin/python3'
CORE = frozenset(('run_os_goal.py', 'watch_os_goal.py', 'os_goal_transport.py',
                  'os_goal_handoff.py', 'os_goal_credits.py'))
PRIVATE = frozenset(('capacity_supervisor.py','capacity_rules.py','catalog_probe.py',
                     'guardian_template.py','finite_launcher_template.py','steering_template.py',
                     'MODEL-CATALOG.json','CONFIG.json','weekly_policy.py'))
DIRECT_CHILDREN = {}


class CapacityDuringArm(RuntimeError):
    """A new, attributed capacity failure may rotate after complete retirement."""


def read(path, cap=4 << 20):
    raw = Path(path).read_bytes()
    if len(raw) > cap:
        raise ValueError('bounded metadata cap exceeded')
    return json.loads(raw)


def raw_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def create(path, value):
    raw = value if isinstance(value, bytes) else raw_json(value)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return digest(raw)


def atomic(path, value):
    temp = path.with_name(path.name+'.tmp-'+str(os.getpid()))
    create(temp, value)
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def birth(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError('positive process identity required')
    try:
        fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    if len(fields) < 20 or not fields[19].isdigit() or int(fields[19]) <= 0:
        raise ValueError('unreadable process birth')
    return dict(pid=pid, start=fields[19], ppid=int(fields[1]), state=fields[0])


def free_lease(path):
    with path.open('a+b') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(stream, fcntl.LOCK_UN)
        return True


def instructions_clear():
    return all(not list((CAMPAIGN/'instructions'/name).glob('*.json'))
               for name in ('pending', 'sending'))


def clocks():
    return time.time(), time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic()


def latch_weekly_end(journal,state):
    """Carry any earlier confirmed ceiling across worker/fresh-session changes."""
    end=min(DEADLINE,journal.get('weekly_effective_end',DEADLINE),
            state.get('weekly_effective_end',DEADLINE))
    if type(end) not in (int,float) or not (1793251609.1432834<end<=DEADLINE):
        raise ValueError('confirmed weekly end is invalid')
    wall,boot,mono=clocks()
    if state.get('weekly_effective_boot_id',journal['caps']['boot_id'])!=journal['caps']['boot_id']:
        raise ValueError('confirmed quota bounds belong to another boot')
    journal['weekly_effective_end']=end
    journal['caps']['boot_deadline']=min(journal['caps']['boot_deadline'],boot+max(0,end-wall),BOOT_CAP+(end-DEADLINE))
    journal['caps']['monotonic_deadline']=min(journal['caps']['monotonic_deadline'],mono+max(0,end-wall),MONO_CAP+(end-DEADLINE))
    for source,target in (('weekly_effective_boot_end','boot_deadline'),
                          ('weekly_effective_monotonic_end','monotonic_deadline')):
        if source in state:
            value=state[source]
            if type(value) not in (int,float) or not 0<value<float('inf'):
                raise ValueError('confirmed monotonic weekly end is invalid')
            journal['caps'][target]=min(journal['caps'][target],value)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def check_packet(path, expected):
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError('explicit sealed capacity packet changed')
    packet = json.loads(raw)
    if set(packet['canonical']) != CORE:
        raise ValueError('exact five canonical launcher sources required')
    if set(packet['private']) != PRIVATE:
        raise ValueError('complete exact private controller/config/catalog source set required')
    for name, sha in packet['canonical'].items():
        if digest((REPO/'scripts'/name).read_bytes()) != sha:
            raise ValueError('canonical source drift: '+name)
    for name, sha in packet['private'].items():
        if Path(name).name != name or digest((HERE/name).read_bytes()) != sha:
            raise ValueError('private source/config drift: '+name)
    config = read(HERE/'CONFIG.json')
    if (config.get('status') != 'FINALIZED_FOR_EXPLICIT_CAPACITY_FALLBACK_ARM'
            or config.get('capacity_fallback_authorized') is not True
            or config.get('billing_mode') != 'included_only'
            or config.get('allow_prepaid_fallback') is not False
            or config.get('credit_run_id') != CREDIT
            or Decimal(str(config.get('credit_ceiling'))) != CEILING):
        raise ValueError('explicit capacity-only authority and retained allowance required')
    floor=Decimal(str(config.get('credit_spent_floor')))
    envelope=config.get('initial_envelope')
    if (not floor.is_finite() or not 0 <= floor < CEILING or not isinstance(envelope,dict)
            or not isinstance(envelope.get('thread_id'),str) or not envelope['thread_id']
            or not isinstance(config.get('initial_model'),str)
            or not config['initial_model'].startswith(('gpt-6.1-','gpt-6-'))):
        raise ValueError('actual initial thread/model and cumulative debit floor required')
    for name in ('guardian_dir','monitor_dir'):
        if not Path(envelope[name]).is_absolute():
            raise ValueError('absolute existing-controller paths required')
    if any(row.get('not_started') for row in envelope['binding'].values()):
        raise ValueError('initial full live envelope must have actual five process births')
    retired(envelope['binding'],lambda pid:None)  # Pure schema validation only.
    if not Path(config['codex']).is_file() or not os.access(config['codex'],os.X_OK):
        raise ValueError('actual executable Codex path required')
    if digest(Path(config['window_path']).read_bytes()) != config['window_sha256']:
        raise ValueError('original actual window changed')
    window = read(config['window_path'])
    auth_raw=Path(config['weekly_authorization_path']).read_bytes()
    if digest(auth_raw)!=config['weekly_authorization_sha256']:
        raise ValueError('weekly-only user authority changed')
    auth=json.loads(auth_raw)
    if (window.get('deadline_epoch') != DEADLINE or auth.get('deadline_epoch') != DEADLINE
            or auth.get('prepaid_credit_fallback') is not False
            or auth.get('weekly_limit_identity')!={'limit_id':'codex','window_duration_mins':10080,'resets_at':DEADLINE}):
        raise ValueError('weekly-only deadline/reset/billing authority changed')
    if remaining(config['caps'], *clocks(), boot_id()) <= 0:
        raise ValueError('authorized window expired')
    return packet, config


def metadata(config, root, child=None):
    """Only owned temporary server and read-only goal/terminal-turn requests."""
    from catalog_probe import CatalogRPC
    client = CatalogRPC(config['codex'], time.monotonic()+30,
                        ('initialize', 'thread/goal/get', 'thread/turns/list'))
    try:
        client.call('initialize', {'clientInfo': {'name': 'mckernel-capacity-metadata',
                                                 'version': '1.0'},
                                   'capabilities': {'experimentalApi': True}})
        client.send({'method': 'initialized', 'params': {}})
        goal = client.call('thread/goal/get', {'threadId': root})['goal']
        turns = client.call('thread/turns/list', {'threadId': child or root, 'limit': 1,
                                                'sortDirection': 'desc', 'itemsView': 'notLoaded'})['data']
        return goal, turns
    finally:
        client.close()


def live_binding(envelope, state):
    if ((state.get('settings') or {}).get('billing') or {}).get('mode')!='included_only':
        raise ValueError('weekly-only controller cannot adopt a credit-funded worker')
    watch = read(CAMPAIGN/'watcher.json')
    old = envelope['binding']['watcher']
    watcher = birth(watch['watcher_pid'])
    worker, server = birth(state['worker_pid']), birth(state['server_pid'])
    if (watcher is None or worker is None or server is None
            or any(row['state'] == 'Z' for row in (watcher, worker, server))
            or (watcher['pid'], watcher['start']) != (old['pid'], old['start'])
            or worker['ppid'] != watcher['pid'] or server['ppid'] != worker['pid']
            or worker['start'] != state['worker_start'] or server['start'] != state['server_start']):
        raise ValueError('healthy actual watcher/worker/server chain differs')
    result = dict(envelope['binding'], watcher=watcher, worker=worker, server=server)
    for name in ('guardian', 'monitor'):
        row = result[name]
        if row.get('not_started') is True:
            continue
        actual = birth(row['pid'])
        if actual is None or actual['start'] != row['start'] or actual['state'] == 'Z':
            raise ValueError('live auxiliary identity differs: '+name)
    return result


def ledger(journal):
    row = read(CAMPAIGN/'credit-runs'/(CREDIT+'.json'))
    if not budget_ok(row, journal['credit_spent_floor']):
        raise ValueError('historical credit ledger identity or debit floor changed')
    journal['credit_spent_floor'] = str(Decimal(str(row['spent'])))
    return row


def stopped_for_user(config, envelope):
    paths = [HERE/'STOP.json'] + [Path(p) for p in config.get('user_stop_files', [])]
    paths.append(Path(envelope['guardian_dir'])/'USER-STOP.json')
    return any(p.exists() for p in paths)


def packet_for(directory, canonical_sources, names, model):
    value = dict(scope=SCOPE, deadline_utc=UTC, credit_run_id=CREDIT,
                 credit_ceiling=str(CEILING), selected_model=model, canonical=canonical_sources,
                 private={name: digest((directory/name).read_bytes()) for name in names})
    return create(directory/'FROZEN-PACKET.json', value)


def finite_source():
    """Three bounded edits to the reviewed finite launcher; preserve its watcher."""
    source = (HERE/'finite_launcher_template.py').read_text()
    needle = '    import run_os_goal\n'
    assert source.count(needle) == 1
    source = source.replace(needle, needle + '''    import json
    config = json.loads((Path(__file__).resolve().parent/'CONFIG.json').read_bytes())
    selected = config['selected_model']
    effort = config['selected_effort']
    if selected not in config['advertised_models']:
        raise ValueError('selected fallback model is not in the sealed advertised catalog')
    if rest.count('--model') != 1 or rest[rest.index('--model')+1] != selected:
        raise ValueError('dispatcher model differs from sealed fallback routing')
    sealed_catalog = {'models': [{'model': m, 'efforts': e} for m, e in config['advertised_efforts'].items()]}
    if set(config['advertised_models']) != set(config['advertised_efforts']):
        raise ValueError('sealed catalog membership differs')
    supported = config['advertised_efforts'].get(selected, [])
    preferred = next((r['effort'] for r in run_os_goal.dispatcher_candidates(sealed_catalog) if r['model'] == selected), None)
    if preferred is None or type(effort) is not str:
        raise ValueError('known advertised dispatcher pair required')
    levels = dict(default_worker='medium', complex_worker='high', auditor='low', reviewer='high')
    if not set(levels.values()) <= set(supported):
        raise ValueError('independent lower worker efforts are not advertised')
    routing = dict(dispatcher=dict(model=selected, effort=effort),
                   **{role: dict(model=selected, effort=level) for role, level in levels.items()})
    initial = config.get('launch_kind') == 'initial_weekly_handoff'
    if initial:
        if config.get('initial_routing') != routing:
            raise ValueError('initial sealed routing differs from independent worker policy')
        saved=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
        if saved.get('thread_id') != config['initial_root_thread'] or '--fresh-session' in rest:
            raise ValueError('weekly handoff must resume the same bound Root without a fresh session')
    allowed_effort = (effort == config.get('initial_effort') and selected == config.get('initial_model')
                      and effort == preferred) if initial else effort == preferred
    if (not allowed_effort or rest.count('--effort') != 1
            or rest[rest.index('--effort')+1] != effort):
        raise ValueError('dispatcher effort differs from sealed weekly routing')
    run_os_goal.DEFAULT_DISPATCHER_MODEL = selected
    run_os_goal.DEFAULT_WORKER_MODEL = selected
    run_os_goal.AUDIT_MODEL = selected
    run_os_goal.REVIEW_MODEL = selected
    # Canonical parser already accepts its full advertised effort vocabulary.
    # Keep AST only for the separate, retained watcher command adaptation below.
    import ast
    original_agent_settings = run_os_goal.agent_settings
    def capacity_agent_settings(args, repo):
        settings = original_agent_settings(args, repo)
        settings['default_subagent_model'] = routing['default_worker']['model']
        settings['default_subagent_reasoning_effort'] = routing['default_worker']['effort']
        return settings
    def capacity_model_routing(args):
        return routing
    run_os_goal.agent_settings = capacity_agent_settings
    run_os_goal.model_routing = capacity_model_routing
    original_instructions = run_os_goal.Campaign.instructions
    def capacity_instructions(campaign):
        text = original_instructions(campaign)
        return text + ('\\nCurrent sealed invocation routing: '+json.dumps(capacity_model_routing(campaign.args),sort_keys=True)+
            '. Dispatcher max preferred; default workers medium, complex/reviewers high, auditors low. '
            'Latest authenticated priority: M14 EXCLUSIVELY until accepted; only then M15. '
            'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.')
    run_os_goal.Campaign.instructions = capacity_instructions
    from weekly_policy import install
    install(run_os_goal,1793774133)
    predecessor = config.get('capacity_predecessor')
    if predecessor is not None:
        original_prepare = run_os_goal.Campaign.prepare_fresh_goal
        def capacity_prepare(campaign):
            current = campaign.state.get('thread_id')
            previous = campaign.state.get('previous_session') or {}
            if current:
                if current == predecessor['thread_id']:
                    raise ValueError('capacity predecessor was not archived before alternate startup')
                # Ordinary worker recovery resumes the already-started alternate
                # thread; its original capacity predecessor is historical now.
                return original_prepare(campaign)
            if previous.get('thread_id') != predecessor['thread_id']:
                args = campaign.args
                if (getattr(args, 'recovered', False)
                        and getattr(args, 'fresh_recovery_proof', None)
                        and (getattr(args, 'recovery_goal_sha256', None)
                             or getattr(args, 'recovery_require_active', False))):
                    # The canonical path validates its own archived successor,
                    # actual proof and live goal. Do not replace those checks.
                    return original_prepare(campaign)
                raise ValueError('unexpected unproved capacity predecessor transition')
            def allowed():
                live = campaign.rpc.call('thread/goal/get', {'threadId': predecessor['thread_id']})['goal']
                turns = campaign.rpc.call('thread/turns/list', {'threadId': predecessor['thread_id'],
                    'limit': 1, 'sortDirection': 'desc', 'itemsView': 'notLoaded'})['data']
                if (live != predecessor['goal'] or live.get('status') != 'blocked'
                        or not turns or turns[0].get('id') != predecessor['failed_turn']
                        or turns[0].get('status') != 'failed' or turns[0].get('willRetry') is True
                        or turns[0].get('error') != predecessor['error']):
                    campaign.remember_goal(live)
                    campaign.stop_reason, campaign.stop_now = 'startup_goal_stopped', True
                    return False
                return True
            # Bind inside actual fresh-session startup, before and after the
            # canonical archive/goal checks. No old goal is resumed or cleared.
            return allowed() and original_prepare(campaign) and allowed()
        run_os_goal.Campaign.prepare_fresh_goal = capacity_prepare
''')
    needle = '    import watch_os_goal\n'
    assert source.count(needle) == 1
    source = source.replace(needle,needle+'''    # Canonical watcher workers are separate Python processes. Re-enter this
    # exact sealed private entry so routing/effort/predecessor checks survive
    # every actual worker start. Only its command assignment is adapted.
    watcher_path = Path('/home/holden/mckernel/scripts/watch_os_goal.py')
    watcher_tree = ast.parse(watcher_path.read_bytes(), filename=str(watcher_path))
    watcher_nodes = [node for node in watcher_tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == 'supervise']
    if len(watcher_nodes) != 1 or args.monotonic_deadline is None:
        raise ValueError('canonical watcher and fixed monotonic cutoff required')
    worker_prefix = [str(Path(__file__).resolve()), '--deadline-utc', args.deadline_utc,
        '--boot-deadline', str(args.boot_deadline), '--monotonic-deadline', str(args.monotonic_deadline),
        '--packet-sha256', args.packet_sha256, '--']
    expected_script = ast.parse("str(repo / 'scripts/run_os_goal.py')", mode='eval').body
    replacements = 0
    for node in ast.walk(watcher_nodes[0]):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'command'):
            if (not isinstance(node.value, ast.List) or len(node.value.elts) < 4
                    or ast.dump(node.value.elts[2]) != ast.dump(expected_script)):
                raise ValueError('canonical worker command interface differs')
            node.value.elts = node.value.elts[:2] + [ast.Constant(value=s) for s in worker_prefix] + node.value.elts[3:]
            replacements += 1
    if replacements != 1:
        raise ValueError('one exact canonical worker command adaptation required')
    watcher_module = ast.fix_missing_locations(ast.Module(body=watcher_nodes,type_ignores=[]))
    exec(compile(watcher_module,str(watcher_path),'exec'),watch_os_goal.__dict__)
''')
    needle = 'boot_deadline=args.boot_deadline,'
    assert source.count(needle) == 1
    # Publish an actual conservative BOOT bound for the watcher's once-only MONO clock.
    source = source.replace(needle, 'boot_deadline=min(args.boot_deadline, '
                            'time.clock_gettime(time.CLOCK_BOOTTIME) + started_lower + seconds - time.monotonic()),')
    compile(source, '<capacity finite launcher>', 'exec')
    return source.encode()


def spawn(argv, directory, label):
    create(directory/(label+'-LAUNCH-INTENT.json'), dict(argv=argv, scope=SCOPE, at=time.time()))
    with (directory/(label+'.log')).open('xb', buffering=0) as stream:
        child = subprocess.Popen(argv, cwd=REPO, stdin=subprocess.DEVNULL, stdout=stream,
                                 stderr=stream, start_new_session=True)
    DIRECT_CHILDREN[child.pid] = (child,directory,label)
    row = birth(child.pid)
    if row is None:
        raise ValueError('launch result identity unavailable; preserve intent, never repeat')
    create(directory/(label+'-ACTUAL-LAUNCH.json'), row)
    return row


def reap_children():
    for pid,(child,directory,label) in list(DIRECT_CHILDREN.items()):
        code = child.poll()  # Direct waitpid(WNOHANG); no PID-based signaling.
        if code is not None:
            create(directory/(label+'-DIRECT-EXIT.json'),dict(pid=pid,returncode=code,
                                                          direct_parent_join=True,at=time.time()))
            del DIRECT_CHILDREN[pid]


def interrupted_arm(journal,watcher,attempt):
    """Preserve positively known births if capacity occurs before auxiliary arm."""
    state=read(CAMPAIGN/'state.json')
    old=journal['current_envelope']
    if not root_capacity(state):
        return
    initial_path=attempt/'bootstrap/initial-watch-clock.json'
    if initial_path.exists():
        initial=read(initial_path)
        expected=digest((attempt/'bootstrap/FROZEN-PACKET.json').read_bytes())
        if (initial.get('watcher_pid'),initial.get('watcher_start'),initial.get('bootstrap_packet_sha256'))!=(watcher['pid'],watcher['start'],expected):
            raise ValueError('failed startup actual watcher clock differs')
        journal['caps']['boot_deadline']=min(journal['caps']['boot_deadline'],initial['boot_deadline'])
        journal['caps']['monotonic_deadline']=min(journal['caps']['monotonic_deadline'],initial['watcher_cutoff_lower'])
    if old.get('directory')==str(attempt):
        raise CapacityDuringArm('capacity interrupted known partial auxiliary arm')
    if state['thread_id']==old['thread_id']:
        return
    binding=dict(watcher=watcher,worker=dict(pid=state['worker_pid'],start=state['worker_start']),
                 server=dict(pid=state['server_pid'],start=state['server_start']),
                 guardian={'not_started':True},monitor={'not_started':True})
    # These two sources have not yet been created or launched in this branch.
    if any((attempt/(name+'-LAUNCH-INTENT.json')).exists() for name in ('guardian','monitor')):
        raise ValueError('auxiliary submission needs reconciliation')
    journal['current_envelope']=dict(thread_id=state['thread_id'],directory=str(attempt),
        model=journal['attempts'][-1]['model'],guardian_dir=str(attempt/'armed-controller'),
        monitor_dir=old['monitor_dir'],binding=binding)
    journal['attempts'][-1]['status']='capacity_before_healthy'
    atomic(HERE/'journal.json',journal)
    raise CapacityDuringArm('typed terminal capacity before healthy auxiliary arm')


def complete_retirement_subject(envelope,state):
    """A later stopped producer must not escape a stale last-healthy birth set."""
    for name in ('worker','server'):
        expected=(state.get(name+'_pid'),state.get(name+'_start'))
        row=envelope['binding'][name]
        if (row['pid'],row['start']) != expected:
            # Producer state is source-bound. A missed canonical watcher recovery
            # is conservatively added to the retirement subject, never ignored.
            actual=birth(expected[0])
            if actual is not None and (actual['start']!=expected[1]
                    or actual['ppid']!=(envelope['binding']['watcher']['pid'] if name=='worker' else state['worker_pid'])):
                raise ValueError('stopped producer ancestry/birth changed')
            if not isinstance(expected[1],str) or not expected[1].isdigit() or int(expected[1])<=0:
                raise ValueError('stopped producer birth unavailable')
            envelope['binding'][name]=dict(pid=expected[0],start=expected[1])


def drain(envelope,reason):
    """Ask only the bound global guardian for a normal drain; never touch native owners."""
    row=envelope['binding']['guardian']
    handed_to_guardian=False
    if row.get('not_started') is not True:
        actual=birth(row['pid'])
        if actual is not None and actual['start']==row['start']:
            handed_to_guardian=True
            path=Path(envelope['guardian_dir'])/'USER-STOP.json'
            if not path.exists():
                create(path,dict(scope=SCOPE,explicit_stop=True,reason=reason,at=time.time()))
    if not handed_to_guardian:
        # A partial envelope may not yet have a guardian. Gracefully stop only
        # its exact known model worker through the reviewed pidfd primitive.
        worker=envelope['binding']['worker']
        actual=birth(worker['pid'])
        if actual is not None and actual['start']==worker['start']:
            intent=HERE/('DRAIN-WORKER-'+str(worker['pid'])+'-'+worker['start']+'.json')
            create(intent,dict(scope=SCOPE,reason=reason,binding=envelope['binding'],
                               signal='SIGTERM',at=time.time(),signal_budget=1))
            spec=importlib.util.spec_from_file_location('capacity_exact_model_drain',HERE/'guardian_template.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.stop_worker(envelope['binding'])
    until=time.monotonic()+60
    while True:
        reap_children()
        state=read(CAMPAIGN/'state.json')
        if state.get('thread_id')==envelope['thread_id']:
            complete_retirement_subject(envelope,state)
        if retired(envelope['binding'],birth):
            return
        if time.monotonic()>=until:
            raise ValueError('bound model envelope still draining; preserve identities, do not restart')
        time.sleep(2)


def launch_envelope(config, packet, journal, state, goal, turns, catalog, model):
    """Called once after positive retirement/live goal proof and durable intent."""
    old = journal['current_envelope']
    raw = (CAMPAIGN/'state.json').read_bytes()
    if json.loads(raw) != state or not live_root_matches(state, goal, turns):
        raise ValueError('capacity subject changed before preparation')
    if (not retired(old['binding'], birth) or not instructions_clear()
            or not all(free_lease(CAMPAIGN/name) for name in ('run.lock', 'watch.lock'))):
        raise ValueError('old model envelope or instruction/lease ownership remains')
    check_packet(HERE/'SOURCE-PACKET.json', journal['source_packet_sha256'])
    account = ledger(journal)
    attempt = HERE/('attempt-%04d' % (len(journal['attempts'])+1))
    attempt.mkdir()
    create(attempt/'STOPPED-CAPACITY-STATE.json', raw)
    create(attempt/'LIVE-CAPACITY-PROOF.json', dict(goal=goal, turns=turns, at=time.time()))
    create(attempt/'RETAINED-CREDIT-LEDGER.json', account)
    create(attempt/'RETAINED-PREDECESSOR.json', old)
    create(attempt/'MODEL-CATALOG.json', catalog)
    bootstrap = attempt/'bootstrap'; bootstrap.mkdir()
    effort=effort_for(catalog,model)
    if effort is None:
        raise ValueError('selected fallback effort is not advertised')
    worker_routing(catalog, model, effort)  # Refuse before generating or launching any envelope.
    note = (SCOPE+'\nCapacity-only automatic alternate-model resume explicitly authorized by the user. '
            'Preserve original fixed '+UTC+' cutoff and all inherited operational clocks; '
            'preserve historical credit ledger '+CREDIT+' and actual past debits; weekly allowance ONLY, no prepaid fallback. '
            'This resumes only the typed terminal serverOverloaded failure retained in this attempt. '
            'Real policy/auth/billing/quota holds and uncertain operations still stop execution.\n'
            'LATEST PHONE PRIORITY: M14 EXCLUSIVELY until M14 is accepted; only then M15. '
            'Reuse accepted prefixes and genuine Rust bodies; implementation/default/link/native/file '
            'results determine progress. Read current AGENTS.md, GOAL.md, START.md, CURRENT.md, '
            'HANDOFF.md and Markdown checkpoints. Preserve all native owners, unknown outcomes, '
            'containers, scratch21 and exclusions. Model retirement is never native cleanup or a '
            'new workload release. Do not replay retained/consumed attempts.\n'
            'This attempt is '+str(attempt)+'. SOURCE/REVIEW ONLY until its own ACTUAL-CONTROLS-ARMED.json '
            'records a healthy actual guardian and sole20minute monitor. The external capacity supervisor '
            'is the sole owner of those global controllers; dispatcher/children must not arm replacements. '
            'Earlier control receipts are historical. Every later heavy/native operation needs its own '
            'fresh admission, live identities and one-shot reviewed release.\n'
            'Dispatcher routing uses '+model+'/'+effort+'; default workers medium, complex/reviewers high, auditors low. '
            'Functional ownership and correctness checks remain required.\n').encode()
    assert len(note) <= 8192
    create(bootstrap/'CURRENT-INVOCATION.txt', note)
    create(bootstrap/'bridge.py', (HERE/'guardian_template.py').read_bytes())
    create(bootstrap/'finite_launcher.py', finite_source())
    create(bootstrap/'weekly_policy.py',(HERE/'weekly_policy.py').read_bytes())
    bc = dict(scope=SCOPE, selected_model=model, selected_effort=effort,
              advertised_models=[r['model'] for r in catalog['models']],
              advertised_efforts={r['model']:r['efforts'] for r in catalog['models']},
              credit_run_id=CREDIT, credit_ceiling=str(CEILING), caps=journal['caps'],
              original_window_path=config['window_path'], original_window_sha256=config['window_sha256'],
              capacity_predecessor=dict(thread_id=state['thread_id'],goal=goal,
                                        failed_turn=state['last_failure']['id'],error=state['last_error']))
    create(bootstrap/'CONFIG.json', bc)
    bsha = packet_for(bootstrap, packet['canonical'],
                       ('bridge.py', 'finite_launcher.py', 'weekly_policy.py', 'CONFIG.json', 'CURRENT-INVOCATION.txt'), model)
    caps = journal['caps']
    argv = ['/usr/bin/taskset', '-c', '0,2-7', PYTHON, '-B', str(bootstrap/'finite_launcher.py'),
            '--deadline-utc', UTC, '--boot-deadline', str(caps['boot_deadline']),
            '--monotonic-deadline', str(caps['monotonic_deadline']), '--packet-sha256', bsha,
            '--publish-initial-clock', '--', '--codex', config['codex'], '--model', model,
            '--effort', effort, '--profile', 'aggressive', '--max-agents', '10', '--build-jobs', '7',
            '--agent-windows', 'off', '--stall-seconds', '1800', '--watchdog-seconds', '180',
            '--quiet', '--grace-seconds', '30', '--fresh-session',
            '--startup-instruction-file', str(bootstrap/'CURRENT-INVOCATION.txt'),
            '--startup-instruction-sha256', digest(note)]
    entry = dict(status='intent', directory=str(attempt), model=model, old_thread=state['thread_id'],
                 failed_turn=state['last_failure']['id'], at=time.time(), started_boot=time.clock_gettime(time.CLOCK_BOOTTIME))
    journal['attempts'].append(entry)
    atomic(HERE/'journal.json', journal)  # Durable before first process mutation.
    if ((CAMPAIGN/'state.json').read_bytes() != raw or stopped_for_user(config, old)
            or remaining(caps, *clocks(), boot_id()) <= 5
            or not retired(old['binding'], birth) or not instructions_clear()
            or not all(free_lease(CAMPAIGN/name) for name in ('run.lock', 'watch.lock'))):
        raise ValueError('capacity launch subject changed after intent; never replay')
    watcher = spawn(argv, attempt, 'watcher')
    entry.update(status='watcher_started', watcher=watcher)
    atomic(HERE/'journal.json', journal)
    return attempt, watcher, bsha, note


def arm_auxiliaries(config, packet, journal, attempt, watcher, bootstrap_sha, note, catalog, model):
    """Only a fresh healthy model chain is bound; every derived packet is immutable."""
    until = time.monotonic()+90
    while True:
        reap_children()
        interrupted_arm(journal,watcher,attempt)
        if remaining(journal['caps'], *clocks(), boot_id()) <= 0:
            raise ValueError('deadline reached while observing new finite model')
        state = read(CAMPAIGN/'state.json')
        if (state.get('phase') == 'running' and (state.get('goal') or {}).get('status') == 'active'
                and state.get('thread_id') != journal['current_envelope']['thread_id']):
            break
        if time.monotonic() >= until or birth(watcher['pid']) is None:
            raise ValueError('new envelope did not become healthy; preserve actual launch, do not duplicate')
        time.sleep(2)
    guardian, monitor = attempt/'armed-controller', attempt/'twenty-minute-steering'
    guardian.mkdir(); monitor.mkdir()
    previous = journal['current_envelope']
    provisional = dict(thread_id=state['thread_id'],directory=str(attempt),model=model, guardian_dir=str(guardian), monitor_dir=str(monitor),
                       previous_monitor_dir=journal['current_envelope'].get('previous_monitor_dir',journal['current_envelope']['monitor_dir']),
                       binding=dict(watcher=watcher, worker=dict(pid=state['worker_pid'],start=state['worker_start']),
                                    server=dict(pid=state['server_pid'],start=state['server_start']),
                                    guardian={'not_started': True}, monitor={'not_started': True}))
    provisional['binding'] = live_binding(provisional, state)
    journal['current_envelope'] = provisional
    atomic(HERE/'journal.json', journal)
    initial = read(attempt/'bootstrap/initial-watch-clock.json')
    if (initial['watcher_pid'], initial['watcher_start'], initial['bootstrap_packet_sha256']) != (watcher['pid'], watcher['start'], bootstrap_sha):
        raise ValueError('actual finite watcher publication differs')
    journal['caps']['boot_deadline'] = min(journal['caps']['boot_deadline'], initial['boot_deadline'])
    journal['caps']['monotonic_deadline'] = min(journal['caps']['monotonic_deadline'], initial['watcher_cutoff_lower'])
    remaining(journal['caps'], *clocks(), boot_id())
    source = (HERE/'guardian_template.py').read_text()
    lines = [line for line in source.splitlines() if line.startswith('THREAD = ')]
    assert len(lines) == 1
    source = source.replace(lines[0], 'THREAD = '+repr(state['thread_id']))
    create(guardian/'bridge.py', source.encode())
    create(guardian/'finite_launcher.py', finite_source())
    create(guardian/'weekly_policy.py',(HERE/'weekly_policy.py').read_bytes())
    create(guardian/'CURRENT-INVOCATION.txt', note)
    window = read(config['window_path'])
    gc = dict(scope=SCOPE, status='ACTUAL_CAPACITY_FALLBACK_GUARDIAN', deadline_utc=UTC,
              expected_thread=state['thread_id'], credit_run_id=CREDIT, credit_ceiling=str(CEILING),
              initial_credit_budget=None, selected_model=model,selected_effort=effort_for(catalog,model),
              advertised_models=[r['model'] for r in catalog['models']], included_first=True,
              advertised_efforts={r['model']:r['efforts'] for r in catalog['models']},
              automatic_credit_purchase=False, api_key_billing=False, billing_mode='included_only',allow_prepaid_fallback=False,window2_initial=True,
              initial_watch_clock=initial, bootstrap_packet_sha256=bootstrap_sha,
              operational_monotonic_deadline=journal['caps']['monotonic_deadline'],
              window=window, window_sha256=config['window_sha256'], max_agents=10, build_jobs=7,
              stall_seconds=1800, watchdog_seconds=180)
    create(guardian/'CONFIG.json', gc)
    gsha = packet_for(guardian, packet['canonical'],
                     ('bridge.py', 'finite_launcher.py', 'weekly_policy.py', 'CONFIG.json', 'CURRENT-INVOCATION.txt'), model)
    # No process submission if the new root has already hit typed capacity again.
    fresh=read(CAMPAIGN/'state.json')
    if root_capacity(fresh) and fresh.get('thread_id')==provisional['thread_id']:
        raise CapacityDuringArm('capacity before guardian launch')
    provisional['binding']['guardian'] = spawn(['/usr/bin/taskset', '-c', '0', PYTHON, '-B',
                                               str(guardian/'bridge.py'), '--run', '--packet-sha256', gsha], attempt, 'guardian')
    atomic(HERE/'journal.json', journal)
    until = time.monotonic()+15
    while not (guardian/'journal.json').exists():
        fresh=read(CAMPAIGN/'state.json')
        if root_capacity(fresh) and fresh.get('thread_id')==provisional['thread_id']:
            raise CapacityDuringArm('capacity while guardian first-arm was pending')
        if time.monotonic() >= until:
            raise ValueError('guardian arm did not publish; preserve partial envelope')
        time.sleep(1)
    gj = read(guardian/'journal.json')
    if gj.get('packet_sha256') != gsha or gj.get('transition_hold') or gj.get('boot_deadline', float('inf')) > journal['caps']['boot_deadline']:
        raise ValueError('new guardian identity/cutoff differs')
    old_path = Path(previous.get('previous_monitor_dir',previous['monitor_dir']))
    old_journal = read(old_path/'journal.json')
    if old_journal.get('status') in {'intent', 'uncertain'}:
        raise ValueError('predecessor monitor queue delivery is uncertain')
    create(monitor/'PREDECESSOR-JOURNAL.json', old_journal)
    for name in ('snapshot.json', 'snapshot.previous.json'):
        if (old_path/name).exists():
            create(monitor/name, (old_path/name).read_bytes())
    source = (HERE/'steering_template.py').read_text()
    lines = [line for line in source.splitlines() if line.startswith('GUARDIAN_JOURNAL = ')]
    assert len(lines) == 1
    source = source.replace(lines[0], 'GUARDIAN_JOURNAL = Path('+repr(str(guardian/'journal.json'))+')')
    create(monitor/'steer_every_twenty_minutes.py', source.encode())
    arm = dict(status='FINALIZED_FOR_EXPLICIT_ARM',scope=SCOPE,thread_id=state['thread_id'],
               campaign=str(CAMPAIGN),deadline=DEADLINE,deadline_utc=UTC,guardian_journal=str(guardian/'journal.json'),
               guardian_packet_sha256=gsha,boot_id=boot_id(),focus_path=str(guardian/'CURRENT-INVOCATION.txt'),
               launcher_sha256=packet['canonical']['run_os_goal.py'],
               recovery_source_sha256={k:packet['canonical'][k] for k in ('watch_os_goal.py','os_goal_transport.py')},
               review_interval_seconds=1200,window_path=config['window_path'],window_sha256=config['window_sha256'])
    asha = create(monitor/'ARM-BINDING.json',arm)
    seed = {key:old_journal[key] for key in ('baseline_at','queued_at','instruction_id','marker') if key in old_journal}
    seed.update(status='queued',thread_id=state['thread_id'],arm_binding_sha256=asha,
                guardian_packet_sha256=gsha,boot_id=boot_id(),deadline=DEADLINE,
                boot_deadline=min(journal['caps']['boot_deadline'],gj['boot_deadline'],old_journal['boot_deadline']),
                capacity_restart_provenance=dict(predecessor_thread=previous['thread_id'],
                    predecessor_journal_sha256=digest((old_path/'journal.json').read_bytes()),
                    old_status=old_journal.get('status'),old_reason=old_journal.get('reason'),
                    queued_at_is_historical=True,catchup='ONE_OVERDUE_REVIEW_THEN1200S'))
    create(monitor/'journal.json',seed)
    argv=['/usr/bin/taskset','-c','0',PYTHON,'-B',str(monitor/'steer_every_twenty_minutes.py'),
          '--binding',str(monitor/'ARM-BINDING.json'),'--binding-sha256',asha]
    fresh=read(CAMPAIGN/'state.json')
    if root_capacity(fresh) and fresh.get('thread_id')==provisional['thread_id']:
        raise CapacityDuringArm('capacity before monitor arm')
    result=subprocess.run(argv+['--check-binding'],cwd=REPO,stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    create(monitor/'READONLY-ARM-CHECK.json',dict(returncode=result.returncode,
                                               stdout=result.stdout.decode()[:8192],stderr=result.stderr.decode()[:8192]))
    if result.returncode:
        raise ValueError('new monitor read-only binding rejected; preserve partial envelope')
    provisional['binding']['monitor']=spawn(argv+['--run'],attempt,'monitor')
    atomic(HERE/'journal.json',journal)
    until=time.monotonic()+20
    while True:
        reap_children()
        fresh=read(CAMPAIGN/'state.json')
        if root_capacity(fresh) and fresh.get('thread_id')==provisional['thread_id']:
            raise CapacityDuringArm('capacity before final controller health readback')
        live_binding(provisional,fresh)
        gj=read(guardian/'journal.json')
        published=monitor/'supervisor.json'
        valid=False
        if published.exists() and (monitor/'journal.json').exists():
            ms=read(published);mj=read(monitor/'journal.json');mr=provisional['binding']['monitor']
            valid=(fresh.get('phase')=='running' and (fresh.get('goal') or {}).get('status')=='active'
                   and not fresh.get('stop_reason') and no_holds(fresh)
                   and ms.get('pid')==mr['pid'] and ms.get('start_ticks')==mr['start']
                   and ms.get('thread_id')==state['thread_id'] and ms.get('arm_binding_sha256')==asha
                   and ms.get('guardian_packet_sha256')==gsha and mj.get('arm_binding_sha256')==asha
                   and mj.get('status')=='queued'
                   and not free_lease(monitor/'supervisor.lock')
                   and not free_lease(guardian/'bridge.lock')
                   and gj.get('packet_sha256')==gsha and not gj.get('transition_hold')
                   and not str(gj.get('last_action','')).startswith(('STOP_','HOLD_')))
        if valid:
            break
        if time.monotonic()>=until:
            raise ValueError('actual guardian/monitor health and exclusive leases not confirmed')
        time.sleep(1)
    provisional.update(guardian_packet_sha256=gsha,monitor_arm_sha256=asha,model=model)
    provisional.pop('previous_monitor_dir',None)
    create(attempt/'ACTUAL-CONTROLS-ARMED.json',dict(scope=SCOPE,thread_id=state['thread_id'],
        binding=provisional['binding'],guardian_packet_sha256=gsha,monitor_arm_sha256=asha,
        caps=journal['caps'],deadline_utc=UTC,at=time.time(),native_release=False))
    journal['attempts'][-1].update(status='healthy_envelope',thread_id=state['thread_id'])
    atomic(HERE/'journal.json',journal)


def superseded_child(row,goal,turns,root):
    return (isinstance(goal,dict) and goal.get('status')=='active'
            and goal.get('threadId',root)==root and isinstance(turns,list) and bool(turns)
            and isinstance(turns[0],dict) and isinstance(turns[0].get('id'),str)
            and bool(turns[0]['id']) and turns[0]['id']!=row.get('turn_id'))


def queue_child(config, packet, journal, state, row, model):
    key=row['thread_id']+'/'+row['turn_id']
    if key in journal['child_requests']:
        return
    entry=dict(status='intent',thread_id=row['thread_id'],turn_id=row['turn_id'],root=state['thread_id'],model=model)
    journal['child_requests'][key]=entry
    atomic(HERE/'journal.json',journal)
    check_packet(HERE/'SOURCE-PACKET.json',journal['source_packet_sha256'])
    fresh=read(CAMPAIGN/'state.json')
    if (not no_holds(fresh) or fresh.get('phase')!='running' or fresh.get('thread_id')!=state['thread_id']
            or (fresh.get('goal') or {}).get('status')!='active' or fresh.get('stop_reason')
            or fresh.get('last_error') is not None or fresh.get('last_failure') is not None
            or fresh.get('worker_pid')!=state.get('worker_pid') or fresh.get('server_pid')!=state.get('server_pid')
            or remaining(journal['caps'],*clocks(),boot_id())<=0 or not instructions_clear()):
        raise ValueError('child-capacity queue subject changed after intent; no replay')
    sys.path.insert(0,str(REPO/'scripts'))
    import run_os_goal
    text=(SCOPE+'\nONLY active root '+state['thread_id']+'. Typed terminal child capacity failure '
          +key+' was freshly confirmed after its backoff. First verify its actual failed model from '
          'your assignment/thread metadata. Replace it with a DIFFERENT advertised model: candidate '
          +model+'; if that was already its failed model, choose another from '
          'gpt-6.1-sol, gpt-6-astra, gpt-6.1-terra, gpt-6-sol, gpt-6-luna as advertised. '
          'Worker effort remains medium by default, high for complex/reviewer work, low for auditors; require it advertised. '
          'using fork_turns=none and a private Markdown handoff. Preserve its completed work and actual '
          'native/operation ownership. Retire its shared-file assignment before a replacement writes it; '
          'never create competing writers. Do not restart in-progress/retrying children. M14 EXCLUSIVE '
          'until accepted, then M15. This is a capacity-only replacement instruction; it grants no '
          'workload, cleanup, policy/hold clearance, credit reset or deadline extension.')
    try:
        ident=run_os_goal.queue_instruction(CAMPAIGN,text)
    except Exception:
        entry['status']='uncertain';atomic(HERE/'journal.json',journal);raise
    entry.update(status='queued',instruction_id=ident,queued_at=time.time())
    atomic(HERE/'journal.json',journal)


def run(packet_sha):
    packet,config=check_packet(HERE/'SOURCE-PACKET.json',packet_sha)
    with (HERE/'supervisor.lock').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        jp=HERE/'journal.json'
        journal=read(jp) if jp.exists() else dict(status='armed',source_packet_sha256=packet_sha,
            caps=config['caps'],current_envelope=config['initial_envelope'],attempts=[],child_requests={},
            failures={},credit_spent_floor=config['credit_spent_floor'])
        if journal['source_packet_sha256']!=packet_sha or journal['caps']['boot_id']!=boot_id():
            raise ValueError('retained supervisor source/boot binding differs')
        if any(submission_action(row).startswith('HOLD') for row in
               journal['attempts']+list(journal['child_requests'].values())):
            raise ValueError('uncertain launch/queue intent requires explicit reconciliation')
        atomic(HERE/'supervisor.json',dict(pid=os.getpid(),birth=birth(os.getpid()),scope=SCOPE,
                                          source_packet_sha256=packet_sha,at=time.time()))
        ledger(journal);atomic(jp,journal)
        catalog=read(HERE/'MODEL-CATALOG.json')
        while True:
            reap_children()
            journal['caps']=tighten(journal['caps'],*clocks())
            envelope=journal['current_envelope']
            if remaining(journal['caps'],*clocks(),boot_id())<=0 or stopped_for_user(config,envelope):
                drain(envelope,'capacity_supervisor_deadline_or_user_stop')
                journal['status']='stopped_deadline_or_user';atomic(jp,journal);return
            state=read(CAMPAIGN/'state.json')
            if state.get('thread_id')!=envelope['thread_id']:
                raise ValueError('unattributed root thread change; do not adopt or relaunch')
            latch_weekly_end(journal,state)
            if remaining(journal['caps'],*clocks(),boot_id())<=0:
                drain(envelope,'confirmed_earlier_weekly_ceiling')
                journal['status']='stopped_earlier_weekly_ceiling';atomic(jp,journal);return
            if state.get('phase')=='running' and (state.get('goal') or {}).get('status')=='active':
                envelope['binding']=live_binding(envelope,state)
                for row in state.get('child_capacity_failures',[])[:16]:
                    if not terminal_child_hint(row):
                        continue
                    key=str(row.get('thread_id'))+'/'+str(row.get('turn_id'))
                    if key in journal['child_requests'] or time.time()<row.get('retry_not_before_unix',float('inf')):
                        continue
                    goal,turns=metadata(config,state['thread_id'],row.get('thread_id'))
                    if superseded_child(row,goal,turns,state['thread_id']):
                        journal['child_requests'][key]=dict(status='superseded',root=state['thread_id'],
                            hinted_thread=row['thread_id'],hinted_turn=row['turn_id'],
                            authoritative_latest_turn=turns[0]['id'],observed_at=time.time(),
                            reason='fresh_latest_turn_differs_from_historical_capacity_hint')
                        atomic(jp,journal)
                        continue
                    if child_capacity(state,row,goal,turns,time.time()):
                        model=choose_model(catalog,envelope.get('model',config['initial_model']),journal['failures'],time.clock_gettime(time.CLOCK_BOOTTIME))
                        if model and instructions_clear():
                            ledger(journal);queue_child(config,packet,journal,state,row,model)
                            break
            elif state.get('phase')=='stopped':
                if not root_capacity(state):
                    journal['status']='stopped_non_capacity';atomic(jp,journal);return
                complete_retirement_subject(envelope,state)
                if not retired(envelope['binding'],birth):
                    time.sleep(5);continue
                if not instructions_clear() or not all(free_lease(CAMPAIGN/n) for n in ('run.lock','watch.lock')):
                    raise ValueError('capacity stop retains instructions or core leases')
                goal,turns=metadata(config,state['thread_id'])
                if not live_root_matches(state,goal,turns):
                    raise ValueError('live goal/latest turn does not match exact typed capacity failure')
                model_now=envelope.get('model',config['initial_model'])
                failure_key=state['thread_id']+'/'+state['last_failure']['id']
                if journal.get('failure_key')!=failure_key:
                    journal['failure_key']=failure_key
                    journal['failures'][model_now]=time.clock_gettime(time.CLOCK_BOOTTIME)
                    journal['retry_after_boot']=time.clock_gettime(time.CLOCK_BOOTTIME)+min(300,5*2**min(len(journal['attempts']),6))
                    atomic(jp,journal)
                if time.clock_gettime(time.CLOCK_BOOTTIME)<journal['retry_after_boot']:
                    time.sleep(5);continue
                model=choose_model(catalog,model_now,journal['failures'],time.clock_gettime(time.CLOCK_BOOTTIME))
                if model is None:
                    # Refresh at most once each minute, using the bounded read-only probe.
                    if time.clock_gettime(time.CLOCK_BOOTTIME)>=journal.get('catalog_refresh_after_boot',0):
                        from catalog_probe import probe
                        path=HERE/('MODEL-CATALOG-REFRESH-'+str(int(time.time()))+'.json')
                        catalog=probe(path)
                        journal['catalog_refresh_after_boot']=time.clock_gettime(time.CLOCK_BOOTTIME)+60
                    atomic(jp,journal);time.sleep(5);continue
                attempt,watcher,bsha,note=launch_envelope(config,packet,journal,state,goal,turns,catalog,model)
                try:
                    arm_auxiliaries(config,packet,journal,attempt,watcher,bsha,note,catalog,model)
                except CapacityDuringArm:
                    journal['attempts'][-1]['status']='capacity_interrupted_arm'
                    atomic(jp,journal)
            else:
                if not no_holds(state):
                    journal['status']='stopped_real_hold';atomic(jp,journal);return
            atomic(jp,journal)
            time.sleep(5)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--run',action='store_true')
    parser.add_argument('--packet-sha256',required=True)
    args=parser.parse_args()
    if os.getuid()!=1000 or os.geteuid()!=1000:
        raise ValueError('ordinary user1000 required')
    if args.check:
        packet,config=check_packet(HERE/'SOURCE-PACKET.json',args.packet_sha256)
        print(json.dumps(dict(status='PASS_SOURCE_ONLY_NO_RUNTIME_ARM',scope=SCOPE,
                             deadline=DEADLINE,credit_run_id=CREDIT,credit_ceiling=str(CEILING))))
        return
    if (HERE/'HOLD.json').exists():
        raise ValueError('retained capacity-supervisor hold needs explicit reconciliation; preserve it')
    try:
        run(args.packet_sha256)
    except Exception as error:
        # Preserve exact prior phase/intent. Do not turn an exception into a retry.
        atomic(HERE/'HOLD.json',dict(scope=SCOPE,error_type=type(error).__name__,
                                    message=str(error)[:2048],at=time.time(),automatic_retry=False))
        # A known partial fallback envelope must not keep developing after its
        # controller arm failed. Original/native actors are never cleaned up.
        jp=HERE/'journal.json'
        if jp.exists():
            journal=read(jp);envelope=journal.get('current_envelope') or {}
            if str(envelope.get('directory','')).startswith(str(HERE/'attempt-')):
                try:
                    drain(envelope,'capacity_fallback_partial_controller_hold')
                except Exception as drain_error:
                    atomic(HERE/'DRAIN-HOLD.json',dict(error_type=type(drain_error).__name__,
                                                     message=str(drain_error)[:2048],at=time.time()))
        raise


if __name__=='__main__':
    main()
