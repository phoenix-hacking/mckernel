"""Functional McKernel OS/apps and Rust migration only; no security testing.
Private source successor of strict native resource capture. No execution grant.
Retains original resource predicates and adds exact Root39/CURRENT113 plus complete Root38/V3 historical controls. Sourcecheckpoint only; Root must rebind after any later operation.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess

A = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
GUARD = E/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'
GUARD_SHA = '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
OBSERVER = E/'daemon-final-ring-suffix-source-1/new12h-operation-preparation-1/resource-observer-window-correction-source-1/check_postnative_current_new12h.py'
OBSERVER_SHA = '2b7362126fbe70475a208e40df9eb56fa12df0993d83d0aa9b9a22a36638481c'
LEDGER = E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER43.json'
LEDGER_SHA = '41ade09947062d4f7cd4136d32d466c502e096c166519b1dba2aaa0d5a53b7f4'
FREE = E/'ROOT-CURRENT113-ABI-PRIVATE-CORRECTION-BUILD-ADMISSION-1/independent-postbuild-current-free-review-1/CURRENT-FREE.json'
FREE_SHA = '13ed764e3ba6fd28861336eacbce7effffc29e879210122ea0e92a2bbb0f952d'
INHERITED111 = E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/INDEPENDENT-POSTBUILD-CURRENT-FREE.json'
INHERITED_NATIVE = E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def checked(reference):
    path = Path(reference['path'])
    assert ref(path) == reference
    return json.loads(path.read_bytes())


ROOT40_FREE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 7877, 'sha256': 'd4ca62159bacb2aa20cbdd34760b455dcadfcafa1c0727ccbb06dfc632824706'}
ROOT40_EXACT = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/FRESH-EXACT-CONTAINER-AND-ACTORS.json', 'bytes': 2948, 'sha256': 'c0e0c3d499b28a442991f077a4f120b557e20f0097f28b17b989b87a4876f0d3'}
ROOT40_RESULT = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/RAW-OWNER/result.json', 'bytes': 257, 'sha256': 'b7eb4a46fb0a65fcc0b47394ec7fdceedaa34678be8a58f67a047d74adea3033'}
ROOT40_STATE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/RAW-OWNER/state.json', 'bytes': 224, 'sha256': '8f64521284e61c6b90c0e54574778624ad158e9b6c8fd520de85e33915c62d66'}
ROOT40_OWNER = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/RAW-OWNER/owner.json', 'bytes': 790, 'sha256': '4f45c36ce19b224474d2b5c591a2cd2b95088fd4779f666a3e35d045814c06fe'}
ROOT40_CAPTURE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/CAPTURE/JOINED.json', 'bytes': 224, 'sha256': '9af96b5b8c96f68be196b8c297fa589f731889c3e9443fbebd5f15195f452f86'}
ROOT40_BRIDGE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/ROOT-ONCE-ENTRY.JOINED.json', 'bytes': 1505, 'sha256': '1b575757e72bc08f51fc00212df9bb497732f313bd17cd24e84bc25a3aa63bc8'}
ROOT40_ACTORS = [1746777, 1746883, 1746887, 1746889, 1746895, 1746901, 1746907, 1746913, 1746919, 1746925, 1746931, 1746937, 1747065, 1747071, 1747077, 1747083, 1747090, 1747096, 1747102, 1747108, 1747114, 1747120, 1747126, 1747132, 1747138, 1747144, 1747150, 1747156, 1747162, 1747168, 1747174, 1747180, 1747186]

def validate_root40_latest(review):
    assert review['decision'] == 'PASS_CURRENT_FREE' and review['independent'] is True and review['implementation_ownership'] is False
    boundary = review['current_boundary']
    assert review['nonce'] == 'cdc739fc1e365619d5be1b9745ecc291' and review['nonce_consumed_once'] is True
    assert boundary['owner_pid'] == 1746887 and boundary['owner_starttime'] == 94092314 and boundary['capture_caller_pid'] == 1746883 and boundary['bridge_pid'] == 1746777
    assert boundary['actual_docker_clients'] == 30 and boundary['all_actual_client_positive_reaps'] is True and boundary['all33_actor_pid_and_pgrp_absent'] is True
    assert boundary['exact_cid_name_label_absent'] is True and boundary['no_running_containers_observed'] is True and boundary['native_cgroup_pids_current'] == 0
    assert boundary['lease_retained'] is False and boundary['owner_absence_verified'] is True and boundary['normal_rm_returncode'] == 0
    assert boundary['qemu_positive_reap'] == dict(pid_in_container=11,returncode=-9,cleanup_reaped=True,errors=[])
    assert len(boundary['permanent27_4_mutex_closed_exclusive_probes']) == 2
    exact=checked(ROOT40_EXACT);result=checked(ROOT40_RESULT);state=checked(ROOT40_STATE);owner=checked(ROOT40_OWNER);capture=checked(ROOT40_CAPTURE);bridge=checked(ROOT40_BRIDGE)
    assert exact['owned_clients'] == 30 and exact['all_reaped'] is True and exact['all_owned_pid_and_pgrp_absent'] == ROOT40_ACTORS and exact['pids_current'] == 0
    assert exact['container'] == result['container'] == boundary['container'] == 'd709acb5c5b508f6c69f0431f08ec232c2214767868eaa340612323b98c44112'
    assert result['status'] == 'PROTOCOL_PASS' and result['absence_verified'] is True and result['lease_retained'] is False and result['secondary'] == []
    assert state['Running'] is False and state['Pid'] == 0 and state['ExitCode'] == 0 and state['OOMKilled'] is False
    assert owner['outer'] == dict(pid=1746887,pgid=1746777,proc_starttime=94092314,sid=1746777)
    assert capture['joined'] is True and capture['returncode'] == 0 and capture['caller_pid'] == 1746883
    assert bridge['direct_child_joined'] is True and bridge['streams_closed'] is True and bridge['returncode'] == 0 and bridge['evidence_error'] is None and bridge['native_helper_pid'] == 1746883
    assert len(exact['queries']) == 5
    return exact


ROOT42_FREE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1/independent-postbuild-current-free-review-1/CURRENT-FREE.json', 'bytes': 104872, 'sha256': '221349f9f93973b57c7d6b4a69d79d9f8e6dd2dcd368d16a08fcfac88c054d0d'}
ROOT41_OBSERVER = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next114-debug32-perf3-coherent-source-1/root41-admission-source-1/observe_root41_current.py', 'bytes': 5061, 'sha256': 'a4cb07216e258a0fddc66c631a729067c4bb5c73620dac846ed5cb54f94d8b08'}

def validate_root42_latest(review):
    assert review['decision']=='PASS_POSITIVE_CURRENT114_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX'
    assert review['independent'] is True and review['implementation_ownership'] is False and review['current_free'] is True and review['normal_owned_retirement'] is True
    assert review['holder']=={'path':'/run/lock/mckernel-development.lock','pid':1763445,'starttime':94341647,'device':27,'inode':4,'fd':3}
    assert review['runner']=={'pid':1763997,'starttime':94348302,'returncode':0,'joined':True}
    assert review['retained_stopped_container']=='d521e2f29e9df27a258f83f22f45f7e959e4cc35be4227b6f742ece9a15ce7ca'
    assert checked(review['runner_join'])==review['runner']
    local=checked(review['local_terminal']);assert local['joined'] is True and local['returncode']==0 and local['holder']==review['holder']
    tool=checked(review['holder_tool_result']);assert tool['positive_tool_completion'] is True and tool['observed_terminal']['exit_code']==0
    terminal=review['container_terminal'];assert terminal['container']==review['retained_stopped_container'] and terminal['returncode']==0 and terminal['state']['Running'] is False and terminal['state']['Pid']==0 and terminal['state']['ExitCode']==0 and terminal['state']['OOMKilled'] is False
    assert review['positive_termination']['actual4_command_returncodes']==[0,0,0,0] and review['positive_termination']['runner_positive_wait'] is True and review['positive_termination']['holder_tool_positive_terminal'] is True
    assert review['fresh_current']['new_groups_absent'] is True and not review['fresh_current']['proc_census_errors'] and review['fresh_current']['startup25clients_reaped'] is True
    assert len(review['fresh_current']['startup28actors_absent'])==28
    return terminal

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--output-path',required=True,type=Path)
    args = parser.parse_args()
    output = args.output_path
    assert output.is_absolute() and output.parent == A
    stdout = output.with_name(output.stem+'.PHYSICAL.stdout')
    stderr = output.with_name(output.stem+'.PHYSICAL.stderr')
    # Original output-collision failure is retained; exclusive preflight precedes
    # actual guard/clock/observer/Docker work. Never overwrite an expired attempt.
    for path in [output,stdout,stderr]:
        assert not os.path.lexists(path), str(path)
    with output.open('xb') as result_stream, stdout.open('xb') as out_stream, stderr.open('xb') as err_stream:
        assert os.getuid() == os.geteuid() == 1000
        assert ref(LEDGER)['sha256'] == LEDGER_SHA and ref(FREE)['sha256'] == FREE_SHA
        ledger = json.loads(LEDGER.read_bytes())
        free = json.loads(FREE.read_bytes())
        assert ledger['author'] == '/root' and ledger['complete_within_declared_current_boundary'] is True
        assert ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
        assert len(ledger['consumed_nonces']) == len(set(ledger['consumed_nonces'])) == 45
        latest40 = checked({'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 7877, 'sha256': 'd4ca62159bacb2aa20cbdd34760b455dcadfcafa1c0727ccbb06dfc632824706'})
        assert ledger['latest_accepted_free_boundary'] == {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 7877, 'sha256': 'd4ca62159bacb2aa20cbdd34760b455dcadfcafa1c0727ccbb06dfc632824706'}
        root39 = checked({'bytes': 5158, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER39.json', 'sha256': 'eacc369bb4d3691000ea8adb1e736e6f9c734d251ca06151fb41ffc2ec9ef56e'})
        latest40_controls = validate_root40_latest(latest40)
        latest42 = checked(ROOT42_FREE); latest42_terminal = validate_root42_latest(latest42)
        assert free['decision'] == 'PASS_POSITIVE_CURRENT113_CORRECTED_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX'
        assert free['independent'] is True and free['implementation_ownership'] is False
        assert free['nonce'] == root39['consumed_nonces'][-1] and free['nonce_consumed'] is True
        assert free['holder']['pid'] == 1740038 and free['holder']['starttime'] == 93979211 and free['holder']['device'] == 27 and free['holder']['inode'] == 4
        assert free['runner'] == dict(pid=1740211,starttime=93985841,returncode=0,joined=True)
        assert free['retained_stopped_container'] == 'bd5d81e6d79b527932bbe45ce139e7b358b546c701d63e8677c7035441e61f97'
        stored_current = checked(free['current_observation'])
        assert not stored_current['observer_result']['group_membership_observation']['errors'] and len(stored_current['observer_result']['closed_exclusive_probes']) == 2
        assert stored_current['permanent_mutex_currently_free'] is True and stored_current['pids_current'] == 0
        assert stored_current['new_actors_absent'] == [dict(pid=1740038,starttime=93979211,role='holder'),dict(pid=1740211,starttime=93985841,role='runner')]
        assert checked(free['runner_join']) == free['runner']
        local_terminal = checked(free['local_terminal'])
        assert local_terminal['joined'] is True and local_terminal['returncode'] == 0 and local_terminal['holder'] == free['holder']
        tool_join = checked(free['holder_tool_result'])
        assert tool_join['tool_terminal_observed'] is True and tool_join['terminal_exit_code'] == 0
        assert tool_join['holder'] == free['holder'] and tool_join['runner'] == free['runner']
        terminal = checked(free['container_terminal'])
        assert terminal['container'] == free['retained_stopped_container'] and terminal['returncode'] == 0
        assert terminal['state']['Running'] is False and terminal['state']['Pid'] == 0 and terminal['state']['ExitCode'] == 0
        assert ref(INHERITED111)['sha256'] == '9904aa3c39b0a83d8675a77b97631f3731f2f3e568c5fde65b6ef91c28f64d19'
        inherited111 = json.loads(INHERITED111.read_bytes())
        inherited_terminal = checked(inherited111['container_terminal'])
        assert inherited_terminal['container'] == inherited111['retained_stopped_container'] and inherited_terminal['state']['Running'] is False and inherited_terminal['state']['Pid'] == 0 and inherited_terminal['state']['ExitCode'] == 0
        assert ref(INHERITED_NATIVE)['sha256'] == 'bf19e5a464ce05f49657acce7e598ce1125d8bf913c85631d5883190290e4890'
        inherited_native = json.loads(INHERITED_NATIVE.read_bytes())
        assert inherited_native['decision'] == 'PASS_POSITIVE_ROOT4_NATIVE_OWNER_RETIREMENT_AND_CURRENT_FREE'
        assert inherited_native['independent'] is True and inherited_native['implementation_ownership'] is False
        assert inherited_native['normal_owned_retirement'] is True and inherited_native['current_free'] is True
        assert inherited_native['owned_client_retirement']['all_exact_reaped'] is True
        assert inherited_native['actual_statuses']['owner_protocol_result']['absence_verified'] is True and inherited_native['actual_statuses']['owner_protocol_result']['lease_retained'] is False
        static = json.loads((A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
        assert static['root_ledger35'] == ref(LEDGER) and static['latest_serial_operation_physical_acceptance'] == {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 7877, 'sha256': 'd4ca62159bacb2aa20cbdd34760b455dcadfcafa1c0727ccbb06dfc632824706'}
        assert static['expected_case'] == 'startup.argv-empty'
        assert static['nonce'] not in ledger['consumed_nonces'] + ledger['reserved_abandoned_unconsumed_nonces']
        for source in static['capture_sources'].values():
            assert ref(Path(source['path'])) == source
        assert ref(GUARD)['sha256'] == GUARD_SHA and ref(OBSERVER)['sha256'] == OBSERVER_SHA
        spec = importlib.util.spec_from_file_location('f05v2_resource_actual_new12h_guard',GUARD)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        assert guard.__file__ == str(GUARD) and guard.__spec__.origin == str(GUARD)
        clocks = guard.guard()
        cutoffs = guard.current_cutoffs()
        observed = subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(OBSERVER)],capture_output=True,timeout=40)
        out_stream.write(observed.stdout)
        err_stream.write(observed.stderr)
        assert observed.returncode == 0 and not observed.stderr
        current = json.loads(observed.stdout)
        # This is the historical-baseline observer, not new F05 postjoin proof.
        # Its exact old native actors, two closed mutex probes, scratch21/UUID,
        # capacity and Docker checks are preserved literally by source binding.
        assert len(current['closed_exclusive_probes']) == 2
        census = current['group_membership_observation']
        assert not census['errors']
        actors = [free['holder'],free['runner'],inherited111['holder'],inherited111['runner']] + [dict(pid=pid) for pid in inherited_native['fresh_current']['all_owned_pids_and_groups_absent']]
        for actor in actors:
            assert not Path('/proc',str(actor['pid'])).exists()
            assert not any(row['pid'] == actor['pid'] or row['pgrp'] == actor['pid'] for row in census['rows'])
        prefix = ['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
        queries = [prefix+['ps','-q','--no-trunc'],prefix+['inspect',free['retained_stopped_container']],prefix+['inspect',inherited111['retained_stopped_container']],prefix+['ps','-aq','--no-trunc','--filter','id='+inherited_native['container']]]
        docker = []
        for argv in queries:
            result = subprocess.run(argv,capture_output=True,text=True,timeout=15)
            assert result.returncode == 0 and not result.stderr
            if 'inspect' in argv:
                data = json.loads(result.stdout)
                assert len(data) == 1 and data[0]['Id'] == argv[-1]
                assert data[0]['State']['Running'] is False and data[0]['State']['Pid'] == 0 and data[0]['State']['ExitCode'] == 0
            else:
                assert not result.stdout.strip()
            docker.append(dict(argv=argv,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,positive_wait=True))
        # Exact reviewed Root38 observer preserves all58 prior controls/V3/failed113.
        # This addition does not replace the original historical baseline observer.
        root38_observer = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root38-correction-admission-source-1/observe_root38_current.py')
        assert ref(root38_observer) == {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root38-correction-admission-source-1/observe_root38_current.py', 'bytes': 5305, 'sha256': 'eb7a8d45a065ab88d94afd905c68c18d8eb04b069eac00ccd641e6b3977d0238'}
        root38_child = subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',str(root38_observer)],capture_output=True,timeout=40)
        assert root38_child.returncode == 0 and not root38_child.stderr
        root38_current = json.loads(root38_child.stdout)
        assert root38_current['status'] == 'PASS_ROOT38_V3_PRE_GUEST_FAILED_RETIREMENT_CURRENT_PENDING_ROOT_ACCEPTANCE'
        assert root38_current['known_numeric_controls_absent'] == [1725949, 1726070, 1726074, 1726076, 1726082, 1726088, 1726094, 1726100, 1726106, 1726112, 1726118, 1726124, 1726347, 1726353, 1726359, 1726365, 1726371, 1726378, 1726384, 1726390, 1726396, 1726402, 1726408, 1726414, 1726420, 1726426, 1726432, 1726438, 1730479, 1731468, 1735781, 1735836, 1735840, 1735842, 1735848, 1735854, 1735860, 1735866, 1735872, 1735878, 1735884, 1735890, 1735966, 1735972, 1735978, 1735984, 1735990, 1735996, 1736002, 1736009, 1736015, 1736021, 1736027, 1736033, 1736039, 1736045, 1736051, 1736057]
        assert not root38_current['group_membership_observation']['errors']
        assert root38_current['new_V3_25_clients_reaped'] is True
        assert root38_current['retained_failed113_container_exit'] == 1
        # Root40 normal native retirement is latest; oldbd5d/363375/V3-9d3 stay separate.
        for pid in ROOT40_ACTORS:
            assert not Path('/proc',str(pid)).exists()
            assert not any(row['pid'] == pid or row['pgrp'] == pid for row in census['rows'])
            assert not any(row['pid'] == pid or row['pgrp'] == pid for row in root38_current['group_membership_observation']['rows'])
        latest40_queries = []
        for retained in latest40_controls['queries']:
            child = subprocess.run(retained['argv'],capture_output=True,text=True,timeout=15)
            assert child.returncode == retained['returncode'] and child.stdout == retained['stdout'] and child.stderr == retained['stderr']
            latest40_queries.append(dict(argv=retained['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
        # Existing Root41 observer keeps exact failed-startup25/28 and all86 prior controls.
        assert ref(Path(ROOT41_OBSERVER['path']))==ROOT41_OBSERVER
        root41_child=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',ROOT41_OBSERVER['path']],capture_output=True,timeout=40)
        assert root41_child.returncode==0 and not root41_child.stderr
        root41_current=json.loads(root41_child.stdout)
        assert root41_current['status']=='PASS_ROOT41_EXACT_FAILED_STARTUP_CURRENT_PENDING_ROOT_ACCEPTANCE' and root41_current['new_exact25_clients_reaped'] is True and len(root41_current['new_exact28_actors'])==28
        assert root41_current['known_numeric_controls_absent']==latest42['fresh_current']['prior_controls_preserved']
        assert not root41_current['group_membership_observation']['errors']
        for actor in [latest42['holder'],latest42['runner']]:
            assert not Path('/proc',str(actor['pid'])).exists()
            assert not any(x['pid']==actor['pid'] or x['pgrp']==actor['pid'] for x in census['rows'])
            assert not any(x['pid']==actor['pid'] or x['pgrp']==actor['pid'] for x in root41_current['group_membership_observation']['rows'])
        retained114=subprocess.run(prefix+['inspect',latest42['retained_stopped_container']],capture_output=True,text=True,timeout=15)
        assert retained114.returncode==0 and not retained114.stderr
        retained114_state=json.loads(retained114.stdout);assert len(retained114_state)==1 and retained114_state[0]['Id']==latest42['retained_stopped_container']
        assert retained114_state[0]['State']['Running'] is False and retained114_state[0]['State']['Pid']==0 and retained114_state[0]['State']['ExitCode']==0 and retained114_state[0]['State']['OOMKilled'] is False
        memory = {line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
        assert memory['MemAvailable'] >= 24*2**30
        paths = ['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy','/sys/fs/cgroup/pids/mckernel-dev/pids.max']
        cgroup = {p:Path(p).read_text().strip() for p in paths}
        assert list(cgroup.values()) == ['100000','400000','12884901888','1','512']
        pids = int(Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text())
        assert pids == 0
        directories = []
        for path in [A/'CAPTURE',Path(static['attempt_parent'])]:
            assert path.is_dir() and not list(path.iterdir())
            info = path.lstat()
            directories.append(dict(path=str(path),device=info.st_dev,inode=info.st_ino,mode=info.st_mode,uid=info.st_uid,gid=info.st_gid))
        assert all(a < b for a,b in zip(guard.guard(),cutoffs))
        value = dict(scope=__doc__.splitlines()[0],observed_clocks=clocks,fixed_cutoffs=list(cutoffs),freshness_seconds_max=120,
            boot_id=guard.BOOT,root_ledger35=ref(LEDGER),actual_latest_operation_postjoin_acceptance={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f05-v3-root-export-native-preparation-source-1/root-adopted-native-entry-outer-cdc-root39-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 7877, 'sha256': 'd4ca62159bacb2aa20cbdd34760b455dcadfcafa1c0727ccbb06dfc632824706'},
            latest_root42=ROOT42_FREE,retained_current114_terminal=latest42_terminal,root41_historical_current=root41_current,retained114_current_query=dict(argv=prefix+['inspect',latest42['retained_stopped_container']],returncode=retained114.returncode,stdout=retained114.stdout,stderr=retained114.stderr),current_physical_observation=current,known_actual_actor_controls_absent=actors,latest_root40=ROOT40_FREE,latest_root40_actual33_actor_controls=ROOT40_ACTORS,latest_root40_exact_queries=latest40_queries,root38_historical_current=root38_current,root38_query_capture=dict(returncode=root38_child.returncode,stdout=root38_child.stdout.decode(),stderr=root38_child.stderr.decode()),retained_current113_terminal=terminal,
            inherited_current111=ref(INHERITED111),inherited_native_retirement=ref(INHERITED_NATIVE),retained_current111_terminal=inherited_terminal,
            no_existing_heavy=True,running_container_observation=docker[0],retained_stopped_observation=docker[1],
            active_shared_records_absent=True,capacity=current['capacity'],memory=memory,cgroup=cgroup,pids_current=pids,
            container_reservation=dict(cpus='2-5',jobs=4,RAM_bytes=12884901888,pids=512,swap_bytes=0,network='none'),
            other_RAM_reserved_bytes=6442450944,aggregate_RAM_ceiling_GiB='21.6619',aggregate_jobs_max=7,
            fresh_directories=directories,native_acceptance=False)
        result_stream.write((json.dumps(value,indent=2)+'\n').encode())
    print(json.dumps(dict(status='ACTUAL_FRESH_ORIGINAL_STARTUP_RESOURCE_CAPTURE_NOT_EXECUTION_RELEASE',resource=ref(output))))

if __name__ == '__main__':
    main()
