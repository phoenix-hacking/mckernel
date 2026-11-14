"""Create new-only downstream source/templates. No execution authority."""
import ast,copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/m07-sigill-successor-native-data-preparation-20261022-1/actual-terminal-preparation-1/bound-terminal-source-correction-1')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def ref(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=digest(raw),bytes=len(raw))
def create(name,raw):
 with (HERE/name).open('xb') as out:out.write(raw if isinstance(raw,bytes) else raw.encode())
def store(name,value):create(name,json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 frozen={str(p):ref(p) for p in HERE.iterdir() if p.is_file()}
 summary=ref(HERE/'readback_observer.py');observer=ref(HERE/'observe_current_pass_image_retirement.py')
 oldsummary='0ef626b8a8199929da016d6cadd71e98311e9937f7862f22de2f1bd1c0f4028f'
 oldout=str(OLD/'root-observation-m07-sigill-pass-image-observation-1')
 newout=str(HERE/'root-observation-m07-sigill-pass-image-observation-postjoin-correction-1')
 for name in ('read_original_five_metadata.py','export_raw_five.py'):
  text=(OLD/name).read_text().replace(oldsummary,summary['sha256']).replace(oldout,newout)
  compile(text,str(HERE/name),'exec');create(name,text)
 chain=json.loads((OLD/'EXECUTOR-SIX-OPERATIONS.json').read_bytes())
 late=[];operations={}
 for op in chain['ordered_operations']+[dict(chain['pre_cleanup_readonly_preflight'],role='readonly-preflight')]:
  role=op['role'];op=copy.deepcopy(op)
  # Rebind only corrected source/helper and future output/data paths. Retain engine/preflight sources exactly.
  for i,arg in enumerate(op['argv']):
   if arg.startswith(str(OLD)):
    name=Path(arg).name
    if name not in ('cleanup_pass_image.py','check_actual_fresh_preflight.py'):op['argv'][i]=arg.replace(str(OLD),str(HERE),1)
   if arg.startswith('BIND_'):
    op['argv'][i]=None;late.append(dict(role=role,argv_index=i,required=arg))
  op['capture_directory']=str(HERE/('cohort-actual-'+role+'-capture-1'))
  assert not Path(op['capture_directory']).exists(),'occupied capture output'
  op['execution_authorized']=False;op['status']='PENDING_EXACT_RELEASE_AND_LATE_BINDINGS'
  operations[role]=op;store('COHORT-OPERATION-'+role+'.PENDING.json',op)
 chain['ordered_operations']=[operations[o['role']] for o in chain['ordered_operations']]
 chain['pre_cleanup_readonly_preflight']=operations['readonly-preflight']
 chain['cleanup_exactbyte_stdout_copy']=str(HERE/'actual-cleanup-result.json')
 assert not Path(chain['cleanup_exactbyte_stdout_copy']).exists(),'occupied cleanup-result output'
 chain['observer_request_draft']=ref(HERE/'OBSERVER-REQUEST-DRAFT.json')
 chain['late_fields']={k:None for k in chain['late_fields']};chain['ordinary_result']=None;chain['source_freeze']=None
 chain['late_argv_bindings']=late;chain['execution_authorized']=False
 # Exact old capture helpers/engine/preflight source are references, never copied/rebased.
 sources={name:ref(HERE/name) for name in ('observe_current_pass_image_retirement.py','PASS-CASE-STATIC.json','readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py','OBSERVER-REQUEST-DRAFT.json')}
 reused={name:ref(OLD/name) for name in ('capture_first_four.py','capture_critical_two.py','cleanup_pass_image.py','check_actual_fresh_preflight.py')}
 assert reused['capture_first_four.py']==chain['capture_callers']['first_four']
 assert reused['capture_critical_two.py']==chain['capture_callers']['critical_two']
 sources['cleanup_selftests']=ref(Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py'))
 tree=ast.parse((OLD/'cleanup_pass_image.py').read_bytes());constants={}
 for n in tree.body:
  if isinstance(n,ast.Assign):
   for target in n.targets:
    if isinstance(target,ast.Name) and target.id in ('PUBLISHED_SCRIPT','PUBLISHED_TESTS'):
     constants[target.id]=ast.literal_eval(n.value)
 chain['source_refs']=sources;chain['reused_immutable_sources']=reused
 store('COHORT-EXECUTOR-SIX-OPERATIONS.PENDING.json',chain)
 store('COHORT-SOURCE-CAPTURE-MAP.json',dict(status='FROZEN_SOURCE_AND_PENDING_OPERATIONS_ONLY_NO_RELEASE',sources=sources,reused_immutable_sources=reused,operations={role:ref(HERE/('COHORT-OPERATION-'+role+'.PENDING.json')) for role in operations},capture_outputs={role:op['capture_directory'] for role,op in operations.items()},late_argv_bindings=late,published_cleanup_aliases=constants,git_commit=None,git_tree=None,fetched_blob_proof=None,physical_clearance=False,execution_authorized=False,preexisting_file_freeze=frozen))
 # Check entire source dependency cohort, including true corrected HERE resolution and source hashes.
 for name in ('read_original_five_metadata.py','export_raw_five.py'):
  ns={'__file__':str(HERE/name),'__name__':'cohort_source_predicate'}
  exec(compile((HERE/name).read_bytes(),str(HERE/name),'exec'),ns)
  assert ns['SUMMARY']==HERE/'readback_observer.py' and ns['SUMMARY_SHA']==summary['sha256']
  if name=='export_raw_five.py':assert str(ns['OUTPUT'])==newout and ns['COMMAND'][-5:]==list(ns['NAMES'])
 for op in operations.values():
  for arg in op['argv']:
   if isinstance(arg,str) and arg.endswith('.py'):
    assert Path(arg).is_file(),arg
 assert all(ref(Path(path))==value for path,value in frozen.items()),'reviewed bytes changed'
 assert all(v is None for v in chain['late_fields'].values())
 store('COHORT-SOURCE-PREDICATE-RESULT.json',dict(status='PASS_NEW_COHORT_LINKS_AND_FROZEN_PREEXISTING_BYTES_ONLY',copied_helpers=2,operation_templates=len(operations),late_argv_bindings=len(late),future_fields_null=True,occupied_outputs_rejected=True,reviewed_existing_bytes_unchanged=True,helper_main_executed=False,root_actions=False,execution_authorized=False))
 print('PASS_NEW_COHORT_SOURCE_PREDICATES_ONLY')
if __name__=='__main__':main()
