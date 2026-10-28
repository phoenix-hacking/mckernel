"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded ABI/ELF qualification only; no dynamic or native behavior claim.
"""
from pathlib import Path
import hashlib,importlib.util,json,sys,struct
D=Path(__file__).resolve().parent
SOURCE_PACKET=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f03-setsiginfo-syscall-event-report-signal-host-preparation-source-1')
RETAINED=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f03-setsiginfo-syscall-event-report-signal-host-preparation-source-1/signal-address-witness-correction-source-1/HOST-output-proposed-1')
helper=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f02-source38-next-current-integration-source-1/check_thirteen_storage.py')
spec=importlib.util.spec_from_file_location('retained_elf',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Elf=module.Elf

def ref(p):
 b=Path(p).read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def word_array(elf,name):
 rows=elf.definitions(name);assert len(rows)==1,(elf.path,name,rows)
 s=rows[0];sec=elf.sections[s['ndx']]
 assert s['kind']==1 and s['bind']==1 and s['size']==72
 assert sec['flags']&2 and not sec['flags']&5 and sec['align']>=8 and s['value']%8==0
 start=sec['off']+s['value']-sec['addr'];return struct.unpack('<9Q',elf.data[start:start+72])
def function(elf,name,global_required):
 rows=elf.definitions(name);assert len(rows)==1,(elf.path,name,rows)
 s=rows[0];assert s['kind']==2 and s['size']>0 and elf.sections[s['ndx']]['flags']&4
 if global_required:assert s['bind']==1
 return dict(name=name,size=s['size'],section=elf.sections[s['ndx']]['name'],binding=s['bind'])
def main():
 out=Path(sys.argv[1]);assert out.resolve()==(D/'HOST-output-proposed-1').resolve()
 names=['f03_ptrace_setsiginfo_v1','ptrace_syscall_event','f03_exec_report_signal_v1']
 rust,c,fallback,joint=[Elf(RETAINED/x) for x in ['rust-selected.o','selected.o','fallback.o','selected-joint.o']]
 oldjoint=Elf(out/'fallback-joint.o');fallback_rust=Elf(out/'rust-fallback.o')
 abi=word_array(rust,'f03_ptrace_HOST_ABI');assert abi==word_array(c,'f03_ptrace_C_ABI')==word_array(fallback,'f03_ptrace_C_ABI')==word_array(joint,'f03_ptrace_HOST_ABI')
 assert abi[0]==128 and abi[2]==160 and abi[4]==24 and abi[6:8]==(4,8)
 exports=[function(rust,n,True) for n in names];[function(joint,n,True) for n in names]
 for n in names:assert not c.definitions(n),(n,'selected C must reference Rust')
 refs={'f03_ptrace_setsiginfo_v1':c.allocated_references('f03_ptrace_setsiginfo_v1')}
 assert refs['f03_ptrace_setsiginfo_v1'],('actual setsiginfo TU consumer required',refs)
 # This is a typed HOST fixture edge, NOT a surviving production C caller.
 witness=c.definitions('f03_ptrace_C_signal_ref');assert len(witness)==1
 ws=witness[0];assert ws['kind']==1 and ws['bind']==1 and ws['size']==8
 witnessrefs=[r for r in c.allocated_references('f03_exec_report_signal_v1') if r['section']==c.sections[ws['ndx']]['name'] and r['offset']==ws['value'] and r['relocation_type']==1 and r['addend']==0]
 assert len(witnessrefs)==1,('typed HOST_ABI_WITNESS R_X86_64_64 required',witnessrefs)
 rust_signal_refs=rust.allocated_references('f03_exec_report_signal_v1')
 rust_event_refs=rust.allocated_references('ptrace_syscall_event')
 for n in ['ptrace_setsiginfo','ptrace_report_signal_bridge']:assert not c.definitions(n)
 oldnames=['ptrace_setsiginfo','ptrace_syscall_event','ptrace_report_signal_bridge']
 oldexports=[function(fallback,n,n=='ptrace_syscall_event') for n in oldnames]
 [function(oldjoint,n,n=='ptrace_syscall_event') for n in oldnames]
 for n in ['sys_ptrace',*names]:assert not fallback_rust.definitions(n),(n,'matching Rust cfg-off must not export the C-owned ptrace entries')
 fallback_sys_ptrace=function(fallback,'sys_ptrace',True);function(oldjoint,'sys_ptrace',True)
 # Public event name is retained for actual architecture/Rust consumers.
 proof=json.loads((SOURCE_PACKET/'REUSED-SEMANTIC-PROVIDER-SOURCE-PROOF.json').read_text())
 retained=Elf(proof['retained_actual_Rust']['path']);assert ref(retained.path)==proof['retained_actual_Rust']
 publicrefs=retained.allocated_references('ptrace_syscall_event');assert publicrefs
 source=json.loads((SOURCE_PACKET/'HOST-WITNESS-BINDING.json').read_text());host=Path(source['HOST_policy']['path']).read_text();assert host.endswith(source['witness_only'])
 assert host[:-len(source['witness_only'])]==Path(source['production_policy']['path']).read_text()
 for n in names:assert not [s for s in joint.symbols if s['name']==n and s['ndx']==0]
 # Partial-linker must preserve every existing Rust retained section.
 retained_sections=[s for s in rust.sections if s['flags']&0x200000 and s['flags']&2]
 assert retained_sections
 for s in retained_sections:
  matches=[z for z in joint.sections if z['name']==s['name']]
  assert len(matches)==1 and matches[0]['flags']&0x200000,(s['name'],'GNU_RETAIN lost')
 fallback_retained_sections=[s for s in fallback_rust.sections if s['flags']&0x200000 and s['flags']&2]
 assert fallback_retained_sections
 for s in fallback_retained_sections:
  matches=[z for z in oldjoint.sections if z['name']==s['name']]
  assert len(matches)==1 and matches[0]['flags']&0x200000,(s['name'],'fallback GNU_RETAIN lost')
 report=dict(status='PASS_CHANGED_THREE_WRAPPER_ABI_ELF_ONLY',scope=__doc__.splitlines()[0],ABI_words=list(abi),Rust_exports=exports,selected_TU_real_consumer_relocations=refs,retained114_public_event_consumers=publicrefs,HOST_ABI_WITNESS_signal_address_relocations=witnessrefs,selected_production_C_signal_consumer='SOURCE_ELIDED_UNDER_SELECTED_FLAGS_NOT_REQUIRED_OR_CREDITED',actual_new_Rust_signal_relocations=rust_signal_refs,actual_new_Rust_signal_call_or_folding_proof='OPEN_REQUIRES_SEPARATE_CALL_OR_FOLD_ANALYSIS',actual_new_public_event_relocations=rust_event_refs,actual_new_public_event_consumer_or_folding_proof='OPEN_RETAINED114_REFS_ARE_NOT_NEWOBJECT_PROOF',fallback_C_functions=oldexports,fallback_C_sys_ptrace=fallback_sys_ptrace,matching_fallback_Rust=ref(out/'rust-fallback.o'),fallback_Rust_cfg='fullselectedcfg-minus-only-f03_ptrace_entry_candidate',retained_Rust_sections=len(retained_sections),fallback_retained_Rust_sections=len(fallback_retained_sections),artifacts=[ref(RETAINED/x) for x in ['rust-selected.o','selected.o','fallback.o','selected-joint.o']]+[ref(out/x) for x in ['rust-fallback.o','fallback-joint.o']],new_dynamic_behavior_tests_run=0,native_credit=0,production_acceptance=False)
 (out/'CHANGED-BOUNDARY-QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PTRACE3 PASS genuineABI/fullRust/setsigCconsumer/HOSTsignalwitness/publicsymbol/fallback; behavior-nativeOPEN')
if __name__=='__main__':main()
