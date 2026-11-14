import struct,json,hashlib,sys
from pathlib import Path
B=Path(sys.argv[1]); out=Path(sys.argv[2]);p=B/'m14-abi-codegen-candidate-1/POSTFLIGHT.SOURCE-ONLY.json';pb=p.read_bytes();assert hashlib.sha256(pb).hexdigest()=='93cd283f8b987f1a9c46177d8eb2fe0de63a2aa45242d29f3cc013a61929c7e0';post=json.loads(pb)
p=Path(post['artifacts']['rust_object']);raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='4ae88ea95ad229725334df27fe4bd0e10c4dbe04ca5109212e578bed4e18da6e' and len(raw)==18948144
assert raw[:6]==b'\x7fELF\x02\x01';h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert h[1]==1 and h[2]==62
sh=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
def data(i):s=sh[i];return raw[s[4]:s[4]+s[5]]
def string(t,o):return t[o:t.index(b'\0',o)].decode('utf-8','replace')
st=data(h[13]);names=[string(st,s[0]) for s in sh];tabs={};symbols=[]
for i,s in enumerate(sh):
 if s[1] in (2,11):
  t=data(s[6]);rows=[]
  for o in range(0,s[5],s[9]):
   n,info,other,sec,val,size=struct.unpack_from('<IBBHQQ',raw,s[4]+o);x=dict(name=string(t,n),type=info&15,binding=info>>4,section=sec,value=val,size=size,index=len(rows),table=i);rows.append(x);symbols.append(x)
  tabs[i]=rows
rels={}
for i,s in enumerate(sh):
 if s[1] in (4,9):
  rows=[]
  for o in range(0,s[5],s[9]):
   if s[1]==4:off,info,add=struct.unpack_from('<QQq',raw,s[4]+o)
   else:off,info=struct.unpack_from('<QQ',raw,s[4]+o);add=None
   sy=tabs[s[6]][info>>32];typ=info&0xffffffff;rows.append(dict(offset=off,type=typ,width={1:8,2:4,4:4,10:4,11:4,24:8}.get(typ,'UNKNOWN'),addend=add,symbol=sy))
  rels[i]=rows
def components(name):
 if not name.startswith('_ZN') or not name.endswith('E'):return None
 pos=3;result=[]
 while pos<len(name)-1:
  end=pos
  while end<len(name)-1 and name[end].isdigit():end+=1
  if end==pos:return None
  size=int(name[pos:end]);part=name[end:end+size]
  if len(part)!=size:return None
  result.append(part);pos=end+size
 return result if pos==len(name)-1 else None
def progress(**fields):
 (out/'PROGRESS.json').write_text(json.dumps(dict(recorder='/root/root_history_audit',grant='ROOT_FIXED9_ELF_2_20261030',resolved=globals().get('refs',[]),**fields),indent=2)+'\n')
def unique(f):
 candidates=[s for s in symbols if f in s['name'] and s['section'] not in (0,65521,65522)]
 rows=[s for s in candidates if f in (components(s['name']) or [])]
 progress(next_identifier=f,raw_candidates=candidates,exact_matches=rows)
 assert len(rows)==1,(f,len(rows),[x['name'] for x in candidates]);return rows[0]
def section_relocs(sec):return [dict(section_index=i,section_name=names[i],entries=rows) for i,rows in rels.items() if sh[i][7]==sec]
refs=[]
for spec in post['codegen_symbol_postflight']['required_reference_statics']:
 s=unique(spec['static']);progress(next_spec=spec,reference=s);assert s['size']==8;rr=[dict(relocation_section=x['section_name'],**r) for x in section_relocs(s['section']) for r in x['entries'] if s['value']<=r['offset']<s['value']+8];assert len(rr)==1,(spec,rr);r=rr[0];sy=r['symbol'];assert r['type']==1 and r['addend'] is not None
 progress(next_spec=spec,reference=s,actual_relocations=rr);sec=sy['section'];off=sy['value']+r['addend'];aliases=[x for x in symbols if x['type']==2 and x['section']==sec and x['value']==off and x['size']>0];assert aliases,(spec,r)
 refs.append(dict(spec=spec,reference=s,relocation=r,expected_target_component_matches=[x for x in aliases if spec['target'] in (components(x['name']) or [])],target_module_components=[components(x['name']) for x in aliases],resolved_section=names[sec],resolved_offset=off,function_aliases=aliases,machine_body_key=[sec,off],attribution='Actual relocation resolves to listed function entry; intended-name alias availability reported literally. Prototype is source contract, not machine-code proof.'))
progress(stage='nine_refs_resolved');arrays=[]
for spec in post['abi_pairs']:
 s=unique(spec['rust_symbol_fragment']);assert s['size']==8*spec['word_count'];rs=section_relocs(s['section']);arrays.append(dict(spec=spec,symbol=s,section_name=names[s['section']],section_relocations=rs,total_section_relocations=sum(len(x['entries']) for x in rs),overlapping_array_relocations=[r for x in rs for r in x['entries'] if s['value']<=r['offset']<s['value']+s['size']],unknown_or_wider_width=any(r['width']=='UNKNOWN' or r['width']>8 for x in rs for r in x['entries'])))
result=dict(recorder='/root/root_history_audit',grant='ROOT_FIXED9_ELF_2_20261030',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',artifact=dict(path=str(p),sha256=digest,bytes=len(raw)),postflight_sha256=hashlib.sha256(pb).hexdigest(),refs=refs,unique_machine_entry_count=len({tuple(x['machine_body_key']) for x in refs}),abi_arrays=arrays,undefined_symbols=[s['name'] for s in symbols if s['section']==0 and s['name']],limitations=['No emitted code called; no production link, runtime or C retirement claim.','Function names/types cannot independently prove ABI prototypes.','Unique machine entries counted by section and offset; no cross-section identical-byte folding inference.'])
(out/'EXTRACTION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(ref_count=len(refs),unique_machine_entry_count=result['unique_machine_entry_count'],array_section_relocations=[a['total_section_relocations'] for a in arrays])))
