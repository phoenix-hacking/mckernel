// Source-only owned fake backend. No actual command, module, proc/sys or signal effects.
mod platform; mod config; mod reboot; mod stop;
use platform::*;use std::{collections::BTreeMap,io};
#[derive(Default)]struct Fake{files:BTreeMap<String,String>,dirs:BTreeMap<String,Vec<String>>,calls:Vec<Call>,sleeps:Vec<u64>,messages:Vec<String>,fail:Option<(String,Vec<String>)>,destroy_failures:usize,mask:u32}
impl Fake{fn ready()->Self{let mut h=Self::default();h.files.insert("/proc/modules".into(),"ihk 1\nihk_smp_x86_64 1\nmcctrl 1\n".into());h.files.insert("/sbin/rmmod".into(),String::new());h}
 fn saw(&self,p:&str,args:&[&str])->bool{self.calls.iter().any(|c|c.program==p&&c.args==args)} }
impl Host for Fake{
 fn call(&mut self,c:Call)->Output{self.calls.push(c.clone());if self.fail.as_ref().map_or(false,|(p,a)|*p==c.program&&*a==c.args){return Output{code:1,..Output::default()}}
 if c.args.get(1).map(String::as_str)==Some("destroy")&&self.destroy_failures>0{self.destroy_failures-=1;return Output{code:1,..Output::default()}}
 let mut o=Output::default();match c.program.as_str(){"systemctl" if c.args.first().map(String::as_str)==Some("status")=>o.code=1,"pidof"|"getenforce"=>o.code=1,"id"=>o.out="tester\n".into(),"lscpu" if c.args==["--parse"]=>o.out="# CPU,Core,Socket,Node\n0,0,0,0\n1,1,0,0\n2,2,0,0\n3,3,0,0\n4,4,1,1\n".into(),"tee"=>{self.files.insert(c.args[0].clone(),c.input.unwrap_or_default());},_=>{if c.args==["0","get","buildid"]{o.out="fixture-build\n".into()}if c.args==["0","query","cpu"]{o.out="2-3\n".into()}}}o}
 fn read(&mut self,p:&str)->io::Result<String>{self.files.get(p).cloned().ok_or_else(||io::ErrorKind::NotFound.into())}
 fn list(&mut self,p:&str)->io::Result<Vec<String>>{Ok(self.dirs.get(p).cloned().unwrap_or_default())}
 fn exists(&mut self,p:&str)->bool{self.files.contains_key(p)||self.dirs.contains_key(p)}fn file(&mut self,p:&str)->bool{self.files.contains_key(p)}fn sleep(&mut self,ms:u64){self.sleeps.push(ms)}fn umask(&mut self,v:u32)->u32{let old=self.mask;self.mask=v;old}fn diagnostic(&mut self,s:&str){self.messages.push(s.into())}}
fn config()->config::Config{config::Config{sbin:"/owned/sbin".into(),etc:"/owned/etc".into(),modules:"/owned/modules".into(),kernel:"/owned/kernel".into(),arch:"x86_64".into(),buildid:"fixture-build".into(),linux_work_irq:false,trampoline:String::new()}}
fn args(s:&[&str])->Vec<String>{s.iter().map(|v|v.to_string()).collect()}
// One genuinely unmatched production selection, using the unchanged existing
// new-resources rollback scenario and exact previously qualified FakeHost.
#[test]
fn production_work_irq_uses_existing_new_resources_case() {
    let production = config::Config::installed();
    assert_eq!(production.sbin, "/usr/local/sbin");
    assert_eq!(production.etc, "/usr/local/etc");
    assert_eq!(production.modules, "/usr/local/kmod");
    assert_eq!(production.kernel, "/usr/local/smp-x86/kernel");
    assert_eq!(production.arch, "x86_64");
    assert_eq!(production.buildid, "8d288b8");
    assert!(production.linux_work_irq);
    assert_eq!(config::Config::installed_stop().sbin, "/usr/local/sbin");
    // Only the actual generated ON selection is transferred into the existing
    // owned fake scenario. Its qualified fixture identities remain unchanged.
    let mut configured = config();
    configured.linux_work_irq = production.linux_work_irq;
    let mut h = Fake::ready();
    h.files.insert("/proc/modules".into(), String::new());
    h.fail = Some(("/owned/sbin/ihkosctl".into(), args(&["0", "boot"])));
    let options = reboot::parse(&args(&["-c2-3", "-R"])).unwrap();
    assert_eq!(reboot::execute(&mut h, &configured, &options), 1);
    assert!(h.saw("insmod", &["/owned/modules/ihk-smp-x86_64.ko", "ihk_ikc_irq_core=0"]));
    assert!(!h.calls.iter().any(|call| call.args.iter().any(|arg| arg.starts_with("ihk_start_irq="))));
    assert!(h.saw("/owned/sbin/ihkconfig", &["0", "release", "cpu", "2-3"]));
    assert!(h.saw("/owned/sbin/ihkconfig", &["0", "release", "mem", "512M@0"]));
    let removals = h.calls.iter().filter(|call| call.program == "rmmod")
        .map(|call| call.args[0].as_str()).collect::<Vec<_>>();
    assert_eq!(removals, ["mcctrl", "ihk_smp_x86_64", "ihk"]);
}
