"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Source-only adaptation; no execution."""
from pathlib import Path
import ast,hashlib,json,shlex
R=Path(__file__).resolve().parent;old=R.parent/'production-consumer-preparation-1/actual-production-1/run_production_once.py'
s=old.read_text()
def change(a,b):
 global s
 if s.count(a)!=1:raise ValueError(('single source pattern required',a,s.count(a)))
 s=s.replace(a,b)
ready=R/'EXECUTABLE-READY.NOT-GRANTED.json';readysha=hashlib.sha256(ready.read_bytes()).hexdigest();p=json.loads(ready.read_bytes())
change('P=Path(__file__).resolve().parent.parent;A=Path(__file__).resolve().parent',"P=Path(__file__).resolve().parent;A=P/'actual-correction-1';A.mkdir(mode=0o700)\nimport importlib.util\n_spec=importlib.util.spec_from_file_location('allocated_memmove_oracle',P/'allocated_memmove_oracle.py');memmove_oracle=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(memmove_oracle)")
change("ready=P/'PRODUCTION-CONSUMER-READY.NOT-GRANTED.json';need(sha(ready)=='88de5ff6c6bfd635371bbeb6466e2b77da52ccacb03a1a1beaeecf5d627ac0c3','frozenready88de')",f"ready=P/'EXECUTABLE-READY.NOT-GRANTED.json';need(sha(ready)=='{readysha}','frozen bounded correction ready')")
change("'373c8db4f70cd176b5abeb444e645aec7d5005668e1b031a4d96144e55add78a'",repr(p['source_identity']))
change("compiler=Path(plan['commands'][0]['argv'][6])","compiler=Path(plan['commands'][5]['argv'][6])")
change("len(plan['commands'][0]['argv'])==48 and plan['commands'][0]['argv'][plan['commands'][0]['argv'].index('--crate-name')+1]", "len(plan['commands'][5]['argv'])==48 and plan['commands'][5]['argv'][plan['commands'][5]['argv'].index('--crate-name')+1]")
change("reused=[plan['actual_reused_complete_GCC9_CPU_object_NOT_rehashed'],plan['actual_reused_real_header_ABI_object_NOT_rehashed']]", "reused=[plan['actual_reused_complete_GCC9_CPU_object_NOT_rehashed'],plan['actual_reused_real_header_ABI_object_NOT_rehashed']]+plan['retained_leaf_C_objects_not_rehashed']+[plan['genuine_check_signal_provider']['object_NOT_rehashed']]\n for row in plan['correction_inputs'].values():need(sha(row['path'])==row['sha256'],'bounded source correction input '+row['path'])\n provider=plan['genuine_check_signal_provider']\n for key in ['authority','actual_C_source','canonical_current_C_source','actual_root_union_partial_NM']:need(sha(provider[key]['path'])==provider[key]['sha256'],'genuine provider authority '+key)\n need(provider['actual_C_source']['sha256']==provider['canonical_current_C_source']['sha256'],'actual provider matches current canonical syscall source')\n old_provider_rows=rows(Path(provider['actual_root_union_partial_NM']['path']).read_text());unique(old_provider_rows,'check_signal',{'T'})\n need(not any(r[-1]=='check_signal' and r[-2]=='U' for r in old_provider_rows),'actual root provider not unresolved')")
change("O=Path(plan['fresh_output_directory']);need(not os.path.lexists(O),'fresh production output');O.mkdir(mode=0o700)","O=Path(plan['fresh_output_directory']);L=Path(plan['fresh_leaf_output_directory'])\n for output in [O,L]:\n  need(not os.path.lexists(output),'fresh changed-source output '+str(output));output.mkdir(mode=0o700)")
change("  if i==0:\n   prefix=", "  if i==5:\n   prefix=")
change("  if i==4:\n   row=", "  if i==9:\n   row=")
change("  if i==1:\n   rr=", "  if i==6:\n   rr=")
change("  if i==5:\n   rr=", "  if i==10:\n   rr=")
change("   write(A/'DURABLE-mckernel_rust.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})", "   write(A/'DURABLE-mckernel_rust.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})\n   allocated=memmove_oracle.observe(O/'mckernel_rust.o')\n   write(A/'ACTUAL-ALLOCATED-MEMMOVE-ABSENCE.json',{'object':row,'oracle_source':plan['allocated_memmove_oracle'],'observation':allocated})")
change("  if i==9:\n", "  if i==0:\n   prefix='--emit=obj=';emitted=[x[len(prefix):] for x in item['argv'] if x.startswith(prefix)]\n   need(emitted==[str(L/'actual_bodies.o')],'exact corrected leaf object')\n   row=ns['hashed'](L/'actual_bodies.o',32<<20);objects['actual_bodies.o']=row\n   write(A/'DURABLE-actual_bodies.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})\n  if i==1:\n   row=ns['hashed'](L/'fixture',32<<20);objects['fixture']=row\n   write(A/'DURABLE-fixture.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})\n  if i==2:\n   need((cap/'stdout').read_text().splitlines()==plan['changed_source_leaf_expected_stdout'],'strict actual8000 counts and NOTEXECUTED qualifiers')\n   need((cap/'stderr').stat().st_size==0,'controlled fixture empty stderr')\n  if i==3:\n   rr=rows((cap/'stdout').read_text())\n   for n in ['__print_stack','mod_nmi_ctx','interrupt_exit']:unique(rr,n,{'T'})\n   need(not any(r[-1]=='memmove' and r[-2]=='U' for r in rr),'leaf no memmove U')\n  if i==9:\n")
change("   data=unique(rr,'no_turbo',{'D'});need(int(data[-3],16)==4,'no_turboD4')", "   data=unique(rr,'no_turbo',{'D'});need(int(data[-3],16)==4,'no_turboD4')\n   need(not any(r[-1] in ['check_signal','memmove'] and r[-2]=='U' for r in rr),'genuine check_signal resolved; no memmove provider')")
change("'PASS_CURRENT78_3068T572U_RETAINED_COMPLETE_GCC9_CPU_REAL_ABI_PARTIAL_ONLY' if failure is None and len(records)==7", "'PASS_CHANGED_SOURCE8000_CURRENT78_3068T572U_NO_ALLOCATED_MEMMOVE_GENUINE_CHECK_SIGNAL_PARTIAL_ONLY' if failure is None and len(records)==12")
change("'new_commands':len(records),", "'new_commands':len(records),'planned_commands':12,'leaf_commands':5,'production_commands':7,'strict8000_expected':plan['expected_unchanged_8000_counts'] if 'plan' in globals() else None,")
# Source grammar check only: do not import or execute the driver/oracle.
ast.parse(s)
(R/'run_correction_once.py').write_text(s)
profile=p['profile']
argv=['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--stack=2097152:2097152','/usr/bin/env','RUST_MIN_STACK=2097152','/home/holden/anaconda3/bin/python3','-I','-B',str(R/'run_correction_once.py')]
def ref(path):
 b=path.read_bytes();return {'path':str(path),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
sealed={'scope':__doc__.split(' Source-only')[0],'status':'SOURCE_READY_AWAITING_FRESH_ROOT_CPU6_GRANT_NOT_EXECUTED','ready':ref(ready),'driver':ref(R/'run_correction_once.py'),'source_correction':ref(R/'SOURCE-CORRECTION-IDENTITY.json'),'recipe':ref(R/'EXACT-CURRENT78-PRODUCTION-RUST.NOT-EXECUTED.json'),'command_count':12,'leaf_commands':5,'production_commands':7,'argv':argv,'cwd':str(R),'shell_display_only':shlex.join(argv),'profile':profile,'actual_result':None,'CPU_reserved':False,'source_grammar_only_parsed':True,'object_read_or_hash':False}
with (R/'SEALED-EXECUTABLE-READY.NOT-GRANTED.json').open('x') as f:json.dump(sealed,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'sealed':ref(R/'SEALED-EXECUTABLE-READY.NOT-GRANTED.json'),'driver':sealed['driver'],'commands':12}))
