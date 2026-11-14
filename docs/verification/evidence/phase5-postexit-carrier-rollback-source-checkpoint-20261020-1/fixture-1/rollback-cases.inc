#[cfg(test)] mod rollback_tests {
 use super::*;
 fn proof(c:&Arc<Registration>)->ForkPreparedV3{ForkPreparedV3{geometry:ForkGeometryV3{root:4096,start:8192,length:12288},child_pid:c.pid,reserved:0,child_mm:400,response:500,nonce:600}}
 fn bytes(selector:u64,pid:u64,carrier:u64)->[u8;96]{let mut b=[0;96];for(at,v)in[(8,91u64),(48,selector),(56,pid),(64,12288),(72,4096),(80,carrier)]{b[at..at+8].copy_from_slice(&v.to_le_bytes())}b}
 fn pair()->(Arc<Registration>,Arc<Registration>){table().lock().clear();MODE.store(0,Ordering::SeqCst);MODULE_RELEASES.store(0,Ordering::SeqCst);let p=Registration::new(10,100);let c=Registration::new(20,200);c.reserve_fork_pair(&p,&proof(&c)).unwrap();(p,c)}
 fn call(p:&Registration,selector:u64)->Result{p.fork_control_current(&HostWorker{handle:1},&bytes(selector,if selector==2{20}else{0},800))}
 #[test] fn rollback_negative_no_transfer_allows_actual_retry_and_ack(){
  let(p,c)=pair();assert_eq!(call(&p,2),Err(errno(-5)));assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),1);
  {let rows=p.control_children.lock();assert_eq!(rows.len(),1);assert_eq!(rows[0].carrier,0);assert_eq!(rows[0].carrier_capsule,0);}
  assert!(c.fork_parent.lock().is_some());MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));assert!(p.control_children.lock().is_empty());assert!(!c.armed.load(Ordering::Acquire));assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),2);
 }
 #[test] fn rollback_bad_request_identity_returns_key_before_corrected_delivery(){
  let(p,_c)=pair();MODE.store(3,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EACCES));assert_eq!(p.control_children.lock()[0].carrier,0);
  MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));
 }
 #[test] fn rollback_partial_and_transferred_errors_never_return_key(){
  for mode in [1,4,5]{let(p,c)=pair();MODE.store(mode,Ordering::SeqCst);assert!(call(&p,2).is_err());assert_eq!(p.control_children.lock()[0].carrier,800);assert_ne!(p.control_children.lock()[0].carrier_capsule,0);assert!(c.fork_parent.lock().is_some());assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),0);MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EBUSY));assert_eq!(p.control_children.lock()[0].carrier,800);
   // A fully transferred error is retained by the adapter. Test teardown alone
   // releases its module; this is not a production ACK/release claim.
   if mode==5{let held=pending().lock().take().unwrap();unsafe{(held.release)(held.owner as *mut c_void)};}
  }
 }
 #[test] fn rollback_inconsistent_success_or_mutated_call_retains_key(){
  for mode in [6,7]{let(p,c)=pair();MODE.store(mode,Ordering::SeqCst);assert_eq!(call(&p,2),Err(errno(-71)));assert_eq!(p.control_children.lock()[0].carrier,800);assert!(c.fork_parent.lock().is_some());assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),1);}
 }
 #[test] fn rollback_exact_attempt_parent_child_epoch_capsule_refusals(){
  for changed in 0..6{let(p,c)=pair();let mut witness=p.bind_fork_carrier(&c,800,1234).unwrap();match changed{0=>witness.parent+=1,1=>witness.child=Registration::new(20,201),2=>witness.carrier+=8,3=>witness.capsule+=1,4=>witness.response+=1,_=>witness.nonce+=1};assert_eq!(p.cancel_untransferred_fork_carrier(witness),Err(EACCES));let rows=p.control_children.lock();assert_eq!(rows[0].carrier,800);assert_eq!(rows[0].carrier_capsule,1234);}
 }
 #[test] fn rollback_stale_attempt_cannot_cancel_rebound_identical_carrier(){
  let(p,c)=pair();let first=p.bind_fork_carrier(&c,800,1234).unwrap();
  // Preserve stale metadata in this private test to model an ABA/refusal probe;
  // production witnesses are move-only and cannot be duplicated by callers.
  let stale=ForkCarrierBinding{parent:first.parent,child:c.clone(),carrier:first.carrier,capsule:first.capsule,response:first.response,nonce:first.nonce};
  p.cancel_untransferred_fork_carrier(first).unwrap();let second=p.bind_fork_carrier(&c,800,1235).unwrap();assert_eq!(p.cancel_untransferred_fork_carrier(stale),Err(EACCES));assert_eq!(p.control_children.lock()[0].carrier_capsule,1235);p.cancel_untransferred_fork_carrier(second).unwrap();assert_eq!(p.control_children.lock()[0].carrier,0);
 }
 #[test] fn rollback_concurrent_duplicate_refuses_then_original_retry_succeeds(){
  let(p,c)=pair();let arrived=Arc::new(std::sync::Barrier::new(2));let resume=Arc::new(std::sync::Barrier::new(2));*blocked().lock()=Some((arrived.clone(),resume.clone()));MODE.store(8,Ordering::SeqCst);
  let owner=p.clone();let job=std::thread::spawn(move||call(&owner,2));arrived.wait();MODE.store(0,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EBUSY));assert_eq!(call(&p,3),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,800);resume.wait();assert_eq!(job.join().unwrap(),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,0);*blocked().lock()=None;
  MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));assert!(!c.armed.load(Ordering::Acquire));
 }
 #[test] fn rollback_zero_capsule_and_other_live_carrier_never_overwrite(){
  let(p,c)=pair();assert!(p.bind_fork_carrier(&c,800,0).is_err());assert_eq!(p.control_children.lock()[0].carrier,0);let held=p.bind_fork_carrier(&c,800,1234).unwrap();let d=Registration::new(21,201);d.reserve_fork_pair(&p,&proof(&d)).unwrap();assert!(p.bind_fork_carrier(&d,800,1235).is_err());assert_eq!(p.control_children.lock()[1].carrier,0);p.cancel_untransferred_fork_carrier(held).unwrap();assert_eq!(p.control_children.lock()[0].carrier,0);
 }
}
