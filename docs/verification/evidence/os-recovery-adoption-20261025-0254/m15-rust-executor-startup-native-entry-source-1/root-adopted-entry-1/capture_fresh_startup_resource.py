"""Functional McKernel OS/apps and Rust migration only; no security testing.
Private source successor of strict native resource capture. No execution grant.
Retains reviewed historical physical observer and adds exact Root35/CURRENT112 plus separately retained native/111 ownership.
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
LEDGER = E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER35.json'
LEDGER_SHA = '5cc235f9518e488ba50d700c7b9c256410e77495a7117a3b912101b71baf05c1'
FREE = E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/CURRENT-FREE.json'
FREE_SHA = '52e1dc0902642855c11df0c726dbc365720db1623fc4082748b010255ff844aa'
INHERITED111 = E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/INDEPENDENT-POSTBUILD-CURRENT-FREE.json'
INHERITED_NATIVE = E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def checked(reference):
    path = Path(reference['path'])
    assert ref(path) == reference
    return json.loads(path.read_bytes())

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
        assert len(ledger['consumed_nonces']) == len(set(ledger['consumed_nonces'])) == 35
        assert ledger['latest_accepted_free_boundary'] == ref(FREE)
        assert free['decision'] == 'PASS_POSITIVE_CURRENT112_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX'
        assert free['independent'] is True and free['implementation_ownership'] is False
        assert free['nonce'] == ledger['consumed_nonces'][-1] and free['nonce_consumed'] is True
        assert free['holder']['pid'] == 1702852 and free['holder']['starttime'] == 93360315 and free['holder']['device'] == 27 and free['holder']['inode'] == 4
        assert free['runner'] == dict(pid=1702974,starttime=93366390,returncode=0,joined=True)
        assert free['retained_stopped_container'] == '50970ddb9d70fd3133037de8b68b6aebb92a3bfe4d311185c706d8f9969811bb'
        stored_current = checked(free['current_observation'])
        assert not stored_current['proc_errors'] and len(stored_current['closed_permanent_mutex_probes']) == 2
        assert checked(free['runner_join']) == free['runner']
        local_terminal = checked(free['local_terminal'])
        assert local_terminal['joined'] is True and local_terminal['returncode'] == 0 and local_terminal['holder'] == free['holder']
        tool_join = checked(free['holder_tool_result'])
        assert tool_join['actual_tool_terminal'] is True and tool_join['actual_tool_exit_code'] == 0 and tool_join['positive_wait_observed'] is True
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
        assert static['root_ledger35'] == ref(LEDGER) and static['latest_serial_operation_physical_acceptance'] == ref(FREE)
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
            boot_id=guard.BOOT,root_ledger35=ref(LEDGER),actual_latest_operation_postjoin_acceptance=ref(FREE),
            current_physical_observation=current,known_actual_actor_controls_absent=actors,retained_current112_terminal=terminal,
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
