from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
H=OUT/'harness-1';H.mkdir(exist_ok=False)
def item(s,needle):
 start=s.index(needle);a=s.index('{',start);n=1;i=a+1
 while n:
  n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]
# Freeze adapters/dependencies separately; none of the reviewed files change.
for name in ['application_rpc.rs','abi/application.rs']:
 p=H/Path(name).name;p.write_bytes((ROOT/'host-kernel/native-rust'/name).read_bytes())
backend=(ROOT/'host-kernel/native-rust/smp_application.rs').read_text()
meta='\n'.join(item(backend,x) for x in ['struct InheritedRoot {','enum ForkResponseLocation {','pub(crate) struct PreparedForkIngress {','struct BackendForkLeaseV4 {','impl Drop for BackendForkLeaseV4 {'])
frame=(ROOT/'host-kernel/native-rust/sysfs_memory.rs').read_text()
frames='\n'.join(item(frame,x) for x in ['    fn read_current_fork_carrier(', '    pub(crate) fn current_fork_control_frame(', '    pub(crate) fn write_fork_control_frame('])
(H/'production-provider-metadata.rs').write_text(meta)
(H/'production-frame-read-write.rs').write_text(frames)
for variant in ['original','candidate']:
 d=H/variant;d.mkdir()
 for name in ['application_syscall.rs','smp_application_syscall.rs','current_fork_control.rs']:
  src=OUT/('source' if variant=='candidate' else 'original')/'host-kernel/native-rust'/name
  data=src.read_text()
  if name=='current_fork_control.rs':data+='\nimpl OwnedRevoke { pub(super) fn fixture_phase(&self)->ControlPhase {self.phase} }\n'
  if name=='application_syscall.rs':data+='\nimpl<M: ResponseMemory> Response<M> { pub(crate) fn fixture_replace_request(&mut self, other: Request) { self.request=other; } }\n'
  if name=='smp_application_syscall.rs':data+='\n'+(OUT/'mailbox-probes.rs').read_text()
  (d/name).write_text(data)
 template=(OUT/'harness-template.rs').read_text().replace('@META@',meta).replace('@FRAMES@',frames)
 template=template.replace(' mod current_fork_control;', ' #[path=\"'+str(d/'current_fork_control.rs')+'\"] mod current_fork_control;').replace('\"C\"fn','\"C\" fn')
 template=template.replace('@RPC@',str(H/'application_rpc.rs')).replace('@ABI@',str(H/'application.rs'))
 (d/'actual.rs').write_text(template)
manifest={'status':'MATERIALIZED_UNRUN','reviewed_source_freeze_sha256':hashlib.sha256((OUT/'SOURCE-FREEZE.json').read_bytes()).hexdigest(),'variants':['original','candidate'],'scope':'Functional OS/apps plus Rust/reviewed assembly cutover. Actual complete Request/Response/Delivery/Mailbox/current-fork-control bodies; explicit std/physical-memory and outer Entry/ChildTaskMm adapters. No native ACK or executor proof.','files':[]}
for p in sorted(H.rglob('*')):
 if p.is_file():manifest['files'].append({'path':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(H/'HARNESS-FREEZE.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Harness materialized; no compiler/test executed:',H)
