"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-result observer; no subprocess/hash/ISA execution.
"""
from pathlib import Path
import importlib.util,struct

def need(ok,why):
 if not ok: raise ValueError(why)
def observe(plan,records):
 need(len(records)==19,'exact19 actual commands')
 for i,r in enumerate(records):
  a=r['result'];need(r['index']==i and r['command']['argv']==plan['commands'][i]['argv'],'exact source-bound argv')
  need(a['returncode']==0 and a['direct_child_joined'] and a['group_absent'] and a['closed_streams'] and a['error'] is None and a['retirement_error'] is None,'actual wholejoin')
 for i,lines in plan['strict_stdout'].items():
  cap=Path(records[int(i)]['result']['captures']['stdout']['path']);need(cap.read_text().splitlines()==lines,'strict tape/NoWalk oracle')
  need(Path(records[int(i)]['result']['captures']['stderr']['path']).stat().st_size==0,'empty runtime stderr')
 def symbols(i):
  return [l.split() for l in Path(records[i]['result']['captures']['stdout']['path']).read_text().splitlines() if l.split()]
 entries=['x86_stack_frame_log_bridge','x86_print_stack_bridge']
 for i in (10,11,16):
  rows=symbols(i)
  for n in entries:
   s=[r for r in rows if r[-1]==n];need(len(s)==1 and s[0][-2]=='T','one genuine entry T noU')
 for i in (12,13):
  rows=symbols(i)
  for n in entries:need(not any(r[-1]==n for r in rows),'no selected/fallback C callback duplicate or import')
 rows=symbols(16)
 for n in ['kprintf','__print_stack']:
  s=[r for r in rows if r[-1]==n];need(len(s)==1 and s[0][-2]=='T','genuine existing Rust provider T/noU')
 spec=importlib.util.spec_from_file_location('elf_reader',plan['ELF_reader']['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 out=Path(plan['fresh_output_directory']);c=m.Elf(out/'selected-ABI.o');r=m.Elf(out/'actual_callbacks.o')
 a=struct.unpack('<8Q',c.bytes('M14_C_STACK_OUTPUT_ABI',64));b=struct.unpack('<8Q',r.bytes('M14_RUST_STACK_OUTPUT_ABI',64));need(a==b==(8,8,8,8,8,8,8,8),'real C/Rust ABI8')
 root=m.Elf(Path(plan['retained_Rust_object']['path']));rel=root.relocations();calls={}
 for name in entries:
  hits=[x for x in rel if x['name']==name];need(hits,'actual allocated current Rust callback import refs');calls[name]=hits
 for n in ['kprintf','__print_stack']:
  row=root.one(n);need(row['section']>0 and row['info']&15==2 and root.sections[row['section']][2]&6==6,'real existing allocated Rust provider')
 return {'status':'PASS_CONTROLLED_STACK_OUTPUT2880_ACTUAL_PROVIDER_NOWALK96_REAL_ABI8_GENUINE_ROOT_RUST_PARTIAL_ONLY','actual_callback_pairs':2880,'actual_NoWalk_pairs':96,'actual_ABI_words':list(a),'genuine_existing_Rust_provider_T':['kprintf','__print_stack'],'allocated_current_Rust_callback_refs':calls,'kernel_stack_hardware_native':'NOTEXECUTED','inherited_NULL_freeze_HOLD':True,'default_final_kernel_link_native':'OPEN','engineering_percentage':None}
