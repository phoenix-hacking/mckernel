// Test-only probes appended after the exact complete frozen mailbox body.
impl<M:ResponseMemory> Mailbox<M> {
 pub(crate) fn fixture_call(&self,w:u64,s:u64,r:&Request,k:bool) {
  let c=self.calls.iter().flatten().find(|c|c.delivery.serial().wire()==s).unwrap();
  assert_eq!(c.delivery.request(),r);assert_eq!(c.worker.unwrap().wire(),w);assert_eq!(c.kernel,k);
  assert!(c.response.is_some());assert!(c.completion.is_none());
  assert_eq!(self.workers.iter().flatten().find(|a|a.worker.wire()==w).unwrap().delivery.map(Token::wire),Some(s));
 }
 pub(crate) fn fixture_memory(&mut self,s:u64)->&mut M {
  self.calls.iter_mut().flatten().find(|c|c.delivery.serial().wire()==s).unwrap().response.as_mut().unwrap().memory_mut()
 }
 #[cfg(not(original))]
 pub(crate) fn fixture_refusal(&mut self,w:u64,s:u64,r:&Request,kind:u8,other:&Request) {
  match kind {0=>self.close().unwrap(),1=>self.quarantine(),_=>{}}
  let c=self.calls.iter_mut().flatten().find(|c|c.delivery.serial().wire()==s).unwrap();
  match kind {
   2=>c.kernel=false,3=>Self::cancel_call(c).unwrap(),4=>c.service=true,5=>c.transferred=true,6=>c.fork_parked=true,
   7=>c.publication_since=Some(1),8=>{c.delivery.begin_return(c.worker.unwrap(),r.cpu() as i64).unwrap();},
   9=>c.response.as_mut().unwrap().fixture_replace_request(other.clone()),
   10=>{let completion=c.response.take().unwrap().prepare_retained(0,0).map_err(|(_,e)|e).unwrap();c.completion=Some(completion);},
   _=>{}
  }
  let before_kernel=c.kernel;let before_request=c.delivery.request().clone();
  let before_response=c.response.as_ref().map(|r|r as *const _ as usize);
  let before_completion=c.completion.as_ref().map(|r|r as *const _ as usize);
  assert!(self.rollback_fork_kernel_admission(w,s,r).is_err());
  let c=self.calls.iter().flatten().find(|c|c.delivery.serial().wire()==s).unwrap();
  assert_eq!(c.kernel,before_kernel);assert_eq!(c.delivery.request(),&before_request);
  assert_eq!(c.response.as_ref().map(|r|r as *const _ as usize),before_response);
  assert_eq!(c.completion.as_ref().map(|r|r as *const _ as usize),before_completion);
 }
}
