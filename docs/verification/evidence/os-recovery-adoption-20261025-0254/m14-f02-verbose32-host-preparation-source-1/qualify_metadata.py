"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact existing global32/local14 metadata ELF gate; never executes compiled code.
"""
from pathlib import Path
import json,struct,importlib.util,sys,hashlib
P=Path(__file__).resolve().parent;E=P.parent
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1')
spec=importlib.util.spec_from_file_location('existing_f02_elf',E/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=json.loads((N/'EXACT46-SLOT78-MAP.json').read_text());globals=[x for x in rows if not x['local']];locals=[x for x in rows if x['local']]
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def relocs(elf,ndx):
 result={}
 for z in elf.sections:
  if z['type']!=4 or z['info']!=ndx:continue
  for off in range(0,z['size'],z['entsize']):
   at,info,addend=struct.unpack_from('<QQq',elf.data,z['off']+off);assert at not in result
   result[at]=(info&0xffffffff,elf.tables[z['link']][info>>32],addend)
 return result

def metadata(elf,wanted,flags,file,require_retain=False):
 actual=[x for x in elf.symbols if x['kind']==1 and 0<x['ndx']<len(elf.sections) and elf.sections[x['ndx']]['name']=='__verbose'];assert len(actual)==len(wanted),(elf.path,len(actual),len(wanted))
 records=[];pointer_count=0
 for row in wanted:
  found=elf.definitions(row['name']);assert len(found)==1,(elf.path,row['name']);symbol=found[0];z=elf.sections[symbol['ndx']]
  assert symbol['kind']==1 and symbol['bind']==(0 if row['local'] else 1) and symbol['size']==row['bytes']
  assert z['name']=='__verbose' and z['flags']&3==3 and not z['flags']&4 and z['align']==8 and symbol['value']%8==0
  if require_retain:assert z['flags']&0x200000,'Source38 GNU_RETAIN missing'
  rs=relocs(elf,symbol['ndx']);entries=[]
  for i,expected in enumerate(row['entries']):
   at=symbol['value']+i*32;start=z['off']+at-z['addr'];raw=elf.data[start:start+32];strings={}
   for key,offset in [('file',0),('function',8)]:
    kind,target,addend=rs[at+offset];assert kind==1;tz=elf.sections[target['ndx']];position=tz['off']+target['value']+addend-tz['addr'];strings[key]=elf.data[position:].split(b'\0',1)[0].decode();pointer_count+=1
   word=struct.unpack_from('<I',raw,24)[0]
   assert strings==dict(file=file,function=expected['function']),(row['name'],i,strings)
   assert word==expected['line']|(flags<<24) and raw[16:24]==b'\0'*8 and raw[28:32]==b'\0'*4
   assert all(at+offset not in rs for offset in [16,24,28])
   entries.append(dict(strings,line=word&0xffffff,flags=word>>24,fmt=None,tail_padding_zero=True))
  records.append(dict(name=row['name'],binding=symbol['bind'],bytes=symbol['size'],section_flags=z['flags'],alignment=z['align'],entries=entries))
 assert pointer_count==sum(x['slots'] for x in wanted)*2
 return dict(object=ref(elf.path),objects=len(wanted),slots=sum(x['slots'] for x in wanted),R64_file_function_relocations=pointer_count,records=records)

def main():
 out=Path(sys.argv[1]);file=str(N/'postimage/kernel/process.c');report=[]
 abi=m.Elf(out/'abi.o');s=abi.definitions('f02_genuine_bitfield_witness');assert len(s)==1 and s[0]['size']==32;s=s[0];z=abi.sections[s['ndx']];at=z['off']+s['value']-z['addr'];assert abi.data[at:at+32]==b'\0'*24+struct.pack('<I',0x01123456)+b'\0'*4
 for flags in [0,1]:
  rust=m.Elf(out/('rust'+str(flags)+'.o'));c=m.Elf(out/('selected'+str(flags)+'.o'));joint=m.Elf(out/('joint'+str(flags)+'.o'))
  report.append(metadata(rust,globals,flags,file,True));report.append(metadata(c,locals,flags,file));report.append(metadata(joint,rows,flags,file))
  for row in globals:assert not c.definitions(row['name'])
  for row in locals:assert not rust.definitions(row['name'])
  # Each selected Rust record must retain its actual compiler's GNU_RETAIN flag
  # in the partially linked output, including globals in mixed C/Rust registries.
  for row in globals:
   ss=joint.definitions(row['name'])[0];assert joint.sections[ss['ndx']]['flags']&0x200000
  # Registry components are exactly78 entries with32byte stride/8alignment.
  assert sum(z['size'] for z in joint.sections if z['name']=='__verbose')==2496
 fallback=m.Elf(out/'fallback.o');report.append(metadata(fallback,rows,0,file))
 retained=json.loads((P/'RETAINED-CONSUMER-EVIDENCE.json').read_text())
 for key in ['process','Rust']:assert ref(retained[key]['path'])==retained[key]
 assert all(x['references'] for x in retained['global_consumers']) and all(x['references'] for x in retained['registry_consumers'])
 result=dict(scope=__doc__.splitlines()[0],decision='PASS_GLOBAL32_HOST_METADATA_ONLY_LOCAL14_RETAINED',ABI_bitfield_word=0x01123456,records=report,retained_consumers=retained,whole_file_delta=0,native_delta=0,production_default_open=True,registry_final_boundary_native_order_open=True)
 (out/'METADATA-QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print('VERBOSE32 PASS 32globals/64slots;14C-local;ABI32/8;flags0/1;exactFILE/FUNC/LINE/FMT/R64;GNU_RETAIN;retainedconsumers')
if __name__=='__main__':main()
