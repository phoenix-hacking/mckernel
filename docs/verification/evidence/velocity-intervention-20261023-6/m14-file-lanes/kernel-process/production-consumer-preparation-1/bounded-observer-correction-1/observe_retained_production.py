"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-adopted sole retained-only observer correction. No compiler/link/tool replay.
"""
from pathlib import Path
import ast,hashlib,json,os,stat,struct,re
P=Path(__file__).resolve().parent;B=P.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def metadata(path):
 st=path.stat();return dict(path=str(path),device=st.st_dev,inode=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns,mode=oct(stat.S_IMODE(st.st_mode)),uid=st.st_uid,gid=st.st_gid,nlink=st.st_nlink)
def stable(row):
 actual=metadata(Path(row['path']));assert all(actual[key]==value for key,value in row.items() if key!='sha256'),(actual,row)
def rows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(symbols,name,kinds):
 found=[row for row in symbols if row[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,found);return found[0]
def main():
 bindings=json.loads((P/'INPUT-BINDINGS.json').read_text());assert bindings['scope']==SCOPE
 for row in bindings['small_pins']:assert pin(Path(row['path']))==row,row['path']
 for row in bindings['durable_metadata']:stable(row)
 r=json.loads((B/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text());c=json.loads((B/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text());failure=json.loads((B/'PRODUCTION-FIRST-FAILURE-1.json').read_text())
 assert len(failure['records'])==14 and failure['CPU6_released']
 capture={}
 for record,command in zip(failure['records'],c['commands']):
  assert record['name']==command['name'];j=record['join']
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['timed_out'] and j['error'] is None and j['retirement_error'] is None and j['remaining_group_members']==[] and j['unexpected_group_members']==[]
  cmd=json.loads(Path(record['command']['path']).read_text());assert cmd['scope']==SCOPE and cmd['argv']==command['argv'] and cmd['cwd']==command['cwd']
  assert json.loads((Path(record['command']['path']).parent/'whole-join.json').read_text())==j
  capture[record['name']]=j['captures']
 assert r['source_identity']=='1003f481cae91c012256264ea0c4eb960cbaaf66ea1e1616e2bed3b0e7bf177d' and len(r['source_inputs'])==78 and len(c['headers'])==73
 assert len(r['argv'])==48 and r['argv']==c['commands'][0]['argv'] and r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 for row in [c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['headers'].values(),*c['canonical_headers'].values()]:assert pin(Path(row['path']))==row
 prior=rows(Path(r['accepted_prior_Rust_symbols']['path']).read_text());new=rows(Path(capture['01-current78-Rust-symbols']['stdout']['path']).read_text());delta={}
 for kind in ('T','U'):
  before={row[-1] for row in prior if row[-2]==kind};after={row[-1] for row in new if row[-2]==kind}
  actual=dict(removed=sorted(before-after),added=sorted(after-before),before=len(before),after=len(after));assert actual==r['expected_'+kind+'_delta'];delta[kind]=actual
 log='vm_range_insert_log_bridge';entry='vm_range_insert_dump_bridge';gate='process_dump_tree_enabled';selector='process_vm_range_insert_debug'
 for symbol in (log,entry,'vm_range_insert','kprintf','virt_to_phys','clear_range_l3','x86_cpu_ulong_log_bridge'):unique(new,symbol,{'T'})
 for symbol in (gate,selector):unique(new,symbol,{'U'})
 elfsource=Path(bindings['ELF_source']['path']);eraw=elfsource.read_bytes();assert pin(elfsource)==bindings['ELF_source']
 nodes=[n for n in ast.parse(eraw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in {'need','textz'} or isinstance(n,ast.ClassDef) and n.name=='Elf'];ns={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(elfsource),'exec'),ns);Elf=ns['Elf']
 objects=failure['durable_objects'];rust=Elf(Path(objects['Rust']['path']));_,logrefs=rust.function_bytes_and_relocations(log);dumpbytes,dumprefs=rust.function_bytes_and_relocations(entry)
 assert {'kprintf',selector}<={ref['symbol'] for ref in logrefs};assert {'kprintf',gate}<={ref['symbol'] for ref in dumprefs};del rust
 preprocess=Path(capture['05-selected-complete-process-preprocess']['stdout']['path']).read_text()
 assert not re.search(r'\bvoid\s+(?:vm_range_insert_log_bridge|vm_range_insert_dump_bridge|dump_tree|dtree)\s*\([^;{}]*\)\s*\{',preprocess)
 assert re.search(r'const\s+int\s+process_dump_tree_enabled\s*=\s*0\s*;',preprocess)
 match=re.search(r'process_vm_range_insert_debug\s*=\s*\{([^}]+)\}',preprocess,re.S);assert match;initializer=match.group(1)
 assert int(re.search(r'\.line\s*=\s*(\d+)',initializer).group(1))==2086 and int(re.search(r'\.flags\s*=\s*(0x[0-9a-fA-F]+|\d+)',initializer).group(1),0)==0
 assert '"vm_range_insert_log_bridge"' in initializer and c['private_source']['path'] in initializer
 csyms=rows(Path(capture['07-selected-process-symbols']['stdout']['path']).read_text());assert not [row for row in csyms if row[-1] in {log,entry,'dtree','dump_tree'}]
 unique(csyms,'vm_range_insert',{'U'});assert int(unique(csyms,gate,{'R'})[-3],16)==4;assert int(unique(csyms,selector,{'D'})[-3],16)==32
 original=Elf(Path(objects['C']['path']));gate_rows=[s for s in original.symbols if s['name']==gate];assert len(gate_rows)==1;g=gate_rows[0]
 assert g['bind']==1 and g['type']==1 and g['size']==4 and 0<g['section']<len(original.sections);gsec=original.sections[g['section']];assert not(gsec['flags']&5)
 assert original.data(gsec)[g['value']:g['value']+4]==b'\0'*4
 debug_rows=[s for s in original.symbols if s['name']==selector];assert len(debug_rows)==1;d=debug_rows[0]
 assert d['bind']==1 and d['type']==1 and d['size']==32 and 0<d['section']<len(original.sections);dsec=original.sections[d['section']];assert dsec['name']=='__verbose';draw=original.data(dsec)[d['value']:d['value']+32]
 assert len(draw)==32 and struct.unpack_from('<I',draw,24)[0]==2086 and draw[16:24]==b'\0'*8
 drefs=[ref for ref in original.relocations if ref['section']==dsec['name'] and d['value']<=ref['offset']<d['value']+32];assert {ref['offset']-d['value'] for ref in drefs}=={0,8}
 psymbols=rows(Path(capture['12-process-fullRust-partial-symbols']['stdout']['path']).read_text())
 for symbol in (log,entry,'vm_range_insert','kprintf'):unique(psymbols,symbol,{'T'})
 unique(psymbols,selector,{'D'});assert int(unique(psymbols,gate,{'R'})[-3],16)==4
 partial=Elf(Path(objects['partial']['path']));partial.defined_function(entry);callers=[]
 for caller in ('process_add_range_insert_bridge','process_split_range_insert_bridge'):
  before,brefs=original.function_bytes_and_relocations(caller);after,arefs=partial.function_bytes_and_relocations(caller)
  assert before==after and brefs==arefs,(caller,brefs,arefs)
  target_refs=[ref for ref in arefs if ref['symbol']=='vm_range_insert'];assert len(target_refs)==1,(caller,target_refs,arefs)
  callers.append(dict(name=caller,bytes=len(after),sha256=hashlib.sha256(after).hexdigest(),actual_relocations=arefs,actual_vm_range_insert_relocations=target_refs))
 assert len([ref for ref in partial.relocations if ref['symbol']=='vm_range_insert'])==2
 actual_dump_bytes,actual_dump_refs=partial.function_bytes_and_relocations(entry);assert dumpbytes==actual_dump_bytes and dumprefs==actual_dump_refs
 assert {'kprintf',gate}<={ref['symbol'] for ref in actual_dump_refs}
 for row in bindings['durable_metadata']:stable(row)
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 result=dict(scope=SCOPE,status='PASS_SOLE_OBSERVER_CORRECTION_F02_DUMP_CURRENT78_WHOLE_GCC9_REAL_ABI_RETAINED_CALLERS_FULLRUST_PARTIAL',first_failure_preserved=bindings['first_failure'],observer_source=pin(Path(__file__)),bindings=pin(P/'INPUT-BINDINGS.json'),actual14command_whole_joins_preserved=True,original_command_seconds=sum(record['join']['seconds'] for record in failure['records']),compiled_objects_not_rehashed=objects,actual_T_U_delta=delta,actual_unchanged_C_callers=callers,full_GOT_relocations_retained_in_equality=True,whole_partial_vm_range_insert_target_relocations=2,Rust_dump_bytes_and_full_relocations_unchanged=True,Rust_dump_relocations=dumprefs,Rust_log_relocations=logrefs,readonly_gate=dict(symbol=g,section=gsec['name'],value=0),debug_descriptor=dict(symbol=d,section=dsec['name'],raw=draw.hex(),pointer_relocations=drefs),actual433_leaf_reused=bindings['accepted_leaf'],source_count=78,headers=73,source_identity=r['source_identity'],compiler_invocations=0,linker_invocations=0,NM_readelf_invocations=0,old14commands_replayed=False,product_mutations=0,canonical_mutations=0,full_default_GCC14_image_link=False,native=False,file_retired=False,retained_C_debt=['Readonly original dump gate data','Other process.c compute bodies'])
 with (P/'OBSERVER-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(scope=SCOPE,status=result['status'],result=pin(P/'OBSERVER-RESULT.json'))))
if __name__=='__main__':main()
