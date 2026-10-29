// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
use abi::{Process,ProcessVm};
use debug::Ddebug;
use core::ptr::{addr_of,addr_of_mut,read_volatile};
#[repr(C)]#[derive(Clone,Copy,Debug,PartialEq,Eq)]struct Trace{calls:u64,kind:i32,first:i32,last:i32,printer_return:i32,values:[u64;5],format:[u8;160],rendered:[u8;256],rendered_length:i32,padding:i32}
impl Default for Trace{fn default()->Self{Self{calls:0,kind:0,first:0,last:0,printer_return:0,values:[0;5],format:[0;160],rendered:[0;256],rendered_length:0,padding:0}}}
unsafe extern "C" {
    static mut mckernel_f06_vdso_map_debug:Ddebug;
    fn original_arch_vdso_map_log_bridge(event:i32,error:i32,vm:*mut ProcessVm,a:u64,b:u64,c:u64,d:u64,pages:i32);
    fn fixture_consumer_call(event:i32,error:i32,vm:*mut ProcessVm,a:u64,b:u64,c:u64,d:u64,pages:i32);
    fn fixture_original_descriptor()->*mut Ddebug;
    fn fixture_selected_descriptor()->*mut Ddebug;
    fn fixture_descriptor_count()->usize;
    fn fixture_set_flags(descriptor:*mut Ddebug,flags:u32);
    fn fixture_read_flags(descriptor:*mut Ddebug)->u32;
    fn fixture_set_original_offset(offset:isize);
    fn fixture_set_selected_offset(offset:isize);
    fn fixture_read_original_offset()->isize;
    fn fixture_read_selected_offset()->isize;
    fn fixture_reset(result:i32);
    fn fixture_read_trace(out:*mut Trace);
}
fn fixed<const N:usize>(text:&str)->[u8;N]{assert!(text.len()<N);let mut out=[0;N];out[..text.len()].copy_from_slice(text.as_bytes());out}
unsafe fn metadata(p:*mut Ddebug)->(String,String,bool,u32,[u8;4]){
    let mut padding=[0;4];unsafe{core::ptr::copy_nonoverlapping(p.cast::<u8>().add(28),padding.as_mut_ptr(),4);}
    unsafe{(std::ffi::CStr::from_ptr((*p).file).to_str().unwrap().to_owned(),std::ffi::CStr::from_ptr((*p).func).to_str().unwrap().to_owned(),(*p).fmt.is_null(),read_volatile(addr_of!((*p).line_flags)),padding)}
}
fn expected(event:i32,error:i32,flags:u32,pid:i32,values:[u64;5],pages:i32,result:i32)->Trace{
    let (format,rendered,kind,first,last,args)=match event{
        1 if flags!=0=>("arch_map_vdso(): not available\n","arch_map_vdso(): not available\n".to_owned(),0,0,0,[0;5]),
        2=>("ERROR: adding memory range for vdso. %d\n",format!("ERROR: adding memory range for vdso. {error}\n"),1,error,0,[0;5]),
        3=>("mcexec_v10: vdso_map pid=%d container=0x%lx vdso=0x%lx vdso_end=0x%lx offset=0x%lx size=0x%lx pages=%d\n",format!("mcexec_v10: vdso_map pid={pid} container=0x{:x} vdso=0x{:x} vdso_end=0x{:x} offset=0x{:x} size=0x{:x} pages={pages}\n",values[0],values[1],values[2],values[3],values[4]),2,pid,pages,values),
        4=>("ihk_mc_pt_set_range failed. %d\n",format!("ihk_mc_pt_set_range failed. {error}\n"),1,error,0,[0;5]),
        5=>("ERROR: adding memory range for vvar. %d\n",format!("ERROR: adding memory range for vvar. {error}\n"),1,error,0,[0;5]),
        _=>return Trace::default(),
    };
    Trace{calls:1,kind,first,last,printer_return:result,values:args,format:fixed(format),rendered:fixed(&rendered),rendered_length:rendered.len()as i32,padding:0}
}
#[test]
fn original_c_and_rust_vdso_map_log(){
    assert_eq!(core::mem::size_of::<Trace>(),488);assert_eq!(core::mem::size_of::<Ddebug>(),32);assert_eq!(core::mem::align_of::<Ddebug>(),8);
    assert_eq!(core::mem::size_of::<ProcessVm>(),304);assert_eq!(core::mem::offset_of!(ProcessVm,proc),136);
    assert_eq!(core::mem::size_of::<Process>(),1728);assert_eq!(core::mem::align_of::<Process>(),64);assert_eq!(core::mem::offset_of!(Process,pid),456);
    assert_eq!(unsafe{fixture_descriptor_count()},2);
    let selected=addr_of_mut!(mckernel_f06_vdso_map_debug);let original=unsafe{fixture_original_descriptor()};assert!(!original.is_null());assert_ne!(selected,original);assert_eq!(unsafe{fixture_selected_descriptor()},selected);
    let identity=("/src/arch/x86_64/kernel/syscall.c".to_owned(),"arch_vdso_map_log_bridge".to_owned(),true,3084,[0;4]);
    assert_eq!(unsafe{metadata(original)},identity);assert_eq!(unsafe{metadata(selected)},identity);
    let mut process=core::mem::MaybeUninit::<Process>::zeroed();let mut vm=core::mem::MaybeUninit::<ProcessVm>::zeroed();
    let p=process.as_mut_ptr();let v=vm.as_mut_ptr();let ints=[i32::MIN,-1,0,7,i32::MAX];let offsets=[isize::MIN,-4096,0,4096,isize::MAX];let words=[0u64,1,0x1234_5678_9abc_def0,1<<63,u64::MAX];
    let mut pairs=0;
    for event in [i32::MIN,-1,0,1,2,3,4,5,6,i32::MAX]{for flags in [0u32,1,2,128,255]{for error in ints{for pi in 0..5{for oi in 0..5{for state in 0..3{for result in [i32::MIN,0,i32::MAX]{
        let pid=ints[pi];let offset=offsets[oi];let pattern=(pi+oi)%5;let a=words[pattern];let b=words[(pattern+1)%5];let c=words[(pattern+2)%5];let d=words[(pattern+3)%5];let pages=ints[(pi+2*oi)%5];
        unsafe{addr_of_mut!((*p).pid).write(pid);addr_of_mut!((*v).proc).write(if state==2{p.cast()}else{core::ptr::null_mut()});}
        let target=if state==0{core::ptr::null_mut()}else{v};
        let before_process=unsafe{core::slice::from_raw_parts(p.cast::<u8>(),core::mem::size_of::<Process>())}.to_vec();let before_vm=unsafe{core::slice::from_raw_parts(v.cast::<u8>(),core::mem::size_of::<ProcessVm>())}.to_vec();
        unsafe{fixture_set_flags(original,flags);fixture_set_flags(selected,flags);fixture_set_original_offset(offset);fixture_set_selected_offset(offset);fixture_reset(result);original_arch_vdso_map_log_bridge(event,error,target,a,b,c,d,pages);}
        let mut reference=Trace::default();unsafe{fixture_read_trace(&mut reference);fixture_reset(result);fixture_consumer_call(event,error,target,a,b,c,d,pages);}
        let mut actual=Trace::default();unsafe{fixture_read_trace(&mut actual);}
        assert_eq!(actual,reference,"unchanged C oracle event={event} state={state} pid={pid} offset={offset}");
        assert_eq!(actual,expected(event,error,flags,if state==2{pid}else{-1},[a,b,c,offset as u64,d],pages,result),"independent format/types/order/render oracle");
        assert_eq!(unsafe{fixture_read_original_offset()},offset);assert_eq!(unsafe{fixture_read_selected_offset()},offset);
        assert_eq!(unsafe{core::slice::from_raw_parts(p.cast::<u8>(),before_process.len())},before_process);assert_eq!(unsafe{core::slice::from_raw_parts(v.cast::<u8>(),before_vm.len())},before_vm);
        for descriptor in [original,selected]{let got=unsafe{metadata(descriptor)};assert_eq!(got.0,identity.0);assert_eq!(got.1,identity.1);assert!(got.2);assert_eq!(got.3,3084|(flags<<24));assert_eq!(got.4,[0;4]);assert_eq!(unsafe{fixture_read_flags(descriptor)},flags);}
        pairs+=1;
    }}}}}}}
    assert_eq!(pairs,56250);
    // Even a nonnull inaccessible sentinel is valid for ignored arguments of
    // non-mapped events. It is never dereferenced by either original or port.
    for event in [i32::MIN,0,1,2,4,5,i32::MAX]{unsafe{fixture_set_flags(original,255);fixture_set_flags(selected,255);fixture_reset(0);original_arch_vdso_map_log_bridge(event,-14,core::ptr::dangling_mut(),0,0,0,0,0);}
        let mut reference=Trace::default();unsafe{fixture_read_trace(&mut reference);fixture_reset(0);fixture_consumer_call(event,-14,core::ptr::dangling_mut(),0,0,0,0,0);}
        let mut actual=Trace::default();unsafe{fixture_read_trace(&mut actual);}assert_eq!(actual,reference);
    }
    println!("functional vdso-map-log original-C/Rust pairs={pairs}; genuine C caller/types, null VM/proc, signed pid/offset/pages, typed varargs, exact inherited metadata, real Rust descriptor and reused state/storage providers checked; ignored-VM cases=7");
}
