"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Expert-specified retained ELF symbol/section/relocation observer; no compilation.
"""
from pathlib import Path
import hashlib,json,struct,os
D=Path(__file__).resolve().parent;P=D.parent;A=P/'actual-attempt-1'
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
stop=P/'ACTUAL-PRODUCTION-OBSERVER-STOP-RECEIPT.json';assert sha(stop)=='90239bcb458a6b716b1bc8370c8b2b36aa56b3434fbd4e6e3b9a63b0dcd24986';j=json.loads(stop.read_bytes())
R=P/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json';C=P/'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.GRANTED.json';assert sha(R)=='061bf24a099120c5995be23ded373392b56cd6c9a295ba6569a9355690d07e45';assert sha(C)=='7ea72905534b5fd4a7772e05d8510cea800ab9c7e6147836b6720e22a2d3a4ce';r=json.loads(R.read_bytes());c=json.loads(C.read_bytes())
assert os.sched_getaffinity(0)=={7}
def unchanged(row):
 s=Path(row['path']).stat()
 for k,v in [('device',s.st_dev),('inode',s.st_ino),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('ctime_ns',s.st_ctime_ns),('uid',s.st_uid),('gid',s.st_gid),('nlink',s.st_nlink)]:assert row[k]==v,(k,row['path'])
art=j['artifacts_durable_hashed_once_before_observers']
for row in art.values():unchanged(row)
for row in r['source_inputs'].values():assert sha(Path(row['private']['path']))==row['private']['sha256']
for row in [c['private_memory_source'],c['ABI_witness'],c['arch_memory_header']]:assert sha(Path(row['path']))==row['sha256']
assert len(j['results'])==11
for rr in j['results']:
 x=rr['join'];assert x['returncode']==0 and x['direct_child_joined'] and x['group_absent'] and x['closed_streams'] and x['error'] is None and x['retirement_error'] is None
 for capture in x['captures'].values():assert sha(Path(capture['path']))==capture['sha256']
raw=Path(art['memory.c.o']['path']).read_bytes();eh=struct.unpack_from('<16sHHIQQQIHHHHHH',raw);assert eh[0][:6]==b'\x7fELF\x02\x01' and eh[1]==1 and eh[2]==62 and eh[11]==64
shoff,shnum,shstr=eh[6],eh[12],eh[13]
sections=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*64))) for i in range(shnum)]
def payload(sec):return raw[sec['offset']:sec['offset']+sec['size']]
def string(tab,off):return tab[off:tab.index(b'\0',off)].decode()
strnames=payload(sections[shstr])
for i,s in enumerate(sections):s.update(index=i,name=string(strnames,s['name_off']))
symtabs=[s for s in sections if s['type']==2];assert len(symtabs)==1;syms_sec=symtabs[0];assert syms_sec['entsize']==24;strings=payload(sections[syms_sec['link']]);syms=[]
for i in range(syms_sec['size']//24):
 name,info,other,shndx,value,size=struct.unpack_from('<IBBHQQ',raw,syms_sec['offset']+i*24);syms.append(dict(index=i,name=string(strings,name),bind=info>>4,type=info&15,shndx=shndx,value=value,size=size,other=other))
def symbol(name):
 found=[s for s in syms if s['name']==name];assert len(found)==1,(name,found);return found[0]
text=[s for s in sections if s['name']=='.text'];assert len(text)==1;text=text[0]
child=symbol('x86_clear_range_walk_l3_bridge');assert child['bind']==0 and child['type']==2 and child['shndx']==text['index'] and child['value']==0x9c0
proof={}
for name,shindex,secname,relname in [('x86_clear_range_l4_callback',11,'.data.rel.ro','.rela.data.rel.ro'),('x86_clear_range_l3_callback',13,'.data.rel.ro.local','.rela.data.rel.ro.local')]:
 sym=symbol(name);assert sym['bind']==1 and sym['type']==1 and sym['size']==8 and sym['shndx']==shindex and sym['value']==0
 sec=sections[sym['shndx']];assert sec['name']==secname and sec['align']==8 and sym['value']+sym['size']<=sec['size']
 relsecs=[s for s in sections if s['type']==4 and s['info']==sym['shndx']];assert len(relsecs)==1;rs=relsecs[0];assert rs['name']==relname and rs['link']==syms_sec['index'] and rs['entsize']==24
 found=[]
 for n in range(rs['size']//24):
  off,info,addend=struct.unpack_from('<QQq',raw,rs['offset']+n*24)
  if off==sym['value']:found.append(dict(offset=off,type=info&0xffffffff,target=syms[info>>32],addend=addend))
 assert len(found)==1;rel=found[0];assert rel['type']==1
 target=rel['target']
 if name=='x86_clear_range_l4_callback':assert target['name']=='x86_clear_range_l4_body' and target['bind']==1 and target['shndx']==0 and rel['addend']==0
 else:assert target['type']==3 and target['shndx']==text['index'] and target['value']==0 and rel['addend']==child['value']
 proof[name]=dict(symbol=sym,section=sec,relocation_section=rs,relocation=rel)
def rows(t,n):return [l.split() for l in t.splitlines() if l.split()[-1:]==[n]]
nm=(A/'01-production-Rust-NM/stdout').read_text();part=(A/'10-partial-symbols/stdout').read_text();u={l.split()[-1] for l in nm.splitlines() if l.split()[-2:-1]==['U']};assert u==set(r['expected_U']) and len(u)==577
for n in r['expected_all_prior_T']+r['expected_T_added']:
 row=rows(nm,n);assert len(row)==1 and row[0][-2]=='T',n
for n in c['expected_partial_unique_Rust_T']:
 row=rows(part,n);assert len(row)==1 and row[0][-2]=='T',n
assert len(c['expected_partial_unique_Rust_T'])==36
for row in art.values():unchanged(row)
result=dict(scope=__doc__,status='PASS_RETAINED_SECTION_AWARE_TWO_CALLBACK_RELOCATIONS_AND_ALL_PRIOR_PRODUCTION_CHECKS',proof=proof,retained_private_C_child_symbol=child,actual_Rust_U_exact_count=577,prior_T_preserved=True,partial_Rust_unique_T=36,all11_actual_command_joins_preserved=True,source78_private_inputs_and_ABI_unchanged=True,objects_stat_unchanged_no_rehash=art,original_stop_receipt_sha256=sha(stop),original_failed_driver_sha256=sha(P/'run_actual_once.py'),observer_source_sha256=sha(Path(__file__)),new_compiler_or_link_or_probe_invocations=0,default_image_link_native=False,remaining_C_callback_chain_debt=c['remaining_C_debt'])
print(json.dumps(result,sort_keys=True))
