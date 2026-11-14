"""Finite source/DATA constructor; no imports of produced code or child operations.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run only under a dispatcher ordinary grant. No root/Docker/guest/census operation.
"""
from pathlib import Path
import ast, copy, hashlib, json, os, stat, importlib.util, subprocess, socket
D=Path(__file__).resolve().parent; R=Path('/home/holden/mckernel-work/host-preparation/m07-sigill-image-only-stage-preparation-20261022-1/ordinary-normalization-preparation-1'); H=Path('/home/holden/mckernel-work/host-preparation')
B=H/'M07-current-profile-next-observation-preparation-20261021-1/boot-challenge-producer-correction-1/normalization-runtime-preparation-1/runtime-construction-source-5/bound-runtime-source-1'
G=H/'current-focused-progress-recording-20261021-1/current-normalization-review-recording-1/M07-SIGILL-ACTUAL-PAIRED-ALIAS-NORMALIZATION-ACCEPTANCE.json'
P=None # Genuine new independent physical report is a mandatory late input.
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def need(v,s):
 if not v:raise ValueError(s)
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 raw=v.encode() if isinstance(v,str) else (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
 with p.open('xb') as f:f.write(raw)
 p.chmod(0o600)
def once(s,a,b):need(s.count(a)==1,'unique qualified source boundary '+a[:90]);return s.replace(a,b)
def function_replace(s,name,new):
 n=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name==name);lines=s.splitlines(True);lines[n.lineno-1:n.end_lineno]=[new+'\n'];return ''.join(lines)
def accepted_current_normalization(acceptance, root):
    root=Path(root);a=json.loads(Path(acceptance).read_bytes())
    need(ref(acceptance)['sha256']=='675277e49541894244498e34eae7d93aab87d3e3215b53d98e565969a449becb','genuine current normalization authority')
    need(a['decision']=='PASS_ACTUAL_PAIRED_ALIAS_NORMALIZATION_BINDINGS_ONLY' and a['implementation_ownership'] is False and a['reviewer'] and a['source_review_projection_permission'] is True and a['native_permission'] is False and a['native_credit']==0 and a['runtime_release'] is None,'current bounded normalization review')
    paths={'preflight':root/'ACTUAL-NATIVE-PREFLIGHT.json','binding':root/'ACTUAL-BINDING.json','provenance':root/'ACTUAL-PAIRED-ALIAS-PROVENANCE.json','source_closure':root/'BOUND-RUNTIME-SOURCE-ONLY.json'}
    binding=json.loads(paths['binding'].read_bytes());paths['manifest']=Path(binding['manifest']['path'])
    need(set(a['accepted_refs'])==set(paths),'complete current accepted reference set')
    for key,path in paths.items():
        observed=ref(path);need(a['accepted_refs'][key]==observed['sha256']+'/'+str(observed['bytes']),'current accepted whole descriptor '+key)
    need(isinstance(a['verified'],list) and len(a['verified'])==4 and all(isinstance(x,str) and x for x in a['verified']),'current review verified facts')
    return a

def accepted_current_stage(acceptance, manifest):
    need(ref(acceptance)['sha256']=='f0243ce2e3bbbd2c09de0b0b4296895aea15ff815a80db4d04f654dca2762aa5','genuine current image-only stage authority')
    a=json.loads(Path(acceptance).read_bytes());v=a['accepted_boundary']
    need(a['decision']=='PASS_ACTUAL_CBB_IMAGE_ONLY_OFFLINE_STAGE_AND_MANIFEST_ONLY' and a['implementation_ownership'] is False and a['reviewer'] and a['findings']==[],'current image-only stage review')
    need(v['members']==60 and v['unchanged_members']==59 and v['sole_changed_member']=='images/mckernel.img' and v['changed_fields']==['size','sha256'] and v['all_other_metadata_preserved'] is True and v['producer_overlay_manifest_maps_equal'] is True and v['manifest_image_base_overlay_joins_match'] is True,'exact image-only stage boundary')
    need(ref(a['manifest']['path'])==a['manifest'],'complete actual stage manifest descriptor')
    image=manifest['artifacts']['mckernel_image'];need(image['sha256']==v['image_sha256'] and image['size']==v['image_bytes'],'normalization accepted staged image joins')
    need(a['physical_acceptance'] is None and a['execution_release'] is None and a['native_credit_delta']==0,'stage grants no physical or execution authority')
    return a

CURRENT_AUTHORITY_HELPER="def accepted_current_normalization(acceptance, root):\n    root=Path(root);a=json.loads(Path(acceptance).read_bytes())\n    need(ref(acceptance)['sha256']=='675277e49541894244498e34eae7d93aab87d3e3215b53d98e565969a449becb','genuine current normalization authority')\n    need(a['decision']=='PASS_ACTUAL_PAIRED_ALIAS_NORMALIZATION_BINDINGS_ONLY' and a['implementation_ownership'] is False and a['reviewer'] and a['source_review_projection_permission'] is True and a['native_permission'] is False and a['native_credit']==0 and a['runtime_release'] is None,'current bounded normalization review')\n    paths={'preflight':root/'ACTUAL-NATIVE-PREFLIGHT.json','binding':root/'ACTUAL-BINDING.json','provenance':root/'ACTUAL-PAIRED-ALIAS-PROVENANCE.json','source_closure':root/'BOUND-RUNTIME-SOURCE-ONLY.json'}\n    binding=json.loads(paths['binding'].read_bytes());paths['manifest']=Path(binding['manifest']['path'])\n    need(set(a['accepted_refs'])==set(paths),'complete current accepted reference set')\n    for key,path in paths.items():\n        observed=ref(path);need(a['accepted_refs'][key]==observed['sha256']+'/'+str(observed['bytes']),'current accepted whole descriptor '+key)\n    need(isinstance(a['verified'],list) and len(a['verified'])==4 and all(isinstance(x,str) and x for x in a['verified']),'current review verified facts')\n    return a\n\ndef accepted_current_stage(acceptance, manifest):\n    need(ref(acceptance)['sha256']=='f0243ce2e3bbbd2c09de0b0b4296895aea15ff815a80db4d04f654dca2762aa5','genuine current image-only stage authority')\n    a=json.loads(Path(acceptance).read_bytes());v=a['accepted_boundary']\n    need(a['decision']=='PASS_ACTUAL_CBB_IMAGE_ONLY_OFFLINE_STAGE_AND_MANIFEST_ONLY' and a['implementation_ownership'] is False and a['reviewer'] and a['findings']==[],'current image-only stage review')\n    need(v['members']==60 and v['unchanged_members']==59 and v['sole_changed_member']=='images/mckernel.img' and v['changed_fields']==['size','sha256'] and v['all_other_metadata_preserved'] is True and v['producer_overlay_manifest_maps_equal'] is True and v['manifest_image_base_overlay_joins_match'] is True,'exact image-only stage boundary')\n    need(ref(a['manifest']['path'])==a['manifest'],'complete actual stage manifest descriptor')\n    image=manifest['artifacts']['mckernel_image'];need(image['sha256']==v['image_sha256'] and image['size']==v['image_bytes'],'normalization accepted staged image joins')\n    need(a['physical_acceptance'] is None and a['execution_release'] is None and a['native_credit_delta']==0,'stage grants no physical or execution authority')\n    return a\n"
def patch_pending_physical(binder):
    start=binder.index("P=Path(c['latest_physical']['path'])")
    end=binder.index("prop=transform",start)
    binder=binder[:start]+"""physical_pending=c['latest_physical'] is None
need(not final or not physical_pending,'genuine independent physical acceptance required before final binding')
whole_ref=c['native_predecessor_binding'];need(ref(whole_ref['path'])==whole_ref,'exact distinct native/native/build role data')
roles=load(whole_ref['path']);decoderref=roles['released_record_projection_source'];predecessor=roles['physical_predecessor']
need(set(predecessor)=={'boot_id','filesystem_uuid','container_id','owner_nonce','lease_path','common_exclusion','shared_heavy'},'existing seven-field predecessor interface')
if physical_pending:
 P=None
 need(roles['physical_review'] is None and roles['native_controller_source'] is None and roles['native_controller_pair'] is None and all(v is None for v in predecessor.values()),'no fabricated physical authority in pending packet')
else:
 P=Path(c['latest_physical']['path']);need(ref(P)==c['latest_physical'] and roles['physical_review']==ref(P),'genuine latest physical report')
 spec=importlib.util.spec_from_file_location('actual_native_terminal_source',D/'root_manual_snapshot_threads.py');snapshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot)
 snapshot.terminal_joins(load(P),roles)
 need(all(not os.path.lexists(predecessor[k]) for k in ['lease_path','common_exclusion','shared_heavy']),'current native ownership records absent')
def physical_ref():return dict(path=None,sha256=None,bytes=None) if physical_pending else ref(P)
"""+binder[end:]
    binder=binder.replace("terminal_cleanup_and_common_shared_release=dict(status='PASS',ref=physical_ref())","terminal_cleanup_and_common_shared_release=dict(status='PENDING_GENUINE_PHYSICAL_ACCEPTANCE' if physical_pending else 'PASS',ref=physical_ref())")
    return binder

def main():
 g=accepted_current_normalization(G,R)
 out=D/'bound-runtime-source-expert-correction-1';need(not os.path.lexists(out),'fresh constructor output');out.mkdir(mode=0o700);(out/'native-packet-1').mkdir(mode=0o700)
 c=load(B/'STATIC-NONTEMPORAL-INPUTS.json');pre=load(R/'ACTUAL-NATIVE-PREFLIGHT.json');closure=load(R/'BOUND-RUNTIME-SOURCE-ONLY.json');binding=load(R/'ACTUAL-BINDING.json');manifest=load(binding['manifest']['path'])
 # A separate explicit projection adds the existing consumer fields. Original stays immutable.
 nine=pre['parent_nine_field_identity'];five=dict(device=nine['st_dev'],inode=nine['st_ino'],uid=nine['st_uid'],gid=nine['st_gid'],mode=oct(stat.S_IMODE(nine['st_mode'])))
 rootargv=['/usr/bin/sudo','-A',c['interpreter']['path'],'-I','-B']+pre['owner_argv'][2:]
 # Reuse accepted normalization's real owner loader. Never treat raw JSON as its canonical view.
 def forbid(*args,**kwargs):raise AssertionError('pure canonical source constructor: no child/socket/exec')
 subprocess.Popen=forbid;subprocess.run=forbid;socket.socket=forbid;os.execve=forbid
 owner_path=Path(closure['owner']['path']);need(ref(owner_path)['sha256']==closure['owner']['sha256'],'actual accepted owner bytes')
 spec=importlib.util.spec_from_file_location('outer_correction_real_accepted_owner',owner_path);actual_owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(actual_owner)
 actual_nd,canonical=actual_owner.bound_manifest(binding['manifest']['path'],binding['manifest']['sha256'])
 expected_canonical=copy.deepcopy(manifest);need('append' not in expected_canonical['profile'],'actual raw append absent')
 expected_canonical['profile']['append']=actual_nd.APPEND
 need(actual_nd._same_plan(actual_nd._freeze(expected_canonical),actual_nd._freeze(actual_nd._thaw(canonical))),'complete raw plus ONLY actual accepted loader APPEND default equals canonical')
 need(actual_owner.SOURCE_HASHES==closure['source_hashes'],'complete accepted owner source binding')
 projected=dict(pre,root_owner_argv=rootargv,parent_identity=five,validated_manifest_view=actual_nd._thaw(canonical),raw_manifest_view=manifest,raw_manifest_descriptor=binding['manifest'],original_preflight=ref(R/'ACTUAL-NATIVE-PREFLIGHT.json'),projection_kind='FINITE_EXISTING_CONSUMER_DATA_FIELDS_PLUS_REAL_OWNER_CANONICAL_VIEW')
 write(out/'ACTUAL-PREFLIGHT-CONSUMER-PROJECTION.json',projected)
 roles=load(Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/remaining-components-functional-case-preparation-20261022-1/joint-mpx-exact-fault-correction-1/current053d-stage-preparation-1/ordinary-normalization-runtime-integration-1/outer-runtime-preparation-1/bound-runtime-control-closure-correction-1/current-normal9-role-binding-1/CURRENT-NATIVE-AND-RELEASED-BUILD-ROLES.json'))
 roles.update(physical_review=None,native_controller_source=None,native_controller_pair=None,physical_predecessor={k:None for k in ('boot_id','filesystem_uuid','container_id','owner_nonce','lease_path','common_exclusion','shared_heavy')},runtime_execution_release=None,external_latest_native_physical_review=None,external_latest_native_physical_role='PENDING_GENUINE_CURRENT_PHYSICAL_ACCEPTANCE')
 write(out/'CURRENT-NATIVE-AND-RELEASED-BUILD-ROLES.json',roles)
 refs=[dict(path=x['path'],sha256=x['sha256'],bytes=x.get('size',x.get('bytes'))) for x in pre['runtime_source_pins']]
 owner=closure['owner'];runner=next(x for x in refs if x['path'].endswith('/native_diagnostic_runner.py'));observer=next(x for x in refs if x['path'].endswith('/native_diagnostic.py') and '/runtime-source-1/' in x['path'])
 c.update(actual_preparation_acceptance=ref(G),actual_full_preflight=ref(out/'ACTUAL-PREFLIGHT-CONSUMER-PROJECTION.json'),actual_original_preflight=ref(R/'ACTUAL-NATIVE-PREFLIGHT.json'),actual_binding_result=ref(R/'ACTUAL-BINDING.json'),actual_normalization_result=ref(R/'actual-normalize-result-1.json'),normalized_manifest=binding['manifest'],binding=binding,payload_contract=manifest['payload'],runtime_owner=owner,runtime_runner=runner,runtime_observer=observer,runtime_source_refs=refs,runtime_source_hashes=closure['source_hashes'],root_owner_argv=rootargv,accepted_owner_argv=pre['owner_argv'],actual_consumed_paths=pre['consumed_paths'],actual_readonly_roots=pre['readonly_roots'],parent_full_nine_field_identity=nine,latest_physical=None,native_predecessor_binding=ref(out/'CURRENT-NATIVE-AND-RELEASED-BUILD-ROLES.json'),physical_consumer_mapping=ref(out/'CURRENT-NATIVE-AND-RELEASED-BUILD-ROLES.json'),runtime_release=False,native_outcome=None)
 stage_review=H/'current-focused-progress-recording-20261021-1/current-normalization-review-recording-1/M07-SIGILL-SUCCESSOR-ACTUAL-IMAGE-ONLY-STAGE-ACCEPTANCE.json'
 stage=accepted_current_stage(stage_review,manifest)
 c['actual_stage_acceptance']=ref(stage_review);c['stage_manifest']=stage['manifest'];c['image_sha256']=manifest['artifacts']['mckernel_image']['sha256']
 # Original accepted image/stage/collector ancestry remains separate; new staged manifest is exact pairedalias.

 c['strict_oracle']=dict(kind='M07_REMAINING_NATIVE_CONDITIONAL_TYPED',case_id=manifest['case_id'],case_evaluator=next(x for x in refs if x['path'].endswith('/case_evaluator.py')),parser=next(x for x in refs if x['path'].endswith('/remaining_stdout.py')),descriptor=next(x for x in refs if x['path'].endswith('/remaining_descriptor.json')),fixed_native_stdout=None,STOP_credit=0,all_inapplicable_credit=0,exit_rule='0 unless stopped mask nonzero then2; STOP unmet prerequisite',stderr_hex='')
 c.update(current_heavy_released_record=roles['current_heavy_released_record'],external_latest_native_physical_review=roles['external_latest_native_physical_review'],legacy_reference_scope='NATIVE_TERMINAL_ANCESTRY_ONLY_C9_RELEASED_BUILD_ANCESTRY')
 write(out/'STATIC-NONTEMPORAL-INPUTS.json',c)
 binder=(B/'bind_numa_native_packet.py').read_text()
 start=binder.index("need(c['actual_preparation_acceptance']['sha256']==")
 end=binder.index("nonce=binding['nonce']",start)
 binder=binder[:start]+'''accepted_current_normalization(A,Path(c['actual_original_preflight']['path']).parent)
pre=load(c['actual_full_preflight']['path']);binding=load(c['actual_binding_result']['path'])
need(ref(c['actual_full_preflight']['path'])==c['actual_full_preflight'] and ref(c['actual_binding_result']['path'])==c['actual_binding_result'],'full actual preflight projection and binding')
original=ref(c['actual_original_preflight']['path']);need(pre['original_preflight']==original and accept['accepted_refs']['preflight']==original['sha256']+'/'+str(original['bytes']),'projection exact independently accepted preflight')
accepted_manifest=binding['manifest'];need(accepted_manifest==c['normalized_manifest']==pre['binding']['manifest'],'actual normalized manifest typed refs')
''' +binder[end:]
 binder=binder.replace("if not row['path'].endswith('.json')","if row['path'].endswith('.py')")
 binder=binder.replace('current-native-M07-enabled-state','current-native-M07-remaining-components').replace('M07 typed5-header+120B-suffix','M07 native conditional typed remaining-component').replace('M07 stdout/empty stderr/exit37','M07 conditional typed stdout/empty stderr/exit0-or-STOP2')
 snap=(B/'root_manual_snapshot_threads.py').read_text()
 snap=function_replace(snap,'static_joins', '''def static_joins(b):
    for row in b['source_pins']:
        need(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],'frozen source')
    meta=checked(b['conditional_metadata']);proposal=checked(meta['proposal']);pending=checked(b['machine_pending'])
    need(meta['parent_identity']==proposal['parent']['identity']==b['parent_identity']==pending['parent_identity'],'parent static join')
    need(pending['independent_static_execution_decision']==b['static_review'],'static review join');checked(b['static_review'])
    checked(b['mandatory_consumer_review']);checked(b['stage_review'])
    c=accepted_current_normalization(b['mandatory_consumer_review']['path'],Path(b['actual_original_preflight']['path']).parent)
    stage=accepted_current_stage(b['stage_review']['path'],checked_manifest(b['manifest']))
    pre=checked(b['actual_original_preflight']);projection=checked(b['actual_full_preflight']);binding=checked(b['actual_binding_result'])
    for key,name in [('actual_original_preflight','ACTUAL-NATIVE-PREFLIGHT.json'),('actual_binding_result','ACTUAL-BINDING.json')]:
        need(c['accepted_refs']['preflight' if key=='actual_original_preflight' else 'binding']==b[key]['sha256']+'/'+str(b[key]['bytes']),'actual accepted descriptor')
    need(projection['original_preflight']==b['actual_original_preflight'] and all(projection[k]==v for k,v in pre.items()),'finite actual preflight projection')
    need(binding['manifest']==b['manifest']==pre['binding']['manifest'] and binding['nonce']==proposal['nonce'] and binding['attempt_parent']==proposal['parent']['path'],'manifest nonce parent joins')
    need(pre['parent_nine_field_identity']==b['parent_review_identity'] and projection['parent_identity']==b['parent_identity'],'full nine-field parent')
    need(pre['consumed_paths']==b['entire_consumed_paths'] and pre['readonly_roots']==projection['readonly_roots'],'consumed roots')
    need(projection['root_owner_argv']==b['root_owner_argv']==proposal['argv'] and pre['owner_argv']==b['accepted_owner_argv'] and pre['inside_owner_argv']==b['inside_argv'] and pre['qemu_argv']==b['qemu_argv'],'all actual owner argv')
    need(pre['guest_runs']==pre['root_operations']==0 and pre['snapshot'] is None and pre['runtime_release'] is None,'bounded no-effect source preparation')
    result=checked(b['actual_normalization_result'])['result'];need(result['returncode']==0 and result['direct_child_joined'] is True and result['group_absent'] is True and result['closed_streams'] is True and result['error'] is None and result['retirement_error'] is None,'actual closed normalization')
    for role,row in result['captures'].items():
        raw=Path(row['path']).read_bytes();need(len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'actual captured bytes')
        if role=='stderr':need(raw==b'','actual empty stderr')
    spec=importlib.util.spec_from_file_location('exact_remaining_owner',b['runtime_owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    _,manifest=owner.bound_manifest(b['manifest']['path'],b['manifest']['sha256'])
    need(manifest['payload']==b['payload_contract'] and manifest['artifacts']['mckernel_image']['sha256']==b['repaired_image_sha256'],'unchanged actual payload and kernel')
    need(owner.SOURCE_HASHES==b['runtime_source_hashes'] and b['strict_oracle']['kind']=='M07_REMAINING_NATIVE_CONDITIONAL_TYPED','actual typed source binding')
    need(proposal['profile']['mckernel_cpus']==2 and proposal['profile']['memory']==proposal['profile']['memory_swap']==12884901888,'reviewed exact profile')
    return proposal,owner''')
 snapshot_helpers = '\n'+CURRENT_AUTHORITY_HELPER+'\ndef checked_manifest(row):\n    raw=Path(row["path"]).read_bytes();need(hashlib.sha256(raw).hexdigest()==row["sha256"] and len(raw)==row.get("size",row.get("bytes")),"exact native manifest descriptor");return json.loads(raw)\n'
 entry="if __name__=='__main__':raise SystemExit(main())"
 need(snap.count(entry)==1,'unique actual snapshot CLI entrypoint')
 snap=snap.replace(entry,snapshot_helpers+'\n'+entry)
 write(out/'root_manual_snapshot_threads.py',snap)
 # Carry actual new preparation inputs into generated snapshot data (DATA only).
 binder=once(binder,"b['source_pins']=c['runtime_source_refs']", "b.update({k:c[k] for k in ('actual_original_preflight','actual_full_preflight','actual_binding_result','actual_normalization_result')})\nb['source_pins']=c['runtime_source_refs']")
 # Above export is written once after all finite changes.
 binder=once(binder,"latest_predecessor_note='Genuine latest exclusive physical release; historical tested HOST66 tuple remains separate'", "latest_predecessor_note='Native87f/C9 retained ancestry only; separate latest external M05 physical requires genuine runtime preentry review plus fresh live snapshot'")
 for anchor,var in [("pref=add(Q/'proposal.json',prop)",'prop'),("baseref=add(Q/'machine-base.json',base)",'base'),("fref=add(Q/'non-temporal-freeze.json',freeze)",'freeze'),("bref=add(D/'fresh-snapshot-bindings.json',b)",'b'),("iref=add(Q/'FINAL-NONTEMPORAL-DATA-INDEX.json',index)",'index'),("projectionref=add(Q/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json',projection)",'projection'),("cfgref=add(Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json',cfg)",'cfg'),("packetref=add(Q/'NATIVE-COHERENT-REVIEW-PACKET.json',packet)",'packet')]:
  binder=once(binder,anchor,var+".update(current_heavy_released_record=roles['current_heavy_released_record'],external_latest_native_physical_review=roles['external_latest_native_physical_review'],legacy_reference_scope='NATIVE_TERMINAL_ANCESTRY_ONLY_C9_RELEASED_BUILD_ANCESTRY')\n"+anchor)
 binder=binder[:binder.index("c=load(D/'STATIC-NONTEMPORAL-INPUTS.json')")]+CURRENT_AUTHORITY_HELPER+'\n'+binder[binder.index("c=load(D/'STATIC-NONTEMPORAL-INPUTS.json')"):]
 binder=patch_pending_physical(binder)
 write(out/'bind_numa_native_packet.py',binder)
 checker=(B/'check_current_whole_caller.py').read_text().replace("contains='complete current failed-owner seven-field predecessor'","contains='latest native container and owner nonce'")
 checker=once(checker,"assert manifest==pre['validated_manifest_view'] and manifest['payload']==cfg['payload_contract']", "assert nd._same_plan(nd._freeze(nd._thaw(manifest)),nd._freeze(pre['validated_manifest_view'])) and manifest['payload']==cfg['payload_contract']\n    assert pre['raw_manifest_descriptor']==cfg['normalized_manifest']\n    assert nd._same_plan(nd._freeze(pre['raw_manifest_view']),nd._freeze(json.loads(Path(cfg['normalized_manifest']['path']).read_bytes())))\n    assert nd._same_plan(nd._freeze(nd._thaw(nd.load_manifest(cfg['normalized_manifest']['path']))),nd._freeze(pre['validated_manifest_view']))")
 checker=once(checker,"    cases=[dict(case=", "    # Inspect complete pending binder outputs and their actual selected control files.\n    pending_cfg=json.loads((Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json.PENDING-STATIC-CORRECTED').read_bytes())\n    runtime_map=json.loads(Path(pending_cfg['runtime_source_fd_identity_map']['path']).read_bytes())\n    selected={row['path'] for row in pending_cfg['runtime_source_refs'] if row['path'].endswith('.py')}\n    assert len(selected)==12 and set(runtime_map['identities'])==selected\n    assert not selected.intersection({str(D/'bind_numa_native_packet.py'),str(D/'check_current_whole_caller.py'),str(Q/'root-run-exact-readonly-stage.py'),str(Q/'review_final_threads_release.py'),str(Q/'root-execute-seven-1.py')})\n    assert pending['root_caller']==ref(Q/'root-run-exact-readonly-stage.py') and pending['final_guard_source']==ref(Q/'review_final_threads_release.py')\n    executor=Q/'root-execute-seven-1.py.PENDING-STATIC-CORRECTED'\n    executor_observed=ref(executor);executor_final=dict(executor_observed,path=str(Q/'root-execute-seven-1.py'))\n    assert executor_final==pending['root_executor'] and not (Q/'root-execute-seven-1.py').exists()\n    assert seven['required_caller']==ref(Q/'root-run-exact-readonly-stage.py')\n    for row in seven['steps']:\n        assert row['caller_argv_template'][3]==str(Q/'root-run-exact-readonly-stage.py')\n    assert any(isinstance(n,__import__('ast').Assign) and any(isinstance(t,__import__('ast').Name) and t.id=='B' for t in n.targets) and __import__('ast').literal_eval(n.value.args[0])==str(Q) for n in __import__('ast').parse(executor.read_text()).body)\n    assert pending['seven_rows']['sha256'] in executor.read_text()\n    code=[row for row in cfg['runtime_source_refs'] if row['path'].endswith('.py')]\n    roles=json.loads(Path(cfg['native_predecessor_binding']['path']).read_bytes())\n    code += [ref(D/'root_manual_snapshot_threads.py'),roles['released_record_projection_source'],ref(D/'bind_numa_native_packet.py'),ref(D/'check_current_whole_caller.py'),ref(Q/'root-run-exact-readonly-stage.py'),ref(Q/'review_final_threads_release.py'),executor_observed]\n    assert len(code)==len({row['path'] for row in code})==17\n    descriptor=next(row for row in cfg['runtime_source_refs'] if row['path'].endswith('/remaining_descriptor.json'))\n    # The qualified caller has an absolute, separately pinned capture primitive provider.\n    caller_source=(Q/'root-run-exact-readonly-stage.py').read_text();caller_tree=__import__('ast').parse(caller_source)\n    helper_node=next(n for n in caller_tree.body if isinstance(n,__import__('ast').Assign) and any(isinstance(t,__import__('ast').Name) and t.id=='hp' for t in n.targets))\n    helper=Path(__import__('ast').literal_eval(helper_node.value.args[0]));helper_ref=ref(helper)\n    assert helper_ref['sha256']=='5c884624b748b862aa1b48a369d3ee758f311ab6c70e82f1346c93d6b478b10d'\n    fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns');identities={}\n    for row in code+[descriptor,helper_ref]:\n        path=Path(row['path']);fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)\n        try:\n            before=os.fstat(fd);chunks=[]\n            while True:\n                chunk=os.read(fd,1<<20)\n                if not chunk:break\n                chunks.append(chunk)\n            after=os.fstat(fd);named=path.lstat();raw=b''.join(chunks)\n            assert __import__('stat').S_ISREG(before.st_mode) and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields)\n            assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row.get('bytes',row.get('size'))\n            identities[str(path)]={k:getattr(before,k) for k in fields}\n        finally:os.close(fd)\n    assert {path:identities[path] for path in selected}==runtime_map['identities']\n    closure=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_COMPLETE_CURRENT_PENDING17_CODE_DESCRIPTOR_HELPER_AND_RUNTIME12_CONFIG_FD_JOINS_ONLY',code=code,descriptor=descriptor,external_qualified_caller_helper=helper_ref,full_nine_field_identities=identities,retained_FD_lease=False,executor_observed=executor_observed,executor_future_final_descriptor=executor_final,actual_pending_packet=ref(Q/'NATIVE-COHERENT-REVIEW-PACKET.json.PENDING-STATIC-CORRECTED'),runtime12_map=ref(Path(pending_cfg['runtime_source_fd_identity_map']['path'])),future_final_static_review=None,snapshot=None,runtime_release=None)\n    (D/'ACTUAL-COMPLETE-CONTROL-AND-FD-CLOSURE.json').open('x').write(json.dumps(closure,sort_keys=True,indent=2)+'\\n')\n"+"    cases=[dict(case=")
 checker=once(checker,"    cases=[dict(case=", "    assert pending_cfg['external_latest_native_physical_review']==cfg['external_latest_native_physical_review']\n    assert pending['external_latest_native_physical_review']==pending_cfg['external_latest_native_physical_review']\n    assert pending_cfg['legacy_reference_scope']=='NATIVE_TERMINAL_ANCESTRY_ONLY_C9_RELEASED_BUILD_ANCESTRY'\n"+"    cases=[dict(case=")
 checker=checker.replace("    physical=json.loads(Path(cfg['latest_physical']['path']).read_bytes())", "    physical_pending=cfg['latest_physical'] is None\n    physical=None if physical_pending else json.loads(Path(cfg['latest_physical']['path']).read_bytes())")
 checker=checker.replace("    snapshot.terminal_joins(physical,b)\n    assert physical==snapshot.checked(cfg['latest_physical'])", "    if physical_pending:\n        assert b['physical_review'] is None and all(v is None for v in b['physical_predecessor'].values())\n    else:\n        snapshot.terminal_joins(physical,b)\n        assert physical==snapshot.checked(cfg['latest_physical'])")
 checker=checker.replace("    # Invoke the real", "    # Invoke the real")
 checker=checker.replace("    before=set(D.rglob('*.PENDING-STATIC-CORRECTED'));assert not before", "    suffix='.PENDING-PHYSICAL' if physical_pending else '.PENDING-STATIC-CORRECTED'\n    before=set(D.rglob('*'+suffix));assert not before")
 checker=checker.replace("produced=set(D.rglob('*.PENDING-STATIC-CORRECTED'))", "produced=set(D.rglob('*'+suffix))")
 checker=checker.replace(".json.PENDING-STATIC-CORRECTED'", ".json'+suffix").replace(".py.PENDING-STATIC-CORRECTED'", ".py'+suffix")
 checker=checker.replace("Q/'FINAL-SEVEN-ROOT-CALL-DATA.json'+suffix", "Q/('FINAL-SEVEN-ROOT-CALL-DATA.json'+suffix)").replace("Q/'NATIVE-COHERENT-REVIEW-PACKET.json'+suffix", "Q/('NATIVE-COHERENT-REVIEW-PACKET.json'+suffix)").replace("Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json'+suffix", "Q/('FINAL-IHK-LOGGING-CHECK-CONFIG.json'+suffix)").replace("Q/'root-execute-seven-1.py'+suffix", "Q/('root-execute-seven-1.py'+suffix)")
 checker=checker.replace("    for key in ('container_id','owner_nonce'):", "    for key in (() if physical_pending else ('container_id','owner_nonce')):")
 checker=checker.replace("PASS_ACTUAL_CURRENT_KIND_PENDING19_AND_CALLER_BODY_ONLY", "PASS_CURRENT_AUTHORITY_PENDING19_CALLER_BODY_NO_PHYSICAL_OR_RUNTIME_CREDIT")
 write(out/'check_current_whole_caller.py',checker)
 # All three existing control bodies are reused at genuine paths until binder DATA output construction.
 freeze=load(H/'numa-current-image-native-app-preparation-20261021-1/runtime-preparation-1/current-physical-bound-1/SOURCE-FREEZE.json')
 controls=[]
 for name in ('root-run-exact-readonly-stage.py','review_final_threads_release.py'):
    authority=next(row for row in freeze['refs'] if Path(row['path']).name==name)
    old=B/'native-packet-1'/name;need(ref(old)['sha256']==authority['sha256'] and ref(old)['bytes']==authority['bytes'],'exact accepted SOURCE-FREEZE control '+name)
    target=out/'native-packet-1'/name;write(target,old.read_text());need(ref(target)['sha256']==authority['sha256'],'byteidentical selected Q control');controls.append(target)
 write(out/'SELECTED-Q-CONTROL-SEED-AUTHORITY.json',dict(source_freeze=ref(H/'numa-current-image-native-app-preparation-20261021-1/runtime-preparation-1/current-physical-bound-1/SOURCE-FREEZE.json'),seeded=[ref(p) for p in controls],executor=None,executor_rule='Only binder-generated actual current seven-row postimage; historical executor is never copied.'))
 code=[x for x in refs if x['path'].endswith('.py')]+[ref(out/'root_manual_snapshot_threads.py'),roles['released_record_projection_source'],ref(out/'bind_numa_native_packet.py'),ref(out/'check_current_whole_caller.py')]+[ref(x) for x in controls]
 need(len(code)==16 and len({x['path'] for x in code})==16,'complete16 prebind Python source set; actual17th executor generated by binder')
 objects=code+[next(x for x in refs if x['path'].endswith('/remaining_descriptor.json'))];identities={}
 for row in objects:
    path=Path(row['path']);fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
      a=os.fstat(fd);raw=b''
      while True:
        chunk=os.read(fd,1<<20)
        if not chunk:break
        raw+=chunk
      z=os.fstat(fd);named=path.lstat();need(stat.S_ISREG(a.st_mode) and all(getattr(a,k)==getattr(z,k)==getattr(named,k) for k in FIELDS),'stable9field '+str(path));need(hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'],'exact selected source');identities[str(path)]={k:getattr(a,k) for k in FIELDS}
    finally:os.close(fd)
 write(out/'PREBIND-16-CODE-PLUS-DESCRIPTOR-FD-IDENTITIES.json',dict(schema='mckernel.remaining.outer.complete-source-fd-identities.v1',identities=identities,python_count=16,all_objects_count=17,executor=None,retained_FD_lease=False))
 # Existing final guard FD set remains Python-only; descriptor already pinned in runtime refs.
 selected={k:v for k,v in identities.items() if k.endswith('.py') and k not in {str(out/'bind_numa_native_packet.py'),str(out/'check_current_whole_caller.py'),*[str(x) for x in controls]}}
 write(out/'RUNTIME-SOURCE-FD-IDENTITIES.json',dict(schema='mckernel.current-native.selected-runtime-source-full-fd-identities.v1',identities=selected))
 pins=[ref(out/n) for n in ('STATIC-NONTEMPORAL-INPUTS.json','CURRENT-NATIVE-AND-RELEASED-BUILD-ROLES.json','ACTUAL-PREFLIGHT-CONSUMER-PROJECTION.json','bind_numa_native_packet.py','root_manual_snapshot_threads.py','check_current_whole_caller.py','RUNTIME-SOURCE-FD-IDENTITIES.json')]
 write(out/'CHECK-INPUT-PINS.json',pins+[ref(G),ref(stage_review)])
 for path in out.glob('*.py'):ast.parse(path.read_text())
 write(D/'CONSTRUCTION-RESULT-DIAGNOSTIC-SUCCESSOR-EXPERT-CORRECTION-SOURCE-ONLY.json',dict(scope=g['scope'],status='SOURCE_DATA_PREPARED_NOT_TESTED',files=[ref(x) for x in sorted(out.rglob('*')) if x.is_file()],prebind_python_count=16,prebind_all_objects_count=17,actual_executor=None,ordinary_check=None,final_static_review=None,fetched_code_checkpoint=None,current_native_physical=None,new_C9_build_physical=None,latest_exclusive_physical=None,snapshot=None,runtime_release=None,guest_runs=0))
 print(json.dumps(ref(D/'CONSTRUCTION-RESULT-DIAGNOSTIC-SUCCESSOR-EXPERT-CORRECTION-SOURCE-ONLY.json'),sort_keys=True))
if __name__=='__main__':main()
