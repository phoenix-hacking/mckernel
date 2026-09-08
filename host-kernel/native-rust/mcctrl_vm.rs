// SPDX-License-Identifier: GPL-2.0
//! Linux mirror VMAs retain the exact application connection and MM identity.

use super::{application_image as wire, mcctrl_process::Registration};
use core::{
    ffi::{c_char, c_void},
    mem::{align_of, size_of, MaybeUninit},
    ptr::{self, NonNull},
    sync::atomic::{AtomicI32, Ordering},
};
use kernel::{bindings, prelude::*, sync::Arc};

// SAFETY: This exported Linux API borrows static operations and transfers one
// file reference. It retains operations.owner on success and leaves priv owned
// by the caller on error. The generated bindings do not include this prototype.
extern "C" {
    // Opaque Linux pointers avoid recursively exposing configuration-empty
    // lockdep types. No structure value crosses this C function boundary.
    fn anon_inode_getfile(
        name: *const c_char,
        operations: *const c_void,
        private: *mut c_void,
        flags: i32,
    ) -> *mut c_void;
}

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

struct CurrentMm(NonNull<bindings::mm_struct>);
impl CurrentMm {
    fn get() -> Result<Self> {
        // SAFETY: The current task remains valid; Linux acquires mm_users.
        let mm = unsafe { bindings::get_task_mm(bindings::get_current()) };
        Ok(Self(NonNull::new(mm).ok_or(ESRCH)?))
    }
}
impl Drop for CurrentMm {
    fn drop(&mut self) {
        // SAFETY: Balance exactly the transient mm_users reference. It is
        // never stored in a VMA-retained owner, which would form a cycle.
        unsafe { bindings::mmput(self.0.as_ptr()) };
    }
}

struct MmIdentity(NonNull<bindings::mm_struct>);
// SAFETY: Only identity and Linux's atomic structural reference are shared.
// VMA access additionally requires a transient current mm_users reference/lock.
unsafe impl Send for MmIdentity {}
unsafe impl Sync for MmIdentity {}
impl MmIdentity {
    fn from_current(mm: &CurrentMm) -> Result<Self> {
        // SAFETY: The current mm_users reference implies a live mm_count.
        // This is Linux mmgrab's atomic increment with checked overflow.
        let count = unsafe {
            AtomicI32::from_ptr(ptr::addr_of_mut!(
                (*mm.0.as_ptr())
                    .__bindgen_anon_1
                    .__bindgen_anon_1
                    .mm_count
                    .counter
            ))
        };
        count
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |n| {
                (n > 0).then(|| n.checked_add(1)).flatten()
            })
            .map_err(|_| errno(-75))?;
        Ok(Self(mm.0))
    }
}
impl Drop for MmIdentity {
    fn drop(&mut self) {
        // SAFETY: Balance exactly our mmgrab reference. SeqCst preserves the
        // full barrier required by Linux mmdrop and membarrier before release.
        let count = unsafe {
            AtomicI32::from_ptr(ptr::addr_of_mut!(
                (*self.0.as_ptr())
                    .__bindgen_anon_1
                    .__bindgen_anon_1
                    .mm_count
                    .counter
            ))
        };
        let old = count.fetch_sub(1, Ordering::SeqCst);
        assert!(old > 0);
        if old == 1 {
            // SAFETY: This was the final structural reference.
            unsafe { bindings::__mmdrop(self.0.as_ptr()) };
        }
    }
}

pub(super) struct Mirror {
    mm: MmIdentity,
    pub(super) start: u64,
    pub(super) end: u64,
}
struct MappingFile {
    registration: Arc<Registration>,
    mirror: Arc<Mirror>,
}

impl Mirror {
    pub(super) fn reserve(registration: Arc<Registration>) -> Result<Arc<Self>> {
        let mm = CurrentMm::get()?;
        // SAFETY: mm_users retains the MM. Read-locking protects find_vma and
        // its address snapshot; vm_mmap later takes its own write lock.
        let first = unsafe {
            let sem = ptr::addr_of_mut!((*mm.0.as_ptr()).__bindgen_anon_1.mmap_lock);
            bindings::down_read(sem);
            let vma = bindings::find_vma(mm.0.as_ptr(), 0);
            let first = if vma.is_null() {
                None
            } else {
                Some((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start)
            };
            bindings::up_read(sem);
            first
        };
        let end = wire::reservation_end(first).map_err(errno)?;
        let mirror = Arc::new(
            Self {
                mm: MmIdentity::from_current(&mm)?,
                start: 0,
                end,
            },
            GFP_KERNEL,
        )?;
        let private = Box::new(
            MappingFile {
                registration,
                mirror: mirror.clone(),
            },
            GFP_KERNEL,
        )?;
        let private = Box::into_raw(private);
        // SAFETY: The immutable operation table is module-resident. The private
        // owner transfers only if Linux returns a successful referenced file.
        let file = unsafe {
            anon_inode_getfile(
                c"[mckernel]".as_ptr(),
                ptr::addr_of!(FILE_OPERATIONS.0).cast(),
                private.cast(),
                2,
            )
        }
        .cast::<bindings::file>();
        if (-4095..0).contains(&(file as isize)) || file.is_null() {
            // SAFETY: anon_inode_getfile did not take ownership on error.
            unsafe { drop(Box::from_raw(private)) };
            return Err(if file.is_null() {
                EIO
            } else {
                errno(file as isize as i32)
            });
        }
        let result = (|| -> Result {
            // Linux abort_creds balances prepare_creds after the transient
            // override is reverted; no credential refcount is reimplemented.
            // SAFETY: These are current-task credential APIs. Only a new,
            // unpublished credential copy is modified.
            let promoted = unsafe { bindings::prepare_creds() };
            if promoted.is_null() {
                return Err(ENOMEM);
            }
            let address = unsafe {
                (*promoted).cap_effective.val |= 1 << 17; // CAP_SYS_RAWIO
                let original = bindings::override_creds(promoted);
                // MAP_FIXED_NOREPLACE | MAP_SHARED, PROT_READ|WRITE|EXEC.
                // A mapping raced into the snapshot gap fails with EEXIST.
                let address = bindings::vm_mmap(file, 0, end, 7, 0x100001, 0);
                bindings::revert_creds(original);
                bindings::abort_creds(promoted);
                address
            };
            if (-4095..0).contains(&(address as isize)) {
                return Err(errno(address as isize as i32));
            }
            if address != 0 {
                return Err(EIO);
            }
            Ok(())
        })();
        // SAFETY: Drop the creator's single file reference. A successful VMA
        // has its own reference; otherwise release returns the private owner.
        unsafe { bindings::fput(file) };
        result?;
        Ok(mirror)
    }

    pub(super) fn current(&self) -> Result {
        if CurrentMm::get()?.0 != self.mm.0 {
            return Err(errno(-18));
        }
        Ok(())
    }

    pub(super) fn unmap(&self) -> Result {
        self.current()?;
        // SAFETY: Rollback is restricted to the originating caller's reserved
        // address range. Linux serializes munmap against concurrent MM edits.
        kernel::error::to_result(unsafe {
            bindings::vm_munmap(self.start, (self.end - self.start) as usize)
        })
        .map(|_| ())
    }

    pub(super) fn clear(&self, start: u64, end: u64) -> Result {
        if start >= end
            || start < self.start
            || end > self.end
            || start % 4096 != 0
            || end % 4096 != 0
        {
            return Err(EINVAL);
        }
        let mm = CurrentMm::get()?;
        if mm.0 != self.mm.0 {
            return Err(errno(-18));
        }
        // SAFETY: The transient MM reference and write lock cover both passes.
        // Preflight all VMAs before modifying PTEs, and touch only this file's
        // exact mirror identity. The shared anon inode is never invalidated.
        unsafe {
            let sem = ptr::addr_of_mut!((*mm.0.as_ptr()).__bindgen_anon_1.mmap_lock);
            bindings::down_write(sem);
            let result = (|| -> Result {
                for apply in [false, true] {
                    let mut address = start;
                    while address < end {
                        let vma = bindings::find_vma(mm.0.as_ptr(), address);
                        if vma.is_null()
                            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start > address
                            || (*vma).vm_ops != &VM_OPERATIONS.0
                            || (*vma).vm_file.is_null()
                        {
                            return Err(EINVAL);
                        }
                        let private = &*(*(*vma).vm_file).private_data.cast::<MappingFile>();
                        if !ptr::eq(&*private.mirror, self) {
                            return Err(EACCES);
                        }
                        let last = end.min((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end);
                        if apply {
                            bindings::zap_vma_ptes(vma, address, last - address);
                        }
                        address = last;
                    }
                }
                Ok(())
            })();
            bindings::up_write(sem);
            result
        }
    }
}

// SAFETY: Linux retains file/module and holds mmap's write lock. The only
// creator of this file supplied the complete MappingFile object above.
unsafe extern "C" fn mmap(file: *mut bindings::file, vma: *mut bindings::vm_area_struct) -> i32 {
    let private = unsafe { &*(*file).private_data.cast::<MappingFile>() };
    let mirror = &private.mirror;
    // SAFETY: Linux lends the live VMA exclusively to this mmap callback.
    unsafe {
        if (*vma).vm_mm != mirror.mm.0.as_ptr()
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start != mirror.start
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end != mirror.end
            || (*vma).vm_pgoff != 0
        {
            return EINVAL.to_errno();
        }
        (*vma).__bindgen_anon_2.__vm_flags |=
            (bindings::VM_PFNMAP | bindings::VM_DONTEXPAND | bindings::VM_DONTDUMP) as u64;
        (*vma).vm_ops = &VM_OPERATIONS.0;
    }
    0
}

// SAFETY: The locked live VMA retains its file, module, mirror and application.
unsafe extern "C" fn fault(vmf: *mut bindings::vm_fault) -> bindings::vm_fault_t {
    let result = (|| -> Result<bindings::vm_fault_t> {
        // SAFETY: Linux supplies the live fault structure and retained VMA.
        let (vma, address, flags) = unsafe {
            (
                (*vmf).__bindgen_anon_1.vma,
                (*vmf).__bindgen_anon_1.address,
                (*vmf).flags,
            )
        };
        let private = unsafe { &*(*(*vma).vm_file).private_data.cast::<MappingFile>() };
        let mirror = &private.mirror;
        if unsafe { (*vma).vm_mm } != mirror.mm.0.as_ptr()
            || address < mirror.start
            || address >= mirror.end
        {
            return Err(EACCES);
        }
        let mut request = [0; 32];
        wire::put_word(&mut request, 0, address).map_err(errno)?;
        // FAULT_FLAG_WRITE=bit 0 and FAULT_FLAG_INSTRUCTION=bit 8 in Linux.
        let access = u64::from(flags & 1 != 0) | u64::from(flags & 256 != 0) << 1;
        wire::put_word(&mut request, 8, access).map_err(errno)?;
        private
            .registration
            .invoke(super::application_abi::LOOKUP, &mut request)?;
        let physical = wire::word(&request, 16).map_err(errno)?;
        let permissions = wire::word(&request, 24).map_err(errno)?;
        // SAFETY: The kernel connection validated this process's live guest
        // page. Linux installs only a 4-KiB PFN and preserves VMA protections,
        // further restricted by the guest's effective page-table permissions.
        unsafe {
            let mut protection = (*vma).vm_page_prot;
            if permissions & 1 == 0 {
                protection.pgprot &= !2;
            }
            if permissions & 2 == 0 {
                protection.pgprot |= 1 << 63;
            }
            Ok(bindings::vmf_insert_pfn_prot(
                vma,
                address & !4095,
                physical >> 12,
                protection,
            ))
        }
    })();
    result.unwrap_or(bindings::vm_fault_reason_VM_FAULT_SIGBUS)
}

// SAFETY: Preserve guest PTE permissions until the full synchronized mprotect
// and relocation adapters exist. These unsupported operations change no VMA.
unsafe extern "C" fn mprotect(_: *mut bindings::vm_area_struct, _: u64, _: u64, _: u64) -> i32 {
    errno(-95).to_errno()
}
unsafe extern "C" fn mremap(_: *mut bindings::vm_area_struct) -> i32 {
    errno(-95).to_errno()
}

// SAFETY: Linux calls final release once, after all VMA/file borrows finish.
unsafe extern "C" fn release(_: *mut bindings::inode, file: *mut bindings::file) -> i32 {
    let private = unsafe { (*file).private_data.cast::<MappingFile>() };
    unsafe {
        (*file).private_data = ptr::null_mut();
        drop(Box::from_raw(private));
    }
    0
}

struct FileOperations(bindings::file_operations);
struct VmOperations(bindings::vm_operations_struct);
// SAFETY: Immutable tables contain module-resident callbacks and module identity.
unsafe impl Sync for FileOperations {}
unsafe impl Sync for VmOperations {}
static FILE_OPERATIONS: FileOperations = FileOperations({
    // SAFETY: Null pointers/optional callbacks and zero flags are valid defaults.
    let mut operations: bindings::file_operations = unsafe { MaybeUninit::zeroed().assume_init() };
    operations.owner = super::THIS_MODULE.as_ptr();
    operations.mmap = Some(mmap);
    operations.release = Some(release);
    operations
});
static VM_OPERATIONS: VmOperations = VmOperations({
    // SAFETY: Null optional callbacks are valid; all supplied code is retained.
    let mut operations: bindings::vm_operations_struct =
        unsafe { MaybeUninit::zeroed().assume_init() };
    operations.fault = Some(fault);
    operations.pfn_mkwrite = Some(fault);
    operations.mprotect = Some(mprotect);
    operations.mremap = Some(mremap);
    operations
});

const _: () = {
    assert!(size_of::<bindings::atomic_t>() == size_of::<AtomicI32>());
    assert!(align_of::<bindings::atomic_t>() == align_of::<AtomicI32>());
};
