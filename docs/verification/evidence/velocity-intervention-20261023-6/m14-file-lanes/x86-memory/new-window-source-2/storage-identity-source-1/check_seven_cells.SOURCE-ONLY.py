"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source candidate/controlled fixture only: exact7 retained cell bytes/RELA, not
whole-observer retry, acceptance, compiler, native or artifact mutation.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,re,struct,time
D=Path(__file__).resolve().parent;B=D.parent;A=B/'actual-bounded-suffix-1'
F=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/f02_data_contract.py')
H=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/whole-memory-closure-source-3/data-state-ownership-source-successor-1/production-consumer-preparation-1/bounded-effect-callback-type-correction-1/expert-exact-compiler-note-correction-1/run_retained_suffix_once.SINGLE-GATE.NOT-RELEASED.py')
HPIN='dac5cb0d3d0bd6a99f190ad4f4c7d1906576ebdd4ead73dd07bca460d7da7bdd';FPIN='f747b6fe08b0b0ee47f91199905815fcb11748e7af6015ccfd1ef93fc71a27d0'
def require(ok,message):
 if not ok: raise ValueError(str(message))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_helpers():
 require(digest(H)==HPIN and digest(F)==FPIN,'exact existing accepted helper hashes')
 ns={'struct':struct}
 for p,want in [(H,{'Elf','owning_relocations','object_bytes','relocated_location'}),(F,{'_f02_fail','_f02_final_view'})]:
  nodes=[n for n in ast.parse(p.read_text()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in want]
  require({n.name for n in nodes}==want,'complete exact helper AST selection')
  exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
 return ns

def exact_object(elf,name,size,align,mutable):
 found=[s for s in elf.symbols if s['name']==name and 0<s['shndx']<len(elf.sections)]
 require(len(found)==1,('unique exact Rust object',name))
 s=found[0];sec=elf.sections[s['shndx']]
 require(s['type']==1 and s['size']==size and s['value']%align==0,('Rust object ABI',name))
 require(sec['align']>=align and sec['flags']&2 and not sec['flags']&4,('Rust allocated nonexec alignment',name))
 require(bool(sec['flags']&1)==mutable,('Rust mutability',name))
 return s

def final_object(final,name,size,align,mutable):
 s=final['defined'](name,1);sec=final['sections'][s['shndx']]
 require(s['size']==size and s['value']%align==0 and sec['align']>=align,('final object ABI',name))
 require(sec['flags']&2 and not sec['flags']&4 and bool(sec['flags']&1)==mutable,('final allocation/mutability',name))
 return s

def check_row(row,rust,final,ns):
 name=row['Rust']['storage_definitions'][0]['name'];cell=row['pointer_cell'];size=row['C_size'];align=row['C_alignment']
 owner=exact_object(rust,name,size,align,True);pointer=exact_object(rust,cell,8,8,False)
 require(owner['shndx']!=pointer['shndx'],'storage distinct from pointer cell')
 require(rust.sections[owner['shndx']]['type']==8 and ns['object_bytes'](rust,owner)==bytes(size),'Rust zero-initialized NOBITS storage')
 relocs=ns['owning_relocations'](rust,pointer)
 require(len(relocs)==1 and relocs[0]['offset']==0 and relocs[0]['type']==1,'exact one8byte absolute pointer relocation')
 location=ns['relocated_location'](rust,relocs[0]);require(location==(owner['shndx'],owner['value']),'cell relocation targets exact storage start')
 require(relocs[0]['target']['name'] in (name,rust.sections[owner['shndx']]['name']),'only exact owner or its exact section target')
 fowner=final_object(final,name,size,align,True);fcell=final_object(final,cell,8,8,False)
 require(fowner['value']!=fcell['value'],'final pointer cell distinct from storage')
 require(final['sections'][fowner['shndx']]['type']==8 and final['read'](fowner['value'],size)==bytes(size),'final zero initialized NOBITS storage')
 raw=final['read'](fcell['value'],8);target=struct.unpack('<Q',raw)[0]
 require(target==fowner['value'],'final8byte pointer target equals exact storage address')
 return {'C_name':row['C_name'],'Rust_exact_name':name,'pointer_cell':cell,'Rust_owner':owner,'Rust_cell':pointer,'Rust_exact_cell_relocation':relocs[0],'final_owner':fowner,'final_cell':fcell,'final_cell_hex':raw.hex(),'final_cell_decoded_target':hex(target)}

def main():
 start=time.monotonic();require(os.sched_getaffinity(0)=={6},'granted CPU6 only')
 ns=load_helpers();mapping=json.loads((D/'SEVEN-STORAGE-IDENTITIES.SOURCE-ONLY.json').read_text());joined=json.loads((A/'INPUTS-JOIN.json').read_text())
 refs={r['path']:r for r in joined['inputs']}
 rustp=next(Path(p) for p in refs if p.endswith('/kernel/rust/mckernel_rust.o'));imagep=next(Path(p) for p in refs if p.endswith('/kernel/mckernel.img'));abip=next(Path(p) for p in refs if p.endswith('/memory_real_C_ABI.o'));sourcep=Path('/home/holden/mckernel/kernel/rust/x86_memory_helpers.rs');cp=Path('/home/holden/mckernel/arch/x86_64/kernel/memory.c')
 observed=json.loads((A/'FOCUSED-SYMBOL-ABI-EVALUATION.json').read_text());abicsrc=Path(observed['ABI_source_binding']['path'])
 inputs=[rustp,imagep,abip,sourcep,cp,abicsrc,H,F,A/'FOCUSED-SYMBOL-ABI-EVALUATION.json',D/'SEVEN-STORAGE-IDENTITIES.SOURCE-ONLY.json']
 before={str(p):digest(p) for p in inputs}
 for p in [rustp,imagep,abip,sourcep,cp]:require(before[str(p)]==refs[str(p)]['sha256'],('retained exact input',str(p)))
 require(before[str(abicsrc)]==observed['ABI_source_binding']['sha256'],'retained exact C ABI source')
 require(observed['status']=='FAIL_STOP_EXPERT_REQUIRED' and len(observed['data_rows'])==79,'original failed79row observer retained')
 unchanged=[r for r in observed['data_rows'] if r['symbol'] not in {x['C_name'] for x in mapping['rows']}]
 require(len(unchanged)==72 and all(r['Rust']['valid_size_alignment_allocated_object'] and r['image']['valid_size_alignment_allocated_object'] for r in unchanged),'all72 existing ABI checks retained passed')
 rust=ns['Elf'](rustp);abi=ns['Elf'](abip);final=ns['_f02_final_view'](imagep);text=sourcep.read_text();lines=text.splitlines()
 indices={name:index for index,name in re.findall(r'const unsigned long closure_C_owner_size_(\d+) = sizeof\((\w+)\);',abicsrc.read_text())}
 require(len(mapping['rows'])==7 and len({r['C_name'] for r in mapping['rows']})==7,'exact7row map')
 rows=[];controls=[];consumer_observations=[]
 for row in mapping['rows']:
  ix=indices[row['C_name']];require(abi.word('closure_C_owner_size_'+ix)==row['C_size'] and abi.word('closure_C_owner_align_'+ix)==row['C_alignment'],'exact original C ABI7row')
  for key in ['source_initializer','source_pointer_initializer','source_consumer_refs']:
   require(row[key] and all(lines[x['line']-1].strip()==x['text'] for x in row[key]),('exact bound source identity',row['C_name'],key))
  result=check_row(row,rust,final,ns);rows.append(result)
  # Capture only exact source consumer functions and their direct named refs.
  consumers=[]
  for x in row['source_consumer_refs']:
   names=[m.group(1) for line in lines[:x['line']] for m in [re.search(r'\bfn\s+(\w+)\s*\(',line)] if m]
   if names and names[-1] not in consumers:consumers.append(names[-1])
  for name in consumers:
   s=rust.sym(name);require(s['type']==2 and rust.sections[s['shndx']]['flags']&6==6,'exact source consumer executable function')
   rs=ns['owning_relocations'](rust,s)
   selected=[x for x in rs if x['target']['name'] in [row['pointer_cell'],result['Rust_exact_name']]]
   consumer_observations.append({'C_name':row['C_name'],'consumer':name,'function':s,'direct_named_cell_or_storage_refs':selected,'limit':'Direct named references only; no section-addend function reference semantics inferred.'})
  # In-memory negative fixtures exercise the SAME predicate, no ELF mutation.
  for mutation in ['wrong_final_pointer','wrong_Rust_relocation_target','storage_wrong_size','storage_wrong_alignment','storage_executable','nonzero_initializer','duplicate_storage','mutable_pointer_cell']:
   rr=copy.copy(rust);rr.sections=copy.deepcopy(rust.sections);rr.symbols=copy.deepcopy(rust.symbols);ff=dict(final);nn=dict(ns)
   owner=next(s for s in rr.symbols if s['name']==result['Rust_exact_name']);cell=next(s for s in rr.symbols if s['name']==row['pointer_cell'])
   if mutation=='wrong_final_pointer':
    read=final['read'];address=result['final_cell']['value'];ff['read']=lambda a,n,read=read,address=address: bytes(8) if a==address and n==8 else read(a,n)
   elif mutation=='wrong_Rust_relocation_target':
    original=ns['owning_relocations'];nn['owning_relocations']=lambda e,s,original=original: [dict(x,addend=x['addend']+1) for x in original(e,s)]
   elif mutation=='storage_wrong_size':owner['size']+=1
   elif mutation=='storage_wrong_alignment':rr.sections[owner['shndx']]['align']=1
   elif mutation=='storage_executable':rr.sections[owner['shndx']]['flags']|=4
   elif mutation=='nonzero_initializer':
    original=ns['object_bytes'];nn['object_bytes']=lambda e,s,original=original: b'\x01'+bytes(s['size']-1) if s['name']==owner['name'] else original(e,s)
   elif mutation=='duplicate_storage':rr.symbols.append(dict(owner))
   elif mutation=='mutable_pointer_cell':rr.sections[cell['shndx']]['flags']|=1
   rejected=False
   try:check_row(row,rr,ff,nn)
   except ValueError:rejected=True
   require(rejected,('negative fixture unexpectedly accepted',row['C_name'],mutation));controls.append({'C_name':row['C_name'],'mutation':mutation,'rejected':True})
 addresses=[(r['final_owner']['value'],r['final_owner']['size']) for r in rows];require(all(a+n<=b or b+m<=a for i,(a,n) in enumerate(addresses) for b,m in addresses[i+1:]),'seven distinct nonoverlapping storage owners')
 require(before=={str(p):digest(p) for p in inputs},'all retained inputs unchanged')
 report={'scope':__doc__.splitlines()[0],'status':'SOURCE_CANDIDATE_EXACT7CELLS_AND_CONTROL_FIXTURES_CAPTURED_REVIEW_PENDING','accepted':False,'native_or_retirement_credit':0,'compiler_native_observer_retry':False,'inputs':before,'helper_AST_reused':{'Elf_owning_relocations_object_bytes_relocated_location':str(H),'final_ELF_view':str(F)},'rows':rows,'in_memory_negative_controls':controls,'retained_unchanged_72_ABI_rows':unchanged,'consumer_observations':consumer_observations,'consumer_reference_gaps':[x['consumer'] for x in consumer_observations if not x['direct_named_cell_or_storage_refs']],'original_failed_observer_preserved':str(A/'FOCUSED-SYMBOL-ABI-EVALUATION.json'),'limits':'Additive7cell source predicate and controlled fixtures only; independent high review required before any new validation acceptance. Direct compiled references only as recorded; original F02/default/native remain open.','wall_seconds':time.monotonic()-start}
 output=D/'EXACT7CELLS-CONTROLLED-SOURCE-RESULT.json';require(not output.exists(),'new exclusive result')
 with output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'status':report['status'],'cells':len(rows),'negative_controls':len(controls),'consumer_reference_gaps':report['consumer_reference_gaps'],'seconds':report['wall_seconds']}))
if __name__=='__main__':main()
