"""Functional own privateflock trace-result fixture; no security testing/effects
on real quarantined actor. Real systemPython subprocess; no mocked field data.
"""
import hashlib,importlib.util,json,os,select,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;E=ROOT.parent
old=E/'current290-quarantine-exception-read-source-1/custody-guard-correction-source-1/exact_root_guard_runner.py'
spec=importlib.util.spec_from_file_location('accepted_lock_guard_only',old);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
results=[]
for mode in ['success','helper_error','debugger_timeout','combined_cap']:
 nonce=uuid.uuid4().hex;release=ROOT/('fixture-release-'+nonce);lock=ROOT/('fixture-lock-'+nonce)
 fixture=subprocess.Popen(['/home/holden/anaconda3/bin/python3.9','-I','-B',str(ROOT/'owned_completed_process_fixture.py'),str(release),str(lock),mode],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 result={};line=b''
 try:
  ready,_,_=select.select([fixture.stdout],[],[],5);assert ready;line=fixture.stdout.readline();identity=json.loads(line);assert identity['pid']==fixture.pid
  expected=guard.lock_metadata(lock.stat());assert (expected['device'],expected['inode'])!=(27,4);before=guard.inspect_held_lock(fixture.pid,str(lock),expected)
  commands=['set pagination off','set confirm off','set may-call-functions off','set may-write-registers off','set may-write-memory off','set may-insert-breakpoints off','set may-insert-fast-tracepoints off','file /home/holden/anaconda3/bin/python3.9','attach '+str(fixture.pid)]
  if mode=='debugger_timeout':commands+=['python import time;time.sleep(5)']
  else:
   filename='/absent-root-command-frame.py' if mode=='helper_error' else str(ROOT/'FIXTURE-ONLY-ROOT-COMMAND.py')
   commands+=['source '+str(ROOT/'read_exact_root_command_result.gdb.py'),'read-exact-root-command-result '+filename+' '+identity['child_code_sha256']+' '+str(identity['child_code_bytes'])+' '+identity['birth']]
  commands+=['detach'];argv=['/usr/bin/gdb','-nx','-nh','-batch','-q','-iex','set auto-load off']
  for command in commands:argv+=['-ex',command]
  (ROOT/(mode+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n')
  try:
   child=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1 if mode=='debugger_timeout' else 10,check=False,env=dict(os.environ,DEBUGINFOD_URLS=''));stdout,stderr,code=child.stdout,child.stderr,child.returncode
  except subprocess.TimeoutExpired as exc:
   assert mode=='debugger_timeout';stdout,stderr,code=exc.stdout or b'',exc.stderr or b'','own-debugger-timeout-killed-reaped'
  (ROOT/(mode+'.gdb.stdout')).write_bytes(stdout);(ROOT/(mode+'.gdb.stderr')).write_bytes(stderr)
  if mode=='success':
   answers=[json.loads(row) for row in stdout.decode().splitlines() if row.startswith('{')];assert code==0 and len(answers)==1
   answer=answers[0];assert answer['status']=='PASS_EXACT_ROOT_COMMAND_RESULT_READ' and answer['returncode']==17
   for stream in ['stdout','stderr']:
    raw=bytes.fromhex(answer[stream]['raw_hex']);expectedraw=(b'OWNED_STDOUT_20261026\x00\xff' if stream=='stdout' else b'OWNED_STDERR_20261026\x00\xfe');assert raw==expectedraw and len(raw)==answer[stream]['bytes'] and hashlib.sha256(raw).hexdigest()==answer[stream]['sha256']
   assert answer['argv']['code_sha256']==identity['child_code_sha256'] and answer['argv']['caller_pid']==fixture.pid and answer['argv']['caller_starttime']==identity['birth']
   result['extraction']=answer
  elif mode=='combined_cap':assert b'combined childoutput5MiB bound: stdout=3145728 stderr=3145728 total=6291456' in stderr and b'PASS_EXACT_ROOT_COMMAND_RESULT_READ' not in stdout
  elif mode=='helper_error':assert b'unique exact recover frame' in stderr and b'PASS_EXACT_ROOT_COMMAND_RESULT_READ' not in stdout
  after=guard.inspect_held_lock(fixture.pid,str(lock),expected);state=Path('/proc/'+str(fixture.pid)+'/stat').read_bytes().rpartition(b') ')[2].split()
  assert fixture.poll() is None and before==after and state[19].decode()==identity['birth'] and state[0] not in (b'T',b't',b'Z')
  result.update(mode=mode,fixture_pid=fixture.pid,birth=identity['birth'],debugger_result=code,same_fd_inode_flock=True,alive_resumed_after=True,before=before,after=after)
 finally:
  release.write_bytes(b'owned fixture normal release\n');stdout,stderr=fixture.communicate(timeout=5);(ROOT/(mode+'.fixture.stdout')).write_bytes(line+stdout);(ROOT/(mode+'.fixture.stderr')).write_bytes(stderr);result['normal_exit']=fixture.returncode;assert fixture.returncode==0
 results.append(result)
(ROOT/'COMPLETED-PROCESS-FIXTURE-RESULT.json').write_text(json.dumps(dict(status='PASS_4_OWNED_COMPLETEDPROCESS_FLOCK_CASES',results=results,actual_actor_attached=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS_4_OWNED_COMPLETEDPROCESS_FLOCK_CASES',cases=4,normal_exits=[x['normal_exit'] for x in results]),indent=2))
