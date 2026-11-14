use std::ptr::{addr_of_mut, null_mut};
#[derive(Debug,PartialEq,Eq,Clone)]
struct Event {kind:u8, lock:usize, node:usize, links:Vec<(usize,usize)>}
struct Context {
 proc:*mut Process,rset:*mut ResourceSet,parent:*mut Process,
 altparent:*mut Process,althash:*mut ProcessHash,entry:*mut AbiListHead,
 nodes:Vec<*mut AbiListHead>,events:Vec<Event>,mutate:bool,hash:bool,
 expected_lock:usize,first_node:usize,
}
static mut CURRENT:*mut Context=std::ptr::null_mut();
unsafe fn links(c:&Context)->Vec<(usize,usize)> {
 c.nodes.iter().map(|p|((**p).next as usize,(**p).prev as usize)).collect()
}
#[no_mangle]
unsafe extern "C" fn process_mcs_writer_lock_bridge(lock:CULong,node:*mut c_void) {
 let c=&mut *CURRENT;
 assert_eq!(lock as usize,c.expected_lock,"wrong bucket/parent lock");
 assert_eq!((node as usize)%64,0,"lock node must retain 64-byte alignment");
 c.first_node=node as usize;
 c.events.push(Event{kind:1,lock:lock as usize,node:node as usize,links:links(c)});
 // This is one synchronous callback. Only non-list fields change, to observe
 // the body's existing cached bucket and parent semantics across callbacks.
 if c.mutate {
  if c.hash {(*c.proc).pid=19;(*c.rset).process_hash=c.althash;}
  else {(*c.proc).parent=c.altparent;}
 }
}
#[no_mangle]
unsafe extern "C" fn process_mcs_writer_unlock_bridge(lock:CULong,node:*mut c_void) {
 let c=&mut *CURRENT;
 assert_eq!(lock as usize,c.expected_lock,"unlock must use original cached lock");
 assert_eq!(node as usize,c.first_node,"unlock must receive same lock node");
 c.events.push(Event{kind:2,lock:lock as usize,node:node as usize,links:links(c)});
}
unsafe extern "C" {
 fn c_process_release_hash_detach_bridge(r:*mut c_void,p:*mut c_void);
 fn c_process_release_sibling_detach_bridge(p:*mut c_void);
}
unsafe fn setup(c:&mut Context,shape:usize) {
 for &p in &c.nodes {(*p).next=null_mut();(*p).prev=null_mut();}
 if shape==0 {return}
 if shape==1 {(*c.entry).next=c.entry;(*c.entry).prev=c.entry;return}
 let h=c.nodes[1];let a=c.nodes[2];let b=c.nodes[3];
 let mut order=match shape {2=>vec![h,c.entry],3=>vec![h,c.entry,a],4=>vec![h,a,c.entry,b],_=>vec![h,a,c.entry]};
 for i in 0..order.len(){(*order[i]).prev=order[(i+order.len()-1)%order.len()];(*order[i]).next=order[(i+1)%order.len()];}
}
unsafe fn expected(c:&Context,shape:usize)->Vec<(usize,usize)> {
 let mut e=links(c);
 if shape>1 {
  let prev=(*c.entry).prev;let next=(*c.entry).next;
  let pi=c.nodes.iter().position(|p|*p==prev).unwrap();
  let ni=c.nodes.iter().position(|p|*p==next).unwrap();
  e[pi].0=next as usize;e[ni].1=prev as usize;
  e[0]=(LIST_POISON1,LIST_POISON2);
 }
 e
}
fn main(){unsafe{
 let mut count=0;
 let pids:Vec<i32>=(0..73).chain([73,74,145,146,i32::MAX]).collect();
 assert_eq!(pids.len(),78);
 for pid in pids {for shape in 0..6 {
  let mut proc:Box<Process>=Box::new(std::mem::zeroed());
  let mut parent:Box<Process>=Box::new(std::mem::zeroed());
  let mut altparent:Box<Process>=Box::new(std::mem::zeroed());
  let mut rset:Box<ResourceSet>=Box::new(std::mem::zeroed());
  let mut phash:Box<ProcessHash>=Box::new(std::mem::zeroed());
  let mut althash:Box<ProcessHash>=Box::new(std::mem::zeroed());
  let mut extras:[AbiListHead;3]=std::mem::zeroed();
  let mut c=Context{proc:&mut *proc,rset:&mut *rset,parent:&mut *parent,altparent:&mut *altparent,althash:&mut *althash,entry:null_mut(),nodes:vec![],events:vec![],mutate:false,hash:false,expected_lock:0,first_node:0};
  CURRENT=&mut c;
  for hash in [true,false] {for mutate in [false,true] {
   c.hash=hash;c.mutate=mutate;
   c.entry=if hash {addr_of_mut!(proc.hash_list)}else{addr_of_mut!(proc.siblings_list)};
   c.nodes=vec![c.entry,&mut extras[0],&mut extras[1],&mut extras[2]];
   let mut traces=Vec::new();
   for rust in [false,true] {
    proc.pid=pid;proc.parent=c.parent;rset.process_hash=&mut *phash;
    c.expected_lock=if hash {addr_of_mut!(phash.lock).cast::<McsRwlockLock>().add((pid%73) as usize) as usize}else{addr_of_mut!(parent.children_lock) as usize};
    c.first_node=0;c.events.clear();setup(&mut c,shape);
    let before=links(&c);let after=expected(&c,shape);
    let other_before=if hash {(proc.siblings_list.next,proc.siblings_list.prev)}else{(proc.hash_list.next,proc.hash_list.prev)};
    if hash {if rust {process_release_hash_detach_bridge(c.rset.cast(),c.proc.cast())}else{c_process_release_hash_detach_bridge(c.rset.cast(),c.proc.cast())}}
    else if rust {process_release_sibling_detach_bridge(c.proc.cast())}else{c_process_release_sibling_detach_bridge(c.proc.cast())}
    let calls=if hash && shape<=1 {0}else{2};
    assert_eq!(c.events.len(),calls,"wrong callback count shape={shape} hash={hash}");
    if calls==2 {assert_eq!(c.events[0].kind,1);assert_eq!(c.events[0].links,before);assert_eq!(c.events[1].kind,2);assert_eq!(c.events[1].links,after);}
    assert_eq!(links(&c),after,"independent list oracle shape={shape} hash={hash}");
    assert_eq!(proc.pid,if mutate&&hash&&calls>0 {19}else{pid});
    assert_eq!(proc.parent,if mutate&&!hash {c.altparent}else{c.parent});
    assert_eq!(rset.process_hash,if mutate&&hash&&calls>0 {c.althash}else{&mut *phash});
    assert_eq!(if hash {(proc.siblings_list.next,proc.siblings_list.prev)}else{(proc.hash_list.next,proc.hash_list.prev)},other_before);
    // All locks are initialized to zero, and these observer callbacks must not
    // change either the selected lock or any unrelated bucket.
    for table in [&*phash,&*althash] {for l in &table.lock {assert_eq!(l.slock.head_tail,0);}}
    assert_eq!(parent.children_lock.slock.head_tail,0);assert_eq!(altparent.children_lock.slock.head_tail,0);
    traces.push((links(&c),c.events.iter().map(|e|(e.kind,e.lock,e.links.clone())).collect::<Vec<_>>()));
   }
   assert_eq!(traces[0],traces[1],"actual C/Rust body parity");
  }}
  count+=1;
 }}
 CURRENT=null_mut();
 println!("PASS {count} actual C/Rust process-release scenarios; 3744 leaf calls; all 73 buckets, independent list oracle, callback ordering/cache/alignment, both selected callbacks");
}}
