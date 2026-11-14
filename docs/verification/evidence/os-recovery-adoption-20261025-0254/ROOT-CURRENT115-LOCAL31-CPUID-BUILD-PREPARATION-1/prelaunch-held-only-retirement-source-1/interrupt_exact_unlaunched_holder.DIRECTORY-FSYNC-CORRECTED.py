#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-granted PIDFD SIGINT to exact ordinary unlaunched UID1000 holder only.
Never process-group/native/watcher/server signals, escalation, retry, unlock or deletion.
This source preparation is not execution authority and does not touch compiler/guest work.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,signal,stat
D=Path(__file__).resolve().parent
FIXED={'admission': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1', 'holder': {'path': '/run/lock/mckernel-development.lock', 'pid': 1815979, 'starttime': 95215128, 'device': 27, 'inode': 4, 'fd': 3}, 'refs': {'holder_ready': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/HOLDER.READY.json', 'bytes': 1371, 'sha256': '43f0ad8ce7ea87f64a24d7ce60132e16687abf0f1edfc5afb8206f271d7aae82'}, 'bootstrap': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/ROOT-HOLDER-BOOTSTRAP-GRANT.json', 'bytes': 1924, 'sha256': '248aa9c98f786a88b822317bc3724409a42fe2937ad3074263352fd59bbc2786'}, 'holder_source': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/hold_and_run_build_only.py', 'bytes': 7010, 'sha256': 'd17bd70e3e3e6ef7febe48b6f0f892ab6f1a94c74e89d43808bbea8b5dc21551'}, 'runner': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/run_build_only.py', 'bytes': 24465, 'sha256': '2471d24bcf8eaa5054c3d33b9ca9cc1cc77bd505e791b7ca6365e9ca0c854a6c'}, 'worker': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/build_only_worker.py', 'bytes': 4113, 'sha256': '0bdd40596f7d5a9fb056b9ff24c7033336af1305ce143391debd225a71d2b105'}, 'profile': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json', 'bytes': 112534, 'sha256': '022d9f08ec381a7b33649daf73840179516eb412d9c5cbcb8640e14692addb76'}, 'refused_review': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/INDEPENDENT-ACTUAL-HELD-RESOURCE-EXECUTION-REVIEW.json', 'bytes': 5725, 'sha256': '91e5ad3309f97e4e5625eaabd246ac8db92351e3955f005762dd84b81d4b4e31'}, 'expired_packet': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json', 'bytes': 2385, 'sha256': '3db1b68b3d260bff78e783054950507d9abc55e2a6cbb195552c59d9ab458be3'}, 'expired_resource': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json', 'bytes': 11839, 'sha256': '5748b55e1233ccdfb07e84f010a74ba3cdc72571efc76b6a897329f9ac7f1e16'}}, 'negative_paths': ['/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/ROOT-BUILD-GRANT.READY.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/RUNNER.STARTED.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/RUNNER.JOINED.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/runner.stdout', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/runner.stderr', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/BUILD-LOCAL-TERMINAL.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/HOLDER/QUARANTINE.json', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/OUTPUT'], 'nonce': 'cf36b84313f404836ec6d80350e0e15a', 'root_tool_session': 11857}
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py')
GUARD_SHA='1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'
def ref(path):
 p=Path(path);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(row):
 assert ref(row['path'])==row
 return json.loads(Path(row['path']).read_bytes())
def parse_stat(raw):
 tail=raw.rsplit(')',1)[1].split();return dict(state=tail[0],ppid=int(tail[1]),pgrp=int(tail[2]),start=int(tail[19]))
def parse_status(raw):return dict(line.split(':',1) for line in raw.splitlines() if ':' in line)
def verify_live():
 h=FIXED['holder'];pid=h['pid'];p=Path('/proc')/str(pid)
 assert pid==1815979 and pid!=os.getpid() and h['starttime']==95215128 and h['fd']==3
 a=parse_stat((p/'stat').read_text());status=parse_status((p/'status').read_text())
 assert a['start']==h['starttime'] and a['state'] not in ('Z','X','x')
 assert p.stat().st_uid==1000 and [int(v) for v in status['Uid'].split()]==[1000]*4
 bit=1<<(signal.SIGINT-1)
 assert int(status['SigIgn'],16)&bit==0 and int(status['SigBlk'],16)&bit==0 and int(status['SigCgt'],16)&bit!=0
 tasks=list((p/'task').iterdir());assert len(tasks)==1 and tasks[0].name==str(pid)
 assert (tasks[0]/'children').read_text().strip()==''
 argv=(p/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
 assert [v.decode() for v in argv[-3:]]==[FIXED['refs']['holder_source']['path'],'--bootstrap-grant',FIXED['refs']['bootstrap']['path']]
 lock=Path(h['path']);st=lock.lstat();fd=(p/'fd'/str(h['fd'])).stat()
 assert stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino)==(fd.st_dev,fd.st_ino)==(27,4)
 info=parse_status((p/'fdinfo'/str(h['fd'])).read_text());assert int(info['flags'],8)&os.O_CLOEXEC
 rows=[line.split() for line in Path('/proc/locks').read_text().splitlines()]
 matching=[r for r in rows if len(r)>=8 and r[5]=='00:1b:4']
 assert len(matching)==1 and matching[0][1:8]==['FLOCK','ADVISORY','WRITE',str(pid),'00:1b:4','0','EOF']
 for name in FIXED['negative_paths']:assert not os.path.lexists(name),name
 return dict(pid=pid,start=h['starttime'],uid=1000,fd=3,device=27,inode=4,children=[],negative_paths_absent=FIXED['negative_paths'],stat=a,cmdline=[v.decode() for v in argv])
def execute(grant_path):
 assert os.getuid()==os.geteuid()==1000
 assert Path(grant_path)==D/'ROOT-ACTUAL-ONE-HOLDER-INTERRUPT-GRANT.json'
 grant=json.loads(Path(grant_path).read_bytes());profile=checked(grant['profile'])
 assert grant['author']=='/root' and grant['decision']=='GRANT_ONE_EXACT_UNLAUNCHED_HOLDER_PIDFD_SIGINT'
 assert grant['maximum_invocations']==1 and grant['signal']=='SIGINT' and grant['holder']==FIXED['holder'] and grant['root_tool_session']==11857
 assert grant['source']==profile['source']==ref(Path(__file__)) and profile['fixed']==FIXED
 assert grant['root_attests_no_publisher_or_grant_ready_write_until_holder_positive_join'] is True
 assert grant['root_attests_no_build_runner_or_Docker_started'] is True and grant['independent_source_review_passed'] is True
 checked(grant['independent_source_review'])
 for key,row in FIXED['refs'].items():
  if key not in ('holder_source','runner','worker'):checked(row)
 # Authenticate Python sources as bytes, never JSON or executable imports.
 for key in ('holder_source','runner','worker'):assert ref(FIXED['refs'][key]['path'])==FIXED['refs'][key]
 holder_ready=checked(FIXED['refs']['holder_ready']);bootstrap=checked(FIXED['refs']['bootstrap']);refusal=checked(FIXED['refs']['refused_review'])
 assert holder_ready['holder']==FIXED['holder'] and holder_ready['source']==FIXED['refs']['holder_source'] and holder_ready['bootstrap']==FIXED['refs']['bootstrap']
 assert bootstrap['nonce']==holder_ready['nonce']==FIXED['nonce'] and bootstrap['source']==FIXED['refs']['holder_source']
 assert refusal['decision']=='REFUSED_EXPIRED_RESOURCE_SNAPSHOT_NO_BUILD_EXECUTION_APPROVAL' and refusal['execution_approval'] is False and refusal['maximum_invocations']==0
 assert hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal')
 assert ref(GUARD)['sha256']==GUARD_SHA
 spec=importlib.util.spec_from_file_location('retained_one_holder_account_window_guard',GUARD);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 clocks=guard.guard();assert grant['issued_epoch']<=clocks[0]<=grant['expires_epoch']<=min(grant['issued_epoch']+60,guard.current_cutoffs()[0])
 journal=D/'ACTUAL-ONE-HOLDER-INTERRUPT.ACTION.jsonl';pidfd=None;attempted=False
 with journal.open('x') as out:
  def emit(value):out.write(json.dumps(value,sort_keys=True)+'\n');out.flush();os.fsync(out.fileno())
  emit(dict(status='ENTERED_NO_SIGNAL',source=ref(Path(__file__)),grant=ref(grant_path),holder=FIXED['holder'],first_clocks=clocks))
  try:
   directory_fd=os.open(D,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
   try:os.fsync(directory_fd)  # Persist exclusive journal directory entry before any signal attempt.
   finally:os.close(directory_fd)
   first=verify_live();pidfd=os.pidfd_open(FIXED['holder']['pid'],0)
   info=parse_status((Path('/proc/self/fdinfo')/str(pidfd)).read_text());assert int(info['Pid'])==FIXED['holder']['pid']
   second=verify_live();last=guard.guard();assert last[0]<=grant['expires_epoch'] and all(a<b for a,b in zip(last,guard.current_cutoffs()))
   emit(dict(status='ATTEMPTING_EXACT_ONE_PIDFD_SIGINT_NO_RETRY',first=first,second=second,signal='SIGINT',last_clocks=last));attempted=True
   signal.pidfd_send_signal(pidfd,signal.SIGINT,None,0)
   emit(dict(status='SIGNAL_SENT_NOT_RETIREMENT',signal_calls=1,root_must_positive_join_tool11857=True,current_free=False))
  except BaseException as error:
   emit(dict(status='FAILED_CLOSED_NO_ESCALATION_OR_RETRY',signal_attempted=attempted,error=repr(error),current_free=False));raise
  finally:
   if pidfd is not None:os.close(pidfd)  # Closes this helper's pidfd only, never permanent lock FD3.
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--grant',required=True);a=p.parse_args();execute(Path(a.grant))
