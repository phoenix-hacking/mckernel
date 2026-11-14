// Functional McKernel OS/apps migration only; no security testing.
// Linux utilities are upstream dependencies; no project shell bodies are invoked.
use std::{fs,io::{self,Write},path::Path,process::{Command,Stdio},time::Duration};
#[derive(Clone,Debug,Default)] pub struct Output { pub code:i32,pub out:String,pub err:String }
impl Output { pub fn ok(&self)->bool {self.code==0} }
#[derive(Clone,Debug,PartialEq)] pub struct Call {pub program:String,pub args:Vec<String>,pub privileged:bool,pub input:Option<String>}
pub trait Host {
 fn call(&mut self,c:Call)->Output;
 fn read(&mut self,path:&str)->io::Result<String>;
 fn list(&mut self,path:&str)->io::Result<Vec<String>>;
 fn exists(&mut self,path:&str)->bool;
 fn file(&mut self,path:&str)->bool;
 fn sleep(&mut self,millis:u64);
 fn umask(&mut self,value:u32)->u32;
 fn diagnostic(&mut self,text:&str);
}
pub fn run(h:&mut dyn Host,p:&str,args:&[&str],root:bool)->Output { {let o=h.call(Call{program:p.into(),args:args.iter().map(|s|s.to_string()).collect(),privileged:root,input:None});if (p.ends_with("/ihkconfig")||p.ends_with("/ihkosctl")||p.ends_with("/ihkmond")||p=="chown")&&!o.err.is_empty(){h.diagnostic(o.err.trim_end())}o} }
pub fn write(h:&mut dyn Host,path:&str,text:&str)->bool {h.call(Call{program:"tee".into(),args:vec![path.into()],privileged:true,input:Some(text.into())}).ok()}
pub fn entries(h:&mut dyn Host,path:&str)->Vec<String> {let mut v=h.list(path).unwrap_or_default();v.sort();v}
pub fn devices(h:&mut dyn Host,prefix:&str)->Vec<String> {entries(h,"/dev").into_iter().filter(|s|s.starts_with(prefix)).map(|s|format!("/dev/{s}")).collect()}
pub fn loaded(h:&mut dyn Host,module:&str)->bool {h.read("/proc/modules").unwrap_or_default().lines().any(|s|s.split_whitespace().next()==Some(module))}
pub fn words(s:&str)->Vec<&str>{s.split_whitespace().collect()}
pub fn destroy(h:&mut dyn Host,ctl:&str,index:&str)->bool {for attempt in 0..5 {if run(h,ctl,&["0","destroy",index],true).ok(){return true}if attempt<4{h.sleep(250)}} false}
pub const IRQ_CONFIG:&str="/run/systemd/system/irqbalance.service.d/mckernel.conf";
pub const IRQ_SAVE:&str="/run/sysconfig/irqbalance_mck_affinities";
pub fn irq_restore(h:&mut dyn Host) {
 if !h.file(IRQ_CONFIG){return}
 for irq in entries(h,&format!("{IRQ_SAVE}/proc/irq")) {let f=format!("/proc/irq/{irq}/smp_affinity");if let Ok(s)=h.read(&format!("{IRQ_SAVE}{f}")){write(h,&f,&s);}}
 run(h,"rm",&["-rf",IRQ_CONFIG,"/run/sysconfig/irqbalance_mck",IRQ_SAVE],true);
 run(h,"rmdir",&["/run/systemd/system/irqbalance.service.d"],true);
 run(h,"systemctl",&["daemon-reload"],true);run(h,"systemctl",&["restart","irqbalance.service"],true);
}
pub struct Native {pub sudo:bool}
extern "C" {fn umask(mask:u32)->u32;fn geteuid()->u32;}
impl Native {pub fn new()->Self{Self{sudo:unsafe{geteuid()!=0}}}}
impl Host for Native {
 fn call(&mut self,c:Call)->Output {
  let mut command=if c.program=="insmod" {let mut q=Command::new("taskset");q.args(["-c","0"]);if c.privileged&&self.sudo{q.arg("sudo");}q.arg("insmod");q}else if c.privileged&&self.sudo {let mut q=Command::new("sudo");q.arg(&c.program);q}else{Command::new(&c.program)};
  command.args(&c.args).stdin(if c.input.is_some(){Stdio::piped()}else{Stdio::null()}).stdout(Stdio::piped()).stderr(Stdio::piped());
  match command.spawn(){Ok(mut child)=>{if let Some(input)=c.input {if let Some(mut stdin)=child.stdin.take(){if let Err(e)=stdin.write_all(input.as_bytes()){let _=child.wait();return Output{code:1,err:e.to_string(),..Output::default()}}}}
   match child.wait_with_output(){Ok(o)=>Output{code:o.status.code().unwrap_or(1),out:String::from_utf8_lossy(&o.stdout).into_owned(),err:String::from_utf8_lossy(&o.stderr).into_owned()},Err(e)=>Output{code:1,err:e.to_string(),..Output::default()}}},
   Err(e)=>Output{code:if e.kind()==io::ErrorKind::NotFound{127}else{126},err:e.to_string(),..Output::default()}}
 }
 fn read(&mut self,p:&str)->io::Result<String>{fs::read_to_string(p)}
 fn list(&mut self,p:&str)->io::Result<Vec<String>>{fs::read_dir(p)?.map(|v|v.map(|e|e.file_name().to_string_lossy().into_owned())).collect()}
 fn exists(&mut self,p:&str)->bool{Path::new(p).exists()} fn file(&mut self,p:&str)->bool{Path::new(p).is_file()}
 fn sleep(&mut self,ms:u64){std::thread::sleep(Duration::from_millis(ms))}
 fn umask(&mut self,v:u32)->u32{unsafe{umask(v)}}
 fn diagnostic(&mut self,t:&str){eprintln!("{t}")}
}
