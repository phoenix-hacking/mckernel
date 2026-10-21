#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct Span {
    physical: u64,
    end: u64,
}

impl Span {
    pub(super) fn new(physical: u64, bytes: usize) -> Result<Self> {
        if physical == 0 || bytes == 0 {
            return Err(EINVAL);
        }
        Ok(Self {
            physical,
            end: physical.checked_add(bytes as u64).ok_or(EINVAL)?,
        })
    }

    fn overlaps(self, other: Self) -> bool {
        self.physical < other.end && other.physical < self.end
    }
}

#[derive(Clone, Copy)]
struct Tagged {
    span: Span,
    serial: u64,
}

struct Ledger {
    fixed: Vec<Span>,
    requests: Vec<Option<Tagged>>,
    responses: Vec<Option<Tagged>>,
    payloads: Vec<Option<Tagged>>,
    // Separate bounded per-response exec group; ordinary payload semantics stay strict.
    exec_payloads: Vec<Option<Vec<Tagged>>>,
    snoops: Vec<Tagged>,
    procfs: Vec<Tagged>,
    zeroing: Vec<Tagged>,
    serial: u64,
}

impl Ledger {
    fn conflicts(&self, span: Span, snoops: bool) -> bool {
        self.fixed.iter().any(|old| old.overlaps(span))
            || self
                .requests
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .payloads
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .responses
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self.exec_payloads.iter().flatten().any(|group| group.iter().any(|old| old.span.overlaps(span)))
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
            || self.procfs.iter().any(|old| old.span.overlaps(span))
            || self.zeroing.iter().any(|old| old.span.overlaps(span))
    }

    fn tag(&mut self, span: Span) -> Result<Tagged> {
        self.serial = self.serial.checked_add(1).ok_or_else(|| errno(-75))?;
        Ok(Tagged {
            span,
            serial: self.serial,
        })
    }
}

// UNWIRED real ledger implementation. Constructor is private to original
// SyscallResponse; scalar keys alone cannot create a group or mapping owner.
struct ExecMapping { tag: Tagged, address: u64 }
pub(crate) struct ExecClaimGroup {
    memory: Arc<Memory>, slot: usize, key: crate::exec_transfer_checked::ExecKey,
    descriptor: crate::exec_transfer_checked::Step,
    mappings: Vec<ExecMapping>, reserved: bool,
}
// SAFETY: SyscallResponse exclusively constructs/holds this group after its
// exact descriptor payload claim. Original Response owns both. Every section
// claim is atomically published in the same Memory ledger, and only original
// ResponseMemory::release removes it after real final status publication.
// Unfinished drop preserves tags; continuing Runtime/BootStorage retain RAM.
unsafe impl crate::exec_transfer_checked::ResponseOwnedExecClaims for ExecClaimGroup {
    fn key(&self)->crate::exec_transfer_checked::ExecKey {self.key}
    fn descriptor(&self)->crate::exec_transfer_checked::Step {self.descriptor}
    fn reserve_sections(&mut self, sections:&[crate::exec_transfer_checked::Section])->core::result::Result<(),i32> {
        self.reserve_all(sections).map_err(|e|e.to_errno())
    }
}
impl ExecClaimGroup {
    fn reserve_all(&mut self, sections:&[crate::exec_transfer_checked::Section])->Result {
        if self.reserved || sections.len()>crate::application_image::MAX_SECTIONS {return Err(EINVAL);}
        // Allocate every fallible vector before publishing ANY new claim.
        let mut mappings=Vec::with_capacity(sections.len(),GFP_KERNEL)?;
        let mut tags=Vec::with_capacity(sections.len(),GFP_KERNEL)?;
        let mut ledger=self.memory.ledger.lock();
        if ledger.responses[self.slot].as_ref().map(|t|t.serial)!=Some(self.key.response_serial)
            || ledger.exec_payloads[self.slot].is_some() {return Err(EBUSY);}
        let descriptor=ledger.payloads[self.slot].ok_or(EIO)?;
        if descriptor.span.physical!=self.descriptor.physical
            || descriptor.span.end-descriptor.span.physical!=self.descriptor.bytes as u64 {return Err(EACCES);}
        for section in sections {
            if section.pages==0 {continue;}
            let bytes=section.pages.checked_mul(4096).and_then(|n|usize::try_from(n).ok()).ok_or(EINVAL)?;
            let span=Span::new(section.physical,bytes)?;
            let address=self.memory.address(section.physical,bytes)?;
            if section.physical%4096!=0 || ledger.conflicts(span,true)
                || tags.iter().any(|old:&Tagged|old.span.overlaps(span)) {return Err(EBUSY);}
            let tag=ledger.tag(span)?;
            tags.push(tag,GFP_KERNEL)?;
            mappings.push(ExecMapping{tag,address},GFP_KERNEL)?;
        }
        // Infallible single ownership publication after all validation and
        // allocations. A failure above may consume serials, never a claim.
        ledger.exec_payloads[self.slot]=Some(tags);
        self.mappings=mappings;self.reserved=true;Ok(())
    }
}

/// Only completed response publication removes this exact ledger tag. Dropping
/// an unfinished capability leaves its span excluded; the continuing Runtime
/// and original started BootStorage retain all RAM/module owners in quarantine.
pub(crate) struct SyscallResponse {
    memory: Arc<Memory>,
    address: u64,
    tag: Tagged,
    slot: usize,
    // Same slot in a distinct ledger: this capability outlives all page I/O
    // and stays excluded until the response's actual final publication.
    payload: Option<(Tagged, u64, bool)>,
    exec_group: Option<ExecClaimGroup>,
}

impl SyscallResponse {

    pub(crate) fn prepare_exec_delivery(&mut self,request:&SyscallRequest,application:u64,worker:u64,delivery:u64)->core::result::Result<crate::exec_delivery::ExecDelivery,i32>{
        use crate::exec_transfer_checked::{ExecKey,Phase2};
        let key=ExecKey{os_slot:self.memory.owner.slot(),os_generation:self.memory.owner.generation(),application,worker,delivery,response_serial:self.tag.serial,response_physical:self.tag.span.physical};
        if request.number()!=59||request.response()!=key.response_physical||application==0||worker==0||delivery==0{return Err(-22);}
        if request.arguments()[0]==1{return Ok(crate::exec_delivery::ExecDelivery::phase1(key));}
        let mut plan=Phase2::begin(request,key)?;let step=plan.expected(request,key)?.ok_or(-22)?;
        let mut snapshot=Vec::with_capacity(step.bytes,GFP_KERNEL).map_err(|_|-12)?;
        for _ in 0..step.bytes{snapshot.push(0,GFP_KERNEL).map_err(|_|-12)?;}
        self.prepare_exec_descriptor(request,key).map_err(|e|e.to_errno())?;
        self.pager_copy(0,&mut snapshot,false).map_err(|e|e.to_errno())?;
        plan.stage_descriptor(request,key,&snapshot)?;
        plan.reserve_sections(self.exec_claim_group().map_err(|e|e.to_errno())?)?;
        Ok(crate::exec_delivery::ExecDelivery::phase2(key,plan,snapshot))
    }
    pub(crate) fn copy_exec_delivery(&mut self,request:&SyscallRequest,key:crate::exec_transfer_checked::ExecKey,step:crate::exec_transfer_checked::Step,bytes:&mut[u8])->core::result::Result<(),i32>{
        if key.os_slot!=self.memory.owner.slot()||key.os_generation!=self.memory.owner.generation()||key.response_serial!=self.tag.serial||key.response_physical!=self.tag.span.physical{return Err(-13);}
        if request.arguments()[0]==1{
            crate::exec_transfer_checked::phase1_upload(request,step,bytes)?;
            self.prepare_payload(step.physical,step.bytes,true).map_err(|e|e.to_errno())?;
            self.pager_copy(0,bytes,true).map_err(|e|e.to_errno())
        }else{self.copy_exec_page(key,step,bytes).map_err(|e|e.to_errno())}
    }


    /// Called only under the original authenticated mailbox delivery guard.
    /// Key OS/response fields come from these actual retained owners; numeric
    /// application/worker/delivery fields must already match that mailbox.
    pub(crate) fn prepare_exec_descriptor(&mut self,request:&SyscallRequest,
        key:crate::exec_transfer_checked::ExecKey)->Result {
        use crate::exec_transfer_checked::{Phase2,Step};
        if key.os_slot!=self.memory.owner.slot() || key.os_generation!=self.memory.owner.generation()
            || key.response_serial!=self.tag.serial || key.response_physical!=self.tag.span.physical
            || request.response()!=self.tag.span.physical || self.exec_group.is_some() {return Err(EACCES);}
        let plan=Phase2::begin(request,key).map_err(errno)?;
        let descriptor=plan.expected(request,key).map_err(errno)?.ok_or(EINVAL)?;
        if descriptor.direction!=1 {return Err(EINVAL);}
        self.prepare_payload(descriptor.physical,descriptor.bytes,false)?;
        self.exec_group=Some(ExecClaimGroup{memory:self.memory.clone(),slot:self.slot,key,
            descriptor:Step{..descriptor},mappings:Vec::new(),reserved:false});Ok(())
    }
    pub(crate) fn exec_claim_group(&mut self)->Result<&mut ExecClaimGroup> {
        self.exec_group.as_mut().ok_or(EINVAL)
    }
    /// Exact cursor check is an additional mandatory caller prerequisite.
    /// This primitive confers no page-order or successful-RET authority.
    pub(crate) fn copy_exec_page(&mut self,key:crate::exec_transfer_checked::ExecKey,
        step:crate::exec_transfer_checked::Step,bytes:&mut[u8])->Result {
        let group=self.exec_group.as_ref().ok_or(EINVAL)?;
        if group.key!=key || !group.reserved || step.direction!=0 || step.bytes!=4096
            || bytes.len()!=4096 || step.physical%4096!=0 {return Err(EACCES);}
        let last=step.physical.checked_add(4096).ok_or(EINVAL)?;
        let mapping=group.mappings.iter().find(|m|step.physical>=m.tag.span.physical&&last<=m.tag.span.end).ok_or(EACCES)?;
        let offset=usize::try_from(step.physical-mapping.tag.span.physical).map_err(|_|EINVAL)?;
        for(i,byte)in bytes.iter().enumerate(){
            // SAFETY: exact original-response group retains the whole checked,
            // disjoint extent; mailbox guard excludes cancellation/publication.
            unsafe {ptr::write_volatile((mapping.address as *mut u8).add(offset+i),*byte)};
        }Ok(())
    }

    pub(crate) fn validate_fork_root(&self,request:&SyscallRequest,root:u64)->Result {
        if request.number()!=56||request.arguments()[3]!=root||root==0||root%4096!=0{return Err(EACCES);}
        // Range/mapping validation is subordinate to the actual retained
        // original delivery/child-credit/root owner. It grants no authority.
        self.memory.address(root,4096)?;Ok(())
    }
    fn read_current_fork_carrier(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let args=request.arguments();
        if request.number()!=56||args[5]!=0x313030434b46434d{return Err(EACCES);}
        if self.payload.is_none(){self.prepare_payload(args[4],128,true)?;}
        let(tag,address,writable)=self.payload.ok_or(EIO)?;
        if !writable||tag.span.physical!=args[4]
            ||tag.span.end.checked_sub(tag.span.physical)!=Some(128){return Err(EACCES);}
        // The same exclusive response-owned span permits both initial reads
        // and the eventual first receipt write; ordinary pager rights remain
        // unchanged. No peer byte is written before the original RET is bound.
        let mut bytes=[0;128];
        for(i,b)in bytes.iter_mut().enumerate(){*b=unsafe {ptr::read_volatile((address as *const u8).add(i))};}
        Ok(bytes)
    }
    pub(crate) fn current_fork_carrier(&mut self,request:&SyscallRequest)->Result<u64> {
        let bytes=self.read_current_fork_carrier(request)?;
        request.current_fork_carrier(&bytes).map_err(errno)
    }
    pub(crate) fn write_first_fork_receipt(&mut self,request:&SyscallRequest,
        receipt:&crate::application_syscall::ForkFirstReceipt)->Result {
        let nonce=self.current_fork_carrier(request)?;
        if nonce!=receipt.nonce{return Err(EACCES);}
        let mut bytes=request.first_fork_receipt(receipt).map_err(errno)?;
        self.pager_copy(0,&mut bytes,true)
    }

    pub(crate) fn current_fork_control_frame(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let a=request.arguments();
        if request.number()!=56||!matches!(a[0],2|3)||a[5]!=0x313030434b46434d{return Err(EACCES);}
        self.read_current_fork_carrier(request)
    }
    pub(crate) fn write_fork_control_frame(&mut self,bytes:&mut[u8;128])->Result {
        self.pager_copy(0,bytes,true)
    }

    pub(crate) fn prepare_pager(&mut self, request: &SyscallRequest) -> Result {
        let operation = crate::application_pager::Operation::decode(request).map_err(errno)?;
        let Some((physical, bytes, to_guest)) = operation.payload() else {
            return Ok(());
        };
        self.prepare_payload(physical, bytes, to_guest)
    }

    fn prepare_payload(&mut self, physical: u64, bytes: usize, to_guest: bool) -> Result {
        if self.payload.is_some() {
            return Err(EBUSY);
        }
        let address = self.memory.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.memory.ledger.lock();
        if ledger.payloads[self.slot].is_some() || ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let tag = ledger.tag(span)?;
        ledger.payloads[self.slot] = Some(tag);
        self.payload = Some((tag, address, to_guest));
        Ok(())
    }

    pub(crate) fn copy_tids(&mut self, request: &SyscallRequest, bytes: &mut [u8]) -> Result {
        let (physical, length) = request.tid_buffer().map_err(errno)?;
        if length != bytes.len() as u64 {
            return Err(EINVAL);
        }
        self.prepare_payload(physical, bytes.len(), true)?;
        self.pager_copy(0, bytes, true)
    }

    pub(crate) fn pager_copy(&mut self, offset: usize, bytes: &mut [u8], to_guest: bool) -> Result {
        let (tag, address, direction) = self.payload.ok_or(EINVAL)?;
        if to_guest != direction
            || offset
                .checked_add(bytes.len())
                .is_none_or(|end| end as u64 > tag.span.end - tag.span.physical)
        {
            return Err(EINVAL);
        }
        // SAFETY: The bounded offset lies in the retained payload span. The
        // mailbox reservation or complete-transfer critical section excludes
        // completion and cancellation, and its unique tag excludes every host
        // mapping; byte accesses need no stronger alignment or Rust reference.
        for (index, byte) in bytes.iter_mut().enumerate() {
            unsafe {
                let pointer = (address as *mut u8).add(offset + index);
                if to_guest {
                    ptr::write_volatile(pointer, *byte);
                } else {
                    *byte = ptr::read_volatile(pointer);
                }
            }
        }
        Ok(())
    }
}

// SAFETY: Memory::syscall is the only constructor. It validates the complete
// retained mapping and excludes aliases under the shared ledger. Unfinished
// destruction does not remove the tag or acknowledge the guest.
unsafe impl ResponseMemory for SyscallResponse {
    fn physical(&self) -> u64 {
        self.tag.span.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.address as *mut u8
    }
    unsafe fn release(self) {
        let mut ledger = self.memory.ledger.lock();
        let slot = &mut ledger.responses[self.slot];
        assert!(slot
            .as_ref()
            .is_some_and(|tag| tag.serial == self.tag.serial));
        *slot = None;
        if let Some((tag, _, _)) = self.payload {
            assert!(ledger.payloads[self.slot]
                .as_ref()
                .is_some_and(|old| old.serial == tag.serial));
            ledger.payloads[self.slot] = None;
        }
        if let Some(group)=self.exec_group {
            let retained=ledger.exec_payloads[self.slot].as_ref();
            if group.reserved {
                let retained=retained.expect("exec claims lost before RET");
                assert!(retained.len()==group.mappings.len());
                for(old,mapping)in retained.iter().zip(group.mappings.iter()) {assert!(old.serial==mapping.tag.serial);}
                ledger.exec_payloads[self.slot]=None;
            } else {assert!(retained.is_none());}
        }
        // The guest can already reuse the response; only host bookkeeping is
        // accessed above. No destructor dereferences its address.
    }
}

