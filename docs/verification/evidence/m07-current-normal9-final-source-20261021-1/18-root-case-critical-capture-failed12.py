import hashlib,json,os,signal,stat,subprocess,time
from pathlib import Path
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def put(p,b):
 fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())

def write(p,v):put(p,canon(v))

def ref(p):return dict(path=str(p),sha256=digest(p))

def start(pid):return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]

def ident(s):return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)

def run(op):
 argv=op['argv'];outp=Path(op['stdout_path']);errp=Path(op['stderr_path']);sp=Path(op['status_path']);write(Path(str(sp)+'.command.json'),dict(argv=argv,role=op['role'],policy=ref(a.policy)));t=time.monotonic();observer_error=None;cs=None
 with outp.open('xb') as out,errp.open('xb') as err:
  child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  try:cs=start(child.pid);write(Path(str(sp)+'.child.json'),dict(pid=child.pid,start=cs,pgid=child.pid,argv=argv))
  except BaseException as e:observer_error=repr(e)
  rc=child.wait()
  out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno());held={k:ident(os.fstat(f.fileno())) for k,f in [('stdout',out),('stderr',err)]}
 streams={}
 for k,path in [('stdout',outp),('stderr',errp)]:
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   ss=os.fstat(fd);assert ident(ss)==held[k]==ident(os.stat(path,follow_symlinks=False));assert stat.S_ISREG(ss.st_mode) and ss.st_uid==1000 and ss.st_nlink==1 and stat.S_IMODE(ss.st_mode)==0o600 and ss.st_size<134217728
   with os.fdopen(os.dup(fd),'rb') as h:sha=hashlib.sha256(h.read()).hexdigest()
   streams[k]=dict(path=str(path),sha256=sha,metadata=ident(ss))
  finally:os.close(fd)
 row=dict(role=op['role'],argv=argv,pid=child.pid,start=cs,returncode=rc,direct_child_joined=True,observer_error=observer_error,elapsed_seconds=time.monotonic()-t,streams=streams);write(sp,row);results.append(row)
 assert rc==0 and observer_error is None,op['role']
 if op['role']=='postjoin-readback':
  summary=json.loads(errp.read_bytes())
  assert summary['status']=='PASS_CLEANUP_POSTJOIN_READBACK_ONLY' and summary['members']==5 and isinstance(summary['actual_object_rows'],list) and len(summary['actual_object_rows'])==24 and summary['application_acceptance'] is False,op['role']
 else:assert streams['stderr']['metadata']['size']==0,op['role']
 return row
