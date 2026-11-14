# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import json,struct,pathlib,hashlib
p=pathlib.Path(__file__).resolve().parent
flags={"idle_halt":0,"allow_oversubscribe":0,"time_sharing":1}
old={"resource_set_list":(16,16),"resource_set_lock":(64,64),"runq_reservation_lock":(4,4)}
def elf(name):
 b=(p/"output"/name).read_bytes()
 h=struct.unpack_from("<16sHHIQQQIHHHHHH",b,0)
 assert h[0][:6]==b"\x7fELF\x02\x01" and h[1]==1
 secs=[struct.unpack_from("<IIQQQQIIQQ",b,h[6]+i*h[11]) for i in range(h[12])]
 names=b[secs[h[13]][4]:secs[h[13]][4]+secs[h[13]][5]]
 def string(buf,off):return buf[off:buf.index(0,off)].decode()
 symbols=[]
 for s in secs:
  if s[1]!=2:continue
  st=secs[s[6]];strings=b[st[4]:st[4]+st[5]]
  for off in range(s[4],s[4]+s[5],s[9]):
   no,info,other,ndx,val,size=struct.unpack_from("<IBBHQQ",b,off)
   name=string(strings,no)
   if name not in flags and name not in old:continue
   sym={"name":name,"binding":info>>4,"type":info&15,"visibility":other&3,"section_index":ndx,"value":val,"bytes":size}
   if 0<ndx<len(secs):
    sec=secs[ndx];sym.update(section=string(names,sec[0]),section_type=sec[1],section_flags=sec[2],section_alignment=sec[8])
    sym["initial_hex"]=(bytes(size) if sec[1]==8 else b[sec[4]+val:sec[4]+val+size]).hex()
   symbols.append(sym)
 return symbols
rows={name:elf(name) for name in ["rust-selected.o","c-selected.o","partial-selected.o","rust-fallback.o","c-fallback.o","partial-fallback.o"]}
def defs(name,sym):return [x for x in rows[name] if x["name"]==sym and x["section_index"]!=0]
for sym,value in flags.items():
 for name in ["rust-selected.o","partial-selected.o","c-fallback.o","partial-fallback.o"]:
  found=defs(name,sym);assert len(found)==1,(name,sym,found)
  x=found[0];assert (x["binding"],x["type"],x["visibility"],x["bytes"])==(1,1,0,4),(name,x)
  assert x["section_alignment"]>=4 and x["value"]%4==0 and x["section_flags"]&3==3,(name,x)
  assert x["initial_hex"]==int(value).to_bytes(4,"little",signed=True).hex(),(name,x)
 for name in ["c-selected.o","rust-fallback.o"]:assert not defs(name,sym),(name,sym)
for sym,(size,alignment) in old.items():
 for name in ["rust-selected.o","partial-selected.o"]:
  found=defs(name,sym);assert len(found)==1,(name,sym)
  x=found[0];assert x["bytes"]==size and x["section_alignment"]>=alignment and x["value"]%alignment==0,(name,x)
  assert x["initial_hex"]==bytes(size).hex(),(name,x)
 for name in ["rust-fallback.o","c-selected.o","c-fallback.o"]:assert not defs(name,sym),(name,sym)
for profile in ["selected","fallback"]:
 text=(p/("run-"+profile+".stdout")).read_text()
 assert text=="PASS HOST three actual control flags: defaults0/0/1, address/align/independence, five signed values C-to-Rust and Rust-to-C; 39 checks\n",text
report={"scope":"Functional McKernel OS/apps and Rust/assembly migration only; no security testing.","status":"PASS_HOST_SLICE_OBJECT_INITIALIZER_OWNER_AND_C_RUST_INT_BEHAVIOR","rows":rows,"behavior":{"selected":39,"fallback":39,"scope":"genuine process.h GCC9 / actual candidate Rust full storage module and actual owned ABI excerpts, single-threaded host only"},"default_GCC14":False,"native":False,"whole_file_retirement":False}
(p/"OBJECT-AND-BEHAVIOR-RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
print(report["status"])
