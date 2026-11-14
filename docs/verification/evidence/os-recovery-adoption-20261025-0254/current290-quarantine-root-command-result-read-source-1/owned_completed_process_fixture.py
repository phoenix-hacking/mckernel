"""Functional own-harness CompletedProcess fixture; no security testing."""
import ctypes,fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(0x59616d61,ctypes.c_ulong(-1).value,0,0,0)!=0:raise OSError(ctypes.get_errno(),'fixture PR_SET_PTRACER_ANY')
lock_fd=os.open(sys.argv[2],os.O_RDONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
CHILD_CODE="import sys;sys.stdout.buffer.write(b'OWNED_STDOUT_20261026\\x00\\xff');sys.stderr.buffer.write(b'OWNED_STDERR_20261026\\x00\\xfe');sys.exit(17)"
if len(sys.argv)>3 and sys.argv[3]=='combined_cap':
 CHILD_CODE="import sys;sys.stdout.buffer.write(b'A'*(3<<20));sys.stderr.buffer.write(b'B'*(3<<20));sys.exit(17)"
birth=Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode()
args=['/usr/bin/python3','-I','-B','-c',CHILD_CODE,'a'*48,str(os.getpid()),birth]
try:
 code='''class Refusal(RuntimeError):pass
def root_command(args,limit):
 result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
 if result.returncode or result.stderr or len(result.stdout)>limit:
  raise Refusal('root-command-failed:'+args[0])
 return result.stdout
def recover():
 try:
  root_command(args,1<<20)
 except Refusal as error:
  print(json.dumps(dict(pid=os.getpid(),birth=birth,ready=True,lock_fd=lock_fd,lock_path=sys.argv[2],child_code_sha256=hashlib.sha256(CHILD_CODE.encode()).hexdigest(),child_code_bytes=len(CHILD_CODE))),flush=True)
  until=time.monotonic()+30
  while not Path(sys.argv[1]).exists() and time.monotonic()<until:
   time.sleep(0.05)
recover()
'''
 exec(compile(code,str(ROOT/'FIXTURE-ONLY-ROOT-COMMAND.py'),'exec'))
finally:os.close(lock_fd)
