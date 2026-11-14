// Functional McKernel OS/apps and Rust/assembly migration; no security testing.
// HOST-only consumer of the EXACT rebuilt kernel-profile core/builtins metadata.
// No libstd, copied core implementation, guessed Rust ABI export or ownership
// mock. The test panic handler observes a HOST terminal; kernel lib.rs is untouched.
#![no_std]
extern crate compiler_builtins;

use core::ffi::{c_int,c_void};
use core::fmt::{self,Write};
use core::hint::black_box;
use core::panic::PanicInfo;
use core::sync::atomic::{AtomicBool,AtomicU8,Ordering};

unsafe extern "C" {
    fn write(fd:c_int,buffer:*const c_void,count:usize)->isize;
    fn _Exit(status:c_int)->!;
}
static CASE:AtomicU8=AtomicU8::new(255);
static IN_TERMINAL:AtomicBool=AtomicBool::new(false);

struct Buffer { bytes:[u8;512],used:usize }
impl Buffer {
    const fn new()->Self{Self{bytes:[0;512],used:0}}
    fn bytes(&self)->&[u8]{&self.bytes[..self.used]}
    fn text(&self)->Result<&str,core::str::Utf8Error>{core::str::from_utf8(self.bytes())}
}
impl Write for Buffer {
    fn write_str(&mut self,text:&str)->fmt::Result{
        let end=match self.used.checked_add(text.len()){Some(end) if end<=self.bytes.len()=>end,_=>return Err(fmt::Error)};
        self.bytes[self.used..end].copy_from_slice(text.as_bytes());self.used=end;Ok(())
    }
}
fn output(bytes:&[u8]){
    let mut position=0;
    while position<bytes.len(){
        let count=unsafe{write(1,bytes[position..].as_ptr().cast(),bytes.len()-position)};
        if count<=0{unsafe{_Exit(103)}}
        position+=count as usize;
    }
}
fn text_or_terminal(buffer:&Buffer)->&str{
    match buffer.text(){Ok(text)=>text,Err(_)=>unsafe{_Exit(104)}}
}
fn json_string(output:&mut Buffer,text:&str)->fmt::Result{
    output.write_char('"')?;
    for ch in text.chars(){
        match ch{
            '"'=>output.write_str("\\\"")?, '\\'=>output.write_str("\\\\")?,
            '\n'=>output.write_str("\\n")?, '\r'=>output.write_str("\\r")?, '\t'=>output.write_str("\\t")?,
            ch if ch.is_ascii_control()=>return Err(fmt::Error),
            ch=>output.write_char(ch)?,
        }
    }
    output.write_char('"')
}
fn case_name(value:u8)->&'static str{
    match value{0=>"normal",1=>"result-expect",2=>"option-unwrap",3=>"option-expect",4=>"bounds",_=>"unexpected"}
}
#[panic_handler]
fn host_panic_terminal(info:&PanicInfo<'_>)->!{
    if IN_TERMINAL.swap(true,Ordering::SeqCst){unsafe{_Exit(102)}}
    let mut message=Buffer::new();
    // This formats the genuine PanicInfo built by the rebuilt core. It is a
    // test observation, not a substitute implementation of any core function.
    if write!(&mut message,"{}",info.message()).is_err(){unsafe{_Exit(105)}}
    let mut record=Buffer::new();
    if record.write_str("{\"case\":").is_err()
        || json_string(&mut record,case_name(CASE.load(Ordering::SeqCst))).is_err()
        || record.write_str(",\"terminal\":\"host-exit-101\",\"message\":").is_err()
        || json_string(&mut record,text_or_terminal(&message)).is_err()
        || record.write_str("}\n").is_err(){unsafe{_Exit(106)}}
    output(record.bytes());
    // Explicit HOST terminal. No unwind/resume, catch_unwind, syscall retry,
    // kernel debugcon/IRQ/GS/native panic or real McKernel operation occurs.
    unsafe{_Exit(101)}
}

// Non-inlined runtime inputs preserve real Option/Result and checked-index
// branches. The compiler must emit its genuine matching core dependencies.
#[inline(never)]
fn result_expect(value:Result<i32,i32>)->i32{value.expect("core-result")}
#[inline(never)]
fn option_unwrap(value:Option<i32>)->i32{value.unwrap()}
#[inline(never)]
fn option_expect(value:Option<i32>)->i32{value.expect("core-option")}
#[inline(never)]
fn checked_index(index:usize)->u8{let values=[5u8,7u8,11u8];values[index]}

fn normal()->c_int{
    let option=option_unwrap(black_box(Some(7)));
    let option_expected=option_expect(black_box(Some(11)));
    let result=result_expect(black_box(Ok(9)));
    let bound=checked_index(black_box(1));
    let mut formatted=Buffer::new();
    if write!(&mut formatted,"d={};x={:x};X={:X}",black_box(i32::MIN),black_box(-42i32),black_box(i32::MAX)).is_err(){return 107;}
    let mut record=Buffer::new();
    if write!(&mut record,"{{\"case\":\"normal\",\"option\":{},\"option_expect\":{},\"result\":{},\"bound\":{},\"fmt\":",option,option_expected,result,bound).is_err()
        || json_string(&mut record,text_or_terminal(&formatted)).is_err()
        || record.write_str("}\n").is_err(){return 108;}
    output(record.bytes());0
}

#[no_mangle]
pub unsafe extern "C" fn main(argc:c_int,argv:*const *const u8)->c_int{
    if argc!=2||argv.is_null(){return 64;}
    let mode=unsafe{*argv.add(1)};
    if mode.is_null(){return 64;}
    let first=unsafe{core::ptr::read_volatile(mode)};
    if unsafe{core::ptr::read_volatile(mode.add(1))}!=0||!(b'0'..=b'4').contains(&first){return 64;}
    let mode=first-b'0';CASE.store(mode,Ordering::SeqCst);
    match mode{
        0=>normal(),
        1=>{let _=result_expect(black_box(Err(-7)));109},
        2=>{let _=option_unwrap(black_box(None));110},
        3=>{let _=option_expect(black_box(None));111},
        4=>{let _=checked_index(black_box(3));112},
        _=>64,
    }
}
