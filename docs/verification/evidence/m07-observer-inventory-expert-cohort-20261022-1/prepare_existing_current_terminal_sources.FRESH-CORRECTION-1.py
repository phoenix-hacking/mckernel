#!/usr/bin/env python3
"""Finite successor source/data binding; never imports the generated machinery.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run a selected phase only after actual inputs and dispatcher ordinary grant.
No build, staging, normalization, observer, cleanup or runtime operation is run.
"""
from pathlib import Path
import argparse, ast, copy, hashlib, json, os, stat

D = Path('/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/census-authority-next-constructor-correction-preparation-1')
S = D.parent
H = S.parent
N = H/'numa-current-image-native-app-preparation-20261021-1'
C = H/'numa-current-image-terminal-preparation-20261021-1/schema-correction-1'
F = N/'runtime-preparation-1/current-physical-bound-1'
FIELDS = ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def need(ok, why):
    if not ok: raise ValueError(why)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def load(p): return json.loads(Path(p).read_bytes())
def ref(p):
    p=Path(p); raw=p.read_bytes()
    return dict(path=str(p),sha256=digest(raw),bytes=len(raw))
def checked(row):
    need(type(row) is dict and {'path','sha256'} <= row.keys() and row['path'] is not None and row['sha256'] is not None,'actual reference remains pending')
    p=Path(row['path']); raw=p.read_bytes()
    need(p.is_absolute() and p.resolve()==p and digest(raw)==row['sha256'] and len(raw)==row.get('bytes',row.get('size')),'exact selected input '+str(p))
    if 'mode' in row: need(p.stat().st_mode==row['mode'],'selected mode '+str(p))
    return raw
def pinned(p, sha):
    raw=Path(p).read_bytes(); need(digest(raw)==sha,'accepted source drift '+str(p)); return raw.decode()
def once(text, old, new):
    need(text.count(old)==1,'unique finite source boundary '+old[:90]); return text.replace(old,new)
def global_value(text, name, expression):
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name]
    need(len(nodes)==1,'one global '+name); n=nodes[0]; lines=text.splitlines(keepends=True)
    lines[n.lineno-1:n.end_lineno]=[name+' = '+expression+'\n']; return ''.join(lines)
def outdir(name):
    p=Path(__file__).resolve().parent/name; need(not os.path.lexists(p),'fresh private phase destination'); p.mkdir(mode=0o700); return p
def write(p, raw):
    if isinstance(raw,str): raw=raw.encode()
    with p.open('xb') as stream: stream.write(raw)
    p.chmod(0o600)
def js(p,v): write(p,json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def source(p,text): ast.parse(text); write(p,text)
def finish(p):
    rows=[ref(f) for f in sorted(p.rglob('*')) if f.is_file()]
    js(p/'GENERATED-SOURCE-DATA-REFS.json',dict(status='SOURCE_DATA_ONLY_NO_EXECUTION_OR_RELEASE',files=rows))
    print(json.dumps(ref(p/'GENERATED-SOURCE-DATA-REFS.json'),sort_keys=True))
def sized(row):
    p=Path(row['path']); checked(row)
    return dict(path=str(p),sha256=row['sha256'],size=p.stat().st_size,mode=p.stat().st_mode)

def stage(b):
    a=b['artifact']; review=json.loads(checked(a['acceptance']))
    need(review['schema']=='mckernel.current-numa-scheduler.production-image-artifact-review.v1' and review['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and review['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY' and review['implementation_ownership'] is False and review['reviewer'],'actual independent successor artifact decision')
    need(review['source_derivative_sha256']==a['source_derivative_sha256'] and review['materialization_sha256']==a['materialization_sha256'],'actual successor source fingerprints')
    base=load(S/'SUCCESSOR-BINDING-DATA-PROPOSAL.json'); old=base['baseline_actual_NUMA_stage']; loc=base['locators']
    image=sized(a['image']); launcher=sized(a['mcexec'])
    for row,role in ((image,'artifacts/mckernel.img'),(launcher,'artifacts/mcexec')):
        fact=review['artifact_descriptors_verified'][role]
        need(all(row[k]==fact[k] for k in ('path','sha256')) and row['size']==fact['bytes'],'actual artifact descriptor '+role)
    need(image['sha256']!=old['image']['sha256'],'corrected new image required; no predecessor alias')
    need(launcher['sha256']==old['mcexec']['sha256'] and launcher['size']==old['mcexec']['size'],'unchanged actual launcher')
    cfg=load(N/'newbound-source-1/binding.json'); c=cfg['cases']['numa']
    cfg.update(image_artifact_review=sized(a['acceptance']),image_source=image,mcexec_source=launcher,accepted_threads_stage=sized(old['acceptance']),assets_root=loc['assets_root'],manifests_root=loc['manifest_root'])
    c.update(old_manifest=old['manifest'],old_base=old['base'],old_overlay=old['overlay'],old_overlay_manifest=old['overlay_manifest'],payload=base['unchanged_payload'],mcexec=launcher,collector=base['unchanged_collector'],output_dir=loc['stage_case_directory'],manifest_dir=loc['stage_manifest_directory'],runtime_parent=loc['attempt_parent'],nonce=loc['nonce'],endpoint=loc['qmp_socket'],endpoint_encoded_bytes=loc['qmp_bytes'])
    need(cfg['payload_contract']==base['unchanged_payload_contract'],'strict unchanged oracle')
    text=pinned(N/'newbound-source-1/stage_numa.py',base['source_ancestry']['accepted_stager']['sha256'])
    for oldpin,newpin in [('7331e75da3966e7e1059257b6456f651f78f056a66363cd9be849f7f9adf5629',a['acceptance']['sha256']),('ea825bb5fd67fb5165d578dfb17831c00c399663f34049d6e132b4c701f994f7',a['source_derivative_sha256']),('1b584ee5b65f39467c8215bb2fc272e1fb0e9c95ee23e01e16e523a8a551a3fa',a['materialization_sha256']),('c6ad2a7f02c686fafcf7fbe645706a0202a1e7f0183e7e5e074865e841771e67',old['acceptance']['sha256'])]: text=once(text,oldpin,newpin)
    text=once(text,"c['old_manifest']==stage['accepted_manifest'] and c['old_base']==stage['accepted_outputs']['base'] and c['old_overlay']==stage['accepted_outputs']['overlay'] and c['old_overlay_manifest']==stage['overlay_manifest']","c['old_manifest']==stage['manifest'] and c['old_base']==stage['base'] and c['old_overlay']==stage['overlay'] and c['old_overlay_manifest']==stage['overlay_manifest']")
    text=text.replace("stage['accepted_outputs']['mcexec']","stage['mcexec']")
    text=once(text,"{'images/mckernel.img','apps/app'}","{'images/mckernel.img'}")
    text=once(text,"need(final['bin/mcexec']==old['bin/mcexec'],'launcher final map explicitly unchanged')","need(all(final[n]==old[n] for n in ('bin/mcexec','apps/app','init')) and sum(final[n]==old[n] for n in final)==59,'exact59 unchanged; launcher/payload/init explicitly equal')")
    text=text.replace('against accepted current threads overlay','against accepted NUMA overlay').replace('PASS_NUMA_IMAGE_AND_PAYLOAD_STAGE_PENDING_ACTUAL_CONSUMER_BINDING_AND_REVIEW','PASS_NUMA_IMAGE_ONLY_STAGE_PENDING_ACTUAL_CONSUMER_BINDING_AND_REVIEW').replace('PASS_SINGLE_NUMA_IMAGE_AND_PAYLOAD_STAGE','PASS_SINGLE_NUMA_IMAGE_ONLY_STAGE')
    p=outdir('bound-stage-source-1')
    contract=load(N/'newbound-source-1/ABI-AND-CONSUMER-CONTRACT.json')
    contract.update(image_artifact_acceptance=sized(a['acceptance']),source_derivative_sha256=a['source_derivative_sha256'],materialization_sha256=a['materialization_sha256'])
    contract['invariants'][1]='Actual successor artifact decision binds corrected allowed-mask Rust/C NUMA and scheduler linkage with all original ABI/layout/native/legacy assertions.'
    js(p/'ABI-AND-CONSUMER-CONTRACT.json',contract); cfg['consumer_contract']=sized(ref(p/'ABI-AND-CONSUMER-CONTRACT.json'))
    source(p/'stage_numa.py',text); js(p/'binding.json',cfg); finish(p)

def normalization(b):
    n=b['normalization']; acceptance=json.loads(checked(n['stage_acceptance'])); cfg=copy.deepcopy(n['settings'])
    need(acceptance['archive_members']==60 and acceptance['unchanged_members']==59 and set(acceptance['observed_delta'])=={'images/mckernel.img'},'actual exact image-only stage acceptance')
    need(cfg['stage_acceptance']==n['stage_acceptance'] and cfg['source_manifest']==acceptance['manifest'],'normalization actual stage joins')
    text=pinned(N/'normalization-preparation-1/prepare_native.py','8f145a79f44ccc8ac9d46460bc3c7d6424b7c4142c3d5c2e4f0c4746fb79b54d')
    text=once(text,'eccae19ce2e4b1439efd4142be6fdde6b739c4f0f65052882e5ecce568211d73',n['stage_acceptance']['sha256'])
    text=once(text,"acceptance['unchanged_members']==58 and set(acceptance['observed_delta'])=={'images/mckernel.img','apps/app'}","acceptance['unchanged_members']==59 and set(acceptance['observed_delta'])=={'images/mckernel.img'}")
    p=outdir('bound-normalization-source-1'); source(p/'prepare_native.py',text); js(p/'SETTINGS.json',cfg); js(p/'INPUT-PINS.json',n['input_pins']); finish(p)

def decode_finite_case(case):
    """Reject scalar inventory schema; bind exact sorted role path union pre-mutation."""
    need(type(case) is dict, 'finite-case: dictionary required')
    roles=case.get('finite_roles'); paths=case.get('finite_unique_paths')
    need(type(roles) is dict and roles and all(type(k) is str and k for k in roles),
         'finite-case: named role dictionary required')
    need(type(paths) is list, 'finite-case: path list required; scalar schema refused')
    need(type(case.get('finite_role_count')) is int and case['finite_role_count']==len(roles),
         'finite-case: role count differs')
    need(type(case.get('finite_unique_path_count')) is int and case['finite_unique_path_count']==len(paths),
         'finite-case: path count differs')
    def path_name(value):
        need(type(value) is str and value.startswith('/') and not value.startswith('//') and
             '\x00' not in value and all(part not in ('','.','..') for part in value.split('/')[1:]),
             'finite-case: canonical absolute path required')
        p=Path(value)
        need(str(p)==value and not any(q.is_symlink() for q in (p,*p.parents)),
             'finite-case: nonsymlink canonical path required')
        return value
    bypath={}
    for role,row in roles.items():
        need(type(row) is dict and set(row)=={'path','sha256','bytes'},
             'finite-case: exact descriptor shape required:'+role)
        path=path_name(row['path']); digest=row['sha256']; size=row['bytes']
        need(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and
             type(size) is int and size>=0, 'finite-case: descriptor hash/byte shape differs:'+role)
        need(path not in bypath or bypath[path]==row, 'finite-case: conflicting aliases:'+role)
        bypath[path]=row
    need(all(type(p) is str for p in paths), 'finite-case: string paths required')
    for p in paths:path_name(p)
    need(paths==sorted(bypath), 'finite-case: exact sorted distinct role path union required')
    return tuple(paths)


def terminal(b):
    t=b['terminal']; case=json.loads(checked(t['case'])); retirement=json.loads(checked(t['retained_review'])); artifact=json.loads(checked(t['artifact_acceptance']))
    decode_finite_case(case)
    need(type(case.get('current_live_postjoin')) is dict and case['current_live_postjoin']==case['finite_roles']['guard_postjoin'], 'exact genuine predecessor guard postjoin reference required; future cleanup is separate')
    need(case['artifact_acceptance']==t['artifact_acceptance'] and case['physical']==t['retained_review'],'four-document exact current report refs')
    need(artifact['producer_receipt']==case['finite_roles']['driver_receipt'],'driver belongs to artifact report, never invented retirement field')
    need(case['source_identity']['source_derivative_sha256']==artifact['source_derivative_sha256'] and case['source_identity']['materialization_sha256']==artifact['materialization_sha256'],'terminal source fingerprints')
    pins=load(C/'SOURCE-PINS.json')['files']; texts={}
    for name,row in pins.items():
        if name.endswith('.py'): texts[name]=checked(row).decode()
    p=outdir('bound-terminal-expert-source-1'); write(p/'PASS-CASE-STATIC.json',checked(t['case']))
    # Bind the finite top-level DATA and two exact guard-directory literals only.
    # Transaction/census/recovery/ownership algorithms and profiles are preserved.
    bindings=t['source_bindings']; need(type(bindings) is dict and bindings['current_typed_request']==case['source_identity'] and bindings['target']==case['target'],'complete current terminal source/target DATA')
    request=json.loads(checked(case['request'])); engine=texts.pop('cleanup_pass_image.py')
    # Historical template remains immutable; select the accepted current PROC literal.
    proc_source=pinned(S/'census-lifetime-race-correction-1/cleanup_pass_image.PROC-CORRECTED.py','b8c7d0f6ff3dc7303ca2063575c1affe0b63a4b283b0cc3223c4f3a11f93d80a')
    proc_node=next(n for n in ast.parse(proc_source).body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PROC_CODE')
    current_proc=ast.literal_eval(proc_node.value)
    need(digest(current_proc.encode())=='24e27a493a84a1ab6c3d22a5248ae456288fa590fc93e31b3fb5a0a29d8659af' and digest(current_proc.encode())!='986e64c50fd8d78bbe3c23e86a690e67b51255ab03c9f03f29db30ee50891532','accepted current PROC authority; obsolete literal forbidden')
    engine=global_value(engine,'PROC_CODE',repr(current_proc))
    values={'SOURCE_REFS':repr(bindings['source_refs']),'CURRENT_TYPED_REQUEST':repr(case['source_identity']),'PUBLISHED_SCRIPT':repr(str(p/'cleanup_pass_image.py').replace(str(H)+'/', 'docs/verification/evidence/')),'NAMESPACE':"Path("+repr(case['namespace'])+")",'NAMESPACE_ANCESTRY':repr(case['namespace_ancestry']),'NAMESPACE_BINDING':repr(case['namespace_binding']),'PREFIX':repr('m07-sigill-current-image-terminal-20261022-1'),'ATTEMPT':"Path("+repr(request['common_exclusion_path'])+")",'REQUEST':"Path("+repr(case['request']['path'])+")",'LEASE':"Path("+repr(request['lease_path'])+")",'OUTPUT':"Path("+repr(str(Path(case['namespace'])/'owner-work'))+")",'EVIDENCE':"Path("+repr(str(Path(case['namespace'])/'owner-evidence'))+")",'KNOWN_TARGET':repr({k:v for k,v in case['target'].items() if k!='image_id'}),'REQUEST_SHA':repr(case['request']['sha256']),'IMAGE_CANDIDATE':repr(case['source_identity']['candidate_sha']),'PASS_LOG_CHANNELS':repr(case['log_channels'])}
    for name,value in values.items(): engine=global_value(engine,name,value)
    oldguard='native-rust-phase5-current-optin-image-guard-9d86fb76cc70406889799278b90e8752'; newguard=Path(case['guard_capture']).name
    need(engine.count(oldguard)==2,'exact two guard directory literal slots'); engine=engine.replace(oldguard,newguard)
    source(p/'cleanup_pass_image.py',engine); engine_ref=ref(p/'cleanup_pass_image.py')
    observer=texts.pop('observe_current_pass_image_retirement.py').replace(str(C),str(p))
    observer=once(observer,'def main(argv=None):','def decode_finite_case(case):\n    """Reject scalar inventory schema; bind exact sorted role path union pre-mutation."""\n    need(type(case) is dict, \'finite-case: dictionary required\')\n    roles=case.get(\'finite_roles\'); paths=case.get(\'finite_unique_paths\')\n    need(type(roles) is dict and roles and all(type(k) is str and k for k in roles),\n         \'finite-case: named role dictionary required\')\n    need(type(paths) is list, \'finite-case: path list required; scalar schema refused\')\n    need(type(case.get(\'finite_role_count\')) is int and case[\'finite_role_count\']==len(roles),\n         \'finite-case: role count differs\')\n    need(type(case.get(\'finite_unique_path_count\')) is int and case[\'finite_unique_path_count\']==len(paths),\n         \'finite-case: path count differs\')\n    def path_name(value):\n        need(type(value) is str and value.startswith(\'/\') and not value.startswith(\'//\') and\n             \'\\x00\' not in value and all(part not in (\'\',\'.\',\'..\') for part in value.split(\'/\')[1:]),\n             \'finite-case: canonical absolute path required\')\n        p=Path(value)\n        need(str(p)==value and not any(q.is_symlink() for q in (p,*p.parents)),\n             \'finite-case: nonsymlink canonical path required\')\n        return value\n    bypath={}\n    for role,row in roles.items():\n        need(type(row) is dict and set(row)=={\'path\',\'sha256\',\'bytes\'},\n             \'finite-case: exact descriptor shape required:\'+role)\n        path=path_name(row[\'path\']); digest=row[\'sha256\']; size=row[\'bytes\']\n        need(type(digest) is str and len(digest)==64 and all(c in \'0123456789abcdef\' for c in digest) and\n             type(size) is int and size>=0, \'finite-case: descriptor hash/byte shape differs:\'+role)\n        need(path not in bypath or bypath[path]==row, \'finite-case: conflicting aliases:\'+role)\n        bypath[path]=row\n    need(all(type(p) is str for p in paths), \'finite-case: string paths required\')\n    for p in paths:path_name(p)\n    need(paths==sorted(bypath), \'finite-case: exact sorted distinct role path union required\')\n    return tuple(paths)\n\n\n'+'def main(argv=None):')
    observer=once(observer,'case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))','case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))\n    finite_paths=decode_finite_case(case)')
    observer=observer.replace("case['finite_unique_paths']",'finite_paths')
    observer=once(observer,"    root_join=json.loads(stable_bytes(Path(case['current_live_postjoin']['path']),case['current_live_postjoin']['sha256']))","    postjoin_ref=case.get('current_live_postjoin')\n    need(isinstance(postjoin_ref,dict) and postjoin_ref==case['finite_roles']['guard_postjoin'],\n         'exact genuine predecessor guard postjoin reference required; future cleanup is separate')\n    root_join=json.loads(stable_bytes(Path(postjoin_ref['path']),postjoin_ref['sha256']))")
    records=case['full_original_record_authority']
    need(len(records)==2 and {row['role'] for row in records}=={'common','shared'},'two genuine original record authorities')
    boots=set()
    for row in records:
        descriptor=row['full_descriptor']; actual=json.loads(checked(dict(path=descriptor['path'],sha256=descriptor['sha256'],bytes=descriptor['size'])))
        need(actual==row['record'] and actual['pid']==case['target']['owner_pid'] and actual['starttime']==case['target']['owner_starttime'],'genuine current original record producer')
        boots.add(actual['boot_id'])
    need(len(boots)==1 and all(type(value) is str and value for value in boots),'original common/shared boot equality')
    boot=next(iter(boots))
    vals={'FAILURE_CASE':"Path("+repr(str(p/'PASS-CASE-STATIC.json'))+")",'FAILURE_CASE_SHA':repr(ref(p/'PASS-CASE-STATIC.json')['sha256']),'PREP':"Path("+repr(str(p))+")",'CASE':"Path("+repr(t['build_case_directory'])+")",'CAPTURE':"Path("+repr(t['guard_capture_directory'])+")",'RETIREMENT':"Path("+repr(t['retained_review']['path'])+")",'RETIREMENT_SHA':repr(t['retained_review']['sha256']),'NONCE':repr(t['observation_nonce']),'BOOT':repr(boot),'PIDS':repr(tuple(t['saved_guard_client_pids'])),'TERMINAL_INSPECTION_SHA':repr(case['finite_roles']['terminal_inspection']['sha256']),'CURRENT_EXPECTED_SOURCE':repr(case['source_identity'])}
    vals['SOURCE_SHA']=repr(engine_ref['sha256'])
    for name,value in vals.items(): observer=global_value(observer,name,value)
    source(p/'observe_current_pass_image_retirement.py',observer); observer_ref=ref(p/'observe_current_pass_image_retirement.py')
    summary=texts.pop('readback_observer.py').replace(str(C),str(p)).replace('numa-current-pass-image-observation-1',t['observation_nonce']); source(p/'readback_observer.py',summary)
    for name,text in texts.items():
        text=text.replace(str(C),str(p)).replace('numa-current-pass-image-observation-1',t['observation_nonce'])
        if name=='check_current_pass_bodies.py':
            cpins=ast.literal_eval(next(n.value for n in ast.parse(text).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PINS'))
            cpins.update(engine=ref(p/'cleanup_pass_image.py'),observer=observer_ref,case=ref(p/'PASS-CASE-STATIC.json'),physical=t['retained_review'],postjoin=t['root_join'],artifact=t['artifact_acceptance'])
            text=global_value(text,'PINS',repr(cpins))
        if name=='check_current_pass_bodies.py': text=once(text,oldguard,newguard)
        if name=='check_current_pass_bodies.py': text=once(text," obs=read('observer').decode();engine=read('engine').decode()\n"," obs=read('observer').decode();engine=read('engine').decode()\n proc=ast.literal_eval(next(n.value for n in ast.parse(engine).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets)))\n assert sha(proc.encode())=='24e27a493a84a1ab6c3d22a5248ae456288fa590fc93e31b3fb5a0a29d8659af' and sha(proc.encode())!='986e64c50fd8d78bbe3c23e86a690e67b51255ab03c9f03f29db30ee50891532','generated engine must retain accepted current PROC authority'\n")
        if name=='postjoin_readback.py':
            text=global_value(global_value(text,'OBSERVER_SHA',repr(observer_ref['sha256'])),'ENGINE_SHA',repr(engine_ref['sha256']))
            start=text.index("        selected={x['path']:x for x in obs['selected_files']};side=")
            end=text.index('        request=m.parse',start)
            text=text[:start]+'        actual,objects=finite_metadata_consumer(m,o,obs)\n'+text[end:]
            text=once(text,'def main():',"def finite_metadata_consumer(m,o,obs):\n    selected={x['path']:x for x in obs['selected_files']};side=selected[str(o.OUTPUT/'new-object-metadata.json')]\n    meta=json.loads(o.stable_bytes(Path(side['path']),side['sha256']))\n    authority=json.loads(o.stable_bytes(o.FAILURE_CASE,o.FAILURE_CASE_SHA,4<<20))\n    finite_paths=o.decode_finite_case(authority)\n    def objects():return [m.observe_identity(Path(p)) for p in finite_paths]\n    actual=objects();need(len(actual)==len(finite_paths) and actual==meta['objects'],'all finite current PASS descriptors differ')\n    return actual,objects\n\n"+'\ndef main():')
        if name=='check_actual_fresh_preflight.py': text=global_value(text,'SOURCE_SHA',repr(engine_ref['sha256']))
        if name in ('read_original_five_metadata.py','export_raw_five.py'): text=global_value(text,'SUMMARY_SHA',repr(ref(p/'readback_observer.py')['sha256']))
        source(p/name,text)
    # Existing finite operation constructors, same order and profiles, new namespace.
    def remap(value):
        if isinstance(value,str): return value.replace(str(C),str(p)).replace('numa-current-pass-image-observation-1',t['observation_nonce'])
        if isinstance(value,list): return [remap(v) for v in value]
        if isinstance(value,dict): return {k:remap(v) for k,v in value.items()}
        return value
    draft=remap(load(C/'OBSERVER-REQUEST-DRAFT.json'))
    draft.update(cleanup_source_sha256=ref(p/'cleanup_pass_image.py')['sha256'],observer_sha256=observer_ref['sha256'],failure_case_sha256=ref(p/'PASS-CASE-STATIC.json')['sha256'],retirement_sha256=t['retained_review']['sha256'])
    need(draft['status']=='NOT_RELEASED' and draft['source_review'] is None and draft['execution_review'] is None,'no future observer release')
    js(p/'OBSERVER-REQUEST-DRAFT.json',draft)
    ops=remap(load(C/'EXECUTOR-SIX-OPERATIONS.json')); ops.update(artifact_review=t['artifact_acceptance'],observer_request_draft=ref(p/'OBSERVER-REQUEST-DRAFT.json'),ordinary_result=None,source_freeze=None,capture_callers=dict(first_four=ref(p/'capture_first_four.py'),critical_two=ref(p/'capture_critical_two.py')))
    need(all(v is None for v in ops['late_fields'].values()),'no future operation facts')
    js(p/'EXECUTOR-SIX-OPERATIONS.json',ops)
    for operation in ops['ordered_operations']: js(p/('OPERATION-'+operation['role']+'.PENDING.json'),operation)
    js(p/'OPERATION-readonly-preflight.PENDING.json',ops['pre_cleanup_readonly_preflight'])
    ordinary=remap(load(C/'ORDINARY-CHECK-OPERATION.json')); ordinary.update(checker=ref(p/'check_current_pass_bodies.py'),root_grant=None); js(p/'ORDINARY-CHECK-OPERATION.json',ordinary)
    need(type(t['source_bindings']) is dict,'complete actual terminal source DATA pending')
    js(p/'CURRENT-PASS-SOURCE-BINDINGS.json',t['source_bindings'])
    js(p/'SOURCE-PINS.json',dict(status='FROZEN_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',files={name:ref(p/name) for name in pins}))
    finish(p)

def runtime(b):
    r=b['runtime']; mapping=json.loads(checked(r['physical_mapping'])); a=mapping['genuine_current_authorities']; physical=json.loads(checked(a['original_physical']))
    need(r['physical_report']==a['original_physical'] and mapping['controller_terminal_contract']['kind']=='tool-owned-unified-exec-terminal','actual matching physical kind')
    expected={}
    for pair in a['controller_terminal_receipts']:
        first=json.loads(checked(pair['started'])); last=json.loads(checked(pair['completed']))
        x=first['event']['params']['item']; y=last['event']['params']['item']
        need(first['event']['method']=='item/started' and last['event']['method']=='item/completed' and x['id']==y['id'] and y['status']=='completed' and y['exitCode']==0,'genuine actual raw protocol pair')
        expected[pair['role']]=(y['id'],y['processId'],y['durationMs'])
    need(set(expected)=={'cleanup','postjoin'} and len(physical['positive_closed_births'])==2,'TWO genuine innerbirths, no outerOS invention')
    p=outdir('bound-runtime-source-1'); (p/'native-packet-1').mkdir(mode=0o700)
    decoder=pinned(F/'current_numa_image_physical.py','4d8f94465e40c0366b1dceeda68ca52f404d979cfc37a4f179a9121717257327')
    decoder=once(decoder,"{'cleanup':('exec-90a521f3-58a5-483c-8374-efd8e0e04264','99784',5672),'postjoin':('exec-85f7c82a-235c-420a-ad80-b5f5d2bffc9e','24157',1644)}",repr(expected))
    decoder=once(decoder,'a8a21b2650a130980be4a78751c497670ccb9869dcd0c145ec051595358266ce',a['execution_review']['sha256'])
    decoder=once(decoder,'ec35a97db4bf461e86fbd944270afabf3df1691a49d2ff64d67ad4a3d8ac6ebf',a['source_cleanup_engine']['sha256'])
    counts=mapping['current_actual_counts']; objects=counts['postreader_actual_objects']; roles=counts['finite_roles']
    decoder=once(decoder,"mapping['current_actual_counts']['selected_files']==92","mapping['current_actual_counts']['selected_files']=="+repr(counts['selected_files']))
    decoder=once(decoder,"mapping['current_actual_counts']['postreader_actual_objects']==88","mapping['current_actual_counts']['postreader_actual_objects']=="+repr(objects))
    decoder=once(decoder,"len(set(r['path'] for r in metadata['objects']))==88","len(set(r['path'] for r in metadata['objects']))=="+repr(objects))
    decoder=once(decoder,"t['preservation']['finite_roles']==97 and t['preservation']['finite_objects']==88","t['preservation']['finite_roles']=="+repr(roles)+" and t['preservation']['finite_objects']=="+repr(objects))
    source(p/'current_numa_image_physical.py',decoder)
    freeze=load(F/'SOURCE-FREEZE.json'); code={Path(row['path']).relative_to(F).as_posix():row for row in freeze['refs'] if row['path'].endswith('.py')}
    for name,row in code.items():
        if name=='current_numa_image_physical.py': continue
        text=checked(row).decode()
        if name in ('bind_numa_native_packet.py','root_manual_snapshot_threads.py'): text=once(text,'809e2828fa78d9a1cced662e832bc4269316c267eff07641d2181db6b6653d3d',r['static_inputs']['actual_preparation_acceptance']['sha256'])
        source(p/name,text)
    cfg=copy.deepcopy(r['static_inputs']); need(cfg['latest_physical']==r['physical_report'] and cfg['physical_consumer_mapping']==r['physical_mapping'],'complete actual runtime DATA joins')
    checked(cfg['actual_preparation_acceptance']); checked(cfg['actual_stage_acceptance'])
    js(p/'CURRENT-PHYSICAL-MAPPING-BINDING.json',r['physical_mapping']); js(p/'CURRENT-PHYSICAL-COMPANION-ACCEPTANCE.json',r['physical_mapping']); js(p/'CURRENT-PHYSICAL-DECODER-SOURCE.json',ref(p/'current_numa_image_physical.py'))
    js(p/'STATIC-NONTEMPORAL-INPUTS.json',cfg)
    qualified=cfg['runtime_source_refs']
    need(len(qualified)==6 and len({row['path'] for row in qualified})==6,'complete qualified SIX runtime source references')
    for row in qualified: checked(row)
    expected_hashes={row['path']:row['sha256'] for row in qualified}
    expected_hashes.update({str(path):ref(path)['sha256'] for path in (p/'root_manual_snapshot_threads.py',p/'current_numa_image_physical.py')})
    paths=list(expected_hashes)
    need(len(paths)==len(set(paths))==8,'complete selected EIGHT source FD set')
    identities={}
    for name in paths:
        path=Path(name); fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd); raw=b''
            while True:
                chunk=os.read(fd,1<<20)
                if not chunk: break
                raw+=chunk
            after=os.fstat(fd); named=path.lstat()
            need(stat.S_ISREG(before.st_mode) and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS),'source full9 stableFD '+name)
            need(digest(raw)==expected_hashes[name],'complete selected source SHA')
            identities[name]={k:getattr(before,k) for k in FIELDS}
        finally: os.close(fd)
    js(p/'RUNTIME-SOURCE-FD-IDENTITIES.json',dict(schema='mckernel.current-native.selected-runtime-source-full-fd-identities.v1',identities=identities))
    names=list(code)+['STATIC-NONTEMPORAL-INPUTS.json','RUNTIME-SOURCE-FD-IDENTITIES.json','CURRENT-PHYSICAL-MAPPING-BINDING.json','CURRENT-PHYSICAL-COMPANION-ACCEPTANCE.json','CURRENT-PHYSICAL-DECODER-SOURCE.json']
    js(p/'CHECK-INPUT-PINS.json',[ref(p/name) for name in names]+[r['physical_mapping'],r['physical_report']]); finish(p)

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False); ap.add_argument('phase',choices=('stage','normalization','terminal','runtime')); ap.add_argument('--bindings',required=True); ap.add_argument('--bindings-sha256',required=True); args=ap.parse_args()
    raw=Path(args.bindings).read_bytes(); need(digest(raw)==args.bindings_sha256,'exact dispatcher binding DATA'); b=json.loads(raw)
    {'stage':stage,'normalization':normalization,'terminal':terminal,'runtime':runtime}[args.phase](b)
if __name__=='__main__': main()
