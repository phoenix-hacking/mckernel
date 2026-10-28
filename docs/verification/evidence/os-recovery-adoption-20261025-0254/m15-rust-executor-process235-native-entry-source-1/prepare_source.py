"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite original235 data/literal successor of successful Root44 entry contracts.
Source only: no API imports, guard, clock, observation, staging or native execution.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;T=D/'templates';F=D/'root-adopted-process235-entry-1'
P=E/'m15-rust-startup-retirement-native-entry-source-1/publication-files-correction-source-1'
S=E/'m15-rust-executor-process235-stage-preparation-source-1/root-actual-qualified-input-plan-source-1'
H=E/'m15-rust-executor-process235-host-preparation-source-1'
CASE='P-M06-01-process-exec-wait-235B';NONCE='d21f4e17faf1b0b806419b1860bd0598'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
binding=read(S/'COLLECTOR-AND-STAGE-BINDING.json');manifest=read(S/'process235.NEW-COLLECTOR.HOST-BOUND.json');plan=read(S.parent/'STAGE-PLAN.NOT-RELEASED.json');stage=read(S/'ROOT-ACTUAL-SCRATCH-STAGE.json')
assert manifest['case_id']==CASE and manifest['payload']['argv']==['/bin/mcexec','-t','1','0','/apps/app']
assert len(bytes.fromhex(manifest['payload']['oracle']['stdout_hex']))==235
contract=read(E/'m15-mcexec-default-f4d-actual-native-preparation-source-1/SOURCE-BOUND-NATIVE-CONTRACT.json');original=contract['cases'][CASE]
assert manifest['payload']['argv']==original['argv'] and manifest['payload']['env']==original['environment'] and manifest['payload']['oracle']==original['oracle'] and manifest['artifacts']['payload']['sha256']==original['payload']['sha256']
assert stage['source_manifest']==ref(S/'process235.NEW-COLLECTOR.HOST-BOUND.json') and stage['nonce'] is None and stage['reserved_unused_native_nonce']==NONCE
profile=plan['native_profile'];assert profile['guest']==contract['profile']==manifest['profile'];profile_sha=hashlib.sha256((json.dumps(profile,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
# Exact json encoding of the retained oncebridge is preserved.
bridge=(P/'templates/root_once_startup_entry.py').read_text();tree=ast.parse(bridge)
encoded=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='encoded');assert 'sort_keys=True' in ast.get_source_segment(bridge,encoded)
free=read(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER45.json')['latest_accepted_free_boundary'];assert free['sha256'].startswith('0ae5')
current=read(free['path']);exact=current['fresh_current']['exact_observation'];actualexact=read(exact['path']);assert current['nonce']=='22a1d92ed402f4d333bf527185e792b2' and actualexact['actual_Docker_commands']==30 and len(actualexact['actors'])==33
p=read(P/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')
replacements={str(P):str(D),'root-adopted-retirement-entry-1':'root-adopted-process235-entry-1','22a1d92ed402f4d333bf527185e792b2':NONCE,'/scratch/m15str1':'/scratch/m15p235','startup.argv-empty':CASE}
def mapped(s):
 for a,b in replacements.items():s=s.replace(a,b)
 return s
p=json.loads(mapped(json.dumps(p)))
for key,bkey in [('collector','collector'),('compiled_collector_adoption','Root_collector_adoption'),('compiled_collector_caseprofile','compiled_profile'),('compiled_collector_facts','compiled_facts'),('overlay','overlay'),('overlay_manifest','actual_receipt')]:p[key]=ref(binding[bkey]['path'])
p['compiled_collector_HOST_acceptance']=ref(H/'independent-actual-review-1/REVIEW.json');assert p['compiled_collector_HOST_acceptance']['sha256'].startswith('c532')
p['composed_case_binding']=ref(S/'COLLECTOR-AND-STAGE-BINDING.json');p['payload']=ref(manifest['artifacts']['payload']['path']);p['expected_case']=CASE;p['expected_guest_argv']=manifest['payload']['argv'];p['expected_oracle']=manifest['payload']['oracle'];p['profile']=profile
p['offline_manifest']=ref(S/'process235.NEW-COLLECTOR.HOST-BOUND.json');p['manifest']=ref(stage['scratch_manifest']['path']);p['scratch_manifest_stage']=ref(S/'ROOT-ACTUAL-SCRATCH-STAGE.json');p['stage_result']=p['scratch_manifest_stage'];p['attempt_parent']=stage['planned_attempt_parent'];p['planned_attempt_parent']=stage['planned_attempt_parent'];p['latest_serial_operation_physical_acceptance']=free;p['root_ledger35']=None;p['nonce_reservation']=None;p['stage_map_acceptance']=None;p['source_only_QMPproof']=None;p['status']='SOURCE_ONLY_ORIGINAL235_ROOT46_BOUNDARY_PENDING_NOT_RUNTIME_RELEASE'
for k in ['source_authority','case_capability','capture_helper','capture_sources','author','root_runtime_grant','source_publication','runtime_authority']:p[k]=None
put('STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p)
rows=[]
for old in (P/'templates').glob('*.py'):
 s=mapped(old.read_text())
 if old.name=='root_once_startup_entry.py':
  s=s.replace("PROFILE_SHA = 'e5584b2c6fecbec0660dfeda3193468cf78af6a9dee0f4cc849e64abbdca1081'","PROFILE_SHA = "+repr(profile_sha))
 if old.name=='prepare_startup_bindings.py':
  s=s.replace('==91','==235').replace('==22','==26').replace('original91B','original235B').replace('all22','all26').replace('retirement startup producer','original235 producer').replace('33c11bb60d337a2a8dd99fbb3b5d4cf9522f44996d3b36080dfd534f38dc6144',p['collector']['sha256']).replace("==45 and ledger", "=='ROOT_CURRENT_CONSUMED_COUNT' and ledger").replace('Root44/free','Root46/free')
 if old.name=='capture_fresh_startup_resource.py':
  s=s.replace('ROOT-CURRENT-NONCE-LEDGER44.json','ROOT-CURRENT-NONCE-LEDGER46.json').replace('00ed4748c3cc06b67526d716c1ca0adb8ba31965c7c3d16e6325aceb612d3f0c','ROOT_CURRENT_LEDGER_SHA256')
  s=s.replace("== 45\n","== 'ROOT_CURRENT_CONSUMED_COUNT'\n")
  marker='def main():\n';extra='ROOT_CURRENT_FREE = '+repr(free)+'\nROOT_CURRENT_EXACT = '+repr(exact)+'''\n\ndef validate_latest_native_current():
    review=checked(ROOT_CURRENT_FREE);exact=checked(ROOT_CURRENT_EXACT)
    assert review['decision']=='PASS_POSITIVE_CORRECTED_STARTUP_NATIVE_OPERATION_RETIREMENT_AND_CURRENT_FREE'
    assert review['independent'] is True and review['implementation_ownership'] is False and review['current_free'] is True and review['normal_owned_retirement'] is True
    assert review['nonce']=='22a1d92ed402f4d333bf527185e792b2' and review['nonce_consumed'] is True
    assert review['actual_statuses']['capture_returncode']==review['actual_statuses']['bridge_returncode']==0
    owner=review['actual_statuses']['owner_result'];assert owner['status']=='PROTOCOL_PASS' and owner['absence_verified'] is True and owner['lease_retained'] is False
    assert review['owned_client_retirement']['actual_commands']==exact['actual_Docker_commands']==30
    assert review['owned_client_retirement']['all_exact_reaped'] is True and review['owned_client_retirement']['all33_owned_actor_PIDs_and_PGRPs_absent'] is True
    assert exact['all33_actor_PID_and_PGRP_absent'] is True and len(exact['actors'])==33 and not exact['census_errors']
    assert review['fresh_current']['exactCID_name_label_absent'] is True and review['fresh_current']['no_running_containers'] is True and review['fresh_current']['pids_current']==0 and not review['fresh_current']['census_errors']
    return review,exact

'''
  s=s.replace(marker,extra+marker)
  s=s.replace("ledger['latest_accepted_free_boundary'] == ROOT42_FREE","ledger['latest_accepted_free_boundary'] == ROOT_CURRENT_FREE")
  s=s.replace("static['latest_serial_operation_physical_acceptance'] == ROOT42_FREE","static['latest_serial_operation_physical_acceptance'] == ROOT_CURRENT_FREE")
  s=s.replace('actual_latest_operation_postjoin_acceptance=ROOT42_FREE','actual_latest_operation_postjoin_acceptance=ROOT_CURRENT_FREE')
  s=s.replace('        latest40 = checked(', '        latest_native,latest_native_exact=validate_latest_native_current()\n        latest40 = checked(',1)
  needle="        memory = {line.split(':')[0]"
  block='''        latest_native_queries=[]
        for actor in latest_native_exact['actors']:
            assert not Path('/proc',str(actor['pid'])).exists()
            assert not any(x['pid']==actor['pid'] or x['pgrp'] in [actor['pid'],actor['pgid']] for x in census['rows'])
        for retained in latest_native_exact['queries']:
            child=subprocess.run(retained['argv'],capture_output=True,text=True,timeout=15)
            assert child.returncode==retained['returncode'] and child.stdout==retained['stdout'] and child.stderr==retained['stderr']
            latest_native_queries.append(dict(argv=retained['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
'''
  assert needle in s;s=s.replace(needle,block+needle,1)
  s=s.replace('latest_root42=ROOT42_FREE,','latest_native_current=ROOT_CURRENT_FREE,latest_native_exact=ROOT_CURRENT_EXACT,latest_native_actual33_actor_controls=latest_native_exact[\'actors\'],latest_native_exact_queries=latest_native_queries,latest_root42=ROOT42_FREE,')
 ast.parse(s);(T/old.name).write_text(s);(D/(old.name+'.diff')).write_text(''.join(difflib.unified_diff(old.read_text().splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(T/old.name))))
 rows.append(dict(name=old.name,retained=ref(old),template=ref(T/old.name)))
put('SOURCE-CONTEXT.json',dict(scope=__doc__.splitlines()[0],status='SOURCE_ONLY_ORIGINAL235_CURRENT_LEDGER_FILL_PENDING',helper_sources=rows,successful_Root44_READY=ref(P/'READY.json'),latest_current_free=free,planned_Root46_path=str(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER46.json'),actual_Root46=None,nonce=NONCE,compiled_controls=26,collector=p['collector'],manifest=p['offline_manifest'],actual_stage=ref(S/'ROOT-ACTUAL-SCRATCH-STAGE.json'),caseprofile=p['compiled_collector_caseprofile'],original_contract=p['executor_contract'],original235_stage_plan=ref(S.parent/'STAGE-PLAN.NOT-RELEASED.json'),native_profile_sha256=profile_sha,native_profile_derivation='exact original235 STAGE-PLAN.native_profile; guest equals original0e3a profile and actual235 manifest. Equal resource-profile digest to another case does not substitute its case/argv/collector/oracle.',runtime_authority=None))
put('ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json',dict(scope=p['scope'],author=None,nonce=NONCE,root_ledger=None,latest_free=free,actual_release_ledger_is_latest=None,Root_attests_no_intervening_operation_since_boundary=None,source_authority=None,case_capability=None,stage_map_acceptance=None,nonce_reservation=None,scratch_manifest_stage=p['scratch_manifest_stage'],current_capture_independent_source_review=None,current_capture_source=None,runtime_authority=None,planned_root_ledger_path=str(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER46.json')))
qmp=str(Path(stage['planned_attempt_parent'])/('attempt-'+NONCE)/'qmp.sock');assert len(qmp.encode())<108;put('QMP-ABSOLUTE-PATH-PREFLIGHT.SOURCE-ONLY.json',dict(scope=p['scope'],path=qmp,encoded_bytes=len(qmp.encode()),limit_exclusive=108,source_receipt=p['scratch_manifest_stage'],actual_socket_created=False))
put('ROOT-PUBLICATION-FILES-SCHEMA.NOT-AUTHORITY.json',dict(scope=p['scope'],required_actual_status='PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS',required_actual_key='files',required_actual_type='list of exact path/bytes/sha256 refs including static and every capture source',rows_is_not_alias=True,runtime_authority=None,orchestration_requirement='Resource wrapper rc0 + positive join + real resource and pending files BEFORE bridge. Any failure: STOP; preserve refusal and namespace; no bridge.'))
print('PASS source-only original235 sixhelper proposal; Root46/refcount/review/authority remain unbound')
