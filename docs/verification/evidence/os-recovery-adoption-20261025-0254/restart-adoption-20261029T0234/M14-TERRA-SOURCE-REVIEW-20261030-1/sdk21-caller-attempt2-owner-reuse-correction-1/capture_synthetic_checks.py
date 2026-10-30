"""Capture independent synthetic check outputs and statuses, source-only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

here=Path(__file__).resolve().parent
sources=('attempt2_gate.v2.py','test_attempt2_gate.v2.py','custody_protocol.py',
         'test_custody_protocol.py','daemon_image_parent.attempt2.py','test_parent_deadline.py',
         'test_group_integration.py','scoped_owner.py','test_scoped_owner.py','capture_synthetic_checks.py')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
before={name:sha(here/name) for name in sources}
out=here/'synthetic-results-1';out.mkdir(mode=0o700)
rows=[]
for index,name in enumerate(('test_attempt2_gate.v2.py','test_custody_protocol.py','test_parent_deadline.py','test_group_integration.py','test_scoped_owner.py'),1):
    argv=[sys.executable,'-B',str(here/name)]
    started=time.monotonic()
    try:
        done=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            cwd=str(here),timeout=30,check=False)
        stdout,stderr,status=done.stdout,done.stderr,done.returncode
        error=None
    except subprocess.TimeoutExpired as exc:
        stdout,stderr,status=exc.stdout or b'',exc.stderr or b'',None
        error='test timeout; outcome not a pass'
    for ext,data in (('stdout',stdout),('stderr',stderr)):
        with (out/('%d.%s'%(index,ext))).open('xb') as stream: stream.write(data)
    rows.append({'script':name,'argv':argv,'exit_status':status,'error':error,
                 'elapsed_monotonic_seconds':time.monotonic()-started,
                 'stdout':{'path':'%d.stdout'%index,'sha256':hashlib.sha256(stdout).hexdigest()},
                 'stderr':{'path':'%d.stderr'%index,'sha256':hashlib.sha256(stderr).hexdigest()}})
after={name:sha(here/name) for name in sources}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
        'source_hashes_before':before,'source_hashes_after':after,
        'sources_unchanged':before==after,'checks':rows,
        'all_pass':before==after and all(row['exit_status']==0 and row['error'] is None for row in rows),
        'physical_observer_or_release':False}
with (out/'result.json').open('x') as stream: json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'all_pass':result['all_pass'],'checks':[{k:r[k] for k in ('script','exit_status','error')} for r in rows]},sort_keys=True))
sys.exit(0 if result['all_pass'] else 1)
