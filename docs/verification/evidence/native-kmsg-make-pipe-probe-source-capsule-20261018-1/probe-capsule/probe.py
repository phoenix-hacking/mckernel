#!/usr/bin/env python3
"""One pinned-tool recursive pipe-jobserver observation, never target compilation."""
import argparse,fcntl,hashlib,json,os,re,signal,stat,subprocess,time
from pathlib import Path
IMAGE='sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d'
SOURCE=Path('/probe');WORK=Path('/work');EVIDENCE=WORK/'evidence'
ARGV=['/usr/bin/make','--jobserver-style=pipe','-j2','-f','/probe/Makefile','all']
CAP=1024*1024

def need(ok,message):
    if not ok:raise ValueError(message)

def identity(st):
    return dict(device=st.st_dev,inode=st.st_ino,mode=st.st_mode,nlink=st.st_nlink,uid=st.st_uid,gid=st.st_gid,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns)

def read_plain(path,limit):
    # Parent roots are fixed canonical no-symlink mountpoints; pin the final
    # regular file and reject FIFO/symlink/hardlink before reading any bytes.
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=limit,'bounded regular input')
        data=b''
        while True:
            chunk=os.read(fd,min(65536,limit+1-len(data)))
            if not chunk:break
            data+=chunk;need(len(data)<=limit,'input cap')
        need(identity(os.fstat(fd))==identity(before)==identity(path.lstat()),'input identity changed')
        return data,identity(before)
    finally:os.close(fd)

def sha(data):return hashlib.sha256(data).hexdigest()

def write_json(path,value):
    raw=(json.dumps(value,indent=2)+'\n').encode();need(len(raw)<=CAP,'JSON cap')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

def inventory(root):
    need(root.is_dir() and root.resolve()==root,'canonical inventory root')
    rows=[]
    for path in sorted(root.rglob('*')):
        s=path.lstat();need(not stat.S_ISLNK(s.st_mode),'symlink inventory')
        if stat.S_ISDIR(s.st_mode):continue
        need(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'nonregular/hardlink inventory; no FIFO exception')
        rows.append(dict(path=str(path.relative_to(root)),identity=identity(s)))
    return rows

def prerequisites():
    need(Path(__file__)==SOURCE/'probe.py' and os.getuid()==os.geteuid()==1000,'fixed unprivileged probe source')
    need(os.sched_getaffinity(0)=={2,3,4,5},'reviewed existing container affinity')
    need(SOURCE.resolve()==SOURCE and WORK.resolve()==WORK and SOURCE!=WORK,'fixed canonical mounts')
    need({r['path'] for r in inventory(SOURCE)}=={'Makefile','probe.py'},'exact two source files')

def child(label):
    prerequisites();need(label in ('a','b'),'fixed recipe child')
    flags=os.environ.get('MAKEFLAGS','');parts=flags.split();auth=[p for p in parts if p.startswith('--jobserver-auth=')]
    need(len(auth)==1 and re.fullmatch(r'--jobserver-auth=[0-9]+,[0-9]+',auth[0]) is not None,'actual numeric pipe jobserver auth required')
    need('fifo:' not in flags and os.environ.get('MAKELEVEL')=='2','recursive make level/style')
    r,w=map(int,auth[0].split('=',1)[1].split(','));need(r!=w and min(r,w)>=3,'jobserver descriptor pair')
    rows=[]
    for fd,mode in [(r,os.O_RDONLY),(w,os.O_WRONLY)]:
        st=os.fstat(fd);link=os.readlink('/proc/self/fd/'+str(fd))
        need(stat.S_ISFIFO(st.st_mode) and re.fullmatch(r'pipe:\[[0-9]+\]',link) is not None,'anonymous pipe descriptor required')
        need(fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==mode,'pipe endpoint access mode')
        rows.append(dict(fd=fd,device=st.st_dev,inode=st.st_ino,link=link,access_mode=mode))
    need(rows[0]['link']==rows[1]['link'] and rows[0]['inode']==rows[1]['inode'],'paired pipe ends')
    # Observe descriptors only. Never consume or return jobserver tokens.
    row=dict(label=label,pid=os.getpid(),parent_pid=os.getppid(),makelevel=2,makeflags=flags,endpoints=rows,pipe_jobserver_observed=True)
    write_json(EVIDENCE/('child-'+label+'.json'),row)

def captured(label,argv,environment,*,wall=10):
    outpath=EVIDENCE/(label+'.stdout');errpath=EVIDENCE/(label+'.stderr');started=time.monotonic();p=None;timed_out=False;actions=[]
    with outpath.open('xb') as out,errpath.open('xb') as err:
        try:
            p=subprocess.Popen(argv,cwd=WORK,env=environment,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            try:p.wait(timeout=wall)
            except subprocess.TimeoutExpired:timed_out=True
        finally:
            if p is not None and p.poll() is None:
                try:os.killpg(p.pid,signal.SIGTERM);actions.append('SIGTERM_owned_group')
                except ProcessLookupError:pass
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL_owned_group')
                    except ProcessLookupError:pass
                    p.wait()
            if p is not None:p.wait()
    group_absent=False
    try:os.killpg(p.pid,0)
    except ProcessLookupError:group_absent=True
    captures={}
    for role,path in [('stdout',outpath),('stderr',errpath)]:
        data,meta=read_plain(path,CAP);captures[role]=dict(path=str(path),bytes=len(data),sha256=sha(data))
    record=dict(argv=argv,pid=p.pid,returncode=p.returncode,direct_child_joined=True,owned_group_absent=group_absent,seconds=time.monotonic()-started,timed_out=timed_out,cleanup_actions=actions,captures=captures)
    write_json(EVIDENCE/(label+'.status.json'),record)
    need(not timed_out and p.returncode==0 and group_absent,'probe child failure/uncertain group; preserve original output')
    return record

def execute():
    prerequisites();need({p.name for p in WORK.iterdir()}=={'home','tmp'},'fresh work layout')
    for n in ('home','tmp'):need((WORK/n).is_dir() and not any((WORK/n).iterdir()),'empty private home/tmp')
    source_refs={}
    for n in ('probe.py','Makefile'):
        data,ident=read_plain(SOURCE/n,CAP);source_refs[n]=dict(bytes=len(data),sha256=sha(data),identity=ident)
    make,make_identity=read_plain(Path('/usr/bin/make'),8*1024**2)
    before=inventory(WORK);EVIDENCE.mkdir(mode=0o700)
    result=dict(status='FAIL',image_id=IMAGE,image_identity_authenticated=False,observation_only=True,make_path='/usr/bin/make',make_sha256=sha(make),make_identity=make_identity,source_refs=source_refs,argv=ARGV,inventory_before=before,pipe_jobserver_observed=False,fifo_count=None,returncode=None,direct_child_joined=False,native_acceptance=False,target_build=False)
    environment=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',TZ='UTC',BASH_ENV='',ENV='',GNUMAKEFLAGS='',MAKEFILES='',MAKEFLAGS='',MAKEOVERRIDES='',MFLAGS='',LD_LIBRARY_PATH='',LD_PRELOAD='',HOME='/work/home',TMPDIR='/work/tmp')
    try:
        version=captured('make-version',['/usr/bin/make','--version'],environment,wall=5)
        version_raw,_=read_plain(EVIDENCE/'make-version.stdout',CAP);need(version_raw.startswith(b'GNU Make '),'GNU make actual version')
        result['make_version']=version_raw.decode('utf-8');result['make_version_status']=version
        command=captured('recursive-pipe',ARGV,environment);result.update(returncode=command['returncode'],direct_child_joined=command['direct_child_joined'],make_status=command)
        children=[]
        for label in ('a','b'):
            raw,_=read_plain(EVIDENCE/('child-'+label+'.json'),CAP);row=json.loads(raw);need(row['label']==label and row['pipe_jobserver_observed'] is True and row['makelevel']==2,'child observation')
            children.append(row)
        need(children[0]['pid']!=children[1]['pid'] and children[0]['parent_pid']!=children[1]['parent_pid'],'two distinct recursive branches')
        need(children[0]['endpoints'][0]['link']==children[1]['endpoints'][0]['link'],'same inherited jobserver pipe')
        after=inventory(WORK);need({r['path'] for r in after}=={'evidence/make-version.stdout','evidence/make-version.stderr','evidence/make-version.status.json','evidence/recursive-pipe.stdout','evidence/recursive-pipe.stderr','evidence/recursive-pipe.status.json','evidence/child-a.json','evidence/child-b.json'},'exact probe files; no jobserver filesystem node')
        current,ident=read_plain(Path('/usr/bin/make'),8*1024**2);need(sha(current)==result['make_sha256'] and ident==make_identity,'make executable changed')
        for n,ref in source_refs.items():
            data,ident=read_plain(SOURCE/n,CAP);need(sha(data)==ref['sha256'] and ident==ref['identity'],'probe source changed')
        result.update(status='PASS_RECURSIVE_MAKE_PIPE_OBSERVATION',pipe_jobserver_observed=True,fifo_count=0,children=children,inventory_after=after)
    except BaseException as e:result['error']=type(e).__name__+': '+str(e)
    finally:write_json(EVIDENCE/'probe-result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--child',choices=('a','b'));a=p.parse_args()
    if a.child:child(a.child);return 0
    r=execute();print(json.dumps({k:r[k] for k in ('status','pipe_jobserver_observed','fifo_count','target_build')}));return int(r['status']!='PASS_RECURSIVE_MAKE_PIPE_OBSERVATION')
if __name__=='__main__':raise SystemExit(main())
