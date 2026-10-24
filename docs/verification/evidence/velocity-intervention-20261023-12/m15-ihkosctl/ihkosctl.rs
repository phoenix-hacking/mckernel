// ihkosctl Rust successor, based on the current IHK CLI reference.
// COPYRIGHT FUJITSU LIMITED 2015-2016; Copyright (C) 2011-2017 RIKEN AICS.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reuses existing libihk ABI providers; no duplicated library parser/sysfs API.
#![no_std]
#![no_main]
#[cfg(not(all(target_os="linux",target_arch="x86_64")))]
compile_error!("Candidate bound to selected Linux x86_64 ABI");
use core::ffi::{c_char,c_int,c_long,c_uint,c_ulong,c_void};
use core::ptr::{null_mut,null};
macro_rules! c {($s:literal)=>{concat!($s,"\0").as_ptr().cast::<c_char>()};}
const BUILDID_CAPACITY:usize=env!("IHKOSCTL_BUILDID").len()+1;
const KMSG_SIZE:usize=(4<<20)-4096;
const MAX_CPUS:usize=1024;
const EINVAL:c_int=22;const ENOMEM:c_int=12;
const LOAD:c_ulong=0x112a00;const BOOT:c_ulong=0x112a01;const SHUTDOWN:c_ulong=0x112a02;
const KARGS:c_ulong=0x112a04;const ALLOC_CPU:c_ulong=0x112a10;const ALLOC_MEM:c_ulong=0x112a11;
const RESERVE_CPU:c_ulong=0x112a12;const RESERVE_MEM:c_ulong=0x112a13;
const CLEAR_KMSG:c_ulong=0x112a21;const ASSIGN_CPU:c_ulong=0x112a22;const RELEASE_CPU:c_ulong=0x112a23;
const ASSIGN_MEM:c_ulong=0x112a24;const RELEASE_MEM:c_ulong=0x112a25;const QUERY_CPU:c_ulong=0x112a26;
const QUERY_MEM:c_ulong=0x112a27;const SET_IKC:c_ulong=0x112a28;const GET_IKC:c_ulong=0x112a29;
const BUILDID:c_ulong=0x112a37;const NUM_CPUS:c_ulong=0x112a38;const DEBUG:c_ulong=0x122a00;
#[repr(C)]struct CpuReq{cpus:*mut c_int,num_cpus:c_int}
#[repr(C)]struct MemReq{sizes:*mut usize,numa_ids:*mut c_int,num_chunks:c_int,min_chunk_size:c_int,max_size_ratio_all:c_int,timeout:c_int}
#[repr(C)]struct IkcReq{src_cpus:*mut c_int,dst_cpus:*mut c_int,num_cpus:c_int}
#[repr(C)]struct GetoptOption{name:*const c_char,has_arg:c_int,flag:*mut c_int,val:c_int}
const _:[();16]=[();core::mem::size_of::<CpuReq>()];
const _:[();32]=[();core::mem::size_of::<MemReq>()];
const _:[();24]=[();core::mem::size_of::<IkcReq>()];
const _:[();32]=[();core::mem::size_of::<GetoptOption>()];
extern "C"{
 static mut stderr:*mut c_void;
 static mut optarg:*mut c_char;static mut optind:c_int;
 fn printf(fmt:*const c_char,...)->c_int;
 fn fprintf(stream:*mut c_void,fmt:*const c_char,...)->c_int;
 fn sprintf(out:*mut c_char,fmt:*const c_char,...)->c_int;
 fn strcmp(a:*const c_char,b:*const c_char)->c_int;
 fn strrchr(s:*const c_char,ch:c_int)->*mut c_char;
 fn atoi(s:*const c_char)->c_int;fn atol(s:*const c_char)->c_long;
 fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;
 fn strtoll(s:*const c_char,end:*mut *mut c_char,base:c_int)->i64;
 fn strtoul(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_ulong;
 fn tolower(ch:c_int)->c_int;
 fn calloc(n:usize,size:usize)->*mut c_void;fn malloc(size:usize)->*mut c_void;fn free(p:*mut c_void);
 fn open(path:*const c_char,flags:c_int,...)->c_int;fn close(fd:c_int)->c_int;
 fn ioctl(fd:c_int,request:c_ulong,...)->c_int;fn perror(label:*const c_char);
 fn __errno_location()->*mut c_int;fn abort()->!;
 fn getopt_long(argc:c_int,argv:*mut *mut c_char,opts:*const c_char,long:*const GetoptOption,index:*mut c_int)->c_int;
 fn time(out:*mut c_long)->c_long;fn localtime(value:*const c_long)->*mut c_void;
 fn strftime(out:*mut c_char,size:usize,fmt:*const c_char,tm:*const c_void)->usize;
 // Exact existing public libihk.h consumers; matched Rust providers owned centrally.
 fn ihk_os_get_status(index:c_int)->c_int;
 fn ihk_os_kmsg(index:c_int,out:*mut c_char,size:isize)->c_int;
 #[cfg(ihkosctl_memdump)]fn ihk_os_makedumpfile(index:c_int,path:*mut c_char,level:c_int,interactive:c_int)->c_int;
 // Existing private ABI contracts reused, not reimplemented in the CLI.
 fn ihklib_os_query_mem_sysfs(index:c_int,out:*mut c_char,size:isize,kind:*const c_char)->c_int;
 fn cpu_str2count(list:*mut c_char)->c_int;fn cpu_str2req(list:*mut c_char,count:c_int,req:*mut CpuReq)->c_int;
 fn cpu_req2str(req:*mut CpuReq)->*mut c_char;
 fn mem_str2count(list:*mut c_char)->c_int;fn mem_str2req(list:*mut c_char,req:*mut MemReq)->c_int;
 fn mem_req2str(req:*mut MemReq)->*mut c_char;
 fn ikc_str2count(list:*mut c_char)->c_int;fn ikc_str2req(list:*mut c_char,count:c_int,req:*mut IkcReq)->c_int;
 fn ikc_req2str(req:*mut IkcReq)->*mut c_char;
}
#[panic_handler]fn panic(_:&core::panic::PanicInfo<'_>)->!{unsafe{abort()}}
#[no_mangle]pub static mut __argc:c_int=0;
#[no_mangle]pub static mut __argv:*mut *mut c_char=null_mut();
unsafe fn arg(i:usize)->*mut c_char{*__argv.add(i)}
unsafe fn is(a:*const c_char,b:*const c_char)->bool{strcmp(a,b)==0}
unsafe fn failed(func:*const c_char,what:*const c_char)->c_int{printf(c!("%s,%s failed\n"),func,what);-1}
unsafe fn zero_mem()->MemReq{MemReq{sizes:null_mut(),numa_ids:null_mut(),num_chunks:0,min_chunk_size:0,max_size_ratio_all:0,timeout:0}}
unsafe fn usage(){
 let mut name=strrchr(arg(0),b'/' as c_int);if name.is_null(){name=arg(0)}else{name=name.add(1)}
 fprintf(stderr,c!("Usage: %s (dev #) (action)\n"),name);
 fprintf(stderr,c!("action:\n    load (kernel.img)\n    boot\n    shutdown\n    assign cpu|mem \n           cpu (cpu_list) \n           mem (size@NUMA) \n    release cpu|mem \n            cpu (cpu_list) \n            mem (size@NUMA) \n    set ikc_map (cpu_list:cpu+cpu_list:cpu+..) \n    get ikc_map\n    query [cpu|mem]\n    query_free_mem\n    kargs (kernel arg)\n    get status\n    kmsg\n    clear_kmsg\n    intr cpu irq_vector\n    ioctl (req) (arg)\n"));
 #[cfg(ihkosctl_memdump)]{fprintf(stderr,c!("    dump [-d level] [file]\n"));}
}
unsafe fn get_ikc_map()->c_int{
 // Original req was uninitialized on early failure, and never closed its fd.
 // Zero initialization and scoped close are explicit correctness proposals.
 let mut req=IkcReq{src_cpus:null_mut(),dst_cpus:null_mut(),num_cpus:0};let mut result=null_mut();
 let mut path=[0 as c_char;128];sprintf(path.as_mut_ptr(),c!("/dev/mcos%d"),atoi(arg(1)));
 let fd=open(path.as_ptr(),0);if fd<0{perror(c!("open"));return -1}
 let ret=(||{
  req.src_cpus=calloc(4,MAX_CPUS).cast();if req.src_cpus.is_null(){return failed(c!("do_get_ikc_map"),c!("allocate request space"))}
  req.dst_cpus=calloc(4,MAX_CPUS).cast();if req.dst_cpus.is_null(){return failed(c!("do_get_ikc_map"),c!("allocate request space"))}
  req.num_cpus=MAX_CPUS as c_int;
  if ioctl(fd,GET_IKC,&mut req as *mut IkcReq)!=0{return failed(c!("do_get_ikc_map"),c!("ioctl"))}
  result=ikc_req2str(&mut req);if result.is_null(){return failed(c!("do_get_ikc_map"),c!("build result string"))}
  printf(c!("%s\n"),result);0
 })();
 free(req.src_cpus.cast());free(req.dst_cpus.cast());free(result.cast());close(fd);ret
}
unsafe fn get(index:c_int)->c_int{
 if __argc<4{usage();return -1}
 if is(arg(3),c!("status")){
  let status=ihk_os_get_status(index);if status<0{return failed(c!("do_get_status"),c!("error: ihk_os_get_status"))}
  match status{0=>{printf(c!("INACTIVE\n"));},1=>{printf(c!("BOOTING\n"));},2=>{printf(c!("RUNNING\n"));},3=>{printf(c!("SHUTDOWN\n"));},4=>{printf(c!("PANIC\n"));},5=>{printf(c!("HUNGUP\n"));},6=>{printf(c!("FREEZING\n"));},7=>{printf(c!("FROZEN\n"));},_=>{}};0
 }else if is(arg(3),c!("ikc_map")){get_ikc_map()}
 else if is(arg(3),c!("buildid")){
  let mut path=[0 as c_char;128];let mut result=[0 as c_char;BUILDID_CAPACITY];sprintf(path.as_mut_ptr(),c!("/dev/mcos%d"),index);
  let fd=open(path.as_ptr(),0);if fd<0{return failed(c!("do_get_buildid"),c!("open"))}
  let ret=if ioctl(fd,BUILDID,result.as_mut_ptr())!=0{failed(c!("do_get_buildid"),c!("IHK_OS_GET_BUILDID"))}else{*result.as_mut_ptr().add(BUILDID_CAPACITY-1)=0;printf(c!("%s\n"),result.as_ptr());0};close(fd);ret
 }else{fprintf(stderr,c!("Unknown target : %s\n"),arg(3));usage();-1}
}
unsafe fn change_resources(fd:c_int,assign:bool)->c_int{
 if __argc<5{usage();return -1}
 let func=if assign{c!("do_assign")}else{c!("do_release")};
 let mut cpu=CpuReq{cpus:null_mut(),num_cpus:0};let mut mem=zero_mem();
 let ret=(||{
  if is(arg(3),c!("cpu")){
   let count=cpu_str2count(arg(4));if count<=0{return failed(func,c!("get num of requested cpus"))}
   cpu.cpus=calloc(4,count as usize).cast();if cpu.cpus.is_null(){return failed(func,c!("allocate request space"))}
   if cpu_str2req(arg(4),count,&mut cpu)<0{return failed(func,c!("parse provided cpulist string"))}
   let ret=ioctl(fd,if assign{ASSIGN_CPU}else{RELEASE_CPU},&cpu as *const CpuReq);
   if ret!=0{if assign{fprintf(stderr,c!("error: assigning CPUs: %s\n"),arg(4));}else{fprintf(stderr,c!("error: releasing CPUs: %s\n"),arg(4));}}ret
  }else if is(arg(3),c!("mem")){
   let all=!assign&&is(arg(4),c!("all"));
   let count=if all{
    if ioctl(fd,QUERY_MEM,&mut mem as *mut MemReq)!=0{fprintf(stderr,c!("error: get mem chunks\n"));}mem.num_chunks
   }else{let n=mem_str2count(arg(4));if n<=0{return failed(func,c!("get num of requested mems"))}n};
   mem.sizes=calloc(8,count as usize).cast();if mem.sizes.is_null(){return failed(func,c!("allocate request space"))}
   mem.numa_ids=calloc(4,count as usize).cast();if mem.numa_ids.is_null(){return failed(func,c!("allocate request space"))}
   if all{if ioctl(fd,QUERY_MEM,&mut mem as *mut MemReq)!=0{fprintf(stderr,c!("error: querying memory\n"));}}
   else if mem_str2req(arg(4),&mut mem)<0{return failed(func,c!("parse provided memlist string"))}
   let ret=ioctl(fd,if assign{ASSIGN_MEM}else{RELEASE_MEM},&mem as *const MemReq);
   if ret!=0{if assign{fprintf(stderr,c!("error: assiging memory: %s\n"),arg(4));}else{fprintf(stderr,c!("error: releasing memory: %s\n"),arg(4));}}ret
  }else{usage();-EINVAL}
 })();free(cpu.cpus.cast());free(mem.sizes.cast());free(mem.numa_ids.cast());ret
}
unsafe fn set(fd:c_int)->c_int{
 if __argc<4{usage();return -1}
 if !is(arg(3),c!("ikc_map")){fprintf(stderr,c!("Unknown target : %s\n"),arg(3));usage();return -1}
 if __argc<5{usage();return -1}
 let mut req=IkcReq{src_cpus:null_mut(),dst_cpus:null_mut(),num_cpus:0};
 let ret=(||{
  let count=ikc_str2count(arg(4));if count<=0{return failed(c!("do_set_ikc_map"),c!("get num of requested maps"))}
  req.src_cpus=calloc(4,count as usize).cast();if req.src_cpus.is_null(){return failed(c!("do_set_ikc_map"),c!("allocate request space"))}
  req.dst_cpus=calloc(4,count as usize).cast();if req.dst_cpus.is_null(){return failed(c!("do_set_ikc_map"),c!("allocate request space"))}
  if ikc_str2req(arg(4),count,&mut req)<0{return failed(c!("do_set_ikc_map"),c!("parse provided memlist string"))}
  let ret=ioctl(fd,SET_IKC,&req as *const IkcReq);if ret!=0{fprintf(stderr,c!("error: setting up IKC map: %s\n"),arg(4));}ret
 })();free(req.src_cpus.cast());free(req.dst_cpus.cast());ret
}
unsafe fn query(fd:c_int)->c_int{
 if __argc<4{usage();return -1}
 let mut cpu=CpuReq{cpus:null_mut(),num_cpus:0};let mut mem=zero_mem();let mut result=null_mut();
 let ret=(||{
  let ret;
  if is(arg(3),c!("cpu")){
   let count=ioctl(fd,NUM_CPUS);if count<0{fprintf(stderr,c!("error: querying num CPUs\n"));}
   cpu.num_cpus=count;cpu.cpus=calloc(4,count as usize).cast();if cpu.cpus.is_null(){return failed(c!("do_query"),c!("allocate request space"))}
   ret=ioctl(fd,QUERY_CPU,&mut cpu as *mut CpuReq);if ret!=0{fprintf(stderr,c!("error: querying CPUs\n"));}
   result=cpu_req2str(&mut cpu);
  }else if is(arg(3),c!("mem")){
   if ioctl(fd,QUERY_MEM,&mut mem as *mut MemReq)!=0{fprintf(stderr,c!("error: get mem chunks\n"));}
   let count=mem.num_chunks;mem.sizes=calloc(8,count as usize).cast();if mem.sizes.is_null(){return failed(c!("do_query"),c!("allocate request space"))}
   mem.numa_ids=calloc(4,count as usize).cast();if mem.numa_ids.is_null(){return failed(c!("do_query"),c!("allocate request space"))}
   ret=ioctl(fd,QUERY_MEM,&mut mem as *mut MemReq);if ret!=0{fprintf(stderr,c!("error: querying memory\n"));}
   result=mem_req2str(&mut mem);
  }else{usage();return -EINVAL}
  if result.is_null(){return failed(c!("do_query"),c!("build result string"))}
  if ret==0{printf(c!("%s\n"),result);}ret
 })();free(cpu.cpus.cast());free(mem.sizes.cast());free(mem.numa_ids.cast());free(result.cast());ret
}
unsafe fn kmsg(index:c_int)->c_int{
 // Keep the API capacity; one sentinel byte removes C's ret==capacity overflow.
 let buffer=calloc(KMSG_SIZE+1,1).cast::<c_char>();if buffer.is_null(){return -ENOMEM}
 let value=ihk_os_kmsg(index,buffer,KMSG_SIZE as isize);
 let ret=if value>=0{*buffer.add((value as usize).min(KMSG_SIZE))=0;printf(c!("%s\n"),buffer);0}else{fprintf(stderr,c!("error querying kmsg\n"));-EINVAL};free(buffer.cast());ret
}
#[cfg(ihkosctl_memdump)]unsafe fn dump(index:c_int)->c_int{
 let options=[GetoptOption{name:c!("interactive"),has_arg:0,flag:null_mut(),val:1},GetoptOption{name:null(),has_arg:0,flag:null_mut(),val:0}];
 let mut level=0;let mut interactive=0;
 loop{let option=getopt_long(__argc,__argv,c!("id:"),options.as_ptr(),null_mut());if option==-1{break}match option{1|105=>interactive=1,100=>level=atoi(optarg),_=>{fprintf(stderr,c!("dump [-d level] [-i|--interactive] [file]\n"));return 1}}}
 let mut path=[0 as c_char;4096];
 let file=if __argc>optind+2{arg((optind+2) as usize)}else{
  let stamp=time(null_mut());if stamp==-1{perror(c!("time"));return 1}
  let tm=localtime(&stamp);if tm.is_null(){perror(c!("localtime"));return 1}
  if strftime(path.as_mut_ptr(),path.len(),c!("mcdump_%Y%m%d_%H%M%S"),tm)==0{perror(c!("strftime"));return 1}path.as_mut_ptr()
 };ihk_os_makedumpfile(index,file,level,interactive)
}
#[cfg(not(ihkosctl_memdump))]unsafe fn dump(_:c_int)->c_int{fprintf(stderr,c!("dump is not supported.\n"));1}
unsafe fn fd_action(fd:c_int,action:*const c_char)->c_int{
 if is(action,c!("load")){
  let path=if __argc>3{arg(3) as *const c_char}else{c!("/home/shimosawa/mcos/mcos.image")};let r=ioctl(fd,LOAD,path as c_ulong);if r!=0{fprintf(stderr,c!("error: loading %s\n"),path);}r
 }else if is(action,c!("boot"))||is(action,c!("shutdown")){
  let boot=is(action,c!("boot"));let r=ioctl(fd,if boot{BOOT}else{SHUTDOWN},0 as c_int);if r!=0{if boot{fprintf(stderr,c!("error: booting\n"));}else{fprintf(stderr,c!("error: shutting down\n"));}}r
 }else if is(action,c!("alloc")){
  let n=if __argc>3{atoi(arg(3))}else{3};let mut size:c_ulong=0x10000000;
  if __argc>4{let mut tail=null_mut();size=strtoul(arg(4),&mut tail,0);let shift=match tolower(*tail as c_int){103=>30,109=>20,107=>10,_=>0};size=size.wrapping_shl(shift);}
  let r=ioctl(fd,ALLOC_CPU,n);if r!=0{fprintf(stderr,c!("error: allocating CPUs\n"));return r}
  let r=ioctl(fd,ALLOC_MEM,size);if r!=0{fprintf(stderr,c!("error: allocating memory\n"));}r
 }else if is(action,c!("reserve_cpu")){
  let n=__argc-3;if n<=0{printf(c!("No CPU is specified.\n"));return 1}
  let values=malloc((n as usize+1)*4).cast::<c_int>();if values.is_null(){return -ENOMEM}*values=n;for i in 0..n as usize{*values.add(i+1)=atoi(arg(i+3));}
  let r=ioctl(fd,RESERVE_CPU,values as c_ulong);if r!=0{fprintf(stderr,c!("error: reserving CPUs\n"));}free(values.cast());r
 }else if is(action,c!("reserve_mem")){
  if __argc<=4{printf(c!("Start or size is not specified.\n"));return 1}
  let values=[strtol(arg(3),null_mut(),16) as c_ulong,strtoll(arg(4),null_mut(),16) as c_ulong];let r=ioctl(fd,RESERVE_MEM,values.as_ptr() as c_ulong);if r!=0{fprintf(stderr,c!("error: reserving memory\n"));}r
 }else if is(action,c!("assign")){change_resources(fd,true)}
 else if is(action,c!("release")){change_resources(fd,false)}
 else if is(action,c!("set")){set(fd)}else if is(action,c!("query")){query(fd)}
 else if is(action,c!("query_free_mem")){
  let mut result=[0 as c_char;16384];if ihklib_os_query_mem_sysfs(atol(arg(1)) as c_int,result.as_mut_ptr(),result.len() as isize,c!("MemFree"))!=0{return failed(c!("do_query_free_mem"),c!("ihklib_os_query_mem_sysfs"))}
  *result.as_mut_ptr().add(result.len()-1)=0;printf(c!("%s\n"),result.as_ptr());0
 }else if is(action,c!("intr")){
  let mut v=0xf1;let mut cpu:c_int=0;if __argc>3{v=atoi(arg(3));}if __argc>4{cpu=atoi(arg(3));v=atoi(arg(4));}
  if ioctl(fd,DEBUG,cpu.wrapping_shl(8)|v)!=0{fprintf(stderr,c!("error: sending IRQ\n"));}0
 }else if is(action,c!("kargs")){
  if __argc<=3{fprintf(stderr,c!("error: no arg specified.\n"));return 1}
  let r=ioctl(fd,KARGS,arg(3));if r!=0{fprintf(stderr,c!("error: sending IRQ\n"));}r
 }else if is(action,c!("clear_kmsg")){
  let r=ioctl(fd,CLEAR_KMSG,0 as c_int);if r>=0{r}else{-*__errno_location()}
 }else if is(action,c!("ioctl")){
  if __argc<=4{fprintf(stderr,c!("No req or arg is specified.\n"));return 1}
  let req=strtol(arg(3),null_mut(),16) as c_uint;let value=strtoll(arg(4),null_mut(),16) as c_ulong;let r=ioctl(fd,req as c_ulong,value);if r!=0{fprintf(stderr,c!("error: ioctl\n"));}r
 }else{fprintf(stderr,c!("Unknown action : %s\n"),action);usage();0}
}
#[no_mangle]pub unsafe extern "C" fn main(argc:c_int,argv:*mut *mut c_char)->c_int{
 __argc=argc;__argv=argv;if argc<3{usage();return 1}
 let index=atoi(arg(1));if is(arg(2),c!("get")){return get(index)}else if is(arg(2),c!("dump")){return dump(index)}else if is(arg(2),c!("kmsg")){return kmsg(index)}
 let mut path=[0 as c_char;128];sprintf(path.as_mut_ptr(),c!("/dev/mcos%d"),index);let fd=open(path.as_ptr(),0);if fd<0{perror(c!("error: open failed"));return 1}
 let ret=fd_action(fd,arg(2));close(fd);ret
}
