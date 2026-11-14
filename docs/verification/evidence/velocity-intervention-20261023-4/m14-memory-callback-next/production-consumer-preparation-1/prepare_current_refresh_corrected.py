"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root authorized exact source-key preparation correction; preserves stopped partialcopy.
"""
from pathlib import Path
import json,hashlib,shutil
R=Path('/home/holden/mckernel');B=Path('/home/holden/mckernel-work/host-preparation');V=B/'velocity-intervention-20261023-4';P=Path(__file__).resolve().parent;D=P/'coherent-current78-refresh-corrected-1';D.mkdir(mode=0o700);S=D/'source';S.mkdir();O=D/'output-1'
def pin(f):
 b=f.read_bytes();return dict(path=str(f),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def wr(f,x):f.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
r=json.loads((P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json').read_text());c=json.loads((P/'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.NOT-EXECUTED.json').read_text());changes=[]
allowed={'kernel/rust/process_helpers.rs':'3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e','kernel/rust/syscall_policy.rs':'f1f7866c0f2ccc8e1b0024dfb632ec7359dd2a0a4bcd8e22deb957d48ef6d770'}
for k,row in r['source_inputs'].items():
 actual=pin(R/k)
 if actual['sha256']!=row['canonical_before']['sha256']:
  assert k in allowed and actual['sha256']==allowed[k],k;changes.append(dict(key=k,before=row['canonical_before'],after=actual))
 source=Path(row['private']['path']) if k=='kernel/rust/x86_memory_helpers.rs' else R/k;dst=S/k;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dst);row['canonical_before']=actual;row['private']=pin(dst)
assert sorted(x['key'] for x in changes)==sorted(allowed)
walk=B/'velocity-intervention-20261023-3/m14-walk-l4/production-consumer-preparation-1/actual-attempt-1/01-production-Rust-NM/stdout';cpu=V/'m14-x86-cpu/production-consumer-preparation-1/actual-production-capture-1/01-production-Rust-NM/stdout';proc=V/'m14-process-next/production-consumer-preparation-1/coherent-current78-refresh-1/actual-production-capture-1/01-current78-Rust-symbols/stdout';sy=V/'m14-syscall-combined-production-preparation-1/header-transport-correction-1/actual-remaining-consumer-attempt-1/11/stdout'
def names(f,k):return {l.split()[-1] for l in f.read_text().splitlines() if l.split()[-2:-1]==[k]}
wu,cu,pu,su=[names(f,'U') for f in [walk,cpu,proc,sy]]
co=wu|{'x86_cpuid6_bridge','x86_running_on_kvm_bridge'};procadd=pu-co;procrm=co-pu;sysadd=su-cu;sysrm=cu-su;after=(co|procadd|sysadd|{'x86_clear_range_l3_callback'})-procrm-sysrm
assert len(wu)==573 and len(cu)==575 and len(pu)==577 and len(su)==574 and len(after)==577
priorT=set().union(*(names(f,'T') for f in [walk,cpu,proc,sy]));r['expected_all_prior_T']=sorted(priorT);r['expected_T_added']=['x86_clear_range_l4_body'];r['expected_U']=sorted(after)
r['expected_U_derivation']=dict(actual_walk=len(wu),actual_CPU=len(cu),actual_process=len(pu),actual_syscall=len(su),coherent_walkCPU=len(co),process_added=sorted(procadd),process_removed=sorted(procrm),combined_vs_CPU_added=sorted(sysadd),combined_vs_CPU_removed=sorted(sysrm),private_added=['x86_clear_range_l3_callback'],after=577)
r['actual_symbol_authorities']=[pin(f) for f in [walk,cpu,proc,sy]];r['refresh_authority_receipts']=[pin(V/'m14-process-next/production-consumer-preparation-1/coherent-current78-refresh-1/ACTUAL-PRODUCTION-WHOLE-JOIN.json'),pin(V/'m14-syscall-combined-production-preparation-1/header-transport-correction-1/ACTUAL-REMAINING15-CONSUMER-RECEIPT.json')]
r['argv'][46]='--emit=obj='+str(O/'mckernel_rust.o');r['argv'][47]=str(S/'kernel/rust/lib.rs');r['additive_current78_refresh']=changes;r['prior_recipe']=pin(P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json');wr(D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json',r)
abi=D/'actual-memory-header-ABI.c';shutil.copyfile(P/'actual-memory-header-ABI.c',abi);c['ABI_witness']=pin(abi);c['Rust_recipe']=pin(D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json')
for cmd in c['commands']:
 cmd['cwd']=str(O);cmd['argv']=[v.replace(str(P),str(D)) for v in cmd['argv']]
for n in ['vm_range_insert','syscall_signalfd_publish_bridge','arch_ptrace']:assert n in priorT
c['expected_partial_unique_Rust_T']+=['vm_range_insert','syscall_signalfd_publish_bridge','arch_ptrace'];c['coherent_refresh_rust_symbol_expectations']=r['expected_U_derivation'];wr(D/'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.GRANTED.json',c)
meta=dict(scope=r['scope'],status='ROOT_GRANTED_ADDITIVE_CURRENT78_TWO_INPUT_REFRESH',preserved_original_ready=pin(P/'PRODUCTION-CONSUMER-READY.json'),source_key_prep_failure=pin(P/'coherent-current78-refresh-1/PREPARATION-KEY-ASSERTION.STOP.json'),preparation_driver=pin(Path(__file__)),refresh=changes,other76_canonical_preimages_match=True,private_override_unchanged=r['candidate_source'],C_override_unchanged=c['private_memory_source'],Rust_recipe=pin(D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json'),C_recipe=pin(D/'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.GRANTED.json'),actual_symbol_union=r['expected_U_derivation'],expected_U_exact_set_count=len(after),profile=r['profile'],outputs_until_actualrun=None)
wr(D/'COHERENT-CURRENT78-REFRESH-AND-GRANT.json',meta);print(json.dumps(dict(refresh=pin(D/'COHERENT-CURRENT78-REFRESH-AND-GRANT.json'),Rust=meta['Rust_recipe'],C=meta['C_recipe'],U_expected=577,partialT=len(c['expected_partial_unique_Rust_T']))))
