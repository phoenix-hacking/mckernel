// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private UNWIRED candidate. Associations use the same R as descriptor/group
// publication and actual Process terminal detach. No persistent Process edge.

use core::ffi::c_void;
use core::mem::ManuallyDrop;
use core::ptr::{addr_of, addr_of_mut, null_mut};
use crate::abi::{CInt, Process};
use super::descriptors::Locked;
use super::events::EventPin;

const EINVAL: CInt = 22;
const EBADF: CInt = 9;

/// Not a PID or a cast pointer alone. The common registry supplies a genuine
/// checked nonzero generation at actual Process construction, before visibility.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) struct ProcessKey { pub(super) address: usize, pub(super) generation: u64 }
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) struct DescriptorKey {
    pub(super) process: usize,
    pub(super) descriptor: usize,
    pub(super) generation: u64,
}

/// An inherited monitor belongs to the actual child Process even when a remote
/// pid>0 target/fork has NO perf descriptor to copy. It is never represented by
/// an invented descriptor address or generation.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum SlotOwner {
    Descriptor(DescriptorKey),
    InheritedProcess(ProcessKey),
}

/// Preallocated at the actual Process construction hook. Its stable storage is
/// owned by the common process registry, not by an event. The actual final path
/// MUST call retire_locked before this record or the Process can be freed.
pub(super) struct Target {
    process: *mut Process,
    key: ProcessKey,
    current: *mut MonitorSlot,
    live: bool,
}
impl Target {
    /// Caller owns exclusive, initialized Process construction storage and a
    /// checked registry generation; move this record before publishing any slot.
    pub(super) unsafe fn new(process: *mut Process, generation: u64) -> Result<Self, CInt> {
        if process.is_null() || generation == 0 { return Err(-EINVAL); }
        Ok(Self { process, key: ProcessKey { address: process as usize, generation },
            current: null_mut(), live: true })
    }
    pub(super) fn key(&self) -> ProcessKey { self.key }
    pub(super) fn process(&self) -> *mut Process { self.process }
    fn valid(&self) -> bool {
        self.live && !self.process.is_null() && self.key.address == self.process as usize
            && self.key.generation != 0
    }

    /// A managed scheduler/exit reader obtains the event/group edge under R,
    /// before using the raw ABI field outside R. Legacy nonmanaged fields remain
    /// explicitly nonmanaged; no callback/data inference establishes ownership.
    pub(super) unsafe fn pin_locked(&self, r: &mut Locked) -> Result<MonitorRead, CInt> {
        if !self.valid() { return Err(-EINVAL); }
        let raw = unsafe { addr_of!((*self.process).monitoring_event).read() };
        if self.current.is_null() {
            return if raw.is_null() { Ok(MonitorRead::None) } else { Ok(MonitorRead::Unmanaged(raw)) };
        }
        let slot = unsafe { &*self.current };
        if slot.closed || slot.target != self as *const Self as *mut Self
            || slot.target_key != Some(self.key) { return Err(-EINVAL); }
        let pin = slot.event.as_ref().ok_or(-EINVAL)?;
        if pin.raw_event() != raw { return Err(-EINVAL); }
        Ok(MonitorRead::Managed(unsafe { pin.try_clone_locked(r)? }))
    }

    /// Ordinary pid0 disable: detach the real association without retiring
    /// or reinitializing this live Process identity. Author-supplied integration
    /// delta after frozen db25e66e; no callback or allocator under R.
    pub(super) unsafe fn clear_locked(&mut self,r:&mut Locked){
        if !self.live{return;}
        if !self.current.is_null(){unsafe{(*self.current).detach_from_target_locked(self,r)};}
        self.current=null_mut();
    }

    /// Genuine terminal Process path, after final monitor accounting and BEFORE
    /// either Process or Target storage is freed. R serializes descriptor close.
    /// Does not acquire P, free storage or call release_process under R.
    pub(super) unsafe fn retire_locked(&mut self, r: &mut Locked) {
        if !self.live { return; }
        if !self.current.is_null() {
            unsafe { (*self.current).detach_from_target_locked(self, r) };
        }
        // No association keeps a pointer to this record past terminal detach.
        self.current = null_mut();
        self.live = false;
        self.process = null_mut();
    }
}

pub(super) enum MonitorRead {
    None,
    Managed(EventPin),
    Unmanaged(*mut c_void),
}

/// Preallocated in an actual managed DescriptorEvent OR real Process record.
/// Bind the explicit owner only AFTER moving to its stable Record storage.
/// Its owned EventPin carries event + own/containing group refs, never Process.
pub(super) struct MonitorSlot {
    owner: Option<SlotOwner>,
    target: *mut Target,
    target_key: Option<ProcessKey>,
    event: Option<ManuallyDrop<EventPin>>,
    closed: bool,
}
impl MonitorSlot {
    pub(super) const fn new() -> Self {
        Self { owner: None, target: null_mut(), target_key: None, event: None, closed: false }
    }
    pub(super) unsafe fn bind_locked(&mut self, key: DescriptorKey, _r: &mut Locked) -> Result<(), CInt> {
        if self.owner.is_some() || self.closed || key.process == 0
            || key.descriptor == 0 || key.generation == 0 { return Err(-EINVAL); }
        self.owner = Some(SlotOwner::Descriptor(key));
        Ok(())
    }
    /// Actual Process record owns this preallocated, stable slot and calls
    /// retire_locked at its terminal hook. No allocation or Process refcycle.
    pub(super) unsafe fn bind_inherited_locked(&mut self, key: ProcessKey, _r: &mut Locked) -> Result<(), CInt> {
        if self.owner.is_some() || self.closed || key.address == 0 || key.generation == 0 { return Err(-EINVAL); }
        self.owner = Some(SlotOwner::InheritedProcess(key));
        Ok(())
    }
    pub(super) fn owner_key(&self) -> Option<SlotOwner> { self.owner }
    pub(super) fn descriptor_key(&self) -> Option<DescriptorKey> {
        match self.owner { Some(SlotOwner::Descriptor(key)) => Some(key), _ => None }
    }

    /// Remove only THIS exact association, including a foreign pid target. The
    /// target's mandatory terminal hook cleared these weak fields before free.
    pub(super) unsafe fn detach_locked(&mut self, r: &mut Locked) {
        if !self.target.is_null() {
            let target = unsafe { &mut *self.target };
            unsafe { self.detach_from_target_locked(target, r) };
            return;
        }
        unsafe { self.release_edge_locked(r) };
    }
    // Reborrow an already-live Target reference supplied by install/terminal,
    // instead of forming another &mut through the stored weak pointer while
    // that same Target is already mutably borrowed by the caller.
    unsafe fn detach_from_target_locked(&mut self, target: &mut Target, r: &mut Locked) {
        if target.live && self.target == target as *mut Target && self.target_key == Some(target.key)
            && target.current == self as *mut Self {
            let pin = self.event.as_ref().expect("perf association missing event edge");
            let actual = unsafe { addr_of!((*target.process).monitoring_event).read() };
            // A displaced/replaced raw field is never cleared by a stale
            // descriptor merely because a PID or event address matches.
            if actual == pin.raw_event() {
                unsafe { addr_of_mut!((*target.process).monitoring_event).write(null_mut()) };
            }
            target.current = null_mut();
        }
        unsafe { self.release_edge_locked(r) };
    }
    unsafe fn release_edge_locked(&mut self, r: &mut Locked) {
        self.target = null_mut();
        self.target_key = None;
        if let Some(pin) = self.event.take() {
            let pin = ManuallyDrop::into_inner(pin);
            unsafe { pin.release_association_locked(r); pin.release_locked(r) };
        }
    }
    pub(super) unsafe fn retire_locked(&mut self, r: &mut Locked) {
        unsafe { self.detach_locked(r) };
        self.closed = true;
    }

    /// After all genuine executing-Thread mapping reservations have committed,
    /// publish without allocation or hardware/offload callbacks. `target` is
    /// protected by the actual caller's live/positive Process edge. In a remote
    /// lookup this function DOES NOT consume with_remote_target's temporary ref.
    /// Caller holds the exact registered target identity and SAME R throughout.
    pub(super) unsafe fn install_locked(
        &mut self, target: &mut Target, expected: ProcessKey, event: &EventPin,
        mode: InstallMode, r: &mut Locked,
    ) -> Result<Installed, CInt> {
        if self.closed { return Err(-EBADF); }
        if self.owner.is_none() || !target.valid() || target.key != expected { return Err(-EINVAL); }
        if let Some(SlotOwner::InheritedProcess(owner)) = self.owner {
            if owner != expected || !matches!(mode, InstallMode::Current) { return Err(-EINVAL); }
        }
        let actual = unsafe { addr_of!((*target.process).monitoring_event).read() };
        if matches!(mode, InstallMode::Remote { .. }) && !actual.is_null() {
            // Exact original pid>0 behavior, including legacy/unmanaged fields:
            // already populated is unchanged success0, not replacement/error.
            return Ok(Installed::AlreadyPopulated);
        }
        // Clone first. A checked reference error leaves both old associations
        // and the real Process.monitoring_event unchanged.
        let retained = unsafe { event.try_clone_locked(r)? };
        if let Err(error) = unsafe { retained.acquire_association_locked(r) } {
            unsafe { retained.release_locked(r) };
            return Err(error);
        }
        if self.target == target as *mut Target {
            unsafe { self.detach_from_target_locked(target, r) };
        } else {
            unsafe { self.detach_locked(r) };
        }
        if !target.current.is_null() {
            unsafe { (*target.current).detach_from_target_locked(target, r) };
        }
        self.target = target;
        self.target_key = Some(expected);
        self.event = Some(ManuallyDrop::new(retained));
        target.current = self;
        unsafe { addr_of_mut!((*target.process).monitoring_event).write(event.raw_event()) };
        if let InstallMode::Remote { pp_reset } = mode {
            // pp_reset comes from actual selected C-header metadata.
            unsafe { addr_of_mut!((*target.process).perf_status).write(pp_reset) };
        }
        Ok(Installed::Published)
    }
}

#[derive(Clone, Copy)]
pub(super) enum InstallMode {
    /// pid0 replaces exactly as the original; start happens AFTER dropping R.
    Current,
    /// pid>0 installs only into actually NULL and records actual PP_RESET.
    Remote { pp_reset: CInt },
}
pub(super) enum Installed { Published, AlreadyPopulated }

pub(super) enum Inherited {
    Disabled,
    Published,
    // Caller preserves the original unmanaged fallback rather than claiming a
    // managed edge or inspecting arbitrary raw event storage as managed kind.
    Unmanaged(*mut c_void),
}

/// Child Process-owned slot and actual Thread maps are prepared BEFORE
/// child visibility. No allocation, target Process hold, or raw-event-only copy.
/// The child's association is independent of the parent's descriptor lifetime.
pub(super) unsafe fn inherit_locked(
    parent: &Target, child: &mut Target, child_slot: &mut MonitorSlot,
    r: &mut Locked,
) -> Result<Inherited, CInt> {
    if !child.valid() || child_slot.owner_key() != Some(SlotOwner::InheritedProcess(child.key)) {
        return Err(-EINVAL);
    }
    match unsafe { parent.pin_locked(r)? } {
        MonitorRead::None => Ok(Inherited::Disabled),
        MonitorRead::Unmanaged(raw) => Ok(Inherited::Unmanaged(raw)),
        MonitorRead::Managed(pin) => {
            if !pin.inherit_enabled() {
                unsafe { pin.release_locked(r) };
                return Ok(Inherited::Disabled);
            }
            let key = child.key;
            let result = unsafe { child_slot.install_locked(child, key, &pin, InstallMode::Current, r) };
            unsafe { pin.release_locked(r) };
            match result {
                Ok(Installed::Published) => Ok(Inherited::Published),
                Ok(Installed::AlreadyPopulated) => Err(-EINVAL),
                Err(error) => Err(error),
            }
        }
    }
}
