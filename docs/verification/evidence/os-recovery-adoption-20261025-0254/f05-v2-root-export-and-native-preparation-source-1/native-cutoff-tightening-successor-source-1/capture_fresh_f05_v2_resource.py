"""Functional McKernel OS/apps and Rust migration only; no security testing.
Private source successor of strict native resource capture. No execution grant.
Retains reviewed historical physical observer and adds exact Root32/CURRENT111 schema.
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
LEDGER = E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER32.json'
LEDGER_SHA = '822f05a582d3bc536b77111457944b7082dc6829d86ef0c956df4e35f4a03010'
FREE = E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2/INDEPENDENT-POSTBUILD-CURRENT-FREE.json'
FREE_SHA = '9904aa3c39b0a83d8675a77b97631f3731f2f3e568c5fde65b6ef91c28f64d19'

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
        assert len(ledger['consumed_nonces']) == len(set(ledger['consumed_nonces'])) == 32
        assert ledger['latest_accepted_free_boundary'] == ref(FREE)
        assert free['decision'] == 'PASS_POSITIVE_CURRENT111_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX'
        assert free['independent'] is True and free['implementation_ownership'] is False
        assert free['nonce'] == ledger['consumed_nonces'][-1] and free['nonce_consumed'] is True
        assert free['holder']['pid'] == 1659765 and free['holder']['starttime'] == 92650542
        assert free['runner'] == dict(pid=1660450,starttime=92662958)
        assert free['retained_stopped_container'] == '5c92e3d9929e46dfe60a02cdda375f17962cc16c72f2727ac5ad65878f1caf27'
        old_current = checked(free['current_observation'])
        terminal = checked(free['container_terminal'])
        holder = checked(old_current['holder_ready'])
        runner_join = checked(old_current['runner_join'])
        tool_join = checked(old_current['holder_tool_result'])
        assert holder['holder']['pid'] == free['holder']['pid'] and holder['holder']['starttime'] == free['holder']['starttime']
        assert holder['holder']['device'] == 27 and holder['holder']['inode'] == 4 and holder['holder']['fd'] == 3
        assert runner_join == dict(pid=1660450,starttime=92662958,returncode=0,joined=True)
        assert tool_join['actual_tool_terminal'] is True and tool_join['actual_tool_exit_code'] == 0 and tool_join['positive_wait_observed'] is True
        assert terminal['container'] == free['retained_stopped_container'] and terminal['returncode'] == 0
        assert terminal['state']['Running'] is False and terminal['state']['Pid'] == 0 and terminal['state']['ExitCode'] == 0
        static = json.loads((A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json').read_bytes())
        assert static['root_ledger32'] == ref(LEDGER) and static['latest_serial_operation_physical_acceptance'] == ref(FREE)
        assert static['expected_case'] == 'M14-05-05-owned-processvm-v2-204B'
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
        actors = [free['holder'],free['runner']]
        for actor in actors:
            assert not Path('/proc',str(actor['pid'])).exists()
            assert not any(row['pid'] == actor['pid'] or row['pgrp'] == actor['pid'] for row in census['rows'])
        prefix = ['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
        queries = [prefix+['ps','-q','--no-trunc'],prefix+['inspect',free['retained_stopped_container']]]
        docker = []
        for argv in queries:
            result = subprocess.run(argv,capture_output=True,text=True,timeout=15)
            assert result.returncode == 0 and not result.stderr
            if 'inspect' in argv:
                data = json.loads(result.stdout)
                assert len(data) == 1 and data[0]['Id'] == free['retained_stopped_container']
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
            boot_id=guard.BOOT,root_ledger32=ref(LEDGER),actual_latest_operation_postjoin_acceptance=ref(FREE),
            current_physical_observation=current,known_current111_actors_absent=actors,retained_current111_terminal=terminal,
            no_existing_heavy=True,running_container_observation=docker[0],retained_stopped_observation=docker[1],
            active_shared_records_absent=True,capacity=current['capacity'],memory=memory,cgroup=cgroup,pids_current=pids,
            container_reservation=dict(cpus='2-5',jobs=4,RAM_bytes=12884901888,pids=512,swap_bytes=0,network='none'),
            other_RAM_reserved_bytes=6442450944,aggregate_RAM_ceiling_GiB='21.6619',aggregate_jobs_max=7,
            fresh_directories=directories,native_acceptance=False)
        result_stream.write((json.dumps(value,indent=2)+'\n').encode())
    print(json.dumps(dict(status='ACTUAL_FRESH_F05_V2_RESOURCE_CAPTURE_NOT_EXECUTION_RELEASE',resource=ref(output))))

if __name__ == '__main__':
    main()
