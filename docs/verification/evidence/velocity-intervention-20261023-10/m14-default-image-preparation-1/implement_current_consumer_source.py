"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Private source adoption, no tests/builds."""
from pathlib import Path
import ast,re,json,hashlib,difflib
N=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');B=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-15/default-image-preparation-1');U=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/root-union-preparation-1');old=B/'native_rust_exact_mckernel_image_offline.py';s=old.read_text();original=s;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tree=ast.parse(s);constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.startswith('M14_')}
root=json.loads((U/'CANONICAL-INTEGRATION.json').read_bytes());pins=dict(constants['M14_SOURCE_PINS'])
for row in root['written']:pins[str(Path(row['path']).relative_to(R))]=row['after']
for rel,h in pins.items():assert sha(R/rel)==h,(rel,'current_sourcechanged')
nm=U/'actual-six-C-partial-1/0/stdout';actualT={x.split()[-1] for x in nm.read_text().splitlines() if len(x.split())>=2 and x.split()[-2]=='T'};actualU={x.split()[-1] for x in nm.read_text().splitlines() if len(x.split())>=2 and x.split()[-2]=='U'}
module_C={'mem_helpers':['kernel/mem.c'],'process_helpers':['kernel/process.c'],'syscall_policy':['kernel/syscall.c','arch/x86_64/kernel/syscall.c'],'x86_cpu_helpers':['arch/x86_64/kernel/cpu.c'],'x86_memory_helpers':['arch/x86_64/kernel/memory.c']};newnames=[];ownership={k:[] for files in module_C.values() for k in files};pattern=r'(?m)^pub (?:unsafe )?extern "C" fn (\w+)\('
for module,files in module_C.items():
 rel=f'kernel/rust/{module}.rs';before=(B/'source-materialization-attempt-1/materialized-source'/rel).read_text();after=(R/rel).read_text();added=sorted(set(re.findall(pattern,after))-set(re.findall(pattern,before)));assert set(added)<=actualT
 newnames+=added
 for name in added:
  owners=[f for f in files if re.search(r'\b'+name+r'\s*\(', (R/f).read_text())]
  assert owners,(name,'no actual selected C declaration/callsite')
  for f in owners:ownership[f].append(name)
callbacks={}
for f,names in constants['M14_SUCCESSOR_C_CALLBACKS'].items():
 for name in names:
  if name in actualT:
   if name not in ownership[f]:ownership[f].append(name)
  else:assert name in actualU;callbacks.setdefault(f,[]).append(name)
# Exact current selected C imports are from accepted complete F05 TU, not old helper-only callers.
memnm=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/combined-l2-l1-production-preparation-1/bounded-current-canonical-binding-correction-1/actual-attempt-1/06-memory-symbols/stdout');memU={x.split()[-1] for x in memnm.read_text().splitlines() if len(x.split())>=2 and x.split()[-2]=='U'}
imports=tuple(n for n in constants['M14_MEMORY_IMPORTS']+('clear_range_l1','clear_range_l2','clear_range_l3') if n in memU);assert imports==('x86_clear_range_public_body','clear_range_l1','clear_range_l2','clear_range_l3')
retired=tuple(dict.fromkeys(constants['M14_C_RETIRED_MEMORY_BODIES']+constants['M14_MEMORY_IMPORTS']+('clear_range_l1','clear_range_l2','clear_range_l3')))
selection=[]
for f,macro,names in constants['M14_SUCCESSOR_SELECTION']:selection.append((f,macro,tuple(dict.fromkeys(names+tuple(ownership[f])))))
selection.append(('arch/x86_64/kernel/memory.c','MCKERNEL_RUST_X86_MEMORY_PUBLIC',tuple(ownership['arch/x86_64/kernel/memory.c'])))
exports=tuple(dict.fromkeys(constants['M14_RUST_EXPORTS']+tuple(newnames)));assert set(exports)<=actualT
header=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/combined-l2-l1-production-preparation-1/bounded-current-canonical-binding-correction-1/actual-memory-header-ABI.c');assertions='\n'.join(l for l in header.read_text().splitlines() if not l.startswith('#include'))+'\n'
changes={'M14_SOURCE_PINS':pins,'M14_MEMORY_IMPORTS':imports,'M14_C_RETIRED_MEMORY_BODIES':retired,'M14_RUST_EXPORTS':exports,'M14_SUCCESSOR_C_CALLBACKS':{f:tuple(v) for f,v in callbacks.items()},'M14_SUCCESSOR_SELECTION':tuple(selection),'M14_L4_HEADER_ABI_ASSERTIONS':constants['M14_L4_HEADER_ABI_ASSERTIONS']+assertions}
lines=s.splitlines(True)
for node in reversed(tree.body):
 if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in changes:lines[node.lineno-1:node.end_lineno]=[node.targets[0].id+' = '+repr(changes[node.targets[0].id])+'\n']
s=''.join(lines)
warning=B/'next-build-preparation-1/pinned-full-image-attempt-1/owner-work/output/build/m14-production/successor-real-ABI-arch-x86_64-kernel-cpu-c.stderr';warningraw=warning.read_bytes();assert sha(warning)=='36db2b44f91dbaa2c84ab62f3193b39b882213cc0086725aec7b8ea2805d6af6'
newwarning=warningraw.replace(b':3720:',b':3732:').replace(b' 3720 |',b' 3732 |').replace(b':3746:',b':3758:').replace(b' 3746 |',b' 3758 |').replace(b':3775:',b':3787:').replace(b' 3775 |',b' 3787 |');assert len(newwarning)==1519 and newwarning.count(b'warning:')==4
# Warning producer expressions and leading columns are byte-identical at exact shifted lines.
oldcpu=(B/'source-materialization-attempt-1/materialized-source/arch/x86_64/kernel/cpu.c').read_text().splitlines();newcpu=(R/'arch/x86_64/kernel/cpu.c').read_text().splitlines()
for a,b in [(3720,3732),(3746,3758),(3775,3787)]:assert oldcpu[a-1]==newcpu[b-1]
addition='''
# Functional OS/Rust only; no security testing. Exact current accepted ownership.
M14_CURRENT_RUST_PROVIDERS = '''+repr({f:tuple(v) for f,v in ownership.items()})+'''
M14_CURRENT_CPU_ABI_WARNINGS = '''+repr(newwarning)+'''

def _m14_check_current_provider_symbols(texts, rust, image):
    def rows(text,name):return [line.split() for line in text.splitlines() if line.split()[-1:]==[name]]
    for relative,names in M14_CURRENT_RUST_PROVIDERS.items():
        for name in names:
            _fail(not any(r[-2] in ('T','t') for r in rows(texts[relative],name)), 'M14 retired current C provider remains: '+name)
            for text in (rust,image):
                found=rows(text,name)
                _fail(len(found)==1 and found[0][-2]=='T', 'M14 current unique Rust/final provider missing: '+name)
    return M14_CURRENT_RUST_PROVIDERS

def _m14_cpu_abi_stderr_allowed(name, raw):
    # All other sites require empty stderr. This exact warning is still retained.
    return raw==b'' or (name=='successor-real-ABI-arch-x86_64-kernel-cpu-c' and raw==M14_CURRENT_CPU_ABI_WARNINGS)

'''
pos=s.index('def _validate_m14_successor_contract(');s=s[:pos]+addition+s[pos:]
needle="    geometry=unique(texts['kernel/mem.c'],'mem_remote_tlb_geometry','R')";assert s.count(needle)==1;s=s.replace(needle,"    current_rust_providers=_m14_check_current_provider_symbols(texts,rust,image)\n"+needle)
s=s.replace("actual_C_callbacks=M14_SUCCESSOR_C_CALLBACKS,actual_Rust_callback_relocation_counts=callback_relocations","actual_C_callbacks=M14_SUCCESSOR_C_CALLBACKS,current_Rust_providers=current_rust_providers,actual_Rust_callback_relocation_counts=callback_relocations")
needle="    _fail(row['exit_code'] == 0 and stderr.stat().st_size == 0, 'M14 observer failed: ' + name)";assert s.count(needle)==1;s=s.replace(needle,"    stderr_raw=stderr.read_bytes()\n    _fail(row['exit_code'] == 0 and _m14_cpu_abi_stderr_allowed(name,stderr_raw), 'M14 observer failed: ' + name)\n    if stderr_raw:row['stderr_qualification']='EXACT_FOUR_SOURCE_BOUND_EXISTING_GCC14_PACKED_MEMBER_WARNINGS_PRESERVED'")
# Current selection includes memory TU as well; keep existing two-pointer dynamic
# section-aware L4/L3 proof exactly unchanged. L3 dispatcher C body remains debt.
out=N/'native_rust_exact_mckernel_image_offline.py';out.write_text(s);(N/'CURRENT-DRIVER-CONSUMER-DELTA.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile=str(old),tofile=str(out))))
proof={'scope':__doc__,'status':'CURRENT_DRIVER_SOURCE_ADOPTED_NO_TEST_OR_EXECUTION','driver':{'path':str(out),'sha256':sha(out)},'base_driver':{'path':str(old),'sha256':sha(old)},'root_integration':{'path':str(U/'CANONICAL-INTEGRATION.json'),'sha256':sha(U/'CANONICAL-INTEGRATION.json')},'actual_union_NM':{'path':str(nm),'sha256':sha(nm)},'actual_current_memory_NM':{'path':str(memnm),'sha256':sha(memnm)},'new_Rust_exports':newnames,'all_exports_count':len(exports),'current_C_to_Rust_ownership':ownership,'retained_C_callbacks':callbacks,'exact_current_C_memory_imports':imports,'old_memory_helper_exports_still_C_excluded_and_Rust_final_T':True,'L4_private_L3_C_child_section_observer_function_UNCHANGED':True,'L3_L2_L1_typed_header_assertions_added_from_accepted_F05':{'path':str(header),'sha256':sha(header)},'warning':{'original_retained_path':str(warning),'original_sha256':sha(warning),'current_expected_sha256':hashlib.sha256(newwarning).hexdigest(),'bytes':len(newwarning),'producer_source_sha256':pins['arch/x86_64/kernel/cpu.c'],'exact_line_pairs':[[3720,3732],[3746,3758],[3775,3787]],'identical_source_expression_bytes':True,'exact_stage_only':True,'no_blanket_stderr':True},'regression_tests':None,'actual_build':None,'default_link':None,'native':None}
(N/'CURRENT-CONSUMER-SOURCE-ADOPTION.NOT-TESTED.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'driver_sha256':sha(out),'new_exports':len(newnames),'all_exports':len(exports),'ownership_counts':{k:len(v) for k,v in ownership.items()},'proof_sha256':sha(N/'CURRENT-CONSUMER-SOURCE-ADOPTION.NOT-TESTED.json')},indent=2))
