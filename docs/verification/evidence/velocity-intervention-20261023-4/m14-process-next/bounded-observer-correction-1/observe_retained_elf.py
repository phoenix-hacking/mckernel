"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One offline observer-only correction: no compiler, linker, workload or mutation.
"""
from pathlib import Path
import hashlib,json,struct
H=Path(__file__).resolve().parent;B=H.parent;W=B/'fixture/ordinary-attempt-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
EXTRA={'ihk_mc_chk_page_address','virt_to_phys'}
CALLBACKS={'vm_range_insert_log_bridge','vm_range_insert_dump_bridge'}
SAFE={'.ltext.rb_first_safe','.ltext.rb_next_safe'}
CALLERS=('process_split_range_insert_bridge','process_add_range_insert_bridge')

def need(ok,message):
 if not ok:raise ValueError(message)
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def textz(raw,offset):
 end=raw.index(b'\0',offset);return raw[offset:end].decode()
class Elf:
 def __init__(self,path):
  self.path=path;self.raw=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.raw)
  need(h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1]==1 and h[2]==62,'ELF64LE x86_64 relocatable')
  need(h[11]==64 and h[12]>0 and h[13]<h[12],'ordinary section table')
  self.sections=[]
  for i in range(h[12]):
   sh=struct.unpack_from('<IIQQQQIIQQ',self.raw,h[6]+i*h[11])
   self.sections.append(dict(index=i,name_offset=sh[0],type=sh[1],flags=sh[2],address=sh[3],offset=sh[4],size=sh[5],link=sh[6],info=sh[7],align=sh[8],entry_size=sh[9]))
  strings=self.data(self.sections[h[13]])
  for s in self.sections:s['name']=textz(strings,s['name_offset'])
  self.tables={};self.symbols=[]
  for s in self.sections:
   if s['type']!=2:continue
   need(s['entry_size']==24 and s['size']%24==0,'ELF symbol entry geometry')
   strings=self.data(self.sections[s['link']]);rows=[]
   for offset in range(0,s['size'],24):
    name,info,other,section,value,size=struct.unpack_from('<IBBHQQ',self.raw,s['offset']+offset)
    row=dict(name=textz(strings,name),bind=info>>4,type=info&15,other=other,section=section,value=value,size=size)
    rows.append(row);self.symbols.append(row)
   self.tables[s['index']]=rows
  self.relocations=[]
  for s in self.sections:
   if s['type']!=4:continue
   need(s['entry_size']==24 and s['size']%24==0 and s['link'] in self.tables,'ELF RELA geometry')
   for offset in range(0,s['size'],24):
    address,info,addend=struct.unpack_from('<QQq',self.raw,s['offset']+offset)
    symbol=self.tables[s['link']][info>>32]
    self.relocations.append(dict(relocation_section=s['name'],section=self.sections[s['info']]['name'],offset=address,type=info&0xffffffff,addend=addend,symbol=symbol['name'],undefined=symbol['section']==0))
 def data(self,section):return self.raw[section['offset']:section['offset']+section['size']]
 def defined_function(self,name):
  rows=[r for r in self.symbols if r['name']==name]
  need(len(rows)==1 and rows[0]['bind']==1 and rows[0]['type']==2 and 0<rows[0]['section']<len(self.sections),'unique global function '+name)
  row=rows[0];section=self.sections[row['section']];need(section['flags']&4,'function executable section '+name)
  return row,section
 def function_bytes_and_relocations(self,name):
  row,section=self.defined_function(name);begin=row['value'];end=begin+row['size']
  raw=self.data(section)[begin:end]
  need(len(raw)==row['size'] and len(raw)>0,'complete function bytes '+name)
  refs=[dict(relative_offset=r['offset']-begin,type=r['type'],addend=r['addend'],symbol=r['symbol']) for r in self.relocations if r['section']==section['name'] and begin<=r['offset']<end]
  return raw,refs

def main():
 binding=H/'INPUT-BINDINGS.json';expected=json.loads(binding.read_text())
 for relative,sha in expected['input_sha256'].items():need(pin(B/relative)['sha256']==sha,'exact unchanged retained input '+relative)
 result=dict(scope=SCOPE,status='FAIL_STOP_PRESERVE_ALL',observer_only=True,compiler_invocations=0,linker_invocations=0,previous_14_commands_replayed=False,product_sources_changed=False,full_crate_proven=False,complete_C_TU_proven=False,default_image_link_proven=False,native_proven=False)
 try:
  original=Elf(W/'actual_provider.o');partial=Elf(W/'actual_selected_leaf_link.o');consumer=Elf(W/'actual_default_consumers.o')
  original_refs=[r for r in original.relocations if r['symbol'] in EXTRA]
  need(len(original_refs)==4,'exact four original extra-name relocations')
  need({r['section'] for r in original_refs}==SAFE,'original extra references confined exact two safe iterator sections')
  for name in SAFE:
   rows=[r for r in original_refs if r['section']==name]
   need(len(rows)==2 and {r['symbol'] for r in rows}==EXTRA,'each safe iterator references exact extra pair')
  need(not SAFE&{s['name'] for s in partial.sections},'both safe iterator sections absent from partial')
  need(not [r for r in partial.relocations if r['symbol'] in EXTRA],'zero retained relocation in ANY partial section to extra names')
  undefined_rows={s['name'] for s in partial.symbols if s['section']==0 and s['name']}
  need(undefined_rows==EXTRA|CALLBACKS,'raw partial UND rows remain exact four names')
  captured_names=set((W/'actual-selected-leaf-undefined.stdout').read_text().split())-{'U'}
  need(captured_names==undefined_rows,'raw first-failure nm names preserved exactly')
  live_undefined=[r for r in partial.relocations if r['undefined']]
  need({r['symbol'] for r in live_undefined}==CALLBACKS,'all retained undefined relocations resolve only diagnostic callbacks')
  need(len(live_undefined)==3 and sum(r['symbol']=='vm_range_insert_log_bridge' for r in live_undefined)==2 and sum(r['symbol']=='vm_range_insert_dump_bridge' for r in live_undefined)==1,'exact two log and one dump relocations')
  partial.defined_function('vm_range_insert');original.defined_function('vm_range_insert')
  caller_witnesses=[]
  for name in CALLERS:
   before,refs_before=consumer.function_bytes_and_relocations(name)
   after,refs_after=partial.function_bytes_and_relocations(name)
   need(before==after,'actual untouched caller bytes '+name)
   need(refs_before==refs_after and len(refs_after)==1 and refs_after[0]['symbol']=='vm_range_insert','actual unchanged caller relocation '+name)
   caller_witnesses.append(dict(name=name,bytes=len(after),sha256=hashlib.sha256(after).hexdigest(),relocations=refs_after))
  need(len([r for r in partial.relocations if r['symbol']=='vm_range_insert'])==2,'exact two caller relocations to unique Rust entry')
  result.update(status='PASS_OBSERVER_CORRECTION_RETAINED_ELF_SECTIONS_AND_LIVE_RELOCATIONS',
   original_extra_relocations=original_refs,discarded_safe_sections=sorted(SAFE),
   raw_undefined_names_preserved=sorted(undefined_rows),retained_extra_relocations=[],
   all_retained_undefined_relocations=live_undefined,unique_Rust_entry=True,actual_unchanged_callers=caller_witnesses,
   successful_prior_actual_body_comparisons=1088,retained_C_diagnostic_callback_debt=sorted(CALLBACKS),
   accepted_fulltree_provider_references=expected['accepted_fulltree_provider_references'],
   precise_scope='Same already compiled original/partial objects; discarded safe-iterator UND rows are not live imports. Existing full-tree providers remain separate production closure references; no new fullcrate/default/native proof.')
 except BaseException as error:result['error']=type(error).__name__+': '+str(error)
 result['bound_inputs']=expected['input_sha256']
 with (H/'OBSERVER-RESULT.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
 print(json.dumps(result,sort_keys=True))
 return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
