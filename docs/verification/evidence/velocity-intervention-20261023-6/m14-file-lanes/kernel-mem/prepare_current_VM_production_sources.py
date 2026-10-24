"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact current78 VM source preparation only."""
from pathlib import Path
import json,hashlib,shutil
D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');U=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-1');P=D/'VM-current-union-production-preparation-1';P.mkdir(exist_ok=False);C=D/'coherent-TLB13-VM-source-only-1/candidate';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((D/'all-thirteen-consumer-preparation-1/production/EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json').read_bytes());rows=[]
for old in base['source_inputs']:
 rel=old['relative_path'];canonical=R/rel;bound=U/'source'/rel;assert sha(canonical)==sha(bound),(rel,'current rootunion source differs')
 source=C/rel if rel=='kernel/rust/mem_helpers.rs' else bound;out=P/'source'/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out);rows.append({'relative_path':rel,'root_union':{'path':str(bound),'sha256':sha(bound)},'canonical':{'path':str(canonical),'sha256':sha(canonical)},'actual_input':{'path':str(out),'sha256':sha(out),'bytes':out.stat().st_size},'private_override':rel=='kernel/rust/mem_helpers.rs'})
assert len(rows)==78 and sum(r['private_override'] for r in rows)==1
command=json.loads((U/'RUST-COMMAND.json').read_bytes());av=command['argv'].copy();assert len(av)==48;av[-1]=str(P/'source/kernel/rust/lib.rs');av[-2]='--emit=obj='+str(P/'output-1/mckernel_rust.o')
nm=U/'actual-six-C-partial-1/0/stdout';T=set();US=set()
for line in nm.read_text().splitlines():
 f=line.split()
 if len(f)>=2:
  if f[-2]=='T':T.add(f[-1])
  if f[-2]=='U':US.add(f[-1])
new={'lookup_node','ihk_mc_pt_lookup_fault_pte'};assert not new&(T|US);assert 'ihk_mc_pt_lookup_pte' in US and {'page_fault_process_vm','phys_to_nid','kprintf'}<=T
expected={'basis':{'path':str(nm),'sha256':sha(nm)},'baseline_T':sorted(T),'baseline_U':sorted(US),'new_T':sorted(new),'expected_T':sorted(T|new),'expected_U':sorted(US),'added_U':[],'removed_U':[],'counts':{'old_T':len(T),'old_U':len(US),'T':len(T)+2,'U':len(US)}};(P/'EXPECTED-SYMBOLS.FROM-ACTUAL-UNION.json').write_text(json.dumps(expected,indent=2)+'\n')
root=json.loads((U/'CANONICAL-INTEGRATION.json').read_bytes());r={'scope':__doc__,'status':'CURRENT_UNION78_PLUS_TWO_VM_ENTRIES_SOURCE_ONLY_NO_COMPILER','argv':av,'cwd':str(P),'source_inputs':rows,'source_count':78,'profile':base['profile'],'compiler_sha256':base['compiler_sha256'],'cfg_count':4,'CGU':1,'external_modules':2,'canonical_C_preimage':{'path':str(R/'kernel/mem.c'),'sha256':sha(R/'kernel/mem.c')},'canonical_Rust_preimage':{'path':str(R/'kernel/rust/mem_helpers.rs'),'sha256':sha(R/'kernel/rust/mem_helpers.rs')},'private_C':{'path':str(C/'kernel/mem.c'),'sha256':sha(C/'kernel/mem.c')},'private_Rust':{'path':str(C/'kernel/rust/mem_helpers.rs'),'sha256':sha(C/'kernel/rust/mem_helpers.rs')},'root_integration':{'path':str(U/'CANONICAL-INTEGRATION.json'),'sha256':sha(U/'CANONICAL-INTEGRATION.json')},'checkpoint':'79620055e4933d3b6eef7b9db5b83e7f0c2dcde8','expected_symbols':expected['counts'],'actual':None,'execution_grant':None,'page_hash_UNTESTED_ports_excluded':True}
(P/'EXACT-CURRENT78-VM-RUST-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(r,indent=2)+'\n')
cp=D/'all-thirteen-consumer-preparation-1/production/EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json';c=json.loads(cp.read_bytes());commands=[];oldP=cp.parent
for i,item in enumerate(c['commands']):
 cmd=dict(item);args=[]
 for arg in item['argv']:
  if arg==c['C_source']['path']:arg=str(C/'kernel/mem.c')
  elif arg==str(D/'all-thirteen-consumer-preparation-1/fixture/actual-header-ABI.c'):arg=str(P/'actual-current-VM-header-ABI.c')
  elif str(oldP/'output-1') in arg:arg=arg.replace(str(oldP/'output-1'),str(P/'output-1'))
  args.append(arg)
 cmd['argv']=args;cmd['cwd']=str(P);commands.append(cmd)
# Real active default C caller of lookup_node: reuse the exact rootaccepted
# current full syscall object by stat/provenance, never recompile or rehash it.
inputs=json.loads((U/'actual-six-C-partial-1/INPUT-OBJECTS.json').read_bytes());caller=next(x for x in inputs if x['path'].endswith('/selected-syscall.o'));st=Path(caller['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(caller[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
ld=next(x for x in commands if x['argv'][0]=='/usr/bin/ld');index=commands.index(ld)
commands[index:index]=[{'argv':['/usr/bin/nm','-a','-S',caller['path']],'cwd':str(P),'label':'retained-current-syscall-caller-symbols'},{'argv':['/usr/bin/readelf','-rW',caller['path']],'cwd':str(P),'label':'retained-current-syscall-caller-relocations'}]
ld['argv'].insert(ld['argv'].index(str(P/'output-1/mckernel_rust.o')),caller['path'])
header=(D/'two-VM-fixture-preparation-1/bounded-provider-uint64-correction-1/fixture/actual-header-ABI.c').read_text();header=header.replace(str(D/'next-fault-pte-source-1/candidate/kernel/mem.c'),str(C/'kernel/mem.c'));header+='\n_Static_assert(__builtin_types_compatible_p(__typeof__(&mem_tlb_atomic_dec_bridge),void(*)(unsigned long)),"preserved actualTLBcompletion ABI");\n';(P/'actual-current-VM-header-ABI.c').write_text(header)
leaf=D/'two-VM-fixture-preparation-1/bounded-provider-uint64-correction-1/actual-VM-fixture-capture-1/FINAL-ACTUAL-VM-FIXTURE-RECEIPT.json';actual=json.loads(leaf.read_bytes());assert actual['actual_pairs']==2268;leafRust=actual['durable_objects']['fixture-rust.o'];st=Path(leafRust['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==tuple(leafRust[k] for k in ['device','inode','size','mtime_ns','ctime_ns'])
q={'scope':__doc__,'status':'WHOLE_CURRENT_GCC9_MEM_AND_RETAINED_ACTUAL_SYSCALL_VM_CALLER_RECIPE_NO_COMPILER','commands':commands,'actual_header_closure':c['actual_header_closure'],'tools':c['tools'],'profile':c['profile'],'accepted_wholemem_recipe':{'path':str(cp),'sha256':sha(cp)},'retained_actual_full_syscall_object':caller,'retained_syscall_authority':{'path':str(U/'actual-six-C-partial-1/INPUT-OBJECTS.json'),'sha256':sha(U/'actual-six-C-partial-1/INPUT-OBJECTS.json')},'actual_VM_leaf':{'path':str(leaf),'sha256':sha(leaf)},'retained_VM_leaf_Rust_metadata_NOT_REHASHED':leafRust,'allocated_ref_contract':'Existing Ctlbhandlerdec stillGLOBALUND allocatedGOT64pointer; retain all13uniqueRustTs. Actual current fullkernel/syscall.c get_mempolicy path calls publiclookup_node; require exactallocatedexecutable GLOBALUNDlookup_node reference and partial resolves uniqueRustT. Record actualtype/offset/addend through owning RELA.sh_info; no inventedCimport for faultPTEentry.','active_scope':'ihk_mc_pt_lookup_fault_pte Ccalls found only optionalTOFU currentsource; this profile does not certify optionalTOFU. Entry stillfullRustT/defaultCexcluded +2268realPUBLICtypedleafproof; no nativecredit.','C_callsite':{'path':str(R/'kernel/syscall.c'),'sha256':sha(R/'kernel/syscall.c'),'line':26578},'unresolved_C_debt':'Underlying ihk_mc_pt_lookup_pte publicCprovider remains realRustU; otherpagehash/mapping/accounting/fault/effect providers remain. Pagehash3source batch excluded/UNTESTED.','actual_objects':None,'execution_grant':None}
(P/'EXACT-WHOLE-GCC9-VM-CONSUMER.NOT-EXECUTED.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({'root':str(P),'Rust_recipe_sha256':sha(P/'EXACT-CURRENT78-VM-RUST-RECIPE.NOT-EXECUTED.json'),'C_recipe_sha256':sha(P/'EXACT-WHOLE-GCC9-VM-CONSUMER.NOT-EXECUTED.json'),'symbols':expected['counts'],'leafRust_rehashed':False,'retained_syscall_rehashed':False},indent=2))
