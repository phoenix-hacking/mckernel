# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Additive source revision for root's exact fatal-branch and255byte requirements.
from pathlib import Path
import json,hashlib,difflib,shutil
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');S=P/'source';B=P/'initial-candidate-preserved';B.mkdir(exist_ok=True)
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def function(s,marker):
 lines=s.splitlines(keepends=True);hits=[i for i,x in enumerate(lines) if x.lstrip().startswith(marker)];assert len(hits)==1,(marker,hits);a=hits[0];indent=len(lines[a])-len(lines[a].lstrip());end=next(i for i in range(a+1,len(lines)) if lines[i].rstrip()==' '*indent+'}');return ''.join(lines[a:end+1]).rstrip('\n')
for rel in ['source/smp_service.rs','source/sysfs_memory.rs','PRIVATE-DIAGNOSTIC.patch','SOURCE-BINDINGS.json','FIXTURE-SOURCE-BINDINGS.json','EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json','prepare_fixture.py']:
 dst=B/rel;dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copyfile(P/rel,dst)
bind=json.loads((P/'SOURCE-BINDINGS.json').read_text());s=(S/'smp_service.rs').read_text();m=(S/'sysfs_memory.rs').read_text()
# Scalar observer tokens correlate bounded diagnostics; these are NOT protocol
# packet/worker/delivery identifiers and never influence error handling.
oldticket=function(s,'fn diagnostic_ticket(');newticket='''fn diagnostic_ticket(counter: &AtomicU64) -> Option<u64> {
    counter.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
        if old < 16 { Some(old + 1) } else { None }
    }).ok().map(|old| old + 1)
}''';s=s.replace(oldticket,newticket,1)
origin_impl='''impl FailureOrigin {
    fn label(self) -> &'static str {
        match self {
            Self::Packet { .. } => "packet_dispatch",
            Self::ControlPump => "control_pump", Self::RegularPump => "regular_pump",
            Self::PublishRemote => "publish_remote", Self::PublishApplications => "publish_apps",
            Self::PublishSyscalls => "publish_syscalls", Self::AdvanceApplications => "advance_apps",
            Self::PublishProcfs => "publish_procfs", Self::Metadata => "metadata", Self::Zeroing => "zeroing",
        }
    }
}

''';s=s.replace('// A separate saturating diagnostic budget',origin_impl+'// A separate saturating diagnostic budget',1)
oldfail=function(s,'fn fail(&self, error: Error, origin:');original=Path(bind['changes']['smp_service.rs']['selected_original']['path']).read_text();basefail=function(original,'fn fail(&self, error: Error)');newfail=basefail.replace('fn fail(&self, error: Error)','fn fail(&self, error: Error, origin: FailureOrigin)',1).replace('        if self.application.fail_service','        self.failure_context(error, origin);\n        if self.application.fail_service',1)
context='''    fn failure_context(&self, error: Error, origin: FailureOrigin) {
        if let Some(diag) = diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-E os={} g={} d={} at={} e={}\\n",
                self.owner.slot(), self.owner.generation(), diag, origin.label(), error.to_errno());
            if let FailureOrigin::Packet { channel, guest_cpu, port, message } = origin {
                pr_err!("IHK-P os={} g={} d={} ch={} c={} port={} m={:x}\\n",
                    self.owner.slot(), self.owner.generation(), diag, channel, guest_cpu, port, message);
            }
        }
    }

''';s=s.replace(oldfail,context+newfail,1)
# Replace unbounded Debug route dumps by correlated scalar lines. Prefix budget
# is tested conservatively at96bytes; each complete rendered line <=255bytes.
helpers='''fn log_conflict(os: u32, generation: u64, diag: u64, conflict: Option<FailureConflict>) {
    if let Some(old) = conflict {
        pr_err!("IHK-C os={} g={} d={} k={:?} i={} j={:?} s={:?}\\n",
            os, generation, diag, old.kind, old.slot, old.member, old.serial);
        pr_err!("IHK-O os={} g={} d={} a={:x} b={:x}\\n",
            os, generation, diag, old.span.physical, old.span.end);
    } else {
        pr_err!("IHK-C os={} g={} d={} k=none\\n", os, generation, diag);
    }
}

fn log_syscall_failure(os: u32, generation: u64, diag: u64, error: Error, context: SyscallFailureContext) {
    pr_err!("IHK-E os={} g={} d={} at=syscall_claim e={}\\n", os, generation, diag, error.to_errno());
    pr_err!("IHK-P os={} g={} d={} c={} p={} rq={} to={}\\n",
        os, generation, diag, context.cpu, context.pid, context.requester, context.target);
    if let Some(end) = context.response_end {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b={:x}\\n",
            os, generation, diag, context.number, context.response, end);
    } else {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b=none\\n",
            os, generation, diag, context.number, context.response);
    }
    log_conflict(os, generation, diag, context.conflict);
}

''';m=m.replace('struct Ledger {',helpers+'struct Ledger {',1)
old='''            if *error != EAGAIN && super::diagnostic_ticket(&self.failure_contexts) {
                let context = syscall_failure_context(request, conflict);
                pr_err!("IHK-SMP: service failure context os={} generation={} origin=syscall_response_claim errno={} route={:?}; diagnostic only, owners unchanged\\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno(), context);
            }'''
new='''            if *error != EAGAIN {
                if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
                    log_syscall_failure(self.owner.slot(), self.owner.generation(), diag,
                        *error, syscall_failure_context(request, conflict));
                }
            }''';assert old in m;m=m.replace(old,new,1)
# Helpers format only retained host scalar snapshots, never guest strings,
# raw packets/padding, or arbitrary pointers. They never touch a ledger/claim.
methods='''    fn diagnostic_conflict_failure(&self, at: &'static str, span: Span,
        conflict: Option<FailureConflict>, own: Option<Tagged>, node_overlap: bool,
        route: Option<(i32, i32)>) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-E os={} g={} d={} at={} e=-16 node={}\\n",
                self.owner.slot(), self.owner.generation(), diag, at, node_overlap as u8);
            pr_err!("IHK-S os={} g={} d={} a={:x} b={:x}\\n",
                self.owner.slot(), self.owner.generation(), diag, span.physical, span.end);
            if let Some((pid, cpu)) = route {
                pr_err!("IHK-P os={} g={} d={} p={} c={}\\n",
                    self.owner.slot(), self.owner.generation(), diag, pid, cpu);
            }
            if let Some(own) = own {
                pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\\n",
                    self.owner.slot(), self.owner.generation(), diag, own.serial, own.span.physical, own.span.end);
            }
            log_conflict(self.owner.slot(), self.owner.generation(), diag, conflict);
        }
    }

    fn diagnostic_completion_failure(&self, kind: wire::Kind, tag: Tagged, operation_error: i32, busy: i32) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-M os={} g={} d={} k={:?} busy={} op_e={} e=-16\\n",
                self.owner.slot(), self.owner.generation(), diag, kind, busy, operation_error);
            pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\\n",
                self.owner.slot(), self.owner.generation(), diag, tag.serial, tag.span.physical, tag.span.end);
        }
    }

''';m=m.replace('    pub(super) fn syscall(',methods+'    pub(super) fn syscall(',1)
procfs=function(m,'pub(super) fn procfs(')
pf=procfs.replace('''if ledger.conflicts(span, true) {
            return Err(EBUSY);''','''if ledger.conflicts(span, true) {
            self.diagnostic_conflict_failure("procfs_overlap", span,
                ledger.diagnostic_conflict(span, true), None, false, None);
            return Err(EBUSY);''',1)
# Keep the existing ONE atomic completion load and its ordering, copy only its
# scalar value for a diagnostic on the same original nonzero error branch.
old='''        if create
            && unsafe { AtomicI32::from_ptr(address as *mut i32) }.load(Ordering::Acquire) != 0
        {
            return Err(EBUSY);
        }'''
new='''        if create {
            let done = unsafe { AtomicI32::from_ptr(address as *mut i32) }.load(Ordering::Acquire);
            if done != 0 {
                if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
                    pr_err!("IHK-W os={} g={} d={} at=procfs_create a={:x} v={} e=-16\\n",
                        self.owner.slot(), self.owner.generation(), diag, physical, done);
                }
                return Err(EBUSY);
            }
        }''';assert old in pf;pf=pf.replace(old,new,1);m=m.replace(procfs,pf,1)
# Pure ABI completion observer captures the existing busy load itself; no
# second guest read, ledger access or post-release observation is introduced.
paths={'sysfs_zeroing.rs':R/'host-kernel/native-rust/sysfs_zeroing.rs','sysfs_remote.rs':R/'host-kernel/native-rust/sysfs_remote.rs','sysfs_rpc.rs':R/'host-kernel/native-rust/sysfs_rpc.rs','abi/sysfs_request.rs':R/'host-kernel/native-rust/abi/sysfs_request.rs'}
base={key:p.read_text() for key,p in paths.items()};w=base['abi/sysfs_request.rs'];complete=function(w,'pub(crate) unsafe fn complete(')
observed=complete.replace('fn complete(', 'fn complete_observed(',1).replace('    handle: Option<u64>,\n','    handle: Option<u64>,\n    on_busy: impl FnOnce(CompletionBusy),\n',1)
observed=observed.replace('''    if busy.load(Ordering::Relaxed) != 1 {
        return Err(-16);
    }''','''    let value = busy.load(Ordering::Relaxed);
    if value != 1 {
        on_busy(CompletionBusy { kind, value });
        return Err(-16);
    }''',1)
legacy='''#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CompletionBusy { pub(crate) kind: Kind, pub(crate) value: i32 }

pub(crate) unsafe fn complete(kind: Kind, request: *mut u8, error: i32, handle: Option<u64>) -> Result<(), i32> {
    unsafe { complete_observed(kind, request, error, handle, |_| {}) }
}

''';w=w.replace(complete,legacy+observed,1)
old='''unsafe { wire::complete(self.kind, self.address as *mut u8, error, handle) }.map_err(errno)''';new='''unsafe { wire::complete_observed(self.kind, self.address as *mut u8, error, handle, |busy| {
            // This is the original failed busy load, under the still-held
            // exclusive ledger mutex, before any final store or peer reuse.
            self.memory.diagnostic_completion_failure(busy.kind, self.tag, error, busy.value);
        }) }.map_err(errno)''';assert old in m;m=m.replace(old,new,1)
# Four exact allocator-zeroing EBUSY branches; no ordering/CAS/release changes.
z=base['sysfs_zeroing.rs'];replacements=[('''if ledger.conflicts(control_span, true) {
                return Err(EBUSY);''','''if ledger.conflicts(control_span, true) {
                self.diagnostic_conflict_failure("zero_control", control_span,
                    ledger.diagnostic_conflict(control_span, true), None, false, Some((request.pid, request.cpu)));
                return Err(EBUSY);'''),('''if header.overlaps(node_span) || ledger.conflicts(header, true) {
                    return Err(EBUSY);''','''if header.overlaps(node_span) || ledger.conflicts(header, true) {
                    self.diagnostic_conflict_failure("zero_header", header,
                        ledger.diagnostic_conflict(header, true), Some(control), header.overlaps(node_span), Some((request.pid, request.cpu)));
                    return Err(EBUSY);'''),('''if span.overlaps(node_span) || ledger.conflicts(span, true) {
                    return Err(EBUSY);''','''if span.overlaps(node_span) || ledger.conflicts(span, true) {
                    self.diagnostic_conflict_failure("zero_chunk", span,
                        ledger.diagnostic_conflict(span, true), Some(control), span.overlaps(node_span), Some((request.pid, request.cpu)));
                    return Err(EBUSY);'''),('''if ledger.conflicts(Span::new(physical, wire::HEADER_BYTES)?, true) {
                    return Err(EBUSY);''','''if ledger.conflicts(Span::new(physical, wire::HEADER_BYTES)?, true) {
                    let candidate = Span::new(physical, wire::HEADER_BYTES)?;
                    self.diagnostic_conflict_failure("zeroed_head", candidate,
                        ledger.diagnostic_conflict(candidate, true), Some(chunk.tag), false, None);
                    return Err(EBUSY);''')]
for before,after in replacements:assert before in z;z=z.replace(before,after,1)
# Exchange observer is pure/read-only, under caller's existing state lock and
# only consulted after the ORIGINAL accept returns the same EBUSY.
rpc=base['sysfs_rpc.rs'];rpc_types='''#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ReplyFailurePhase { Queued, Published, Complete }
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ReplyFailureContext {
    pub(crate) message: i32, pub(crate) error: i32, pub(crate) token: u64,
    pub(crate) result: i64, pub(crate) pending_token: u64, pub(crate) phase: ReplyFailurePhase,
}

''';rpc=rpc.replace('pub(crate) struct Exchange {',rpc_types+'pub(crate) struct Exchange {',1)
accessor='''    pub(crate) fn reply_failure_context(&self, packet: &[u8]) -> Option<ReplyFailureContext> {
        if packet.len() != PACKET_BYTES { return None; }
        let pending = self.pending?;
        Some(ReplyFailureContext {
            message: i32::from_le_bytes(packet[8..12].try_into().unwrap()),
            error: i32::from_le_bytes(packet[12..16].try_into().unwrap()),
            token: u64::from_le_bytes(packet[24..32].try_into().unwrap()),
            result: i64::from_le_bytes(packet[32..40].try_into().unwrap()),
            pending_token: pending.token.wire(),
            phase: match pending.phase { Phase::Queued => ReplyFailurePhase::Queued,
                Phase::Published => ReplyFailurePhase::Published, Phase::Complete(_) => ReplyFailurePhase::Complete },
        })
    }

''';rpc=rpc.replace('    pub(crate) fn completed(',accessor+'    pub(crate) fn completed(',1)
remote=base['sysfs_remote.rs'];remote=remote.replace('AtomicBool, Ordering','AtomicBool, AtomicU64, Ordering',1).replace('    data: SharedData,','    data: SharedData,\n    failure_contexts: AtomicU64,',1).replace('''                data,
                state <-''','''                data,
                failure_contexts: AtomicU64::new(0),
                state <-''',1)
# Remote module keeps a separate saturating error-only budget; no printk while
# decoding unknown packet kinds or after state lock release/phase mutation.
old='''        state.exchange.accept(packet).map_err(errno)?;''';new='''        if let Err(error) = state.exchange.accept(packet) {
            if error == -16 {
                if let Some(context) = state.exchange.reply_failure_context(packet) {
                    if let Ok(diag) = self.failure_contexts.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
                        |old| if old < 16 { Some(old + 1) } else { None }) {
                        pr_err!("IHK-R os={} g={} d={} m={:x} t={:x} pt={:x} ph={:?} e=-16\\n",
                            self.data.owner.slot(), self.data.owner.generation(), diag + 1,
                            context.message, context.token, context.pending_token, context.phase);
                        pr_err!("IHK-V os={} g={} d={} peer_e={} value={}\\n",
                            self.data.owner.slot(), self.data.owner.generation(), diag + 1, context.error, context.result);
                    }
                }
            }
            return Err(errno(error));
        }''';assert old in remote;remote=remote.replace(old,new,1)
newfiles={'smp_service.rs':s,'sysfs_memory.rs':m,'sysfs_zeroing.rs':z,'sysfs_remote.rs':remote,'sysfs_rpc.rs':rpc,'abi/sysfs_request.rs':w}
# Exact retained SDK6map paths are authoritative for every new source key.
root=Path(bind['changes']['smp_service.rs']['selected_original']['path']).parent
patch='';changes={}
for rel,text in newfiles.items():
 original_path=root/rel;canonical=R/'host-kernel/native-rust'/rel;assert original_path.read_bytes()==canonical.read_bytes()
 write(S/rel,text);changes[rel]=dict(selected_original=pin(original_path),canonical_preimage=pin(canonical),private_postimage=pin(S/rel));patch+=''.join(difflib.unified_diff(original_path.read_text().splitlines(True),text.splitlines(True),fromfile='a/host-kernel/native-rust/'+rel,tofile='b/host-kernel/native-rust/'+rel,n=4))
bind['changes']=changes;bind['diagnostic_budgets']='Separate16-entry saturating counters perMemory/Runtime/Remote; compactcorrelatedlines,96byteprefixbudget. No existingcounters modified.';bind['revised_root_requirements']='Final foregroundbranchmap consumed; Memory.claim EBUSY swallowed/unmodified, syscallclaim distinct; metadata finalbusy observedonce before finalstore; actualremoteTOKEN24..32/phase;4zeroingoriginbranches beforeErr. Backend/privatePREPARE flags requireseparateappscopegrant.'
write(P/'PRIVATE-DIAGNOSTIC.patch',patch);bind['patch']=pin(P/'PRIVATE-DIAGNOSTIC.patch');write(P/'SOURCE-BINDINGS.json',json.dumps(bind,indent=2)+'\n');write(P/'REVISION-FOR-LINE-BOUND-AND-FATAL-ORIGINS.json',json.dumps(dict(scope=bind['scope'],status='SOURCE_REVISION_ROOT_STEERING_NOT_SEMANTIC_REPAIR',initial_source_preserved=str(B),changed_keys=list(changes),printk_prefix_budget_bytes=96,parser_total_line_bytes=255,compiler_family_history='one initial fixturemissingREQUEST_MESSAGE constant; boundedfixturecorrection pending; no nativecandidate executed'),indent=2)+'\n')
print(json.dumps(dict(patch=bind['patch'],changed_keys=list(changes))))
