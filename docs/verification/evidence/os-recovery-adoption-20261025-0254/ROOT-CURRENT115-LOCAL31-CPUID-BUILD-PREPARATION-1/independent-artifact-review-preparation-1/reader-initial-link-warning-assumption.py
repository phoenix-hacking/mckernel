"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite existing prlimit/data/folded ABI/warning supplement for actual CURRENT115.
"""
from pathlib import Path
import importlib.util,ast,json,struct,re,collections,hashlib
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('current115_prefix',D/'review_actual115.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
F=E/'m14-f02-local14-final14-qualified-preparation-source-1';FR=F/'independent-actual-qualification-review-1';fa=read(auth(contract['qualified_F02_actual_HOST_and_folded']));host=elf(auth(fa['actual_artifacts']['rust-selected.o']))
HOST_FILE=(str(F/'candidate/kernel/process.c')+'\0').encode();PROD_FILE=b'/src/kernel/process.c\0';HOST_X86_FILE=(str(F/'relative-module-context-correction-source-1/context-root/kernel/rust/x86_cpu_helpers.rs')+'\0').encode();PROD_X86_FILE=b'/src/kernel/rust/x86_cpu_helpers.rs\0'
finite=read(OLD/'independent-artifact-review-1/FINITE-ANONYMOUS-OWNER-INVENTORY.json');finite_sections={r['section']['name'] for r in finite}
t=ast.parse((D/'review_consumers115.py').read_text());exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('literal','relocated_function')],type_ignores=[]),'exact_existing115_function_and_data_RELA_helpers','exec'),globals())
def fn(e,name):
 s=own(e,name);assert s['type']==2 and e.sections[s['shndx']]['flags']&6==6;return s
path=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_selected_edges.py'
t=ast.parse(path.read_text());exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('exact_target_table','special') or isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=='allowed_tails' for z in n.targets)],type_ignores=[]),'retained112_exact_prlimit_table_reader','exec'),globals())
a,ar=special(old,'f03_prlimit_body_result',oldimage);b,br=special(new,'f03_prlimit_body_result',image);assert (a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type'])
shape=lambda rr:[(r['offset'],r['type'],r['kind'],r['target'],r.get('literal_hex'),None if r['kind']=='EXACT_SECTION_STRING' else r['addend']) for r in rr]
assert shape(ar)==shape(br)
aa=bytearray(data(old,a));bb=bytearray(data(new,b))
for r in br:aa[r['offset']:r['offset']+8]=bytes(8);bb[r['offset']:r['offset']+8]=bytes(8)
assert aa==bb
prlimit=dict(name='f03_prlimit_body_result',existing_reader=ref(path),nonrelocated_complete_code_equal114=True,complete_final_code_reproduced=True,actual_targets=br)
data_matches=[]
for row in contract['F02_target31']['internal_debug14']+contract['F02_target31']['configs3']+contract['F02_target31']['readonly14']:
 name=row['name'];a,ab,ar,_=relocated_function(host,name);b,bb,br,rr=relocated_function(new,name,image)
 assert (a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type']) and ab==bb and ar==br,(name,'qualified HOST data fields/targets mismatch')
 data_matches.append(dict(name=name,all_nonpointer_initializer_bytes_equal_qualified_HOST=True,all_pointer_targets_equal_FILE_context_only=True,complete_current_final_bytes_reproduced=True,current_R64=rr))
core=read(auth(contract['accepted114_core']));inherited_data=[]
for row in core['inherited_tables']+core['inherited_scalar_proofs']:
 name=row['name'];a,ab,ar,_=relocated_function(old,name);b,bb,br,rr=relocated_function(new,name,image)
 assert (a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type']) and ab==bb and ar==br and not new.sections[b['shndx']]['flags']&5
 inherited_data.append(dict(name=name,bytes=b['size'],raw_data_and_RELA_equal114=True,full_current_final_bytes_reproduced=True))
warnings=[]
for i in range(4):
 path=P/'OUTPUT/work/evidence'/('%02d.stderr'%i);text=path.read_text();warnings.append(dict(index=i,stream=ref(path),messages=re.findall(r'^warning(?:\[[^\]]+\])?: (.*)',text,re.M)))
assert all(not x['messages'] and x['stream']['bytes']==0 for x in warnings[1:])
oldwarnings=re.findall(r'^warning(?:\[[^\]]+\])?: (.*)',(OLD/'OUTPUT/work/evidence/00.stderr').read_text(),re.M)
warning_added=list((collections.Counter(warnings[0]['messages'])-collections.Counter(oldwarnings)).elements());warning_removed=list((collections.Counter(oldwarnings)-collections.Counter(warnings[0]['messages'])).elements());assert not warning_added
folds=read(auth(fa['folded_proofs']['FINAL-CELL-FOLDED-CONSUMER-SUPPLEMENT.json']));configfolds=read(auth(fa['folded_proofs']['THREE-CONFIG-FOLDED-ABI-ARGUMENTS.json']));tracked=read(auth(fa['folded_proofs']['TRACKED33-FILENAME-LITERAL-EDGES.CORRECTED.json']))
consumer=read(D/'ACTUAL-CURRENT-CONSUMER-READBACK.CORRECTED.json');proven={x['name']:x for x in consumer['selected_function_and_consumer_proofs']};assert {x['name'] for x in consumer['failures']}=={'f03_prlimit_body_result'}
fold_names={r['consumer'] for r in configfolds['proofs']}|{r['consumer'] for r in folds['register_FILE_line_proofs']+folds['stack_FILE_line_proofs']}|{r['name'] for r in folds['disabled_complete_code']}|{folds['schedule_NULL_argument']['consumer'],folds['copy_extra_fields']['consumer'],folds['arch_memclear_None']['consumer']}|{r['name'] for r in tracked}
assert fold_names<=set(proven) and all(proven[n]['reference']=='qualified_F02_selected_HOST' for n in fold_names)
assert len(configfolds['proofs'])==3 and sum(len(r['field_arguments']) for r in configfolds['proofs'])==54 and len(tracked)==33
for r in folds['disabled_complete_code']:
 name=r['name'];assert data(new,own(new,name)).hex()==r['complete_code_hex'] and not rels(new,own(new,name))
fold_transfer=dict(qualified16_predicates=fa['closed_original16_predicates'],qualified_three_config54_fields=fa['folded_proofs']['THREE-CONFIG-FOLDED-ABI-ARGUMENTS.json'],qualified_remaining_predicates=fa['folded_proofs']['FINAL-CELL-FOLDED-CONSUMER-SUPPLEMENT.json'],qualified33_filename_operands=fa['folded_proofs']['TRACKED33-FILENAME-LITERAL-EDGES.CORRECTED.json'],current_31_config_and_cell_fields_exact_HOST=data_matches,all_current_predicate_functions_complete_code_equal_HOST=sorted(fold_names),complete_new_final_code_and_all_positive_R64_proven=ref(D/'ACTUAL-CURRENT-CONSUMER-READBACK.CORRECTED.json'),only_FILE_literal_context_changes=[dict(HOST=HOST_FILE.decode()[:-1],production=PROD_FILE.decode()[:-1]),dict(HOST=HOST_X86_FILE.decode()[:-1],production=PROD_X86_FILE.decode()[:-1])],no_predicate_weakened_or_native_claim=True)
report=dict(scope=__doc__.splitlines()[0],decision='PASS_EXACT_CURRENT115_PRLIMIT_DATA31_INHERITED_DATA_AND_FOLDED16_CURRENT_INSTRUCTIONS',independent=True,reviewer='/root/current110_execution_review',actual_Rust=ref(new.path),actual_image=ref(image.path),prlimit16_table_and_body=prlimit,qualified31_storage_and_pointer_targets=data_matches,inherited_readonly_tables_and_scalars=inherited_data,folded_consumer_transfer=fold_transfer,warnings=warnings,Rust_warning_messages_added=warning_added,Rust_warning_messages_removed=warning_removed,Rust_warning_stream_byte_equal114=(P/'OUTPUT/work/evidence/00.stderr').read_bytes()==(OLD/'OUTPUT/work/evidence/00.stderr').read_bytes(),C_and_link_stderr_empty=True,actual_native_acceptance=False,wholefile_acceptance=False)
if __name__=='__main__':print(json.dumps(dict(proof=save('ACTUAL-PRLIMIT-DATA-FOLDED-WARNING-SUPPLEMENT.json',report),decision=report['decision'],data31=len(data_matches),inherited_data=len(inherited_data),folded_current_functions=len(fold_names),warnings_removed=warning_removed)))
