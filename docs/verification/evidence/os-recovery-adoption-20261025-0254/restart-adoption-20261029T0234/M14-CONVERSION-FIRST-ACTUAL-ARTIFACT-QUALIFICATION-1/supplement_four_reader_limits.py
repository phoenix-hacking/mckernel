"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Four exact read-only119 relocation supplements. Original reader/oracle unchanged.
"""
from pathlib import Path
import ast,struct,json,hashlib,re
p=Path(__file__).resolve().parent/'inspect_conversion.py';nodes=[]
for node in ast.parse(p.read_bytes()).body:
 if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='proofs'for t in node.targets):break
 nodes.append(node)
context={'__file__':str(p)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':READONLY_CONTEXT_ONLY','exec'),context);globals().update(context)
observed_tables={'arch_vdso_map_log_bridge':40,'arch_vdso_setup_log_bridge':32,'f03_wait_log_v1':40};MASK=(1<<64)-1;proofs=[]
for name in list(observed_tables)+['vdso_get_vdso_info']:
 e=new;s=own(e,name);f=image.sym(name);assert(s['type'],s['bind'],s['size'])==(f['type'],f['bind'],f['size'])and s['type']==2 and s['bind']==1
 assert not[(r['link_token'],q)for r,x in objects if x is not new for q in defined(x,name)]
 original=data(e,s);actual=image.bytes(f);patched=bytearray(original);details=[]
 for rel in rels(e,s):
  off=rel['offset'];t=rel['target'];add=rel['addend'];assert rel['type']==1 and 0<=off<=len(original)-8
  value=struct.unpack_from('<Q',actual,off)[0];sec=e.sections[t['shndx']]if t['shndx']else None
  if sec and sec['name']in('.lrodata.str1.1','.rodata.str1.1'):
   text=literal(e,t,add);assert image.at(value,len(text),True)[0]==text;detail=dict(kind='EXACT_INPUT_NUL_STRING',literal_hex=text.hex())
  elif t['name']:
   exact=image.sym(t['name'])['value']+add;assert value==exact&MASK
   if exact!=value:assert name=='vdso_get_vdso_info'and off==559 and t['name']=='mckernel_f06_vdso_state'and add==0x1800000
   detail=dict(kind='NAMED_R_X86_64_64',target=t['name'],addend=add,unbounded_S_plus_A=hex(exact),actual_u64=hex(value),wrap64=exact!=value)
  else:
   assert name in observed_tables and t['type']==3 and t['bind']==0 and t['value']==0 and add==0
   assert sec['name']=='.lrodata.'+name and sec['flags']&7==2 and sec['align']==8 and sec['size']==observed_tables[name]
   payload=e.payload(sec);assert payload==bytes(sec['size']);rs=[x for x in e.sections if x['type']==4 and x['info']==sec['index']];assert len(rs)==1 and rs[0]['size']==sec['size']//8*24
   targets=[]
   for i in range(sec['size']//8):
    offset,info,a=struct.unpack_from('<QQq',e.raw,rs[0]['offset']+24*i);target=e.symbols[info>>32]
    assert offset==8*i and info&0xffffffff==1 and target['type']==3 and target['shndx']==s['shndx']and target['value']==0 and 0<=a<s['size'];targets.append(a)
   table=struct.pack('<'+'Q'*len(targets),*[f['value']+a for a in targets]);assert image.at(value,sec['size'],True)[0]==table
   detail=dict(kind='EXACT_SELF_RELATIVE_JUMP_TABLE',section=sec['name'],bytes=sec['size'],function_relative_targets=targets,actual_final_table=table.hex(),actual_final_address=hex(value))
  struct.pack_into('<Q',patched,off,value);details.append(dict(offset=off,relocation_type=1,**detail))
 assert bytes(patched)==actual
 proofs.append(dict(name=name,input=s,final=f,unique_actual_Rust_owner=True,all_nonrelocated_instruction_bytes_equal=True,all_relocation_targets_proven=True,full_actual_final_function_bytes=True,relocations=details))
result=dict(scope=__doc__.splitlines()[0],status='PASS_FOUR_EXACT_CURRENT119_RELOCATION_SUPPLEMENTS_PENDING_INDEPENDENT_DISPOSITION',actual_Rust=ref(new.path),actual_image=ref(image.path),preserved_first_reader_failures=ref(D/'ACTUAL119-ARTIFACT-FACTS.json'),frozen_original_readers_unchanged=True,original389_unchanged=True,proofs=proofs,interpretation='Three newly emitted selfjump tables were outside fixed old-reader function whitelist. One R_X86_64_64 result wraps modulo2^64; old Python reader compared an unbounded integer. No input/output/expected389 bytes altered.',artifact_acceptance=False,native_acceptance=False,wholefile_acceptance=False,runtime_authority=None)
(D/'FOUR-READER-LIMIT-SUPPLEMENT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],functions=len(proofs),report=ref(D/'FOUR-READER-LIMIT-SUPPLEMENT.json'))))
