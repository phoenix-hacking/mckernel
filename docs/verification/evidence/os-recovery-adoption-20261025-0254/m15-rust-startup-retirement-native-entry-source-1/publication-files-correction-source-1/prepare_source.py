"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fresh Root44 data/path successor; old refusal/helper tree stays untouched.
"""
from pathlib import Path
import json,hashlib,re,ast,difflib
C=Path(__file__).resolve().parent;D=C.parent;E=D.parent;T=C/'templates';T.mkdir(exist_ok=True)
OLD_NONCE='5fe0acdfcc75309f0cb40ddb1178b88b';NONCE='22a1d92ed402f4d333bf527185e792b2'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def js(n,x):(C/n).write_text(json.dumps(x,indent=2)+'\n')
L=ref(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER44.json');assert L['sha256']=='00ed4748c3cc06b67526d716c1ca0adb8ba31965c7c3d16e6325aceb612d3f0c';ledger=read(L['path']);assert len(ledger['consumed_nonces'])==45 and OLD_NONCE in ledger['reserved_abandoned_unconsumed_nonces'] and NONCE not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']
FREE=ledger['latest_accepted_free_boundary'];assert FREE['sha256']=='221349f9f93973b57c7d6b4a69d79d9f8e6dd2dcd368d16a08fcfac88c054d0d'
oldctx=read(D/'SOURCE-CONTEXT.json');oldL=oldctx['Root43'];ctx=json.loads(json.dumps(oldctx));ctx.pop('Root43');ctx.update(Root44=L,Root43_historical=oldL,status='FRESH_ROOT44_AFTER_ABANDONED_PRECAPTURE_5FE0_NOT_RELEASED',nonce=NONCE)
p=read(D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json');p=json.loads(json.dumps(p).replace(str(D/'root-adopted-retirement-entry-1'),str(C/'root-adopted-retirement-entry-1')).replace(OLD_NONCE,NONCE));p.update(root_ledger35=L,latest_serial_operation_physical_acceptance=FREE,source_authority=None,case_capability=None,nonce_reservation=None,scratch_manifest_stage=None,stage_map_acceptance=None,source_only_QMPproof=None,root_runtime_grant=None,source_publication=None,runtime_authority=None,status='FRESH_ROOT44_PUBLICATION_FILES_CORRECTION_SOURCE_ONLY');js('STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p)
files=[]
for old in sorted((D/'templates').glob('*.py')):
 s=old.read_text();new=s.replace(str(D),str(C)).replace(OLD_NONCE,NONCE).replace('ROOT-CURRENT-NONCE-LEDGER43.json','ROOT-CURRENT-NONCE-LEDGER44.json').replace(oldL['sha256'],L['sha256'])
 if old.name=='root_once_startup_entry.py':new=new.replace("GUARD = BASE.parent/","GUARD = Path("+repr(str(E))+")/")
 # Status/context names truthful; no resource/clock/claim/publication predicate change.
 if old.name=='prepare_startup_bindings.py':new=new.replace('exact actual Root42-or43/free boundary','exact actual Root44/free boundary')
 (T/old.name).write_text(new);ast.parse(new);files.append(dict(name=old.name,retained=ref(old),template=ref(T/old.name)))
ctx['helper_sources']=files;ctx['preserved_refusal_reconciliation']=ref(D/'ROOT-5FE0-PRECAPTURE-REFUSAL-RECONCILIATION.json');js('SOURCE-CONTEXT.json',ctx)
f=(D/'finalize_context.py').read_text().replace(OLD_NONCE,NONCE).replace("context['Root43']","context['Root44']").replace('Root43','Root44').replace('ROOT43','ROOT44')
f=re.sub(r"CONTEXT_SHA='[0-9a-f]{64}'","CONTEXT_SHA="+repr(ref(C/'SOURCE-CONTEXT.json')['sha256']),f,1);f=re.sub(r"STATIC_TEMPLATE_SHA='[0-9a-f]{64}'","STATIC_TEMPLATE_SHA="+repr(ref(C/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')['sha256']),f,1);(C/'finalize_context.py').write_text(f);ast.parse(f)
q=read(D/'scratch-stage-context-join-source-1/ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json');q.update(author=None,nonce=NONCE,root_ledger=L,latest_free=FREE,source_authority=None,case_capability=None,nonce_reservation=None,scratch_manifest_stage=None,actual_release_ledger_is_latest=None,Root_attests_no_intervening_operation_since_boundary=None,current_capture_independent_source_review=None,current_capture_source=ref(T/'capture_fresh_startup_resource.py'),known_source_checkpoint=dict(Root44=L,latest114free=FREE,preserved_old_5fe0_reconciliation=ctx['preserved_refusal_reconciliation']));js('ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json',q)
qmp=p['attempt_parent']+'/attempt-'+NONCE+'/qmp.sock';assert len(qmp.encode())==92<108
js('QMP-ABSOLUTE-PATH-PREFLIGHT.SOURCE-ONLY.json',dict(scope=p['scope'],runtime_authority=None,nonce=NONCE,absolute_socket_path=qmp,encoded_bytes=92,limit_exclusive=108,owner=p['owner_source']))
# Required existing pre-capture schema is retained exactly, never alias rows.
s=(T/'run_startup_resource_once.py').read_text();assert s==(D/'templates/run_startup_resource_once.py').read_text() and "publication['files']" in s and s.index("publication['files']")<s.index('capture=retain(')
js('ROOT-PUBLICATION-FILES-SCHEMA.NOT-AUTHORITY.json',dict(scope=p['scope'],runtime_authority=None,required_actual_status='PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS',required_actual_key='files',required_actual_type='list of exact path/bytes/sha256 refs; includes static and everycapture_sources entry',rows_is_not_alias=True,old_publication_or_namespace_not_reusable=True,existing_guard=ref(T/'run_startup_resource_once.py'),orchestration_requirement='Inspect resourcewrapper rc0 + positivejoin + actualresource/pendingfiles before independent executionreview and bridge; any nonzero/exception meansSTOP, no bridge, preserve namespace.'))
for name in ['capture_fresh_startup_resource.py','prepare_startup_bindings.py','root_once_startup_entry.py']:
 (C/(name+'.Root44.diff')).write_text(''.join(difflib.unified_diff((D/'templates'/name).read_text().splitlines(True),(T/name).read_text().splitlines(True),fromfile='preserved5fe0/'+name,tofile='freshRoot44/'+name)))
ready=dict(scope=p['scope'],status='READY_FRESH_ROOT44_PUBLICATION_FILES_SCHEMA_SOURCE_ONLY_NOT_RELEASED',runtime_authority=None,profile_unchanged=True,source_files=[ref(x) for x in sorted(T.glob('*.py'))]+[ref(C/x) for x in ['finalize_context.py','SOURCE-CONTEXT.json','STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json','ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json','QMP-ABSOLUTE-PATH-PREFLIGHT.SOURCE-ONLY.json']],Root44=L,current_free=FREE,nonce=NONCE,preserved_old_reconciliation=ctx['preserved_refusal_reconciliation'],old5fe0_abandoned_unconsumed=True,normal3helpers_byteexact=True,required_publication_files_guard_retained=True,QMP_bytes=92,actual_authority_capability_reservation_join=None,guard_query_resource_native_cleanup_canonical=0)
js('READY.json',ready);print(json.dumps(dict(READY=ref(C/'READY.json'),capture=ref(T/'capture_fresh_startup_resource.py'))))
