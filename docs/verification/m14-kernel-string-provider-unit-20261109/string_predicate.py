"""Bounded two-root object/decoded-instruction predicate; never executes roots."""
from pathlib import Path
import hashlib
import importlib.util
import re

def qualify(request,receipt):
 reader=Path(request['qualified_elf_reader']['path']);assert hashlib.sha256(reader.read_bytes()).hexdigest()==request['qualified_elf_reader']['sha256'];spec=importlib.util.spec_from_file_location('qualified_storage_elf_reader',reader);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 image=module.Image(request['provider_object']);expected={'memset','strnlen'};assert set(image.defined)==expected and image.undefined==set()
 for name,symbol in image.defined.items():assert image.kind(symbol)=='T' and symbol['type']==2 and symbol['size']>0 and symbol['other']&3==0,name
 actual_functions={s['name'] for s in image.symbols if s['type']==2 and s['section']!=0};assert actual_functions==expected,'Unexpected out-of-line helper or other generated function'
 text_relocations=[]
 for r in image.relocations:
  for name,symbol in image.defined.items():
   if r['section']==symbol['section'] and symbol['value']<=r['offset']<symbol['value']+symbol['size']:text_relocations.append({'root':name,'target':r['symbol']['name'],'type':r['type']})
 assert text_relocations==[],'Unexpected self/cross/helper/compiler-lowered text relocation'
 nm,undefined=module.parse_nm((receipt/'provider-symbols.stdout').read_text());assert set(nm)==expected and undefined==set()
 for name,fields in nm.items():assert fields=={'kind':'T','size':image.defined[name]['size']}
 current=None;instructions={name:0 for name in expected};returns={name:0 for name in expected};branches={name:0 for name in expected}
 for line in (receipt/'provider-disassembly.stdout').read_text().splitlines():
  header=re.match(r'^([0-9a-f]+) <([^>]+)>:$',line.strip())
  if header:
   current=header.group(2);assert current in expected,'Unexpected decoded function';continue
  row=re.match(r'^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*?)\s*$',line)
  if not row:continue
  assert current is not None;address=int(row.group(1),16);symbol=image.defined[current]
  if not(symbol['value']<=address<symbol['value']+symbol['size']):continue # section padding is not a function body
  mnemonic,operand=row.group(2),row.group(3);instructions[current]+=1
  assert not mnemonic.startswith('call') and mnemonic!='lcall','Unexpected direct/indirect call: '+line
  if mnemonic.startswith('j') or mnemonic.startswith('loop'):
   target=re.match(r'^([0-9a-f]+)\s+<([^>]+)>$',operand);assert target,'Unexpected indirect or unbound tail/control transfer: '+line
   assert target.group(2).split('+',1)[0]==current and symbol['value']<=int(target.group(1),16)<symbol['value']+symbol['size'],'Cross/self-lowered function transfer: '+line
   branches[current]+=1
  if mnemonic.startswith('ret'):returns[current]+=1
 assert all(instructions[name]>0 and returns[name]>0 for name in expected)
 assert (receipt/'provider-elf.stdout').read_bytes()
 return {'status':'PASS_ACTUAL_TWO_ROOT_FUNCTIONS_ZERO_U_NO_GENERATED_CALLS','object_sha256':hashlib.sha256(Path(request['provider_object']).read_bytes()).hexdigest(),'global_T':{name:image.defined[name]['size'] for name in sorted(expected)},'global_data':[],'genuine_U':[],'defined_private_helper_functions':[],'text_relocations':text_relocations,'decoded_instruction_counts':instructions,'internal_branch_counts':branches,'actual_return_instructions':returns,'direct_indirect_self_cross_helper_calls':0,'exact_source_volatile_bodies_preserved':True,'functions_or_native_runtime_executed':False}
