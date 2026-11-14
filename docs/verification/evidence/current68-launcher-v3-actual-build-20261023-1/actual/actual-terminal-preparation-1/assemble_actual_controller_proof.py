"""Finite DATA assembly using unchanged accepted current-controller contract.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import argparse,hashlib,json,runpy
T=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--artifact-review',required=True);p.add_argument('--artifact-review-sha256',required=True);a=p.parse_args()
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
x=json.loads((T/'ACTUAL-CLOSED-LAUNCHER-RECORDS.json').read_bytes());artifact=ref(a.artifact_review);assert artifact['sha256']==a.artifact_review_sha256
roles=dict(x['roles']);roles.update(artifact_review=artifact,supervisor_command=ref(T/'ACTUAL-EXECUTED-SUPERVISOR-COMMAND.json'),tool_started=ref(T/'ACTUAL-TOOL-CONTROLLER-started.json'),tool_completed=ref(T/'ACTUAL-TOOL-CONTROLLER-completed.json'))
proof=dict(schema='mckernel.launcher.single-child-controller-proof.v1',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',roles=roles,target=x['target'],controller_client_ledger=x['controller_client_ledger'],launcher_source_sha256='8f9fbe474220433118e6662c9f2517f73a547730575b83ffb73255d06e9b40d7',tool_session='96106',outer_os_identity=None,outer_group_observation=None,runtime_release=None)
p=T/'CURRENT-CONTROLLER-PROOF.json'
with p.open('x')as f:json.dump(proof,f,sort_keys=True,indent=2);f.write('\n')
c=runpy.run_path(str(T/'current_controller_contract.py'));result=c['validate'](ref(p),require_authority=False)
report=dict(status='PASS_UNCHANGED_CONTROLLER_CONTRACT_RETAINED_DATA_JOIN_NO_INDEPENDENT_REVIEW_YET',proof=ref(p),contract=ref(T/'current_controller_contract.py'),saved_pids=list(result['pids']),physical_clearance=False,controller_review=None,cleanup_release=None,native_acceptance=False)
with(T/'ACTUAL-CONTROLLER-CONTRACT-DATA-JOIN.json').open('x')as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(ref(p),sort_keys=True))
