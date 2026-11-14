#[cfg(test)] mod original_witness {
 use super::*;
 #[test] fn original_intact_negative_capsule_poisoned_corrected_retry(){
  table().lock().clear();MODE.store(0,Ordering::SeqCst);let p=Registration::new(10,100);let c=Registration::new(20,200);
  let proof=ForkPreparedV3{geometry:ForkGeometryV3{root:4096,start:8192,length:12288},child_pid:20,reserved:0,child_mm:400,response:500,nonce:600};c.reserve_fork_pair(&p,&proof).unwrap();
  let mut bytes=[0;96];for(at,v)in[(8,91u64),(48,2),(56,20),(64,12288),(72,4096),(80,800)]{bytes[at..at+8].copy_from_slice(&v.to_le_bytes())}
  assert_eq!(p.fork_control_current(&HostWorker{handle:1},&bytes),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,800);
  MODE.store(2,Ordering::SeqCst);assert_eq!(p.fork_control_current(&HostWorker{handle:1},&bytes),Err(EBUSY));assert_eq!(p.control_children.lock()[0].carrier,800);
  println!("ORIGINAL: intact negative capsule return left carrier 800; corrected actual caller refused EBUSY before provider");
 }
}
