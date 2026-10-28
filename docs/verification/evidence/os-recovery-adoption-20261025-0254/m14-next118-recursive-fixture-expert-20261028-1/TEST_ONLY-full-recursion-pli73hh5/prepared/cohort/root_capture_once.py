"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root capture owner only. Requires live independent PREWARM before either clock.
Runs exact existing capture helper once/phase; never approves or publishes grants.
"""
from pathlib import Path
import argparse,json,os,signal,subprocess,time,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from handoff_common import *
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bindings',required=True);p.add_argument('--handoff',required=True);p.add_argument('--phase',choices=['physical','held'],required=True);a=p.parse_args();b=read_json(a.bindings);H=Path(a.handoff);A=Path(b['admission']);need(b['Root_capture_owner']=='/root','Root capture owner only');no_launch(A)
 ready=read_json(H/'PREWARM_READY.json');need(ready['reviewer']==REVIEWER and ready['nonce']==b['nonce'] and ready['admission']==str(A) and birth(ready['pid'])==ready['starttime'],'independent reviewer already live BEFORE clock')
 verify_ref(ready['verifier']);need(ready['verifier']==b['finite_verifier'],'exact reviewed finite verifier');in_window(clocks(),ready['earliest_clamps'])
 source=verify_ref(b['capture_source']);argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(source)]
 if a.phase=='physical':argv+=['--physical-output',str(A/'ROOT-PREHOLDER-PHYSICAL-1.json')]
 else:
  physical_marker=read_json(H/'ROOT-PHYSICAL-CAPTURE.COMPLETE.json');need(physical_marker['returncode']==0 and physical_marker['direct_child_joined'] and physical_marker['group_absent'] and physical_marker['closed_streams'],'actual positive physical capture required')
  argv+=['--admission',str(A),'--root-input',str(A/'ROOT-ACTUAL-RESOURCE-INPUT-1.json')]
 atomic_json(H/('ROOT-'+a.phase.upper()+'-CAPTURE.ONCE-CLAIM.json'),dict(scope=SCOPE,owner='/root',nonce=b['nonce'],argv=argv,prewarm_ready=reference(H/'PREWARM_READY.json')))
 stdout=H/(a.phase+'.stdout');stderr=H/(a.phase+'.stderr')
 with stdout.open('xb') as out,stderr.open('xb') as err:
  child=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
  # No auto-kill/retry. A timeout preserves PID/birth for Root ownership repair.
  atomic_json(H/(a.phase+'.CHILD-STARTED.json'),dict(pid=child.pid,starttime=birth(child.pid),argv=argv))
  rc=child.wait(timeout=90)
 absent=False
 try:os.killpg(child.pid,0)
 except ProcessLookupError:absent=True
 need(rc==0 and absent,'capture must return0 and positivelyjoin entire group')
 value=dict(scope=SCOPE,status='ROOT_'+a.phase.upper()+'_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN',nonce=b['nonce'],admission=str(A),argv=argv,pid=child.pid,returncode=rc,direct_child_joined=True,group_absent=absent,closed_streams=True,stdout=reference(stdout),stderr=reference(stderr),capture_source=b['capture_source'],prewarm_ready=reference(H/'PREWARM_READY.json'),physical=reference(A/'ROOT-PREHOLDER-PHYSICAL-1.json'))
 if a.phase=='held':
  for k,n in [('pending_input','ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json'),('resource','ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json'),('root_resource_input','ROOT-ACTUAL-RESOURCE-INPUT-1.json'),('holder_ready','HOLDER/HOLDER.READY.json'),('holder_bootstrap','ROOT-HOLDER-BOOTSTRAP-GRANT.json')]:value[k]=reference(A/n)
 marker=atomic_json(H/('ROOT-'+a.phase.upper()+'-CAPTURE.COMPLETE.json'),value);print(json.dumps(dict(status=value['status'],complete_marker=marker)))
if __name__=='__main__':main()
