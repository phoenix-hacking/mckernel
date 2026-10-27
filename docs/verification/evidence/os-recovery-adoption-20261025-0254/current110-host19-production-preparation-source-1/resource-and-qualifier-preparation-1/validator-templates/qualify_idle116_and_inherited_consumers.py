"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Strict idle116 ownership/bytes/RELA and positive current inherited-code comparison.
No changed oracle, compiler, native app, physical observer or execution authority.
"""
from pathlib import Path
import hashlib,json,struct,traceback
D=Path(__file__).resolve().parent
STATIC=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1')
X=json.loads((STATIC/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text())
s=(D/'qualify_clone_pointer_and_warning_suffix.py').read_text()
ctx={'__file__':str(D/'qualify_idle116_and_inherited_consumers.py')}
exec(compile(s[:s.index("\nclone=ns['_reuse_elf_function']")],'same strict actual ET_REL/EXEC readers','exec'),ctx)
Elf=ctx['Elf'];rust=ctx['rust'];process=ctx['process'];B=ctx['B'];P=ctx['P']
final=ctx['final'];data=ctx['data'];sections=ctx['sections'];ref=ctx['ref']
relocs=ctx['ns']['_reuse_elf_owning_relocations'];object_bytes=ctx['ns']['_reuse_elf_object_bytes']
def own(elf,name):
 rows=[v for v in elf.symbols if v['name']==name and v['shndx']!=0]
 assert len(rows)==1,(name,len(rows))
 return rows[0]
def image_reader(path):
 raw=path.read_bytes();h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
 assert h[0][:7]==b'\x7fELF\x02\x01\x01' and h[1:3]==(2,62) and h[11]==64
 sh=[dict(zip(['name_off','type','flags','addr','offset','size','link','info','align','entsize'],struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*64))) for i in range(h[12])]
 tables=[v for v in sh if v['type']==2];assert len(tables)==1 and tables[0]['entsize']==24
 table=tables[0];strings=sh[table['link']];st=raw[strings['offset']:strings['offset']+strings['size']];syms=[]
 for i in range(table['size']//24):
  no,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',raw,table['offset']+i*24)
  syms.append(dict(name=st[no:st.index(b'\0',no)].decode(),bind=info>>4,type=info&15,other=other,shndx=idx,value=value,size=size))
 def symbol(name):
  rows=[v for v in syms if v['name']==name and v['shndx']!=0];assert len(rows)==1,(name,len(rows));return rows[0]
 def payload(sym):
  sec=sh[sym['shndx']];offset=sym['value']-sec['addr'];assert 0<=offset and offset+sym['size']<=sec['size']
  return bytes(sym['size']) if sec['type']==8 else raw[sec['offset']+offset:sec['offset']+offset+sym['size']]
 return symbol,payload
def patched_final(elf,sym,symbol,payload):
 raw=bytearray(object_bytes(elf,sym));rows=relocs(elf,sym);last=-8;records=[]
 for r in sorted(rows,key=lambda v:v['offset']):
  assert r['type']==1 and r['offset']>=last+8 and r['offset']+8<=len(raw),'only exact nonoverlapping R_X86_64_64 patches'
  name=r['target']['name'];assert name,'no anonymous/section target substitution'
  target=symbol(name);assert target['shndx']!=0
  struct.pack_into('<Q',raw,r['offset'],(target['value']+r['addend'])&((1<<64)-1));last=r['offset']
  records.append(dict(offset=r['offset'],type=r['type'],addend=r['addend'],target=name,final_target=target))
 f=symbol(sym['name']);assert f['type']==2 and f['size']==sym['size'] and payload(f)==bytes(raw)
 return records
report=dict(scope=__doc__.splitlines()[0],status='IN_PROGRESS',native_acceptance=False,whole_file_retirement=False)
try:
 for key in ['current110_baseline_Rust','current110_baseline_image','current110_baseline_process']:
  assert ref(X[key]['path'])==X[key]
 oldrust=Elf(Path(X['current110_baseline_Rust']['path']));oldprocess=Elf(Path(X['current110_baseline_process']['path']))
 oldfinal,olddata=image_reader(Path(X['current110_baseline_image']['path']))
 for row in P['cohort_source_bindings']:assert ref(row['postimage']['path'])==row['postimage']
 C=[(r['link_token'],Elf(B/r['build_relative'] if r['replace'] else Path(r['source']['path']))) for r in P['inputs']['objects'] if r['link_token']!='rust/mckernel_rust.o']
 witness=X['idle116'];assert ref(witness['HOST']['path'])==witness['HOST'];assert ref(witness['HOST_Rust_object']['path'])==witness['HOST_Rust_object']
 host=Elf(Path(witness['HOST_Rust_object']['path']));tables={}
 for row in witness['tables']:
  name=row['name'];size=row['bytes'];align=row['minimum_alignment'];expected=bytes.fromhex(row['bytes_hex'])
  a=own(rust,name);sec=rust.sections[a['shndx']]
  assert (a['bind'],a['type'],a['size'])==(1,1,size) and sec['align']>=align and a['value']%align==0
  assert rust.raw[rust.table['offset']+a['index']*24+5]==0
  assert sec['flags']&2 and not sec['flags']&5 and object_bytes(rust,a)==expected
  assert not relocs(rust,a),'integer descriptor words cannot hide pointer relocations'
  assert object_bytes(host,own(host,name))==expected and object_bytes(oldprocess,own(oldprocess,name))==expected
  assert not [(key,v) for key,elf in C for v in elf.symbols if v['name']==name and v['shndx']!=0]
  f=final(name);fs=sections[f['shndx']]
  assert (f['bind'],f['type'],f['other'],f['size'])==(1,1,0,size) and f['value']%align==0
  assert fs['flags']&2 and not fs['flags']&5 and data(f)==expected
  tables[name]=dict(Rust=a,final=f,size=size,alignment=align,bytes_hex=expected.hex(),unique_Rust_provider=True,hidden_pointer_RELA=False)
 # Genuine ABI definitions and pinned C assertions are unchanged inputs, not mocks.
 assert ref(witness['ABI_assertions']['path'])==witness['ABI_assertions']
 abi=Path(P['inputs']['source_directory_exports'][0]['host_path'])/'abi.rs'
 sched=abi.parent/'sched_helpers.rs'
 oldmap=json.loads(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/qualified-current26eb-next-default-source-1/RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json').read_text())
 for name in ['abi.rs','sched_helpers.rs']:
  baseline=next(r['snapshot'] for r in oldmap['files'] if r['relative']==name)
  assert ref(abi.parent/name)['sha256']==baseline['sha256']
 report['idle116']=tables
 # Reread all current final instruction bytes. Carry no old tuple/address proof.
 names=sorted(set(X['HOST13_production_consumer_map'].values())|{'set_timer','timer_set_timer_body_result'})
 comparisons=[]
 for name in names:
  before=own(oldrust,name);after=own(rust,name)
  assert before['type']==after['type']==2 and before['size']==after['size']
  ba=bytearray(object_bytes(oldrust,before));aa=bytearray(object_bytes(rust,after))
  def shape(elf,fn):return [(r['offset'],r['type'],r['addend'],r['target']['name']) for r in relocs(elf,fn)]
  bs=shape(oldrust,before);ns=shape(rust,after);assert bs==ns,(name,'relocation shape/target identity changed')
  for off,kind,addend,target in bs:
   assert kind==1 and off+8<=len(ba)
   ba[off:off+8]=bytes(8);aa[off:off+8]=bytes(8)
  assert ba==aa,(name,'actual consumer instructions changed outside exact R64 addresses')
  oldpatches=patched_final(oldrust,before,oldfinal,olddata)
  newpatches=patched_final(rust,after,final,data)
  comparisons.append(dict(consumer=name,old_symbol=before,current_symbol=after,exact_nonrelocated_code=True,
   old_final_R64_targets=oldpatches,current_final_R64_targets=newpatches))
 report['inherited13_and_timer_current_instruction_proof']=comparisons
 report['current_final_relocation_targets_checked']=sum(len(r['current_final_R64_targets']) for r in comparisons)
 report['timer_scope']='All15 readonly words remain checked by retained timer gate; identical current consumer instructions preserve prior nine consumed fields. Six other words remain data-only.'
 entry=own(rust,'process_idle_entry');assert entry['type']==2
 refs=relocs(rust,entry);entrypatches=patched_final(rust,entry,final,data)
 bound={r['target']['name'] for r in refs}&set(tables)
 report['idle_current_consumer']=dict(consumer='process_idle_entry',symbol=entry,current_final_R64_targets=entrypatches,
  exact_direct_table_targets=sorted(bound),direct_table_bindings_complete=bound==set(tables),
  missing_direct_table_bindings=sorted(set(tables)-bound),folded_argument_waiver=False)
 report['status']='PASS_IDLE116_READONLY_ABI_UNIQUE_ORIGIN_AND_CURRENT_INHERITED_CONSUMER_BYTES'
 if bound!=set(tables):report['idle_final_consumer_open']='Independent exact current final folded pointer/argument proof required for missing direct table target; source/HOST data alone is insufficient.'
except BaseException as error:
 report.update(status='FAIL_FIRST_IDLE116_OR_INHERITED_CONSUMER_PROOF_PRESERVED',first_failure=repr(error),traceback=traceback.format_exc())
(D/'IDLE116-AND-INHERITED-CONSUMERS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],first_failure=report.get('first_failure'),idle_consumer=report.get('idle_current_consumer',{}).get('direct_table_bindings_complete'))))
if report['status'].startswith('FAIL'):raise SystemExit(1)
