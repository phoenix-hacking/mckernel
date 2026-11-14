# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,difflib
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');S=P/'source';bind=json.loads((P/'SOURCE-BINDINGS.json').read_text());root=Path(bind['changes']['smp_service.rs']['selected_original']['path']).parent
p=root/'smp_application.rs';base=p.read_text();s=base
s=s.replace('AtomicBool, AtomicI32, AtomicUsize, Ordering','AtomicBool, AtomicI32, AtomicU64, AtomicUsize, Ordering',1).replace('    syscall_cursor: AtomicUsize,','    syscall_cursor: AtomicUsize,\n    failure_contexts: AtomicU64,',1).replace('syscall_cursor: AtomicUsize::new(0),','syscall_cursor: AtomicUsize::new(0), failure_contexts: AtomicU64::new(0),',1)
helper='''    fn diagnostic_application_failure(&self, at: &'static str, entry: &Entry, cpu: i32, error: Error) {
        if let Ok(ticket) = self.failure_contexts.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
            |old| if old < 16 { Some(old + 1) } else { None }) {
            let diag = ticket + 1;
            let prepare = entry.prepare.as_ref().and_then(|image| image.result());
            let revoke = entry.fork_ingress.as_ref().is_some_and(|owner| owner.host_revoke.is_some());
            let sealed = entry.fork_ingress.as_ref().map(|owner| owner.sealed.load(Ordering::Acquire));
            pr_err!("IHK-A os={} g={} d={} at={} p={} c={} e={}\\n",
                self.owner.slot(), self.owner.generation(), diag, at, entry.cleanup.pid(), cpu, error.to_errno());
            pr_err!("IHK-B os={} g={} d={} prep={} ret={:?} rev={} inh={} seal={:?}\\n",
                self.owner.slot(), self.owner.generation(), diag, entry.prepare.is_some() as u8,
                prepare, revoke as u8, entry.inherited_root.is_some() as u8, sealed);
            pr_err!("IHK-F os={} g={} d={} need={} sch={} q={} closed={} drain={} res={} ret={:?}\\n",
                self.owner.slot(), self.owner.generation(), diag, entry.needs_cleanup as u8,
                entry.scheduled as u8, entry.quarantined as u8, entry.closed as u8,
                entry.syscalls.drained() as u8, entry.cleanup.reserved() as u8, entry.cleanup.result());
            pr_err!("IHK-K os={} g={} d={} token={:x}\\n",
                self.owner.slot(), self.owner.generation(), diag, entry.cleanup.token().wire());
        }
    }

'''
s=s.replace('    pub(crate) fn procfs_process(',helper+'    pub(crate) fn procfs_process(',1)
# This explicit branch replaces only the former ? propagation. It is entered
# AFTER the exact same backend_ready decision, while the same slots lock lives.
start=s.index('    pub(crate) fn procfs_process(');end=s.index('\n    }',start)+6;fragment=s[start:end];assert '        entry.backend_ready()?;' in fragment
fragment=fragment.replace('        entry.backend_ready()?;','''        if let Err(error) = entry.backend_ready() {
            self.diagnostic_application_failure("procfs_backend", entry, cpu, error);
            return Err(error);
        }''',1);s=s[:start]+fragment+s[end:]
needle='''                        if entry.needs_cleanup && !entry.quarantined {
                            entry.request_cleanup()?;
                        }'''
replacement='''                        if entry.needs_cleanup && !entry.quarantined {
                            if let Err(error) = entry.request_cleanup() {
                                // Returned sub-guard context only; no inference
                                // about a delivery or cleanup phase is made.
                                self.diagnostic_application_failure("prepare_cleanup", entry, entry.cleanup.cpu(), error);
                                return Err(error);
                            }
                        }''';assert needle in s;s=s.replace(needle,replacement,1)
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert p.read_bytes()==(R/'host-kernel/native-rust/smp_application.rs').read_bytes();(S/'smp_application.rs').write_text(s)
bind['changes']['smp_application.rs']=dict(selected_original=pin(p),canonical_preimage=pin(R/'host-kernel/native-rust/smp_application.rs'),private_postimage=pin(S/'smp_application.rs'))
bind['revised_root_requirements']='Final directed7filecoverage only. Existingfatalguards/ordering/ownership unchanged. Application diagnostics only2errorreturns underexistingslotslock; all fields actualhostscalars, unavailable private mailbox phases notinvented. Initialsource and missingfixtureconstant failure retained.'
patch=''
for rel,row in bind['changes'].items():patch+=''.join(difflib.unified_diff(Path(row['selected_original']['path']).read_text().splitlines(True),Path(row['private_postimage']['path']).read_text().splitlines(True),fromfile='a/host-kernel/native-rust/'+rel,tofile='b/host-kernel/native-rust/'+rel,n=4))
(P/'PRIVATE-DIAGNOSTIC.patch').write_text(patch);bind['patch']=pin(P/'PRIVATE-DIAGNOSTIC.patch');(P/'SOURCE-BINDINGS.json').write_text(json.dumps(bind,indent=2)+'\n');print(json.dumps(dict(patch=bind['patch'],changed_keys=list(bind['changes']))))
