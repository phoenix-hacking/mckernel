"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual real-type ABI and live C consumer edges only; no dynamic/native acceptance.
"""
from pathlib import Path
import hashlib,importlib.util,json,struct,sys
D=Path(__file__).resolve().parent
helper=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/f02-source38-next-current-integration-source-1/check_thirteen_storage.py')
spec=importlib.util.spec_from_file_location('existing_elf_wakeup4',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);Elf=m.Elf
names=['ptrace_wakeup_clear_saved_bridge','ptrace_wakeup_set_single_step_bridge','ptrace_wakeup_trace_syscall_bridge','ptrace_wakeup_pending_take_bridge']
def ref(p):
 raw=Path(p).read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def words(e,name):
 defs=e.definitions(name);assert len(defs)==1;s=defs[0];z=e.sections[s['ndx']];assert s['kind']==1 and s['bind']==1 and s['size']==128 and z['flags']&2 and not z['flags']&5 and z['align']>=8
 offset=z['off']+s['value']-z['addr'];return struct.unpack('<16Q',e.data[offset:offset+128])
def function(e,name,global_required):
 defs=e.definitions(name);assert len(defs)==1;f=defs[0];assert f['kind']==2 and f['size']>0 and e.sections[f['ndx']]['flags']&4
 if global_required:assert f['bind']==1
 return f
def main():
 out=Path(sys.argv[1]);assert out.resolve()==(D/'HOST-output-proposed-1').resolve()
 rust,rf,c,cf,j,jf=[Elf(out/n) for n in ['rust-selected.o','rust-fallback.o','selected.o','fallback.o','selected-joint.o','fallback-joint.o']]
 abi=words(rust,'f03_wakeup4_HOST_ABI');assert abi==words(c,'f03_wakeup4_C_ABI')==words(cf,'f03_wakeup4_C_ABI')==words(j,'f03_wakeup4_HOST_ABI');assert abi[:6]==(4,4,8,8,8,8)
 consumer=function(c,'ptrace_wakeup_sig',False);section=c.sections[consumer['ndx']]['name'];edges={}
 for name in names:
  function(rust,name,True);function(j,name,True);assert not c.definitions(name) and not rf.definitions(name)
  function(cf,name,False);function(jf,name,False)
  edges[name]=[r for r in c.allocated_references(name) if r['section']==section and consumer['value']<=r['offset']<consumer['value']+consumer['size']]
  assert edges[name],(name,'real ptrace_wakeup_sig callback consumer required; no HOST address witness substitutes')
  assert not [s for s in j.symbols if s['name']==name and s['ndx']==0]
 retained=[]
 for origin,linked in [(rust,j),(rf,jf)]:
  sections=[s for s in origin.sections if s['flags']&0x200000 and s['flags']&2];assert sections
  for s in sections:
   matches=[z for z in linked.sections if z['name']==s['name']];assert len(matches)==1 and matches[0]['flags']&0x200000
  retained.append(len(sections))
 report=dict(scope=__doc__.splitlines()[0],status='PASS_WAKEUP4_GENUINE_ABI_CURRENT_C_CONSUMER_AND_MATCHED_FALLBACK_ELF_ONLY',ABI_words=list(abi),real_current_consumer=consumer,selected_consumer_edges=edges,retained_sections=retained,artifacts=[ref(out/n) for n in ['rust-selected.o','rust-fallback.o','selected.o','fallback.o','selected-joint.o','fallback-joint.o']],dynamic_behavior_run=0,production_default_link_native='OPEN',wholefile_retirement=False)
 (out/'WAKEUP4-ABI-CONSUMER-QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
 print('WAKE4 PASS genuine16wordABI/liveCcallbackconsumer/matchedselectedfallback/GNU_RETAIN; default-nativeOPEN')
if __name__=='__main__':main()
