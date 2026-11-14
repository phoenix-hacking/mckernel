"""Exactly two proposed no-effect vectors through the actual S4 LAST caller.
Never invokes caller main/static_joins/root/snapshot/owner/guard/binder.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,socket,stat,subprocess,sys
D=Path(__file__).resolve().parent

def forbidden(*a,**kw):raise AssertionError('process/socket/exec effect forbidden in contract-only vector')
def exact(row):
 p=Path(row['path']);raw=p.read_bytes();s=p.lstat()
 assert stat.S_ISREG(s.st_mode) and s.st_mode==row['mode'] and len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 return raw

def main():
 assert len(sys.argv)==2 and sys.argv[1] in ('positive','changed_report_mode')
 cfg=json.loads((D/'CONTRACT-CHECK-INPUTS.json').read_bytes())
 exact(cfg['actual_caller']);exact(cfg['helper']);exact(cfg['actual_acceptance'])
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden
 spec=importlib.util.spec_from_file_location('exact_source_only_S4_LAST_caller',cfg['actual_caller']['path'])
 caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)
 helper=caller.m03_contract()
 if sys.argv[1]=='positive':
  role=helper.validate(cfg['actual_acceptance'],cfg['actual_stage_acceptance'])
  assert role['report_ref']==cfg['actual_acceptance'] and role['stage_ref']==cfg['actual_stage_acceptance']
  assert role['report']['normalization_acceptance'] is True and role['report']['native_acceptance'] is False
  print(json.dumps(dict(vector='positive',actual_caller=cfg['actual_caller'],helper=cfg['helper'],actual_body=True,full_report_and_stage_roles=True,root_operations=0,guest_runs=0,process_socket_exec_effects=0)))
 else:
  changed=dict(cfg['actual_acceptance']);changed['mode']^=1
  try:helper.validate(changed,cfg['actual_stage_acceptance'])
  except AssertionError:pass
  else:raise AssertionError('changed report full mode identity accepted')
  exact(cfg['actual_acceptance'])
  print(json.dumps(dict(vector='changed_report_mode',actual_caller=cfg['actual_caller'],helper=cfg['helper'],actual_body=True,changed_identity_refused=True,immutable_report_unchanged=True,root_operations=0,guest_runs=0,process_socket_exec_effects=0)))
if __name__=='__main__':main()
