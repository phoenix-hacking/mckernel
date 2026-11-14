"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SOURCE ONLY until an exact independent execution release. Capture one sudo child;
never signal a keeper, interpret a timeout as retirement, or claim an old JOIN.
"""
import argparse
import hashlib
import json
import stat
import os
from pathlib import Path
import selectors
import sys
import time

HERE=Path(__file__).resolve().parent
e=None # Entry code is executed only after its exact packet source pin is read.

def bootstrap_read(path):
 path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<=before.st_size<=32<<20:raise ValueError('bootstrap-bounded-regular-file')
  raw=bytearray()
  while len(raw)<=before.st_size:
   block=os.read(fd,min(65536,before.st_size+1-len(raw)))
   if not block:break
   raw.extend(block)
  after=os.fstat(fd)
  fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  current=path.lstat()
  if len(raw)!=before.st_size or any(getattr(before,key)!=getattr(after,key) for key in fields) or (after.st_dev,after.st_ino)!=(current.st_dev,current.st_ino):raise ValueError('bootstrap-file-raced')
  return bytes(raw)
 finally:os.close(fd)

def bootstrap_entry(raw,packet_sha):
 global e
 if hashlib.sha256(raw).hexdigest()!=packet_sha:raise ValueError('packet-sha256')
 def pairs(items):
  result={}
  for key,value in items:
   if key in result:raise ValueError('duplicate-json-key')
   result[key]=value
  return result
 packet=json.loads(raw,object_pairs_hook=pairs)
 ref=packet['pipeline_sources']['entry']
 if Path(ref['path'])!=HERE/'capture_entry.py':raise ValueError('fixed-entry-source-path')
 source=bootstrap_read(ref['path'])
 if len(source)!=ref['bytes'] or hashlib.sha256(source).hexdigest()!=ref['sha256']:raise ValueError('entry-source-pin')
 module=type(sys)('_keeper_capture_entry');module.__file__=ref['path']
 exec(compile(source,ref['path'],'exec'),module.__dict__);e=module
 return e.parse(raw)



def child_identity(pid):
 raw=Path('/proc/%d/stat'%pid).read_bytes();fields=raw.rpartition(b') ')[2].split()
 e.need(len(fields)>=50,'child-process-stat')
 return dict(pid=pid,starttime=fields[19].decode(),ppid=int(fields[1]),pgid=int(fields[2]),
             command_hex=Path('/proc/%d/cmdline'%pid).read_bytes().hex())


def launch_argv(packet_path,packet_sha,packet,authorization_path,authorization_sha):
 # Authorization is a separately pinned late envelope. Its own hash cannot be
 # embedded in the grant inside that envelope. The grant binds this payload
 # prefix; the envelope suffix is built exclusively from verified CLI inputs.
 payload=e.payload_argv(packet_path,packet_sha,packet)+[
     '--authorization',str(authorization_path),'--authorization-sha256',authorization_sha]
 return ['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit',
         '--as=2147483648:2147483648','--fsize=33554432:33554432','--core=0:0','--']+payload


def capture_child(argv,capture,*,maximum=32<<20):
 """Direct child evidence only. Private tests supply ordinary harmless argv."""
 e.need(type(maximum) is int and 0<maximum<=e.MAX_FILE,'bounded-capture-limit')
 streams={};pipes=[];child=None;gate=None;joined=False;released=False;selector=selectors.DefaultSelector()
 try:
  # All output destinations are precreated regular files before a child exists.
  for name in ('STDOUT','STDERR'):
   e.need(e.identity(capture.path)==capture.before,'capture-directory-raced')
   fd=os.open(name+'.raw',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=capture.fd)
   streams[name]=dict(fd=fd,bytes_observed=0,bytes_stored=0,overflow=False,write_error=None)
   read_fd,write_fd=os.pipe();pipes.append((read_fd,write_fd))
  gate_read,gate_write=os.pipe();gate=gate_write
  child=os.fork()
  if child==0:
   try:
    os.close(gate_write)
    for read_fd,_ in pipes:os.close(read_fd)
    for row in streams.values():os.close(row['fd'])
    os.close(capture.fd)
    if os.read(gate_read,1)!=b'G':os._exit(125)
    os.close(gate_read)
    os.dup2(pipes[0][1],1);os.dup2(pipes[1][1],2)
    for _,write_fd in pipes:os.close(write_fd)
    os.execv(argv[0],argv) # Inherit askpass normally; never inspect/log its value.
   except BaseException:
    os._exit(126)
  os.close(gate_read)
  for (name,row),(read_fd,write_fd) in zip(streams.items(),pipes):
   os.close(write_fd);os.set_blocking(read_fd,False);selector.register(read_fd,selectors.EVENT_READ,name)
  birth=child_identity(child)
  e.need(birth['ppid']==os.getpid(),'genuine-direct-child-birth')
  capture.write('DIRECT-CHILD-BIRTH.json',e.canonical(dict(
      scope=e.SCOPE,process=birth,planned_exec_argv=argv,observation='blocked-before-exec',
      clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)])))
  os.write(gate,b'G');released=True;os.close(gate);gate=None
  while selector.get_map():
   for key,_ in selector.select(.2):
    block=os.read(key.fd,65536)
    if not block:selector.unregister(key.fd);os.close(key.fd);continue
    row=streams[key.data];row['bytes_observed']+=len(block)
    keep=block[:max(0,maximum-row['bytes_stored'])] if row['write_error'] is None else b''
    view=memoryview(keep)
    try:
     while view:
      count=os.write(row['fd'],view);e.need(count>0,'capture-write-no-progress');view=view[count:];row['bytes_stored']+=count
    except (OSError,ValueError) as error:
     row['write_error']=type(error).__name__+': '+str(error)
    row['overflow']=row['bytes_observed']>maximum
  while True:
   try:pid,status,usage=os.wait4(child,0);joined=True;break
   except InterruptedError:continue
  e.need(pid==child,'exact-direct-child-wait4')
  result=dict(pid=pid,starttime=birth['starttime'],wait_status=status,
      exit_code=os.waitstatus_to_exitcode(status),direct_join=True,
      joined_clock=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)],
      rusage={key:getattr(usage,key) for key in dir(usage) if key.startswith('ru_')},
      streams={name:{key:value for key,value in row.items() if key!='fd'} for name,row in streams.items()},
      historical_actor_join_inferred=False,automatic_signal=False)
  for row in streams.values():os.fsync(row['fd'])
  os.fsync(capture.fd);capture.write('DIRECT-CHILD-JOIN.json',e.canonical(result));return result
 except BaseException as error:
  try:
   capture.write('OUTER-UNRESOLVED-CAPTURE.json',e.canonical(dict(
       status='CAPTURE_FAULT_RETAIN_DIRECT_CHILD_WAIT' if released and not joined else 'CAPTURE_FAULT',
       error=type(error).__name__+': '+str(error),pid=child,exec_released=released,
       direct_join_observed=joined,automatic_signal=False,retirement_inferred=False,
       pipe_ownership='retained-until-direct-join')))
  except BaseException:pass # Evidence writer failure grants no lifecycle action.
  raise
 finally:
  if gate is not None:os.close(gate) # EOF before G refuses exec, without signals.
  for row in streams.values():os.close(row['fd'])
  # A post-exec capture fault cannot authorize killing a retained keeper. We
  # still own our direct child's wait, potentially indefinitely.
  if child is not None and child>0 and not joined:
   while True:
    try:
     pid,status,usage=os.wait4(child,0);joined=True
     try:capture.write('OUTER-FAULT-DIRECT-CHILD-JOIN.json',e.canonical(dict(pid=pid,wait_status=status,exit_code=os.waitstatus_to_exitcode(status),direct_join=True,automatic_signal=False,rusage={key:getattr(usage,key) for key in dir(usage) if key.startswith('ru_')})))
     except BaseException:pass
     break
    except InterruptedError:continue
  for key in list(selector.get_map().values()):os.close(key.fd)
  selector.close()


def main(argv=None):
 parser=argparse.ArgumentParser()
 parser.add_argument('--packet',type=Path,required=True);parser.add_argument('--packet-sha256',required=True)
 parser.add_argument('--authorization',type=Path,required=True);parser.add_argument('--authorization-sha256',required=True)
 args=parser.parse_args(argv)
 raw=bootstrap_read(args.packet);packet=bootstrap_entry(raw,args.packet_sha256)
 e.verify_sources(packet);e.verify_directories(packet,packet['entry_capture_directory']);e.clock_check(packet)
 auth_raw,_=e.read_file(args.authorization);e.need(e.sha(auth_raw)==args.authorization_sha256,'authorization-sha256')
 e.verify_authorization(packet,raw,args.packet,e.parse(auth_raw))
 capture=e.Capture(packet['outer_capture_directory'])
 try:
  capture.write('LAUNCH-PACKET.raw.json',raw);capture.write('LAUNCH-AUTHORIZATION.raw.json',auth_raw)
  capture.write('OUTER-PROCESS.json',e.canonical(dict(scope=e.SCOPE,process=e.process_identity(),argv=sys.argv)))
  command=launch_argv(args.packet,args.packet_sha256,packet,args.authorization,args.authorization_sha256)
  result=capture_child(command,capture)
  # Overflow is explicit functional capture failure, never silently accepted.
  return 1 if result['exit_code']!=0 or any(row['overflow'] or row['write_error'] for row in result['streams'].values()) else 0
 finally:capture.close()

if __name__=='__main__':raise SystemExit(main())
