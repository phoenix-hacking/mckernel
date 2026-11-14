# One P03 PTY case under Root admission; no compilation or test-suite runner here.
import json,os,sys
from pathlib import Path
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W))
from owned_process import Owner
O=W/'output/behavior-run-1'
O.mkdir(parents=True,exist_ok=False)
expected=['info threads\n','thread 1\n','bt\n','thread 2\n','quit\n','y\n']
record={'status':'FAIL','scope':'one controlled-child P03 PTY dialogue; no production/native parity claim'}
try:
 owner=Owner(O)
 result=owner.run([str(W/'output/p03-controlled-build-1/eclair-dump-backtrace.exp')],dict(os.environ),str(W),20,'controlled-P03')
 assert result.returncode==0,result.returncode
 assert result.stderr==b'',result.stderr
 child=json.loads((O/'controlled-child.json').read_text())
 assert child['status']=='CONTROLLED_DIALOGUE_COMPLETE_RETURNING_0'
 assert child['commands']==expected
 assert child['argv']==['-k',str(W/'controlled-prefix/smp-x86_64/kernel/mckernel.img'),'-i','-l']
 assert child['standard_fds_tty'] and child['kernel_argument_never_opened']
 assert len(owner.records)==1
 own=owner.records[0]
 assert child['ppid']==own['leader']
 assert own['leader_birth'] and child['birth']
 assert own['leader_parent_joined'] and own['whole_descendants_joined'] and own['streams_closed']
 assert not own['adopted_reaps'] and not own['adopted_kills'] and not own['remaining_direct_children']
 assert own['error'] is None and not own['timed_out']
 record.update(status='PASS_CONTROLLED_PTY_DIALOGUE_EXIT_AND_CLEANUP',ownership=own,controlled_child=child,program_runtime_executed=True,production_Eclair_or_kernel_executed=False)
except BaseException as exc:
 record['error']=type(exc).__name__+': '+str(exc)
 (O/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
 raise
(O/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
