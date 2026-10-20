from pathlib import Path
import re,hashlib,json,difflib
P=Path(__file__).parent; B=P/'base/host-kernel/native-rust'; S=P/'source/host-kernel/native-rust'
def read(n): return (B/n).read_text()
def put(n,t): (S/n).write_text(t)
def once(t,a,b):
 assert t.count(a)==1,(a[:80],t.count(a));return t.replace(a,b,1)
abi='''
// Distinct synchronous, park-only control ABI. No receipt/MM/terminal authority.
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) struct ForkControlV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) epoch: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) physical: u64,
    pub(crate) response: u64,
}
// Payload is a shared metadata borrow owned by the exact IHK pending claim.
// No pointer, claim or ticket may escape either synchronous callback.
pub(crate) type ForkControlParkV1 = unsafe extern "C" fn(*mut c_void, *const c_void) -> i32;
pub(crate) type ForkControlResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkControlV1, Option<ForkControlParkV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareControlV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkControlResolveV1>, *mut c_void,
) -> i32;
'''
put('abi/application.rs',read('abi/application.rs')+abi)
t=read('smp_application.rs')
t=once(t,'pub(crate) use fork_link::PreparedLinkTicket;','pub(crate) use fork_link::{PreparedLinkTicket, PreparedControlTicket};')
t=once(t,'    ack: Option<ForkAckRecord>,','    ack: Option<ForkAckRecord>,\n    control: Option<fork_link::ForkControlOwner>,')
t=once(t,'link: None, ack: None, held_lease: None,','link: None, ack: None, control: None, held_lease: None,')
t=once(t,'    if fork_ingress::publication_frozen(slots, parent, cpu) { return true; }','    if fork_ingress::publication_frozen(slots, parent, cpu)\n        || fork_link::control_publication_frozen(slots, parent, cpu) { return true; }')
t=once(t,'    fork_link::authorize_return(slots, parent, worker, serial, cpu, value)?;','    fork_link::authorize_control_return(slots, parent, worker, serial)?;\n    fork_link::authorize_return(slots, parent, worker, serial, cpu, value)?;')
assert t.count('            let ack = fork.ack.as_ref().ok_or(EIO)?;') == 2
t=t.replace('            let ack = fork.ack.as_ref().ok_or(EIO)?;', '            if fork.control.is_some() { return Err(EBUSY); }\n            let ack = fork.ack.as_ref().ok_or(EIO)?;')
t=once(t,'    if stage == FORK_GUEST_DESTROYED_V1 && fork.retained_parent.is_some() { return Err(EBUSY); }','    if fork.control.is_some()\n        || stage == FORK_GUEST_DESTROYED_V1 && fork.retained_parent.is_some() { return Err(EBUSY); }')
put('smp_application.rs',t)
t=once(read('smp_fork_ingress.rs'),'held_lease: None, link: None,','held_lease: None, link: None, control: None,');put('smp_fork_ingress.rs',t)
control='''
// A real fresh delivered response, retained independently of the already
// published first RET. No Drop/release API: discard cannot authorize completion.
pub(super) struct ForkControlOwner {
    descriptor: super::super::application_abi::ForkControlV1,
    request: Request,
    _response: super::super::smp_application_syscall::ForkIngressResponse<SyscallResponse>,
    _parent: ForkParentPin,
    quarantined: bool,
}
pub(crate) struct PreparedControlTicket {
    remote: Arc<Remote>, parent: Token, child: Token,
    descriptor: super::super::application_abi::ForkControlV1,
    request: Request, parked: bool,
}

// Call only with SAME Remote slots guard. This validates metadata, not a revoke
// receipt. Exact current ChildFork and first-publication state supply authority.
fn control_snapshot(remote: &Remote, slots: &[Option<Entry>], parent: Token,
    worker: u64, serial: u64, cpu: i64,
) -> Result<Option<(Token, super::super::application_abi::ForkControlV1, Request)>> {
    remote.transport_health()?;
    let p = slots.iter().flatten().find(|e| e.key() == parent).ok_or(ENOENT)?;
    let proof = p.syscalls.unique_delivered(|r| r.number() == 56 && r.arguments()[0] == 2).map_err(errno)?;
    let Some((actual_worker, actual_serial, request)) = proof else { return Ok(None); };
    if actual_worker != worker || actual_serial != serial { return Ok(None); }
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled { return Err(EBUSY); }
    if p.owner_slot != remote.owner.slot() as i32 || p.owner_generation != remote.owner.generation()
        || request.pid() != p.cleanup.pid() || request.cpu() as i64 != cpu
        || cpu < 0 || request.response() == 0 || request.arguments()[5] != CARRIER_MARKER
    { return Err(EACCES); }
    let args = request.arguments();
    let c = slots.iter().flatten().find(|e| e.fork.as_ref().is_some_and(|f|
        f.reservation.identity.parent == parent.wire()
            && f.reservation.identity.child_pid as i64 == args[1] as i64)).ok_or(ENOENT)?;
    if c.key() == parent || c.closed || c.needs_cleanup || c.quarantined
        || c.scheduled || c.prepare.is_some() || c.procfs.is_some() || !c.syscalls.drained()
    { return Err(EBUSY); }
    if c.owner_slot != remote.owner.slot() as i32 || c.owner_generation != remote.owner.generation() { return Err(EACCES); }
    let f = c.fork.as_ref().unwrap(); let k = f.reservation.identity;
    let link = f.link.as_ref().ok_or(EBUSY)?;
    let ack = f.ack.as_ref().ok_or(EBUSY)?;
    if k.slot != remote.owner.slot() || k.generation != remote.owner.generation()
        || k.child != c.key().wire() || f.owner.number != k.child_pid
        || f.owner.mm.as_ptr() as usize != k.child_mm || args[2] != k.length || args[3] != k.root
        || !f.seal.sealed.load(Ordering::Acquire) || f.reservation.state.prepared()
        || !f.reservation.return_published || f.reservation.return_value != Some(k.child_pid as i64)
        || f.reservation.state.phase() != ForkPhase::FirstReturnPublished
        || f.control.is_some() || f.retained_parent.is_none()
        || ack.epoch == 0 || ack.delivery.is_some() || ack.busy || ack.verified || ack.accepted
        || link.identity != k || link.physical != args[4] || link.last_sequence != 1
        || link.gate.load(Ordering::Acquire) != 0 || link.second.is_some() || link.busy
        || link.published || link.receipt_written || link.revoked_receipt_written
        || request.response() == link.original_response
    { return Err(EBUSY); }
    let descriptor = super::super::application_abi::ForkControlV1 {
        version: 1, bytes: core::mem::size_of::<super::super::application_abi::ForkControlV1>() as u32,
        identity: host_key(k), epoch: ack.epoch, worker, delivery: serial, cpu: request.cpu(),
        reserved: 0, physical: link.physical, response: request.response(),
    };
    Ok(Some((c.key(), descriptor, request)))
}
impl Remote {
    pub(crate) fn begin_fork_control(self: &Arc<Self>, parent: Token, worker: u64,
        serial: u64, cpu: i64, _value: i64) -> Result<Option<PreparedControlTicket>> {
        let slots = self.slots.lock();
        let Some((child, descriptor, request)) = control_snapshot(self, &slots, parent, worker, serial, cpu)?
            else { return Ok(None); };
        Ok(Some(PreparedControlTicket { remote: self.clone(), parent, child, descriptor, request, parked: false }))
    }
}
impl PreparedControlTicket {
    pub(crate) fn descriptor(&self) -> super::super::application_abi::ForkControlV1 { self.descriptor }
    /// # Safety
    /// IHK lends only its initialized exact-epoch capsule under an exclusive
    /// PENDING control claim. Shared metadata borrow ends before claim restore.
    pub(crate) unsafe fn park(&mut self, payload: &ForkPayload) -> Result {
        if self.parked { return Err(EBUSY); }
        let mut slots = self.remote.slots.lock();
        let d = self.descriptor;
        let Some((child, current, request)) = control_snapshot(&self.remote, &slots, self.parent,
            d.worker, d.delivery, d.cpu as i64)? else { return Err(EACCES); };
        if child != self.child || current != d || request != self.request { return Err(EACCES); }
        let pi = slots.iter().position(|e| e.as_ref().is_some_and(|e| e.key() == self.parent)).ok_or(ENOENT)?;
        let ci = slots.iter().position(|e| e.as_ref().is_some_and(|e| e.key() == self.child)).ok_or(ENOENT)?;
        let f = slots[ci].as_ref().unwrap().fork.as_ref().unwrap();
        let key = f.reservation.identity; let reservation = f.reservation.token.wire();
        let original = f.link.as_ref().unwrap().original_response;
        if !payload_matches(payload, key, d.physical, original) { return Err(EACCES); }
        let count = slots[pi].as_ref().unwrap().fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?;
        // No fallible effect follows this actual mailbox ownership transfer.
        // All validation and count arithmetic precede moving the SAME Response.
        let response = slots[pi].as_mut().unwrap().syscalls.take_fork_ingress_response(
            d.worker, d.delivery, &self.request).map_err(errno)?;
        let owner = ForkControlOwner { descriptor: d, request: self.request.clone(), _response: response,
            _parent: ForkParentPin { parent: self.parent, identity: key, reservation, remote: self.remote.clone() },
            quarantined: false };
        slots[pi].as_mut().unwrap().fork_prepared_parent_refs = count;
        slots[ci].as_mut().unwrap().fork.as_mut().unwrap().control = Some(owner);
        self.parked = true;
        Ok(())
    }
    // Restore failure after the move must retain both actual owners, never
    // return the response to ordinary RET or decrement the pin on uncertainty.
    pub(crate) fn quarantine_if_parked(&self) {
        if !self.parked { return; }
        let mut slots = self.remote.slots.lock();
        if let Some(c) = slots.iter_mut().flatten().find(|e| e.key() == self.child) {
            if let Some(control) = c.fork.as_mut().and_then(|f| f.control.as_mut()) {
                if control.descriptor == self.descriptor && control.request == self.request {
                    control.quarantined = true; c.quarantined = true;
                }
            }
        }
    }
}
pub(super) fn control_publication_frozen(slots: &[Option<Entry>], parent: Token, cpu: i32) -> bool {
    let Some(p) = slots.iter().flatten().find(|e| e.key() == parent) else { return false; };
    slots.iter().flatten().filter_map(|e| e.fork.as_ref()).any(|f| {
        let k = f.reservation.identity;
        if k.parent != parent.wire() { return false; }
        if f.control.as_ref().is_some_and(|c| c.descriptor.cpu == cpu) { return true; }
        let Some(link) = &f.link else { return false; };
        p.syscalls.has_private_fork_response(cpu, 2, |r| {
            let a = r.arguments(); r.pid() == p.cleanup.pid() && a[1] == k.child_pid as u64
                && a[2] == k.length && a[3] == k.root && a[4] == link.physical && a[5] == CARRIER_MARKER
        })
    })
}
pub(super) fn authorize_control_return(slots: &[Option<Entry>], parent: Token, worker: u64, serial: u64) -> Result {
    if slots.iter().flatten().filter_map(|e| e.fork.as_ref()).any(|f| f.control.as_ref().is_some_and(|c|
        c.descriptor.identity.parent == parent.wire() && c.descriptor.worker == worker && c.descriptor.delivery == serial))
    { return Err(EBUSY); }
    Ok(())
}
'''
t=read('smp_fork_link.rs');t=once(t,'        let fork = c.fork.as_mut().unwrap();\n        let key = fork.reservation.identity;','        let fork = c.fork.as_mut().unwrap();\n        if fork.control.is_some() { return Err(EBUSY); }\n        let key = fork.reservation.identity;');put('smp_fork_link.rs',t+control)
service='''
    /// A successful park owns the fresh response; caller MUST skip ordinary RET.
    pub(in super::super) unsafe fn prepare_fork_control(
        &self, worker: u64, serial: u64, cpu: i64, value: i64,
        resolve: super::super::application_abi::ForkControlResolveV1, context: *mut core::ffi::c_void,
    ) -> Result<bool> {
        let Some(mut ticket) = self.started.runtime.application.begin_fork_control(
            self.token, worker, serial, cpu, value,
        )? else { return Ok(false); };
        let descriptor = ticket.descriptor();
        let status = unsafe { resolve(context, &descriptor, Some(Self::park_fork_control_scope),
            core::ptr::from_mut(&mut ticket).cast()) };
        if status != 0 {
            ticket.quarantine_if_parked();
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        Ok(true)
    }
    unsafe extern "C" fn park_fork_control_scope(ticket: *mut core::ffi::c_void,
        payload: *const core::ffi::c_void) -> i32 {
        if ticket.is_null() || payload.is_null() { return EINVAL.to_errno(); }
        let ticket = unsafe { &mut *ticket.cast::<super::super::smp_application::PreparedControlTicket>() };
        let payload = unsafe { &*payload.cast::<memory::ForkPayload>() };
        unsafe { ticket.park(payload) }.map_or_else(|e| e.to_errno(), |()| 0)
    }
'''
t=once(read('smp_service.rs'),'    // END PRIVATE FORK PROVIDER APPLICATION',service+'    // END PRIVATE FORK PROVIDER APPLICATION');put('smp_service.rs',t)
# IHK exact PENDING stage0 acquisition: validation and BUSY publish in SAME lock.
claim='''
    fn acquire_control(object: &OsObject, identity: super::application_abi::ForkIdentityV1,
        child_context: usize, epoch: u64) -> Result<Self> {
        let mut table = object.forks.lock();
        let index = table.entries.iter().position(|e| e.as_ref().is_some_and(|e|
            e.identity == Some(identity) && e.child_context == child_context && e.epoch == epoch)).ok_or(ENOENT)?;
        let entry = table.entries[index].as_mut().unwrap();
        if epoch == 0 || entry.phase != FORK_PROVIDER_PENDING || entry.host_revoked || entry.guest_released
            || entry.attempted || entry.capsule.is_none() || entry.payload.is_none()
            || entry.final_published || entry.consumer_accepted || entry.payload_completed || entry.backend_released
        { return Err(EBUSY); }
        let claim = Self { object: ptr::from_ref(object), index, epoch, identity,
            previous_phase: entry.phase, guest_released: entry.guest_released,
            attempted: entry.attempted, receipt_index: entry.receipt_index,
            capsule: entry.capsule.clone(), payload: entry.payload.clone(), owner: entry.owner.clone(), active: true };
        entry.phase = FORK_PROVIDER_BUSY;
        Ok(claim)
    }
'''
t=read('os_runtime.rs');t=once(t,'    fn begin_link_attempt(&mut self) -> Result {',claim+'    fn begin_link_attempt(&mut self) -> Result {')
t=once(t,'    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,\n}','    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,\n    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n}')
# Every old constructor initializes the new callback absent, preserving old ABI.
t=re.sub(r'(                release_fork_ack(?:: None)?,\n)',r'\1                prepare_fork_control: None,\n',t)
# Add v11 as a separately named copy of v10 constructor, with ONE additive argument.
a=t.index('pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v10(');a=t.rfind('/// # Safety',0,a);end=t.index('\n/// # Safety',a+15)
v11=t[a:end].replace('ihk_os_create_unbooted_v10','ihk_os_create_unbooted_v11')
v11=once(v11,'    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,\n) -> i64','    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,\n    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n) -> i64')
v11=once(v11,'                prepare_fork_control: None,','                prepare_fork_control,')
t=t[:end]+'\n'+v11+t[end:]
resolver='''
unsafe extern "C" fn resolve_fork_control_scope(
    context: *mut c_void, descriptor: *const super::application_abi::ForkControlV1,
    park: Option<super::application_abi::ForkControlParkV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkControlV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let park = park.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let before = unsafe { *descriptor }; let key = before.identity;
        if before.version != VERSION || before.bytes as usize != core::mem::size_of::<ForkControlV1>()
            || before.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation || before.epoch == 0
            || key.parent == 0 || key.child == 0 || key.parent == key.child || key.worker == 0
            || key.delivery == 0 || key.nonce == 0 || key.child_pid <= 0 || key.child_mm == 0
            || before.worker == 0 || before.delivery == 0 || before.cpu < 0
            || before.physical == 0 || before.response == 0
        { return Err(EACCES); }
        let object = unsafe { &*scope.object };
        let child_context = {
            let table = object.forks.lock();
            table.entries.iter().flatten().find(|e| e.identity == Some(key) && e.epoch == before.epoch)
                .map(|e| e.child_context).ok_or(ENOENT)?
        };
        let claim = ForkProviderClaim::acquire_control(object, key, child_context, before.epoch)?;
        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        if capsule.context.load(Ordering::Acquire).is_null() { return Err(EIO); }
        let payload_context = payload.context.load(Ordering::Acquire);
        if payload_context.is_null() { return Err(EIO); }
        // No IHK table guard spans backend/Remote code. Both exact capsules,
        // module and OS admission remain owned by this BUSY claim. Callback is
        // registered backend code, and receives ONLY shared payload metadata.
        let status = unsafe { park(ticket, payload_context.cast_const()) };
        if unsafe { *descriptor } != before { return Err(errno(-71)); }
        if status != 0 {
            // The trusted park callback has no fallible step after moving its
            // response. A refusal therefore has no backend ownership effects.
            claim.restore()?;
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        // Restore failure quarantines IHK via Drop; caller retains its durable
        // parked response and independently marks its backend owner uncertain.
        claim.restore()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// Actual live ApplicationConnection pre-RETURN hook. Positive result means
/// durable park ONLY: no revoke/receipt/terminal authority and no standard RET.
#[export_name = "ihk_os_application_prepare_fork_control_v1"]
pub(crate) unsafe extern "C" fn prepare_fork_control_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result<bool> {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|b| b.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_control else { return Ok(false); };
        let mut scope = ForkLinkResolverScope { object: ptr::from_ref(object), slot: handle.minor() as u32,
            generation: handle.generation() };
        match unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_control_scope), ptr::from_mut(&mut scope).cast()) } {
            0 => Ok(false), 1 => Ok(true), e if (-4095..0).contains(&e) => Err(errno(e)), _ => Err(errno(-71)),
        }
    })();
    result.map_or_else(|e| e.to_errno(), |parked| i32::from(parked))
}
'''
t=once(t,'unsafe extern "C" fn resolve_fork_ack_scope(',resolver+'\nunsafe extern "C" fn resolve_fork_ack_scope(')
exports='''
// SAFETY: Module-resident additive private control callback relocations.
#[export_name = "__export_symbol_ihk_os_application_prepare_fork_control_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_PREPARE_FORK_CONTROL_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0", namespace: *b"MCKERNEL_IHK_V1\\0", padding: [0; 4],
    symbol: prepare_fork_control_application as *const () as *const u8,
};
#[export_name = "__export_symbol_ihk_os_create_unbooted_v11"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V11_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0", namespace: *b"MCKERNEL_IHK_V1\\0", padding: [0; 4],
    symbol: ihk_os_create_unbooted_v11 as *const () as *const u8,
};
'''
put('os_runtime.rs',t+exports)
# Actual SMP registration plus typed synchronous adapter.
t=read('ihk_smp_x86_64.rs').replace('ihk_os_create_unbooted_v10','ihk_os_create_unbooted_v11')
t=once(t,'                    Some(application_release_fork_ack),','                    Some(application_release_fork_ack),\n                    Some(application_prepare_fork_control),')
t=once(t,'        application_release_fork_ack: Option<application_abi::ForkReleaseAckV1>,','        application_release_fork_ack: Option<application_abi::ForkReleaseAckV1>,\n        application_prepare_fork_control: Option<application_abi::ForkPrepareControlV1>,')
callback='''
unsafe extern "C" fn application_prepare_fork_control(
    parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64,
    resolver: Option<application_abi::ForkControlResolveV1>, context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() { return EINVAL.to_errno(); }
    let Some(resolver) = resolver else { return EINVAL.to_errno(); };
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    unsafe { parent.prepare_fork_control(worker, serial, cpu, value, resolver, context) }
        .map_or_else(|e| e.to_errno(), |parked| i32::from(parked))
}
'''
t=once(t,'unsafe extern "C" fn application_prepare_fork_ack(',callback+'\nunsafe extern "C" fn application_prepare_fork_ack(');put('ihk_smp_x86_64.rs',t)
t=read('mcctrl_process.rs')
t=once(t,'    fn ihk_os_application_prepare_fork_ack_v1(', '    fn ihk_os_application_prepare_fork_control_v1(parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64) -> i32;\n    fn ihk_os_application_prepare_fork_ack_v1(')
hook='''        // Park a genuine fresh selector2 delivery before any legacy return
        // hook. The incoming launcher -95 is not authority. Parked MUST stop
        // ordinary RETURN; it cannot manufacture RET0 or a revoke receipt.
        match unsafe { ihk_os_application_prepare_fork_control_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) } {
            0 => {}, 1 => return Err(EBUSY),
            e if (-4095..0).contains(&e) => return Err(errno(e)),
            _ => return Err(errno(-71)),
        }
'''
t=once(t,'        // SAFETY: This live fd/worker pins our return frame and connection. IHK',hook+'        // SAFETY: This live fd/worker pins our return frame and connection. IHK');put('mcctrl_process.rs',t)
# Freeze exact patch against each retained base; no current production overlay.
patch=[];pins=[]
for f in sorted(S.rglob('*.rs')):
 n=str(f.relative_to(S));a=(B/n).read_text();b=f.read_text()
 if a!=b:patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/host-kernel/native-rust/'+n,tofile='b/host-kernel/native-rust/'+n))
 pins.append(dict(path=str(f),relative=n,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,changed=a!=b))
(P/'positive-control-park.patch').write_text(''.join(patch));(P/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print('changed_files',sum(x['changed'] for x in pins),'patch_bytes',(P/'positive-control-park.patch').stat().st_size)
