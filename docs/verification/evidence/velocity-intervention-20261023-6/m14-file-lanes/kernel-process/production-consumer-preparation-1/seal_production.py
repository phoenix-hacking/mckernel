"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only adaptation of accepted7a runner, no job or CPU reservation.
"""
from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent;B=P.parent
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
 runner=(OLD/'run_corrected_production_once.py').read_text()
 runner=runner.replace('One frozen current78/wholeGCC9 process consumer14 job, root CPU6 grant.','One dump current78/wholeGCC9 process consumer14 job; explicit new root grant required.')
 runner=runner.replace("P=Path(__file__).resolve().parent;B=P.parent;", "P=Path(__file__).resolve().parent;B=P.parent;")
 runner=runner.replace('EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json','EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').replace('EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json','EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').replace('EXECUTABLE-READY.CORRECTED-NOT-GRANTED.json','EXECUTABLE-READY.NOT-GRANTED.json')
 start=runner.index(" assert pin(READY)['sha256']==");end=runner.index(" for row in r['source_inputs'].values():",start)
 runner=runner[:start]+''' grant=json.loads((P/'ROOT-GRANT.json').read_text());assert grant['scope']==SCOPE and grant['CPU']==6 and grant['ready_sha256']==pin(READY)['sha256'] and grant['ordinary_jobs']==1 and grant['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 ready=json.loads(READY.read_text());assert pin(RF)==ready['Rust_recipe'] and pin(CF)==ready['C_recipe'] and pin(Path(__file__))==ready['driver']
 r=json.loads(RF.read_text());c=json.loads(CF.read_text());assert len(r['source_inputs'])==78 and len(c['commands'])==14
 assert r['source_identity']=='1003f481cae91c012256264ea0c4eb960cbaaf66ea1e1616e2bed3b0e7bf177d'
 for row in ready['evidence_bindings']:assert pin(Path(row['path']))==row,row['path']
''' +runner[end:]
 runner=runner.replace("Root explicit sole bounded corrected b516/b6b45/b819 production grant: pinnednightly1.95-2026-02-18 compiler70eb48argv unchanged; first E0428 failure preserved2fb3/e9a, no third attempt.","Root explicit frozen dump current78 production grant; pinnednightly1.95-2026-02-18 compiler70eb48argv unchanged; prior corrected E0428 family retained2fb3/e9a/7a, no family reset.")
 pos=runner.index(" helper=Path(")
 census=''' competitors=[];races=[]
 for process in Path('/proc').iterdir():
  if not process.name.isdigit() or int(process.name)==os.getpid():continue
  try:
   if process.stat().st_uid==1000 and os.sched_getaffinity(int(process.name))=={6}:competitors.append(dict(pid=int(process.name),cmdline=(process/'cmdline').read_bytes().replace(b'\\0',b' ').decode(errors='replace')))
  except (FileNotFoundError,ProcessLookupError):races.append(int(process.name))
 write(P/'CPU6-ADMISSION-NO-EXCLUSIVE-COMPETITOR.json',dict(scope=SCOPE,competitors=competitors,transient_procfs_races=races,no_exclusive_competing_job=not competitors));assert not competitors,competitors
'''
 runner=runner[:pos]+census+runner[pos:]
 runner=runner.replace("Root explicit SOLE bounded corrected CPU6 b516 current78 production job, 70eb48argv; rootphysical CPU7 reserved, no competing jobs or third attempt","Root explicit sole dump CPU6 current78 production grant bound by ROOT-GRANT.json; 70eb48argv; no competing ordinary CPU6 job or automatic retry")
 runner=runner.replace("log='vm_range_insert_log_bridge';selector='process_vm_range_insert_debug';", "log='vm_range_insert_log_bridge';selector='process_vm_range_insert_debug';entry='vm_range_insert_dump_bridge';gate='process_dump_tree_enabled';")
 runner=runner.replace("observed_delta={};rust_callback_relocs=[]", "observed_delta={};rust_callback_relocs=[];dump_relocs=[];caller_witnesses=[];gate_metadata={}")
 runner=runner.replace("for symbol in (log,'vm_range_insert','kprintf','virt_to_phys'):","for symbol in (log,entry,'vm_range_insert','kprintf','virt_to_phys','clear_range_l3','x86_cpu_ulong_log_bridge'):")
 runner=runner.replace("   unique(rows,selector,{'U'})", "   unique(rows,selector,{'U'});unique(rows,gate,{'U'})")
 runner=runner.replace("   rows=nmrows(text);found=[row for row in rows if row[-1]==log];assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0,found", "   rows=nmrows(text)\n   for symbol in (log,entry):\n    found=[row for row in rows if row[-1]==symbol];assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0,found")
 start=runner.index("   rustelf=Elf(O/'mckernel_rust.o');");end=runner.index("  elif name=='05-selected-complete-process-preprocess':",start)
 runner=runner[:start]+'''   rustelf=Elf(O/'mckernel_rust.o');_,rust_callback_relocs=rustelf.function_bytes_and_relocations(log);_,dump_relocs=rustelf.function_bytes_and_relocations(entry)
   assert {'kprintf',selector}<={row['symbol'] for row in rust_callback_relocs},rust_callback_relocs
   assert {'kprintf',gate}<={row['symbol'] for row in dump_relocs},dump_relocs
''' +runner[end:]
 pos=runner.index("   match=re.search(r'process_vm_range_insert_debug")
 runner=runner[:pos]+'''   assert not re.search(r'\\bvoid\\s+(?:vm_range_insert_dump_bridge|dump_tree|dtree)\\s*\\([^;{}]*\\)\\s*\\{',text)
   assert re.search(r'const\\s+int\\s+process_dump_tree_enabled\\s*=\\s*0\\s*;',text)
''' +runner[pos:]
 runner=runner.replace("   rows=nmrows(text);assert not [row for row in rows if row[-1]==log];unique(rows,'vm_range_insert',{'U'});unique(rows,'vm_range_insert_dump_bridge',{'T'});value=unique(rows,selector,{'D'});assert int(value[-3],16)==32", "   rows=nmrows(text);assert not [row for row in rows if row[-1] in {log,entry,'dtree','dump_tree'}];unique(rows,'vm_range_insert',{'U'});g=unique(rows,gate,{'R'});assert int(g[-3],16)==4;value=unique(rows,selector,{'D'});assert int(value[-3],16)==32")
 pos=runner.index("   celf=Elf(O/'process.c.o');")
 runner=runner[:pos]+'''   celf=Elf(O/'process.c.o')
   gates=[row for row in celf.symbols if row['name']==gate];assert len(gates)==1;g=gates[0];assert g['bind']==1 and g['type']==1 and g['size']==4 and 0<g['section']<len(celf.sections)
   gsec=celf.sections[g['section']];assert not (gsec['flags']&1) and not (gsec['flags']&4);graw=celf.data(gsec)[g['value']:g['value']+4];assert graw==b'\\0'*4
   gate_metadata=dict(symbol=g,section=gsec['name'],readonly=True,bytes=graw.hex(),value=0)
''' +runner[pos:]
 runner=runner.replace("   celf=Elf(O/'process.c.o');matches=", "   matches=")
 runner=runner.replace("for symbol in (log,'vm_range_insert','kprintf','vm_range_insert_dump_bridge'):","for symbol in (log,entry,'vm_range_insert','kprintf'):")
 needle="   unique(rows,selector,{'D'})\n for row in durable.values():"
 replacement="""   unique(rows,selector,{'D'});g=unique(rows,gate,{'R'});assert int(g[-3],16)==4
  elif name=='13-process-fullRust-partial-relocations':
   partial=Elf(O/'process-rust-partial.o');celf=Elf(O/'process.c.o');partial.defined_function(entry)
   for caller in ('process_add_range_insert_bridge','process_split_range_insert_bridge'):
    before,brefs=celf.function_bytes_and_relocations(caller);after,arefs=partial.function_bytes_and_relocations(caller)
    assert before==after and brefs==arefs and len(arefs)==1 and arefs[0]['symbol']=='vm_range_insert',(caller,brefs,arefs)
    caller_witnesses.append(dict(name=caller,sha256=hashlib.sha256(after).hexdigest(),bytes=len(after),actual_relocations=arefs))
   assert len([ref for ref in partial.relocations if ref['symbol']=='vm_range_insert'])==2
   _,actual_dump_refs=partial.function_bytes_and_relocations(entry);assert dump_relocs==actual_dump_refs
   assert {'kprintf',gate}<={row['symbol'] for row in actual_dump_refs}
 for row in durable.values():"""
 assert needle in runner;runner=runner.replace(needle,replacement)
 start=runner.index(" result=dict(scope=SCOPE,status=");end=runner.index(" write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'",start)
 runner=runner[:start]+''' result=dict(scope=SCOPE,status='PASS_F02_DUMP_CURRENT78_COMPLETE_GCC9_PROCESS_REAL_ABI_CALLER_RELOCS_FULLRUST_PARTIAL',ready=pin(READY),Rust_recipe=pin(RF),C_recipe=pin(CF),grant=pin(P/'ROOT-GRANT.json'),records=records,objects=durable,source_count=78,source_identity=r['source_identity'],headers=73,actual_commands=14,actual_T_U_delta=observed_delta,debug_metadata=pin(P/'ACTUAL-DEBUG-METADATA-ABI.json'),Rust_log_relocations=rust_callback_relocs,Rust_dump_relocations=dump_relocs,actual_unchanged_C_callers=caller_witnesses,readonly_dump_gate=gate_metadata,selected_C_dump_compute_absent=True,Rust_dump_unique=True,kprintf_existing_Rust_provider=True,actual433and20commands_reused=ready['accepted_actual433_leaf'],failure_history=r['failure_history'],retained_C_debt=['Readonly original dump gate metadata','Other process.c compute bodies'],seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_default_GCC14_image_link=False,native=False,file_retired=False)
''' +runner[end:]
 runner=runner.replace("PRODUCTION-BOUNDED-CORRECTION-FAILURE-1.json","PRODUCTION-FIRST-FAILURE-1.json").replace("STOP_EXPERT_ESCALATION_NO_THIRD_ATTEMPT","STOP_FIRST_UNEXPECTED_RESULT_PRESERVE_HISTORY_NO_AUTOMATIC_RETRY")
 ast.parse(runner)
 driver=P/'run_production_once.py';driver.write_text(runner)
 rf=P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json';cf=P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json';r=json.loads(rf.read_text());c=json.loads(cf.read_text())
 evidence=[pin(B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),pin(P/'COHERENT-CURRENT78-AND-REUSED-LEAF.json'),pin(P/'PRESEAL-ABI-SOURCE-ORDER-CORRECTION.json')]
 ready=dict(scope=SCOPE,status='EXECUTABLE_READY_F02_DUMP_PRODUCTION_NO_GRANT_OR_JOB',Rust_recipe=pin(rf),C_recipe=pin(cf),driver=pin(driver),preparer=pin(P/'prepare_production.py'),sealer=pin(Path(__file__)),evidence_bindings=evidence,accepted_actual433_leaf=evidence[0],source_count=78,headers=73,source_identity=r['source_identity'],profile=r['profile'],compiler=pin(Path(r['argv'][6])),prepared_commands=len(c['commands']),argv_count=len(r['argv']),cfg_count=4,CGU=1,current_canonical_refresh=r['canonical_refresh'],only_private_override='kernel/rust/process_helpers.rs dump70015',private_C=c['private_source'],private_Rust=r['source_inputs']['kernel/rust/process_helpers.rs']['private'],expected_T_delta=r['expected_T_delta'],expected_U_delta=r['expected_U_delta'],historical_failures=r['failure_history'],requires='New explicit exact root CPU6 grant materialized ROOT-GRANT.json, fresh local admission and positive per-command whole joins. No compiler/test run by preparation.',compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,leaf_replayed=False,whole_file_default_image_native_credit=False)
 write(P/'EXECUTABLE-READY.NOT-GRANTED.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'EXECUTABLE-READY.NOT-GRANTED.json'),Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],driver=ready['driver'],source_identity=r['source_identity'],commands=14,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
