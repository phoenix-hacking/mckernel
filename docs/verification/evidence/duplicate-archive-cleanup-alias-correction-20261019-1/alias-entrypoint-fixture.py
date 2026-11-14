#!/usr/bin/python3
"""ONE affected actual process_census call-path fixture, ordinary only.
Frozen13 actual selected mount-row views become synthetic /proc topology with
real live child PID/stat identity, real filesystem readlink/stat/IO, no function
mocks for namespace authentication/normalization/census. No setns/root/mount.
An idle bounded child supplies live PID/stat only; synthetic views aren't runtime
proof. Two FIFO rendezvous cases change synthetic mount state during real census.
"""
import importlib.util
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

BASE = Path(__file__).resolve().parent
ORACLE = json.loads((BASE / 'alias-normalization-oracle.json').read_text())


def load():
    spec=importlib.util.spec_from_file_location('actual_alias',BASE/'exact120.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def scenario(out, pid, positive, mutation=None):
    out.mkdir();m=load();root=out/'proc';root.mkdir();process=root/str(pid);process.mkdir()
    tasks=process/'task';tasks.mkdir();task=tasks/str(pid);task.mkdir();(task/'ns').mkdir();(task/'fd').mkdir()
    (task/'stat').symlink_to('/proc/%s/task/%s/stat'%(pid,pid))
    namespace=positive['namespace'];(task/'ns/mnt').symlink_to(namespace)
    rows=list(positive['rows']);candidate=sorted(m.PARENTS)[0];suffix=candidate[len(str(m.ROOT)):]
    alias_candidate=m.SCRATCH_ALIAS+suffix
    expected=None;path_change=None;fifo_change=None
    if mutation in ('root','source','device','type','destination','access','propagation','shadow','unknown-namespace'):
        if mutation=='root':rows[0]=rows[0].replace('7:36 / ','7:36 /subtree ',1);expected='mapping root/source/type changed'
        if mutation=='source':rows[0]=rows[0].replace('/dev/loop36','/dev/loop99');expected='mapping root/source/type changed'
        if mutation=='device':rows=[r.replace('7:36','7:37') if m.SCRATCH_ALIAS in r else r for r in rows];expected='alias namespace pair changed'
        if mutation=='type':rows[0]=rows[0].replace(' - ext4 ',' - xfs ');expected='mapping root/source/type changed'
        if mutation=='destination':rows=[r.replace(m.SCRATCH_ALIAS,m.SCRATCH_ALIAS+'-changed') if m.SCRATCH_ALIAS in r else r for r in rows];expected='alias namespace pair changed'
        if mutation=='access':rows[0]=rows[0].replace(' rw,nosuid',' ro,nosuid');expected='mapping access/options changed'
        if mutation=='propagation':rows[0]=rows[0].replace('master:151','master:999');expected='mapping propagation changed'
        if mutation=='shadow':rows.append('9900 1 0:99 / '+alias_candidate+' rw - tmpfs tmpfs rw');expected='shadow/target-subtree mount'
        if mutation=='unknown-namespace':namespace='mnt:[999999999]';(task/'ns/mnt').unlink();(task/'ns/mnt').symlink_to(namespace);expected='unreviewed alias namespace'
    (task/'mountinfo').write_text('\n'.join(rows)+'\n')
    for name,target in [('cwd','/tmp'),('root','/'),('exe','/usr/bin/python3')]:
        (task/name).symlink_to(target)
    safe=out/'safe';safe.write_bytes(b'safe');target=out/'candidate-inode';target.write_bytes(b'target')
    fdpath=task/'fd/3';fdpath.symlink_to(safe)
    maps=''
    if mutation in ('alias-cwd','alias-root','alias-exe'):
        field=mutation.split('-')[1];(task/field).unlink();(task/field).symlink_to(alias_candidate+'/nested');expected='process path consumer: '+field
    if mutation in ('alias-file-FD','alias-directory-FD'):
        fdpath.unlink();fdpath.symlink_to(alias_candidate+('/payload' if mutation=='alias-file-FD' else ''));expected='open descriptor consumer path'
    if mutation=='alias-mapped-path':maps='1000-2000 r--p 00000000 00:00 0 '+alias_candidate+'/mapped\n';expected='mapped path consumer'
    if mutation=='FD-inode':fdpath.unlink();fdpath.symlink_to(target);expected='open descriptor consumer inode'
    if mutation=='mapped-inode':
        st=target.stat();maps='1000-2000 r--p 00000000 %x:%x %d %s\n'%(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino,safe);expected='mapped target consumer inode'
    thread=None;thread_errors=[]
    if mutation in ('changed-task-namespace-during-census','changed-mountinfo-during-census'):
        expected='task namespace/mountinfo/start raced';fifo_change=mutation;os.mkfifo(task/'maps')
        def writer():
            try:
                with (task/'maps').open('w'):
                    if fifo_change=='changed-task-namespace-during-census':
                        (task/'ns/mnt').unlink();(task/'ns/mnt').symlink_to('mnt:[4026532662]' if namespace=='mnt:[4026532924]' else 'mnt:[4026532924]')
                    else:
                        raw=(task/'mountinfo').read_text();first,rest=raw.split(' ',1);(task/'mountinfo').write_text(str(int(first)+100000)+' '+rest)
            except BaseException as exc:thread_errors.append(repr(exc))
        thread=threading.Thread(target=writer,daemon=True);thread.start()
    else:(task/'maps').write_text(maps)
    held={'rows':[{'candidate_metadata':m.meta(target.lstat())}],'target_fds':[],'parent_fds':[]}
    error=None
    try:
        result=m.process_census(held,proc_root=root)  # Actual changed entrypoint.
        assert len(result)==1 and len(result[0]['task_views'])==1
        assert result[0]['task_views'][0]['aliases']==[(m.SCRATCH_ALIAS,str(m.ROOT))]
        # Boundary and longest-prefix behavior are exercised with literal paths.
        view=m.authenticated_mount_view(('\n'.join(rows)+'\n').encode(),namespace)
        assert m.canonical_path(m.SCRATCH_ALIAS+'/abc',view)==str(m.ROOT)+'/abc'
        assert m.canonical_path(m.SCRATCH_ALIAS+'-sibling/abc',view)==m.SCRATCH_ALIAS+'-sibling/abc'
    except BaseException as exc:error=repr(exc)
    if thread is not None:
        thread.join(timeout=2);assert not thread.is_alive() and not thread_errors,(thread.is_alive(),thread_errors)
    ok=error is None if expected is None else error is not None and expected in error
    report={'status':'PASS' if ok else 'FAIL','case':out.name,'mutation':mutation,'expected':expected,'error':error,
            'production_entrypoint':'process_census','helper_or_consumer_mocks':False,'topology':'synthetic proc view; live child stat/PID unmocked','mountrows_source_PIDstart':positive['source_PIDstart']}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    if not ok:raise RuntimeError('first affected alias fixture failure: '+repr(report))
    return report


def container_negative(out):
    out.mkdir();m=load();cid='a'*64
    # Only external Docker response transport is synthetic; actual current-reader
    # task_view + production container_census/canonical_path run unmocked.
    queue=[(cid+'\n').encode(),json.dumps([{'Id':cid,'Mounts':[{'Source':m.SCRATCH_ALIAS+'/native-application-start-retained-20260908-1'}],'State':{'Status':'exited'}}]).encode()]
    m.run=lambda argv,data=None:queue.pop(0)
    error=None
    try:m.container_census()
    except BaseException as exc:error=repr(exc)
    assert error and ('authenticated mapping' in error or 'candidate ancestry' in error),error
    report={'status':'PASS','case':'container-source-alias-refusal','error':error,'production_entrypoint':'container_census','only_transport_mocked':True}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False)
    results=[];child=subprocess.Popen(['/usr/bin/python3','-I','-c','import time; time.sleep(25)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    result={}
    # Wait for the deliberately idle identity child to reach its bounded sleep,
    # so startup state transitions don't masquerade as alias behavior.
    for attempt in range(100):
        state=Path('/proc',str(child.pid),'stat').read_bytes().rpartition(b') ')[2].split()[0]
        if state==b'S':break
        time.sleep(0.002)
    else:raise RuntimeError('idle identity child did not settle')
    try:
        for i,view in enumerate(ORACLE['positive_views']):results.append(scenario(out/('positive-real-view-%02d'%i),child.pid,view))
        view=ORACLE['positive_views'][0]
        mutations=('root','source','device','type','destination','access','propagation','shadow','unknown-namespace','alias-cwd','alias-root','alias-exe','alias-file-FD','alias-directory-FD','alias-mapped-path','FD-inode','mapped-inode','changed-task-namespace-during-census','changed-mountinfo-during-census')
        for case in mutations:results.append(scenario(out/case,child.pid,view,case))
        results.append(container_negative(out/'container-source-alias-refusal'))
        result={'status':'PASS_AFFECTED_ALIAS_ENTRYPOINT_SYNTHETIC_ONLY','cases':results,'interpreter':sys.executable,'version':sys.version,'actual_setns_or_mount':False,'root_observer_replayed':False,'unchanged_old_corpus_replayed':False}
    except BaseException as exc:
        result={'status':'FAIL_PRESERVED','cases':results,'error':repr(exc)}
        raise
    finally:
        if child.poll() is None:child.terminate()
        code=child.wait(timeout=3);result['idle_live_PID_child_joined']=True;result['idle_child_returncode']=code
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(results),'version':sys.version.split()[0],'idle_child_joined':True}))


if __name__=='__main__':main()
