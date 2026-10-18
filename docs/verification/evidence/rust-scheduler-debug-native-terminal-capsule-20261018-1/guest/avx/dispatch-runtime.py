"""Dormant dispatcher runtime, selected owner-join/readback pattern only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import time

HERE=Path(__file__).resolve().parent
EXPECTED_PARENT_IDENTITY={'device': 1828, 'inode': 755803, 'uid': 1000, 'gid': 1000, 'mode': '0o700'}


def checked(row):
    data=Path(row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    return json.loads(data)


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--release',required=True);parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args()
    assert os.getuid()==os.geteuid()==1000
    release=checked({'path':args.release,'sha256':args.release_sha256})
    assert release['status']=='PASS_EXECUTION_RELEASE'and release['runtime_release']is True
    assert type(release['execution_count'])is int and release['execution_count']==1
    terminal=release['terminal_cleanup_and_common_shared_release']
    assert terminal['status']=='PASS'
    checked(terminal['ref'])
    meta=checked(release['conditional_metadata_release'])
    proposal=checked(meta['proposal'])
    fresh=checked(release['fresh_live_preflight'])
    checked(release['independent_static_execution_decision'])
    assert fresh['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT'and 0<=time.time()-fresh['time_epoch']<=60
    assert fresh['exclusive_heavy_accepted']is True and fresh['root_mutex_snapshot_free']is True
    parent=Path(proposal['parent']['path']);st=parent.lstat()
    identity=dict(device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)))
    assert identity==EXPECTED_PARENT_IDENTITY==fresh['parent_identity']==release['parent_identity']
    assert parent.resolve(strict=True)==parent and list(parent.iterdir())==[]
    nonce=proposal['nonce'];attempt=parent/('attempt-'+nonce);owner_evidence=Path(str(parent)+'.owner-'+nonce)
    assert not os.path.lexists(attempt)and not os.path.lexists(owner_evidence)
    started=time.monotonic()
    # The reviewed owner supplies lifecycle/cleanup bounds. Do not impose an
    # outer kill that could abandon its retained recovery lease.
    with(HERE/'owner.stdout').open('xb')as out,(HERE/'owner.stderr').open('xb')as err:
        owner=subprocess.run(proposal['argv'],stdout=out,stderr=err,check=False)
    join=dict(argv=proposal['argv'],returncode=owner.returncode,joined=True,elapsed_seconds=time.monotonic()-started,
              source_known_positive_retirement=owner.returncode==0,
              scope='Direct client physically joined; accepted exact owner zero-exit path includes checked retirement, lease release and evidence flush')
    with(HERE/'owner-join.json').open('x')as stream:json.dump(join,stream,indent=2);stream.write('\n')
    print(json.dumps(join),flush=True)
    if owner.returncode:raise SystemExit(owner.returncode)
    for path,uid in[(owner_evidence,0),(attempt,1000)]:
        st=path.lstat();assert path.resolve(strict=True)==path and stat.S_ISDIR(st.st_mode)and st.st_uid==uid
    st=(attempt/'result.json').lstat();assert stat.S_ISREG(st.st_mode)and st.st_nlink==1
    plan=meta['postjoin_readback']
    assert plan['timeout_seconds_per_command']==30 and plan['capture_limit_bytes_per_command']==33554432
    def bounds():
        resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    for index,argv in enumerate(plan['argv'],1):
        row=dict(argv=argv,timeout_seconds=30,fsize_bytes=33554432);began=time.monotonic()
        try:
            with(HERE/('readback-'+str(index)+'.stdout')).open('xb')as out,(HERE/('readback-'+str(index)+'.stderr')).open('xb')as err:
                done=subprocess.run(argv,stdout=out,stderr=err,timeout=30,preexec_fn=bounds,check=False)
            row.update(returncode=done.returncode,elapsed_seconds=time.monotonic()-began)
        except BaseException as error:
            row['failure']=type(error).__name__+': '+str(error)
            with(HERE/('readback-'+str(index)+'.command.json')).open('x')as stream:json.dump(row,stream,indent=2)
            raise SystemExit('STOP readback failure; retain evidence for dispatcher')
        with(HERE/('readback-'+str(index)+'.command.json')).open('x')as stream:json.dump(row,stream,indent=2);stream.write('\n')
        if done.returncode:raise SystemExit(done.returncode)
    print('Owner and three bounded postjoin readbacks joined; independent actual result review required',flush=True)


if __name__=='__main__':main()
