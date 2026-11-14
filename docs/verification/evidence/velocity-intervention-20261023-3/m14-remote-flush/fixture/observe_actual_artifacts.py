# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# ELF metadata/source observer only; never executes compiled target callbacks.
from pathlib import Path
import struct,json
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
def symbols(path):
 raw=path.read_bytes();off=struct.unpack_from('<Q',raw,40)[0];ents,n=struct.unpack_from('<HH',raw,58);secs=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*ents) for i in range(n)];rows=[]
 for sec in secs:
  if sec[1]!=2:continue
  strings=secs[sec[6]];tab=raw[strings[4]:strings[4]+strings[5]]
  for at in range(sec[4],sec[4]+sec[5],24):
   ni,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,at);end=tab.find(bytes([0]),ni);assert end>=ni
   rows.append((tab[ni:end].decode(),info>>4,info&15,idx,value,size))
 return rows
def named(rows,name):return [r for r in rows if r[0]==name]
cm=object_words(O/'header-abi.o','M14_C_TLB_LAYOUT',15);rm=object_words(O/'rust-entry.o','M14_RUST_TLB_LAYOUT',15);assert cm==rm,(cm,rm);geometry=object_words(O/'header-abi.o','M14_C_TLB_GEOMETRY',3,4)
r=symbols(O/'rust-entry.o');c=symbols(O/'selected-c.o');f=symbols(O/'fallback-c.o');p=symbols(O/'partial.o')
entry='remote_flush_tlb_array_cpumask';rr=named(r,entry);assert len(rr)==1 and rr[0][1:3]==(1,2) and rr[0][3]!=0
assert len(named(c,entry))==1 and named(c,entry)[0][3]==0
assert len(named(f,entry))==1 and named(f,entry)[0][3]!=0
assert len(named(p,entry))==1 and named(p,entry)[0][3]!=0
names=['mem_tlb_'+n+'_bridge' for n in ['rdtsc','current_cpu','get_vector','interrupt_cpu','noirq_lock','noirq_unlock','atomic_set','atomic_inc','atomic_read','flush_single','flush_all','pause']]
for name in names:
 assert len(named(r,name))==1 and named(r,name)[0][3]==0,name
 assert len(named(c,name))==1 and named(c,name)[0][1:3]==(1,2) and named(c,name)[0][3]!=0,name
 # Unused fallback-only bridges may be optimized away; those retained are local.
 assert all(row[1]==0 for row in named(f,name)),name
for name in ['mem_remote_tlb_geometry','tlb_flush_vector']:
 assert len(named(r,name))==1 and named(r,name)[0][3]==0,name
 assert len(named(c,name))==1 and named(c,name)[0][3]!=0,name
assert object_words(O/'selected-c.o','mem_remote_tlb_geometry',3,4)==geometry
assert named(c,'tlb_flush_vector')[0][5]==geometry[0]*cm[6]
assert len(named(r,'mem_remote_flush_tlb_array_body_result'))==1 and named(r,'mem_remote_flush_tlb_array_body_result')[0][3]==0
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_FOCUSED_ENTRY_ABI_HEADER_SELECTION_AND_PARTIAL_LINK_ONLY',layout_words=15,geometry_words=3,actual_header_geometry=geometry,actual_layout=cm,callback_identities=12,Rust_entry_one_definition=True,selected_C_no_entry_definition=True,fallback_C_entry_preserved=True,partial_link_one_Rust_entry=True,underlying_Rust_body_algorithm_executed=False,whole_C_TU=False,production_fullcrate=False,default_kernel_link=False,native=False)
(P/'ACTUAL-ABI-SELECTION-OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
