"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite accepted-reader supplements for actual116 legitimate changed callsites.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base116',D/'review_actual116.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);globals().update({k:v for k,v in vars(m).items() if not k.startswith('__')})
def extract_current(path,names):
 nodes=[n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in names for x in n.targets)]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':FINITE_CURRENT_READERS','exec'),globals())
extract_current(auth(accepted['reader_sources']['review_consumers115.py']),{'literal','relocated_function'})
host=None;HOST_FILE=b'';PROD_FILE=b'';HOST_X86_FILE=b'';PROD_X86_FILE=b'';finite_sections={'.lrodata.'+n for n in ['process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge']}
def fn(e,n):return own(e,n)
p=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_selected_edges.py';extract_current(p,{'exact_target_table','special','allowed_tails'})
a,ar=special(old,'f03_prlimit_body_result',oldimage);b,br=special(new,'f03_prlimit_body_result',image)
shape=lambda rr:[(r['offset'],r['type'],r['kind'],r['target'],r.get('literal_hex'),None if r['kind']=='EXACT_SECTION_STRING' else r['addend']) for r in rr]
assert (a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type']) and shape(ar)==shape(br)
aa=bytearray(data(old,a));bb=bytearray(data(new,b))
for r in br:aa[r['offset']:r['offset']+8]=bytes(8);bb[r['offset']:r['offset']+8]=bytes(8)
assert aa==bb
prlimit=dict(existing_reader=ref(p),full_current_final_bytes_reproduced=True,normalized_code_and_table_equal115=True,actual_targets=br)
logger='arch_process_vm_rw_log_bridge';img=image
logger_reader=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_inherited_core_current112.py'
logger_text=logger_reader.read_text();logger_segment='q=E/'+logger_text.split('q=E/',1)[1].split('\nmetadata=[]',1)[0]
exec(compile(logger_segment,str(logger_reader)+':EXACT_FOUR_RECORD_LOGGER','exec'),globals())
extract_current(auth(accepted['reader_sources']['review_consumers115.py']),{'literal'})

q=read(E/'m14-f03-setsiginfo-syscall-event-report-signal-host-preparation-source-1/actual-new-rust-folded-caller-proof-source-1/ACTUAL-FOLDED-CALLER-PROOF.json');qualified=elf(auth(q['artifacts']['rust-selected.o']))
qualified_proofs=[];deltas=[]
for name in q['selected_functions']:
 try:
  a,ab,ar,_=relocated_function(qualified,name);b,bb,br,rr=relocated_function(new,name,image)
  assert (a['size'],a['type'],a['bind'])==(b['size'],b['type'],b['bind']),(name,'shape',a['size'],b['size'])
  assert ab==bb,(name,'instructions');assert ar==br,(name,'targets')
  qualified_proofs.append(dict(name=name,reference=q['artifacts']['rust-selected.o'],input=b,final=image.sym(name),nonrelocated_and_target_bytes_equal_qualified_HOST=True,full_actual_final_bytes_reproduced=True))
 except Exception as error:deltas.append(dict(name=name,error=repr(error)))
report=dict(scope=__doc__.splitlines()[0],actual_Rust=ref(new.path),actual_image=ref(image.path),prlimit=prlimit,logger=dict(name=logger,bytes=337,full_current_final_bytes_reproduced=True,code_and_targets_equal115=True),qualified_new_folded_proofs=qualified_proofs,qualified_new_folded_deltas=deltas,runtime_authority=None)
p=D/'ACTUAL-FINITE-SUPPLEMENT.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':ref(p),'qualified_pass':[x['name'] for x in qualified_proofs],'deltas':deltas}))
