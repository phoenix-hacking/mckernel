// ihkmond Rust daemon; original Copyright (C) 2017 Masamichi Takagi.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private Linux x86_64 source candidate. No project C callbacks or shell body.
#[cfg(not(all(target_os="linux",target_arch="x86_64")))]
compile_error!("Candidate is bound to selected Linux x86_64 user ABI");
use std::collections::VecDeque;
use std::ffi::{CStr,CString};
use std::fs::{self,File,OpenOptions,DirBuilder};
use std::io::{Read,Write};
use std::os::raw::{c_char,c_int,c_ulong,c_void};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{DirBuilderExt,OpenOptionsExt};
use std::path::Path;
use std::sync::{Arc,Mutex,Condvar};
use std::sync::atomic::{AtomicBool,AtomicI32,Ordering};
use std::thread::{self,JoinHandle};
use std::time::{Duration,Instant};
macro_rules! c{($s:literal)=>{concat!($s,"\0").as_ptr().cast::<c_char>()};}
const KMSG_SIZE:usize=(4<<20)-4096;const SLOT:usize=1<<20;const SLOTS:usize=64;
const TMP:&str=env!("IHKMOND_TMP");const POLL_MS:c_int=250;
const GET_KMSG:c_ulong=0x112908;const READ_KMSG:c_ulong=0x112909;
const RELEASE_KMSG:c_ulong=0x11290a;const DETECT:c_ulong=0x11290f;
#[repr(C)]struct GetKmsg{os_index:c_int,handle:*mut c_void}
#[repr(C)]struct ReadKmsg{handle:*mut c_void,shift:c_int,buf:*mut u8}
#[repr(C,packed)]#[derive(Copy,Clone)]struct Event{events:u32,data:u64}
impl Event{fn fd(self)->c_int{self.data as c_int}fn input(fd:c_int)->Self{Self{events:1,data:fd as u32 as u64}}}
#[repr(C)]struct SigSet{words:[u64;16]}
#[repr(C)]struct GetoptOption{name:*const c_char,has_arg:c_int,flag:*mut c_int,val:c_int}
const _:[();16]=[();std::mem::size_of::<GetKmsg>()];
const _:[();24]=[();std::mem::size_of::<ReadKmsg>()];
const _:[();12]=[();std::mem::size_of::<Event>()];
const _:[();128]=[();std::mem::size_of::<SigSet>()];
const _:[();32]=[();std::mem::size_of::<GetoptOption>()];
extern "C"{
 fn ihklib_device_open(index:c_int)->c_int;fn ihk_os_get_eventfd(index:c_int,kind:c_int)->c_int;
 fn daemon(nochdir:c_int,noclose:c_int)->c_int;
 fn epoll_create(size:c_int)->c_int;fn epoll_ctl(ep:c_int,op:c_int,fd:c_int,event:*const Event)->c_int;
 fn epoll_wait(ep:c_int,events:*mut Event,max:c_int,timeout:c_int)->c_int;
 fn eventfd(initial:u32,flags:c_int)->c_int;fn read(fd:c_int,out:*mut c_void,size:usize)->isize;
 fn write(fd:c_int,buf:*const c_void,size:usize)->isize;fn close(fd:c_int)->c_int;
 fn open(path:*const c_char,flags:c_int,...)->c_int;fn ioctl(fd:c_int,req:c_ulong,...)->c_int;
 fn stat(path:*const c_char,out:*mut c_void)->c_int;fn __errno_location()->*mut c_int;
 fn strerror(error:c_int)->*const c_char;
 fn geteuid()->u32;fn sigemptyset(set:*mut SigSet)->c_int;fn sigaddset(set:*mut SigSet,sig:c_int)->c_int;
 fn pthread_sigmask(how:c_int,set:*const SigSet,old:*mut SigSet)->c_int;
 fn signalfd(fd:c_int,set:*const SigSet,flags:c_int)->c_int;
 fn openlog(id:*const c_char,option:c_int,facility:c_int);fn closelog();fn syslog(priority:c_int,format:*const c_char,...);
 fn printf(format:*const c_char,...)->c_int;fn atoi(value:*const c_char)->c_int;
 fn getopt_long(argc:c_int,argv:*mut *mut c_char,opts:*const c_char,long:*const GetoptOption,index:*mut c_int)->c_int;
 static mut optarg:*mut c_char;
 fn udev_new()->*mut c_void;fn udev_unref(ctx:*mut c_void)->*mut c_void;
 fn udev_monitor_new_from_netlink(ctx:*mut c_void,name:*const c_char)->*mut c_void;
 fn udev_monitor_filter_add_match_subsystem_devtype(mon:*mut c_void,sub:*const c_char,dev:*const c_char)->c_int;
 fn udev_monitor_enable_receiving(mon:*mut c_void)->c_int;fn udev_monitor_get_fd(mon:*mut c_void)->c_int;
 fn udev_monitor_receive_device(mon:*mut c_void)->*mut c_void;fn udev_monitor_unref(mon:*mut c_void)->*mut c_void;
 fn udev_device_get_devnode(dev:*mut c_void)->*const c_char;fn udev_device_get_action(dev:*mut c_void)->*const c_char;
 fn udev_device_unref(dev:*mut c_void)->*mut c_void;
}
fn errno()->i32{unsafe{*__errno_location()}}
fn error_text(error:i32)->String{unsafe{CStr::from_ptr(strerror(error)).to_string_lossy().into_owned()}}
fn kprint(message:&str){kprint_bytes(message.as_bytes())}
fn kprint_bytes(message:&[u8]){
 if unsafe{geteuid()}!=0{return}let fd=unsafe{open(c!("/dev/kmsg"),1)};if fd<0{return}
 let mut bytes=message[..message.len().min(3839)].to_vec();bytes.push(0);let mut offset=0;
 while offset<bytes.len(){let n=unsafe{write(fd,bytes[offset..].as_ptr().cast(),bytes.len()-offset)};if n<=0{break}offset+=n as usize;}
 unsafe{close(fd);}
}
fn fail(code:i32,message:&str)->i32{kprint(message);code}
struct Fd(i32);impl Fd{fn new(value:i32,message:&str)->Result<Self,i32>{if value<0{Err(fail(255,message))}else{Ok(Self(value))}}}
impl Drop for Fd{fn drop(&mut self){unsafe{close(self.0);}}}
fn notify(fd:i32)->Result<(),i32>{let value=1u64;let n=unsafe{write(fd,(&value as *const u64).cast(),8)};if n!=8{Err(fail(255,"write failed\n"))}else{Ok(())}}
fn reap(fd:i32)->Result<(),i32>{let mut value=0u64;let n=unsafe{read(fd,(&mut value as *mut u64).cast(),8)};if n==0{Err(fail(-1,"EOF detected\n"))}else if n<0{Err(fail(-1,&format!("error: {}\n",error_text(errno()))))}else{Ok(())}}
fn add(ep:i32,fd:i32)->Result<(),i32>{let event=Event::input(fd);if unsafe{epoll_ctl(ep,1,fd,&event)}!=0{Err(fail(-22,"epoll_ctl failed\n"))}else{Ok(())}}
fn del(ep:i32,fd:i32)->Result<(),i32>{if unsafe{epoll_ctl(ep,2,fd,std::ptr::null())}!=0{Err(fail(-22,"epoll_ctl failed\n"))}else{Ok(())}}
fn wait(ep:i32,events:&mut [Event],timeout:i32)->Result<usize,i32>{loop{let n=unsafe{epoll_wait(ep,events.as_mut_ptr(),events.len() as i32,timeout)};if n<0&&errno()==4{continue}if n<0{return Err(fail(-22,"epoll_wait failed\n"))}return Ok(n as usize)}}
struct State{added:bool,stopping:bool}
struct Life{state:Mutex<State>,wake:Condvar,removed:Fd,finished:AtomicBool,status:AtomicI32}
impl Life{
 fn new()->Result<Arc<Self>,i32>{Ok(Arc::new(Self{state:Mutex::new(State{added:false,stopping:false}),wake:Condvar::new(),removed:Fd::new(unsafe{eventfd(0,0)},"eventfd failed\n")?,finished:AtomicBool::new(false),status:AtomicI32::new(0)}))}
 fn wait_add(&self)->bool{let mut state=self.state.lock().unwrap_or_else(|e|e.into_inner());while !state.added&&!state.stopping{state=self.wake.wait(state).unwrap_or_else(|e|e.into_inner())}if state.stopping{return false}state.added=false;true}
 fn added(&self){let mut s=self.state.lock().unwrap_or_else(|e|e.into_inner());s.added=true;self.wake.notify_one();}
 fn stopping(&self)->bool{self.state.lock().unwrap_or_else(|e|e.into_inner()).stopping}
 fn stop(&self){{let mut s=self.state.lock().unwrap_or_else(|e|e.into_inner());s.stopping=true;self.wake.notify_all();}let _=notify(self.removed.0);}
}
#[derive(Clone)]struct Args{life:Arc<Life>,done:Arc<Fd>,dev:i32,os:i32,facility:i32,logid:Arc<CString>,interval:i32}
struct Worker{life:Arc<Life>,thread:Option<JoinHandle<i32>>}
struct Workers{items:Vec<Worker>,done:Arc<Fd>}
impl Workers{
 fn new()->Result<Self,i32>{Ok(Self{items:Vec::new(),done:Arc::new(Fd::new(unsafe{eventfd(0,0)},"eventfd failed\n")?)})}
 fn spawn(&mut self,monitor:bool,facility:i32,logid:Arc<CString>,interval:i32)->Result<(),i32>{
  let life=Life::new()?;let args=Args{life:life.clone(),done:self.done.clone(),dev:0,os:0,facility,logid,interval};
  let name=if monitor{"ihkmond-hungup"}else{"ihkmond-kmsg"};
  let thread=thread::Builder::new().name(name.to_string()).spawn(move||{
   let ret=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||if monitor{detect_hungup(&args)}else{redirect_kmsg(&args)})).unwrap_or(255);
   args.life.status.store(ret,Ordering::Release);args.life.finished.store(true,Ordering::Release);let _=notify(args.done.0);ret
  }).map_err(|e|fail(255,&format!("pthread_create returned {}\n",error_text(e.raw_os_error().unwrap_or(11)))))?;
  self.items.push(Worker{life,thread:Some(thread)});Ok(())
 }
 fn add(&self){for w in &self.items{w.life.added();}}
 fn remove(&self)->Result<(),i32>{for w in &self.items{notify(w.life.removed.0)?}Ok(())}
 fn failure(&self)->Option<i32>{self.items.iter().find(|w|w.life.finished.load(Ordering::Acquire)).map(|w|{let n=w.life.status.load(Ordering::Acquire);if n==0{255}else{n}})}
 fn finish(&mut self)->i32{for w in &self.items{if w.thread.is_some(){w.life.stop();}}let mut ret=0;for w in &mut self.items{if let Some(t)=w.thread.take(){let n=t.join().unwrap_or(255);if ret==0&&n!=0{ret=n}}}ret}
}
impl Drop for Workers{fn drop(&mut self){self.finish();}}
fn detect_hungup(args:&Args)->i32{fn run(args:&Args)->Result<(),i32>{
 let ep=Fd::new(unsafe{epoll_create(1)},"epoll_create failed\n")?;add(ep.0,args.life.removed.0)?;
 let path=CString::new(format!("/dev/mcos{}",args.os)).unwrap();
 while args.life.wait_add(){
  let mut attempts=0;
  // stat's output is opaque and unused. 256 aligned bytes cover Linux x86_64
  // struct stat; fixture asserts the real system struct fits this binding.
  #[repr(C,align(8))]struct StatBuffer([u8;256]);let mut st=StatBuffer([0;256]);
  while unsafe{stat(path.as_ptr(),(&mut st as *mut StatBuffer).cast())}!=0{
   if args.life.stopping(){return Ok(())}let e=errno();if e!=2{return Err(fail(-e,"/dev/mcosX access failed\n"))}thread::sleep(Duration::from_micros(200));attempts+=1;if attempts>50_000{return Err(fail(-110,"/dev/mcosX create timeout\n"))}
  }
  'active:loop{
   if args.life.stopping(){break}
   // Preserve the reference's selected dev/os arguments (both0 in supported profile).
   let value=unsafe{ihklib_device_open(args.os)};if value<0{return Err(value)}let dev=Fd(value);unsafe{ioctl(dev.0,DETECT,args.dev as c_ulong);}drop(dev);
   let start=Instant::now();let duration=if args.interval<0{None}else{Some(Duration::from_secs(args.interval as u64))};
   loop{
    if args.life.stopping(){break 'active}
    let timeout=duration.map(|d|d.saturating_sub(start.elapsed()).as_millis().min(POLL_MS as u128) as i32).unwrap_or(POLL_MS);
    let mut events=[Event{events:0,data:0};1];let n=wait(ep.0,&mut events,timeout)?;
    if n==0{if duration.is_some_and(|d|start.elapsed()>=d){break}continue}
    if events[0].fd()==args.life.removed.0{let _=reap(args.life.removed.0);break 'active}
   }
  }
 }
 Ok(())}run(args).err().unwrap_or(0)}
struct Lease{dev:i32,os:i32,handle:*mut c_void,attempted:bool}
impl Lease{
 fn get(dev_index:i32,os:i32)->Result<Self,i32>{let value=unsafe{ihklib_device_open(dev_index)};if value<0{return Err(fail(value,&format!("ihklib_device_open returned {value}\n")))}let dev=Fd(value);let mut desc=GetKmsg{os_index:os,handle:std::ptr::null_mut()};let ret=unsafe{ioctl(dev.0,GET_KMSG,&mut desc as *mut GetKmsg)};if ret<0{return Err(fail(ret,&format!("IHK_DEVICE_GET_KMSG_BUF returned {ret}\n")))}Ok(Self{dev:dev_index,os,handle:desc.handle,attempted:false})}
 fn release(&mut self)->Result<(),i32>{if self.attempted{return Ok(())}self.attempted=true;let value=unsafe{ihklib_device_open(self.dev)};if value<0{kprint(&format!("unreleased kmsg lease dev={} os={} handle={:p}\n",self.dev,self.os,self.handle));return Err(fail(value,"ihklib_device_open failed releasing kmsg lease\n"))}let dev=Fd(value);let ret=unsafe{ioctl(dev.0,RELEASE_KMSG,self.handle)};if ret!=0{kprint(&format!("unreleased kmsg lease dev={} os={} handle={:p}\n",self.dev,self.os,self.handle));Err(fail(ret,"IHK_DEVICE_RELEASE_KMSG_BUF failed\n"))}else{Ok(())}}
 fn bytes(&self)->Result<Vec<u8>,i32>{let value=unsafe{ihklib_device_open(self.dev)};if value<0{return Err(fail(value,&format!("ihklib_device_open returned {value}\n")))}let dev=Fd(value);let mut buf=vec![0u8;KMSG_SIZE+1];let desc=ReadKmsg{handle:self.handle,shift:1,buf:buf.as_mut_ptr()};let n=unsafe{ioctl(dev.0,READ_KMSG,&desc as *const ReadKmsg)};if n<0||n as usize>KMSG_SIZE{return Err(fail(if n<0{n}else{-22},"ioctl failed\n"))}buf.truncate(n as usize);Ok(buf)}
}
impl Drop for Lease{fn drop(&mut self){if !self.attempted{let _=self.release();}}}
struct Ring{files:Vec<Option<File>>,sizes:[usize;SLOTS],order:VecDeque<usize>,prod:usize,os:i32}
impl Ring{
 fn new(os:i32)->Self{Self{files:(0..SLOTS).map(|_|None).collect(),sizes:[0;SLOTS],order:VecDeque::new(),prod:0,os}}
 fn append(&mut self,bytes:&[u8])->Result<(),i32>{
  // Normal reads retain the reference's rotate-before-write policy. Oversized
  // reads are chunked to prevent a >1MiB slot and reference truncation/loss.
  for part in bytes.chunks(SLOT){if part.is_empty(){continue}let rotate=self.sizes[self.prod]+part.len()>SLOT;if rotate{self.prod=(self.prod+1)%SLOTS;self.files[self.prod]=None;}
   if self.files[self.prod].is_none(){let root=Path::new(TMP);for path in [root.to_path_buf(),root.join(format!("mcos{}",self.os))]{if let Err(e)=DirBuilder::new().mode(0o755).create(&path){if e.kind()!=std::io::ErrorKind::AlreadyExists{return Err(fail(-e.raw_os_error().unwrap_or(22),"mkdir failed\n"))}}}
    let path=root.join(format!("mcos{}/kmsg{}",self.os,self.prod));let file=OpenOptions::new().read(true).write(true).create(true).truncate(true).mode(0o666).open(path).map_err(|_|fail(-22,"fopen failed\n"))?;self.files[self.prod]=Some(file);self.sizes[self.prod]=0;
    let current=self.prod;self.order.retain(|n|*n!=current);self.order.push_back(current);
   }
   self.files[self.prod].as_mut().unwrap().write_all(part).map_err(|_|fail(-22,"fwrite failed\n"))?;self.sizes[self.prod]+=part.len();
  }Ok(())
 }
 fn syslog(&mut self)->Result<(),i32>{use std::io::{Seek,SeekFrom};
  while let Some(index)=self.order.pop_front(){if let Some(mut file)=self.files[index].take(){file.seek(SeekFrom::Start(0)).map_err(|_|fail(-22,"rewind failed\n"))?;let mut bytes=Vec::new();file.read_to_end(&mut bytes).map_err(|_|fail(-22,"ferror()\n"))?;drop(file);for line in bytes.split(|b|*b==b'\n'){if line.is_empty(){continue}let end=line.iter().position(|b|*b==0).unwrap_or(line.len());if end==0{continue}let text=CString::new(&line[..end]).unwrap();unsafe{syslog(6,c!("%s"),text.as_ptr());}thread::sleep(Duration::from_micros(200));}}}Ok(())
 }
}
struct LogGuard;impl Drop for LogGuard{fn drop(&mut self){unsafe{closelog();}}}
fn consume(lease:&Lease,ring:&mut Ring,flush:bool)->Result<(),i32>{let bytes=lease.bytes().map_err(|n|fail(-22,&format!("fwrite_kmsg returned {n}\n")))?;
 #[cfg(ihkmond_kmsg_redirect)]{if bytes.is_empty(){return Ok(())}for line in bytes.split(|b|*b==b'\n'){let end=line.iter().position(|b|*b==0).unwrap_or(line.len());let mut text=b"<3>".to_vec();text.extend_from_slice(&line[..end]);kprint_bytes(&text);thread::sleep(Duration::from_micros(200));}let _=(ring,flush);}
 #[cfg(not(ihkmond_kmsg_redirect))]{ring.append(&bytes).map_err(|n|fail(-22,&format!("fwrite_kmsg returned {n}\n")))?;if flush{ring.syslog().map_err(|n|fail(n,&format!("syslog_kmsg returned {n}\n")))?;}}
 Ok(())}
fn redirect_kmsg(args:&Args)->i32{fn run(args:&Args)->Result<(),i32>{
 unsafe{openlog(args.logid.as_ptr(),1,args.facility);}let _log=LogGuard;
 let ep=Fd::new(unsafe{epoll_create(1)},"epoll_create failed\n")?;add(ep.0,args.life.removed.0)?;let mut ring=Ring::new(args.os);
 while args.life.wait_add(){
  let mut lease=Lease::get(args.dev,args.os)?;
  let value=unsafe{ihk_os_get_eventfd(args.os,101)};if value<0{return Err(fail(-22,"ihk_os_get_eventfd\n"))}let kmsg=Fd(value);add(ep.0,kmsg.0)?;
  let value=unsafe{ihk_os_get_eventfd(args.os,2)};if value<0{return Err(fail(-22,"ihk_os_get_eventfd\n"))}let status=Fd(value);add(ep.0,status.0)?;
  loop{
   if args.life.stopping(){consume(&lease,&mut ring,true)?;break}
   let mut events=[Event{events:0,data:0};2];let n=wait(ep.0,&mut events,POLL_MS)?;let mut removed=false;
   for event in &events[..n]{let fd=(*event).fd();let _=reap(fd);if fd==kmsg.0{consume(&lease,&mut ring,false)?;}else if fd==status.0{consume(&lease,&mut ring,true)?;}else if fd==args.life.removed.0{consume(&lease,&mut ring,true)?;removed=true;break}}
   if removed{break}
  }
  // Release before closing notification endpoints, as in the reference. RAII
  // also releases once on every partial setup/error path. Failed release is
  // reported, not silently retried or credited as restoration.
  lease.release()?;del(ep.0,kmsg.0)?;del(ep.0,status.0)?;drop(kmsg);drop(status);
 }
 Ok(())}run(args).err().unwrap_or(0)}
struct SignalMask{old:SigSet,fd:Fd}
impl SignalMask{fn new()->Result<Self,i32>{unsafe{let mut set=SigSet{words:[0;16]};let mut old=SigSet{words:[0;16]};sigemptyset(&mut set);sigaddset(&mut set,2);sigaddset(&mut set,15);let ret=pthread_sigmask(0,&set,&mut old);if ret!=0{return Err(fail(255,"pthread_sigmask failed\n"))}let fd=signalfd(-1,&set,0);if fd<0{pthread_sigmask(2,&old,std::ptr::null_mut());return Err(fail(255,"signalfd failed\n"))}Ok(Self{old,fd:Fd(fd)})}}}
impl Drop for SignalMask{fn drop(&mut self){unsafe{pthread_sigmask(2,&self.old,std::ptr::null_mut());}}}
struct Udev(*mut c_void);impl Drop for Udev{fn drop(&mut self){unsafe{udev_unref(self.0);}}}
struct Monitor(*mut c_void);impl Drop for Monitor{fn drop(&mut self){unsafe{udev_monitor_unref(self.0);}}}
struct Device(*mut c_void);impl Drop for Device{fn drop(&mut self){unsafe{udev_device_unref(self.0);}}}
fn os_zero(node:&[u8])->bool{let name=node.rsplit(|b|*b==b'/').next().unwrap_or(node);name==b"mcos0"}
fn supervise(facility:i32,enable_kmsg:bool,interval:i32,logid:Arc<CString>)->Result<(),i32>{
 let signals=SignalMask::new()?;let mut workers=Workers::new()?;
 if interval!=-1{workers.spawn(true,facility,logid.clone(),interval)?}if enable_kmsg{workers.spawn(false,facility,logid,interval)?}
 let value=unsafe{udev_new()};if value.is_null(){return Err(fail(255,"udev_new failed\n"))}let udev=Udev(value);
 let value=unsafe{udev_monitor_new_from_netlink(udev.0,c!("udev"))};if value.is_null(){return Err(fail(255,"udev_monitor_new_from_netlink failed\n"))}let monitor=Monitor(value);
 let ret=unsafe{udev_monitor_filter_add_match_subsystem_devtype(monitor.0,c!("mcos"),std::ptr::null())};if ret<0{return Err(fail(255,&format!("udev_monitor_filter_add_match_subsystem_devtype returned {}\n",error_text(-ret))))}
 let ret=unsafe{udev_monitor_enable_receiving(monitor.0)};if ret<0{return Err(fail(255,&format!("udev_monitor_enable_receiving {}\n",error_text(-ret))))}
 let monfd=unsafe{udev_monitor_get_fd(monitor.0)};if monfd<0{return Err(fail(255,&format!("udev_monitor_get_fd returned {}\n",error_text(-monfd))))}
 let ep=Fd::new(unsafe{epoll_create(1)},"epoll_create failed\n")?;add(ep.0,monfd).map_err(|_|255)?;add(ep.0,signals.fd.0).map_err(|_|255)?;add(ep.0,workers.done.0).map_err(|_|255)?;
 let result=(||{loop{
  if let Some(ret)=workers.failure(){return Err(ret)}
  let mut events=[Event{events:0,data:0};3];let n=wait(ep.0,&mut events,POLL_MS)?;
  for event in &events[..n]{let fd=(*event).fd();if fd==signals.fd.0{let mut info=[0u8;128];if unsafe{read(fd,info.as_mut_ptr().cast(),info.len())}!=128{return Err(fail(255,"signalfd read failed\n"))}return Ok(())}
   if fd==workers.done.0{let _=reap(fd);if let Some(ret)=workers.failure(){return Err(ret)}continue}
   if fd!=monfd{continue}let value=unsafe{udev_monitor_receive_device(monitor.0)};if value.is_null(){return Err(fail(255,"udev_monitor_receive_device failed\n"))}let device=Device(value);
   let node=unsafe{udev_device_get_devnode(device.0)};let action=unsafe{udev_device_get_action(device.0)};
   if node.is_null()||action.is_null(){kprint("invalid mcos udev event\n");continue}
   if !os_zero(unsafe{CStr::from_ptr(node).to_bytes()}){continue}
   match unsafe{CStr::from_ptr(action).to_bytes()}{b"add"=>workers.add(),b"remove"=>workers.remove()?,_=>{}}
  }
 }})();let worker_result=workers.finish();if worker_result!=0&&result.is_ok(){Err(worker_result)}else{result}
}
fn usage(name:&CStr){unsafe{printf(c!("%s [--help|-?] [-f <facility_name>] [-k <redirect_kmsg>] [-n <detect_hungup>]\n--help            \tShow usage\n-f <facility_name>\tUse <facility_name> when redirecting kmsg by using syslog()\n-k <redirect_kmsg>\t1: Redirect kmsg\n                  \t0: Otherwise\n-i <monitor_interval>\t!=-1: Polling interval (in second) for detecting hungup\n                  \t-1: Don't detect hungup\n"),name.as_ptr());}}
fn run()->i32{
 let strings:Vec<CString>=std::env::args_os().map(|a|CString::new(a.as_os_str().as_bytes()).unwrap()).collect();let mut argv:Vec<*mut c_char>=strings.iter().map(|s|s.as_ptr() as *mut c_char).chain(std::iter::once(std::ptr::null_mut())).collect();
 let basename=strings[0].as_bytes().rsplit(|b|*b==b'/').next().unwrap_or(b"ihkmond");let logid=Arc::new(CString::new(basename).unwrap());
 let options=[GetoptOption{name:c!("help"),has_arg:0,flag:std::ptr::null_mut(),val:63},GetoptOption{name:std::ptr::null(),has_arg:0,flag:std::ptr::null_mut(),val:0}];
 let mut facility=176;let mut kmsg=1;let mut interval=600;
 loop{let opt=unsafe{getopt_long(strings.len() as i32,argv.as_mut_ptr(),c!("f:k:i:"),options.as_ptr(),std::ptr::null_mut())};if opt==-1{break}match opt{102=>{let bytes=unsafe{CStr::from_ptr(optarg).to_bytes()};let found=(0..8).find(|n|bytes==format!("LOG_LOCAL{n}").as_bytes());if let Some(n)=found{facility=128+n*8}else{return fail(255,"Unknown facility\n")}},107=>kmsg=unsafe{atoi(optarg)},105=>interval=unsafe{atoi(optarg)},_=>usage(&logid)}}
 let ret=unsafe{daemon(1,if cfg!(ihkmond_debug){1}else{0})};if ret!=0{return -errno()}
 supervise(facility,kmsg!=0,interval,logid).err().unwrap_or(0)
}
#[cfg(ihkmond_fixture)]fn fixture_ring()->i32{
 fn body()->Result<(),i32>{let mut lease=Lease::get(0,0)?;let mut ring=Ring::new(0);for _ in 0..3{ring.append(&lease.bytes()?)?;}ring.syslog()?;lease.release()?;Ok(())}body().err().unwrap_or(0)
}
fn main(){
 #[cfg(ihkmond_fixture)]{if std::env::var_os("IHKMOND_HELPER").is_some(){std::process::exit(fixture_ring());}}
 std::process::exit(run());
}
