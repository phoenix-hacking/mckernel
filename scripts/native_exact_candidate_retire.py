#!/usr/bin/env python3
"""Fail-closed, callback-bound ordinary retirement template (never a CLI executor)."""
from __future__ import print_function
import argparse, ctypes, hashlib, io, json, os, stat, sys, time, tarfile, importlib.util
from datetime import datetime, timezone
from pathlib import Path

TERMINAL_CONTAINER_ID = 'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9'
RENAME_NOREPLACE = 1
OBSERVER_SOURCE = Path(__file__).resolve().parents[1] / 'docs/verification/evidence/native-exact-candidate-live-reference-observer-68cf089a-2.py'
class RetirementError(RuntimeError): pass
def fail(s): raise RetirementError(s)
def digest_bytes(b): return hashlib.sha256(b).hexdigest()
def exact_json(b):
    def unique(items):
        d = {}
        for k,v in items:
            if k in d: fail('duplicate JSON key: '+k)
            d[k] = v
        return d
    try: return json.loads(b.decode('utf8') if isinstance(b,bytes) else b, object_pairs_hook=unique)
    except (ValueError,UnicodeError,TypeError) as e: fail('invalid JSON: '+str(e))
def flags(directory=False, write=False):
    if not hasattr(os,'O_NOFOLLOW') or directory and not hasattr(os,'O_DIRECTORY'): fail('safe open unavailable')
    return (os.O_WRONLY if write else os.O_RDONLY)|os.O_NOFOLLOW|(os.O_DIRECTORY if directory else 0)|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NONBLOCK',0)
def kind(s):
    return 'directory' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'special'
def identity(s): return dict(device=int(s.st_dev),inode=int(s.st_ino),uid=int(s.st_uid),gid=int(s.st_gid),mode=stat.S_IMODE(s.st_mode),kind=kind(s),size=int(s.st_size))
def same(actual,wanted,root=False):
    fields=('device','inode','uid','gid','mode')
    if not isinstance(wanted,dict) or any(actual.get(k)!=wanted.get(k) for k in fields) or actual['kind'] != wanted.get('kind','directory' if root else None): fail(('root' if root else 'member')+' identity mismatch')
def safe_name(n):
    if not isinstance(n,str) or not n or n in ('.','..') or '/' in n or '\0' in n: fail('unsafe name')
def readfd(fd):
    a=[]
    while True:
        b=os.read(fd,1<<20)
        if not b:return b''.join(a)
        a.append(b)
def stable_read(path):
    fd=os.open(os.fspath(path),flags())
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):fail('artifact is not regular')
        data=readfd(fd);after=os.fstat(fd);named=os.stat(os.fspath(path),follow_symlinks=False)
        if identity(before)!=identity(after) or identity(named)!=identity(after):fail('artifact changed while read')
        return data
    finally:os.close(fd)
def _archive_module():
    path=Path(__file__).resolve().with_name('native_exact_candidate_retention_archive.py')
    spec=importlib.util.spec_from_file_location('_retention_archive',str(path));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def verify_archive_bytes(capsule_bytes,manifest_bytes):
    """Use the public byte verifier when present; fallback never reopens input paths."""
    module=_archive_module(); public=getattr(module,'verify_archive_bytes',None)
    if public is not None:
        try:return public(capsule_bytes,manifest_bytes)
        except BaseException as e:fail('public archive byte verification failed: '+str(e))
    try:
        manifest=exact_json(manifest_bytes); rows,selected=module._selection(manifest)
        with tarfile.open(fileobj=io.BytesIO(capsule_bytes),mode='r:') as archive:
            infos=archive.getmembers(); expected={'manifest.json'}|{root+'/'+path for root,path in selected}
            if not infos or infos[0].name!='manifest.json' or {x.name for x in infos}!=expected:fail('capsule byte membership mismatch')
            source=archive.extractfile(infos[0])
            if source is None or source.read()!=manifest_bytes:fail('capsule embedded manifest mismatch')
            for info in infos[1:]:
                root,path=info.name.split('/',1); row=rows[(root,path)]
                if row['type']=='directory':
                    if not info.isdir() or info.mode!=row['mode'] or info.uid!=row['uid'] or info.gid!=row['gid'] or info.size:fail('capsule directory mismatch')
                else:
                    source=archive.extractfile(info)
                    if source is None or not info.isfile() or info.mode!=row['mode'] or info.uid!=row['uid'] or info.gid!=row['gid'] or digest_bytes(source.read())!=row['sha256']:fail('capsule member mismatch')
    except (tarfile.TarError,KeyError,ValueError) as e:fail('capsule byte verification failed: '+str(e))
def full_write(fd,data,write=os.write):
    at=0
    while at<len(data):
        n=write(fd,data[at:])
        if not isinstance(n,int) or n<=0 or n>len(data)-at: fail('short or invalid write')
        at+=n
def fsync_dir(x):
    close=not isinstance(x,int); fd=os.open(os.fspath(x),flags(True)) if close else x
    try: os.fsync(fd)
    finally:
        if close:os.close(fd)
def exclusive_fd(path):
    fd=os.open(os.fspath(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0),0o600)
    try: fsync_dir(os.path.dirname(os.path.abspath(os.fspath(path)))); return fd
    except BaseException: os.close(fd); raise
def full_write_json(path,value):
    data=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode(); fd=exclusive_fd(path)
    try: full_write(fd,data); os.fsync(fd)
    finally: os.close(fd)
    return digest_bytes(data)
write_durable=full_write_json
class Journal:
    def __init__(self,path): self.path=os.fspath(path);self.fd=exclusive_fd(path)
    def write(self,phase,**kw):
        data=(json.dumps(dict(phase=phase,**kw),sort_keys=True,separators=(',',':'))+'\n').encode();full_write(self.fd,data);os.fsync(self.fd)
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None
def root_identity(path):
    fd=os.open(os.fspath(path),flags(True))
    try:
        x=identity(os.fstat(fd));
        if x['kind']!='directory':fail('root is not directory')
        return x
    finally:os.close(fd)
def open_checked(parent,name,wanted):
    safe_name(name);same(identity(os.stat(name,dir_fd=parent,follow_symlinks=False)),wanted)
    fd=os.open(name,flags(wanted.get('kind')=='directory'),dir_fd=parent)
    try:
        same(identity(os.fstat(fd)),wanted);same(identity(os.stat(name,dir_fd=parent,follow_symlinks=False)),wanted);return fd
    except BaseException:os.close(fd);raise
def inventory_root(path):
    rootfd=os.open(os.fspath(path),flags(True))
    try:
        root=identity(os.fstat(rootfd)); rows=[]
        if root['kind']!='directory':fail('root type')
        def walk(fd,prefix):
            for name in sorted(os.listdir(fd)):
                safe_name(name); rel=name if not prefix else prefix+'/'+name; row=identity(os.stat(name,dir_fd=fd,follow_symlinks=False));row['path']=rel
                if row['kind']=='special':fail('special member: '+rel)
                if row['kind']=='symlink':
                    row['target']=os.readlink(name,dir_fd=fd);row['sha256']=digest_bytes(os.fsencode(row['target']));rows.append(row);continue
                child=open_checked(fd,name,row)
                try:
                    if row['kind']=='file':
                        if os.fstat(child).st_nlink!=1:fail('hardlink alias: '+rel)
                        row['sha256']=digest_bytes(readfd(child));same(identity(os.fstat(child)),row)
                    else:walk(child,rel)
                    same(identity(os.stat(name,dir_fd=fd,follow_symlinks=False)),row)
                finally:os.close(child)
                rows.append(row)
        walk(rootfd,'');return dict(root=root,members=sorted(rows,key=lambda x:x['path']))
    finally:os.close(rootfd)
def member_map(rows):
    if not isinstance(rows,list):fail('released member map missing')
    d={}
    for r in rows:
        if not isinstance(r,dict) or r.get('kind') not in ('file','directory','symlink'):fail('released special member')
        p=r.get('path')
        if not isinstance(p,str) or not p or p.startswith('/') or '..' in p.split('/') or p in d:fail('bad released member map')
        d[p]=r
    return d
def under(path,parent):
    return os.path.commonpath((path,parent))==parent
def artifact_paths(seal,roots):
    paths=[]
    for key in ('retention_manifest_path','capsule_path'):
        value=seal.get(key)
        if not isinstance(value,str) or not os.path.isabs(value):fail('absolute retained artifact path required')
        value=os.path.abspath(value)
        try:
            if stat.S_ISLNK(os.lstat(value).st_mode):fail('retained artifact symlink')
        except OSError as e:fail('retained artifact unavailable: '+str(e))
        if any(under(value,os.path.abspath(root)) for root in roots):fail('retained artifact is inside candidate')
        paths.append(value)
    if paths[0]==paths[1]:fail('retention artifacts alias')
    return paths
def manifest_authority(release,roots):
    seal=release['sealed'];manifest_path,capsule_path=artifact_paths(seal,roots)
    manifest_bytes,capsule_bytes=stable_read(manifest_path),stable_read(capsule_path)
    for key,data in (('retention_manifest_sha256',manifest_bytes),('retention_manifest_pushed_sha256',manifest_bytes),('retention_manifest_fetched_sha256',manifest_bytes),('capsule_sha256',capsule_bytes),('capsule_pushed_sha256',capsule_bytes),('capsule_fetched_sha256',capsule_bytes)):
        if digest_bytes(data)!=seal.get(key):fail('retention artifact hash mismatch: '+key)
    manifest=exact_json(manifest_bytes)
    if not isinstance(manifest,dict) or manifest.get('format')!='native-exact-candidate-retention-v1':fail('retention planner manifest mismatch')
    verify_archive_bytes(capsule_bytes,manifest_bytes)
    return manifest
def release_roots(release,roots):
    if not isinstance(release,dict) or release.get('schema')!='mckernel.ordinary-retirement-release.v1':fail('unreleased retirement')
    seal=release.get('sealed')
    required=('retention_manifest_sha256','retention_manifest_pushed_sha256','retention_manifest_fetched_sha256','capsule_sha256','capsule_pushed_sha256','capsule_fetched_sha256')
    if not isinstance(seal,dict) or not all(isinstance(seal.get(k),str) and len(seal[k])==64 for k in required):fail('retention/capsule binding')
    if seal['retention_manifest_sha256']!=seal['retention_manifest_pushed_sha256'] or seal['retention_manifest_sha256']!=seal['retention_manifest_fetched_sha256'] or seal['capsule_sha256']!=seal['capsule_pushed_sha256'] or seal['capsule_sha256']!=seal['capsule_fetched_sha256']:fail('pushed/fetched retention binding')
    if not isinstance(release.get('operational_exclusion'),str) or not release['operational_exclusion']:fail('operational exclusion binding')
    rs=release.get('roots')
    if not isinstance(rs,list) or len(rs)!=2 or len(roots)!=2:fail('exactly two released roots')
    manifest=manifest_authority(release,roots); answer=[]
    if not isinstance(manifest.get('roots'),list) or not isinstance(manifest.get('entries'),list) or len(manifest['roots'])!=2:fail('planner root/entry authority missing')
    manifest_roots={x.get('name'):x for x in manifest['roots'] if isinstance(x,dict)}
    if set(manifest_roots)!={'candidate','metadata-backup'} or len(manifest_roots)!=2:fail('planner root names')
    manifest_entries={}
    for entry in manifest['entries']:
        if not isinstance(entry,dict) or entry.get('root') not in manifest_roots or not isinstance(entry.get('path'),str) or (entry['root'],entry['path']) in manifest_entries:fail('planner entry map')
        manifest_entries[(entry['root'],entry['path'])]=entry
    for supplied,r,label in zip(roots,rs,('candidate','metadata-backup')):
        p=os.path.abspath(os.fspath(supplied))
        authority=manifest_roots[label]
        if not isinstance(r,dict) or r.get('path')!=p or authority.get('path')!=p or not isinstance(authority.get('identity'),dict):fail('released/manifest root path')
        safe_name(r.get('quarantine_name'));parent=os.path.dirname(p)
        for ownership in ('quarantine_uid','quarantine_gid'):
            if not isinstance(r.get(ownership),int) or r[ownership] < 0: fail('quarantine ownership binding')
        if os.path.basename(p)==r['quarantine_name']:fail('nonfresh quarantine')
        root_authority=authority['identity']
        if any(r.get('root',{}).get(ours)!=root_authority.get(theirs) for ours,theirs in (('device','dev'),('inode','inode'),('uid','uid'),('gid','gid'),('mode','mode'))):fail('released root differs from planner')
        released=member_map(r.get('members')); planned={path:entry for (which,path),entry in manifest_entries.items() if which==label}
        if set(released)!=set(planned):fail('released/planner entry set mismatch')
        for path,row in released.items():
            plan=planned[path]; mapped={'directory':'directory','regular':'file','symlink':'symlink'}.get(plan.get('type'))
            if row.get('kind')!=mapped or any(row.get(k)!=plan.get(k) for k in ('path','mode','uid','gid','size')):fail('released/planner member metadata mismatch')
            if mapped=='file' and row.get('sha256')!=plan.get('sha256'):fail('released/planner regular digest mismatch')
            if mapped=='symlink' and row.get('target')!=plan.get('target'):fail('released/planner symlink mismatch')
        same(root_identity(parent),r.get('parent'),True);same(root_identity(p),r.get('root'),True)
        inv=inventory_root(p)
        if inv['root']!=r['root'] or inv['members']!=r.get('members'):fail('sealed root/member mismatch')
        member_map(r['members']);answer.append(dict(path=p,parent=parent,record=r,quarantine=os.path.join(parent,r['quarantine_name'])))
    if len({x['path'] for x in answer})!=2 or len({x['quarantine'] for x in answer})!=2 or under(answer[0]['path'],answer[1]['path']) or under(answer[1]['path'],answer[0]['path']):fail('root/quarantine containment or alias')
    return answer
def rename_noreplace(parent,old,new):
    fn=getattr(ctypes.CDLL(None,use_errno=True),'renameat2',None)
    if fn is None:fail('renameat2 unavailable')
    fn.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint);fn.restype=ctypes.c_int
    if fn(parent,os.fsencode(old),parent,os.fsencode(new),RENAME_NOREPLACE)!=0:
        e=ctypes.get_errno();raise OSError(e,os.strerror(e),new)
def quarantine_target(record):
    """The exact descriptor-visible identity required after the transition."""
    if record.get('quarantine_mode') is None:return dict(record['root'])
    if record['quarantine_mode']!=0o700:fail('unreleased quarantine chmod')
    return dict(record['root'],uid=record['quarantine_uid'],gid=record['quarantine_gid'],mode=0o700)
def observer_member_identity(row):
    kinds={'directory':stat.S_IFDIR,'file':stat.S_IFREG,'symlink':stat.S_IFLNK}
    try:return [row['device'],row['inode'],row['uid'],row['gid'],kinds[row['kind']],row['mode']]
    except (KeyError,TypeError):fail('released observer member identity')
def quarantine(item,journal):
    r=item['record'];fd=os.open(item['parent'],flags(True))
    try:
        same(identity(os.fstat(fd)),r['parent'],True);old=os.path.basename(item['path']);new=r['quarantine_name']
        same(identity(os.stat(old,dir_fd=fd,follow_symlinks=False)),r['root'],True)
        try:os.stat(new,dir_fd=fd,follow_symlinks=False);fail('quarantine collision')
        except FileNotFoundError:pass
        target=quarantine_target(r)
        journal.write('quarantine-before',path=item['path'],quarantine=item['quarantine'],released_root=r['root'],ownership_transition_target=target);rename_noreplace(fd,old,new);fsync_dir(fd)
        same(identity(os.stat(new,dir_fd=fd,follow_symlinks=False)),r['root'],True)
        if r.get('quarantine_mode') is not None:
            rootfd=open_checked(fd,new,r['root'])
            try:
                os.fchown(rootfd,r['quarantine_uid'],r['quarantine_gid'])
                same(identity(os.fstat(rootfd)),dict(r['root'],uid=r['quarantine_uid'],gid=r['quarantine_gid']),True)
                os.fchmod(rootfd,0o700);os.fsync(rootfd)
            finally:os.close(rootfd)
            fsync_dir(fd)
            rootfd=open_checked(fd,new,target)
            try: item['quarantine_root']=identity(os.fstat(rootfd))
            finally: os.close(rootfd)
            same(identity(os.stat(new,dir_fd=fd,follow_symlinks=False)),item['quarantine_root'],True)
        else:
            item['quarantine_root']=dict(r['root'])
        journal.write('quarantine-after',path=item['path'],quarantine=item['quarantine'],released_root=r['root'],ownership_transition_target=target,observed_quarantine_root=item['quarantine_root'])
    finally:os.close(fd)
def clean_list(x,k):
    if not isinstance(x.get(k),list) or x[k]:fail('observer sticky '+k)
def parse_utc(value):
    if not isinstance(value,str) or not value.endswith('Z'):fail('observer UTC scalar')
    try:return datetime.fromisoformat(value[:-1]+'+00:00').timestamp()
    except ValueError:fail('observer UTC scalar')
def current_boot_id():
    try:return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError:fail('current boot id unavailable')
def validate_observation(v,binding,quarantines,members,root_ids,started,ended):
    if not isinstance(v,dict) or v.get('schema')!='mckernel.read-only-live-reference-snapshot.v7' or v.get('status')!='PASS' or v.get('scan_complete') is not True or v.get('failure') is not None:fail('observer v7 scalar')
    actual_source=digest_bytes(stable_read(OBSERVER_SOURCE))
    if v.get('observer_sha256')!=actual_source or binding.get('observer_sha256')!=actual_source or v.get('boot_id')!=binding.get('boot_id') or v.get('boot_id')!=current_boot_id():fail('observer source/boot')
    if not isinstance(v.get('observer_pid'),int) or v['observer_pid']<=0 or not isinstance(v.get('observer_starttime'),str):fail('observer process identity')
    observed_start,observed_end=parse_utc(v.get('started_at_utc')),parse_utc(v.get('ended_at_utc'))
    if observed_end<observed_start or observed_start<started-2 or observed_end>ended+2:fail('stale observer record')
    clean_list(v,'persistent_tree_revalidation_failures')
    for k in ('permission_denials','target_references','tree_revalidation_failures','unscanned_final_identities'):
        if k in v:clean_list(v,k)
    if 'complete_mount_proofs' in v and v['complete_mount_proofs'] is not True:fail('mount proof')
    rows=v.get('roots');rounds=v.get('rounds')
    if not isinstance(rows,list) or len(rows)!=2 or not isinstance(rounds,list) or not 2<=len(rounds)<=5:fail('observer roots/rounds')
    if not isinstance(v.get('tree_observation_transients'),list):fail('observer transients missing')
    for row,p,m,rootid in zip(rows,quarantines,members,root_ids):
        if row.get('path')!=p or row.get('mode')!='0700' or row.get('tree_member_identities')!=m or not isinstance(row.get('device_number'),int) or not isinstance(row.get('inode'),int) or row.get('uid')!=rootid['uid'] or row.get('gid')!=rootid['gid']:fail('observer root/member proof')
        root_member=observer_member_identity(rootid)
        if [row['device_number'],row['inode']]!=[rootid['device'],rootid['inode']] or root_member not in m:fail('observer root identity mismatch')
    for num,row in enumerate(rounds,1):
        if not isinstance(row,dict) or row.get('round')!=num:fail('round sequence')
        for k in ('target_references','permission_denials','tree_revalidation_failures'):clean_list(row,k)
        if not isinstance(row.get('unscanned_final_identities'),list) or not isinstance(row.get('unresolved_churn'),list) or not isinstance(row.get('closure_nonconvergent'),bool) or row.get('complete_mount_proofs') is not True:fail('round closure')
    for row in rounds[-2:]:
        if row.get('clean') is not True or row['unscanned_final_identities'] or row['unresolved_churn'] or row['closure_nonconvergent']:fail('final rounds not clean')
def paths_intersect(a,b):
    if not isinstance(a,str) or not isinstance(b,str) or not a.startswith('/') or not b.startswith('/') or '\0' in a+b:fail('Docker mount path')
    a,b=os.path.normpath(a),os.path.normpath(b);return os.path.commonpath((a,b)) in (a,b)
def mount_paths(row):
    mounts=row.get('Mounts',row.get('mounts',[]))
    if not isinstance(mounts,list):fail('Docker mount list')
    return [m[k] for m in mounts if isinstance(m,dict) for k in ('Source','Destination') if k in m]
def validate_docker_census(census,docker,protected):
    if not isinstance(census,dict) or not isinstance(census.get('ps_all'),list) or not isinstance(census.get('inspect'),list):fail('Docker census missing')
    ids=census['ps_all'];rows=census['inspect']
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or len(x)!=64 for x in ids) or len(rows)!=len(ids) or {x.get('Id') for x in rows if isinstance(x,dict)}!=set(ids):fail('Docker reconciliation')
    terminal=docker.get('terminal') if isinstance(docker,dict) else None
    terminal_rows=[x for x in rows if isinstance(x,dict) and x.get('Id')==TERMINAL_CONTAINER_ID]
    if not isinstance(terminal,dict) or terminal.get('id')!=TERMINAL_CONTAINER_ID or len(terminal_rows)!=1:fail('required terminal container missing')
    exact=terminal_rows[0]; state=exact.get('State'); restart=exact.get('HostConfig',{}).get('RestartPolicy')
    if not isinstance(state,dict) or state.get('Status')!='exited' or any(state.get(k) is not False for k in ('Running','Paused','Restarting','Dead')) or state.get('Pid')!=0 or state.get('ExitCode')!=1 or state.get('OOMKilled') is not False or restart not in ({'Name':'no','MaximumRetryCount':0},{'Name':'no'}) or exact.get('HostConfig',{}).get('AutoRemove') is not False:fail('terminal state mutation')
    expected=terminal.get('exact_config')
    if not isinstance(expected,dict) or set(expected)!={'Config','HostConfig','Mounts'} or any(exact.get(k)!=v for k,v in expected.items()) or exact.get('State')!=terminal.get('state'):fail('terminal config mutation')
    config,host=expected['Config'],expected['HostConfig']
    if not isinstance(config,dict) or not isinstance(host,dict) or any(k not in config for k in ('Image','User','Cmd')) or any(k not in host for k in ('SecurityOpt','Privileged','ReadonlyRootfs','NanoCpus','Memory','PidsLimit','CpusetCpus','RestartPolicy','AutoRemove')):fail('incomplete released container configuration')
    for row in rows:
        if any(paths_intersect(p,q) for p in mount_paths(row) for q in protected):
            if row.get('Id')!=TERMINAL_CONTAINER_ID:fail('unexpected candidate container')
def verify_entry(fd,name,wanted,dev):
    actual=identity(os.stat(name,dir_fd=fd,follow_symlinks=False));same(actual,wanted)
    if actual['device']!=dev or actual['kind']=='special':fail('cross-device/special member')
    if actual['kind']=='file':
        c=open_checked(fd,name,wanted)
        try:
            if os.fstat(c).st_nlink!=1 or digest_bytes(readfd(c))!=wanted.get('sha256'):fail('file changed/hardlinked')
            same(identity(os.fstat(c)),wanted)
        finally:os.close(c)
    elif actual['kind']=='symlink':
        target=os.readlink(name,dir_fd=fd)
        if target!=wanted.get('target') or digest_bytes(os.fsencode(target))!=wanted.get('sha256'):fail('symlink changed')
    return actual
def delete_verified(fd,expected,prefix,dev,journal,rootname,wanted_dir):
    same(identity(os.fstat(fd)),wanted_dir,True);direct={x[len(prefix):].split('/',1)[0] for x in expected if x.startswith(prefix)}
    if set(os.listdir(fd))!=direct:fail('member set changed')
    for name in sorted(direct):
        rel=prefix+name;wanted=expected[rel];actual=verify_entry(fd,name,wanted,dev)
        if actual['kind']=='directory':
            c=open_checked(fd,name,wanted)
            try:
                delete_verified(c,expected,rel+'/',dev,journal,rootname,wanted);same(identity(os.fstat(c)),wanted);same(identity(os.stat(name,dir_fd=fd,follow_symlinks=False)),wanted)
                journal.write('delete-entry-before',root=rootname,path=rel,operation='rmdir');same(identity(os.fstat(c)),wanted);same(identity(os.stat(name,dir_fd=fd,follow_symlinks=False)),wanted);os.rmdir(name,dir_fd=fd);fsync_dir(fd);journal.write('delete-entry-after',root=rootname,path=rel,operation='rmdir')
            finally:os.close(c)
        else:
            journal.write('delete-entry-before',root=rootname,path=rel,operation='unlink');verify_entry(fd,name,wanted,dev);os.unlink(name,dir_fd=fd);fsync_dir(fd);journal.write('delete-entry-after',root=rootname,path=rel,operation='unlink')
    same(identity(os.fstat(fd)),wanted_dir,True)
def survivors(items,claim,journal,evidence): return dict(originals={x['path']:os.path.lexists(x['path']) for x in items},quarantines={x['quarantine']:os.path.lexists(x['quarantine']) for x in items},claim=os.path.lexists(claim),journal=os.path.lexists(journal),evidence=os.path.lexists(evidence))
def remove_root(item,journal):
    r=item['record'];p=os.open(item['parent'],flags(True))
    try:
        same(identity(os.fstat(p)),r['parent'],True)
        wanted_root=item.get('quarantine_root',r['root'])
        fd=open_checked(p,r['quarantine_name'],wanted_root)
        try:
            delete_verified(fd,member_map(r['members']),'',r['root']['device'],journal,item['quarantine'],wanted_root)
            if os.listdir(fd):fail('root not empty')
            same(identity(os.fstat(fd)),wanted_root,True);same(identity(os.stat(r['quarantine_name'],dir_fd=p,follow_symlinks=False)),wanted_root,True)
            journal.write('root-rmdir-before',root=item['quarantine']);same(identity(os.fstat(p)),r['parent'],True);same(identity(os.stat(r['quarantine_name'],dir_fd=p,follow_symlinks=False)),wanted_root,True);os.rmdir(r['quarantine_name'],dir_fd=p);fsync_dir(p);journal.write('root-rmdir-after',root=item['quarantine'])
        finally:os.close(fd)
    finally:os.close(p)
def retire(roots,release,claim_path,journal_path,evidence_path,observer_runner,docker_census):
    items=release_roots(release,roots)
    for x in (claim_path,journal_path,evidence_path):
        if os.path.lexists(x):fail('one-shot output exists: '+os.fspath(x))
    j=Journal(journal_path)
    try:
        rsha=digest_bytes(json.dumps(release,sort_keys=True,separators=(',',':')).encode());claim=dict(schema='mckernel.ordinary-retirement-claim.v1',release_sha256=rsha,created=int(time.time()),roots=[x['path'] for x in items])
        j.write('journal-created',survivors=survivors(items,claim_path,journal_path,evidence_path));full_write_json(claim_path,claim)
        with open(claim_path,'rb') as claim_input: claim_digest=digest_bytes(claim_input.read())
        j.write('claim-created',claim_sha256=claim_digest)
        for x in items:quarantine(x,j)
        members=[sorted([observer_member_identity(x.get('quarantine_root',x['record']['root']))]+[observer_member_identity(r) for r in x['record']['members']]) for x in items];qs=[x['quarantine'] for x in items];rootids=[x.get('quarantine_root',x['record']['root']) for x in items]
        observed_at=time.time();observation=observer_runner(qs,members);observed_done=time.time();validate_observation(observation,release.get('observer',{}),qs,members,rootids,observed_at,observed_done);census=docker_census();validate_docker_census(census,release.get('docker',{}),[x['path'] for x in items]+qs)
        evidence=dict(schema='mckernel.ordinary-retirement-evidence.v1',release_sha256=rsha,operational_exclusion=release['operational_exclusion'],observation=observation,docker_census=census);full_write_json(evidence_path,evidence)
        with open(evidence_path,'rb') as evidence_input: evidence_digest=digest_bytes(evidence_input.read())
        j.write('proofs-passed',evidence_sha256=evidence_digest)
        for x in items:remove_root(x,j)
        result=dict(status='PASS',runtime_acceptance=False);j.write('terminal-success',result=result,survivors=survivors(items,claim_path,journal_path,evidence_path));return result
    except BaseException as e:
        try:j.write('terminal-failure',error=repr(e),survivors=survivors(items,claim_path,journal_path,evidence_path))
        except BaseException:pass
        raise
    finally:j.close()
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--release',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args(argv)
    if a.execute:fail('execution disabled: separately hash-bound packet must integrate callbacks')
    with open(a.release,'rb') as f:exact_json(f.read())
    print('validated template input; no roots were changed')
if __name__=='__main__':
    try:sys.exit(main())
    except RetirementError as e:print('FAIL CLOSED: '+str(e),file=sys.stderr);sys.exit(2)
