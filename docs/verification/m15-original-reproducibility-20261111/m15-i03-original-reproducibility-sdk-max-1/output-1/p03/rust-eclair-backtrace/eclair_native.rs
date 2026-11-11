// Linux PTY transport. Only upstream libc interfaces; no Tcl/shell body.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use crate::eclair_backtrace::Terminal;
use std::{ffi::{c_char,c_int,c_ulong,c_void},fs::File,io::{self,Read,Write},os::{fd::{AsRawFd,FromRawFd},unix::process::CommandExt},process::{Child,Command,Stdio}};
#[link(name="util")]extern "C"{fn openpty(master:*mut c_int,slave:*mut c_int,name:*mut c_char,term:*const c_void,window:*const c_void)->c_int;}
extern "C"{fn setsid()->c_int;fn ioctl(fd:c_int,request:c_ulong,...)->c_int;}
pub struct Pty{master:File,child:Child,waited:bool}
impl Pty{pub fn spawn(executable:&str,kernel:&str)->io::Result<Self>{let(mut master,mut slave)=(-1,-1);if unsafe{openpty(&mut master,&mut slave,std::ptr::null_mut(),std::ptr::null(),std::ptr::null())}<0{return Err(io::Error::last_os_error())}let master=unsafe{File::from_raw_fd(master)};let slave=unsafe{File::from_raw_fd(slave)};
 let mut command=Command::new(executable);command.args(["-k",kernel,"-i","-l"]).stdin(Stdio::from(slave.try_clone()?)).stdout(Stdio::from(slave.try_clone()?)).stderr(Stdio::from(slave));
 // Closing the master in the child prevents an inherited writer from keeping the
 // PTY alive at EOF. FDs created by openpty predate Command's CLOEXEC discipline.
 let master_fd=master.as_raw_fd();unsafe{command.pre_exec(move||{if setsid()<0{return Err(io::Error::last_os_error())}if ioctl(0,0x540e as c_ulong,0 as c_int)<0{return Err(io::Error::last_os_error())}close_fd(master_fd);Ok(())});}
 let child=command.spawn()?;Ok(Self{master,child,waited:false})}}
extern "C"{fn close(fd:c_int)->c_int;}
unsafe fn close_fd(fd:c_int){close(fd);}
impl Terminal for Pty{
 fn read(&mut self)->io::Result<Vec<u8>>{let mut buf=vec![0u8;8192];loop{match self.master.read(&mut buf){Ok(n)=>{buf.truncate(n);return Ok(buf)},Err(e)if e.kind()==io::ErrorKind::Interrupted=>continue,Err(e)if e.raw_os_error()==Some(5)=>return Ok(Vec::new()),Err(e)=>return Err(e)}}}
 fn send(&mut self,text:&str)->io::Result<()>{self.master.write_all(text.as_bytes())}
 fn transcript(&mut self,b:&[u8])->io::Result<()>{let mut out=io::stdout().lock();out.write_all(b)?;out.flush()}
 fn wait(&mut self)->io::Result<()>{if !self.waited{self.child.wait()?;self.waited=true;}Ok(())}
}
