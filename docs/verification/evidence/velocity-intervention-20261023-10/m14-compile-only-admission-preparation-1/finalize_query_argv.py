"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite data finalization only, after dispatcher publishes the sealed root context.
No root query, Docker operation, compiler, lease operation or release publication.
"""
from pathlib import Path
import hashlib
import json
import os
import stat

D = Path(__file__).resolve().parent
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def no_missing(value):
    if value is None:
        return False
    if isinstance(value, dict):
        return all(no_missing(item) for item in value.values())
    if isinstance(value, list):
        return all(no_missing(item) for item in value)
    return True

context_path = D / 'ROOT-CONTEXT.ACTUAL.json'
a = context_path.lstat()
assert context_path.resolve(strict=True) == context_path and stat.S_ISREG(a.st_mode)
assert a.st_uid == 0 and a.st_nlink == 1 and not stat.S_IMODE(a.st_mode) & 0o022 and a.st_size <= 1 << 20
raw = context_path.read_bytes()
b = context_path.lstat()
assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns)
context = json.loads(raw)
assert no_missing(context), 'Root must fill actual declarations/authority references; no defaults or minted observations'
profile = json.loads((D / 'READONLY-QUERY-PROFILE.COMPACT.json').read_text())
assert digest(D / 'observe_m14_admission.compact.py') == profile['query_sha256']
inner = ['/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit',
         '--as=2147483648:2147483648', '--cpu=30:30', '--fsize=33554432:33554432',
         '--nofile=256:256', '--core=0:0', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B',
         str(D / 'observe_m14_admission.compact.py'), digest(D / 'READONLY-QUERY-PROFILE.COMPACT.json'), hashlib.sha256(raw).hexdigest()]
outer = json.loads((D / 'ROOT-OWNED-QUERY-PROFILE.PENDING-CONTEXT.json').read_text())
assert digest(D / 'run_root_LONG_admission_capture.py') == outer['runner']['sha256'] == '522ef331dba4e84f45b2f2bc0965c0bb58490127154eb169f469da98619528bf'
outer['query_argv'] = inner
outer['input_sources'].append({'path':str(context_path), 'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)})
outer['status'] = 'EXACT_CONTEXT_BOUND_PENDING_INDEPENDENT_ROOT_EXECUTION_RELEASE'
outer_path = D / 'ROOT-OWNED-QUERY-PROFILE.FINAL.NOT-RELEASED.json'
fd = os.open(outer_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as stream:
    json.dump(outer,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
argv = ['/usr/bin/sudo', '-A', '/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit',
        '--as=2147483648:2147483648', '--cpu=30:30', '--fsize=33554432:33554432',
        '--nofile=256:256', '--core=0:0', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B',
        str(D / 'run_root_LONG_admission_capture.py'), str(outer_path), digest(outer_path)]
document = {'scope':profile['scope'],'status':'EXACT_ARGV_ONLY_PENDING_INDEPENDENT_ROOT_EXECUTION_RELEASE',
            'argv':argv,'query_sha256':profile['query_sha256'],'profile_sha256':digest(D / 'READONLY-QUERY-PROFILE.COMPACT.json'), 'outer_profile_sha256':digest(outer_path), 'inner_argv':inner,
            'context_sha256':hashlib.sha256(raw).hexdigest(),'actual_query':None,'actual_facts':None,'actual_release':None,
            'launch_authorized_by_this_file':False}
path = D / 'ROOT-READONLY-QUERY.EXACT-ARGV.NOT-EXECUTED.json'
fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as stream:
    json.dump(document,stream,sort_keys=True,indent=2)
    stream.write('\n')
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps(document,sort_keys=True))
