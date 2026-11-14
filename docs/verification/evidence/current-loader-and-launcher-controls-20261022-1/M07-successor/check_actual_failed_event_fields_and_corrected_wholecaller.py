from pathlib import Path
import importlib.util,json,runpy,copy
OLD=Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/stage-runtime-preparation-1/runtime-source-preparation-1/failed-owner-successor-runtime-preparation-1/typed-controller-pair-correction-1/bound-runtime-source-1')
D=Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/stage-runtime-preparation-1/runtime-source-preparation-1/failed-owner-successor-runtime-preparation-1/expert-failed-terminal-status-correction-1/bound-runtime-source-1')
s=importlib.util.spec_from_file_location('retained_previous_failed_status_snapshot',OLD/'root_manual_snapshot_threads.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=json.loads((OLD/'STATIC-NONTEMPORAL-INPUTS.json').read_bytes());physical=json.loads(Path(c['latest_physical']['path']).read_bytes());roles=json.loads(Path(c['native_predecessor_binding']['path']).read_bytes())
try:m.terminal_joins(physical,roles)
except m.Refusal as e:assert str(e)=='genuine actual failed tool completion, handle is not OS PID',str(e)
else:raise AssertionError('original failed-status predicate did not refuse genuine failed completion')
s=importlib.util.spec_from_file_location('actual_expert_failed_terminal_snapshot',D/'root_manual_snapshot_threads.py');fixed=importlib.util.module_from_spec(s);s.loader.exec_module(fixed)
fixed.terminal_joins(physical,roles)
original_checked=fixed.checked;event_ref=physical['controller_terminal']['completed_event']
for key,value in [('status','completed'),('exitCode',0)]:
 def fixture_checked(row,key=key,value=value):
  document=original_checked(row)
  if row==event_ref:
   document=copy.deepcopy(document);document['event']['params']['item'][key]=value
  return document
 fixed.checked=fixture_checked
 try:fixed.terminal_joins(physical,roles)
 except fixed.Refusal as e:assert str(e)=='genuine actual failed tool completion, handle is not OS PID',str(e)
 else:raise AssertionError('required failed-event refusal absent: '+key)
 finally:fixed.checked=original_checked
runpy.run_path(str(D/'check_current_whole_caller.py'),run_name='__main__')

