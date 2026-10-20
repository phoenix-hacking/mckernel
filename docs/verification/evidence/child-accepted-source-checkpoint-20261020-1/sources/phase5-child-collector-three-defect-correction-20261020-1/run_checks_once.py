"""One dispatcher-admitted ordinary CPU6 envelope; no stage/root/guest."""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, time

D = Path(__file__).resolve().parent
CAPTURE = Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')

def main():
    begin = time.monotonic()
    for row in json.loads((D/'SOURCE-FREEZE.json').read_text())['files']:
        data = (D/row['path']).read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert hashlib.sha256(CAPTURE.read_bytes()).hexdigest() == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
    spec = importlib.util.spec_from_file_location('accepted_owned_capture', CAPTURE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
    assert resource.getrlimit(resource.RLIMIT_AS) == (1 << 30, 1 << 30)
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    assert state['phase'] == 'running' and not state.get('pause_reason') and not state.get('stop_reason')
    assert state['last_rate_limits']['primary']['usedPercent'] < 100

    def capacity():
        mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                       if x.startswith('MemAvailable:'))) * 1024
        assert mem >= 6 << 30
        values = {'mem_available': mem}
        for path, floor, growth in [('/home/holden',16 << 30,128 << 20),
                                    ('/home/holden/mckernel-work/scratch',12 << 30,0)]:
            v = os.statvfs(path)
            free = v.f_bavail * v.f_frsize
            assert free >= floor + growth
            values[path] = free
        return values

    # Root separately admits the slot. Conservatively refuse every other
    # CPU6-only user process; never match shell command bodies as identities.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():
            continue
        try:
            if os.sched_getaffinity(int(proc.name)) != {6}:
                continue
            fields = (proc/'stat').read_text().rsplit(')',1)[1].split()
            assert int(fields[6]) & 0x200000, 'CPU6-only user process: ' + proc.name
        except ProcessLookupError:
            raise RuntimeError('Unstable CPU6 census; preserve admission failure')
    admission = capacity()
    out = D/'ordinary-check-1'
    assert not out.exists()
    out.mkdir(mode=0o700)
    (out/'vectors').mkdir(mode=0o700)
    m.write(out/'admission.json', {'capacity': admission, 'service_usage': state['last_rate_limits']['primary']['usedPercent'],
                                  'scope': 'child collector host-only affected bodies/static compile; no stage or native'})
    for sig in m.STOP_SIGNALS:
        signal.signal(sig, m.stop)
    records = []
    error = None
    try:
        for i, command in enumerate(json.loads((D/'COMMANDS.json').read_text())):
            capacity()
            left = 35 - (time.monotonic() - begin)
            assert left > 0
            p = out/('%02d-' % i + command['name'])
            p.mkdir(mode=0o700)
            m.write(p/'command.json', command)
            def limits():
                for kind, value in [(resource.RLIMIT_AS,960 << 20), (resource.RLIMIT_CPU,30),
                                    (resource.RLIMIT_FSIZE,32 << 20), (resource.RLIMIT_CORE,0),
                                    (resource.RLIMIT_NOFILE,256)]:
                    resource.setrlimit(kind, (value,value))
            result = m.owned_capture({'argv':command['argv']}, p, min(20,left), limits)
            m.write(p/'status.json',result)
            records.append(result)
            if (result['returncode'] != command['expected_exit'] or not result['direct_child_joined']
                    or not result['group_absent'] or result['timed_out'] or result['error']
                    or result['retirement_error'] or result['captures']['stderr']['size']):
                error = 'First unexpected command failure: ' + command['name']
                break
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    ok = error is None and len(records) == 9
    whole = {'status':'PASS_HOST_ONLY_AFFECTED_BODIES_STATIC_CHILD_COLLECTOR' if ok else 'FAIL_PRESERVE',
             'records':records,'error':error,'elapsed_seconds':time.monotonic()-begin,
             'guest_runs':0,'stage_runs':0,'native_or_ACK_acceptance':False}
    m.write(out/'whole.json',whole)
    print(json.dumps({k:whole[k] for k in ('status','error','elapsed_seconds')}))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
