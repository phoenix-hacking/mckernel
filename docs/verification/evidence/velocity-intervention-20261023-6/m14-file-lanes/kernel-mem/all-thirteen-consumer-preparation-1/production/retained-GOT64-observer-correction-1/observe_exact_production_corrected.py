"""Functional OS/Rust only; no security testing. Bounded all13 retained ELF observer."""
import struct
from collections import Counter

def nm_sets(path):
 rows=[]
 for line in path.read_text().splitlines():
  f=line.split()
  if len(f)>=2:rows.append((f[-2],f[-1]))
 return Counter(name for typ,name in rows if typ=='T'),set(name for typ,name in rows if typ=='U'),rows

def allocated_callback_relocations(path,names):
 # ELF64 little-endian ET_REL x86_64; symbol index and relocation target-section
 # identity are authoritative, never equal offsets merged across sections.
 before=path.stat();b=path.read_bytes();assert len(b)==before.st_size and len(b)<=32<<20
 assert b[:6]==b'\x7fELF\x02\x01'
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',b,0);assert h[1:3]==(1,62)
 off,size,count,strings=h[6],h[11],h[12],h[13];assert size==64 and off+size*count<=len(b)
 sections=[struct.unpack_from('<IIQQQQIIQQ',b,off+i*size) for i in range(count)]
 def content(s):assert s[4]+s[5]<=len(b);return b[s[4]:s[4]+s[5]]
 shstr=content(sections[strings])
 def text(s,i):assert i<len(s);return s[i:s.index(0,i)].decode()
 proof=[]
 for i,s in enumerate(sections):
  if s[1]!=4:continue
  assert s[7]<count and s[6]<count and s[9]==24
  target=sections[s[7]]
  if not target[2]&2:continue
  table=sections[s[6]];assert table[1]==2 and table[9]==24
  symbols=content(table);strtab=content(sections[table[6]])
  for k in range(0,s[5],24):
   where,info,addend=struct.unpack_from('<QQq',b,s[4]+k);index,typ=info>>32,info&0xffffffff
   assert (index+1)*24<=len(symbols)
   sym=struct.unpack_from('<IBBHQQ',symbols,index*24);name=text(strtab,sym[0])
   if name not in names:continue
   assert where<target[5]
   proof.append({'symbol':name,'symbol_binding':sym[1]>>4,'symbol_type':sym[1]&15,'symbol_shndx':sym[3],'relocation_section_index':i,'relocation_section':text(shstr,s[0]),'target_section_index':s[7],'target_section':text(shstr,target[0]),'target_allocated':True,'offset':where,'type':typ,'addend':addend})
 selected=[x for x in proof if x['symbol']=='mem_tlb_atomic_dec_bridge']
 assert len(selected)==1,selected
 assert selected[0]=={'symbol':'mem_tlb_atomic_dec_bridge','symbol_binding':1,'symbol_type':0,'symbol_shndx':0,'relocation_section_index':2,'relocation_section':'.rela.text','target_section_index':1,'target_section':'.text','target_allocated':True,'offset':18051,'type':27,'addend':0},selected
 after=path.stat();assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
 return {'ELF':'ELF64 little-endian ET_REL x86_64','allocated_callback_relocations':proof,'handler_real_completion_import_exact_R_X86_64_GOT64_addend0':selected,'object_stat_unchanged':True,'object_rehashed':False}
