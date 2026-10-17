// SPDX-License-Identifier: GPL-2.0
// Actual MM lifetime, VMA ownership, fault and transaction bodies. Linux locks,
// VMA tree, allocation and connection LOOKUP are explicit adapters, not ABI proof.
#![allow(dead_code, non_camel_case_types)]
mod fixture {
use std::{cell::{Cell, RefCell, RefMut}, ffi::c_void, pin::Pin, ptr::{self, NonNull}, sync::atomic::{AtomicI32, Ordering}};
type Result<T = ()> = std::result::Result<T, i32>;
const ESRCH: i32 = -3; const EINVAL: i32 = -22; const EACCES: i32 = -13;
const EOVERFLOW: i32 = -75; const GFP_KERNEL: u32 = 0;
fn errno(code: i32) -> i32 { code }
thread_local! { static ALLOCATION: Cell<(usize, usize)> = const { Cell::new((0,0)) }; }
fn allocate() -> Result { ALLOCATION.with(|a| { let (n, fail) = a.get(); a.set((n+1,fail)); if n+1 == fail { Err(-12) } else { Ok(()) } }) }
struct Arc<T>(std::sync::Arc<T>);
impl<T> Arc<T> {
    fn new(value: T, _: u32) -> Result<Self> { allocate()?; Ok(Self(std::sync::Arc::new(value))) }
    fn into_raw(this: Self) -> *const T { std::sync::Arc::into_raw(this.0) }
    unsafe fn from_raw(raw: *const T) -> Self { Self(unsafe { std::sync::Arc::from_raw(raw) }) }
    fn strong_count(this: &Self) -> usize { std::sync::Arc::strong_count(&this.0) }
}
impl<T> Clone for Arc<T> { fn clone(&self) -> Self { Self(self.0.clone()) } }
impl<T> std::ops::Deref for Arc<T> { type Target = T; fn deref(&self) -> &T { &self.0 } }
struct ArcBorrow<'a,T> { raw: *const T, lifetime: std::marker::PhantomData<&'a T> }
impl<'a,T> ArcBorrow<'a,T> { unsafe fn from_raw(raw: *const T) -> Self { Self { raw, lifetime: std::marker::PhantomData } } }
impl<T> std::ops::Deref for ArcBorrow<'_,T> { type Target=T; fn deref(&self)->&T { unsafe { &*self.raw } } }
impl<T> From<ArcBorrow<'_,T>> for Arc<T> {
    fn from(borrow:ArcBorrow<'_,T>)->Self { let value=std::mem::ManuallyDrop::new(unsafe { Arc::from_raw(borrow.raw) }); Arc::clone(&value) }
}
struct Vec<T>(std::vec::Vec<T>);
impl<T> Vec<T> {
    fn with_capacity(n: usize, _:u32)->Result<Self> { allocate()?; Ok(Self(std::vec::Vec::with_capacity(n))) }
    fn push(&mut self, value:T, _:u32)->Result { assert!(self.0.len()<self.0.capacity()); self.0.push(value); Ok(()) }
}
impl<T> std::ops::Deref for Vec<T> { type Target=std::vec::Vec<T>; fn deref(&self)->&Self::Target { &self.0 } }
impl<T> std::ops::DerefMut for Vec<T> { fn deref_mut(&mut self)->&mut Self::Target { &mut self.0 } }
struct Mutex<T>(RefCell<T>);
impl<T> Mutex<T> { fn lock(&self)->RefMut<'_,T> { self.0.borrow_mut() } }
mod bindings {
    use super::*;
    #[repr(C)] pub struct atomic_t { pub counter:i32 }
    #[repr(C)] pub struct mm_fields { pub mm_count:atomic_t }
    #[repr(C)] pub struct mm_union { pub __bindgen_anon_1:mm_fields }
    #[repr(C)] pub struct mm_struct { pub __bindgen_anon_1:mm_union, pub users:Cell<i32>, pub drops:Cell<usize> }
    pub struct file { pub private_data:*mut c_void }
    pub const VM_PFNMAP:u64=1024; pub const VM_DONTEXPAND:u64=2048; pub const VM_DONTDUMP:u64=4096;
    pub struct geometry { pub vm_start:u64, pub vm_end:u64 }
    pub struct fields { pub __bindgen_anon_1:geometry }
    pub struct flags { pub __vm_flags:u64 }
    pub struct vm_area_struct {
        pub vm_mm:*mut mm_struct, pub vm_file:*mut file, pub vm_private_data:*mut c_void,
        pub vm_ops:*const (), pub vm_pgoff:u64, pub __bindgen_anon_1:fields, pub __bindgen_anon_2:flags,
        pub old_owner:*mut c_void, pub writing:bool, pub cleared:bool,
    }
    pub struct fault_fields { pub vma:*mut vm_area_struct, pub address:u64 }
    pub struct vm_fault { pub __bindgen_anon_1:fault_fields, pub flags:u64 }
    pub unsafe fn get_current()->*mut () { ptr::null_mut() }
    pub unsafe fn get_task_mm(_: *mut ())->*mut mm_struct { MODEL.with(|m| { let mm=m.borrow().mm; unsafe { (*mm).users.set((*mm).users.get()+1) }; mm }) }
    pub unsafe fn mmput(mm:*mut mm_struct) { unsafe { (*mm).users.set((*mm).users.get()-1) }; }
    pub unsafe fn __mmdrop(mm:*mut mm_struct) { unsafe { (*mm).drops.set((*mm).drops.get()+1) }; }
    pub unsafe fn find_vma(mm:*mut mm_struct, address:u64)->*mut vm_area_struct {
        MODEL.with(|m| { let m=m.borrow(); assert!(m.locked); assert_eq!(mm,m.mm);
            m.vmas.iter().copied().find(|v| unsafe { (**v).__bindgen_anon_1.__bindgen_anon_1.vm_end>address }).unwrap_or(ptr::null_mut()) })
    }
    pub unsafe fn zap_vma_ptes(vma:*mut vm_area_struct, first:u64, length:u64) {
        MODEL.with(|m| { let mut m=m.borrow_mut(); assert!(m.locked);
            for pointer in &m.vmas { unsafe { assert!((**pointer).writing); assert_eq!((**pointer).vm_private_data,(**pointer).old_owner); } }
            unsafe { assert_eq!(first,(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start); assert_eq!(first+length,(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end); (*vma).cleared=true; }
            m.events.push("zap"); })
    }
}
struct Model { mm:*mut bindings::mm_struct, vmas:std::vec::Vec<*mut bindings::vm_area_struct>, locked:bool, valid:bool, events:std::vec::Vec<&'static str> }
thread_local! { static MODEL: RefCell<Model> = RefCell::new(Model { mm:ptr::null_mut(),vmas:vec![],locked:false,valid:true,events:vec![] }); }
#[no_mangle] unsafe extern "C" fn mckernel_inherited_mmap_write_lock(mm:*mut bindings::mm_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut(); m.valid=m.valid&&m.mm==mm&&!m.locked; m.locked=true; m.events.push("lock"); });
}
#[no_mangle] unsafe extern "C" fn mckernel_inherited_mmap_write_unlock(mm:*mut bindings::mm_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut(); m.valid=m.valid&&m.mm==mm&&m.locked; for v in &m.vmas { unsafe { (**v).writing=false; } } m.events.push("unlock"); m.locked=false; });
}
#[no_mangle] unsafe extern "C" fn mckernel_inherited_vma_start_write(vma:*mut bindings::vm_area_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut(); m.valid=m.valid&&m.locked&&unsafe{(*vma).vm_mm==m.mm}; unsafe { (*vma).writing=true; } m.events.push("write"); });
}
mod application_abi { pub const LOOKUP:u32=3; }
mod wire {
    pub fn put_word(b:&mut[u8],o:usize,v:u64)->Result<(),i32> { b[o..o+8].copy_from_slice(&v.to_le_bytes()); Ok(()) }
    pub fn word(b:&[u8],o:usize)->Result<u64,i32> { Ok(u64::from_le_bytes(b[o..o+8].try_into().unwrap())) }
}
struct Registration { slot:u32, generation:u64, physical:u64, calls:Cell<usize> }
impl Registration {
    @SAME_GENERATION@
    fn invoke(&self, command:u32, bytes:&mut[u8])->Result { assert_eq!(command,3); self.calls.set(self.calls.get()+1); wire::put_word(bytes,16,self.physical)?; wire::put_word(bytes,24,3) }
}
struct VmOperations(()); static VM_OPERATIONS:VmOperations=VmOperations(());
struct FaultPage { vma:*mut bindings::vm_area_struct,address:u64,physical:u64,permissions:u64 }
mod actual {
use super::*;
@MM_LIFETIME@
@MIRROR@
@OWNERS@
@TRANSACTION@
@FAULT@

struct Scenario {
    owner:Arc<VmaOwner>, parent:Arc<Mirror>, parent_registration:Arc<Registration>, child_registration:Arc<Registration>,
    parent_vma:Box<bindings::vm_area_struct>, children:std::vec::Vec<Box<bindings::vm_area_struct>>,
    file:Box<bindings::file>, parent_mm:Box<bindings::mm_struct>, child_mm:Box<bindings::mm_struct>,
}
fn mm()->Box<bindings::mm_struct> { Box::new(bindings::mm_struct { __bindgen_anon_1:bindings::mm_union {
    __bindgen_anon_1:bindings::mm_fields { mm_count:bindings::atomic_t { counter:1 } } },users:Cell::new(1),drops:Cell::new(0) }) }
fn count(mm:&bindings::mm_struct)->i32 { unsafe { AtomicI32::from_ptr(ptr::addr_of!(mm.__bindgen_anon_1.__bindgen_anon_1.mm_count.counter).cast_mut()) }.load(Ordering::SeqCst) }
fn vma(mm:*mut bindings::mm_struct,file:*mut bindings::file,first:u64,last:u64,owner:Arc<VmaOwner>)->Box<bindings::vm_area_struct> {
    let raw=Arc::into_raw(owner).cast_mut().cast();
    Box::new(bindings::vm_area_struct {vm_mm:mm,vm_file:file,vm_private_data:raw,old_owner:raw,vm_ops:&VM_OPERATIONS.0,vm_pgoff:first/4096,
        __bindgen_anon_1:bindings::fields {__bindgen_anon_1:bindings::geometry {vm_start:first,vm_end:last}},
        __bindgen_anon_2:bindings::flags {__vm_flags:1024|2048|4096},writing:false,cleared:false})
}
impl Scenario {
    fn new()->Self {
        ALLOCATION.with(|a|a.set((0,0)));
        let mut parent_mm=mm(); let mut child_mm=mm();
        MODEL.with(|m|m.borrow_mut().mm=&mut *parent_mm);
        let current=CurrentMm::get().unwrap();
        let parent=Arc::new(Mirror {mm:MmIdentity::from_current(&current).unwrap(),start:0,end:0x8000},0).unwrap(); drop(current);
        let parent_registration=Arc::new(Registration {slot:0,generation:2,physical:0x9000,calls:Cell::new(0)},0).unwrap();
        let child_registration=Arc::new(Registration {slot:0,generation:2,physical:0x19000,calls:Cell::new(0)},0).unwrap();
        let owner=Arc::new(VmaOwner {registration:parent_registration.clone(),mirror:parent.clone()},0).unwrap();
        let mut file=Box::new(bindings::file {private_data:ptr::null_mut()});
        let parent_vma=vma(&mut *parent_mm,&mut *file,0,0x8000,owner.clone());
        let children=vec![vma(&mut *child_mm,&mut *file,0,0x4000,owner.clone()),vma(&mut *child_mm,&mut *file,0x4000,0x8000,owner.clone())];
        let mut scenario=Self {owner,parent,parent_registration,child_registration,parent_vma,children,file,parent_mm,child_mm};
        scenario.install(); scenario
    }
    fn install(&mut self) { MODEL.with(|m|*m.borrow_mut()=Model {mm:&mut *self.child_mm,vmas:self.children.iter_mut().map(|v|&mut **v as *mut _).collect(),locked:false,valid:true,events:vec![]}); ALLOCATION.with(|a|a.set((0,0))); }
    fn unchanged(&self, refs:usize) {
        assert_eq!(Arc::strong_count(&self.owner),refs);
        assert_eq!(count(&self.child_mm),1); assert_eq!(self.child_mm.users.get(),1);
        for v in &self.children { assert_eq!(v.vm_private_data,v.old_owner); assert!(!v.cleared); }
        MODEL.with(|m| { let m=m.borrow(); assert!(m.valid); assert!(!m.locked); assert!(!m.events.contains(&"write")); assert!(!m.events.contains(&"zap")); });
    }
    fn run(&self)->Result<Arc<Mirror>> { unsafe { Mirror::inherit_vmas(&self.parent,&self.parent_registration,self.child_registration.clone(),0,0x8000,|_| panic!("seal must not run on validation failure")) } }
}
impl Drop for Scenario { fn drop(&mut self) { unsafe { vma_close(&mut *self.parent_vma); for v in &mut self.children { vma_close(&mut **v); } } } }

#[test]
fn inherited_transaction_rejects_geometry_generation_and_same_mm_without_mutation() {
    for variant in 0..5 {
        let mut s=Scenario::new(); let refs=Arc::strong_count(&s.owner);
        match variant {
            0=>{},
            1=>{s.child_registration=Arc::new(Registration {slot:0,generation:3,physical:0,calls:Cell::new(0)},0).unwrap();},
            2=>{s.child_registration=Arc::new(Registration {slot:1,generation:2,physical:0,calls:Cell::new(0)},0).unwrap();},
            3=>{s.child_registration=Arc::new(Registration {slot:0,generation:0,physical:0,calls:Cell::new(0)},0).unwrap();},
            _=>MODEL.with(|m|m.borrow_mut().mm=&mut *s.parent_mm),
        }
        let result=if variant==0 { unsafe {Mirror::inherit_vmas(&s.parent,&s.parent_registration,s.child_registration.clone(),0x1000,0x8000,|_|panic!("unexpected seal"))} } else {s.run()};
        assert!(result.is_err()); s.unchanged(refs);
    }
}
#[test]
fn inherited_transaction_rejects_foreign_mixed_gapped_overlapping_and_wrong_mm_vmas() {
    for variant in 0..9 {
        let mut s=Scenario::new(); let refs=Arc::strong_count(&s.owner);
        match variant {
            0=>s.children[1].vm_mm=&mut *s.parent_mm,
            1=>s.children[1].vm_ops=ptr::null(),
            2=>s.children[1].__bindgen_anon_1.__bindgen_anon_1.vm_start+=4096,
            3=>s.children[1].__bindgen_anon_1.__bindgen_anon_1.vm_start-=4096,
            4=>s.children[1].vm_pgoff=0,
            5=>s.children[1].__bindgen_anon_2.__vm_flags=0,
            6=>s.children[1].__bindgen_anon_2.__vm_flags|=8,
            7=>s.children[1].vm_file=ptr::null_mut(),
            _=>{let foreign=Arc::new(VmaOwner {registration:s.child_registration.clone(),mirror:s.parent.clone()},0).unwrap(); unsafe{vma_close(&mut *s.children[1]);} s.children[1].vm_private_data=Arc::into_raw(foreign).cast_mut().cast();s.children[1].old_owner=s.children[1].vm_private_data;},
        }
        assert!(s.run().is_err()); s.unchanged(if variant==8 {refs-1}else{refs});
    }
}
#[test]
fn inherited_transaction_allocation_failures_balance_owners_and_mm_before_mutation() {
    for fail in 1..=3 { let s=Scenario::new();let refs=Arc::strong_count(&s.owner); ALLOCATION.with(|a|a.set((0,fail))); assert!(matches!(s.run(),Err(-12))); s.unchanged(refs); }
}
#[test]
fn inherited_transaction_clears_every_pfn_before_child_owner_and_seal_publication() {
    let mut s=Scenario::new(); let parent_raw=s.parent_vma.vm_private_data;
    let old_refs=Arc::strong_count(&s.owner);
    let child=unsafe {Mirror::inherit_vmas(&s.parent,&s.parent_registration,s.child_registration.clone(),0,0x8000,|mirror| {
        MODEL.with(|m| {let mut m=m.borrow_mut();assert!(m.valid&&m.locked);assert_eq!(m.events,vec!["lock","write","write","zap","zap"]);m.events.push("seal");});
        for v in &s.children { assert!(v.writing&&v.cleared); let owner=vma_owner(&**v as *const _ as *mut _).unwrap(); assert!(ptr::eq(&*owner.mirror,&**mirror));assert!(ptr::eq(&*owner.registration,&*s.child_registration)); }
    })}.unwrap();
    assert_eq!(Arc::strong_count(&s.owner),old_refs-2);assert_eq!(s.parent_vma.vm_private_data,parent_raw);assert!(!s.parent_vma.cleared);
    assert_eq!(count(&s.child_mm),2);assert_eq!(s.child_mm.users.get(),1);assert_eq!(count(&s.parent_mm),2);
    MODEL.with(|m|assert_eq!(m.borrow().events,vec!["lock","write","write","zap","zap","seal","unlock"]));
    for (v,physical) in [(&mut *s.parent_vma,0x9000),(&mut *s.children[0],0x19000)] {
        let mut fault=bindings::vm_fault {__bindgen_anon_1:bindings::fault_fields {vma:v,address:0x1000},flags:0};
        assert_eq!(unsafe{lookup_fault(&mut fault,false)}.unwrap().physical,physical);
    }
    assert_eq!(s.parent_registration.calls.get(),1);assert_eq!(s.child_registration.calls.get(),1);
    for v in &mut s.children {unsafe{vma_close(&mut **v)}}
    drop(child);assert_eq!(count(&s.child_mm),1);assert_eq!(s.child_mm.users.get(),1);
}
}
}
