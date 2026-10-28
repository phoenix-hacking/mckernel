"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite16-object folded-consumer supplement on retained actual objects; no code runs.
"""
from pathlib import Path
import ast,hashlib,json,re,struct
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'inspect_folded.py')};exec(compile((D/'inspect_folded.py').read_text().split('\nconfigmap=')[0],'<retained ELF reader initialization>','exec'),ns);globals().update({k:v for k,v in ns.items() if k!='__file__'})
def ins(name,label='newHOST'):
 out=[]
 for line in (D/('section-'+label+'--'+name+'.objdump')).read_text().splitlines():
  a=line.split('\t')
  if len(a)>=3 and re.fullmatch(r'\s*[0-9a-f]+:',a[0]):out.append(dict(offset=int(a[0].strip()[:-1],16),raw=bytes.fromhex(a[1]),text=a[2].strip()))
 return out
FILE=(str(P/'candidate/kernel/process.c')+'\0').encode()
def literal_relocation(name,off):
 rr=next(r for r in rels(new,own(new,name)) if r['offset']==off);t=rr['target'];z=new.sections[t['shndx']]
 assert rr['type']==1 and t['type']==3 and t['bind']==0 and t['value']==0 and z['name']=='.lrodata.str1.1' and z['flags']&0x32==0x32 and not z['flags']&5
 at=z['offset']+rr['addend'];literal=new.raw[at:new.raw.index(b'\0',at)+1];assert literal==FILE
 return rr

def field_file_reg(name,reg,line,line_reg,callee):
 ii=ins(name);rr=rels(new,own(new,name));ptr=[]
 for i,v in enumerate(ii):
  if re.fullmatch(r'movabs\s+\$0x0,%'+reg,v['text']):
   r=next((r for r in rr if r['offset']==v['offset']+2),None)
   if r and not r['target']['name']:
    try:literal_relocation(name,r['offset']);ptr.append((i,r))
    except AssertionError:pass
 assert len(ptr)==1,(name,'unique filename load');i,fileref=ptr[0]
 call=next((j for j in range(i+1,len(ii)) if ii[j]['text'].startswith('call')),None);assert call is not None
 line_inst=next(v for v in ii[i+1:call] if re.fullmatch(r'mov\s+\$0x%x,%%%s'%(line,line_reg),v['text'])) if line is not None else None
 for v in ii[i+1:call]:
  assert not re.match(r'j\w*\s',v['text'])
  if re.search(r',%'+reg+r'$',v['text']):raise AssertionError((name,'filename ABI register overwritten',v))
 targetregs={}
 for v in ii[i:call]:
  r=next((r for r in rr if r['offset']==v['offset']+2 and r['target']['name']==callee),None)
  if r:targetregs[v['text'].split(',')[-1]]=r
 assert ii[call]['text'].split()[-1][1:] in targetregs,(name,callee,'actual indirect call')
 return dict(consumer=name,FILE_ABI_register=reg,filename_literal=FILE.decode()[:-1],filename_relocation=fileref,line=line,line_ABI_register=line_reg,line_instruction=None if line_inst is None else dict(offset=line_inst['offset'],instruction=line_inst['text']),actual_callee=callee,call_offset=ii[call]['offset'],no_intervening_branch_or_filename_overwrite=True)

def field_file_stack(name,line,callee):
 ii=ins(name);rr=rels(new,own(new,name));candidates=[]
 for i,v in enumerate(ii):
  r=next((r for r in rr if r['offset']==v['offset']+2 and not r['target']['name']),None)
  if not r:continue
  try:literal_relocation(name,r['offset'])
  except AssertionError:continue
  dest=v['text'].split(',')[-1];call=next((j for j in range(i+1,len(ii)) if ii[j]['text'].startswith('call')),None)
  if call is None:continue
  chunk=ii[i+1:call];pushes=[x for x in chunk if x['text'].startswith('push')]
  # Two arguments are pushed in ABI reverse order; line may precede literal load.
  allpushes=[x for x in ii[max(0,i-1):call] if x['text'].startswith('push')]
  if len(allpushes)<2:continue
  if allpushes[-2]['text']!='push   $0x%x'%line or allpushes[-1]['text']!='push   '+dest:continue
  assert not any(re.match(r'j\w*\s',x['text']) for x in chunk)
  target=next(r for r in rr if r['target']['name']==callee and i<=next(j for j,v in enumerate(ii) if v['offset']+2==r['offset'])<call)
  treg=next(v['text'].split(',')[-1] for v in chunk if v['offset']+2==target['offset'])
  assert ii[call]['text'].split()[-1]=='*'+treg
  candidates.append(dict(consumer=name,filename_relocation=r,filename_literal=FILE.decode()[:-1],FILE_ABI_argument=7,line_ABI_argument=8,line=line,reverse_pushes=[dict(offset=x['offset'],instruction=x['text']) for x in allpushes[-2:]],actual_callee=callee,call_offset=ii[call]['offset']))
 assert len(candidates)==1,(name,'exact FILE+line stack ABI',len(candidates));return candidates[0]

register_proofs=[field_file_reg('process_init_stack_free_pages_bridge','rcx',3364,'r8d','pagealloc_track_free_result'),field_file_reg('remap_one_page','rcx',2469,'r8d','pagealloc_track_free_result'),field_file_reg('process_alloc_bridge','rdx',340,'ecx','_kmalloc')]
stack_proofs=[field_file_stack('process_init_stack_alloc_aligned_bridge',3359,'_ihk_mc_alloc_aligned_pages_node'),field_file_stack('process_page_fault_cow_allocate_body_result',3145,'_ihk_mc_alloc_aligned_pages_node'),field_file_stack('process_page_fault_anon_allocate_body_result',3058,'_ihk_mc_alloc_aligned_pages_node')]
# Positive exact FILE MOVABS operands in all33 compiled users of original generic
# tracked filename cell, not a conclusion drawn from missing named relocations.
tracked=read(D/'TRACKED33-FILENAME-LITERAL-EDGES.CORRECTED.json');assert len(tracked)==33
for row in tracked:
 assert row['literal_refs']
 for r in row['literal_refs']:
  literal_relocation(row['name'],r['offset']);v=next(x for x in ins(row['name']) if x['offset']+2==r['offset']);assert v['text'].startswith('movabs ') and len(v['raw'])==10

# Disabled timer/rusage: complete actual instruction bytes are frame+RET.
empty=[]
for name,cell in [('process_sched_timer_init_bridge','process_sched_timer_configuration'),('process_sched_rusage_debug_bridge','process_schedule_exit_debug_input')]:
 assert data(new,own(new,name))==bytes.fromhex('554889e55dc3') and not rels(new,own(new,name))
 cell_sym=own(new,cell);assert data(new,cell_sym)==bytes(8) and not rels(new,cell_sym) and not new.sections[cell_sym['shndx']]['flags']&5
 empty.append(dict(name=name,cell=cell,cell_hex='0000000000000000',complete_code_hex='554889e55dc3',actual_effect='Return after frame prologue/epilogue. Existing source guard [0,0] or NULL prevents all timer/rusage operations.'))
# schedule forwards actual NULL as fourth SysV argument to genuine cleanup.
ii=ins('schedule');rr=next(r for r in rels(new,own(new,'schedule')) if r['target']['name']=='sched_schedule_exit_cleanup');start=next(i for i,v in enumerate(ii) if v['offset']+2==rr['offset']);tail=ii[start:];jmp=next(i for i,v in enumerate(tail) if v['text']=='jmp    *%rax');assert any(v['text']=='xor    %ecx,%ecx' for v in tail[:jmp])
assert not any(v['text'].endswith(',%rcx') or v['text'].endswith(',%ecx') for v in tail[next(i for i,v in enumerate(tail) if v['text']=='xor    %ecx,%ecx')+1:jmp])
schedule=dict(consumer='schedule',actual_callee='sched_schedule_exit_cleanup',NULL_ABI_argument=4,register='RCX',exact_xor_then_tailjump=[dict(offset=v['offset'],instruction=v['text']) for v in tail[:jmp+1]])

# Missing copy config visit_flags/nowait are positively embedded into the actual
# existing visitor context and allocation ABI; all other54 fields checked apart.
ii=ins('copy_user_ranges');t={v['offset']:v for v in ii}
assert t[0x1e7]['text']=='mov    $0x2,%esi' and t[0x2b2]['text']=='movl   $0x1,-0x88(%rbp)' and t[0x2ab]['text']=='mov    %rax,-0x90(%rbp)'
assert t[0x348]['text']=='lea    -0x90(%rbp),%rdi' and t[0x365]['text']=='call   *%rax'
assert any(r['offset']==0x35d and r['target']['name']=='visit_pte_l4' for r in rels(new,own(new,'copy_user_ranges')))
xsrc=Path(P/'relative-module-context-correction-source-1/context-root/kernel/rust/x86_memory_helpers.rs').read_text();snippet=xsrc.split('struct X86VisitPteArgs {',1)[1].split('\n}',1)[0];assert 'pt: *mut c_void,' in snippet and 'flags: CInt,' in snippet
copy_extra=dict(consumer='copy_user_ranges',nowait2_instruction=dict(offset=0x1e7,text=t[0x1e7]['text']),visit_flags1_instruction=dict(offset=0x2b2,text=t[0x2b2]['text']),actual_context_base_store=dict(offset=0x2ab,text=t[0x2ab]['text']),actual_context_argument=dict(offset=0x348,text=t[0x348]['text']),existing_repr_C_context='X86VisitPteArgs: pt pointer at0, flags CInt at8',actual_visitor='visit_pte_l4',call_offset=0x365)

# The selected None memclear provider removes precisely the optional branch.
# Compare entire old default zeroing loop with actual new loop, allowing only
# its finite register renaming, compiler no-ops and branch-address relocation.
rename={'rdi':'rax','rax':'rcx','rcx':'rdx','rdx':'rdi','eax':'ecx','ecx':'edx','edx':'edi','cl':'dl'}
def loop(label,start):
 seq=[v for v in ins('process_add_range_memclear_bridge',label) if v['offset']>=start]
 seq=[v for v in seq if not ('nop' in v['text'] or v['text']=='xchg   %ax,%ax')]
 indexes={v['offset']:i for i,v in enumerate(seq)};out=[]
 for v in seq:
  text=v['text'];op=text.split()[0]
  if re.fullmatch(r'j\w+',op):
   target=int(text.split()[1],16);assert target in indexes;text=op+' BLOCK_'+str(indexes[target])
  elif label=='old114':text=re.sub(r'%([a-z0-9]+)',lambda m:'%'+rename.get(m[1],m[1]),text)
  out.append(re.sub(r'\s+',' ',text).strip())
 return out
oldloop=loop('old114',0x46);newloop=loop('newHOST',0x2f);assert oldloop==newloop,(oldloop,newloop)
name='process_add_range_arch_memclear_callback';s=own(new,name);assert data(new,s)==bytes(8) and not rels(new,s) and not new.sections[s['shndx']]['flags']&5
for label,e in [('old114',old),('newHOST',new)]:
 ts=[r['target']['name'] for r in rels(e,own(e,'process_add_range_memclear_bridge'))];assert ts.count('linux_page_offset_base')==1 and ts.count('_RNvNtNtCsbVRkTr4hvpt_13mckernel_rust18x86_memory_helpers17owned_memory_data20OWNED_INIT_PT_LOADED')==1
memclear=dict(consumer='process_add_range_memclear_bridge',typed_cell=name,selected_value='None/NULL',positive_new_RO_initial_hex='0000000000000000',old_default_loop_start=0x46,current_loop_start=0x2f,complete_normalized_loop_instructions=oldloop,exact_finite_register_renaming=rename,loop_equal=True,translation='Both load same actual view selector and linux_page_offset_base, otherwise0xffff800000000000, and add original phys exactly once. Existing unmodified phys_to_virt source supplies this operation; current full disassemblies retained.',optional_callback_branch='Original C default pointer and new Rust Option are NULL; actual new loop retains zero stores/length guards; no nondefault ARCH_MEMCLEAR behavior is accepted.')
report=dict(decision='PASS_EXACT_FOLDED_FINAL_CELLS_AND_CONFIG_EXTRA_FIELDS',Rust=ref(new.path),register_FILE_line_proofs=register_proofs,stack_FILE_line_proofs=stack_proofs,tracked33_positive_literal_edges=ref(D/'TRACKED33-FILENAME-LITERAL-EDGES.CORRECTED.json'),disabled_complete_code=empty,schedule_NULL_argument=schedule,copy_extra_fields=copy_extra,arch_memclear_None=memclear,scope='Only original16 missing actual consumer predicates; no whole-image behavior/native/file acceptance.')
out=D/'FINAL-CELL-FOLDED-CONSUMER-SUPPLEMENT.json'
with out.open('x') as o:json.dump(report,o,indent=2);o.write('\n')
print(json.dumps(dict(proof=ref(out),register_proofs=3,stack_proofs=3,disabled_bridges=2,tracked_literal_users=33)))
