"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Same bounded read-only qualification methods, new candidate hash and fresh attempt2.
"""
from pathlib import Path
import ast,hashlib,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7};OLD=D.parent/'maintenance-source/readonly-qualification';Q=D/'readonly-qualification-attempt2';Q.mkdir(mode=0o700)
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
g=ref(D/'grow_scratch.py');sha=g['sha256'];oldsha='932f92710d7fb5dfd7bc4e66eedb9684059dd9b328bad7ae3a7c3edf872b3a84'
a=(OLD/'query_installed.py').read_text();b=a.replace(str(D.parent/'maintenance-source/grow_scratch.py'),str(D/'grow_scratch.py')).replace(oldsha,sha);assert b!=a
query=Q/'query_installed.py';query.write_text(b);ast.parse(b);qsha=ref(query)['sha256']
c=(OLD/'capture_query.py').read_text();oldq='f0db6e0338cb5e8b806cc2a0fd926fc7ccde1b79adfce0b9bfaf48d1eae255cf';assert oldq in c
capture_root='/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/readonly-qualification-attempt-2'
c=c.replace(oldq,qsha).replace('readonly-qualification-attempt-1','readonly-qualification-attempt-2');capture=Q/'capture_query.py';capture.write_text(c);ast.parse(c)
profile=(OLD/'READONLY-PROFILE.md').read_text().replace(str(OLD),str(Q)).replace(str(D.parent/'maintenance-source/grow_scratch.py'),str(D/'grow_scratch.py')).replace(oldsha,sha).replace(oldq,qsha).replace('readonly-qualification-attempt-1','readonly-qualification-attempt-2')
(Q/'READONLY-PROFILE.md').write_text(profile)
frozen=json.loads((OLD/'FROZEN-ARGV.json').read_text());frozen.update(approved_snapshot_sha256=sha,fresh_capture=capture_root,status='EXPERT_DERIVED_ATTEMPT2_PREPARATION_ONLY_NOT_EXECUTION_RELEASED',privileged_execution_performed=False,mutation_released=False)
frozen['ordinary_parent_argv'][-1]=str(capture);frozen['root_argv'][-1]=str(query);frozen['source_files']=[ref(p)for p in (query,capture,Q/'READONLY-PROFILE.md')]
frozen['expert_failure_history']='Original candidate1 + correctioncandidate2 exhausted; express expert escalation prescribes typed ASCII major:minor padding decoder only. Actual attempt1failed loopbinding on padded fields; candidate3 requires fresh independent expert review before attempt2. No automatic retry.'
frozen['required_independent_expert_review']=None;write(Q/'FROZEN-ARGV.json',frozen)
write(D/'LOCAL-PASS-AND-NEXT-QUERY.json',dict(scope=__doc__.splitlines()[0],status='PASS_34_LOCAL_TESTS_NEXT_READONLY_QUERY_PREPARED_PENDING_EXPERT_REVIEW',candidate2_preserved=ref(D/'candidate2.grow_scratch.py'),candidate3=g,actual_failed_report=ref(D/'FAILED-READONLY-REPORT1.raw.json'),actual_losetup_fixture=ref(D/'ACTUAL-LOSETUP1.raw.json'),local_tests=dict(count=34,existing_reused=27,new_actual_parser_snapshot_regressions=7,stdout=ref(D/'local-tests.stdout'),stderr=ref(D/'local-tests.stderr'),qualification='Snapshot tests other than the captured raw major:minor fields use synthetic headers/metadata; no live header qualification.'),next_query_frozen=ref(Q/'FROZEN-ARGV.json'),family='EXPRESS_EXPERT_ESCALATION prescribed candidate3; no further edit/retry after new failure without review.',root_Docker_query_resize_operations=0,mutation_authorized=False,execution_released=False))
print(json.dumps(dict(candidate3=g,query=ref(query),capture=ref(capture),frozen_argv=ref(Q/'FROZEN-ARGV.json'))))
