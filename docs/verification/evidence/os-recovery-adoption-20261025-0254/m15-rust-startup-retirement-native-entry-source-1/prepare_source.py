"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Parameterize the existing reviewed startup entry before any fresh capture clock.
"""
from pathlib import Path
import json,hashlib,re,ast,difflib
D=Path(__file__).resolve().parent;E=D.parent
OLD=E/'m15-rust-executor-startup-native-entry-source-1/correct-rust-collector-native-entry-source-1/root40-current-binding-delta-1'
STAGE=E/'m15-rust-startup-retirement-stage-preparation-source-1/root-actual-qualified-input-plan-source-1'
T=D/'templates';T.mkdir(exist_ok=True);F=D/'root-adopted-retirement-entry-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(p,s):
 p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def js(p,x):save(p,json.dumps(x,indent=2)+'\n')
L=ref(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER42.json');assert L['sha256']=='ca862a13e3eeb621b53177d78a21cd932e366efb60a8d838b790c8e75c2d76ee';ledger=json.loads(Path(L['path']).read_text());FREE=ledger['latest_accepted_free_boundary'];assert FREE['sha256']=='221349f9f93973b57c7d6b4a69d79d9f8e6dd2dcd368d16a08fcfac88c054d0d';free=json.loads(Path(FREE['path']).read_text())
p=json.loads((OLD/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_text());stage=json.loads((STAGE/'FULL-MAP-AND-CAPABILITY.TEMPLATE.NOT-RELEASED.json').read_text())
def norm(r):return dict(path=r['path'],bytes=r.get('bytes',r.get('size')),sha256=r['sha256'])
known={'collector':'new_collector_artifact','compiled_collector_adoption':'new_collector_Root_adoption','compiled_collector_caseprofile':'new_collector_profile','compiled_collector_HOST_acceptance':'new_collector_actual_HOST_qualification','compiled_collector_facts':'new_collector_facts'}
for key,field in known.items():p[key]=norm(stage[field])
assert p['collector']['sha256']=='33c11bb60d337a2a8dd99fbb3b5d4cf9522f44996d3b36080dfd534f38dc6144'
unknown=['nonce_reservation','scratch_manifest_stage','stage_map_acceptance','manifest','offline_manifest','overlay','overlay_manifest','composed_case_binding','source_authority','case_capability','source_only_QMPproof']
for k in unknown:p[k]=None
p.update(author=None,status='SOURCE_ONLY_RETIREMENT_COLLECTOR_STAGE_BINDINGS_PENDING',nonce=None,attempt_parent='/home/holden/mckernel-work/scratch/m15str1',planned_attempt_parent='/home/holden/mckernel-work/scratch/m15str1',capture_directory=str(F/'CAPTURE'),root_admission_directory=str(F),root_ledger35=None,latest_serial_operation_physical_acceptance=None,capture_helper=None,capture_sources=None,source_publication=None,root_runtime_grant=None,runtime_authority=None)
for flag,value in [('--manifest','ROOT_ACTUAL_RETIREMENT_MANIFEST_REQUIRED'),('--manifest-sha256','ROOT_ACTUAL_RETIREMENT_MANIFEST_SHA256_REQUIRED'),('--attempt-parent',p['attempt_parent']),('--nonce','ROOT_FRESH_RESERVED_NONCE_REQUIRED')]:p['exact_argv'][p['exact_argv'].index(flag)+1]=value
js('STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p)
# Preserve all original capture predicates and add actual latest114 termination.
cap=(OLD/'templates/capture_fresh_startup_resource.py').read_text();cap=cap.replace("ROOT-CURRENT-NONCE-LEDGER40.json'","ROOT_FUTURE_LEDGER_NAME_REQUIRED'").replace("'30543310425872f739b77fa973b63d4cee8430380413a5b3d3ae388f793ea6d1'","'ROOT_FUTURE_LEDGER_SHA_REQUIRED'").replace("== 40\n","== ROOT_FUTURE_LEDGER_COUNT_REQUIRED\n")
oldfree40=json.loads((OLD/'SOURCE-CONTEXT.json').read_text())['root40_free']
cap=cap.replace("assert ledger['latest_accepted_free_boundary'] == "+repr(oldfree40),"assert ledger['latest_accepted_free_boundary'] == ROOT42_FREE")
cap=cap.replace("static['latest_serial_operation_physical_acceptance'] == "+repr(oldfree40),"static['latest_serial_operation_physical_acceptance'] == ROOT42_FREE")
cap=cap.replace("actual_latest_operation_postjoin_acceptance="+repr(oldfree40),"actual_latest_operation_postjoin_acceptance=ROOT42_FREE")
extra='''
ROOT42_FREE = FREE_LITERAL
ROOT41_OBSERVER = OBSERVER_LITERAL

def validate_root42_latest(review):
    assert review['decision']=='PASS_POSITIVE_CURRENT114_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX'
    assert review['independent'] is True and review['implementation_ownership'] is False and review['current_free'] is True and review['normal_owned_retirement'] is True
    assert review['holder']=={'path':'/run/lock/mckernel-development.lock','pid':1763445,'starttime':94341647,'device':27,'inode':4,'fd':3}
    assert review['runner']=={'pid':1763997,'starttime':94348302,'returncode':0,'joined':True}
    assert review['retained_stopped_container']=='d521e2f29e9df27a258f83f22f45f7e959e4cc35be4227b6f742ece9a15ce7ca'
    assert checked(review['runner_join'])==review['runner']
    local=checked(review['local_terminal']);assert local['joined'] is True and local['returncode']==0 and local['holder']==review['holder']
    tool=checked(review['holder_tool_result']);assert tool['positive_tool_completion'] is True and tool['observed_terminal']['exit_code']==0
    terminal=review['container_terminal'];assert terminal['container']==review['retained_stopped_container'] and terminal['returncode']==0 and terminal['state']['Running'] is False and terminal['state']['Pid']==0 and terminal['state']['ExitCode']==0 and terminal['state']['OOMKilled'] is False
    assert review['positive_termination']['actual4_command_returncodes']==[0,0,0,0] and review['positive_termination']['runner_positive_wait'] is True and review['positive_termination']['holder_tool_positive_terminal'] is True
    assert review['fresh_current']['new_groups_absent'] is True and not review['fresh_current']['proc_census_errors'] and review['fresh_current']['startup25clients_reaped'] is True
    assert len(review['fresh_current']['startup28actors_absent'])==28
    return terminal

'''.replace('FREE_LITERAL',repr(FREE)).replace('OBSERVER_LITERAL',repr(free['fresh_current']['exact_Root41_observer']))
cap=cap.replace('def main():',extra+'def main():',1)
cap=cap.replace("latest40_controls = validate_root40_latest(latest40)","latest40_controls = validate_root40_latest(latest40)\n        latest42 = checked(ROOT42_FREE); latest42_terminal = validate_root42_latest(latest42)",1)
anchor="        memory = {line.split(':')[0]:int(line.split()[1])*1024"
add='''        # Existing Root41 observer keeps exact failed-startup25/28 and all86 prior controls.
        assert ref(Path(ROOT41_OBSERVER['path']))==ROOT41_OBSERVER
        root41_child=subprocess.run(['/home/holden/anaconda3/bin/python3','-I','-B',ROOT41_OBSERVER['path']],capture_output=True,timeout=40)
        assert root41_child.returncode==0 and not root41_child.stderr
        root41_current=json.loads(root41_child.stdout)
        assert root41_current['status']=='PASS_ROOT41_EXACT_FAILED_STARTUP_CURRENT_PENDING_ROOT_ACCEPTANCE' and root41_current['new_exact25_clients_reaped'] is True and len(root41_current['new_exact28_actors'])==28
        assert root41_current['known_numeric_controls_absent']==latest42['fresh_current']['prior_controls_preserved']
        assert not root41_current['group_membership_observation']['errors']
        for actor in [latest42['holder'],latest42['runner']]:
            assert not Path('/proc',str(actor['pid'])).exists()
            assert not any(x['pid']==actor['pid'] or x['pgrp']==actor['pid'] for x in census['rows'])
            assert not any(x['pid']==actor['pid'] or x['pgrp']==actor['pid'] for x in root41_current['group_membership_observation']['rows'])
        retained114=subprocess.run(prefix+['inspect',latest42['retained_stopped_container']],capture_output=True,text=True,timeout=15)
        assert retained114.returncode==0 and not retained114.stderr
        retained114_state=json.loads(retained114.stdout);assert len(retained114_state)==1 and retained114_state[0]['Id']==latest42['retained_stopped_container']
        assert retained114_state[0]['State']['Running'] is False and retained114_state[0]['State']['Pid']==0 and retained114_state[0]['State']['ExitCode']==0 and retained114_state[0]['State']['OOMKilled'] is False
'''
assert anchor in cap;cap=cap.replace(anchor,add+anchor,1)
cap=cap.replace("current_physical_observation=current,", "latest_root42=ROOT42_FREE,retained_current114_terminal=latest42_terminal,root41_historical_current=root41_current,retained114_current_query=dict(argv=prefix+['inspect',latest42['retained_stopped_container']],returncode=retained114.returncode,stdout=retained114.stdout,stderr=retained114.stderr),current_physical_observation=current,",1)
save('templates/capture_fresh_startup_resource.py',cap)
for name in ['run_native_startup_capture.py','prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py','root_once_startup_entry.py']:
 source=(OLD/'templates'/name).read_text();source=source.replace(str(OLD),str(D)).replace('root-adopted-correct-entry-1','root-adopted-retirement-entry-1')
 if name=='prepare_startup_bindings.py':source=source.replace('d0bf61dc45754e72d3ebab34853756c6ce5cce0c9e84ac1713122ba1cf8f0d5a',p['collector']['sha256']).replace("['actual_test_count']==16","['actual_test_count']==22").replace("['consumed_nonces'])==40","['consumed_nonces'])==ROOT_FUTURE_LEDGER_COUNT_REQUIRED").replace('exact Root40/free boundary','exact actual Root42-or43/free boundary')
 if name=='root_once_startup_entry.py':source=source.replace("NONCE = '6d2e6c210f8bf62b1a4f1abc127fb09a'","NONCE = 'ROOT_FINAL_NONCE_REQUIRED'")
 save('templates/'+name,source)
# Explicit field list consumed only by Root final-fill, never guessed stage hashes.
js('SOURCE-CONTEXT.json',dict(scope=__doc__.splitlines()[0],runtime_authority=None,status='PARAMETERIZED_SOURCE_ONLY_ACTUAL_STAGE_REFS_PENDING',original_context=ref(OLD/'READY.json'),Root42=L,current_free=FREE,stage_source=ref(STAGE/'SOURCE-READY.json'),qualified_stage_plan=ref(STAGE/'STAGE-PLAN.NOT-RELEASED.json'),collector=p['collector'],HOST22=p['compiled_collector_HOST_acceptance'],facts22=p['compiled_collector_facts'],future_stage_fields=unknown,future_nonce=None,Root43_explicit_binding_allowed_if_ordinary_compose_recorded=True,attempt_parent=p['attempt_parent'],fixed_case_argv=p['expected_guest_argv'],fixed_oracle=p['expected_oracle'],fixed_kernel=p['expected_new_image_sha256'],fixed_executor=p['expected_executor_sha256'],owner=p['owner_source'],evaluator=p['evaluator_source'],helper_sources=[dict(name=x.name,retained=ref(OLD/'templates'/x.name),template=ref(x)) for x in sorted(T.glob('*.py'))]))
qmp=p['attempt_parent']+'/attempt-'+'0'*32+'/qmp.sock';assert len(qmp.encode())<108
js('QMP-ABSOLUTE-PATH-PREFLIGHT.SOURCE-ONLY.json',dict(scope=__doc__.splitlines()[0],status='PASS_SOURCE_UNIVERSAL_FRESH32HEX_NONCE_PATH',absolute_socket_path_for_length_proof=qmp,encoded_bytes=len(qmp.encode()),limit_exclusive=108,nonce_is_reserved=False,QMP_argument='unix:'+qmp+',server=on,wait=off',guard_bound_owner=p['owner_source'],actual_Root_full_QMP_and_owner_API_proof_required_before_capture=True))
for path in T.glob('*.py'):ast.parse(path.read_text())
print(json.dumps(dict(status='parameterized reviewed helpers prepared',qmp_path_bytes=len(qmp.encode()),actual_stage_fields='NULL',guard_query_runtime=0)))
