"""Only this ordinary C ABI caller and actual two-provider final ELF bindings."""
from pathlib import Path
import hashlib,importlib.util,json,struct,re

def provider(q):
 p=Path(q['qualified_ELF_reader']['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['qualified_ELF_reader']['sha256'];spec=importlib.util.spec_from_file_location('qualified_string_witness_reader',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 actual=Path(q['provider_object']);assert hashlib.sha256(actual.read_bytes()).hexdigest()==q['provider_sha256'];e=m.Image(actual);assert set(e.defined)=={'memset','strnlen'} and e.undefined==set();proof=json.loads(Path(q['actual_core_check']).read_text());assert proof['object_sha256']==q['provider_sha256'] and proof['direct_indirect_self_cross_helper_calls']==0 and proof['text_relocations']==[]
 return m,e

def decoded(image,text):
 instructions=[];section=None
 for line in text.splitlines():
  head=re.match(r'^Disassembly of section (.+):$',line)
  if head:
   matches=[s for s in image.sections if s['name']==head.group(1)];assert len(matches)==1;section=matches[0]['index'];continue
  row=re.match(r'^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*?)\s*$',line)
  if not row:continue
  assert section is not None;mnemonic,operands=row.group(2),row.group(3)
  if mnemonic in ('notrack','bnd') and operands.startswith('call '):mnemonic='call';operands=operands[5:].strip()
  instructions.append({'section':section,'address':int(row.group(1),16),'mnemonic':mnemonic,'operands':operands})
 return instructions

def register_name(value):
 table={'eax':'rax','ax':'rax','al':'rax','ah':'rax','ebx':'rbx','bx':'rbx','bl':'rbx','bh':'rbx','ecx':'rcx','cx':'rcx','cl':'rcx','ch':'rcx','edx':'rdx','dx':'rdx','dl':'rdx','dh':'rdx','esi':'rsi','si':'rsi','sil':'rsi','edi':'rdi','di':'rdi','dil':'rdi','ebp':'rbp','bp':'rbp','bpl':'rbp','esp':'rsp','sp':'rsp','spl':'rsp'}
 if re.fullmatch(r'r(?:8|9|1[0-5])(?:d|w|b)',value):return re.sub(r'[dwb]$','',value)
 return table.get(value,value)

def caller(q):
 m,e=provider(q);c=m.Image(q['caller_object']);required={'memset','strnlen'};assert required<=c.undefined and not(required&set(c.defined));assert c.undefined<=set(q['allowed_HOST_caller_imports'])
 assert set(c.defined)=={'main'} and c.kind(c.defined['main'])=='T'
 definitions,imports=m.parse_nm(Path(q['caller_nm']).read_text());assert set(definitions)==set(c.defined) and imports==c.undefined
 slots=[x for x in c.symbols if x['name']==q['memset_pointer_slot']];assert len(slots)==1;slot=slots[0];assert slot['bind']==0 and slot['type']==1 and slot['size']==8 and c.kind(slot)=='D'
 initializers=[r for r in c.relocations if r['section']==slot['section'] and slot['value']<=r['offset']<slot['value']+8];assert len(initializers)==1;r=initializers[0];assert r['offset']==slot['value'] and r['type']==1 and r['symbol']['name']=='memset' and r['symbol']['section']==0 and r['addend']==0
 direct=0
 for r in c.relocations:
  if r['symbol']['name']=='strnlen':
   assert r['symbol']['section']==0 and r['type'] in (2,4) and r['offset']>0;section=c.sections[r['section']];assert section['flags']&4 and c.contents(section)[r['offset']-1]==0xe8;direct+=1
 assert direct>0
 instructions=decoded(c,Path(q['caller_disassembly']).read_text());loads=[]
 for r in c.relocations:
  if not c.sections[r['section']]['flags']&4 or r['symbol']['section']!=slot['section']:continue
  adjustment=4 if r['type']==2 else 0
  if r['type'] not in (2,10,11) or r['symbol']['value']+r['addend']+adjustment!=slot['value']:continue
  matches=[]
  for i,ins in enumerate(instructions):
   if ins['section']!=r['section']:continue
   later=[x['address'] for x in instructions if x['section']==r['section'] and x['address']>ins['address']];limit=min(later) if later else ins['address']+15
   if ins['address']<=r['offset']<limit:matches.append(i)
  assert len(matches)==1;i=matches[0];load=instructions[i]
  functions=[x for x in c.symbols if x['type']==2 and x['section']==load['section'] and x['value']<=load['address']<x['value']+x['size']];assert len(functions)==1;function=functions[0]
  if load['mnemonic']=='call':assert load['operands'].startswith('QWORD PTR [');call=load
  else:
   target=re.match(r'^(r(?:ax|bx|cx|dx|si|di|bp|8|9|1[0-5])),\s*QWORD PTR \[',load['operands']);assert load['mnemonic']=='mov' and target,'Expected actual64bit volatile slot load';register=target.group(1);call=None
   for next_ in instructions[i+1:]:
    if next_['section']!=load['section'] or not(function['value']<=next_['address']<function['value']+function['size']):continue
    if next_['mnemonic']=='call':assert next_['operands']==register;call=next_;break
    assert not next_['mnemonic'].startswith(('j','ret','loop')),'Control transfer before loaded-pointer call'
    destination=register_name(next_['operands'].split(',',1)[0].strip())
    assert destination!=register or next_['mnemonic'] in ('cmp','test','bt','nop'),'Loaded function pointer clobbered beforecall'
   assert call is not None
  loads.append({'source_function':function['name'],'slot_reference_offset':r['offset'],'slot_reference_type':r['type'],'volatile_load_address':load['address'],'indirect_call_address':call['address']})
 assert loads,'Noactualslot-load/indirectcall proven'
 return {'status':'PASS_ACTUAL_CALLER_POINTER_AND_DIRECT_CALL_PROVENANCE_BEFORE_LINK','required_genuine_Kernel_undefined':sorted(required),'private8Bvolatile_pointer_slot':slot['name'],'actual_slot_initializer':'R_X86_64_64 to U memset+0','actual_memset_load_indirect_calls':loads,'actual_strnlen_direct_E8_calls':direct,'no_local_Kernel_substitute':True,'exact_HOST_imports':sorted(c.undefined-required),'real_header_bound_printf_chk':'__printf_chk' in c.undefined}

def executable(q):
 _,original=provider(q);raw=Path(q['executable']).read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1]==2 and h[2]==62 and h[8]==64 and h[11]==64
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+64*i) for i in range(h[12])];tables=[s for s in sections if s[1]==2];assert len(tables)==1;table=tables[0];assert table[9]==24 and table[5]%24==0;strings=sections[table[6]];names=raw[strings[4]:strings[4]+strings[5]];found={};slots=[];all_symbols=[]
 for offset in range(0,table[5],24):
  name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,table[4]+offset);end=names.index(0,name);text=names[name:end].decode('utf8')
  all_symbols.append({'name':text,'bind':info>>4,'type':info&15,'section':index,'value':value,'size':size})
  if text==q['memset_pointer_slot']:slots.append({'bind':info>>4,'type':info&15,'section':index,'value':value,'size':size})
  if text not in original.defined:continue
  assert text not in found and info>>4==1 and info&15==2 and other&3==0 and 0<index<len(sections)
  section=sections[index];assert section[1]==1 and section[2]&4 and value>=section[3];within=value-section[3];assert within+size<=section[5]
  assert size==original.defined[text]['size'];code=raw[section[4]+within:section[4]+within+size];assert code==original.symbol_bytes(original.defined[text]),text
  found[text]={'address':hex(value),'bytes':size,'source_object_exact_function_sha256':hashlib.sha256(code).hexdigest(),'unique_global_FUNC_not_U_PLT_or_libc':True}
 assert set(found)=={'memset','strnlen'} and Path(q['executable_elf']).read_bytes()
 assert len(slots)==1;slot=slots[0];assert slot['bind']==0 and slot['type']==1 and slot['size']==8 and 0<slot['section']<len(sections);section=sections[slot['section']];assert section[1]==1 and section[2]&1;within=slot['value']-section[3];assert within>=0 and within+8<=section[5];pointer=int.from_bytes(raw[section[4]+within:section[4]+within+8],'little');assert pointer==int(found['memset']['address'],16),'FinalvolatilepointerdoesnotbindactualKernelmemsetFUNC'
 for relocation_section in sections:
  if relocation_section[1]!=4:continue
  assert relocation_section[9]==24
  for offset in range(0,relocation_section[5],24):
   relocation_offset=struct.unpack_from('<Q',raw,relocation_section[4]+offset)[0];assert not(slot['value']<=relocation_offset<slot['value']+8),'Runtime relocation mayreplace bound private pointer'
 caller_provenance=caller(q);module,_=provider(q);original_caller=module.Image(q['caller_object']);final_callers={}
 for evidence in caller_provenance['actual_memset_load_indirect_calls']:
  name=evidence['source_function'];before=[x for x in original_caller.symbols if x['name']==name and x['type']==2];after=[x for x in all_symbols if x['name']==name and x['type']==2 and x['section']!=0];assert len(before)==len(after)==1;before,after=before[0],after[0];assert before['bind']==after['bind'] and before['size']==after['size'];section=sections[after['section']];base=after['value']-section[3];assert base>=0 and base+after['size']<=section[5];actual=raw[section[4]+base:section[4]+base+after['size']];expected=original_caller.symbol_bytes(before);mask=bytearray(len(expected))
  for relocation in original_caller.relocations:
   if relocation['section']!=before['section'] or not(before['value']<=relocation['offset']<before['value']+before['size']):continue
   widths={1:8,2:4,4:4,10:4,11:4};assert relocation['type'] in widths;at=relocation['offset']-before['value'];width=widths[relocation['type']];assert at+width<=len(mask);mask[at:at+width]=bytes([1])*width
  assert all(mark or left==right for mark,left,right in zip(mask,expected,actual)),'Finalcallerload/callopcodeorregisterflowchanged'
  at=evidence['slot_reference_offset']-before['value'];field=int.from_bytes(actual[at:at+4],'little',signed=evidence['slot_reference_type'] in (2,11));load_target=after['value']+at+4+field if evidence['slot_reference_type']==2 else field;assert load_target==slot['value'],'Finalvolatileloadaddresseswrongpointercell';final_callers[name]={'bytes':after['size'],'nonrelocated_opcode_bytes_preserved':True,'actual_final_pointer_load_target':hex(load_target),'actual_final_indirect_call_address':hex(after['value']+evidence['indirect_call_address']-before['value'])}
 direct_final=[]
 for relocation in original_caller.relocations:
  if relocation['symbol']['name']!='strnlen':continue
  before=[x for x in original_caller.symbols if x['type']==2 and x['section']==relocation['section'] and x['value']<=relocation['offset']<x['value']+x['size']];assert len(before)==1;before=before[0];after=[x for x in all_symbols if x['name']==before['name'] and x['type']==2 and x['section']!=0];assert len(after)==1;after=after[0];section=sections[after['section']];relative=relocation['offset']-before['value'];at=section[4]+after['value']-section[3]+relative;assert raw[at-1]==0xe8;displacement=int.from_bytes(raw[at:at+4],'little',signed=True);target=after['value']+relative+4+displacement;assert target==int(found['strnlen']['address'],16),'FinalstrnlencallnotactualKernelroot';direct_final.append(hex(target))
 assert direct_final
 return {'status':'PASS_ACTUAL_FINAL_ELF_KERNEL_BINDINGS_BEFORE_RUNTIME','ELF':'actualordinaryHOSTnonPIEEXEC/x86_64','actual_Kernel_roots':found,'qualified_provider_sha256':q['provider_sha256'],'private_pointer_value_equals_actual_memset_FUNC':hex(pointer),'actual_final_caller_load_and_indirect_call_bindings':final_callers,'actual_final_direct_strnlen_targets':direct_final,'no_kernel_state_native_or_initialization_claim':True}
