// SPDX-License-Identifier: GPL-2.0
//! Checked placement of the preserved x86_64 McKernel ELF image.
//!
//! Reuse the canonical SMP ownership map and IHK mapping geometry. The ELF
//! field offsets match the existing `kernel/rust/abi.rs` layouts; unlike the
//! application loaders, this parser accepts an immutable byte slice and never
//! casts an untrusted header to a Rust reference. Linux owns file reads and
//! physical writes in the attached adapters, not in this allocation-free core.

use super::ihk_mapping::{AlignedPhysicalRange, MappingError, PageGeometry, PhysicalRange};
use super::smp_resource::{MemoryExtent, MemoryMap, OsToken};

pub(crate) const KERNEL_BASE: u64 = 0xffff_ffff_fe80_0000;
pub(crate) const KERNEL_WINDOW_BYTES: u64 = 8 << 20;
pub(crate) const IDENTITY_WINDOW_END: u64 = 256 << 30;
const LARGE_PAGE_BYTES: u64 = 2 << 20;
const HEADER_BYTES: usize = 64;
const PROGRAM_HEADER_BYTES: usize = 56;
const MAX_PROGRAM_HEADERS: usize = 64;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ImageError {
    BadElf,
    NoBootstrapMemory,
    InvalidOwnership,
    OutsideBootstrap,
    SegmentOverlap,
    BadEntry,
    Overflow,
}

impl From<MappingError> for ImageError {
    fn from(error: MappingError) -> Self {
        match error {
            MappingError::AddressOverflow => Self::Overflow,
            _ => Self::OutsideBootstrap,
        }
    }
}

/// Addresses only; this value cannot grant access to memory or start a CPU.
/// An adapter must retain the exact OS lease and the resource-map lock.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BootLayout {
    extent: MemoryExtent,
    kernel: AlignedPhysicalRange,
    startup: u64,
    stack: u64,
}

impl BootLayout {
    pub(crate) fn select<const N: usize>(
        map: &MemoryMap<N>,
        owner: OsToken,
    ) -> Result<Self, ImageError> {
        map.validate().map_err(|_| ImageError::InvalidOwnership)?;
        let mut selected: Option<MemoryExtent> = None;
        for index in 0..map.len() {
            let extent = map.extent(index).ok_or(ImageError::InvalidOwnership)?;
            if extent.owner() != Some(owner) {
                continue;
            }
            // Preserve lowest-node/largest-chunk selection, but consider only
            // this exact owner. The old C minimum-node loop included other OSes.
            if selected.is_none_or(|old| {
                extent.numa_node() < old.numa_node()
                    || (extent.numa_node() == old.numa_node() && extent.length() > old.length())
            }) {
                selected = Some(extent);
            }
        }
        Self::from_extent(selected.ok_or(ImageError::NoBootstrapMemory)?)
    }

    fn from_extent(extent: MemoryExtent) -> Result<Self, ImageError> {
        if extent.owner().is_none() {
            return Err(ImageError::InvalidOwnership);
        }
        let pages = PageGeometry::new(12)?;
        let large = PageGeometry::new(21)?;
        let owned = PhysicalRange::new(extent.start(), extent.length())?;
        if owned.end() > IDENTITY_WINDOW_END {
            return Err(ImageError::OutsideBootstrap);
        }
        let physical = large.align_up(
            extent
                .start()
                .checked_add(LARGE_PAGE_BYTES)
                .ok_or(ImageError::Overflow)?,
        )?;
        let kernel = AlignedPhysicalRange::from_start_length(physical, KERNEL_WINDOW_BYTES, pages)?;
        let startup = large
            .align_down(owned.end())
            .checked_sub(2 * LARGE_PAGE_BYTES)
            .ok_or(ImageError::OutsideBootstrap)?;
        let stack = owned
            .end()
            .checked_sub(pages.size())
            .ok_or(ImageError::OutsideBootstrap)?;
        if !owned.contains(kernel.range())
            || kernel.end() > startup
            || !owned.contains(PhysicalRange::new(startup, pages.size())?)
            || startup + pages.size() > stack - pages.size()
        {
            return Err(ImageError::OutsideBootstrap);
        }
        Ok(Self {
            extent,
            kernel,
            startup,
            stack,
        })
    }

    pub(crate) const fn extent(self) -> MemoryExtent {
        self.extent
    }

    pub(crate) const fn kernel(self) -> AlignedPhysicalRange {
        self.kernel
    }

    pub(crate) const fn startup(self) -> u64 {
        self.startup
    }

    pub(crate) const fn stack(self) -> u64 {
        self.stack
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Segment<'image> {
    pub(crate) destination: u64,
    pub(crate) memory_bytes: u64,
    pub(crate) file: &'image [u8],
    pub(crate) executable: bool,
}

/// Describes the image's actual compiled boot ABI. This is compatibility
/// metadata, not image authentication or permission to execute an image.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct NativeBootAbi {
    pub(crate) header_bytes: usize,
    pub(crate) performance: bool,
    pub(crate) completed_queue_reads: bool,
    pub(crate) generic_vdso: bool,
}

/// All program headers and destination ranges are checked before this exists.
/// The immutable input borrow prevents header/segment changes between preflight
/// and execution. No per-segment array occupies the Linux kernel stack.
#[derive(Debug)]
pub(crate) struct ImagePlan<'image> {
    image: &'image [u8],
    headers: &'image [u8],
    layout: BootLayout,
    entry: u64,
    load_segments: usize,
    native_boot_abi: Option<NativeBootAbi>,
}

fn bytes<const N: usize>(input: &[u8], offset: usize) -> Result<[u8; N], ImageError> {
    input
        .get(offset..offset.checked_add(N).ok_or(ImageError::Overflow)?)
        .ok_or(ImageError::BadElf)?
        .try_into()
        .map_err(|_| ImageError::BadElf)
}

fn u16_at(input: &[u8], offset: usize) -> Result<u16, ImageError> {
    Ok(u16::from_le_bytes(bytes(input, offset)?))
}

fn u32_at(input: &[u8], offset: usize) -> Result<u32, ImageError> {
    Ok(u32::from_le_bytes(bytes(input, offset)?))
}

fn u64_at(input: &[u8], offset: usize) -> Result<u64, ImageError> {
    Ok(u64::from_le_bytes(bytes(input, offset)?))
}

impl<'image> ImagePlan<'image> {
    pub(crate) fn parse(image: &'image [u8], layout: BootLayout) -> Result<Self, ImageError> {
        if image.get(..7) != Some(&b"\x7fELF\x02\x01\x01"[..])
            || u16_at(image, 16)? != 2
            || u16_at(image, 18)? != 62
            || u32_at(image, 20)? != 1
            || u32_at(image, 48)? != 0
            || u16_at(image, 52)? as usize != HEADER_BYTES
            || u16_at(image, 54)? as usize != PROGRAM_HEADER_BYTES
        {
            return Err(ImageError::BadElf);
        }
        let count = u16_at(image, 56)? as usize;
        let offset = usize::try_from(u64_at(image, 32)?).map_err(|_| ImageError::Overflow)?;
        let end = offset
            .checked_add(count * PROGRAM_HEADER_BYTES)
            .ok_or(ImageError::Overflow)?;
        if count == 0 || count > MAX_PROGRAM_HEADERS || offset < HEADER_BYTES || end > 4096 {
            return Err(ImageError::BadElf);
        }
        let headers = image.get(offset..end).ok_or(ImageError::BadElf)?;
        let mut plan = Self {
            image,
            headers,
            layout,
            entry: u64_at(image, 24)?,
            load_segments: 0,
            native_boot_abi: None,
        };
        let entry_offset = plan
            .entry
            .checked_sub(KERNEL_BASE)
            .ok_or(ImageError::BadEntry)?;
        let mut entry_found = false;
        for (index, header) in headers.chunks_exact(PROGRAM_HEADER_BYTES).enumerate() {
            if u32_at(header, 0)? == 4 {
                plan.read_notes(header)?;
            }
            let Some(segment) = plan.segment(header)? else {
                continue;
            };
            plan.load_segments += 1;
            let start = segment.destination - layout.kernel.start();
            let end = start + segment.memory_bytes;
            // The entry must be present in an executable file-backed range;
            // a zero-filled BSS address is never a valid image entry point.
            if segment.executable
                && start <= entry_offset
                && entry_offset < start + segment.file.len() as u64
            {
                entry_found = true;
            }
            for prior in headers[..index * PROGRAM_HEADER_BYTES].chunks_exact(PROGRAM_HEADER_BYTES)
            {
                if let Some(other) = plan.segment(prior)? {
                    let other_start = other.destination - layout.kernel.start();
                    if start < other_start + other.memory_bytes && other_start < end {
                        return Err(ImageError::SegmentOverlap);
                    }
                }
            }
        }
        if !entry_found || plan.load_segments == 0 {
            return Err(ImageError::BadEntry);
        }
        Ok(plan)
    }

    fn read_notes(&mut self, header: &[u8]) -> Result<(), ImageError> {
        let offset = usize::try_from(u64_at(header, 8)?).map_err(|_| ImageError::Overflow)?;
        let length = usize::try_from(u64_at(header, 32)?).map_err(|_| ImageError::Overflow)?;
        // Keep optional metadata bounded independently of image load segments.
        if length > 4096 {
            return Err(ImageError::BadElf);
        }
        let end = offset.checked_add(length).ok_or(ImageError::Overflow)?;
        let notes = self.image.get(offset..end).ok_or(ImageError::BadElf)?;
        let mut cursor = 0;
        while cursor < notes.len() {
            let name_bytes = u32_at(notes, cursor)? as usize;
            let descriptor_bytes = u32_at(notes, cursor + 4)? as usize;
            let kind = u32_at(notes, cursor + 8)?;
            let name_start = cursor + 12;
            let name_end = name_start
                .checked_add(name_bytes)
                .ok_or(ImageError::Overflow)?;
            let descriptor_start = name_end.checked_add(3).ok_or(ImageError::Overflow)? & !3;
            let descriptor_end = descriptor_start
                .checked_add(descriptor_bytes)
                .ok_or(ImageError::Overflow)?;
            let next = descriptor_end.checked_add(3).ok_or(ImageError::Overflow)? & !3;
            let name = notes.get(name_start..name_end).ok_or(ImageError::BadElf)?;
            let descriptor = notes
                .get(descriptor_start..descriptor_end)
                .ok_or(ImageError::BadElf)?;
            if next > notes.len() {
                return Err(ImageError::BadElf);
            }
            if name == b"MCKERNEL\0" && kind == 0x4d43_4b01 {
                if self.native_boot_abi.is_some()
                    || descriptor_bytes != 16
                    || !matches!(u32_at(descriptor, 0)?, 1 | 2 | 3)
                    || u32_at(descriptor, 4)? != 0x0006_0c00
                {
                    return Err(ImageError::BadElf);
                }
                let header_bytes = u32_at(descriptor, 8)? as usize;
                let flags = u32_at(descriptor, 12)?;
                if !matches!((header_bytes, flags), (6656, 0) | (7616, 1)) {
                    return Err(ImageError::BadElf);
                }
                self.native_boot_abi = Some(NativeBootAbi {
                    header_bytes,
                    performance: flags == 1,
                    completed_queue_reads: u32_at(descriptor, 0)? >= 2,
                    generic_vdso: u32_at(descriptor, 0)? >= 3,
                });
            }
            cursor = next;
        }
        Ok(())
    }

    fn segment(&self, header: &[u8]) -> Result<Option<Segment<'image>>, ImageError> {
        match u32_at(header, 0)? {
            1 => {}
            0 | 4 | 6 | 0x6474_e551 | 0x6474_e552 => return Ok(None),
            _ => return Err(ImageError::BadElf),
        }
        let flags = u32_at(header, 4)?;
        let offset = u64_at(header, 8)?;
        let virtual_address = u64_at(header, 16)?;
        let file_bytes = u64_at(header, 32)?;
        let memory_bytes = u64_at(header, 40)?;
        let alignment = u64_at(header, 48)?;
        if flags & !7 != 0 || file_bytes > memory_bytes || memory_bytes == 0 {
            return Err(ImageError::BadElf);
        }
        if alignment > 1
            && (!alignment.is_power_of_two() || virtual_address % alignment != offset % alignment)
        {
            return Err(ImageError::BadElf);
        }
        let relative = virtual_address
            .checked_sub(KERNEL_BASE)
            .ok_or(ImageError::OutsideBootstrap)?;
        let destination = self
            .layout
            .kernel
            .start()
            .checked_add(relative)
            .ok_or(ImageError::Overflow)?;
        let memory = PhysicalRange::new(destination, memory_bytes)?;
        if !self.layout.kernel.range().contains(memory) {
            return Err(ImageError::OutsideBootstrap);
        }
        virtual_address
            .checked_add(memory_bytes)
            .ok_or(ImageError::Overflow)?;
        let file_end = offset.checked_add(file_bytes).ok_or(ImageError::Overflow)?;
        let offset = usize::try_from(offset).map_err(|_| ImageError::Overflow)?;
        let file_end = usize::try_from(file_end).map_err(|_| ImageError::Overflow)?;
        let file = self.image.get(offset..file_end).ok_or(ImageError::BadElf)?;
        Ok(Some(Segment {
            destination,
            memory_bytes,
            file,
            executable: flags & 1 != 0,
        }))
    }

    pub(crate) const fn layout(&self) -> BootLayout {
        self.layout
    }
    pub(crate) const fn entry(&self) -> u64 {
        self.entry
    }
    pub(crate) const fn load_segments(&self) -> usize {
        self.load_segments
    }

    pub(crate) const fn native_boot_abi(&self) -> Option<NativeBootAbi> {
        self.native_boot_abi
    }

    pub(crate) fn segments(&self) -> impl Iterator<Item = Segment<'image>> + '_ {
        self.headers
            .chunks_exact(PROGRAM_HEADER_BYTES)
            .filter_map(|header| {
                self.segment(header)
                    .expect("immutable preflighted ELF header")
            })
    }
}
