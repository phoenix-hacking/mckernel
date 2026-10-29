"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/retained-data preparation only; no actual process or guard query.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;OLD=E/'CURRENT118-normal-retirement-preparation-1';C=OLD/'compatibility-source-1'
SC=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1200-pacific-1')
R=E/'m14-next118-restart-independent-review-20261028-1/CURRENT118-FAILED-RETIREMENT-OWNER-RECONCILIATION-1'
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def put(n,v):
 p=D/n;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
facts=read(R/'FACTS.json');started=read(OLD/'actual-retirement-root1-e984/STARTED.json');cb=read(C/'BINDINGS.json');controls=read(SC/'ACTUAL-CONTROLS-ARMED.json')
primitive=facts['primitive'];assert primitive['sha256']=='3fdb4dde4dbbd5d07d85d68c02e68d4aee3acca45dce12be3479f3252765abd6'
exe=ref('/usr/bin/python3.8');st=Path(exe['path']).stat()
profile=dict(scope=cb['scope'],status='SOURCE_PROFILE_NOT_EXECUTION_RELEASE',runtime_authority=None,historical_release_inapplicable=True,bound_guard=dict(pid=2232651,starttime='103343097',parent_pid=2232650,parent_birth='103343093',boot_id=cb['boot'],uid=1000,gid=1000,threads=1,pgrp=2232651,session=2232651,exe=exe['path'],exe_device=st.st_dev,exe_inode=st.st_ino,exe_size=exe['bytes'],exe_sha256=exe['sha256'],source=facts['executor']['path'],source_sha256=facts['executor']['sha256'],argv=['/usr/bin/python3','-I','-B',facts['executor']['path'],'--release',started['release']['path'],'--release-sha256',started['release']['sha256'],'--execute'],root_lock=dict(path='/run/lock/mckernel-development.lock',device=27,inode=4,fd=4),parent_exe=facts['actual_parent']['exe'],parent_threads=1,parent_pgrp=facts['actual_parent']['pgrp'],parent_session=facts['actual_parent']['session']),first_readonly_client=dict(pid=2232653,birth='103343210',status='UNKNOWN',positive_wait4=False,group_absent_recorded=True,streams_closed_recorded=True),nonce=cb['nonce'],CID=cb['cid'],NAME=cb['name'],mutation_scope='ONE_PIDFD_BOUND_IDLE_FAILED_HELPER_ONLY_CONTAINER_UNCHANGED',parent_positive_join_mandatory=True,native_acceptance=False,current_free=False)
pr=put('PROFILE.SOURCE-ONLY.json',profile)
protected=[ref(R/'FACTS.json'),ref(R/'REVIEW.json'),started['release'],facts['executor'],facts['bindings'],facts['started'],facts['uncertain'],facts['quarantine'],facts['client_receipt'],facts['client_status'],facts['client_stdout'],facts['client_stderr'],cb['protected'],cb['packet'],cb['failed_current118_retirement_attempt'],cb['parent_tool_join'],exe]
protected.extend({k:x[k] for k in ('path','bytes','sha256')} for x in read(cb['protected']['path'])['records'] if x['kind']=='file')
unique=list({x['path']:x for x in protected}.values())
b=dict(scope=cb['scope'],runtime_authority=None,profile=pr,primitive=primitive,historical_profile=ref(E.parent/'scratch22-authority1-root-quarantine-recovery-independent-review-20261017.json'),transport_executor=ref(C/'retire_exact_current118_stopped_container.py'),transport_bindings=ref(C/'BINDINGS.json'),portable_converter=cb['wait_status_helper'],guardian=cb['guardian'],controls=ref(SC/'ACTUAL-CONTROLS-ARMED.json'),earliest_caps=ref(SC/'EARLIEST-CONTROL-CAPS.json'),reconciliation_facts=ref(R/'FACTS.json'),reconciliation_review=ref(R/'REVIEW.json'),protected=unique,deny_targets=[dict(role=k,pid=v['pid'],birth=v['start']) for k,v in controls['actors'].items()],prior_actors=cb['prior_actors']+cb['new_known_actors'][:10],unknown_client=2232653,cutoffs=cb['cutoffs'],boot=cb['boot'],signal_budget=1,maximum_invocations=1,normal_retirement_still_required=True,parent_tool=90401,parent_positive_join_mandatory=True,failed_client_status='UNKNOWN',keep_container_and_outputs=True)
assert len(b['deny_targets'])==6 and all(x['pid']!=profile['bound_guard']['pid'] for x in b['deny_targets'])
print(json.dumps(dict(bindings=put('BINDINGS.json',b),profile=pr,protected=len(unique))))
