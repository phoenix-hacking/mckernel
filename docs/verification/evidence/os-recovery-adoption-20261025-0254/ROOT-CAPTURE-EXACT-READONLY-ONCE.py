"""Functional McKernel OS work only; no security testing. One bounded observation."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def publish(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


grant_path = Path(sys.argv[1]).resolve()
grant = json.loads(grant_path.read_text())
assert grant['author'] == '/root'
assert grant['decision'] == 'GRANT_EXACT_BOUNDED_READONLY_OBSERVATION_ONCE'
packet_path = Path(grant['packet']['path'])
assert reference(packet_path) == grant['packet']
packet = json.loads(packet_path.read_text())
assert grant['argv'] == packet['argv']
for key in ('source', 'profile', 'cleanup_source'):
    assert reference(Path(packet[key]['path'])) == packet[key]
assert reference(Path(grant['independent_review']['path'])) == grant['independent_review']
root = Path(grant['outer_capture_directory'])
root.mkdir(mode=0o700)
started = time.time()
with (root / 'stdout').open('xb') as stdout, (root / 'stderr').open('xb') as stderr:
    child = subprocess.Popen(packet['argv'], stdin=subprocess.DEVNULL,
                             stdout=stdout, stderr=stderr, start_new_session=True)
    try:
        stat = Path('/proc', str(child.pid), 'stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        stat = None
    publish(root / 'PROCESS.json', dict(pid=child.pid, starttime=stat[19] if stat else None,
            pgid=int(stat[2]) if stat else None, argv=packet['argv'], started_at=started,
            grant=reference(grant_path), deadline_owner='observer own 240s ITIMER_REAL'))
    returncode = child.wait()
    stdout.flush()
    stderr.flush()
    os.fsync(stdout.fileno())
    os.fsync(stderr.fileno())
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
group = []
observation_errors = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if int(fields[2]) == child.pid:
            group.append(int(proc.name))
    except FileNotFoundError:
        continue
    except OSError as error:
        observation_errors.append(dict(pid=int(proc.name), error=type(error).__name__))
publish(root / 'JOIN.json', dict(pid=child.pid, returncode=returncode,
        direct_child_joined=True, group_members=group, group_observation_errors=observation_errors,
        closed_streams=True,
        wall_seconds=time.time()-started, cpu_seconds=usage.ru_utime+usage.ru_stime,
        peak_rss_kib=usage.ru_maxrss, stdout=reference(root / 'stdout'),
        stderr=reference(root / 'stderr')))
print(json.dumps(dict(returncode=returncode, group_members=group,
                      capture_directory=str(root))))
