"""Only this ordinary C ABI caller and actual two-provider final ELF bindings."""
from pathlib import Path
import hashlib,importlib.util,json,struct

def provider(q):
 p=Path(q['qualified_ELF_reader']['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['qualified_ELF_reader']['sha256'];spec=importlib.util.spec_from_file_location('qualified_string_witness_reader',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 actual=Path(q['provider_object']);assert hashlib.sha256(actual.read_bytes()).hexdigest()==q['provider_sha256'];e=m.Image(actual);assert set(e.defined)=={'memset','strnlen'} and e.undefined==set();proof=json.loads(Path(q['actual_core_check']).read_text());assert proof['object_sha256']==q['provider_sha256'] and proof['direct_indirect_self_cross_helper_calls']==0 and proof['text_relocations']==[]
 return m,e

def caller(q):
 m,e=provider(q);c=m.Image(q['caller_object']);required={'memset','strnlen'};assert required<=c.undefined and not(required&set(c.defined));assert c.undefined<=set(q['allowed_HOST_caller_imports'])
 assert set(c.defined)=={'main'} and c.kind(c.defined['main'])=='T'
 definitions,imports=m.parse_nm(Path(q['caller_nm']).read_text());assert set(definitions)==set(c.defined) and imports==c.undefined
 calls={name:0 for name in required}
 for r in c.relocations:
  if r['symbol']['name'] in required:
   assert r['symbol']['section']==0 and r['type'] in (2,4) and r['offset']>0
   section=c.sections[r['section']];assert section['flags']&4 and c.contents(section)[r['offset']-1]==0xe8,'Expected actual direct C ABI call relocation'
   calls[r['symbol']['name']]+=1
 assert all(calls.values());disassembly=Path(q['caller_disassembly']).read_text();assert 'memset' in disassembly and 'strnlen' in disassembly
 return {'status':'PASS_ACTUAL_CALLER_CALLS_BEFORE_LINK','required_genuine_Kernel_undefined':sorted(required),'actual_direct_call_relocations':calls,'no_local_Kernel_substitute':True,'HOST_only_other_imports':sorted(c.undefined-required),'builtin_disable_flags_bound_in_request':True}

def executable(q):
 _,original=provider(q);raw=Path(q['executable']).read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1]==2 and h[2]==62 and h[8]==64 and h[11]==64
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+64*i) for i in range(h[12])];tables=[s for s in sections if s[1]==2];assert len(tables)==1;table=tables[0];assert table[9]==24 and table[5]%24==0;strings=sections[table[6]];names=raw[strings[4]:strings[4]+strings[5]];found={}
 for offset in range(0,table[5],24):
  name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,table[4]+offset);end=names.index(0,name);text=names[name:end].decode('utf8')
  if text not in original.defined:continue
  assert text not in found and info>>4==1 and info&15==2 and other&3==0 and 0<index<len(sections)
  section=sections[index];assert section[1]==1 and section[2]&4 and value>=section[3];within=value-section[3];assert within+size<=section[5]
  assert size==original.defined[text]['size'];code=raw[section[4]+within:section[4]+within+size];assert code==original.symbol_bytes(original.defined[text]),text
  found[text]={'address':hex(value),'bytes':size,'source_object_exact_function_sha256':hashlib.sha256(code).hexdigest(),'unique_global_FUNC_not_U_PLT_or_libc':True}
 assert set(found)=={'memset','strnlen'} and Path(q['executable_elf']).read_bytes()
 return {'status':'PASS_ACTUAL_FINAL_ELF_KERNEL_BINDINGS_BEFORE_RUNTIME','ELF':'actualordinaryHOSTnonPIEEXEC/x86_64','actual_Kernel_roots':found,'qualified_provider_sha256':q['provider_sha256'],'no_kernel_state_native_or_initialization_claim':True}
