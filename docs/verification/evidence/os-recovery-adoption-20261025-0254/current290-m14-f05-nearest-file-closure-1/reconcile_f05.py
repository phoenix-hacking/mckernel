"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only selected F05 source/object/link reconciliation; grants no execution.
"""
import hashlib,json,pathlib,re,struct,subprocess
E=pathlib.Path(__file__).resolve().parent
D=E.parent

def ref(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
class Elf:
 def __init__(self,p):
  self.p=pathlib.Path(p);self.b=self.p.read_bytes();assert self.b[:6]==b'\x7fELF\x02\x01'
  h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.b);self.sections=[]
  for i in range(h[12]):
   z=struct.unpack_from('<IIQQQQIIQQ',self.b,h[6]+i*h[11]);self.sections.append(dict(index=i,nameoff=z[0],type=z[1],flags=z[2],addr=z[3],offset=z[4],size=z[5],link=z[6],info=z[7],align=z[8],entsize=z[9]))
  names=self.sections[h[13]];ns=self.b[names['offset']:names['offset']+names['size']]
  for s in self.sections:s['name']=ns[s['nameoff']:].split(b'\0')[0].decode()
  self.syms=[]
  for s in self.sections:
   if s['type']!=2:continue
   st=self.sections[s['link']];raw=self.b[st['offset']:st['offset']+st['size']]
   for i in range(0,s['size'],s['entsize']):
    no,info,other,shndx,value,size=struct.unpack_from('<IBBHQQ',self.b,s['offset']+i)
    self.syms.append(dict(name=raw[no:].split(b'\0')[0].decode(),type=info&15,bind=info>>4,shndx=shndx,value=value,size=size))
 def one(self,name):
  a=[s for s in self.syms if s['name']==name and s['shndx']];assert len(a)==1,(name,len(a));return a[0]
 def data(self,s):
  sec=self.sections[s['shndx']]
  if sec['type']==8:return bytes(s['size'])
  off=sec['offset']+s['value']-(sec['addr'] if sec['addr'] else 0);return self.b[off:off+s['size']]
link=json.loads((D/'current290-actual-build3-qualification-source-1/IMAGE-LINK-RESULT.json').read_text())
mem=next(x['actual_original'] for x in link['nine_RO_original_input_resolution'] if x['container'].endswith('/memory.c.o'))
assert ref(mem['path'])==mem
source=pathlib.Path(json.loads((D/'current290-unprivileged-build-only-source-1/PROFILE.SOURCE-ONLY.json').read_text())['inputs']['source6153'])
c=Elf(mem['path']); r=Elf(D/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/output/build/kernel/rust/mckernel_rust.o'); img=Elf(D/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/output/build/kernel/mckernel.img')
assert ref(img.p)['sha256']=='e6a82f87461e3bbf262c1a1eb3bb47398c5b820bb3c974c8f22b3577dfe51da4'
alloc=[s for s in c.sections if s['flags']&2 and s['size']]
assert [(s['name'],s['size']) for s in alloc]==[('.note.gnu.property',48)]
assert not [s for s in c.syms if s['type'] in (1,2) or (s['name'] and s['shndx']==0)]
assert not [s for s in c.sections if s['type'] in (4,9) and c.sections[s['info']]['flags']&2]
providers=[];sources=[]
for f in ['x86_memory_helpers.rs','x86_memory_loggers.rs','x86_memory_logger_bridges.rs']:
 p=source/'kernel/rust'/f;sources.append(ref(p))
 names=re.findall(r'#\[no_mangle\]\s*(?:#\[[^\n]*\]\s*)*pub\s+(?:unsafe\s+)?extern\s+"C"\s+fn\s+(\w+)',p.read_text())
 for name in names:
  rs=r.one(name); im=img.one(name);assert rs['type']==im['type']==2
  providers.append(dict(name=name,rust_size=rs['size'],image_value=hex(im['value']),image_size=im['size']))
assert len(providers)==343 and len({s['name'] for s in providers})==343
pairs={'x86_memory_last_page_slot':'OWNED_LAST_PAGE','x86_memory_init_pt_slot':'OWNED_INIT_PT','x86_memory_boot_pt_slot':'OWNED_BOOT_PT','x86_memory_init_pt_loaded_slot':'OWNED_INIT_PT_LOADED','x86_memory_init_pt_lock_address':'OWNED_INIT_PT_LOCK','x86_memory_fixed_virt_slot':'OWNED_FIXED_VIRT','x86_clear_l3_use_1gb_page':'OWNED_USE_1GB_PAGE'}
storage=[]
for slot,tail in pairs.items():
 matches=[s for s in r.syms if s['name'].endswith(tail) and 'owned_memory_data' in s['name']];assert len(matches)==1
 own=matches[0];image_own=img.one(own['name']);si=img.one(slot);sr=r.one(slot)
 assert own['type']==image_own['type']==1 and r.data(own)==bytes(own['size']) and img.data(image_own)==bytes(own['size'])
 assert sr['size']==si['size']==8 and struct.unpack('<Q',img.data(si))[0]==image_own['value']
 storage.append(dict(slot=slot,owner=own['name'],owner_size=own['size'],final_pointer=hex(image_own['value']),initial_zero=True))
attr=img.one('attr_mask');assert struct.unpack('<Q',img.data(attr))[0]==0x807
report=dict(scope=__doc__.strip(),status='PASS_SELECTED_F05_CURRENT290_SOURCE_DEFAULT_OBJECT_LINK_AND_SEVEN_FINAL_POINTERS_ONLY',memory_source=ref(source/'arch/x86_64/kernel/memory.c'),memory_object=mem,rust_object=ref(r.p),image=ref(img.p),c_runtime_functions=0,c_runtime_objects=0,c_allocated_relocations=0,c_allocated_metadata=alloc,source_modules=sources,rust_function_providers=providers,function_provider_count=len(providers),seven_owned_storage=storage,attr_mask_initial='0x807',native_startup_reuse='CURRENT290-NATIVE2-INDEPENDENT-STARTUP-CASE-ACCEPTANCE.json',whole_file_acceptance=False,remaining_gate='Matching native memory mapping/unmapping/protection/usercopy and supported large-page/TLB/failure-ownership evidence plus independent whole-file acceptance; startup does not exercise all obligations.')
(E/'SELECTED-F05-RECONCILIATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['status','c_runtime_functions','c_runtime_objects','c_allocated_relocations','function_provider_count','whole_file_acceptance']}))
