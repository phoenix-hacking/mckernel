"""Proposed two ordinary saved-evidence checks; no root/main/live workload.
One genuinepositive S5 through actual unchangedQ4 terminalcaller, then one
changed complete reportFD identity refusal through the same acceptedFD reader.
"""
from pathlib import Path
import copy,fcntl,hashlib,importlib.util,json,os,socket,subprocess
D=Path(__file__).resolve().parent

def exact(row):
 p=Path(row['path']);s=p.lstat();raw=p.read_bytes()
 assert s.st_mode==row['mode'] and len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 return raw

def load(name,row):
 exact(row);spec=importlib.util.spec_from_file_location(name,row['path'])
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def forbidden(*a,**kw):raise AssertionError('No root/main/live/process/socket/exec/flock effect in savedpositive consumer check')

def main():
 cfg=json.loads((D/'CHECK-INPUTS.json').read_bytes())
 for key in ['actual_caller','projection_source','accepted_FD_reader','context','genuine_physical','overlay']:exact(cfg[key])
 subprocess.Popen=forbidden;socket.socket=forbidden;os.execve=forbidden;fcntl.flock=forbidden
 caller=load('actual_unchanged_Q4_terminal_caller',cfg['actual_caller'])
 for name in ['main','collect_live','validate_live','publish','command']:setattr(caller,name,forbidden)
 p=load('exact_positive_S5_consumer',cfg['projection_source'])
 ctx=p.checked(p.CONTEXT_REF);t=p.checked(ctx['physical_FD']);overlay=json.loads(exact(cfg['overlay']))
 caller.terminal_joins(t,overlay)
 wrong=copy.deepcopy(ctx['physical_FD']);wrong['inode']+=1
 try:p.read_bytes(wrong)
 except (AssertionError,ValueError):pass
 else:raise AssertionError('changed full report FD identity accepted')
 exact(cfg['genuine_physical'])
 O=D/'ordinary-check-1';assert not os.path.lexists(O);O.mkdir(mode=0o700)
 result=dict(status='PASS',cases=['genuine_positiveS5_full30client7stage_receipt_QEMU_retirement_through_actual_Q4_saved_terminal_caller','changed_complete_report_FD_inode_identity_refused'],actual_projection_calls=1,actual_projection=overlay['physical_predecessor'],physical=ctx['physical'],physical_FD=ctx['physical_FD'],projection_source=cfg['projection_source'],actual_caller=cfg['actual_caller'],immutable_report_unchanged=True,root_operations=0,main_invocations=0,live_collections=0,guest_runs=0,scope='Saved latestpositiveS5 owner PHYSICAL retirement only. No application/sourceSDK/wholecriterion/default/ACK/runtimeacceptance.')
 with (O/'RESULT.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(dict(status='PASS',cases=len(result['cases']),actual_projection_calls=1,root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
