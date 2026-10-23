// SPDX-License-Identifier: GPL-2.0
//! Finite exec delivery state; held by the ORIGINAL mailbox Call.
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use super::{application_syscall::Request,exec_transfer_checked::{ExecKey,Phase2,Step,phase1_upload}};
use kernel::prelude::*;
type Result<T=()> = core::result::Result<T,i32>;
enum Phase { One{complete:bool},Two{plan:Phase2,snapshot:Vec<u8>,pending:bool} }
pub(crate) struct ExecDelivery {key:ExecKey,phase:Phase}
impl ExecDelivery {
 pub(crate) fn phase1(key:ExecKey)->Self{Self{key,phase:Phase::One{complete:false}}}
 pub(crate) fn phase2(key:ExecKey,plan:Phase2,snapshot:Vec<u8>)->Self{Self{key,phase:Phase::Two{plan,snapshot,pending:false}}}
 pub(crate) fn pending(&self)->bool{matches!(&self.phase,Phase::Two{pending:true,..})}
 pub(crate) fn transfer(&mut self,r:&Request,step:Step,bytes:&mut[u8],copy:impl FnOnce(ExecKey,Step,&mut[u8])->Result)->Result{
  match &mut self.phase {
   Phase::One{complete}=>{if *complete{return Err(-16);}phase1_upload(r,step,bytes)?;copy(self.key,step,bytes)?;*complete=true;Ok(())}
   Phase::Two{plan,snapshot,pending}=>{
    if *pending||plan.expected(r,self.key)?!=Some(step)||step.bytes!=bytes.len(){return Err(-22);}
    if step.direction==1{if snapshot.len()!=bytes.len(){return Err(-22);}bytes.copy_from_slice(snapshot);*pending=true;Ok(())}
    else{copy(self.key,step,bytes)?;plan.copied(r,self.key,step)}
   }
  }
 }
 // Called by exact backend worker/delivery COMMIT or ABORT after UserSlice writer.
 pub(crate) fn usercopy_done(&mut self,r:&Request,success:bool)->Result{
  let Phase::Two{plan,pending,..}=&mut self.phase else{return Err(-22);};if !*pending{return Err(-16);}
  if success{let step=plan.expected(r,self.key)?.ok_or(-22)?;plan.copied(r,self.key,step)?;}
  *pending=false;Ok(())
 }
 pub(crate) fn complete(&self,r:&Request)->Result<bool>{match &self.phase{Phase::One{complete}=>Ok(*complete&&r.number()==59&&r.arguments()[0]==1),Phase::Two{plan,pending,..}=>Ok(!*pending&&plan.complete(r,self.key)?)}}
}
