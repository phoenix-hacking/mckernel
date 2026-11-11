import hashlib,struct
from pathlib import Path
def fact(p):
 h=hashlib.sha256();n=0
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
 return {'path':str(p),'bytes':n,'sha256':h.hexdigest()}
def elf(p):
 raw=p.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[0][:6]==b'\x7fELF\x02\x01' and h[2]==62
 ss=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])];ns=ss[h[13]];st=raw[ns[4]:ns[4]+ns[5]]
 def z(b,n):return b[n:b.index(b'\0',n)].decode('utf-8','surrogateescape')
 sections=[{'index':i,'name':z(st,s[0]),'type':s[1],'flags':s[2],'address':s[3],'offset':s[4],'bytes':s[5],'link':s[6],'info':s[7],'align':s[8],'entry_bytes':s[9]} for i,s in enumerate(ss)]
 syms=[]
 for s in ss:
  if s[1]!=2:continue
  t=ss[s[6]];strings=raw[t[4]:t[4]+t[5]];assert s[9]==24
  for off in range(s[4],s[4]+s[5],24):
   n,info,other,si,value,size=struct.unpack_from('<IBBHQQ',raw,off);syms.append({'index':(off-s[4])//24,'name':z(strings,n),'binding':{0:'LOCAL',1:'GLOBAL',2:'WEAK'}.get(info>>4,str(info>>4)),'type':{0:'NOTYPE',1:'OBJECT',2:'FUNC',3:'SECTION',4:'FILE',6:'TLS'}.get(info&15,str(info&15)),'visibility':other&3,'section_index':si,'value':value,'bytes':size})
 ph=[struct.unpack_from('<IIQQQQQQ',raw,h[5]+i*h[9]) for i in range(h[10])]
 return {'path':str(p),'header':{'type':h[1],'machine':h[2],'entry':h[4]},'sections':sections,'symbols':syms,'program_headers':[{'type':x[0],'flags':x[1],'offset':x[2],'vaddr':x[3],'paddr':x[4],'file_bytes':x[5],'memory_bytes':x[6],'align':x[7]} for x in ph]}
