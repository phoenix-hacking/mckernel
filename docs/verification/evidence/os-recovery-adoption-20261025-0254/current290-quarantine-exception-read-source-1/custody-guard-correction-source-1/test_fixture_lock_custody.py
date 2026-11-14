"""Functional owned private-flock debugger fixture; no security testing.
Never opens/locks actual27:4, attaches actualactor or changes host permissions.
"""
import hashlib,importlib.util,json,os,select,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PYTHON='/home/holden/anaconda3/bin/python3.9'
spec=importlib.util.spec_from_file_location('guard_functions_only',ROOT/'exact_root_guard_runner.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
results=[]
for mode in ['success','helper_error','debugger_timeout']:
 nonce=uuid.uuid4().hex;release=ROOT/('fixture-release-'+nonce);lock=ROOT/('fixture-lock-'+nonce)
 fixture=subprocess.Popen([PYTHON,'-I','-B',str(ROOT/'owned_lock_fixture.py'),str(release),str(lock)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 result={};line=b''
 try:
  ready,_,_=select.select([fixture.stdout],[],[],5);assert ready
  line=fixture.stdout.readline();identity=json.loads(line);assert identity['pid']==fixture.pid
  birth=(Path('/proc')/str(fixture.pid)/'stat').read_bytes().rpartition(b') ')[2].split()[19]
  expected=guard.lock_metadata(lock.stat());assert (expected['device'],expected['inode'])!=(27,4)
  before=guard.inspect_held_lock(fixture.pid,str(lock),expected);assert before['fd']==identity['lock_fd']
  commands=['set pagination off','set confirm off','set may-call-functions off','set may-write-registers off','set may-write-memory off','set may-insert-breakpoints off','set may-insert-fast-tracepoints off','file '+PYTHON,'attach '+str(fixture.pid)]
  if mode=='debugger_timeout':commands+=['python import time;time.sleep(5)']
  else:
   filename=str(ROOT/'FIXTURE-ONLY-EXACT-CO-FILENAME.py') if mode=='success' else '/fixture-absent-frame.py'
   commands+=['source '+str(ROOT.parent/'read_exact_recover_error.gdb.py'),'read-exact-recover-error '+filename+' RuntimeError']
  commands+=['detach'];argv=['/usr/bin/gdb','-nx','-nh','-batch','-q','-iex','set auto-load off']
  for command in commands:argv+=['-ex',command]
  (ROOT/(mode+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
  try:
   child=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1 if mode=='debugger_timeout' else 10,check=False,env=dict(os.environ,DEBUGINFOD_URLS=''))
   stdout,stderr=child.stdout,child.stderr;code=child.returncode
  except subprocess.TimeoutExpired as exc:
   assert mode=='debugger_timeout';stdout,stderr=exc.stdout or b'',exc.stderr or b'';code='owned-debugger-timeout-killed-reaped'
  (ROOT/(mode+'.gdb.stdout')).write_bytes(stdout);(ROOT/(mode+'.gdb.stderr')).write_bytes(stderr)
  if mode=='success':
   answers=[json.loads(row) for row in stdout.decode().splitlines() if row.startswith('{')]
   assert code==0 and len(answers)==1 and answers[0]['error_argument']=='MCKERNEL_OWNED_FIXTURE_LOCKED_ERROR_20261026'
  elif mode=='helper_error':assert b'must find exactly one matching recover frame' in stderr and b'PASS_EXACT_RECOVER_ERROR_READ' not in stdout
  after=guard.inspect_held_lock(fixture.pid,str(lock),expected)
  assert fixture.poll() is None and after==before
  state=(Path('/proc')/str(fixture.pid)/'stat').read_bytes().rpartition(b') ')[2].split()
  assert state[19]==birth and state[0] not in (b'T',b't',b'Z')
  result=dict(mode=mode,fixture_pid=fixture.pid,starttime=birth.decode(),debugger_result=code,same_fd_inode_and_flock_before_after=True,alive_resumed_after=True,before=before,after=after)
 finally:
  release.write_bytes(b'owned fixture normal release\n');stdout,stderr=fixture.communicate(timeout=5)
  (ROOT/(mode+'.fixture.stdout')).write_bytes(line+stdout);(ROOT/(mode+'.fixture.stderr')).write_bytes(stderr)
  result['fixture_normal_exit']=fixture.returncode
  assert fixture.returncode==0
 results.append(result)
(ROOT/'FIXTURE-LOCK-CUSTODY-RESULT.json').write_text(json.dumps(dict(status='PASS_ALL3_OWNED_PRIVATE_FLOCK_FIXTURES',results=results,actual_actor_attached=False,actual27_4_opened_or_locked=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS_ALL3_OWNED_PRIVATE_FLOCK_FIXTURES',cases=3,normal_exits=[x['fixture_normal_exit'] for x in results]),indent=2))
