#![allow(dead_code)]
#[derive(Debug,PartialEq,Eq,Clone,Copy)] struct Error(i32);
impl Error { fn from_errno(n:i32)->Self { assert!((-4095..0).contains(&n)); Self(n) } }
type Result<T=()> = core::result::Result<T,Error>;
const EIO:Error=Error(-5);
mod kernel { pub mod error { use crate::{Error,Result}; pub fn to_result(err: core::ffi::c_int) -> Result {
    if err < 0 {
        Err(Error::from_errno(err))
    } else {
        Ok(())
    }
} } }
struct Counter { next_epoch:u64, fork_prepared_parent_refs:u32, last_sequence:u64, accesses:u32 }
mod os_runtime { use super::*; use crate::kernel::error::to_result; fn errno(value: i32) -> Error {
    to_result(value).err().unwrap_or(EIO)
}
fn probe(n:u64)->Result<u64> { let table=Counter { next_epoch:n,fork_prepared_parent_refs:0,last_sequence:0,accesses:0 }; let result = table.next_epoch.checked_add(1).ok_or(EOVERFLOW)?; Ok(result as u64) }
pub fn test(){ checks64(probe); } }
mod smp_application { use super::*; fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}
fn probe(n:u64)->Result<u64> { let p=Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 }; let result = p.fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?; Ok(result as u64) }
mod smp_fork_link { use super::*; fn probe(n:u64)->Result<u64> { let p=Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 }; let result = p.fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?; Ok(result as u64) }
fn sequence(n:u64)->Result<u64> { let record=Counter { next_epoch:0,fork_prepared_parent_refs:0,last_sequence:n,accesses:0 }; Ok(record.last_sequence.checked_add(1).ok_or(EOVERFLOW)?) } pub fn test(){ checks32(probe); checks64(sequence); } }
mod smp_fork_ingress { use super::*; fn probe(n:u64)->Result<u64> { let slots=[Some(Counter { next_epoch:0,fork_prepared_parent_refs:n as u32,last_sequence:0,accesses:0 })]; let pi=0; let result = slots[pi].as_ref().unwrap().fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?; Ok(result as u64) }
pub fn test(){ checks32(probe); } }
pub fn test(){ checks32(probe); smp_fork_link::test(); smp_fork_ingress::test(); } }
mod smp_application_image { use super::*; fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}
 impl Counter { fn probe(&self)->Result<u64> { Ok(self.accesses.checked_add(1).ok_or(EOVERFLOW)?) .map(|v| v as u64) } } fn probe(n:u64)->Result<u64>{ Counter { next_epoch:0,fork_prepared_parent_refs:0,last_sequence:0,accesses:n as u32 }.probe() } pub fn test(){checks32(probe);} }fn checks64(f:fn(u64)->Result<u64>){assert_eq!(f(0),Ok(1));assert_eq!(f(u64::MAX-1),Ok(u64::MAX));assert_eq!(f(u64::MAX),Err(Error(-75)));}
fn checks32(f:fn(u64)->Result<u64>){assert_eq!(f(0),Ok(1));assert_eq!(f(u32::MAX as u64-1),Ok(u32::MAX as u64));assert_eq!(f(u32::MAX as u64),Err(Error(-75)));}
fn main(){os_runtime::test();smp_application::test();smp_application_image::test();assert_ne!(Error(-75),EIO);assert_ne!(Error(-75),Error(-16));println!("six extracted production expressions: positive, boundary, overflow PASS; distinct errno -75 PASS");}
