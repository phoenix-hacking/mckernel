// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact actual Ddebug type/candidate; genuine C macro/original function oracle.
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
// Selected storage and callback are linked from the actual no_std Rust object.
use core::ptr::{addr_of,addr_of_mut,read_volatile};
use debug::Ddebug;
#[repr(C)]#[derive(Clone,Copy,Debug,PartialEq,Eq)]struct Trace{calls:u64,cpu:i32,printer_return:i32,value:u64,format:[u8;96],rendered:[u8;128],rendered_length:i32,padding:i32}
impl Default for Trace{fn default()->Self{Self{calls:0,cpu:0,printer_return:0,value:0,format:[0;96],rendered:[0;128],rendered_length:0,padding:0}}}
unsafe extern "C" {
    static mut mckernel_f06_arch_prctl_debug:Ddebug;
    fn arch_prctl_log_bridge(event:i32,cpu:i32,value:u64);
    fn fixture_selected_descriptor()->*mut Ddebug;
    fn fixture_consumer_set_flags(flags:u32);
    fn fixture_consumer_read_flags()->u32;
    fn fixture_consumer_call(event:i32,cpu:i32,value:u64);
    fn original_arch_prctl_log_bridge(event:i32,cpu:i32,value:u64);
    fn fixture_original_descriptor()->*mut Ddebug;
    fn fixture_descriptor_count()->usize;
    fn fixture_set_flags(descriptor:*mut Ddebug,flags:u32);
    fn fixture_original_flag_field(descriptor:*mut Ddebug)->u32;
    fn fixture_reset(result:i32);
    fn fixture_read_trace(out:*mut Trace);
}
fn fixed<const N:usize>(text:&str)->[u8;N]{assert!(text.len()<N);let mut out=[0;N];out[..text.len()].copy_from_slice(text.as_bytes());out}
unsafe fn metadata(descriptor:*mut Ddebug)->(String,String,bool,u32,[u8;4]){
    let mut padding=[0u8;4];unsafe{core::ptr::copy_nonoverlapping(descriptor.cast::<u8>().add(28),padding.as_mut_ptr(),4);}
    unsafe{(std::ffi::CStr::from_ptr((*descriptor).file).to_str().unwrap().to_owned(),std::ffi::CStr::from_ptr((*descriptor).func).to_str().unwrap().to_owned(),(*descriptor).fmt.is_null(),read_volatile(addr_of!((*descriptor).line_flags)),padding)}
}
#[test]
fn original_c_and_rust_descriptor_ownership(){
    assert_eq!(core::mem::size_of::<Trace>(),256);assert_eq!(core::mem::size_of::<Ddebug>(),32);assert_eq!(core::mem::align_of::<Ddebug>(),8);assert_eq!(core::mem::offset_of!(Ddebug,line_flags),24);
    assert_eq!(unsafe{fixture_descriptor_count()},2);
    let original=unsafe{fixture_original_descriptor()};let selected=addr_of_mut!(mckernel_f06_arch_prctl_debug);assert!(!original.is_null());assert_ne!(original,selected);
    let expected_metadata=("/src/arch/x86_64/kernel/syscall.c".to_owned(),"arch_prctl_log_bridge".to_owned(),true,669u32,[0u8;4]);
    assert_eq!(unsafe{metadata(original)},expected_metadata);assert_eq!(unsafe{metadata(selected)},expected_metadata);
    assert_eq!(unsafe{fixture_selected_descriptor()},selected,"genuine C extern imports the one actual Rust owner");
    for flags in [0u32,1,2,128,255]{
        unsafe{fixture_consumer_set_flags(flags);}
        assert_eq!(unsafe{read_volatile(selected.cast::<u8>().add(27))},flags as u8);
        assert_eq!(unsafe{fixture_consumer_read_flags()},flags);
        unsafe{core::ptr::write_volatile(selected.cast::<u8>().add(27),255-flags as u8);}
        assert_eq!(unsafe{fixture_consumer_read_flags()},255-flags);
    }
    unsafe{fixture_consumer_set_flags(0);}
    let mut pairs=0;
    for event in [i32::MIN,-1,0,0x1002,0x1003,i32::MAX]{for flags in [0u32,1,2,128,255]{for cpu in [i32::MIN,-1,0,7,i32::MAX]{for value in [0u64,1,0x1234_5678_9abc_def0,1<<63,u64::MAX]{for result in [i32::MIN,-1,0,1,i32::MAX]{
        unsafe{fixture_set_flags(original,flags);fixture_consumer_set_flags(flags);fixture_reset(result);original_arch_prctl_log_bridge(event,cpu,value);}
        let mut original_trace=Trace::default();unsafe{fixture_read_trace(&mut original_trace);fixture_reset(result);}
        unsafe{fixture_consumer_call(event,cpu,value);}let mut actual_trace=Trace::default();unsafe{fixture_read_trace(&mut actual_trace);}
        assert_eq!(actual_trace,original_trace);
        let expected=if event==0x1002&&flags!=0{let rendered=format!("[{cpu}] arch_prctl: ARCH_SET_FS: 0x{value:X}\n");Trace{calls:1,cpu,printer_return:result,value,format:fixed("[%d] arch_prctl: ARCH_SET_FS: 0x%lX\n"),rendered:fixed(&rendered),rendered_length:rendered.len()as i32,padding:0}}else{Trace::default()};
        assert_eq!(actual_trace,expected,"independent event/flag/message/argument/render oracle");
        for descriptor in [original,selected]{let observed=unsafe{metadata(descriptor)};assert_eq!(observed.0,expected_metadata.0);assert_eq!(observed.1,expected_metadata.1);assert!(observed.2);assert_eq!(observed.3,669|(flags<<24));assert_eq!(observed.4,[0;4]);assert_eq!(unsafe{fixture_original_flag_field(descriptor)},flags);assert_eq!(unsafe{read_volatile(descriptor.cast::<u8>().add(27))},flags as u8);}
        pairs+=1;
    }}}}}
    assert_eq!(pairs,3750);
    println!("functional actual-Rust-descriptor/C-consumer original-C/Rust pairs={pairs}; exact inherited metadata, real C bitfield/byte27 gate, event/vararg/rendered output and full trace canaries checked");
}
