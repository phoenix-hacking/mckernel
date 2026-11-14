from pathlib import Path
import json,hashlib,ast,shutil
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254');A=E/'restart-adoption-20261029T0234';D=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1';W=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1');OLD=A/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/expert-census-observer-consumer-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
arm=json.loads((W/'ACTUAL-CONTROLS-ARMED.json').read_bytes());cuts=[arm['caps'][k]for k in ['deadline','monotonic_deadline','boot_deadline']]
g=ref(D/'guardian_guard.py')
s=(D.parent/'operation_window_guard64.weekly-template.py').read_text()
binding=dict(weekly_limit_identity=dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774133),window_sha256=ref(W/'ACTUAL-WINDOW.json')['sha256'],billing_mode='included_only',allow_prepaid_fallback=False,armed_receipt=ref(W/'ACTUAL-CONTROLS-ARMED.json'),guardian=g,operation_cutoffs=cuts)
s=s.replace('RUNTIME_BINDINGS=None','RUNTIME_BINDINGS='+repr(binding))
a=s.index(" need(RUNTIME_BINDINGS['armed_receipt']");b=s.index(' return RUNTIME_BINDINGS',a)
s=s[:a]+" authenticated(RUNTIME_BINDINGS['armed_receipt'])\n authenticated(RUNTIME_BINDINGS['guardian'])\n"+s[b:]
s=s.replace("operation=='current118-postjoin-current64'","operation in ('current118-postjoin-current64','bfd-postjoin-current62')")
s=s.replace('PRIVATE UNBOUND weekly consumer template. No runtime/source approval is conveyed.','Private actual-bound weekly operation consumer. Separate exact operation review required.')
(D/'operation_window_guard.py').write_text(s);ast.parse(s);shared=ref(D/'operation_window_guard.py')
# Source-only recursive data layout. Existing typed filler and physical successor reused.
oldpins=json.loads((OLD/'INPUTS.json').read_bytes());B=Path(oldpins['base_source']['path']).parent;R=D/'recursive-current62';H=R/'history';H.mkdir(parents=True,exist_ok=True)
for name in ['observe_bfd_root59_history.py','observe_bfd_current60_history.py']:
 shutil.copy2(B/'history'/name,H/name)
# Existing current60 uses sibling data, so code remains byte-identical.
cp=json.loads((B/'history/ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json').read_bytes());cp['common_source']=ref(H/'observe_bfd_root59_history.py');cp['common_dependencies']=None
put(H/'ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json',cp)
# Root61 alone contains an active old literal clock clamp and current60 source pin.
s=(B/'history/observe_bfd_current61.py').read_text();tree=ast.parse(s);node=next(n for n in tree.body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='PINS');v=ast.literal_eval(node.value);v['current60_source']=ref(H/'observe_bfd_current60_history.py');lines=s.splitlines(True);lines[node.lineno-1:node.end_lineno]=['PINS='+repr(v)+'\n'];s=''.join(lines)
assert s.count('(1793253600.0,1035704.5689393478,1051042.6959879305)')==1;s=s.replace('(1793253600.0,1035704.5689393478,1051042.6959879305)',repr(tuple(cuts)))
(H/'observe_bfd_current61.py').write_text(s)
for name in ['ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json','ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json']:
 v=json.loads((B/'history'/name).read_bytes());key='observer';v[key]=ref(H/('observe_bfd_current61.py'if name.startswith('ROOT61')else'observe_bfd_root59_history.py'));put(H/name,v)
shutil.copy2(B/'bind_history.py',R/'bind_history.py')
# Current62 live source delegates accepted historical adoption to the complete
# immutable old validator. No historical descriptor/source is relabeled.
s=(B/'observe_current62_bfd_postjoin.py').read_text()
old="else:current_capture=validate_current_adoption(bindings,retained)"
new="else:current_capture=load("+repr(ref(B/'observe_current62_bfd_postjoin.py'))+",'frozen_historical_Root63_adoption_only').validate_current_adoption(bindings,retained)"
assert s.count(old)==1;s=s.replace(old,new);(R/'observe_current62_bfd_postjoin.py').write_text(s)
bp=json.loads((B/'INPUTS.json').read_bytes());bp.update(guardian=g,shared_guard=shared,limits=cuts,history_runtime_source=ref(H/'observe_bfd_current61.py'));put(R/'INPUTS.json',bp)
# Existing filler checks same new guard/config at Root61/common/physical depths.
for n in ['ROOT61-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json','ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json']:
 v=json.loads((H/n).read_bytes())
 if n.startswith('ROOT61'):v['guard_adapter']=bp['guard_adapter']
 else:v['account_window_guard']=bp['guard_adapter']
 put(H/n,v)
# Existing physical source uses explicit reviewed runtime data (no source edit).
physical=json.loads((H/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.TEMPLATE.NOT-AUTHORITY.json').read_bytes())['physical_history_observer']
# Outer source keeps every historical validator/actor addition. It adds only
# typed explicit live recursive source/data routing and closure declarations.
s=(OLD/'observe_current64_current118_postjoin.py').read_text()
s=s.replace("keys=['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','custody_supplement']", "keys=['ledger','retirement_result','retirement_parent_join','guard_adapter','guard_configuration','custody_supplement','recursive_current63_bindings']")
s=s.replace("historical=retained['base'].observe(checked(PINS['base_bindings']),out)","historical=load(PINS['runtime_base_source'],'weekly_recursive_Root63_live_observer').observe(checked(bindings['recursive_current63_bindings']),out)")
a=" result=dict(observer=ref(__file__),inputs=ref(HERE/'INPUTS.json'))"
z=a+"\n runtime=load(PINS['runtime_base_source'],'weekly_recursive_source_closure');result['runtime_base_source']=PINS['runtime_base_source'];auth(PINS['runtime_base_source']);result.update({'weekly_recursive:'+key:value for key,value in runtime.source_subjects().items()})"
assert s.count(a)==1;s=s.replace(a,z)
a="base.capture_scope(),new_operation=PINS['operation']";z="base.capture_scope(),explicit_weekly_recursive_entry=PINS['runtime_base_source'],explicit_weekly_recursive_scope=load(PINS['runtime_base_source'],'weekly_recursive_capture_scope').capture_scope(),new_operation=PINS['operation']";assert s.count(a)==1;s=s.replace(a,z)
(D/'observe_current64_current118_postjoin.py').write_text(s)
p=oldpins;p.update(guardian=g,shared_guard=shared,limits=cuts,runtime_base_source=ref(R/'observe_current62_bfd_postjoin.py'));put(D/'INPUTS.json',p)
# All mutable runtime dependency data remain explicit Root/reviewer slots.
v=json.loads(Path(oldpins['base_bindings']['path']).read_bytes());v.update(guard_configuration=None,independent_review=None);put(R/'ROOT63-WEEKLY-LIVE-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',v)
q=dict(author='/root',decision='BIND_REVIEWED_ROOT62_HISTORY_DEPENDENCIES_SOURCE_ONLY',runtime_authority=None,guard_configuration=None,physical_configuration=None,common_dependency_review=None,Root61_dependency_review=None);put(R/'ROOT-HISTORY-INPUT.TEMPLATE.NOT-AUTHORITY.json',q)
# Static source references are now final; no operation data or release generated.
for path in [D/'guardian_guard.py',D/'operation_window_guard.py',D/'observe_current64_current118_postjoin.py',R/'observe_current62_bfd_postjoin.py',R/'bind_history.py']+list(H.glob('*.py')):ast.parse(path.read_text())
put(D/'SOURCE-EXTERNAL-INPUTS.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',armed=ref(W/'ACTUAL-CONTROLS-ARMED.json'),config=ref(W/'armed-controller/CONFIG.json'),packet=ref(W/'armed-controller/FROZEN-PACKET.json'),window=ref(W/'ACTUAL-WINDOW.json'),authorization=ref(W/'USER-WEEKLY-ONLY-AUTHORIZATION.json'),earliest=ref(W/'EARLIEST-CONTROL-CAPS.json'),policy=ref(W/'weekly_policy.py'),monitor_arm=ref(W/'twenty-minute-steering/ARM-BINDING.json'),phone_packet=ref(W/'phone-window-adapter/PHONE-PACKET.json'),physical_successor=physical))
print('WEEKLY_GUARD',g);print('SHARED',shared);print('OUTER',ref(D/'observe_current64_current118_postjoin.py'));print('NESTED',ref(R/'observe_current62_bfd_postjoin.py'))
