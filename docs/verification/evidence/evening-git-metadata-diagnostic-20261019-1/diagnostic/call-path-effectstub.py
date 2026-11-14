#!/usr/bin/python3
"""Ordinary user production main path; privileged effects and Git stubbed."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import types
from unittest.mock import patch
BASE = Path('/home/holden/mckernel-work/host-preparation/evening-git-metadata-diagnostic-20261019-1')

def load(path, name):
    m = types.ModuleType(name); m.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), m.__dict__)
    return m

def main():
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise RuntimeError('ordinary fixture only')
    d = load(BASE / 'git-metadata-only.py', 'diagnostic_fixture')
    c = d.load_contract()
    rows = c.pinned()['rows']
    expected = {}
    for row in rows:
        r = row['restoration']; expected[r['git_blob']] = ('blob', str(r['size']))
        expected[r['git_commit']] = ('commit', '123')
    keys = sorted(expected); data = ('\n'.join(keys)+'\n').encode()
    output = ''.join(key+' '+expected[key][0]+' '+expected[key][1]+'\n' for key in keys).encode()
    release = {'status': 'ROOT_GIT_METADATA_ONLY_RELEASE', 'source_sha256': d.SOURCE_SHA256,
               'diagnostic_sha256': c.digest((BASE/'git-metadata-only.py').read_bytes()), 'manifest_sha256': c.PIN,
               'independent_review': {'status': 'PASS', 'sha256': 'f'*64}, 'boot_id': c.BOOT,
               'expires_unix': time.time()+120, 'coordinator_identity': [os.getpid(), c.proc_identity(os.getpid())[0]],
               'selected_rows':120, 'selected_objects':len(keys)}
    raw = json.dumps(release).encode(); release_path = str(BASE/'FIXTURE-NOT-A-RELEASE.json')
    original_raw = c.raw_small; original_open = os.open; original_fstat = os.fstat; original_lstat = os.lstat
    locked = []
    lockfd = original_open('/dev/null', os.O_RDONLY)
    lockstat = types.SimpleNamespace(st_dev=c.LOCK_ID[0], st_ino=c.LOCK_ID[1])
    calls=[]
    def git_effect(argv, body=None):
        assert argv == ['/usr/bin/setpriv','--reuid=1000','--regid=1000','--clear-groups','--no-new-privs',
                        '/usr/bin/git','-c','core.packedGitWindowSize=8m','-c','core.packedGitLimit=64m',
                        '-C',str(c.REPO),'cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)']
        assert body == data
        calls.append({'argv':argv,'input_sha256':c.digest(body),'objects':len(keys)})
        return output
    stream=io.StringIO()
    try:
        with patch.object(d,'load_contract',return_value=c), patch.object(c,'raw_small',side_effect=lambda path,*args:raw if str(path)==release_path else original_raw(path,*args)), patch.object(c,'run',side_effect=git_effect), patch.object(os,'getuid',return_value=0), patch.object(os,'geteuid',return_value=0), patch.object(os,'open',side_effect=lambda path,*args,**kw:lockfd if Path(path)==c.LOCK else original_open(path,*args,**kw)), patch.object(os,'fstat',side_effect=lambda fd:lockstat if fd==lockfd else original_fstat(fd)), patch.object(os,'lstat',side_effect=lambda path,*args,**kw:lockstat if Path(path)==c.LOCK else original_lstat(path,*args,**kw)), patch.object(d.fcntl,'flock',side_effect=lambda fd,flags:locked.append((fd,flags))), patch.object(sys,'argv',[str(BASE/'git-metadata-only.py'),'--release',release_path,'--release-sha256',c.digest(raw)]), contextlib.redirect_stdout(stream):
            d.main()
    finally:
        # main owns its lock fd; do not close/reuse it again.
        pass
    result=json.loads(stream.getvalue()); assert result['status']=='ROOT_GIT_METADATA_ONLY_PASS'
    assert len(calls)==1 and len(locked)==1 and result['git']['objects']==len(keys)
    packet={'status':'PASS_ACTUAL_MAIN_CALL_PATH_EFFECTSTUB','root_execution':False,'real_git_execution':False,
            'selected_rows':len(rows),'selected_objects':len(keys),'git_calls':calls,
            'production_git_available_used':True,'production_pinned_used':True,'result':result,
            'effect_stubs':['root uid/euid','release bytes (fixture only)','mutex open/stat/flock','Git process run'],
            'actual_reads':['exact source','frozen manifest','frozen advisory','repository owner directories','own PID stat','boot ID'],
            'diagnostic_sha256':release['diagnostic_sha256']}
    with (BASE/'call-path-effectstub-result-1.json').open('x') as f: json.dump(packet,f,indent=2);f.write('\n')
    print(json.dumps({'status':packet['status'],'selected_rows':len(rows),'selected_objects':len(keys),'git_calls':len(calls)}))
if __name__=='__main__':main()
