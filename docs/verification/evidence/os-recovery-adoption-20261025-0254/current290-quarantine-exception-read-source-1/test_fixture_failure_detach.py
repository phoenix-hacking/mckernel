"""Functional owned-fixture error/timeout detach proof only; no security testing.
Only the owned debugger is killed by subprocess timeout; no target/group signals.
"""
import json,os,select,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PYTHON='/home/holden/anaconda3/bin/python3.9'
results=[]
for mode in ['helper_error','debugger_timeout']:
 release=ROOT/('fixture-release-'+uuid.uuid4().hex)
 fixture=subprocess.Popen([PYTHON,'-I','-B',str(ROOT/'owned_fixture.py'),str(release)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 result={}
 try:
  ready,_,_=select.select([fixture.stdout],[],[],5);assert ready
  line=fixture.stdout.readline();identity=json.loads(line);assert identity['pid']==fixture.pid
  before=Path('/proc/'+str(fixture.pid)+'/stat').read_bytes().rpartition(b') ')[2].split()[19]
  commands=['set pagination off','set confirm off','set may-call-functions off','set may-write-registers off','set may-write-memory off','set may-insert-breakpoints off','set may-insert-fast-tracepoints off','file '+PYTHON,'attach '+str(fixture.pid)]
  if mode=='helper_error':commands+=['source '+str(ROOT/'read_exact_recover_error.gdb.py'),'read-exact-recover-error /fixture-absent-frame.py RuntimeError']
  else:commands+=['python import time;time.sleep(5)']
  commands+=['detach'];argv=['/usr/bin/gdb','-nx','-nh','-batch','-q','-iex','set auto-load off']
  for command in commands:argv+=['-ex',command]
  (ROOT/(mode+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
  try:
   child=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10 if mode=='helper_error' else 1,check=False)
   stdout,stderr=child.stdout,child.stderr
   (ROOT/(mode+'.gdb.stdout')).write_bytes(stdout);(ROOT/(mode+'.gdb.stderr')).write_bytes(stderr)
   assert mode=='helper_error' and b'must find exactly one matching recover frame' in stderr and b'PASS_EXACT_RECOVER_ERROR_READ' not in stdout
   exit_status=child.returncode
  except subprocess.TimeoutExpired as exc:
   assert mode=='debugger_timeout';stdout,stderr=exc.stdout or b'',exc.stderr or b'';exit_status='subprocess.TimeoutExpired debugger killed/reaped'
  (ROOT/(mode+'.gdb.stdout')).write_bytes(stdout);(ROOT/(mode+'.gdb.stderr')).write_bytes(stderr)
  assert fixture.poll() is None
  after=Path('/proc/'+str(fixture.pid)+'/stat').read_bytes().rpartition(b') ')[2].split()
  assert after[19]==before and after[0] not in (b'Z',b'T',b't')
  result=dict(mode=mode,fixture_pid=fixture.pid,fixture_starttime=before.decode(),debugger_result=exit_status,fixture_alive_resumed_same_birth=True,no_target_or_group_signal=True)
 finally:
  release.write_bytes(b'owned fixture normal release\n');stdout,stderr=fixture.communicate(timeout=5)
  (ROOT/(mode+'.fixture.stdout')).write_bytes(line+stdout if 'line' in locals() else stdout);(ROOT/(mode+'.fixture.stderr')).write_bytes(stderr)
  result['fixture_normal_exit']=fixture.returncode
  assert fixture.returncode==0
 results.append(result)
(ROOT/'FAILURE-DETACH-RESULT.json').write_text(json.dumps(dict(status='PASS_OWNED_ERROR_AND_TIMEOUT_DETACH',results=results,actual_actor_attached=False),indent=2)+'\n')
print(json.dumps(results,indent=2))
