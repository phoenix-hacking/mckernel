"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
TEST_ONLY actual117 materializer→closed123runner→Cold. No live account/runtime calls.
Every fixture resides in the private temporary source-test directory.
"""
from pathlib import Path
import contextlib,copy,hashlib,importlib.util,io,json,sys,tempfile,unittest
D=Path(__file__).resolve().parent;E=D.parents[1];C=D/'cohort'
S=D.parent
OLD=E/'current116-newwindow-integration-source-20261028-1/configured-dependencies-successor-1/cohort'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read(p):return json.loads(Path(p).read_bytes())
def write(p,data):p.write_bytes(data if isinstance(data,bytes) else (json.dumps(data,indent=2)+'\n').encode());return ref(p)

class Pipeline(unittest.TestCase):
 def test_actual_materializer_to_cold(self):
  m=load(C/'materialize_admission.py','TEST_ONLY117materializer')
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY117-',dir=D) as directory:
   T=Path(directory);export=T/'closed123';export.mkdir()
   overlay=read(S/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json');source=read(S/'SOURCE-MAP-FROM116.json');profile=read(C/'PROFILE.TEMPLATE.SOURCE-ONLY.json')
   files=[]
   for row in overlay['files']:
    self.assertEqual(ref(row['source']['path']),row['source']);p=export/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path(row['source']['path']).read_bytes());files.append(dict(relative=row['relative'],snapshot=ref(p)))
   self.assertEqual((len(files),sum(x['relative'].endswith('.rs') for x in files)),(123,112))
   closed=dict(schema='mckernel.exact-kernel-rust-subtree-readonly.v1',runtime_authority=None,export_root=str(export),container_destination='/src/kernel/rust',base_source_root=profile['inputs']['source6153']+'/kernel/rust',files=files,external_inputs=profile['inputs']['external_relative_modules'])
   closedref=write(T/'closed.json',closed)
   baseline=read(E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json')
   schema=ref(D/'OBSERVER-SCHEMA.CURRENT118.SOURCE-ONLY.json');obs=ref(D/'observe_current61_current118.py')
   sr=write(T/'schema-review.TEST_ONLY.json',dict(decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',independent=True,reviewed_observer_schema=schema,TEST_ONLY=True))
   review=write(T/'boundary-review.TEST_ONLY.json',dict(TEST_ONLY=True))
   boundary=dict(author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',root_attests_exact_current_boundary=True,nonce_ledger=baseline['current_ledger'],native_custody_clearance=baseline['current_free'],observer=obs,observer_schema=schema,observer_schema_review=sr,independent_current_boundary_review=review)
   bref=write(T/'boundary.TEST_ONLY.json',boundary)
   testcheckout=T/'TEST_ONLY-canonical';testchanges=[]
   for change in source['writes']:
    after=testcheckout/change['relative'];after.parent.mkdir(parents=True,exist_ok=True);after.write_bytes(Path(change['postimage']['path']).read_bytes());testchanges.append(dict(relative=change['relative'],after=ref(after)))
   m.CHECKOUT_ROOT=testcheckout
   adoption=write(T/'adoption.TEST_ONLY.json',dict(author='/root',TEST_ONLY=True,source_changes=testchanges))
   exporter=load(D/'materialize_source_export.py','TEST_ONLY118exportvalidator');exporter.CHECKOUT_ROOT=testcheckout
   eb=read(D/'ROOT118-EXPORT-INPUT.TEMPLATE.NOT-AUTHORITY.json');eb['source_adoption']=adoption
   valid_overlay,external,_profile=exporter.validate_export(eb)
   self.assertEqual((len(valid_overlay['files']),len(external)),(123,3))
   retained=read(OLD/'ROOT-ACTUAL-BINDINGS-1.json')
   header=write(T/'header.TEST_ONLY.h',Path(retained['actual_generated_header']['path']).read_bytes());metadata=write(T/'metadata.TEST_ONLY.rs',Path(retained['actual_generated_metadata']['path']).read_bytes())
   context=read(retained['actual_origin_binding']['path']);context.update(source_sha256=next(x['postimage']['sha256']for x in source['writes']if x['relative']=='arch/x86_64/kernel/syscall.c'),profile_sha256=ref(S/'candidate/scripts/f06_origin_command_profile.json')['sha256'],command={k:profile['exact_commands'][2][k]for k in ['stage','cwd','argv','new_output']})
   contextref=write(T/'origin-binding.TEST_ONLY.json',context)
   env=write(T/'env.TEST_ONLY.json',dict(MCKERNEL_F06_RT_SIGRETURN_ORIGIN='/src/arch/x86_64/kernel/syscall.c',MCKERNEL_F06_CLONE_CPUID_METADATA_RS=metadata['path']))
   cmake=write(T/'cmake.TEST_ONLY.cmake',Path(retained['actual_CMake_origin']['path']).read_bytes())
   origin=write(T/'origin.TEST_ONLY.json',dict(TEST_ONLY=True,source_generation_only=True,compiler=False,returncode=0,child_positive_join=True,closed_streams=True,argv=read(C/'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json')['argv'],outputs=[header,metadata,contextref,env,cmake]))
   fixture=write(T/'source-review.TEST_ONLY.json',dict(TEST_ONLY=True,runtime_authority=None,independent=True,implementation_ownership=False,decision='PASS_TEST_ONLY_EXACT118_SOURCE_PROFILE',source_map=ref(S/'SOURCE-MAP-FROM116.json'),recipe=ref(S/'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')))
   manifest=write(T/'manifest.TEST_ONLY.json',dict(files=[ref(p)for p in C.glob('*.py')],external_inputs=[ref(E/'CURRENT116-ACCEPTED-ARTIFACT-AND-CURRENTFREE.json')]))
   b=dict(author='/root',decision='MATERIALIZE_REVIEWED_CURRENT118_STATIC_INPUTS_AND_HOLDER_ONLY',maximum_invocations=1,root_attests_exact_UID1000_readonly_exports=True,nonce='e'*32,admission=str(T/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-1'),source_adoption=adoption,current_boundary=bref,nonce_ledger=baseline['current_ledger'],native_custody_clearance=baseline['current_free'],independent_source_profile_review=fixture,mechanical_source_profile_review=fixture,preparation_manifest=manifest,actual_origin_producer=origin,actual_generated_header=header,actual_generated_metadata=metadata,actual_origin_binding=contextref,actual_Rust_environment=env,actual_CMake_origin=cmake,rust_export_root=str(export),rust_export_manifest=closedref)
   boundref=write(T/'root-bindings.TEST_ONLY.json',b)
   # REAL Root61→117 observer/configuration/schema bridge; only live leaves mocked.
   observer=load(D/'observe_current61_current118.py','TEST_ONLY117_observer_producer')
   successor=read(D/'ROOT118-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json')
   successor.update(operation_cutoffs=[1793253600.0,1035704.5689393478,1051042.6959879305],subjects={'observer':obs},source_owners=['/root','/root/m14_compose','/root/restart_guard'],minimum_cumulative_spent='22812.3311',guardian={'source':load(Path(read(D/'RESTART-GUARD-SOURCE-DEPENDENCY.json')['shared_guard']['path']),'TEST_ONLY_guard_data').GUARDIAN_SOURCE,'entrypoint':'guard'})
   successorref=write(T/'op-successor.TEST_ONLY.json',successor)
   opreview=write(T/'op-review.TEST_ONLY.json',dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY_review',operation='current118-build',successor=successor))
   guardref=ref(D/'current118_guard_adapter.py')
   cfg=write(T/'guard-config.TEST_ONLY.json',dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='current118-build',shared_guard=ref(D/'operation_window_guard117.py'),successor=successorref,review=opreview,subjects=successor['subjects']))
   depreview=write(T/'deps-review.TEST_ONLY.json',dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_ROOT61_CURRENT118_OBSERVER_DEPENDENCIES',observer=obs,guard_adapter=guardref,guard_configuration=cfg))
   write(T/'ROOT61-RUNTIME-DEPENDENCIES.json',dict(author='/root',observer=obs,ledger=b['nonce_ledger'],guard_adapter=guardref,guard_configuration=cfg,independent_review=depreview))
   real_observer_load=observer.load
   def no_live_observer_load(reference,name):
    module=real_observer_load(reference,name)
    if reference==guardref:
     real_configure=module.configure
     def configured(configref):
      real_configure(configref)
      module.guard=lambda:[1793170000.0,950000.0,965000.0]
     module.configure=configured
    elif reference==observer.PINS['current60_source']:
     capture=read(observer.PINS['capture2']['path'])
     capture['group_membership_observation']['rows']=[x for x in capture['group_membership_observation']['rows']if x['pid']!=1907223 and x['pgrp']!=1907223]
     module.observe=lambda:capture
    return module
   observer.load=no_live_observer_load;observer.HERE=T;observer.BOUNDARY=Path(bref['path'])
   real_Path=Path
   class AbsentProc:
    def exists(self):return False
   observer.Path=lambda *parts:AbsentProc() if str(real_Path(*parts)).startswith('/proc')else real_Path(*parts)
   observed117=observer.observe()
   self.assertEqual(observed117['current_boundary'],bref)
   self.assertEqual(observed117['Root61'],b['nonce_ledger'])
   self.assertEqual(observed117['actual_latest_operation_postjoin_acceptance'],b['native_custody_clearance'])
   # Only the live account guard and admission-parent location are TEST_ONLY effects.
   # The ACTUAL producer emits every profile clamp/source/export value unchanged.
   actual_load=m.load_runner;counts=dict(guard=0)
   def no_account_runner():
    runner=actual_load()
    def no_account():counts['guard']+=1;return [1793166746,948853,964191]
    runner.current_operation_guard=no_account
    return runner
   m.load_runner=no_account_runner;m.ADMISSION_PARENT=T
   with contextlib.redirect_stdout(io.StringIO()):m.materialize(Path(boundref['path']))
   self.assertEqual(counts['guard'],1)
   A=Path(b['admission']);p=read(A/'PROFILE.SOURCE-ONLY.json');x=read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json')
   self.assertEqual(p['fixed_three_clock_cutoffs'],[1793253600.0,1035704.5689393478,1051042.6959879305])
   self.assertEqual(p['exact_commands'],read(S/'MINIMAL-FOUR-COMMAND-CONTINUATION.NOT-GRANTED.json')['ordered_commands'])
   r=load(A/'run_build_only.py','TEST_ONLY_actual_produced117runner');rows=r.source_directory_postimages(p)
   self.assertEqual(len(rows),123);self.assertEqual(len(r.commands_for_plan(p)),4)
   self.assertEqual(sum(not z['replace'] for z in p['inputs']['objects']),8)
   self.assertEqual(len(x['qualified_readonly_files']),len(p['inputs']['configuration'])+8+len(p['inputs']['postimages'])+123)
   # Execute unchanged real cold producer with exact materialized117 outputs.
   finite=load(C/'finite_review.py','TEST_ONLY117cold');H=A/'FINITE-REVIEW-HANDOFF';H.mkdir()
   template=read(OLD/'REVIEWER-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');refs=template['static_refs']
   mapping=dict(profile='PROFILE.SOURCE-ONLY.json',input_export='ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json',request_payload='STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json',request_adoption='ROOT-REQUEST-ADOPTION.json',runner='run_build_only.py',worker='build_only_worker.py',holder_source='hold_and_run_build_only.py',publisher_source='publish_approved_ready.py')
   for key,name in mapping.items():refs[key]=ref(A/name)
   for key,name in dict(capture_source='capture_resources.py',finite_verifier='finite_review.py',handoff_common='handoff_common.py',hot_predicates='hot_predicates.py',root_capture_source='root_capture_once.py',publisher_adapter='publish_after_independent_pass_once.py').items():refs[key]=ref(C/name)
   refs.update(nonce_ledger=b['nonce_ledger'],native_custody_clearance=b['native_custody_clearance'],current_boundary=bref,observer_source=obs,source_adoption=adoption,source_review=fixture,mechanical_review=fixture,current_boundary_review=review,observer_schema=schema,observer_schema_review=sr)
   pub=write(T/'publication.TEST_ONLY.json',dict(TEST_ONLY=True,runtime_authority=None,status='PASS_FETCHED_CURRENT118_TEST_ONLY_NOT_ACTUAL_PUBLICATION',commit='0'*40,unchanged_accepted_SDK=True,passed_compiler_prefix_replayed=False,rows=[dict(actual=v)for v in refs.values()if isinstance(v,dict)]));refs['source_publication']=pub
   template.update(reviewer=finite.REVIEWER,Root_must_not_execute_approver=True,admission=str(A),nonce=b['nonce'],authorized_cutoffs=p['fixed_three_clock_cutoffs'])
   bindings=write(T/'cold-bindings.TEST_ONLY.json',template);template['_bindings']=bindings['path']
   original_load=finite.load
   def no_live_load(reference,name):
    module=original_load(reference,name)
    if reference==refs['runner']:module.current_operation_guard=lambda:[1793166746,948853,964191]
    return module
   finite.load=no_live_load;finite.clocks=lambda:[1793166746,948853,964191]
   cold=finite.cold(template,H)
   self.assertEqual(cold['p']['inputs']['source_directory_exports'][0]['manifest'],closedref)
   self.assertEqual(cold['limits'],p['fixed_three_clock_cutoffs'])
   self.assertTrue((H/'PREWARM_READY.json').exists())
   # ACTUAL hot verifier consumes the ACTUAL117 cold producer's exact static data.
   # Retained116 physical/resource records seed explicit TEST_ONLY leaf observations.
   OA=E/'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1'
   oldmarker=read(OA/'FINITE-REVIEW-HANDOFF/ROOT-HELD-CAPTURE.COMPLETE.json')
   physical=read(oldmarker['physical']['path']);resource=read(oldmarker['resource']['path']);inputs=read(oldmarker['root_resource_input']['path']);ready=read(oldmarker['holder_ready']['path']);pending=read(oldmarker['pending_input']['path'])
   now=[1793170000.0,950000.0,965000.0]
   physical.update(TEST_ONLY=True,current_boundary=bref,observer=obs,observed_clocks=[v-3 for v in now])
   physical['physical']=observed117
   physicalref=write(T/'physical.TEST_ONLY.json',physical)
   for key,refkey in [('profile','profile'),('runner','runner'),('worker','worker'),('input_export_authority','input_export'),('native_custody_clearance','native_custody_clearance'),('nonce_ledger','nonce_ledger'),('current_boundary','current_boundary'),('source_publication','source_publication')]:inputs[key]=refs[refkey]
   inputs.update(TEST_ONLY=True,nonce=b['nonce'],at_epoch=now[0]-2,request_sha256=p['request_sha256'],physical_observation=physicalref)
   inputref=write(T/'resource-input.TEST_ONLY.json',inputs)
   bootstrapref=ref(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
   ready.update(TEST_ONLY=True,nonce=b['nonce'],bootstrap=bootstrapref)
   readyref=write(T/'holder-ready.TEST_ONLY.json',ready)
   resource.update(TEST_ONLY=True,nonce=b['nonce'],reservation_owner=b['nonce'],observed_clocks=[v-1 for v in now],observed_at_epoch=now[0]-1,native_custody_clearance=b['native_custody_clearance'],reservation_ready_record=readyref,fresh_output_root=str(A/'OUTPUT'))
   resource['actual_observations'].update(physical_observation=physicalref,Root_resource_input=inputref)
   resourceref=write(T/'resource.TEST_ONLY.json',resource)
   for key,refkey in [('runner','runner'),('worker','worker'),('profile','profile'),('input_export_authority','input_export')]:pending[key]=refs[refkey]
   pending.update(TEST_ONLY=True,nonce=b['nonce'],resource_authority=resourceref,native_custody_clearance=b['native_custody_clearance'],fresh_output_root=str(A/'OUTPUT'),review=None)
   pendingref=write(T/'pending.TEST_ONLY.json',pending)
   marker=dict(status='ROOT_HELD_CAPTURE_COMPLETE_ZERO_POSITIVE_JOIN',returncode=0,direct_child_joined=True,group_absent=True,closed_streams=True,prewarm_ready=cold['ready_ref'],nonce=b['nonce'],admission=str(A),capture_source=refs['capture_source'],pending_input=pendingref,resource=resourceref,physical=physicalref,root_resource_input=inputref,holder_ready=readyref,holder_bootstrap=bootstrapref)
   write(H/'ROOT-HELD-CAPTURE.COMPLETE.json',marker)
   holder=ready['holder'];locks=resource['actual_observations']['lock_rows']
   realpath=Path
   class ProcFixture:
    def __init__(self,path):self.path=str(path)
    def __truediv__(self,part):return ProcFixture(self.path+'/'+str(part))
    def stat(self):return type('StatTESTONLY',(),dict(st_dev=27,st_ino=4))()
    def read_text(self):
     return {'/proc/locks':locks,'/proc/meminfo':'MemAvailable: 50331648 kB\n','/proc/loadavg':'0 0 0 1/100 100','/proc/sys/kernel/threads-max':'1000000'}[self.path]
   finite.Path=lambda *parts:ProcFixture(realpath(*parts)) if str(realpath(*parts)).startswith('/proc') else realpath(*parts)
   finite.birth=lambda pid:holder['starttime']
   cold['runner'].current_operation_guard=lambda:list(now)
   result=finite.hot(cold,marker)
   self.assertEqual(result['earliest_clamps'],p['fixed_three_clock_cutoffs'])
   self.assertEqual(result['resource_age_seconds'],1.0)
   badresource=copy.deepcopy(resource);badresource['observed_at_epoch']=now[0]-121
   badref=write(T/'stale-resource.TEST_ONLY.json',badresource)
   badmarker=copy.deepcopy(marker);badmarker['resource']=badref
   # Exact pending/resource identity catches any unreviewed replacement too.
   with self.assertRaises((ValueError,AssertionError)):finite.hot(cold,badmarker)
   # Cheap negatives exercise the actual pure binding producer, not copied keys.
   for key in ['source_adoption','actual_origin_producer','rust_export_manifest']:
    bad=copy.deepcopy(b);bad[key]['sha256']='0'*64
    with self.assertRaises(AssertionError):m.validate118(bad)
   old_cutoffs=copy.deepcopy(p);old_cutoffs['fixed_three_clock_cutoffs'][1]=1035706.5689547858
   self.assertGreater(old_cutoffs['fixed_three_clock_cutoffs'][1],cold['limits'][1])
   self.result=dict(status='PASS_TEST_ONLY_ACTUAL117_MATERIALIZER_TO_COLD_AND_HOT',profile_clamps=p['fixed_three_clock_cutoffs'],source_closure=len(rows),commands=4,retained_objects=8,live_guard_calls=0,compiler_calls=0)

 def test_guard_initial117_and_observer_predicates(self):
  g=load(D/'operation_window_guard117.py','TEST_ONLYnew117guard');s=read(D/'ROOT118-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json')
  s.update(operation_cutoffs=[1793253600.0,1035704.5689393478,1051042.6959879305],subjects={'source':ref(D/'observe_current61_current118.py')},source_owners=['/root','/root/m14_compose','/root/restart_guard'],minimum_cumulative_spent='22812.3311',guardian={'source':g.GUARDIAN_SOURCE,'entrypoint':'guard'})
  review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/TEST_ONLY_review',operation='current118-build',successor=copy.deepcopy(s))
  self.assertEqual(g.validate_operation(s,review,'current118-build',s['subjects'],[1793166746,948853,964191]),tuple(s['operation_cutoffs']))
  for key,value in [('predecessor_cutoffs',[0,0,0]),('first_prepared_window_sha256','old')]:
   bad=copy.deepcopy(s);bad[key]=value;badreview=copy.deepcopy(review);badreview['successor']=bad
   with self.assertRaises(ValueError):g.validate_operation(bad,badreview,'current118-build',bad['subjects'],[1793166746,948853,964191])
  observer=load(D/'observe_current61_current118.py','TEST_ONLY117current61');ledger,free,ext,actors=observer.validate_current(observer.CURRENT)
  self.assertEqual(len(ledger['consumed_nonces']),70);self.assertEqual(len(actors),61)
  self.assertEqual(free['prior_native_nonce'],'4d1c28c2d9caa913e4ab1e8a504ac5ea');self.assertFalse(free['native_operation_reclassified_as_ordinary'])

if __name__=='__main__':unittest.main(verbosity=2)
