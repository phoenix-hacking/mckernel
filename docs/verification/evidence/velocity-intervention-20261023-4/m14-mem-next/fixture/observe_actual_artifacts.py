# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,struct
P=Path(__file__).resolve().parent.parent;O=P/'output-1'
def object_words(path,name,count,width=8):
 raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,16)[0]==1
 off=struct.unpack_from('<Q',raw,40)[0];ents,n=struct.unpack_from('<HH',raw,58);assert ents==64 and 0<n<65535 and off+n*ents<=len(raw)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*ents) for i in range(n)];found=[]
 for sec in sections:
  if sec[1]!=2:continue
  assert sec[9]==24 and sec[6]<n;strings=sections[sec[6]];tab=raw[strings[4]:strings[4]+strings[5]]
  for at in range(sec[4],sec[4]+sec[5],24):
   ni,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,at);end=tab.find(b'\0',ni);assert end>=ni
   if tab[ni:end].decode()==name:
    assert (info&15)==1 and 0<idx<n and size==count*width,(name,info,idx,size)
    target=sections[idx];start=target[4]+value;assert value+size<=target[5] and start+size<=len(raw)
    found.append(struct.unpack_from('<'+('Q' if width==8 else 'I')*count,raw,start))
 assert len(found)==1,(name,len(found));return found[0]
def rows(name):return [line.split() for line in (P/'actual-owned-capture-1'/name/'stdout').read_text().splitlines() if line.split()]
def selected(rs,n):return [r for r in rs if r[-1]==n]
r=rows('07-Rust-symbols');s=rows('08-selected-C-symbols');f=rows('09-fallback-C-symbols');p=rows('13-actual-consumer-partial-symbols')
single='remote_flush_tlb_cpumask';array='remote_flush_tlb_array_cpumask'
assert len(selected(r,single))==1 and selected(r,single)[0][-2]=='T'
assert len(selected(r,array))==1 and selected(r,array)[0][-2]=='U'
assert not selected(s,single)
assert len(selected(f,single))==1 and selected(f,single)[0][-2]=='T'
assert len(selected(f,array))==1 and selected(f,array)[0][-2]=='U'
assert len(selected(p,single))==1 and selected(p,single)[0][-2]=='T'
assert not any(x[-2]=='U' for x in selected(p,single))
assert len(selected(p,'x86_pt_split_flush_bridge'))==1
a=object_words(O/'header-abi.o','M14_C_SINGLE_ABI',5);b=object_words(O/'single-entry.o','M14_RUST_SINGLE_ABI',5);assert a==b==(4,8,8,8,8)
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_SINGLE_ENTRY_LEAF_ABI_FALLBACK_AND_RETAINED_ACTUAL_C_CONSUMER_PARTIAL_LINK_ONLY',actual_ABI_words=5,actual_ABI=a,Rust_entry_one_T=True,Rust_array_callee_U_expected_leaf_only=True,selected_C_entry_excluded=True,fallback_C_entry_preserved=True,actual_C_pt_split_consumer_scalar_U_resolved_by_Rust=True,whole_current_C_mem_TU=False,whole_production_Rust=False,default_kernel_link=False,native=False)
(P/'ACTUAL-ABI-CONSUMER-OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
