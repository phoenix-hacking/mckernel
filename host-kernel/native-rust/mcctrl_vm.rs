// SPDX-License-Identifier: GPL-2.0
//! Linux mirror VMAs retain the exact application connection and MM identity.

use super::{application_image as wire, mcctrl_process::Registration};
use core::{
    ffi::{c_char, c_void},
    mem::{align_of, size_of, MaybeUninit},
    pin::Pin,
    ptr::{self, NonNull},
    sync::atomic::{AtomicI32, Ordering},
};
use kernel::{bindings, prelude::*, sync::{new_mutex, Arc, ArcBorrow, Mutex}};

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
// SAFETY: Shared MmIdentity use exposes only immutable identity while its owned
// structural reference keeps the opaque mm alive until the single Drop balance.
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
// BEGIN FORK VMA OWNERS
// Each installed VMA owns one raw Arc. A file is neutral after its initial
// mmap: inheriting vm_file must not retain the parent's application forever.
struct VmaOwner {
    registration: Arc<Registration>,
    mirror: Arc<Mirror>,
}
struct MappingFile {
    bootstrap: Pin<Box<Mutex<Option<Arc<VmaOwner>>>>>,
}

// SAFETY: The caller holds Linux's live VMA exclusion and keeps its owned raw
// Arc valid for the entire returned borrow. Owner changes require both mmap
// write exclusion and the pinned Linux per-VMA write discipline.
unsafe fn vma_owner<'a>(vma: *mut bindings::vm_area_struct) -> Result<ArcBorrow<'a, VmaOwner>> {
    let raw = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
    if raw.is_null() || unsafe { (*vma).vm_ops } != &VM_OPERATIONS.0 {
        return Err(EACCES);
    }
    // SAFETY: mmap and open install exactly one owned raw reference, and the
    // caller excludes close/rebind throughout this borrow.
    Ok(unsafe { ArcBorrow::from_raw(raw) })
}

// SAFETY: Linux calls open on a copied VMA while the original owner is live.
// This includes both a same-MM split and a different-MM fork. Clone is an
// allocation-free reference increment; the inherited MM mismatch stays intact.
unsafe extern "C" fn vma_open(vma: *mut bindings::vm_area_struct) {
    if let Ok(owner) = unsafe { vma_owner(vma) } {
        let reference: Arc<VmaOwner> = owner.into();
        unsafe { (*vma).vm_private_data = Arc::into_raw(reference).cast_mut().cast() };
    }
}

// SAFETY: Linux invokes close once for each successfully opened/mapped VMA,
// after its fault borrows end. Returning this raw owner balances exactly that
// VMA's reference; the file no longer contains an application owner.
unsafe extern "C" fn vma_close(vma: *mut bindings::vm_area_struct) {
    let raw = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
    unsafe { (*vma).vm_private_data = ptr::null_mut() };
    if !raw.is_null() {
        unsafe { drop(Arc::from_raw(raw)) };
    }
}
// END FORK VMA OWNERS

// BEGIN INHERITED VMA TRANSACTION
// Native thunks are supplied by 0011-mm-export-inherited-vma-write-primitives.
// They use Linux mmap_write_lock/unlock (including vma_end_write_all) and
// vma_start_write, not manually replicated semaphore/sequence operations.
extern "C" {
    fn mckernel_inherited_mmap_write_lock(mm: *mut bindings::mm_struct);
    fn mckernel_inherited_mmap_write_unlock(mm: *mut bindings::mm_struct);
    fn mckernel_inherited_vma_start_write(vma: *mut bindings::vm_area_struct);
}

struct InheritedMmWrite<'a> {
    mm: &'a CurrentMm,
}
impl Drop for InheritedMmWrite<'_> {
    fn drop(&mut self) {
        // SAFETY: The transaction acquired this exact live MM's write lock.
        unsafe { mckernel_inherited_mmap_write_unlock(self.mm.0.as_ptr()) };
    }
}

struct InheritedVmaReplacement {
    vma: NonNull<bindings::vm_area_struct>,
    owner: Option<Arc<VmaOwner>>,
}

#[allow(dead_code)]
impl Mirror {
    /// Replace only the current child MM's complete inherited mirror extent.
    ///
    /// # Safety
    /// The parent proof must come from retained backend/VMA
    /// provenance. `seal` must commit that already-reserved backend transaction
    /// infallibly under this exclusion, without allocation, sleepable external
    /// calls, user copies, or publication beforehand. No runtime caller is
    /// permitted until native ABI and revoke/final-ACK proofs are verified.
    pub(super) unsafe fn inherit_vmas(
        parent: &Arc<Self>, parent_registration: &Arc<Registration>,
        child_registration: Arc<Registration>, start: u64, end: u64,
        seal: impl FnOnce(&Arc<Self>),
    ) -> Result<Arc<Self>> {
        if start != parent.start || end != parent.end || start >= end
            || start % 4096 != 0 || end % 4096 != 0
        { return Err(EINVAL); }
        if ptr::eq(&**parent_registration, &*child_registration)
            || !parent_registration.same_generation(&child_registration)
        { return Err(EACCES); }
        let mm = CurrentMm::get()?;
        if mm.0 == parent.mm.0 { return Err(EACCES); }
        let child = Arc::new(Self { mm: MmIdentity::from_current(&mm)?, start, end }, GFP_KERNEL)?;
        let owner = Arc::new(VmaOwner { registration: child_registration, mirror: child.clone() }, GFP_KERNEL)?;
        // SAFETY: The referenced live child MM remains retained through unlock.
        unsafe { mckernel_inherited_mmap_write_lock(mm.0.as_ptr()) };
        let guard = InheritedMmWrite { mm: &mm };
        let result = (|| -> Result {
            let mut address = start;
            let mut count = 0usize;
            let mut file = ptr::null_mut();
            let mut flags = None;
            // Preflight the entire extent before allocation-dependent journal
            // publication, any per-VMA write transition, PFN zap or owner swap.
            while address < end {
                let vma = unsafe { bindings::find_vma(mm.0.as_ptr(), address) };
                if vma.is_null() { return Err(EINVAL); }
                let (first, last, current_flags) = unsafe {
                    ((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                     (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end,
                     (*vma).__bindgen_anon_2.__vm_flags)
                };
                let required = (bindings::VM_PFNMAP | bindings::VM_DONTEXPAND | bindings::VM_DONTDUMP) as u64;
                if first != address || last <= first || last > end || last % 4096 != 0
                    || unsafe { (*vma).vm_mm } != mm.0.as_ptr()
                    || unsafe { (*vma).vm_file.is_null() }
                    || unsafe { (*vma).vm_pgoff } != (first - start) / 4096
                    || current_flags & required != required
                { return Err(EINVAL); }
                if count == 0 { file = unsafe { (*vma).vm_file }; flags = Some(current_flags); }
                if unsafe { (*vma).vm_file } != file || flags != Some(current_flags) { return Err(EACCES); }
                let inherited = unsafe { vma_owner(vma) }?;
                if !ptr::eq(&*inherited.registration, &**parent_registration)
                    || !ptr::eq(&*inherited.mirror, &**parent)
                { return Err(EACCES); }
                count = count.checked_add(1).ok_or(EOVERFLOW)?;
                address = last;
            }
            let mut replacements = Vec::with_capacity(count, GFP_KERNEL)?;
            let mut address = start;
            while address < end {
                // Same MM write exclusion preserves the validated VMA set.
                let vma = NonNull::new(unsafe { bindings::find_vma(mm.0.as_ptr(), address) }).ok_or(EINVAL)?;
                replacements.push(InheritedVmaReplacement { vma, owner: Some(owner.clone()) }, GFP_KERNEL)?;
                address = unsafe { (*vma.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.vm_end };
            }
            // All fallible work is complete. Exclude every VMA reader before
            // clearing all inherited aliases; only then publish child owners.
            for replacement in replacements.iter() {
                unsafe { mckernel_inherited_vma_start_write(replacement.vma.as_ptr()) };
            }
            for replacement in replacements.iter() {
                let vma = replacement.vma.as_ptr();
                let first = unsafe { (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start };
                let last = unsafe { (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end };
                unsafe { bindings::zap_vma_ptes(vma, first, last - first) };
            }
            for replacement in replacements.iter_mut() {
                let vma = replacement.vma.as_ptr();
                let old = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
                unsafe { (*vma).vm_private_data = Arc::into_raw(replacement.owner.take().unwrap()).cast_mut().cast() };
                // Parent Arcs above retain Registration/Mirror while this raw
                // per-VMA owner is balanced; their final release cannot run.
                unsafe { drop(Arc::from_raw(old)) };
            }
            seal(&child);
            Ok(())
        })();
        drop(guard); // Real mmap_write_unlock ends the per-VMA write epoch.
        result?;
        Ok(child)
    }
}
// END INHERITED VMA TRANSACTION

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
        let owner = Arc::new(VmaOwner { registration, mirror: mirror.clone() }, GFP_KERNEL)?;
        let private = Box::new(
            MappingFile { bootstrap: Box::pin_init(new_mutex!(Some(owner)), GFP_KERNEL)? },
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
            // SAFETY: prepare_creds returned this unpublished current-task copy;
            // override/revert and abort are paired before it can escape this call.
            let address = unsafe {
                (*promoted).cap_effective.val |= 1 << 17; // CAP_SYS_RAWIO
                let original = bindings::override_creds(promoted);
                // MAP_FIXED_NOREPLACE | MAP_SHARED, PROT_READ|WRITE. Linux
                // anon_inodefs is noexec; this mirror serves host data access.
                // The guest's own page tables retain application execution.
                // A mapping raced into the snapshot gap fails with EEXIST.
                let address = bindings::vm_mmap(file, 0, end, 3, 0x100001, 0);
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
                        let owner = vma_owner(vma)?;
                        if !ptr::eq(&*owner.mirror, self) {
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
    let mut bootstrap = private.bootstrap.lock();
    let Some(owner) = bootstrap.as_ref() else {
        return EINVAL.to_errno();
    };
    let mirror = &owner.mirror;
    // SAFETY: Linux lends the live VMA exclusively to this mmap callback.
    unsafe {
        if (*vma).vm_mm != mirror.mm.0.as_ptr()
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start != mirror.start
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end != mirror.end
            || (*vma).vm_pgoff != 0
            || !(*vma).vm_private_data.is_null()
        {
            return EINVAL.to_errno();
        }
        (*vma).__bindgen_anon_2.__vm_flags |=
            (bindings::VM_PFNMAP | bindings::VM_DONTEXPAND | bindings::VM_DONTDUMP) as u64;
        (*vma).vm_ops = &VM_OPERATIONS.0;
        // All checks finished; this callback cannot fail after the transfer.
        // Linux invokes close for the installed VMA, including later teardown.
        (*vma).vm_private_data = Arc::into_raw(bootstrap.take().unwrap()).cast_mut().cast();
    }
    0
}

struct FaultPage {
    vma: *mut bindings::vm_area_struct,
    address: u64,
    physical: u64,
    permissions: u64,
}

// SAFETY: The caller keeps Linux's locked live VMA and its retained file,
// module, mirror and application valid through use of the returned page.
unsafe fn lookup_fault(vmf: *mut bindings::vm_fault, write: bool) -> Result<FaultPage> {
    // SAFETY: Linux supplies the live fault structure and retained VMA.
    let (vma, address, flags) = unsafe {
        (
            (*vmf).__bindgen_anon_1.vma,
            (*vmf).__bindgen_anon_1.address,
            (*vmf).flags,
        )
    };
    // SAFETY: The fault's VMA exclusion retains its exact per-VMA raw owner.
    let owner = unsafe { vma_owner(vma) }?;
    let mirror = &owner.mirror;
    // SAFETY: The same locked live VMA remains valid while its MM identity is
    // compared against the per-VMA owner before any request is issued.
    if unsafe { (*vma).vm_mm } != mirror.mm.0.as_ptr()
        || address < mirror.start
        || address >= mirror.end
    {
        return Err(EACCES);
    }
    let mut request = [0; 32];
    wire::put_word(&mut request, 0, address).map_err(errno)?;
    // FAULT_FLAG_WRITE=bit 0 and FAULT_FLAG_INSTRUCTION=bit 8 in Linux.
    let access = u64::from(write || flags & 1 != 0) | u64::from(flags & 256 != 0) << 1;
    wire::put_word(&mut request, 8, access).map_err(errno)?;
    owner
        .registration
        .invoke(super::application_abi::LOOKUP, &mut request)?;
    Ok(FaultPage {
        vma,
        address,
        physical: wire::word(&request, 16).map_err(errno)?,
        permissions: wire::word(&request, 24).map_err(errno)?,
    })
}

// SAFETY: The locked live VMA retains its file, module, mirror and application.
unsafe extern "C" fn fault(vmf: *mut bindings::vm_fault) -> bindings::vm_fault_t {
    let result = (|| -> Result<bindings::vm_fault_t> {
        // SAFETY: Linux retains the VMA throughout this callback.
        let page = unsafe { lookup_fault(vmf, false) }?;
        // SAFETY: The kernel connection validated this process's live guest
        // page. Linux installs only a 4-KiB PFN and preserves VMA protections,
        // further restricted by the guest's effective page-table permissions.
        unsafe {
            let mut protection = (*page.vma).vm_page_prot;
            if page.permissions & 1 == 0 {
                protection.pgprot &= !2;
            }
            if page.permissions & 2 == 0 {
                protection.pgprot |= 1 << 63;
            }
            Ok(bindings::vmf_insert_pfn_prot(
                page.vma,
                page.address & !4095,
                page.physical >> 12,
                protection,
            ))
        }
    })();
    result.unwrap_or(bindings::vm_fault_reason_VM_FAULT_SIGBUS)
}

// SAFETY: Linux retains the VMA while its original PTE awaits a write upgrade.
unsafe extern "C" fn pfn_mkwrite(vmf: *mut bindings::vm_fault) -> bindings::vm_fault_t {
    // The prepared image remains owned by this VMA's application connection.
    // Recheck guest write permission; zero lets Linux lock and revalidate the
    // original PTE in finish_mkwrite_fault. Inserting a PFN here would return
    // VM_FAULT_NOPAGE and leave the PTE read-only, causing an endless refault.
    match unsafe { lookup_fault(vmf, true) } {
        Ok(_) => 0,
        Err(_) => bindings::vm_fault_reason_VM_FAULT_SIGBUS,
    }
}

// SAFETY: Preserve guest PTE permissions until the full synchronized mprotect
// and relocation adapters exist. These unsupported operations change no VMA.
unsafe extern "C" fn mprotect(_: *mut bindings::vm_area_struct, _: u64, _: u64, _: u64) -> i32 {
    errno(-95).to_errno()
}
// SAFETY: Linux invokes this module-resident callback with a live VMA, but this
// unsupported operation reads neither pointer nor VMA state and changes nothing.
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
// SAFETY: The initialized VM table is immutable and contains only module-retained
// callbacks, so concurrent readers cannot mutate or outlive its contents.
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
    operations.open = Some(vma_open);
    operations.close = Some(vma_close);
    operations.pfn_mkwrite = Some(pfn_mkwrite);
    operations.mprotect = Some(mprotect);
    operations.mremap = Some(mremap);
    operations
});

const _: () = {
    assert!(size_of::<bindings::atomic_t>() == size_of::<AtomicI32>());
    assert!(align_of::<bindings::atomic_t>() == align_of::<AtomicI32>());
};
