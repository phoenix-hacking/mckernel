"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Adapt existing producer DATA to actual119 adoption/export, without generating origin,
copying sources, executing guards/compilers or granting any build.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
JOINT=HERE.parent
E=JOINT.parent
ACTUAL=E/'restart-adoption-20261029T0234'
OLD=E/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3'
SCOPE=__doc__.splitlines()[0]

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 assert type(row)is dict and set(row)=={'path','bytes','sha256'} and Path(row['path']).is_absolute() and not Path(row['path']).is_symlink() and ref(row['path'])==row
 return Path(row['path'])
def read(path):return json.loads(Path(path).read_bytes())
def write(name,value):
 with (HERE/name).open('x')as stream:stream.write(value if isinstance(value,str)else json.dumps(value,indent=2)+'\n')

def actual_inputs():
 adoption_path=ACTUAL/'M14-CANONICAL119-SOURCE-ADOPTION-1/ROOT-SOURCE-ADOPTION.ACTUAL.json'
 export_path=ACTUAL/'CURRENT119-EXACT-RUST-SOURCE-EXPORT-1/SOURCE-EXPORT.ACTUAL.json'
 assert ref(adoption_path)['sha256']=='45d2e604c96f15b189d0f22c98ee2ec5300feb82877b1e91cce0f81c94f9e664'
 assert ref(export_path)['sha256']=='607fa54fca73452ea8d45e7bf078050e7808ed9bf4e398e587248f662c120b53'
 adoption=read(adoption_path);export=read(export_path);profile=read(OLD/'PROFILE.SOURCE-ONLY.json')
 assert adoption['author']=='/root' and adoption['status']=='PASS_EXACT18_CANONICAL119_SOURCE_ADOPTION_ONLY' and len(adoption['canonical_rows'])==18
 assert export['author']=='/root' and export['canonical_adoption']==ref(adoption_path) and export['files_count']==133 and export['rust_count']==122 and len(export['files'])==133
 expected=read(JOINT/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json')['files']
 adopted={r['relative']:r['actual']for r in adoption['canonical_rows']}
 assert [dict(relative=r['relative'],source=r['source'])for r in export['files']]==[dict(relative=r['relative'],source=adopted.get('kernel/rust/'+r['relative'],r['source']))for r in expected]
 for row in adoption['canonical_rows']:
  assert auth(row['actual']).read_bytes()==auth(row['owner_source']).read_bytes()
 root=Path(export['directory']);files=[]
 for row in export['files']:
  current=auth(row['actual_export']);assert current==root/row['relative'] and (row['actual_export']['bytes'],row['actual_export']['sha256'])==(row['source']['bytes'],row['source']['sha256'])
  files.append(dict(relative=row['relative'],snapshot=row['actual_export']))
 assert {str(p.relative_to(root))for p in root.rglob('*')if p.is_file()}=={r['relative']for r in files}
 return adoption_path,adoption,export_path,export,profile,files

def main():
 adoption_path,adoption,export_path,export,profile,files=actual_inputs()
 recipe_path=JOINT/'CURRENT119-FOUR-COMMANDS.NOT-GRANTED.json';recipe=read(recipe_path)
 manifest=dict(schema='mckernel.exact-kernel-rust-subtree-readonly.v1',runtime_authority=None,export_root=export['directory'],container_destination='/src/kernel/rust',base_source_root=profile['inputs']['source6153']+'/kernel/rust',files=files,external_inputs=profile['inputs']['external_relative_modules'],actual_export_receipt=ref(export_path),actual_canonical_adoption=ref(adoption_path))
 write('CURRENT119-EXISTING-EXPORT-MANIFEST.json',manifest)
 adopted={r['relative']:r['actual']for r in adoption['canonical_rows']}
 for row in profile['inputs']['postimages']:
  if row['relative']in adopted:row['postimage']=adopted[row['relative']]
  if row['relative'].startswith('kernel/rust/f06-origin/'):row['postimage']=None
 profile['inputs']['source_directory_exports']=[dict(host_path=export['directory'],container_destination='/src/kernel/rust',readonly=True,manifest=ref(HERE/'CURRENT119-EXISTING-EXPORT-MANIFEST.json'))]
 profile['exact_commands']=recipe['ordered_commands']
 clock=read(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1/bootstrap/initial-watch-clock.json'))
 profile['fixed_three_clock_cutoffs']=[clock['deadline'],clock['watcher_cutoff_lower'],clock['boot_deadline']];profile['deadline_epoch']=clock['deadline']
 profile['status']='CURRENT119_ACTUAL_SOURCE_EXPORT_BOUND_ORIGIN_REQUEST_RUNTIME_FIELDS_REQUIRED'
 for key in ['request_sha256','native_custody_clearance','actual_nonce','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder','actual_source_publication','origin_source_materialization','source_preparation_current_context']:
  profile[key]=None
 profile['actual_root_adoption']=ref(adoption_path)
 profile['qualified119_source_recipe']=ref(recipe_path)
 profile['producer_contract']['source']='Exact integrated119 canonical18 + actual closed133/122Rust export + retained external3; genuine119 origin still required'
 profile['producer_contract']['process_delta']='Accepted116 process object retained unchanged;119 combines reviewed F03 BODY3-13/F06 BODY3-12 with original389 source identity repairs.'
 profile['producer_contract']['postbuild_required'].append('Actual119 original389 tuple multiset must match unchanged oracleaf46e443; no expected-record rewriting or ELF patch.')
 reuse=read(Path(profile['reuse_descriptor']));reuse['actual_commands']=recipe['ordered_commands'];reuse['Rust_source_map']=ref(JOINT/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json');reuse['genuine_new119_origin_required']=True
 write('CURRENT119-EIGHT-OBJECT-REUSE.json',reuse);profile['reuse_descriptor']=str(HERE/'CURRENT119-EIGHT-OBJECT-REUSE.json')
 profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage'])for r in profile['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot'])for r in files]
 write('PROFILE.TEMPLATE.SOURCE-ONLY.json',profile)
 old=(OLD/'run_build_only.py').read_text();new=old
 start=new.index('RUNTIME_GUARD_REF=');end=new.index('\n',start);new=new[:start]+'RUNTIME_GUARD_REF=None  # Root must seal exact fresh current119 operation consumer.'+new[end:]
 start=new.index('COMMAND_RECIPE_REF=');end=new.index('\n',start);new=new[:start]+'COMMAND_RECIPE_REF='+repr(ref(recipe_path))+new[end:]
 oldcount="len(manifest['files'])==123 and sum(row['relative'].endswith('.rs') for row in manifest['files'])==112"
 assert new.count(oldcount)==1;new=new.replace(oldcount,"len(manifest['files'])==133 and sum(row['relative'].endswith('.rs') for row in manifest['files'])==122")
 oldpath="path = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/runtime_guard.py')"
 assert new.count(oldpath)==1;new=new.replace(oldpath,'path = auth(RUNTIME_GUARD_REF)')
 new=new.replace("name='current118-build-build-only-'","name='current119-build-build-only-'")
 new=new.replace('    current_operation_guard()\n    argv=docker_argv(profile,name,rows,output)','    argv=docker_argv(profile,name,rows,output)')
 new=new.replace('        result=subprocess.run(argv,stdout=stdout,stderr=stderr,check=False)','        current_operation_guard()\n        result=subprocess.run(argv,stdout=stdout,stderr=stderr,check=False)')
 ast.parse(new);write('run_build_only.template.py',new)
 write('MINIMAL-RUNNER-DELTA.patch',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='actual118/run_build_only.py',tofile='private119/run_build_only.template.py')))
 write('hold_and_run_build_only.py',(OLD/'hold_and_run_build_only.py').read_text())
 worker=(OLD/'build_only_worker.py').read_text();a=worker.index('CUTOFFS=');b=worker.index('\n',a);worker=worker[:a]+'CUTOFFS='+repr(profile['fixed_three_clock_cutoffs'])+worker[b:];worker=worker.replace("plan['deadline_epoch']==1793253600","plan['deadline_epoch']==CUTOFFS[0]");write('build_only_worker.template.py',worker)
 write('SOURCE-BINDING-RESULT.json',dict(scope=SCOPE,status='PASS_EXISTING119_CANONICAL_EXPORT_TO_PRODUCER_DATA_ONLY',actual_adoption=ref(adoption_path),actual_export=ref(export_path),manifest=ref(HERE/'CURRENT119-EXISTING-EXPORT-MANIFEST.json'),profile=ref(HERE/'PROFILE.TEMPLATE.SOURCE-ONLY.json'),runner_template=ref(HERE/'run_build_only.template.py'),existing_holder_byte_identical=True,existing_worker_clamps_only=True,new_source_copies=0,origin_generations=0,compiler_or_Docker_or_guard_calls=0,runtime_authority=None))
 print(json.dumps(read(HERE/'SOURCE-BINDING-RESULT.json')))

if __name__=='__main__':main()
