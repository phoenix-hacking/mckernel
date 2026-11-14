#!/usr/bin/env python3
"""Fixed M02 fresh-parent metadata observation; external reviewed grant required."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
DATA = HERE / 'CURRENT-CASE-DATA.reader-bound.json'
DATA_SHA = '6e0d8ff35828340d9b0037d40b07074363ffb9e68e13359bbd49863f3e5174d4'
RESULT = HERE / 'ACTUAL-FRESH-PARENT-AND-FULL-PREFLIGHT.json'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def checked(row):
    path = Path(row['path'])
    st = path.lstat()
    raw = path.read_bytes()
    need(st.st_mode == row['mode'] and len(raw) == row.get('bytes', row.get('size')) and
         hashlib.sha256(raw).hexdigest() == row['sha256'], 'bound source/report drift')
    return raw

def full9(path):
    s = path.lstat()
    return dict(device=s.st_dev, inode=s.st_ino, mode=s.st_mode, uid=s.st_uid, gid=s.st_gid,
                nlink=s.st_nlink, size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)

def write(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())

need(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000, 'ordinary uidgid1000')
need(os.sched_getaffinity(0) == {6}, 'reviewed CPU6')
raw = DATA.read_bytes()
need(hashlib.sha256(raw).hexdigest() == DATA_SHA, 'fixed current case DATA')
data = json.loads(raw)
need(data['profile']['guest_timeout_seconds'] == 40, 'immutable40 profile')
owner = data['current_owner']
checked(owner)
for row in data['HERE_runtime_sources']:
    need(checked(row['private']) == checked(row['accepted']), 'HERE sibling identity')
checked(data['unchanged_absolute_RUNNER'])
checked(data['unchanged_absolute_bound_manifest_diagnostic'])
checked(data['actual_source_closure_acceptance'])
reader = json.loads(checked(data['positive_reader_actual_acceptance']))
need(reader['schema'] == 'mckernel.independent-native-positive-physical-actual-two-witness-review.v1' and
     reader['status'] == 'PASS_SOURCE_AND_ACTUAL_WHOLE_CONSUMER_CHECKS_ONLY' and
     reader['decision'] == 'PASS_EXACT_CURRENT_POSITIVE_NATIVE_OWNER_PHYSICAL_CONSUMER_AND_TWO_WITNESS_CHECKS', 'current physical consumer acceptance')
checked(data['positive_reader_candidate'])
checked(data['positive_reader_context'])
checked(data['latest_exclusive_physical'])
need(data['runtime_release'] is None and data['LAST_snapshot'] is None, 'no runtime release')
parent = Path(data['prospective_parent'])
base = parent.parent
scratch = Path('/home/holden/mckernel-work/scratch')
need(parent == scratch / 'e7t-261020-1' / 'p', 'one exact fresh parent')
need(scratch.resolve() == scratch and stat.S_ISDIR(scratch.lstat().st_mode), 'canonical scratch root')
need(not os.path.lexists(base) and not os.path.lexists(parent) and not os.path.lexists(RESULT), 'fresh metadata outputs')
for path in data['final19_outputs'] + data['capture_paths'] + [data['prospective_attempt'], data['prospective_owner_evidence']]:
    need(not os.path.lexists(path), 'fresh bound output namespace')
need(len(set(data['final19_outputs'])) == 19 and len(set(data['capture_paths'])) == 49, 'exact19 and49 roles')
need(not (set(data['final19_outputs']) | set(data['capture_paths'])) &
     (set(data['source_input_paths']) | set(data['prior_output_paths'])), 'namespace source/prior collision')
state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
need(state['last_rate_limits']['primary']['usedPercent'] < 100, 'included usage guard')
mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))) * 1024
need(mem >= 5 << 30, 'ordinary RAM headroom')
hv, sv = os.statvfs(HERE), os.statvfs(scratch)
need(hv.f_bavail * hv.f_frsize >= (16 << 30) + (64 << 20), 'host floor plus growth')
need(sv.f_bavail * sv.f_frsize >= (12 << 30) + (1 << 20), 'scratch floor plus metadata')
# These are the only scratch mutations. Failures retain their exact state.
os.mkdir(base, 0o700)
os.mkdir(parent, 0o700)
for path in (base, parent):
    s = path.lstat()
    need(s.st_uid == s.st_gid == 1000 and s.st_mode == stat.S_IFDIR | 0o700, 'new private parent identity')
need(not list(parent.iterdir()), 'empty fresh parent')
enginepath = Path(owner['path']).parent / 'native_owner_binding.py'
expected_engine = next(row['private'] for row in data['HERE_runtime_sources'] if Path(row['private']['path']).name == 'native_owner_binding.py')
need(str(enginepath) == expected_engine['path'], 'current HERE engine')
checked(expected_engine)
spec = importlib.util.spec_from_file_location('m02_current_fresh_parent_exact_existing_engine', enginepath)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
result = engine.verify(data['binding'])
for key in ('owner_argv', 'inside_owner_argv', 'container_create_argv', 'qemu_argv'):
    need(result[key] == data['prospective_full_argv'][key], 'actual complete argv differs: ' + key)
need(result['paths']['qmp_socket'] == data['QMP']['path'] and result['paths']['qmp_socket_bytes'] == 99, 'actual QMP99')
need(result['clocks_or_host_effects'] == 0 and result['native_execution_release'] is None, 'no owner effects')
create = result['container_create_argv']
ro = []
for i, arg in enumerate(create[:-1]):
    if arg == '--mount':
        fields = create[i+1].split(',')
        if fields[0] == 'type=bind' and 'readonly' in fields:
            ro.append(Path(next(x[4:] for x in fields if x.startswith('src='))))
for path in [owner['path'], data['unchanged_absolute_RUNNER']['path'], data['unchanged_absolute_bound_manifest_diagnostic']['path']]:
    need(any(Path(path) == root or root in Path(path).parents for root in ro), 'active source RO visibility')
need(not list(parent.iterdir()), 'parent remained empty after no-effect verify')
identity = full9(parent)
record = dict(status='PASS_ACTUAL_FRESH_PARENT_AND_COMPLETE_NO_EFFECT_PREFLIGHT_ONLY',
    schema='mckernel.m02-actual-fresh-parent-and-full-preflight.v1', case_data=dict(path=str(DATA), bytes=len(raw), sha256=DATA_SHA),
    binding=data['binding'], parent_full9=identity, parent_identity=dict(device=identity['device'], inode=identity['inode'], mode=identity['mode'], uid=1000, gid=1000),
    actual_full_preflight=result, current_owner=owner, final19_outputs=data['final19_outputs'], capture_paths=data['capture_paths'],
    parent_empty=True, runtime_release=None, LAST_snapshot=None, root_operations=0, guest_runs=0)
write(RESULT, record)
print(json.dumps(dict(status=record['status'], actual_result=str(RESULT), QMP99=True, final19=19, captures=49, runtime_release=None)))
