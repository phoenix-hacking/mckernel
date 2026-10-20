// SPDX-License-Identifier: GPL-2.0
//! Linux mirror VMAs retain the exact application connection and MM identity.

use super::{application_image as wire, mcctrl_process::Registration};
use core::{
    ffi::{c_char, c_void},
    mem::{align_of, size_of, MaybeUninit,ManuallyDrop},
    pin::Pin,
    ptr::{self, NonNull},
    sync::atomic::{AtomicBool,AtomicI32,AtomicPtr,Ordering},
};
use kernel::{bindings, prelude::*, sync::{new_mutex,Arc,ArcBorrow,Mutex}};

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
    admission:AtomicBool,foreign_alias_seen:AtomicBool,
}
// Each VMA owns a raw Arc. The file transfers its bootstrap once, so a
// shared inherited file does not permanently retain a parent's application.
// The one shared VmaOwner can be referenced by any number of copied VMAs.
// Only its final Drop queues ONE separately preallocated node. The close
// callback therefore cannot call Registration cleanup, MM release or a service.
struct DeferredVmaOwner {
    registration:Arc<Registration>,mirror:Arc<Mirror>,next:AtomicPtr<DeferredVmaOwner>,
    // Last field: all application/MM reference destructors retain this module.
    _module:DeferredModule,
}
pub(super) struct DeferredModule(*mut c_void);
unsafe impl Send for DeferredModule {}
unsafe impl Sync for DeferredModule {}
extern "C" {
    fn try_module_get(module:*mut c_void)->bool;
    fn module_put(module:*mut c_void);
}
impl DeferredModule {
    pub(super) fn acquire()->Result<Self> {
        let module:*mut c_void=super::THIS_MODULE.as_ptr().cast();
        if !unsafe {try_module_get(module)} {return Err(ENODEV);}
        Ok(Self(module))
    }
}
impl Drop for DeferredModule {fn drop(&mut self){unsafe {module_put(self.0)};}}
static DEFERRED_VMA_OWNERS:AtomicPtr<DeferredVmaOwner>=AtomicPtr::new(ptr::null_mut());
struct VmaOwner {deferred:ManuallyDrop<Box<DeferredVmaOwner>>}
impl core::ops::Deref for VmaOwner {
    type Target=DeferredVmaOwner;
    fn deref(&self)->&DeferredVmaOwner {&self.deferred}
}
impl VmaOwner {
    fn new(registration:Arc<Registration>,mirror:Arc<Mirror>)->Result<Arc<Self>> {
        // Every fallible allocation/module acquisition precedes mmap/VMA seal.
        let module=DeferredModule::acquire()?;
        let node=Box::new(DeferredVmaOwner{registration,mirror,
            next:AtomicPtr::new(ptr::null_mut()),_module:module},GFP_KERNEL)?;
        Ok(Arc::new(Self{deferred:ManuallyDrop::new(node)},GFP_KERNEL)?)
    }
}
impl Drop for VmaOwner {
    fn drop(&mut self) {
        let node=Box::into_raw(unsafe {ManuallyDrop::take(&mut self.deferred)});
        let mut observed=DEFERRED_VMA_OWNERS.load(Ordering::Acquire);
        loop {
            // This unique node has never been queued before. Published nodes
            // are immutable until the existing reaper's acquire detach.
            unsafe {(*node).next.store(observed,Ordering::Relaxed)};
            match DEFERRED_VMA_OWNERS.compare_exchange_weak(observed,node,Ordering::Release,Ordering::Acquire) {
                Ok(_)=>break,Err(next)=>observed=next,
            }
        }
        // No allocation, blocking lock, owner Drop or service invocation here.
    }
}
/// Existing mcctrl reaper ONLY, with no table/publication/MM locks held.
/// Queue drain means deferred reference release; it never means a guest ACK.
/// Registration/Runtime's existing retirement/quarantine owners remain binding.
pub(super) fn drain_deferred_vma_owners() {
    let mut node=DEFERRED_VMA_OWNERS.swap(ptr::null_mut(),Ordering::AcqRel);
    while !node.is_null() {
        let owner=unsafe {Box::from_raw(node)};
        node=owner.next.load(Ordering::Relaxed);
        // Final Registration::Drop, possible cleanup and mm_count Drop now
        // occur solely in the existing sleepable reaper context, outside MM.
        drop(owner);
    }
}

struct MappingFile { bootstrap:Pin<Box<Mutex<Option<Arc<VmaOwner>>>>> }

unsafe fn vma_owner<'a>(vma:*mut bindings::vm_area_struct)->Result<ArcBorrow<'a,VmaOwner>> {
    if vma.is_null() || unsafe {(*vma).vm_ops}!=&VM_OPERATIONS.0 {return Err(EACCES);}
    let raw=unsafe {(*vma).vm_private_data.cast::<VmaOwner>()};
    if raw.is_null(){return Err(EACCES);}
    // Caller keeps the live VMA and its ownership stable through this borrow.
    Ok(unsafe {ArcBorrow::from_raw(raw)})
}
unsafe extern "C" fn vma_open(vma:*mut bindings::vm_area_struct) {
    // Linux copied a live original VMA. Its raw reference remains borrowed,
    // and this new VMA takes an independent increment for split/fork lifetime.
    if let Ok(owner)=unsafe {vma_owner(vma)} {
        if unsafe {(*vma).vm_mm}!=owner.mirror.mm.0.as_ptr(){
            owner.mirror.foreign_alias_seen.store(true,Ordering::Release);
        }
        let owned:Arc<VmaOwner>=owner.into();
        unsafe {(*vma).vm_private_data=Arc::into_raw(owned).cast_mut().cast()};
    }
}
unsafe extern "C" fn vma_close(vma:*mut bindings::vm_area_struct) {
    let raw=unsafe {(*vma).vm_private_data.cast::<VmaOwner>()};
    unsafe {(*vma).vm_private_data=ptr::null_mut()};
    if !raw.is_null(){unsafe {drop(Arc::from_raw(raw))};}
}
// EXISTING permitted Linux control-plane wrapper providers, never compute-C.
extern "C" {
    fn mckernel_inherited_mmap_write_lock(mm:*mut c_void);
    fn mckernel_inherited_mmap_write_unlock(mm:*mut c_void);
    fn mckernel_inherited_vma_start_write(vma:*mut c_void);
}
struct InheritedWrite<'a>(&'a CurrentMm);
impl Drop for InheritedWrite<'_> {
    fn drop(&mut self){unsafe {mckernel_inherited_mmap_write_unlock(self.0.0.as_ptr().cast())};}
}
struct VmaReplacement {vma:NonNull<bindings::vm_area_struct>,owner:Option<Arc<VmaOwner>>}

impl Mirror {
    /// Borrow actual inherited VMA provenance; geometry is only a filter.
    pub(super) fn inherited_registration(start:u64,end:u64)->Result<(Arc<Self>,Arc<Registration>)> {
        if start>=end || start%4096!=0 || end%4096!=0{return Err(EINVAL);}
        let mm=CurrentMm::get()?;
        let sem=unsafe {ptr::addr_of_mut!((*mm.0.as_ptr()).__bindgen_anon_1.mmap_lock)};
        unsafe {bindings::down_read(sem)};
        let result=(||->Result<(Arc<Self>,Arc<Registration>)> {
            let vma=unsafe {bindings::find_vma(mm.0.as_ptr(),start)};
            if vma.is_null() || unsafe {(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start}!=start{return Err(EACCES);}
            let owner=unsafe {vma_owner(vma)}?;
            if owner.mirror.mm.0==mm.0 || owner.mirror.start!=start || owner.mirror.end!=end{return Err(EACCES);}
            Ok((owner.mirror.clone(),owner.registration.clone()))
        })();
        unsafe {bindings::up_read(sem)};
        result
    }

    /// # Safety
    /// Caller owns an actual authenticated original-delivery/backend/root/
    /// child-task/MM scope, preallocated durable retention and publication
    /// reservations. The seal is infallible, nonblocking and allocation-free.
    /// NO provider/publication lock may span this function: CurrentMm drops
    /// after write unlock, before any local Registration publication lock.
    pub(super) unsafe fn inherit_vmas(parent:&Arc<Self>,parent_registration:&Arc<Registration>,
        child_registration:Arc<Registration>,start:u64,end:u64,expected_mm:u64,
        seal:impl FnOnce(&Arc<Self>))->Result<Arc<Self>> {
        if start!=parent.start || end!=parent.end || start>=end || start%4096!=0 || end%4096!=0{return Err(EINVAL);}
        child_registration.validate_current_fork_child(parent_registration)?;
        let mm=CurrentMm::get()?;
        if mm.0==parent.mm.0||mm.0.as_ptr() as u64!=expected_mm{return Err(EACCES);}
        let child=Arc::new(Self{mm:MmIdentity::from_current(&mm)?,start,end,
            admission:AtomicBool::new(true),foreign_alias_seen:AtomicBool::new(false)},GFP_KERNEL)?;
        let replacement=VmaOwner::new(child_registration,child.clone())?;
        unsafe {mckernel_inherited_mmap_write_lock(mm.0.as_ptr().cast())};
        let write=InheritedWrite(&mm);
        let result=(||->Result {
            let mut address=start;let mut count=0usize;let mut file=ptr::null_mut();let mut flags=None;
            while address<end {
                let vma=unsafe {bindings::find_vma(mm.0.as_ptr(),address)};
                if vma.is_null(){return Err(EACCES);}
                let (first,last,current_flags)=unsafe {((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                    (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end,(*vma).__bindgen_anon_2.__vm_flags)};
                let required=(bindings::VM_PFNMAP|bindings::VM_DONTEXPAND|bindings::VM_DONTDUMP) as u64;
                if first!=address || last<=first || last>end || last%4096!=0
                    || unsafe {(*vma).vm_mm}!=mm.0.as_ptr() || unsafe {(*vma).vm_file.is_null()}
                    || unsafe {(*vma).vm_pgoff}!=(first-start)/4096 || current_flags&required!=required{return Err(EACCES);}
                if count==0{file=unsafe {(*vma).vm_file};flags=Some(current_flags);}
                if unsafe {(*vma).vm_file}!=file || flags!=Some(current_flags){return Err(EACCES);}
                let inherited=unsafe {vma_owner(vma)}?;
                if !ptr::eq(&*inherited.registration,&**parent_registration)
                    || !ptr::eq(&*inherited.mirror,&**parent){return Err(EACCES);}
                count=count.checked_add(1).ok_or_else(||errno(-75))?;address=last;
            }
            // All allocations and reference acquisitions finish before any
            // per-VMA write, PFN zap, owner swap or authenticated seal effect.
            let mut plan=Vec::with_capacity(count,GFP_KERNEL)?;address=start;
            while address<end {
                let vma=NonNull::new(unsafe {bindings::find_vma(mm.0.as_ptr(),address)}).ok_or(EACCES)?;
                plan.push(VmaReplacement{vma,owner:Some(replacement.clone())},GFP_KERNEL)?;
                address=unsafe {(*vma.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.vm_end};
            }
            for item in plan.iter(){unsafe {mckernel_inherited_vma_start_write(item.vma.as_ptr().cast())};}
            for item in plan.iter(){let vma=item.vma.as_ptr();let(first,last)=unsafe {
                ((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end)};
                unsafe {bindings::zap_vma_ptes(vma,first,last-first)};
            }
            for item in plan.iter_mut(){let vma=item.vma.as_ptr();let old=unsafe {(*vma).vm_private_data.cast::<VmaOwner>()};
                unsafe {(*vma).vm_private_data=Arc::into_raw(item.owner.take().unwrap()).cast_mut().cast()};
                // Parent Registration/Mirror arguments retain both fields, so
                // this balance cannot invoke their final destructors under MM.
                unsafe {drop(Arc::from_raw(old))};
            }
            seal(&child);Ok(())
        })();
        drop(write);drop(mm);result?;Ok(child)
    }

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
                admission:AtomicBool::new(true),foreign_alias_seen:AtomicBool::new(false),
            },
            GFP_KERNEL,
        )?;
        let initial=VmaOwner::new(registration,mirror.clone())?;
        let private=Box::new(MappingFile{bootstrap:Box::pin_init(new_mutex!(Some(initial)),GFP_KERNEL)?},GFP_KERNEL)?;
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

    pub(super) fn revoke_fork_aliases(self:&Arc<Self>,claim:&super::application_abi::ForkRevokeClaimV1)->Result {
        let identity=claim.identity;
        if identity.child_mm!=self.mm.0.as_ptr() as u64||identity.start!=self.start
            ||identity.start.checked_add(identity.length)!=Some(self.end)||identity.generation==0
            ||identity.root==0||identity.root%4096!=0||identity.parent==0||identity.child==0
            ||identity.parent==identity.child||identity.worker==0||identity.delivery==0
            ||identity.nonce==0||identity.child_pid<=0||claim.carrier==0||claim.carrier%8!=0{return Err(EACCES);}
        // Monotonic closure. No PID disappearance or scalar return proves MM
        // retirement. The structural pin only permits this guarded mmget.
        self.admission.store(false,Ordering::Release);
        let users=unsafe {AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.0.as_ptr()).__bindgen_anon_1.mm_users.counter))};
        users.fetch_update(Ordering::Acquire,Ordering::Relaxed,|n|
            if n>0{n.checked_add(1)}else{None}).map_err(|_|EBUSY)?;
        let mm=CurrentMm(self.mm.0);
        unsafe {mckernel_inherited_mmap_write_lock(mm.0.as_ptr().cast())};
        let guard=InheritedWrite(&mm);
        let result=(||->Result {
            if self.foreign_alias_seen.load(Ordering::Acquire){return Err(EBUSY);}
            // Include split/moved aliases throughout this MM. Preflight all,
            // exclude per-VMA readers, then zap (including Linux TLB finish).
            for pass in 0..3 {
                let mut address=0;
                loop {
                    let vma=unsafe {bindings::find_vma(mm.0.as_ptr(),address)};
                    if vma.is_null(){break;}
                    let(first,last)=unsafe {((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                        (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end)};
                    if first<address||last<=first||last%4096!=0
                        ||unsafe {(*vma).vm_mm}!=mm.0.as_ptr(){return Err(EBUSY);}
                    if unsafe {(*vma).vm_ops}==&VM_OPERATIONS.0 {
                        let owner=unsafe {vma_owner(vma)}.map_err(|_|EBUSY)?;
                        if ptr::eq(&*owner.mirror,&**self) {
                            if first%4096!=0||unsafe {(*vma).vm_file.is_null()}
                                ||unsafe {(*vma).__bindgen_anon_2.__vm_flags}&bindings::VM_PFNMAP as u64==0{return Err(EBUSY);}
                            if pass==1{unsafe {mckernel_inherited_vma_start_write(vma.cast())};}
                            if pass==2{unsafe {bindings::zap_vma_ptes(vma,first,last-first)};}
                        }
                    }
                    address=last;
                }
            }
            Ok(())
        })();
        drop(guard);drop(mm);result
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
                        let private = vma_owner(vma)?;
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
unsafe extern "C" fn mmap(file:*mut bindings::file,vma:*mut bindings::vm_area_struct)->i32 {
    let private=unsafe {&*(*file).private_data.cast::<MappingFile>()};
    let mut bootstrap=private.bootstrap.lock();
    let Some(owner)=bootstrap.as_ref()else{return EINVAL.to_errno();};let mirror=&owner.mirror;
    unsafe {
        if (*vma).vm_mm!=mirror.mm.0.as_ptr()
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start!=mirror.start
            || (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end!=mirror.end
            || (*vma).vm_pgoff!=0 || !(*vma).vm_private_data.is_null(){return EINVAL.to_errno();}
        (*vma).__bindgen_anon_2.__vm_flags|=(bindings::VM_PFNMAP|bindings::VM_DONTEXPAND|bindings::VM_DONTDUMP) as u64;
        (*vma).vm_ops=&VM_OPERATIONS.0;
        (*vma).vm_private_data=Arc::into_raw(bootstrap.take().unwrap()).cast_mut().cast();
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
    // SAFETY: lookup_fault's caller retains the locked live VMA and file;
    // mmap installed a non-null MappingFile private_data of this exact type.
    let private=unsafe {vma_owner(vma)}?;
    let mirror = &private.mirror;
    // SAFETY: The same locked live VMA remains valid while its MM identity is
    // compared against the MappingFile owner before any request is issued.
    if !mirror.admission.load(Ordering::Acquire)||unsafe { (*vma).vm_mm } != mirror.mm.0.as_ptr()
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
    private
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
    operations.open=Some(vma_open);
    operations.close=Some(vma_close);
    operations.fault = Some(fault);
    operations.pfn_mkwrite = Some(pfn_mkwrite);
    operations.mprotect = Some(mprotect);
    operations.mremap = Some(mremap);
    operations
});

const _: () = {
    assert!(size_of::<bindings::atomic_t>() == size_of::<AtomicI32>());
    assert!(align_of::<bindings::atomic_t>() == align_of::<AtomicI32>());
};
