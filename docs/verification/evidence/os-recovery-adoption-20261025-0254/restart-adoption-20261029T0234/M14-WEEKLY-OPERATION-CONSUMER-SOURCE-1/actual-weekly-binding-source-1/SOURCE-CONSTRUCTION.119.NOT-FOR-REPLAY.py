from pathlib import Path
import shutil,json,hashlib,ast
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254');A=E/'restart-adoption-20261029T0234';D=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1';W=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1');B=E/'CURRENT119-JOINT-M14-REGISTRY-REPAIR-SOURCE-1/m14-exclusive-producer-binding-1';OLD=B/'root-sealer-predicate-correction-source-1/actual-guardian-schema-binding-source-1/expert-census-observer-binding-source-1';N=D/'current119';N.mkdir(exist_ok=True)
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for name in ['accepted_bindings.py','seal_root_current119_inputs.py','run_build_only.corrected-template.py','hold_and_run_build_only.py','ROOT-CURRENT119-INPUT.TEMPLATE.NOT-AUTHORITY.json']:shutil.copy2(OLD/name,N/name)
s=(N/'accepted_bindings.py').read_text();tree=ast.parse(s);lines=s.splitlines(True)
for node in tree.body:
 if isinstance(node,ast.Assign)and isinstance(node.targets[0],ast.Name):
  name=node.targets[0].id
  if name=='GUARDIAN':lines[node.lineno-1:node.end_lineno]=['GUARDIAN=Path('+repr(str(D/'guardian_guard.py'))+')\n']
  elif name=='ORIGINAL_MAX':lines[node.lineno-1:node.end_lineno]=['ORIGINAL_MAX=[1793774133,1556237.568944064,1571575.6959913536]\n']
s=''.join(lines);oldobs=ref(A/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/expert-census-observer-consumer-source-1/observe_current64_current118_postjoin.py');assert s.count(repr(oldobs))==1;s=s.replace(repr(oldobs),repr(ref(D/'observe_current64_current118_postjoin.py')))
a=s.index('def armed_metadata(');b=s.index('\n\ndef review_binds_guard',a)
s=s[:a]+'''WEEKLY_BINDINGS_REF='''+repr(ref(D.parent/'weekly_source_bindings.py'))+'''
WEEKLY_AUTH_REF='''+repr(ref(W/'USER-WEEKLY-ONLY-AUTHORIZATION.json'))+'''
WEEKLY_WINDOW_REF='''+repr(ref(W/'ACTUAL-WINDOW.json'))+'''
WEEKLY_GUARDIAN_REF='''+repr(ref(D/'guardian_guard.py'))+'''

def weekly_limits(armed,bootstrap):
 binding=load(WEEKLY_BINDINGS_REF,'pure_actual_weekly_caps')
 return binding.minimum_caps(read(WEEKLY_AUTH_REF),read(WEEKLY_WINDOW_REF),bootstrap,armed['caps'])

def armed_metadata(armed,packet_ref,current_thread,bootstrap):
 guardian=load(WEEKLY_GUARDIAN_REF,'exact_weekly_guardian_metadata_only')
 need(current_thread==guardian.THREAD and packet_ref['sha256']==guardian.PACKET_SHA,'actual weekly current Root/packet')
 guardian.validate_armed_metadata(armed) # Pure function; never guardian.guard().
 return weekly_limits(armed,bootstrap)
'''+s[b:]
(N/'accepted_bindings.py').write_text(s)
s=(N/'seal_root_current119_inputs.py').read_text();a=s.index('NEWSC=Path(');b=s.index('\n\ndef cutoffs',a);s=s[:a]+"NEWSC=Path("+repr(str(W))+")\nINITIAL=NEWSC/'EARLIEST-CONTROL-CAPS.json'\n"+s[b:]
s=s.replace('minimum=accepted.CUTOFF.bind_cutoffs(accepted.ORIGINAL_MAX,armed,bootstrap)','minimum=accepted.weekly_limits(armed,bootstrap)')
(N/'seal_root_current119_inputs.py').write_text(s)
for p in [N/'accepted_bindings.py',N/'seal_root_current119_inputs.py']:ast.parse(p.read_text())
print('119helper',ref(N/'accepted_bindings.py'));print('119sealer',ref(N/'seal_root_current119_inputs.py'))
