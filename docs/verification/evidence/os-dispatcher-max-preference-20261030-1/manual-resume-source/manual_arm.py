"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicit manual same-thread arm; the capacity fallback keeps its distinct rule.
Retains actor pinning and heartbeat; carries the current monitor cursor exactly.
"""
from capacity_supervisor import *
from readiness import fresh_heartbeat


def manual_ready(previous, stopped, state, watcher, observed):
    root = stopped.get('thread_id')
    if not root or previous.get('thread_id') != root or state.get('thread_id') != root:
        raise ValueError('manual same-Root equality required')
    if state.get('phase') != 'running' or (state.get('goal') or {}).get('status') != 'active' or not no_holds(state):
        raise ValueError('manual Root is not healthy and active')
    if state.get('stop_reason'):
        raise ValueError('manual Root has a new stop')
    if ((state.get('settings') or {}).get('billing') or {}).get('mode') != 'included_only':
        raise ValueError('manual Root must remain included-only')
    effective = state.get('effective_permissions') or {}
    if effective.get('sandbox', {}).get('type') != 'dangerFullAccess' or effective.get('approval_policy') != 'never':
        raise ValueError('manual Root permissions differ')
    for role in ('watcher', 'worker', 'server'):
        row, old = observed[role], previous['binding'][role]
        if row is None or row.get('state') in ('Z', 'X'):
            raise ValueError('manual actor is not live: ' + role)
        if (row['pid'], row['start']) == (old['pid'], old['start']):
            raise ValueError('manual actor identity was not replaced: ' + role)
    if (observed['watcher']['pid'], observed['watcher']['start']) != (watcher['pid'], watcher['start']):
        raise ValueError('manual submitted watcher differs')
    for role in ('worker', 'server'):
        row = observed[role]
        if (row['pid'], row['start']) != (state.get(role + '_pid'), state.get(role + '_start')):
            raise ValueError('manual saved actor binding differs: ' + role)
    if observed['worker']['ppid'] != watcher['pid'] or observed['server']['ppid'] != observed['worker']['pid']:
        raise ValueError('manual live ancestry differs')
    return True


def arm_manual_same_thread(config, packet, journal, attempt, watcher, bootstrap_sha, note, catalog, model):
    state = read(CAMPAIGN / 'state.json')
    stopped = read(attempt / 'STOPPED-STATE.json')
    observed = dict(watcher=birth(watcher['pid']), worker=birth(state['worker_pid']), server=birth(state['server_pid']))
    manual_ready(journal['current_envelope'], stopped, state, watcher, observed)
    if not fresh_heartbeat(state, journal['attempts'][0]['at'], time.time(),
                           {key: state.get(key) for key in ('worker_pid','worker_start','server_pid','server_start')}):
        raise ValueError('manual guardian requires a fresh current-invocation heartbeat')
    if remaining(journal['caps'], *clocks(), boot_id()) <= 0:
        raise ValueError('manual weekly ceiling reached')
    guardian, monitor = attempt/'armed-controller', attempt/'twenty-minute-steering'
    guardian.mkdir(); monitor.mkdir()
    previous = journal['current_envelope']
    provisional = dict(thread_id=state['thread_id'],directory=str(attempt),model=model, guardian_dir=str(guardian), monitor_dir=str(monitor),
                       previous_monitor_dir=journal['current_envelope']['monitor_dir'],
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
              initial_credit_budget=None, selected_model=model,selected_effort=state['settings']['effort'],
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
    old_path = Path(previous['monitor_dir'])
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

