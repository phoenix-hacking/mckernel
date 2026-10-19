#!/home/holden/anaconda3/bin/python3
"""Finite exact terminal readback, only after independently released joined cleanup."""
import fcntl,hashlib,json,os,resource,stat,subprocess,sys,types
from pathlib import Path
ROOT=Path('/home/holden/mckernel-work/scratch')
ENGINE = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/failure-terminal-preparation-1/cleanup_failed.py')
ENGINE_SHA = 'b09ae03763bcf7d75c21d2028aef902f12a40aba678b1cd03e7b6b35892fa488'
OBSERVER = Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/failure-terminal-preparation-1/observe_failed_retirement.py')
OBSERVER_SHA = '88f6558d8c6280877e4981b68b9817b60c856f340d46cc0cac2bd0beaab9bdd2'
CAP=128*2**20

def need(ok,why):
    if not ok:raise RuntimeError(why)

def load(path,sha):
    raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==sha,'source/hash mismatch: '+str(path))
    m=types.ModuleType('_readback_'+path.stem);m.__file__=str(path);exec(compile(raw,str(path),'exec'),m.__dict__);return m

def census_at_2g(m):
    before=resource.getrlimit(resource.RLIMIT_AS)
    need(before==(1073741824,2147483648),'readback parent must have soft1GiB hard2GiB')
    resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648))
    try:return m.census()
    finally:resource.setrlimit(resource.RLIMIT_AS,before)

def bind_readback(m,r):
    # configure validates active records and cannot run after their archival.
    # Hash-authenticated exact release is installed solely for read-only mount checks.
    m.RELEASE=r
    m.DEVICE=r['observation']['root']['device']
    m.validate_mount()

def archive_argv(paths):
    # Preserve original flat member names while each file stays on its bound
    # parent filesystem; all five paths come from the exact cleanup engine.
    argv=['/usr/bin/tar','--format=ustar','--no-recursion','-cf','-']
    for path in paths:
        argv.extend(['-C',str(path.parent),'--add-file='+path.name])
    return argv

def main():
    need(os.getuid()==os.geteuid()==0,'released root readback required')
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,2147483648));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(CAP,CAP))
    release,sha,resultpath=sys.argv[1:];release=Path(release)
    raw=release.read_bytes();need(hashlib.sha256(raw).hexdigest()==sha,'exact release hash differs')
    r=json.loads(raw);need(r['status']=='PASS_EXECUTION_RELEASE','independent release required');obs=r['observation'];target=obs['target']
    m=load(ENGINE,ENGINE_SHA);o=load(OBSERVER,OBSERVER_SHA)
    result=json.loads(Path(resultpath).read_bytes())
    need(result['status']=='PASS_EXECUTED' and result['terminal'] and result['container_absent'],'joined positive execution result required')
    need(result['container_id']==target['container_id'] and result['release_sha256']==m.digest(m.canonical(r)),'exact result release/CID binding')
    parent,_=m.directory(m.ROOT_LOCK.parent);lock=os.open(m.ROOT_LOCK.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    try:
        need((os.fstat(lock).st_dev,os.fstat(lock).st_ino)==(27,4),'root lock differs')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==obs['boot_id']==o.BOOT,'boot differs')
        m.BOOT_ID=obs['boot_id'];m.OWNER_PID=target['owner_pid'];m.OWNER_START=target['owner_starttime'];m.WAITER_PIDS=tuple(x['pid'] for x in obs['client_ledger'])
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=target['exit_code'];m.EXPECTED_CONTAINER=obs['container_inspect']
        bind_readback(m,r);need(not census_at_2g(m),'original CID reappeared')
        need(not os.path.lexists(m.QUARANTINE) and not os.path.lexists(m.ATTEMPT) and not os.path.lexists(m.SHARED) and not os.path.lexists(m.LEASE),'released names/lease/quarantine not absent')
        paths=[m.PLAN,m.JOURNAL,m.CAPTURE]+list(m.archive_paths())
        def snapshot():
            rows=[m.observe_identity(p) for p in paths]
            need(all(stat.S_ISREG(p.lstat().st_mode) and row['nlink']==1 and row['uid']==1000 for p,row in zip(paths,rows)),'regular UID1000 single-link files required')
            need(sum(x['size'] for x in rows)+len(rows)*4096<CAP,'finite archive cap')
            return rows
        before=snapshot();byname={Path(x['path']).name:x for x in before}
        for key,path in [('plan',m.PLAN),('journal',m.JOURNAL),('capture',m.CAPTURE)]:need(result[key]==byname[path.name],'result file identity differs')
        need(result['archives']==before[3:],'result archives differ')
        plan=m.parse(m.read_bounded(m.PLAN));need(m.digest(m.canonical(plan))==result['plan_sha256'] and plan['release_sha256']==result['release_sha256'],'plan hash/release differs')
        need(plan['container']==[target['container_id'],target['container_name'],target['owner_nonce']],'plan CID/nonce differs')
        journal=m.read_bounded(m.JOURNAL);need(journal.endswith(b'\n'),'torn journal')
        rows=[m.parse(x) for x in journal.splitlines()];need(len(rows)==9,'exact complete journal required');previous=m.digest(m.canonical(plan))
        legal=[(e,i) for i in range(2) for e in ('before_exchange','after_exchange','release','after_release')]+[('complete',2)]
        for seq,(row,(event,index)) in enumerate(zip(rows,legal)):
            body=dict(event=event,index=index,sequence=seq,plan_sha256=m.digest(m.canonical(plan)),previous=previous,plan_identity=[before[0]['device'],before[0]['inode']]);wanted=dict(body,hash=m.digest(m.canonical(body)))
            need(row==wanted and journal.splitlines(keepends=True)[seq]==m.canonical(wanted)+b'\n','journal chain differs');previous=row['hash']
        old_records={x['path']:x for x in obs['retained_exclusions']}
        for row,path in zip(before[3:],(m.ATTEMPT,m.SHARED)):
            old=old_records[str(path)]
            need(all(row[k]==old[k] for k in ('device','inode','size','sha256','uid','gid','mode','nlink')),'archived original record differs')
        selected={x['path']:x for x in obs['selected_files']};side=selected[str(o.OUTPUT/'new-object-metadata.json')]
        meta=json.loads(o.stable_bytes(Path(side['path']),side['sha256']));authority=json.loads(o.stable_bytes(o.NEW_OBJECT_AUTHORITY,o.NEW_OBJECT_AUTHORITY_SHA))
        def objects():return [o.new_object_binding(m,pair[key]) for pair in authority for key in ('original','retained')]
        o.fp_contract().authority_pairs(authority,o.FOURLEAF_ROLES)
        actual=objects();need(len(actual)==2*len(authority) and actual==meta['objects'],'all finite failed-log FD metadata rows differ')
        need(snapshot()==before,'inputs drift before tar')
        argv=archive_argv(paths)
        cp=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=sys.stdout.buffer,stderr=subprocess.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},timeout=30,check=False)
        need(cp.returncode==0 and not cp.stderr,'default nondereferencing tar failed')
        need(snapshot()==before and objects()==actual and not census_at_2g(m),'postcheck drift')
        sys.stderr.write(json.dumps(dict(status='PASS_CLEANUP_POSTJOIN_READBACK_ONLY',members=5,actual_object_rows=actual,application_acceptance=False),sort_keys=True)+'\n');sys.stderr.flush()
    finally:fcntl.flock(lock,fcntl.LOCK_UN);os.close(lock);os.close(parent)

if __name__=='__main__':main()
