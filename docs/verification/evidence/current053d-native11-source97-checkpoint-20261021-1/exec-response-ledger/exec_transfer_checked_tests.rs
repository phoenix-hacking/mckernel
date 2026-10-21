// SPDX-License-Identifier: GPL-2.0
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code)]
#[path="application_rpc.rs"] mod application_rpc;
#[path="application_syscall.rs"] mod application_syscall;
#[path="application_image.rs"] mod application_image;
#[path="exec_transfer_checked.rs"] mod checked;
use application_syscall::Request;
use checked::{ExecKey, Phase2, ResponseOwnedExecClaims, Section, Step};

fn request(number:u64,args:[u64;6])->Request {
    let mut b=[0u8;128];b[8..12].copy_from_slice(&4i32.to_le_bytes());
    b[32..36].copy_from_slice(&700i32.to_le_bytes());b[48..52].copy_from_slice(&900i32.to_le_bytes());
    b[56..64].copy_from_slice(&1u64.to_le_bytes());b[64..72].copy_from_slice(&number.to_le_bytes());
    for(i,a)in args.iter().enumerate(){b[72+i*8..80+i*8].copy_from_slice(&a.to_le_bytes());}
    b[120..128].copy_from_slice(&0x200000u64.to_le_bytes());Request::decode(&b,1).unwrap()
}
fn put(b:&mut[u8],at:usize,n:u64){b[at..at+8].copy_from_slice(&n.to_le_bytes());}
// Independent ABI fixture: header776, section56, vaddr/memsz/rpa/filesz/offset.
fn descriptor(sections:&[(u64,u64,u64,u64)])->Vec<u8>{
    let mut b=vec![0;776+56*sections.len()];put(&mut b,0,0xcafecafe44332211);
    b[8..12].copy_from_slice(&(sections.len() as i32).to_le_bytes());
    for(i,(va,memory,physical,files))in sections.iter().enumerate(){
        let at=776+56*i;put(&mut b,at,*va);put(&mut b,at+8,*memory);
        put(&mut b,at+16,*physical);put(&mut b,at+24,*files);
        b[at+40..at+44].copy_from_slice(&5i32.to_le_bytes());
    }b
}
fn phase2(b:&[u8])->Request{request(59,[2,0x300000,b.len() as u64,0,0,0])}
fn upload(physical:u64)->Step{Step{physical,bytes:4096,direction:0}}
fn read(b:&[u8])->Step{Step{physical:0x300000,bytes:b.len(),direction:1}}

#[test] fn actual_request_phase_and_tid_contracts_are_disjoint(){
    let b=descriptor(&[(0x400000,4096,0x500000,1)]);
    let tid=request(186,[0,0,0,0,2,0x300000]);assert_eq!(tid.tid_buffer(),Ok((0x300000,8)));
    assert!(begin(&tid).is_err());
    assert!(begin(&request(59,[1,0x300000,b.len() as u64,0,0,0])).is_err());
    assert_eq!(phase2(&b).tid_buffer(),Err(-22));
}
#[test] fn phase1_exact_descriptor_and_optional_flat_argv(){
    let mut b=descriptor(&[(0x400000,4096,0,1)]);let r=request(59,[1,0,0x400000,0x300000,0,0]);
    let step=Step{physical:0x300000,bytes:b.len(),direction:0};
    assert_eq!(checked::phase1_upload(&r,step,&b),Ok(step));
    // One flattened string: count1, offset24, terminal26, "x\0".
    let mut argv=vec![0;26];put(&mut argv,0,1);put(&mut argv,8,24);put(&mut argv,16,26);argv[24]=b'x';
    put(&mut b,160,26);b.extend_from_slice(&argv);
    let step=Step{bytes:b.len(),..step};assert_eq!(checked::phase1_upload(&r,step,&b),Ok(step));
    b.pop();assert!(checked::phase1_upload(&r,Step{bytes:b.len(),..step},&b).is_err());
}
#[test] fn phase1_wrong_span_direction_extra_bytes_and_overcapacity_reject(){
    let mut b=descriptor(&[(0x400000,4096,0,1)]);let r=request(59,[1,0,0x400000,0x300000,0,0]);
    let good=Step{physical:0x300000,bytes:b.len(),direction:0};
    for bad in [Step{direction:1,..good},Step{physical:0x301000,..good},Step{bytes:good.bytes-1,..good}]{
        assert!(checked::phase1_upload(&r,bad,&b).is_err());
    }
    b.push(0);assert!(checked::phase1_upload(&r,Step{bytes:b.len(),..good},&b).is_err());
    b.resize(16385,0);assert!(checked::phase1_upload(&r,Step{bytes:b.len(),..good},&b).is_err());
}
#[test] fn descriptor_delivery_commit_required_even_all_bss(){
    let b=descriptor(&[(0x400000,8192,0,0)]);let r=phase2(&b);let mut p=begin(&r).unwrap();
    assert!(!p.complete(&r,key()).unwrap());assert_eq!(p.expected(&r,key()),Ok(Some(read(&b))));
    assert!(p.copied(&r,key(),read(&b)).is_err());p.stage_descriptor(&r,key(),&b).unwrap();
    // A failed outer UserSlice writer performs no commit. Repeated reads stay exact.
    for _ in 0..3{assert!(!p.complete(&r,key()).unwrap());assert_eq!(p.expected(&r,key()),Ok(Some(read(&b))));}
    assert!(p.stage_descriptor(&r,key(),&b).is_err());reserve(&mut p,&b);p.copied(&r,key(),read(&b)).unwrap();
    assert!(p.complete(&r,key()).unwrap());assert_eq!(p.expected(&r,key()),Ok(None));
    assert!(p.copied(&r,key(),read(&b)).is_err());
}
#[test] fn actual_launcher_file_page_order_excludes_unsent_bss(){
    let b=descriptor(&[(0x400003,20000,0x500000,4096),(0x410000,4096,0,0),(0x420000,8192,0x600000,1)]);
    let r=phase2(&b);let mut p=begin(&r).unwrap();p.stage_descriptor(&r,key(),&b).unwrap();
    assert_eq!(p.sections().unwrap().iter().map(|s|s.pages).collect::<Vec<_>>(),vec![2,0,1]);
    reserve(&mut p,&b);p.copied(&r,key(),read(&b)).unwrap();
    for physical in [0x500000,0x501000,0x600000]{
        assert!(!p.complete(&r,key()).unwrap());assert_eq!(p.expected(&r,key()),Ok(Some(upload(physical))));
        p.copied(&r,key(),upload(physical)).unwrap();
    }
    assert!(p.complete(&r,key()).unwrap());assert!(p.copied(&r,key(),upload(0x601000)).is_err());
}
#[test] fn failures_do_not_advance_page_or_enable_ret_zero(){
    let b=descriptor(&[(0x400000,8192,0x500000,4097)]);let r=phase2(&b);
    let mut p=begin(&r).unwrap();p.stage_descriptor(&r,key(),&b).unwrap();reserve(&mut p,&b);p.copied(&r,key(),read(&b)).unwrap();
    for bad in [upload(0x501000),Step{direction:1,..upload(0x500000)},Step{bytes:4095,..upload(0x500000)}]{
        assert!(p.copied(&r,key(),bad).is_err());assert_eq!(p.expected(&r,key()),Ok(Some(upload(0x500000))));
        assert!(!p.complete(&r,key()).unwrap());
    }
    p.copied(&r,key(),upload(0x500000)).unwrap();assert!(p.copied(&r,key(),upload(0x500000)).is_err());
    assert!(!p.complete(&r,key()).unwrap());
}
#[test] fn malformed_later_section_does_not_publish_partial_plan(){
    let mut b=descriptor(&[(0x400000,4096,0x500000,1),(0x410000,1,0x600000,2)]);let r=phase2(&b);
    let mut p=begin(&r).unwrap();assert!(p.stage_descriptor(&r,key(),&b).is_err());
    assert!(p.sections().is_err());assert!(!p.complete(&r,key()).unwrap());
    put(&mut b,776+56+8,4096);p.stage_descriptor(&r,key(),&b).unwrap();assert_eq!(p.sections().unwrap().len(),2);
}
#[test] fn malformed_descriptor_and_physical_overflows_reject(){
    for (va,memory,physical,files) in [(0x400000,1,0x500000,2),(0x400000,4096,0x500001,1),
        (u64::MAX,4096,0x500000,1),(0x400000,4096,u64::MAX-4095,1)]{
        let b=descriptor(&[(va,memory,physical,files)]);let r=phase2(&b);let mut p=begin(&r).unwrap();
        assert!(p.stage_descriptor(&r,key(),&b).is_err());assert!(!p.complete(&r,key()).unwrap());
    }
    assert!(begin(&request(59,[2,0x300001,832,0,0,0])).is_err());
    assert!(begin(&request(59,[2,0x300000,833,0,0,0])).is_err());
}
#[test] fn every_transition_requires_the_same_retained_request(){
    let b=descriptor(&[(0x400000,4096,0x500000,1)]);let r=phase2(&b);
    let other=request(59,[2,0x301000,b.len() as u64,0,0,0]);let mut p=begin(&r).unwrap();
    assert!(p.complete(&other,key()).is_err());assert!(p.expected(&other,key()).is_err());
    assert!(p.stage_descriptor(&other,key(),&b).is_err());p.stage_descriptor(&r,key(),&b).unwrap();
    assert!(p.copied(&other,key(),read(&b)).is_err());assert!(!p.complete(&r,key()).unwrap());
}

fn key()->ExecKey{ExecKey{os_slot:0,os_generation:1,application:2,worker:3,delivery:4,response_serial:5,response_physical:0x200000}}
fn begin(r:&Request)->Result<Phase2,i32>{Phase2::begin(r,key())}
struct Group{key:ExecKey,descriptor:Step,fail:bool,owned:Vec<Section>,calls:usize}
impl Group{fn new(b:&[u8])->Self{Self{key:key(),descriptor:read(b),fail:false,owned:Vec::new(),calls:0}}}
// Controlled test provider owns no guest mappings. Its reservation is an atomic
// model of the interface; no native provider is implemented by this fixture.
unsafe impl ResponseOwnedExecClaims for Group{
 fn key(&self)->ExecKey{self.key}
 fn descriptor(&self)->Step{self.descriptor}
 fn reserve_sections(&mut self,sections:&[Section])->Result<(),i32>{
  self.calls+=1;if self.fail{return Err(-12);}assert!(self.owned.is_empty());
  self.owned=sections.to_vec();Ok(())
 }
}
fn reserve(p:&mut Phase2,b:&[u8]){p.reserve_sections(&mut Group::new(b)).unwrap();}
#[test] fn allocation_failure_and_stale_keys_never_publish_page_eligibility(){
 let b=descriptor(&[(0x400000,4096,0x500000,1)]);let r=phase2(&b);let mut p=begin(&r).unwrap();
 p.stage_descriptor(&r,key(),&b).unwrap();let mut g=Group::new(&b);g.fail=true;
 assert_eq!(p.reserve_sections(&mut g),Err(-12));assert!(g.owned.is_empty());
 p.copied(&r,key(),read(&b)).unwrap();assert_eq!(p.expected(&r,key()),Err(-16));
 assert!(!p.complete(&r,key()).unwrap());g.fail=false;p.reserve_sections(&mut g).unwrap();
 assert_eq!(g.calls,2);assert_eq!(p.expected(&r,key()),Ok(Some(upload(0x500000))));
 assert!(p.reserve_sections(&mut g).is_err());
 for bad in [ExecKey{os_generation:2,..key()},ExecKey{application:9,..key()},ExecKey{worker:9,..key()},
  ExecKey{delivery:9,..key()},ExecKey{response_serial:9,..key()},ExecKey{response_physical:0x201000,..key()}]{
  assert!(p.expected(&r,bad).is_err());assert!(p.copied(&r,bad,upload(0x500000)).is_err());
  assert!(p.complete(&r,bad).is_err());
 }
 assert!(!p.complete(&r,key()).unwrap());assert_eq!(g.owned.len(),1);
 // Queue-full, partial cancel and uncertain transport make no helper transition:
 // the original response/group remains retained by the native owner.
 for _ in 0..3{assert_eq!(p.expected(&r,key()),Ok(Some(upload(0x500000))));assert_eq!(g.owned.len(),1);}
}
#[test] fn overlap_and_wrong_group_descriptor_reject_before_reservation(){
 for sections in [vec![(0x400000,4096,0x300000,1)],vec![(0x400000,4096,0x500000,1),(0x410000,4096,0x500000,1)]]{
  let b=descriptor(&sections);let r=phase2(&b);let mut p=begin(&r).unwrap();assert!(p.stage_descriptor(&r,key(),&b).is_err());
 }
 let b=descriptor(&[(0x400000,4096,0x500000,1)]);let r=phase2(&b);let mut p=begin(&r).unwrap();
 p.stage_descriptor(&r,key(),&b).unwrap();let mut g=Group::new(&b);g.key.worker+=1;
 assert!(p.reserve_sections(&mut g).is_err());assert_eq!(g.calls,0);g.key=key();g.descriptor.physical+=4096;
 assert!(p.reserve_sections(&mut g).is_err());assert_eq!(g.calls,0);
}
