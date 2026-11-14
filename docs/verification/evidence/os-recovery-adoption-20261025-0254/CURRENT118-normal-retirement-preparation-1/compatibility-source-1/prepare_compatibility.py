"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Additive single wait-status API correction; no runtime, guard or ownership action.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).resolve().parent;P=D.parent
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(n,v):
 p=D/n;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
old=ref(P/'retire_exact_current118_stopped_container.py');assert old['sha256']=='4179233c5a604b2a5924b98469e0dba5fe782eb76e3ff54286767b69288e4488'
helper=ref(D/'wait_status_compat.py');assert helper['sha256']=='c895898a0a0162d78e521f4ded5ea7c75b46bd47d7764003f31c09d2d2f31d0a'
out=P/'actual-retirement-root1-e984';uncertain=json.loads((out/'UNCERTAIN.json').read_text());receipt=uncertain['commands'][0];raw=json.loads(Path(receipt['path']).read_text())
failure=put('FAILED-ATTEMPT-RETAINED.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='RETAINED_FAILURE_NOT_CUSTODY_CLEARANCE',runtime_authority=None,executor=old,bindings=ref(P/'BINDINGS.json'),uncertain=ref(out/'UNCERTAIN.json'),quarantine=ref(out/'QUARANTINE.json'),command_receipt=receipt,raw=raw['raw'],positive_wait4_recorded=raw['positive_wait4'],returncode_claimed=False,commit_attempted=uncertain['commit_attempted'],owner=dict(pid=2232651,birth=103343097,permanent_mutex=[27,4]),parent=dict(pid=2232650,birth=103343093,tool_session=90401),first_client=dict(pid=2232653,birth=103343210),ownership_reconciliation_required=True,signals_sent=0,retry_authority=None))
b=json.loads((P/'BINDINGS.json').read_text());b.update(wait_status_helper=helper,pre_compatibility_executor=old,failed_current118_retirement_attempt=failure,output_root_parent=str(D))
b['actor_evidence'].append(failure)
b['new_known_actors'].extend([dict(pid=2232651,start=103343097,role='CURRENT118_failed_retirement_quarantine_owner'),dict(pid=2232650,start=103343093,role='CURRENT118_failed_retirement_parent'),dict(pid=2232653,start=103343210,role='CURRENT118_failed_retirement_readonly_client_unproven')])
binding=put('BINDINGS.json',b)
code=Path(old['path']).read_text();original=code
oldhash="BINDINGS_SHA='e402b73ca6b21763228fe14e37a0e7a85c86468280ca6e3693a3c227071e4d1c'";assert code.count(oldhash)==1
code=code.replace(oldhash,"BINDINGS_SHA='"+binding['sha256']+"'")
anchor='def bindings():\n';assert code.count(anchor)==1
code=code.replace(anchor,'WAIT_STATUS_SOURCE='+repr(helper)+'\nWAIT_STATUS_COMPAT=load(WAIT_STATUS_SOURCE,\'current118_portable_wait_status\')\n\n'+anchor)
anchor="b=strict((D/'BINDINGS.json').read_bytes());need(b['scope']==SCOPE and b['runtime_authority'] is None,'source binding is not authority');return b";assert code.count(anchor)==1
code=code.replace(anchor,"b=strict((D/'BINDINGS.json').read_bytes());need(b['scope']==SCOPE and b['runtime_authority'] is None,'source binding is not authority');need(b['wait_status_helper']==WAIT_STATUS_SOURCE,'exact portable wait-status source');return b")
anchor='self.returncode=os.waitstatus_to_exitcode(status)';assert code.count(anchor)==1
code=code.replace(anchor,'self.returncode=WAIT_STATUS_COMPAT.waitstatus_to_exitcode(status)')
anchor="('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor')";assert code.count(anchor)==1
code=code.replace(anchor,"('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor','wait_status_helper','pre_compatibility_executor')")
ast.parse(code);(D/'retire_exact_current118_stopped_container.py').write_text(code)
(D/'MINIMAL-COMPATIBILITY-DIFF.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),code.splitlines(True),fromfile=old['path'],tofile=str(D/'retire_exact_current118_stopped_container.py'))))
print(json.dumps(dict(executor=ref(D/'retire_exact_current118_stopped_container.py'),bindings=binding,helper=helper,failure=failure)))
