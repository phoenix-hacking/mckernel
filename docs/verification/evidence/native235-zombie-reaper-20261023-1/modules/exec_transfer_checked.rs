// SPDX-License-Identifier: GPL-2.0
//! Pure checked geometry for the supported x86-64 exec transfer protocol.
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//!
//! UNWIRED: these values confer no mapping, worker, delivery or memory authority.
//! The native caller must retain the exact response and all claims, serialize
//! against RET/close, authenticate its worker/delivery, and verify guest extents.

use super::{application_image as image, application_syscall::Request};
type Result<T> = core::result::Result<T, i32>;
const PAGE: u64 = 4096;
const EXEC_DESCRIPTOR_CAPACITY: usize = 4 * PAGE as usize;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Step {
    pub(crate) physical: u64,
    pub(crate) bytes: usize,
    /// Existing remote_transfer ABI: zero uploads, one downloads.
    pub(crate) direction: u64,
}

fn section_geometry(section: &[u8]) -> Result<(u64, u64, u64)> {
    let address = image::word(section, 0)?;
    let memory = image::word(section, 8)?;
    let files = image::word(section, 24)?;
    let offset = image::word(section, 32)?;
    let prot = image::integer(section, 40)?;
    let last = address.checked_add(memory).ok_or(-75)?;
    if memory == 0 || files > memory || last > image::USER_LIMIT
        || prot & !7 != 0 || section[44] > 1 || offset.checked_add(files).is_none()
    { return Err(-22); }
    let pages = if files == 0 { 0 } else {
        files.checked_add(address & (PAGE - 1)).and_then(|n| n.checked_add(PAGE - 1))
            .ok_or(-75)? / PAGE
    };
    Ok((address, memory, pages))
}

/// Validate exactly the phase1 descriptor plus optional flattened shebang argv.
/// The 16KiB bound comes from the actual do_execveat four-page allocation.
pub(crate) fn phase1_upload(request: &Request, step: Step, bytes: &[u8]) -> Result<Step> {
    let a = request.arguments();
    if request.number() != 59 || a[0] != 1 || a[3] == 0 || a[3] % PAGE != 0
        || step != (Step { physical: a[3], bytes: bytes.len(), direction: 0 })
        || bytes.len() > EXEC_DESCRIPTOR_CAPACITY
        || a[3].checked_add(EXEC_DESCRIPTOR_CAPACITY as u64).is_none()
    { return Err(-22); }
    let descriptor = image::descriptor_bytes(bytes)?;
    let args = usize::try_from(image::word(bytes, image::ARGS_LEN)?).map_err(|_| -75)?;
    if descriptor.checked_add(args) != Some(bytes.len()) { return Err(-22); }
    for section in bytes[image::HEADER..descriptor].chunks_exact(image::SECTION) {
        section_geometry(section)?;
    }
    if args != 0 { image::flattened(&bytes[descriptor..])?; }
    Ok(step)
}

#[derive(Clone, Copy, Default, Debug, Eq, PartialEq)]
pub(crate) struct Section {
    pub(crate) physical: u64,
    pub(crate) pages: u64,
}

/// Metadata checked against the real retained native owners before every hook.
/// Constructing these numbers alone never grants a claim or publication permit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExecKey {
    pub(crate) os_slot: u32,
    pub(crate) os_generation: u64,
    pub(crate) application: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) response_serial: u64,
    pub(crate) response_physical: u64,
}

/// Deliberately UNIMPLEMENTED by the native backend in this preparation.
///
/// # Safety
/// Implementor is held by the ORIGINAL exact Response, with this key bound to
/// retained OS/application/worker/delivery/response-tag owners. It already owns
/// the exact descriptor claim before staging any bytes. reserve_sections must
/// atomically acquire every nonempty section's entire extent under the real
/// ledger, after all mapping/extent/conflict/quiescence checks and allocation.
/// Failure leaves no page writes or partial new claims. Success retains ALL
/// tags/mapping owners through real RET status publication; cancellation,
/// queue-full and uncertain transport retain/quarantine them. Ordinary Drop
/// cannot release any unacknowledged owner. Never overwrite payloads[slot].
pub(crate) unsafe trait ResponseOwnedExecClaims {
    fn key(&self) -> ExecKey;
    fn descriptor(&self) -> Step;
    fn reserve_sections(&mut self, sections: &[Section]) -> Result<()>;
}

/// Checked plan/cursor only. Native activation must acquire the descriptor and
/// every full Section extent as one retained response-owned group first.
pub(crate) struct Phase2 {
    key: ExecKey,
    request: Request,
    descriptor: Step,
    sections: [Section; image::MAX_SECTIONS],
    count: usize,
    section: usize,
    page: u64,
    staged: bool,
    descriptor_delivered: bool,
    sections_reserved: bool,
}

impl Phase2 {
    pub(crate) fn begin(request: &Request, key: ExecKey) -> Result<Self> {
        let a = request.arguments();
        let bytes = usize::try_from(a[2]).map_err(|_| -75)?;
        if key.os_generation == 0 || key.application == 0 || key.worker == 0
            || key.delivery == 0 || key.response_serial == 0 || key.response_physical != request.response()
            || request.number() != 59 || a[0] != 2 || a[1] == 0 || a[1] % PAGE != 0
            || !(image::HEADER + image::SECTION..=image::DESCRIPTOR_CAPACITY).contains(&bytes)
            || (bytes - image::HEADER) % image::SECTION != 0
            || a[1].checked_add(bytes as u64).is_none()
        { return Err(-22); }
        Ok(Self { key, request: request.clone(), descriptor: Step { physical: a[1], bytes, direction: 1 },
            sections: [Section::default(); image::MAX_SECTIONS], count: 0,
            section: 0, page: 0, staged: false, descriptor_delivered: false, sections_reserved: false })
    }

    /// Called from the exact retained descriptor claim. On user-copy failure
    /// keep these immutable bytes outside this helper and retry that same read;
    /// never re-read a changed guest descriptor or replace this staged plan.
    pub(crate) fn stage_descriptor(&mut self, request: &Request, key: ExecKey, bytes: &[u8]) -> Result<()> {
        if key != self.key || request != &self.request || self.staged { return Err(-16); }
        if bytes.len() != self.descriptor.bytes || image::descriptor_bytes(bytes)? != bytes.len()
        { return Err(-22); }
        let mut sections = [Section::default(); image::MAX_SECTIONS];
        let mut count = 0;
        for raw in bytes[image::HEADER..].chunks_exact(image::SECTION) {
            let (_, _, pages) = section_geometry(raw)?;
            let physical = image::word(raw, 16)?;
            if pages != 0 && (physical == 0 || physical % PAGE != 0
                || pages.checked_mul(PAGE).and_then(|n| physical.checked_add(n)).is_none())
            { return Err(-22); }
            if pages != 0 {
                let end = physical + pages * PAGE;
                let descriptor_end = self.descriptor.physical + self.descriptor.bytes as u64;
                if physical < descriptor_end && self.descriptor.physical < end { return Err(-22); }
                for old in &sections[..count] {
                    if old.pages != 0 && physical < old.physical + old.pages * PAGE && old.physical < end
                    { return Err(-22); }
                }
            }
            sections[count] = Section { physical, pages };
            count += 1;
        }
        // Publish no partial plan on malformed later sections.
        self.sections = sections;
        self.count = count;
        self.staged = true;
        Ok(())
    }

    /// Geometry only: native caller must separately validate retained extents,
    /// conflicts and all claim lifetimes. Zero-file/BSS sections need no upload.
    pub(crate) fn sections(&self) -> Result<&[Section]> {
        if !self.staged { return Err(-16); }
        Ok(&self.sections[..self.count])
    }

    /// Real backend claims are acquired atomically, once. A failed reservation
    /// leaves the cursor and eligibility unchanged and can be retried exactly.
    pub(crate) fn reserve_sections(&mut self, group: &mut impl ResponseOwnedExecClaims) -> Result<()> {
        if !self.staged || self.sections_reserved || group.key() != self.key
            || group.descriptor() != self.descriptor { return Err(-16); }
        group.reserve_sections(&self.sections[..self.count])?;
        self.sections_reserved = true;
        Ok(())
    }

    pub(crate) fn expected(&self, request: &Request, key: ExecKey) -> Result<Option<Step>> {
        if key != self.key || request != &self.request { return Err(-16); }
        if !self.descriptor_delivered { return Ok(Some(self.descriptor)); }
        if !self.sections_reserved { return Err(-16); }
        if self.section == self.count { return Ok(None); }
        let section = self.sections[self.section];
        Ok(Some(Step { physical: section.physical + self.page * PAGE, bytes: PAGE as usize, direction: 0 }))
    }

    /// Commit only AFTER actual full copy and, for descriptor downloads, after
    /// successful UserSlice writer. Copy failure leaves expected() unchanged.
    /// This does not release any descriptor/page claim; retain all until RET.
    pub(crate) fn copied(&mut self, request: &Request, key: ExecKey, step: Step) -> Result<()> {
        if !self.staged || self.expected(request, key)? != Some(step) { return Err(-22); }
        if !self.descriptor_delivered { self.descriptor_delivered = true; }
        else { self.page += 1; }
        while self.section < self.count && self.page == self.sections[self.section].pages {
            self.section += 1;
            self.page = 0;
        }
        Ok(())
    }

    /// Only the native original-response owner may use this to permit RET0.
    pub(crate) fn complete(&self, request: &Request, key: ExecKey) -> Result<bool> {
        if key != self.key || request != &self.request { return Err(-16); }
        Ok(self.staged && self.descriptor_delivered && self.sections_reserved && self.expected(request, key)?.is_none())
    }
}
