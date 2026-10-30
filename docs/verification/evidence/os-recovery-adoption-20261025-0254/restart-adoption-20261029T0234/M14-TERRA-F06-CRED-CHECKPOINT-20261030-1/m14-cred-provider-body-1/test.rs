#![allow(non_camel_case_types)]
use std::sync::Mutex;
type c_int=i32;type c_ulong=u64;
type McctrlControlCredValueFn=unsafe extern "C" fn()->c_int;
type McctrlControlPhysToVirtFn=unsafe extern "C" fn(c_ulong)->c_ulong;
const EINVAL:c_int=22;
include!("actual-bodies.rs");
static LOG:Mutex<Vec<u32>>=Mutex::new(Vec::new());
unsafe extern "C" fn map(p:u64)->u64{LOG.lock().unwrap().push(9);p}
macro_rules! cb {($n:ident,$v:expr)=>{unsafe extern "C" fn $n()->i32{LOG.lock().unwrap().push($v);100+$v as i32}}}
cb!(u,0);cb!(eu,1);cb!(su,2);cb!(fu,3);cb!(g,4);cb!(eg,5);cb!(sg,6);cb!(fg,7);
fn run(missing:Option<usize>)->(i32,[i32;8],Vec<u32>) {
 LOG.lock().unwrap().clear();let mut out=[-1;8];
 let mut mapfn:Option<McctrlControlPhysToVirtFn>=Some(map);
 let mut f:[Option<McctrlControlCredValueFn>;8]=[Some(u),Some(eu),Some(su),Some(fu),Some(g),Some(eg),Some(sg),Some(fg)];
 if let Some(i)=missing {if i==8{mapfn=None}else{f[i]=None;}}
 let rc=unsafe{mcctrl_control_getcred_body_result(out.as_mut_ptr() as u64,mapfn,f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7])};
 let log=LOG.lock().unwrap().clone();(rc,out,log)
}
#[test] fn success_fills_all_eight_in_order_before_return() {assert_eq!(run(None),(0,[100,101,102,103,104,105,106,107],vec![9,0,1,2,3,4,5,6,7]));}
#[test] fn missing_any_provider_fails_without_writing_or_callbacks() {for i in 0..9 {assert_eq!(run(Some(i)),(-22,[-1;8],vec![]));}}
