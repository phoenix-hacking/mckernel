"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite readback of three retained straight-line SysV configuration forwarders.
"""
from pathlib import Path
import json,re,struct
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'inspect_folded.py')};exec(compile((D/'inspect_folded.py').read_text().split('\nconfigmap=')[0],'<retained ELF readers only>','exec'),ns);globals().update({k:v for k,v in ns.items() if k!='__file__'})
e=new

def token(r):
 t=r['target'];pos=t['value']+r['addend']
 if not t['shndx']:return ['UNDEFINED',t['name'],r['addend']]
 z=e.sections[t['shndx']]
 if z['name']=='.lrodata.str1.1':
  assert z['flags']&0x32==0x32 and not z['flags']&5;start=z['offset']+pos;lit=e.raw[start:e.raw.index(b'\0',start)+1];return ['EXACT_READONLY_NUL_STRING',lit.hex()]
 owners=[s for s in e.symbols if s['type'] in (1,2) and s['shndx']==t['shndx'] and s['value']<=pos<s['value']+s['size']]
 assert owners,(r,'no positive owner')
 return ['INPUT_DEFINED_ADDRESS',t['shndx'],pos,sorted(s['name'] for s in owners)]
def equivalent(a,b):
 if isinstance(a,list) and isinstance(b,list) and a[:1]==b[:1]==['INPUT_DEFINED_ADDRESS']:return a[:3]==b[:3]
 return a==b

def function_token(name):
 s=own(e,name);return ['INPUT_DEFINED_ADDRESS',s['shndx'],s['value'],[name]]
def instructions(name):
 f=D/('section-newHOST--'+name+'.objdump');out=[]
 for line in f.read_text().splitlines():
  cols=line.split('\t')
  if len(cols)>=3 and re.fullmatch(r'\s*[0-9a-f]+:',cols[0]):out.append((int(cols[0].strip()[:-1],16),bytes.fromhex(cols[1]),cols[2].strip()))
 assert out and sum(len(b) for _,b,_ in out)==own(e,name)['size']
 return out
aliases={'eax':'rax','ebx':'rbx','ecx':'rcx','edx':'rdx','esi':'rsi','edi':'rdi','ebp':'rbp','esp':'rsp'}
def reg(s):
 s=s.lstrip('%');return aliases.get(s,s[:-1] if re.fullmatch(r'r\d+d',s) else s)
def read_call(name,body,total):
 regs={r:['ARG',i] for i,r in enumerate(['rdi','rsi','rdx','rcx','r8','r9'],1)};regs.update({r:['ENTRY_SAVED',r] for r in ['rbp','rax','rbx','r10','r11','r12','r13','r14','r15']});sp=0;memory={8:['ARG',7]};rr={r['offset']:r for r in rels(e,own(e,name))};proof=[];used=set()
 def val(text):
  if text.startswith('$'):return int(text[1:],16)&((1<<64)-1)
  if text.startswith('%'):return ['STACK_ADDRESS',sp] if text=='%rsp' else regs[reg(text)]
  m=re.fullmatch(r'(0x[0-9a-f]+)\(%rbp\)',text);assert m,(name,text)
  assert regs['rbp'][0]=='STACK_ADDRESS';return memory[regs['rbp'][1]+int(m[1],16)]
 for off,raw,text in instructions(name):
  op,_,args=text.partition(' ');args=args.strip()
  if op=='push':sp-=8;memory[sp]=val(args) if args!='%rsp' else ['STACK_ADDRESS',sp+8]
  elif op in ('mov','movabs'):
   src,dest=args.split(',');v=val(src)
   if off+2 in rr:
    assert op=='movabs' and len(raw)==10 and raw[0] in (0x48,0x49) and 0xb8<=raw[1]<=0xbf
    v=token(rr[off+2]);used.add(off+2)
   if isinstance(v,int) and (dest in ['%eax','%ebx','%ecx','%edx','%esi','%edi'] or re.fullmatch(r'%r\d+d',dest)):v&=0xffffffff
   regs[reg(dest)]=v
  elif op=='call':
   assert args.startswith('*%') and equivalent(regs[reg(args[1:])],function_token(body)),(name,'callee',regs[reg(args[1:])])
   actual=[regs[r] for r in ['rdi','rsi','rdx','rcx','r8','r9']]+[memory[sp+i*8] for i in range(total-6)]
   assert used==set(rr);return actual,proof+[dict(offset=off,instruction=text,callee=body,SysV_arguments=actual)]
  else:raise AssertionError((name,op,'outside finite straight-line vocabulary'))
  proof.append(dict(offset=off,bytes_hex=raw.hex(),instruction=text))
 raise AssertionError('no actual call')

def fields(config,defs):
 s=own(e,config);raw=data(e,s);rr={r['offset']:r for r in rels(e,s)};result=[]
 for name,offset,kind in defs:
  if kind in ('ptr','fn'):v=token(rr[offset])
  else:v=struct.unpack_from('<'+kind,raw,offset)[0]&((1<<64)-1)
  result.append(dict(field=name,offset=offset,kind=kind,expected=v))
 return result
mapping=read(P/'EXACT-LOCAL14-CONFIG3-MAP.json');rows={r['name']:r for r in mapping['configs']}
copy_order=['page_size','page_shift','nowait','user_category','kernel_category','wipe_on_fork','file','alloc_line','free_line','found_debug','size_debug','allocated_debug','zeroed_debug','copied_debug','installed_debug']
extend_order=list(rows['process_extend_region_entry_config']['fields'])
stack_defs=[('page_size',0,'Q'),('page_shift',8,'i'),('user_stack_page_mask',16,'Q'),('user_stack_page_shift',24,'i'),('user_stack_prepage_size',32,'Q'),('stack_alloc_size_override',40,'Q'),('user_stack_page_p2align',48,'i'),('alloc_nowait',56,'Q'),('alloc_user',64,'Q'),('mpol_no_stack',72,'Q'),('user_context_sp_reg',80,'i'),('pf_populate',88,'Q')]+[(n,96+i*8,'fn') for i,n in enumerate(['alloc_aligned','free_pages','add_range','virt_to_phys','attr','pt_set_range','hwcap','modify_context','log'])]
proofs=[]
for name,body,cfg,start,defs in [('copy_user_pte','process_copy_user_pte_body_result','process_copy_entry_config',6,[(n,*rows['process_copy_entry_config']['fields'][n]) for n in copy_order]),('extend_process_region','process_extend_region_body_result','process_extend_region_entry_config',5,[(n,*rows['process_extend_region_entry_config']['fields'][n]) for n in extend_order]),('init_process_stack','process_init_stack_body_result','process_init_stack_entry_config',8,stack_defs)]:
 expected=fields(cfg,defs);actual,trace=read_call(name,body,start-1+len(expected))
 for i,row in enumerate(expected,start):assert equivalent(actual[i-1],row['expected']),(name,i,row,actual[i-1])
 proofs.append(dict(consumer=name,actual_callee=body,config=cfg,field_arguments=[dict(ABI_argument=i,actual=actual[i-1],**row) for i,row in enumerate(expected,start)],full_current_instruction_trace=trace,all_config_fields_forwarded_exact=True,scope='Only config-derived ABI arguments; existing entry dynamic-argument behavior remains at unchanged source/body contract.'))
out=D/'THREE-CONFIG-FOLDED-ABI-ARGUMENTS.json'
with out.open('x') as o:json.dump(dict(decision='PASS_EXACT_THREE_FOLDED_CONFIG_SYSV_FORWARDERS',Rust=ref(e.path),proofs=proofs,nonforwarded_copy_fields=['visit_flags proven separately in copy_user_ranges']),o,indent=2);o.write('\n')
print(json.dumps(dict(proof=ref(out),config_forwarders=3,argument_fields=sum(len(r['field_arguments']) for r in proofs))))
