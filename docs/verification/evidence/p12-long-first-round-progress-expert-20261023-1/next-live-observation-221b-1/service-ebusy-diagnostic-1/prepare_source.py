# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,difflib
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;S=P/'source';F=P/'fixture'
REPORT=R/'docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/next-live-observation-221b-1/trace-retention-failure-1/FINITE-CAUSE-AND-PROVENANCE.json'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def function(s,marker):
 lines=s.splitlines(keepends=True);hits=[i for i,x in enumerate(lines) if x.lstrip().startswith(marker)];assert len(hits)==1,(marker,hits);a=hits[0];indent=len(lines[a])-len(lines[a].lstrip());end=next(i for i in range(a+1,len(lines)) if lines[i].rstrip()==' '*indent+'}');return ''.join(lines[a:end+1]).rstrip('\n')
assert pin(REPORT)['sha256']=='105a9a49303e290dd55644f15bce9acc53c0225cca12fc2ea6105658ae343b56';facts=json.loads(REPORT.read_text());refs=facts['SDK6_provenance']['focused_sources'];old={}
for name in ['smp_service.rs','sysfs_memory.rs']:
 p=Path(refs[name]['path']);assert pin(p)==refs[name];assert pin(R/'host-kernel/native-rust'/name)['sha256']==refs[name]['sha256'];old[name]=p.read_text()
s=old['smp_service.rs'];m=old['sysfs_memory.rs']
origin='''// Diagnostic-only types. They carry host-owned route fields or the already
// decoded message header, never packet padding or an inferred worker/delivery.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FailureOrigin {
    Packet { channel: usize, guest_cpu: u32, port: i32, message: i32 },
    ControlPump,
    RegularPump,
    PublishRemote,
    PublishApplications,
    PublishSyscalls,
    AdvanceApplications,
    PublishProcfs,
    Metadata,
    Zeroing,
}

// A separate saturating diagnostic budget does not change existing counters,
// admission, ownership, errors, quarantine or the service's work scheduling.
fn diagnostic_ticket(counter: &AtomicU64) -> bool {
    counter.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
        if old < 16 { Some(old + 1) } else { None }
    }).is_ok()
}

'''
ns=s.replace('struct Metadata {',origin+'struct Metadata {',1)
ns=ns.replace('    rejected: AtomicU64,','    rejected: AtomicU64,\n    failure_contexts: AtomicU64,',1)
oldfail=function(s,'fn fail(&self, error: Error)');newfail=oldfail.replace('fn fail(&self, error: Error)','fn fail(&self, error: Error, origin: FailureOrigin)',1).replace('        if self.application.fail_service', '''        if diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-SMP: service failure context os={} generation={} origin={:?} errno={}; diagnostic only, owners unchanged\\n",
                self.owner.slot(), self.owner.generation(), origin, error.to_errno());
        }
        if self.application.fail_service''',1);ns=ns.replace(oldfail,newfail,1)
regular=function(s,'fn pump_regular(&self)');newregular=regular.replace('let (port, packet) = {','let (port, guest_cpu, packet) = {',1).replace('(entry.channel.port, packet)','(entry.channel.port, entry.channel.guest_cpu, packet)',1).replace('self.fail(error);','''self.fail(error, FailureOrigin::Packet {
                        channel: index, guest_cpu, port,
                        message: i32::from_le_bytes(packet[8..12].try_into().unwrap()),
                    });''',1);ns=ns.replace(regular,newregular,1)
pump=function(s,'fn pump(&self)');newpump=pump
for call,tag in [('pump_master','ControlPump'),('pump_regular','RegularPump'),('publish_remote','PublishRemote'),('publish_applications','PublishApplications'),('publish_syscalls','PublishSyscalls'),('application.advance','AdvanceApplications'),('publish_procfs','PublishProcfs')]:
 prefix='self.'+call+'()';needle='if let Err(error) = '+prefix+' {\n            self.fail(error);';replacement='if let Err(error) = '+prefix+' {\n            self.fail(error, FailureOrigin::'+tag+');';assert needle in newpump,call;newpump=newpump.replace(needle,replacement,1)
ns=ns.replace(pump,newpump,1)
for call,tag in [('metadata','Metadata'),('zeroing','Zeroing')]:
 needle='if let Err(error) = entry.runtime.'+call+'() {\n                    entry.runtime.fail(error);';assert needle in ns;ns=ns.replace(needle,'if let Err(error) = entry.runtime.'+call+'() {\n                    entry.runtime.fail(error, FailureOrigin::'+tag+');',1)
needle='error: AtomicI32::new(0), completed: AtomicU64::new(0), rejected: AtomicU64::new(0),';assert needle in ns;ns=ns.replace(needle,needle+'\n            failure_contexts: AtomicU64::new(0),',1)
assert 'self.fail(error);' not in ns and 'entry.runtime.fail(error);' not in ns
conflict_types='''// Diagnostic snapshots contain only initialized, host-owned ledger fields.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ConflictKind { Fixed, Request, Payload, Response, ExecPayload, Snoop, Procfs, Zeroing }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FailureConflict {
    kind: ConflictKind,
    slot: usize,
    member: Option<usize>,
    serial: Option<u64>,
    span: Span,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SyscallFailureContext {
    cpu: i32, pid: i32, requester: i32, target: i32, number: u64,
    response: u64, response_end: Option<u64>,
    conflict: Option<FailureConflict>,
}

fn syscall_failure_context(request: &SyscallRequest, conflict: Option<FailureConflict>) -> SyscallFailureContext {
    SyscallFailureContext {
        cpu: request.cpu(), pid: request.pid(), requester: request.requester(),
        target: request.target(), number: request.number(),
        response: request.response(), response_end: request.response().checked_add(RESPONSE_BYTES as u64),
        conflict,
    }
}

'''
nm=m.replace('struct Ledger {',conflict_types+'struct Ledger {',1)
scanner='''    // Read-only diagnostic traversal after the ORIGINAL conflicts predicate
    // already chose EBUSY. Keep its first-match order; never use this observer
    // to admit/reject, retire a tag, acquire a claim or interpret guest bytes.
    fn diagnostic_conflict(&self, span: Span, snoops: bool) -> Option<FailureConflict> {
        for (slot, old) in self.fixed.iter().enumerate() {
            if old.overlaps(span) {
                return Some(FailureConflict { kind: ConflictKind::Fixed, slot, member: None, serial: None, span: *old });
            }
        }
        for (kind, slots) in [(ConflictKind::Request, &self.requests), (ConflictKind::Payload, &self.payloads), (ConflictKind::Response, &self.responses)] {
            for (slot, old) in slots.iter().enumerate() {
                if let Some(old) = old {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (slot, group) in self.exec_payloads.iter().enumerate() {
            if let Some(group) = group {
                for (member, old) in group.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind: ConflictKind::ExecPayload, slot, member: Some(member), serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (kind, tags, enabled) in [(ConflictKind::Snoop, &self.snoops, snoops), (ConflictKind::Procfs, &self.procfs, true), (ConflictKind::Zeroing, &self.zeroing, true)] {
            if enabled {
                for (slot, old) in tags.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        None
    }

'''
nm=nm.replace('    fn tag(&mut self, span: Span) -> Result<Tagged> {',scanner+'    fn tag(&mut self, span: Span) -> Result<Tagged> {',1)
nm=nm.replace('    numa_nodes: usize,\n    #[pin]','    numa_nodes: usize,\n    failure_contexts: AtomicU64,\n    #[pin]',1)
nm=nm.replace('owner, direct_map, extents, layout, numa_nodes,','owner, direct_map, extents, layout, numa_nodes,\n                failure_contexts: AtomicU64::new(0),',1)
original_syscall=function(m,'pub(super) fn syscall(');body=original_syscall[original_syscall.index('{')+1:original_syscall.rindex('}')].strip('\n');assert body.count('if ledger.conflicts(span, true) {')==1
observed_body=body.replace('if ledger.conflicts(span, true) {\n            return Err(EBUSY);','if ledger.conflicts(span, true) {\n            conflict = ledger.diagnostic_conflict(span, true);\n            return Err(EBUSY);',1)
wrapped='''    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let mut conflict = None;
        let result = (|| {
'''+''.join('    '+line+'\n' for line in observed_body.splitlines())+'''        })();
        // The original ledger guard has ended. The copied snapshot has no
        // borrowed tag/pointer, and this diagnostic runs BEFORE returning the
        // same error to the unchanged mailbox/Remote quarantine path.
        if let Err(error) = &result {
            if *error != EAGAIN && super::diagnostic_ticket(&self.failure_contexts) {
                let context = syscall_failure_context(request, conflict);
                pr_err!("IHK-SMP: service failure context os={} generation={} origin=syscall_response_claim errno={} route={:?}; diagnostic only, owners unchanged\\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno(), context);
            }
        }
        result
    }'''
nm=nm.replace(original_syscall,wrapped,1)
patch='';new={'smp_service.rs':ns,'sysfs_memory.rs':nm}
for name,text in new.items():
 write(S/name,text);patch+=''.join(difflib.unified_diff(old[name].splitlines(True),text.splitlines(True),fromfile='a/host-kernel/native-rust/'+name,tofile='b/host-kernel/native-rust/'+name,n=4))
write(P/'PRIVATE-DIAGNOSTIC.patch',patch);write(F/'ORIGINAL-Memory-syscall.rs',original_syscall+'\n');write(F/'ACTUAL-Memory-syscall.rs',wrapped+'\n')
bind=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='SOURCE_ONLY_DIAGNOSTIC_CANDIDATE_NOT_REPAIR_NOT_COMPILED',retained_expert_facts=pin(REPORT),selected_SDK6_source_identity=facts['SDK6_provenance']['source_identity'],selected_SDK6_input_map=facts['SDK6_provenance']['input_map'],changes={name:dict(selected_original=refs[name],canonical_preimage=pin(R/'host-kernel/native-rust'/name),private_postimage=pin(S/name)) for name in new},patch=pin(P/'PRIVATE-DIAGNOSTIC.patch'),unmodified_error_ownership_modules={name:refs[name] for name in ['application_syscall.rs','smp_application_syscall.rs','smp_application.rs']},unchanged_policy='No retries, EBUSY handling, admission decision, claim/tag release, quarantine/ACK/deadline/oracle changes. Ledger conflicts bool predicate original bytes remain. Only diagnostics after decisions/before unchanged failures.',failure_classification='Actualround48serviceEBUSY originunknown; firstconflict candidate is not provedcause. No worker/delivery/packetidentity inferred from adjacentvalidrecords.',diagnostic_budgets='Separate16-entry saturating counters per Memory and perRuntime, no existingcounters modified',compiler_jobs=0,runtime_jobs=0,canonical_mutations=0)
write(P/'SOURCE-BINDINGS.json',json.dumps(bind,indent=2)+'\n');print(json.dumps(dict(patch=pin(P/'PRIVATE-DIAGNOSTIC.patch'),bindings=pin(P/'SOURCE-BINDINGS.json'),changed_files=list(new))))
