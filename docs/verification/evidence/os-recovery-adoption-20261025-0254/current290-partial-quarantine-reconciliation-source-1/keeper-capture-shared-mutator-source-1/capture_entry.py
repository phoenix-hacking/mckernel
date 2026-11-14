"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact keeper entry + one-shot command transport. No source selected from commands,
no signals, no watchdog kill, no cleanup/custody descriptor ownership here.
"""
import argparse,hashlib,importlib.util,json,math,os,resource,stat,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
WINDOW_ID='new18h-20261026-bf8b8eb1832f4c94a0166f20a95642ea'
CUTOFFS=[1793100290.0,882395.5689528405,897734.6960034363] # wall,monotonic,BOOTTIME: conservative exact parent
RESOURCES=dict(cpus='7',jobs=1,address_space_bytes=2147483648,file_size_bytes=33554432,core_bytes=0)
OPERATIONS={'RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY','ADOPT_AFTER_POSITIVE_RETIREMENT_CURRENT_ABSENCE','FINISH_REMAINING_SHARED_ONLY','RELEASE_KEEPER_AFTER_SHARED_TERMINAL'}
MAX_FILE=32<<20
class Refusal(ValueError):pass
def need(ok,why):
 if not ok:raise Refusal(why)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def parse(raw):
 def pairs(items):
  result={}
  for key,value in items:need(key not in result,'duplicate-json-key');result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Refusal('nonfinite-json')))
def read_file(path,maximum=MAX_FILE):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=maximum,'bounded-regular-file')
  raw=bytearray()
  while len(raw)<=before.st_size:
   block=os.read(fd,min(1<<20,before.st_size+1-len(raw)))
   if not block:break
   raw.extend(block)
  after=os.fstat(fd);fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  need(len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k) for k in fields),'file-raced')
  need((after.st_dev,after.st_ino)==(path.lstat().st_dev,path.lstat().st_ino),'file-path-raced')
  return bytes(raw),after
 finally:os.close(fd)
def pinned(ref):
 need(isinstance(ref,dict) and set(ref)=={'path','bytes','sha256'},'exact-reference-shape');raw,_=read_file(ref['path']);need(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'],'source-or-document-pin');return raw
def identity(path):
 path=Path(path);need(path.is_absolute() and not path.is_symlink(),'absolute-real-directory');m=path.stat();need(stat.S_ISDIR(m.st_mode),'directory-required');return [m.st_dev,m.st_ino,m.st_uid,m.st_gid,stat.S_IMODE(m.st_mode)]
def process_identity():
 raw=Path('/proc/self/stat').read_bytes();fields=raw.rpartition(b') ')[2].split();need(len(fields)>=50,'self-process-stat')
 return dict(pid=os.getpid(),starttime=fields[19].decode(),pgid=os.getpgrp(),command_hex=Path('/proc/self/cmdline').read_bytes().hex())
class Capture:
 def __init__(self,path):
  self.path=Path(path);self.before=identity(self.path);self.fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 def write(self,name,raw):
  need(Path(name).name==name and len(raw)<=MAX_FILE,'capture-name-or-size');need(identity(self.path)==self.before,'capture-directory-raced')
  fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
  try:
   if os.geteuid()==0:os.fchown(fd,1000,1000)
   view=memoryview(raw)
   while view:
    count=os.write(fd,view);need(count>0,'capture-write-no-progress');view=view[count:]
   os.fsync(fd)
  finally:os.close(fd)
  os.fsync(self.fd);return dict(path=str(self.path/name),bytes=len(raw),sha256=sha(raw))
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None

def clock_check(packet,now=None):
 need(packet.get('window_id')==WINDOW_ID,'exact-parent-window-id')
 need(packet.get('fixed_cutoffs')==CUTOFFS,'exact-parent-fixed-cutoffs')
 current=now or [time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
 need(all(type(x) in (int,float) and math.isfinite(x) and x<end for x,end in zip(current,CUTOFFS)) and len(current)==3,'fixed-parent-window-ended')
def verify_sources(packet,here=HERE):
 refs=packet.get('pipeline_sources');need(isinstance(refs,dict) and set(refs)=={'runtime','entry','outer'},'exact-three-pipeline-sources')
 for role,filename in [('runtime','runtime_pipeline.py'),('entry','capture_entry.py'),('outer','capture_outer.py')]:
  need(Path(refs[role]['path'])==here/filename,'fixed-pipeline-source-path');pinned(refs[role])
def verify_directories(packet,capture_path):
 names=['evidence_directory','entry_capture_directory','outer_capture_directory'];paths=[Path(packet[name]) for name in names]+[Path(packet['command_inbox']['path'])]
 need(all(path.is_absolute() and path==path.resolve() for path in paths),'canonical-pipeline-directories')
 need(len(set(map(str,paths)))==4 and all(a not in b.parents and b not in a.parents for i,a in enumerate(paths) for b in paths[i+1:]),'disjoint-pipeline-directories')
 need(len({tuple(identity(path)[:2]) for path in paths})==4,'distinct-pipeline-directory-identities')
 for name in names:need(identity(packet[name])==packet[name+'_identity'],'exact-directory-identity:'+name)
 need(Path(capture_path)==Path(packet['entry_capture_directory']),'exact-entry-capture-path')
 inbox=packet['command_inbox'];row=identity(inbox['path']);need(row==inbox['identity'] and row[2:4]==[0,0] and not row[4]&0o022,'root-sole-writer-inbox')
def verify_resources(packet):
 need(packet.get('resources')==RESOURCES,'exact-reviewed-resources');need(os.sched_getaffinity(0)=={7},'exact-control-cpu7')
 for key,limit in [('address_space_bytes',resource.RLIMIT_AS),('file_size_bytes',resource.RLIMIT_FSIZE),('core_bytes',resource.RLIMIT_CORE)]:need(resource.getrlimit(limit)==(RESOURCES[key],RESOURCES[key]),'exact-rlimit:'+key)
def payload_argv(packet_path,packet_sha,packet):
 return ['/home/holden/anaconda3/bin/python3.9','-I','-B',packet['pipeline_sources']['entry']['path'],'--packet',str(packet_path),'--packet-sha256',packet_sha,'--capture-directory',packet['entry_capture_directory']]
def verify_authorization(packet,raw,packet_path,envelope,here=HERE):
 need(isinstance(envelope,dict) and set(envelope)=={'root_grant','independent_execution_review'},'external-launch-authorization-envelope')
 grant=parse(pinned(envelope['root_grant']));review=parse(pinned(envelope['independent_execution_review']));need(grant.get('author')=='/root' and grant.get('operation')=='GRANT_EXACT_STANDBY_KEEPER_ONLY_NO_RETIREMENT','exact-standby-only-launch-grant')
 bindings=dict(launch_sha256=sha(raw),pipeline_sources=packet['pipeline_sources'],source_hashes=packet['source_hashes'],target=packet['old_actor'],fixed_cutoffs=packet['fixed_cutoffs'],resources=packet['resources'],entry_payload_argv=payload_argv(packet_path,sha(raw),packet),command_inbox=packet['command_inbox'],capture_directories={name:dict(path=packet[name],identity=packet[name+'_identity']) for name in ['evidence_directory','entry_capture_directory','outer_capture_directory']})
 for key,value in bindings.items():need(grant.get(key)==value,'launch-grant-binding:'+key)
 need(review.get('status')=='PASS_EXECUTION_RELEASE' and review.get('reviewer') not in (None,'','/root') and review.get('root_grant_sha256')==envelope['root_grant']['sha256'] and review.get('launch_sha256')==sha(raw) and review.get('pipeline_sources')==packet['pipeline_sources'],'exact-independent-launch-release')
 return dict(root_grant=envelope['root_grant'],independent_execution_review=envelope['independent_execution_review'],grant=grant)
class Inbox:
 def __init__(self,packet,capture,*,writer_uid=0):
  self.packet,self.capture=packet,capture;self.path=Path(packet['command_inbox']['path']);self.binding=packet['command_inbox']['identity'];self.sequence=0;self.writer_uid=writer_uid
  need(identity(self.path)==self.binding and self.binding[2]==writer_uid and not self.binding[4]&0o022,'exact-inbox-identity')
 def next_command(self):
  need(identity(self.path)==self.binding,'inbox-directory-raced');name='command-%06d.json'%self.sequence;path=self.path/name
  if not path.exists():clock_check(self.packet);return None
  raw,meta=read_file(path,1<<20);need(meta.st_uid==self.writer_uid and not stat.S_IMODE(meta.st_mode)&0o022,'root-command-owner-mode')
  seq=self.sequence;self.capture.write('COMMAND-%06d.raw.json'%seq,raw)
  self.capture.write('COMMAND-%06d.CONSUMED.json'%seq,canonical(dict(sequence=seq,source=str(path),bytes=len(raw),sha256=sha(raw),one_shot=True)))
  self.sequence+=1 # A bad consumed command never requeues/retries.
  clock_check(self.packet)
  need(raw.endswith(b'\n'),'command-newline-framing');command=parse(raw);need(isinstance(command,dict) and command.get('operation') in OPERATIONS,'unknown-or-malformed-command')
  return command # Runtime alone checks semantic Root grants/deadlines/actual PID.
def load_runtime(packet):
 ref=packet['pipeline_sources']['runtime'];raw=pinned(ref);module=type(sys)('_exact_keeper_runtime');module.__file__=ref['path'];exec(compile(raw,ref['path'],'exec'),module.__dict__);return module

def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--packet',type=Path,required=True);parser.add_argument('--packet-sha256',required=True);parser.add_argument('--capture-directory',type=Path,required=True);parser.add_argument('--authorization',type=Path,required=True);parser.add_argument('--authorization-sha256',required=True);args=parser.parse_args(argv)
 need(os.getuid()==os.geteuid()==0,'root-exact-entry-required');capture=Capture(args.capture_directory);entered=False
 try:
  raw,_=read_file(args.packet);capture.write('LAUNCH-PACKET.raw.json',raw);capture.write('ENTRY-PROCESS.json',canonical(dict(scope=SCOPE,process=process_identity(),argv=sys.argv)))
  need(sha(raw)==args.packet_sha256,'packet-sha256');packet=parse(raw);verify_sources(packet);verify_directories(packet,args.capture_directory);verify_resources(packet);clock_check(packet)
  auth_raw,_=read_file(args.authorization);capture.write('LAUNCH-AUTHORIZATION.raw.json',auth_raw);need(sha(auth_raw)==args.authorization_sha256,'authorization-sha256');authorization=verify_authorization(packet,raw,args.packet,parse(auth_raw));capture.write('ENTRY-AUTHORIZED.json',canonical(authorization))
  runtime=load_runtime(packet);inbox=Inbox(packet,capture);entered=True
  result=runtime.run_pipeline(packet,raw,Path(packet['evidence_directory']),inbox.next_command)
  capture.write('ENTRY-RESULT.json',canonical(dict(result=result)));print(json.dumps(dict(status='PIPELINE_RETURNED',result=result),sort_keys=True));return 0
 except BaseException as error:
  try:capture.write('ENTRY-ERROR.json',canonical(dict(error=type(error).__name__+': '+str(error),entered_pipeline=entered,automatic_retry=False)))
  finally:
   if entered:
    # Runtime owns custody and its hold protocol. Unknown post-entry failures
    # must never make this wrapper terminate/close an unseen custody descriptor.
    while True:time.sleep(.2)
  raise
 finally:
  capture.close() # The runtime returns only after a terminal, released state.
if __name__=='__main__':raise SystemExit(main())
