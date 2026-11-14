// SPDX-License-Identifier: GPL-2.0
//! Allocation-free validation core for IHK physical and virtual mappings.
//!
//! This file deliberately contains no Linux bindings.  It turns raw address,
//! length, VMA, cache-policy, and adapter-result values into checked
//! descriptors, and models the cleanup obligations around a user mapping.
//! A later adapter must connect those descriptors to the exact Rocky kernel
//! APIs and prove ordering, locking, pinning, and VMA lifetime behavior.

/// Smallest Linux errno accepted from a mapping adapter.
const LINUX_ERRNO_MIN: i32 = -4095;

/// A validated negative Linux errno.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LinuxErrno(i32);

impl LinuxErrno {
    pub(crate) const EINVAL: Self = Self(-22);
    pub(crate) const ENOMEM: Self = Self(-12);
    pub(crate) const ENOSYS: Self = Self(-38);
    pub(crate) const EOVERFLOW: Self = Self(-75);
    pub(crate) const EALREADY: Self = Self(-114);

    /// Accept only the kernel's conventional negative errno range.
    pub(crate) fn from_adapter(code: i32) -> Result<Self, MappingError> {
        if (LINUX_ERRNO_MIN..=-1).contains(&code) {
            Ok(Self(code))
        } else {
            Err(MappingError::InvalidAdapterErrno)
        }
    }

    pub(crate) const fn get(self) -> i32 {
        self.0
    }
}

/// Deterministic validation failures produced before Linux APIs are called.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MappingError {
    InvalidPageShift,
    ZeroLength,
    AddressOverflow,
    Misaligned,
    OutsidePhysicalWindow,
    InvalidCachePolicy,
    InvalidProtection,
    InvalidAdapterErrno,
    InvalidTransition,
    ZeroMappedAddress,
    TranslationMismatch,
}

impl MappingError {
    pub(crate) const fn errno(self) -> LinuxErrno {
        match self {
            Self::AddressOverflow => LinuxErrno::EOVERFLOW,
            Self::InvalidTransition => LinuxErrno::EALREADY,
            Self::ZeroMappedAddress
            | Self::InvalidPageShift
            | Self::ZeroLength
            | Self::Misaligned
            | Self::OutsidePhysicalWindow
            | Self::InvalidCachePolicy
            | Self::InvalidProtection
            | Self::InvalidAdapterErrno
            | Self::TranslationMismatch => LinuxErrno::EINVAL,
        }
    }
}

/// Host base-page geometry supplied by the future Linux adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PageGeometry {
    shift: u8,
    size: u64,
    mask: u64,
}

impl PageGeometry {
    /// Linux base-page shifts from 4 KiB through 2^63 bytes are representable.
    pub(crate) fn new(shift: u8) -> Result<Self, MappingError> {
        if !(12..=63).contains(&shift) {
            return Err(MappingError::InvalidPageShift);
        }
        let size = 1_u64
            .checked_shl(u32::from(shift))
            .ok_or(MappingError::InvalidPageShift)?;
        Ok(Self {
            shift,
            size,
            mask: size - 1,
        })
    }

    pub(crate) const fn shift(self) -> u8 {
        self.shift
    }

    pub(crate) const fn size(self) -> u64 {
        self.size
    }

    pub(crate) const fn is_aligned(self, address: u64) -> bool {
        address & self.mask == 0
    }

    pub(crate) const fn align_down(self, address: u64) -> u64 {
        address & !self.mask
    }

    pub(crate) fn align_up(self, address: u64) -> Result<u64, MappingError> {
        if self.is_aligned(address) {
            return Ok(address);
        }
        address
            .checked_add(self.mask)
            .map(|value| value & !self.mask)
            .ok_or(MappingError::AddressOverflow)
    }

    pub(crate) fn pfn_to_address(self, pfn: u64) -> Result<u64, MappingError> {
        pfn.checked_mul(self.size)
            .ok_or(MappingError::AddressOverflow)
    }

    pub(crate) fn address_to_pfn(self, address: u64) -> Result<u64, MappingError> {
        if !self.is_aligned(address) {
            return Err(MappingError::Misaligned);
        }
        Ok(address >> self.shift)
    }
}

/// Non-empty half-open physical byte range with a checked exclusive end.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PhysicalRange {
    start: u64,
    end: u64,
}

impl PhysicalRange {
    pub(crate) fn new(start: u64, length: u64) -> Result<Self, MappingError> {
        if length == 0 {
            return Err(MappingError::ZeroLength);
        }
        let end = start
            .checked_add(length)
            .ok_or(MappingError::AddressOverflow)?;
        Ok(Self { start, end })
    }

    pub(crate) fn from_bounds(start: u64, end: u64) -> Result<Self, MappingError> {
        let length = end.checked_sub(start).ok_or(MappingError::ZeroLength)?;
        Self::new(start, length)
    }

    pub(crate) const fn start(self) -> u64 {
        self.start
    }

    pub(crate) const fn end(self) -> u64 {
        self.end
    }

    pub(crate) const fn length(self) -> u64 {
        self.end - self.start
    }

    pub(crate) const fn contains(self, other: Self) -> bool {
        self.start <= other.start && other.end <= self.end
    }

    pub(crate) fn covering_pages(
        self,
        pages: PageGeometry,
    ) -> Result<AlignedPhysicalRange, MappingError> {
        let start = pages.align_down(self.start);
        let end = pages.align_up(self.end)?;
        AlignedPhysicalRange::from_bounds(start, end, pages)
    }
}

/// Page-aligned, non-empty physical byte range.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct AlignedPhysicalRange(PhysicalRange);

impl AlignedPhysicalRange {
    pub(crate) fn from_bounds(
        start: u64,
        end: u64,
        pages: PageGeometry,
    ) -> Result<Self, MappingError> {
        if !pages.is_aligned(start) || !pages.is_aligned(end) {
            return Err(MappingError::Misaligned);
        }
        Ok(Self(PhysicalRange::from_bounds(start, end)?))
    }

    pub(crate) fn from_start_length(
        start: u64,
        length: u64,
        pages: PageGeometry,
    ) -> Result<Self, MappingError> {
        let range = PhysicalRange::new(start, length)?;
        if !pages.is_aligned(range.start()) || !pages.is_aligned(range.end()) {
            return Err(MappingError::Misaligned);
        }
        Ok(Self(range))
    }

    pub(crate) const fn range(self) -> PhysicalRange {
        self.0
    }

    pub(crate) const fn start(self) -> u64 {
        self.0.start()
    }

    pub(crate) const fn end(self) -> u64 {
        self.0.end()
    }

    pub(crate) const fn length(self) -> u64 {
        self.0.length()
    }
}

/// Exact values of the frozen IHK mapping flags.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(i32)]
pub(crate) enum CachePolicy {
    Cached = 0,
    Uncached = 1,
}

impl CachePolicy {
    pub(crate) fn from_legacy_flag(flag: i32) -> Result<Self, MappingError> {
        match flag {
            0 => Ok(Self::Cached),
            1 => Ok(Self::Uncached),
            _ => Err(MappingError::InvalidCachePolicy),
        }
    }

    pub(crate) const fn legacy_flag(self) -> i32 {
        self as i32
    }
}

/// A checked kernel-virtual mapping description without an API call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct KernelMapDescriptor {
    requested: PhysicalRange,
    mapped: AlignedPhysicalRange,
    byte_offset: u64,
    desired_virtual_base: Option<u64>,
    cache_policy: CachePolicy,
}

impl KernelMapDescriptor {
    pub(crate) fn new(
        requested: PhysicalRange,
        desired_virtual: Option<u64>,
        cache_policy: CachePolicy,
        pages: PageGeometry,
    ) -> Result<Self, MappingError> {
        let mapped = requested.covering_pages(pages)?;
        let byte_offset = requested.start() - mapped.start();
        let desired_virtual_base = match desired_virtual {
            Some(address) => {
                if address == 0 {
                    return Err(MappingError::ZeroMappedAddress);
                }
                if address & (pages.size() - 1) != byte_offset {
                    return Err(MappingError::Misaligned);
                }
                address
                    .checked_add(requested.length())
                    .ok_or(MappingError::AddressOverflow)?;
                let base = address
                    .checked_sub(byte_offset)
                    .ok_or(MappingError::AddressOverflow)?;
                if base == 0 {
                    return Err(MappingError::ZeroMappedAddress);
                }
                base.checked_add(mapped.length())
                    .ok_or(MappingError::AddressOverflow)?;
                Some(base)
            }
            None => None,
        };
        Ok(Self {
            requested,
            mapped,
            byte_offset,
            desired_virtual_base,
            cache_policy,
        })
    }

    pub(crate) const fn requested(self) -> PhysicalRange {
        self.requested
    }

    pub(crate) const fn mapped(self) -> AlignedPhysicalRange {
        self.mapped
    }

    pub(crate) const fn byte_offset(self) -> u64 {
        self.byte_offset
    }

    pub(crate) const fn desired_virtual_base(self) -> Option<u64> {
        self.desired_virtual_base
    }

    pub(crate) const fn cache_policy(self) -> CachePolicy {
        self.cache_policy
    }
}

/// VMA protection facts supplied by a future file-operation adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MmapProtection {
    pub(crate) readable: bool,
    pub(crate) writable: bool,
    pub(crate) executable: bool,
    pub(crate) shared: bool,
}

/// Explicit protection policy; the validation core does not invent one.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MmapProtectionPolicy {
    pub(crate) require_readable: bool,
    pub(crate) allow_write: bool,
    pub(crate) allow_execute: bool,
    pub(crate) require_shared: bool,
}

impl MmapProtectionPolicy {
    pub(crate) fn validate(self, protection: MmapProtection) -> Result<(), MappingError> {
        if (self.require_readable && !protection.readable)
            || (!self.allow_write && protection.writable)
            || (!self.allow_execute && protection.executable)
            || (self.require_shared && !protection.shared)
        {
            return Err(MappingError::InvalidProtection);
        }
        Ok(())
    }
}

/// Validated user VMA and page-offset request bounded by one authorized window.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct UserMmapRequest {
    user_start: u64,
    user_end: u64,
    physical: AlignedPhysicalRange,
    protection: MmapProtection,
}

impl UserMmapRequest {
    pub(crate) fn validate(
        user_start: u64,
        user_end: u64,
        page_offset: u64,
        pages: PageGeometry,
        allowed_window: PhysicalRange,
        protection: MmapProtection,
        policy: MmapProtectionPolicy,
    ) -> Result<Self, MappingError> {
        if !pages.is_aligned(user_start) || !pages.is_aligned(user_end) {
            return Err(MappingError::Misaligned);
        }
        let length = user_end
            .checked_sub(user_start)
            .ok_or(MappingError::ZeroLength)?;
        if length == 0 {
            return Err(MappingError::ZeroLength);
        }
        policy.validate(protection)?;
        let physical_start = pages.pfn_to_address(page_offset)?;
        let physical = AlignedPhysicalRange::from_start_length(
            physical_start,
            length,
            pages,
        )?;
        if !allowed_window.contains(physical.range()) {
            return Err(MappingError::OutsidePhysicalWindow);
        }
        Ok(Self {
            user_start,
            user_end,
            physical,
            protection,
        })
    }

    pub(crate) const fn user_start(self) -> u64 {
        self.user_start
    }

    pub(crate) const fn user_end(self) -> u64 {
        self.user_end
    }

    pub(crate) const fn length(self) -> u64 {
        self.user_end - self.user_start
    }

    pub(crate) const fn physical(self) -> AlignedPhysicalRange {
        self.physical
    }

    pub(crate) const fn protection(self) -> MmapProtection {
        self.protection
    }
}

/// A validated device translation suitable for a later `remap_pfn_range` call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DeviceMapping {
    remote: AlignedPhysicalRange,
    local: AlignedPhysicalRange,
    local_pfn: u64,
}

impl DeviceMapping {
    pub(crate) fn new(
        request: UserMmapRequest,
        local_start: u64,
        pages: PageGeometry,
    ) -> Result<Self, MappingError> {
        if local_start == 0 {
            return Err(MappingError::ZeroMappedAddress);
        }
        let local = AlignedPhysicalRange::from_start_length(
            local_start,
            request.length(),
            pages,
        )?;
        let local_pfn = pages.address_to_pfn(local.start())?;
        Ok(Self {
            remote: request.physical(),
            local,
            local_pfn,
        })
    }

    pub(crate) const fn remote(self) -> AlignedPhysicalRange {
        self.remote
    }

    pub(crate) const fn local(self) -> AlignedPhysicalRange {
        self.local
    }

    pub(crate) const fn local_pfn(self) -> u64 {
        self.local_pfn
    }
}

/// A cleanup operation that a later Linux adapter must execute in order.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CleanupStep {
    UnmapUser {
        user_start: u64,
        length: u64,
    },
    UnmapDevice {
        local: AlignedPhysicalRange,
    },
}

/// Ordered, fixed-capacity rollback description preserving the original errno.
#[must_use = "mapping cleanup plans must be executed by the Linux adapter"]
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct RollbackPlan {
    errno: Option<LinuxErrno>,
    steps: [Option<CleanupStep>; 2],
}

impl RollbackPlan {
    const fn none(errno: LinuxErrno) -> Self {
        Self {
            errno: Some(errno),
            steps: [None, None],
        }
    }

    const fn device(errno: LinuxErrno, local: AlignedPhysicalRange) -> Self {
        Self {
            errno: Some(errno),
            steps: [Some(CleanupStep::UnmapDevice { local }), None],
        }
    }

    const fn user_then_device(
        errno: LinuxErrno,
        request: UserMmapRequest,
        local: AlignedPhysicalRange,
    ) -> Self {
        Self {
            errno: Some(errno),
            steps: [
                Some(CleanupStep::UnmapUser {
                    user_start: request.user_start(),
                    length: request.length(),
                }),
                Some(CleanupStep::UnmapDevice { local }),
            ],
        }
    }

    const fn close(local: AlignedPhysicalRange) -> Self {
        Self {
            errno: None,
            steps: [Some(CleanupStep::UnmapDevice { local }), None],
        }
    }

    pub(crate) const fn errno(&self) -> Option<LinuxErrno> {
        self.errno
    }

    /// Consume the next cleanup operation so it cannot be replayed by mistake.
    pub(crate) fn next_step(&mut self) -> Option<CleanupStep> {
        let next = self.steps[0].take();
        self.steps[0] = self.steps[1].take();
        next
    }
}

/// Explicit state of the allocation-free mmap preparation protocol.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MmapStage {
    Validated,
    DeviceMapped,
    UserRemapped,
    Live,
    Terminal,
}

/// One owner of the cleanup state for a validated user mapping request.
#[must_use = "mapping transactions must reach rollback, live, or close"]
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct MmapTransaction {
    request: UserMmapRequest,
    mapping: Option<DeviceMapping>,
    stage: MmapStage,
}

impl MmapTransaction {
    pub(crate) const fn new(request: UserMmapRequest) -> Self {
        Self {
            request,
            mapping: None,
            stage: MmapStage::Validated,
        }
    }

    pub(crate) const fn stage(&self) -> MmapStage {
        self.stage
    }

    pub(crate) fn record_device_mapping(
        &mut self,
        mapping: DeviceMapping,
    ) -> Result<(), MappingError> {
        if self.stage != MmapStage::Validated {
            return Err(MappingError::InvalidTransition);
        }
        if mapping.remote() != self.request.physical() {
            return Err(MappingError::TranslationMismatch);
        }
        self.mapping = Some(mapping);
        self.stage = MmapStage::DeviceMapped;
        Ok(())
    }

    pub(crate) fn record_user_remap(&mut self) -> Result<(), MappingError> {
        if self.stage != MmapStage::DeviceMapped {
            return Err(MappingError::InvalidTransition);
        }
        self.stage = MmapStage::UserRemapped;
        Ok(())
    }

    pub(crate) fn record_metadata_installed(&mut self) -> Result<(), MappingError> {
        if self.stage != MmapStage::UserRemapped {
            return Err(MappingError::InvalidTransition);
        }
        self.stage = MmapStage::Live;
        Ok(())
    }

    /// Freeze the transaction and return cleanup in adapter execution order.
    pub(crate) fn rollback(
        &mut self,
        errno: LinuxErrno,
    ) -> Result<RollbackPlan, MappingError> {
        let plan = match (self.stage, self.mapping) {
            (MmapStage::Validated, None) => RollbackPlan::none(errno),
            (MmapStage::DeviceMapped, Some(mapping)) => {
                RollbackPlan::device(errno, mapping.local())
            }
            (MmapStage::UserRemapped, Some(mapping)) => {
                RollbackPlan::user_then_device(errno, self.request, mapping.local())
            }
            _ => return Err(MappingError::InvalidTransition),
        };
        self.stage = MmapStage::Terminal;
        self.mapping = None;
        Ok(plan)
    }

    /// VMA close already removes the user PTEs; release only the device map.
    pub(crate) fn vma_close(&mut self) -> Result<RollbackPlan, MappingError> {
        if self.stage != MmapStage::Live {
            return Err(MappingError::InvalidTransition);
        }
        let mapping = self.mapping.ok_or(MappingError::InvalidTransition)?;
        self.stage = MmapStage::Terminal;
        self.mapping = None;
        Ok(RollbackPlan::close(mapping.local()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pages() -> PageGeometry {
        PageGeometry::new(12).unwrap()
    }

    fn request() -> UserMmapRequest {
        UserMmapRequest::validate(
            0x10_0000,
            0x10_2000,
            0x20,
            pages(),
            PhysicalRange::new(0x20_000, 0x20_000).unwrap(),
            MmapProtection {
                readable: true,
                writable: true,
                executable: false,
                shared: true,
            },
            MmapProtectionPolicy {
                require_readable: true,
                allow_write: true,
                allow_execute: false,
                require_shared: true,
            },
        )
        .unwrap()
    }

    #[test]
    fn page_geometry_and_range_edges_are_checked() {
        assert_eq!(PageGeometry::new(11), Err(MappingError::InvalidPageShift));
        assert_eq!(PageGeometry::new(64), Err(MappingError::InvalidPageShift));
        let page = pages();
        assert_eq!(page.align_down(0x1234), 0x1000);
        assert_eq!(page.align_up(0x1234), Ok(0x2000));
        assert_eq!(page.align_up(u64::MAX), Err(MappingError::AddressOverflow));
        assert_eq!(PhysicalRange::new(1, 0), Err(MappingError::ZeroLength));
        assert_eq!(
            PhysicalRange::new(u64::MAX, 1),
            Err(MappingError::AddressOverflow)
        );
    }

    #[test]
    fn mapped_translation_requires_nonzero_aligned_local_address() {
        let request = request();
        assert_eq!(
            DeviceMapping::new(request, 0, pages()),
            Err(MappingError::ZeroMappedAddress)
        );
        assert_eq!(
            DeviceMapping::new(request, 0x30_001, pages()),
            Err(MappingError::Misaligned)
        );
        let mapping = DeviceMapping::new(request, 0x30_000, pages()).unwrap();
        assert_eq!(mapping.local_pfn(), 0x30);
        assert_eq!(mapping.remote(), request.physical());
    }

    #[test]
    fn rollback_state_cannot_be_replayed() {
        let request = request();
        let mapping = DeviceMapping::new(request, 0x30_000, pages()).unwrap();
        let mut transaction = MmapTransaction::new(request);
        transaction.record_device_mapping(mapping).unwrap();
        let mut plan = transaction.rollback(LinuxErrno::ENOMEM).unwrap();
        assert_eq!(plan.errno(), Some(LinuxErrno::ENOMEM));
        assert_eq!(
            plan.next_step(),
            Some(CleanupStep::UnmapDevice {
                local: mapping.local()
            })
        );
        assert_eq!(plan.next_step(), None);
        assert_eq!(plan.next_step(), None);
        assert_eq!(
            transaction.rollback(LinuxErrno::ENOMEM),
            Err(MappingError::InvalidTransition)
        );
    }
}
