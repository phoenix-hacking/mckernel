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
profile = json.loads((D / 'READONLY-QUERY-PROFILE.json').read_text())
assert digest(D / 'observe_bfd_admission.py') == profile['query_sha256']
argv = ['/usr/bin/sudo', '-A', '/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit',
        '--as=2147483648:2147483648', '--cpu=30:30', '--fsize=33554432:33554432',
        '--nofile=256:256', '--core=0:0', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B',
        str(D / 'observe_bfd_admission.py'), digest(D / 'READONLY-QUERY-PROFILE.json'), hashlib.sha256(raw).hexdigest()]
document = {'scope':profile['scope'],'status':'EXACT_ARGV_ONLY_PENDING_INDEPENDENT_ROOT_EXECUTION_RELEASE',
            'argv':argv,'query_sha256':profile['query_sha256'],'profile_sha256':digest(D / 'READONLY-QUERY-PROFILE.json'),
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
