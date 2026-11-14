"""This partition's ELF64-LE/REL data/relocation predicate; no execution loader.

Only the admitted storage object and exact current lower partial are inspected.
This is not an ELF loader, provider substitute or runtime initialization proof.
"""
from pathlib import Path
import hashlib
import json
import struct

class Image:
 def __init__(self,path):
  self.path=Path(path);self.raw=self.path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.raw)
  assert h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1]==1 and h[2]==62 and h[3]==1,'Expected actual ELF64-LE x86_64 REL'
  assert h[8]==64 and h[11]==64 and h[12]>0 and 0<h[13]<h[12]
  assert h[6]+64*h[12]<=len(self.raw)
  self.sections=[]
  for i in range(h[12]):
   f=struct.unpack_from('<IIQQQQIIQQ',self.raw,h[6]+64*i);s=dict(zip(('name_offset','type','flags','address','offset','size','link','info','align','entry_size'),f));s['index']=i
   if s['type']!=8:assert s['offset']+s['size']<=len(self.raw)
   self.sections.append(s)
  strings=self.contents(self.sections[h[13]])
  for s in self.sections:s['name']=self.string(strings,s['name_offset'])
  tables=[s for s in self.sections if s['type']==2];assert len(tables)==1;table=tables[0];assert table['entry_size']==24 and table['size']%24==0
  assert self.sections[table['link']]['type']==3;names=self.contents(self.sections[table['link']]);self.symbols=[];self.defined={};self.undefined=set()
  for offset in range(0,table['size'],24):
   f=struct.unpack_from('<IBBHQQ',self.raw,table['offset']+offset);symbol={'name':self.string(names,f[0]),'bind':f[1]>>4,'type':f[1]&15,'other':f[2],'section':f[3],'value':f[4],'size':f[5]};self.symbols.append(symbol)
   if symbol['bind']!=0:
    assert symbol['bind']==1 and symbol['name'],'Unexpected weak/unique/global alias'
    if symbol['section']==0:self.undefined.add(symbol['name'])
    else:
     assert 0<symbol['section']<len(self.sections) and symbol['name'] not in self.defined
     self.defined[symbol['name']]=symbol
  self.relocations=[]
  for s in self.sections:
   assert s['type']!=9,'Unexpected REL rather than selected native RELA'
   if s['type']==4:
    assert s['link']==table['index'] and s['entry_size']==24 and s['size']%24==0 and 0<s['info']<len(self.sections)
    for offset in range(0,s['size'],24):
     at,info,addend=struct.unpack_from('<QQq',self.raw,s['offset']+offset);assert info>>32<len(self.symbols)
     self.relocations.append({'section':s['info'],'offset':at,'type':info&0xffffffff,'symbol':self.symbols[info>>32],'addend':addend})
 @staticmethod
 def string(table,offset):
  assert 0<=offset<len(table);end=table.index(0,offset);return table[offset:end].decode('utf8')
 def contents(self,section):
  assert section['type']!=8,'NOBITS is metadata, not fabricated initialized HOST bytes'
  return self.raw[section['offset']:section['offset']+section['size']]
 def symbol_bytes(self,symbol):
  section=self.sections[symbol['section']];assert symbol['value']+symbol['size']<=section['size'];return self.contents(section)[symbol['value']:symbol['value']+symbol['size']]
 def kind(self,symbol):
  s=self.sections[symbol['section']]
  if symbol['type']==2 and s['flags']&4:return 'T'
  assert symbol['type']==1
  if s['type']==8:return 'B'
  assert s['type']==1
  return 'D' if s['flags']&1 else 'R'
 def pointer_target(self,relocation,size):
  assert relocation['type']==1,'Selected native data pointer requires R_X86_64_64'
  symbol=relocation['symbol'];assert 0<symbol['section']<len(self.sections);section=self.sections[symbol['section']];assert section['type']==1 and not section['flags']&5
  offset=symbol['value']+relocation['addend'];assert offset>=0 and offset+size<=section['size'];return section['index'],offset,self.contents(section)[offset:offset+size]

def storage(image,contract,strict):
 expected=set(contract['data'])|{contract['function']}
 if strict:assert set(image.defined)==expected and image.undefined=={'kprintf'}
 else:assert expected<=set(image.defined) and 'kprintf' in image.undefined
 details={}
 for name,(kind,size) in contract['data'].items():
  sym=image.defined[name];assert image.kind(sym)==kind and sym['size']==size and sym['other']&3==0,name
  section=image.sections[sym['section']];assert sym['value']+size<=section['size'];details[name]={'kind':kind,'bytes':size,'section':section['name']}
  if kind=='B':assert section['type']==8 and size==8
 assert image.symbol_bytes(image.defined['num_processors'])==b'\x01\x00\x00\x00'
 assert image.symbol_bytes(image.defined['x86_map_kernel_start_geometry'])==bytes.fromhex('000080feffffffff')
 file_addresses=[]
 for name,flags in contract['descriptor_flags'].items():
  sym=image.defined[name];section=image.sections[sym['section']];assert section['name']=='__verbose' and section['align']>=8 and section['align']%8==0 and sym['value']%8==0
  raw=image.symbol_bytes(sym);assert raw[16:24]==bytes(8) and int.from_bytes(raw[24:28],'little')==flags
  relocs=[r for r in image.relocations if r['section']==sym['section'] and sym['value']<=r['offset']<sym['value']+32];assert {r['offset']-sym['value'] for r in relocs}=={0,8} and len(relocs)==2
  by_offset={r['offset']-sym['value']:r for r in relocs};where=image.pointer_target(by_offset[0],len(contract['trace_file_bytes']));assert where[2]==bytes(contract['trace_file_bytes']);file_addresses.append(where[:2]);function=image.pointer_target(by_offset[8],len(contract['descriptor_function_bytes']));assert function[2]==bytes(contract['descriptor_function_bytes'])
  details[name].update({'line_flags':flags,'fmt_null':True,'exact_original_file_bytes':len(where[2]),'exact_original_function_string':True,'data_pointer_relocations':'R_X86_64_64'})
 assert file_addresses[0]==file_addresses[1],'Both actual descriptors retain the same static TRACE_FILE'
 sym=image.defined[contract['function']];assert image.kind(sym)=='T' and sym['size']>0
 relocs=[r for r in image.relocations if r['section']==sym['section'] and sym['value']<=r['offset']<sym['value']+sym['size']]
 assert any(r['symbol']['name']=='kprintf' and r['symbol']['section']==0 for r in relocs),'Real unresolved kprintf call must remain'
 for name in contract['descriptor_flags']:
  target=image.defined[name];assert any(r['symbol']['section']==target['section'] and target['value']<=r['symbol']['value']+r['addend']<target['value']+32 for r in relocs),name
 return {'global_storage':details,'logger_bytes':sym['size'],'genuine_kprintf_undefined_and_referenced':True,'no_runtime_initialization_claim':True}

def parse_nm(text):
 defined={};undefined=set()
 for line in text.splitlines():
  f=line.split();assert len(f)>=2
  if f[1]=='U':undefined.add(f[0])
  elif f[1].isupper():
   assert len(f)==4 and f[0] not in defined;defined[f[0]]={'kind':f[1],'size':int(f[3],16)}
 return defined,undefined

def prejoin(request,contract,receipt):
 q=request;object_path=Path(q['storage_object']);lower_path=Path(q['actual_lower_partial']['path']);assert hashlib.sha256(lower_path.read_bytes()).hexdigest()==q['actual_lower_partial']['sha256']
 unit=Image(object_path);lower=Image(lower_path);decision=storage(unit,contract,True)
 assert set(lower.defined)==set(q['actual_lower_partial']['actual21T_sizes']) and lower.undefined==set(q['actual_lower_partial']['actual19_genuine_U'])
 for name,size in q['actual_lower_partial']['actual21T_sizes'].items():assert lower.kind(lower.defined[name])=='T' and lower.defined[name]['size']==size
 assert not(set(unit.defined)&set(lower.defined)),'Duplicate strong owners are forbidden'
 nm,undefined=parse_nm((receipt/'storage-symbols.stdout').read_text());assert set(nm)==set(unit.defined) and undefined==unit.undefined
 for name,fields in nm.items():assert fields=={'kind':unit.kind(unit.defined[name]),'size':unit.defined[name]['size']}
 assert (receipt/'storage-elf.stdout').read_bytes() and (receipt/'storage-bytes.stdout').read_bytes()
 return {'status':'PASS_CALLED_PREJOIN_STORAGE_ABI_BYTES_RELOCATIONS_UNIQUE_OWNERS','storage_object_sha256':hashlib.sha256(object_path.read_bytes()).hexdigest(),'actual_lower_sha256':q['actual_lower_partial']['sha256'],'global_strong_definitions':len(unit.defined),'global_data_definitions':len(contract['data']),'genuine_unit_U':sorted(unit.undefined),'existing21_unique_T_verified':True,'duplicate_strong_owners':[],'checks':decision,'runtime_executed':False}

def postjoin(request,contract):
 unit=Image(request['storage_object']);lower=Image(request['actual_lower_partial']['path']);joined=Image(request['joined_object']);expected=set(unit.defined)|set(lower.defined);assert len(expected)==30 and set(joined.defined)==expected
 assert joined.undefined==set(request['prospective_join']['expected_genuine_unresolved']) and len(joined.undefined)==13
 for name,sym in {**lower.defined,**unit.defined}.items():
  assert joined.defined[name]['size']==sym['size']
  if sym['type']==2:
   original=lower if name in lower.defined else unit;assert joined.kind(joined.defined[name])=='T' and joined.symbol_bytes(joined.defined[name])==original.symbol_bytes(sym),name
 decision=storage(joined,contract,False)
 return {'status':'PASS_CALLED_POSTJOIN_EXACT_30_STRONG_13_GENUINE_U','joined_sha256':hashlib.sha256(Path(request['joined_object']).read_bytes()).hexdigest(),'global_strong_definitions':30,'function_T':22,'global_data':8,'genuine_U':sorted(joined.undefined),'all21_predecessor_function_sizes_and_bytes_preserved':True,'new_logger_bytes_preserved':True,'storage_checks':decision,'no_runtime_or_native_init_claim':True}
