// Based on mcstop+release-smp.sh.in; Copyright FUJITSU LIMITED 2018, RIKEN AICS 2015.
// Functional McKernel OS/apps migration only; no security testing.
use crate::{config::Config,platform::*};
#[derive(Default,Debug,PartialEq)] pub struct Options {pub rmmod:String,pub kill:bool,pub retain:bool}
pub fn parse(args:&[String])->Result<Options,String> {
 let mut o=Options{rmmod:"/sbin/rmmod".into(),..Options::default()};let mut i=0;
 while i<args.len(){let a=&args[i];if a=="--"{i+=1;break}if !a.starts_with('-')||a=="-"{break}
 let mut chars=a[1..].char_indices().peekable();while let Some((n,c))=chars.next(){match c{'k'=>o.kill=true,'R'=>o.retain=true,'r'=>{let start=n+2;if start<a.len(){o.rmmod=a[start..].into()}else{i+=1;o.rmmod=args.get(i).ok_or("option requires an argument -- r")?.clone()}break},_=>return Err(format!("invalid option -- {c}"))}}i+=1;}
 if i<args.len(){return Err(format!("Extra arguments: {}",args[i..].join(" ")))}Ok(o)
}
pub fn execute(h:&mut dyn Host,c:&Config,o:&Options)->i32 {
 if !h.file(&o.rmmod){h.diagnostic(&format!("error: {} doesn't exist, please specify by -r <path_to_rmmod>",o.rmmod));return 1}
 let smp=format!("ihk_smp_{}",c.arch);if !loaded(h,&smp){return 0}
 if h.file(IRQ_CONFIG){run(h,"systemctl",&["stop","irqbalance"],true);}
 let ctl=format!("{}/ihkconfig",c.sbin);
 for dev in devices(h,"mcos") {
  let users=run(h,"lsof",&["-t",&dev],false).out;
  if !users.trim().is_empty(){if !o.kill{h.diagnostic(&format!("Proesses still using {dev}: {}",users.trim_end()));return 1}
   let mut args=vec!["-9"];args.extend(words(&users));run(h,"kill",&args,false);}
  let index=&dev[9..];if !destroy(h,&ctl,index){h.diagnostic(&format!("error: destroying LWK instance {index} failed"));return 1}
 }
 h.sleep(2000);
 if !run(h,&ctl,&["0","query","cpu"],true).ok(){h.diagnostic("error: querying cpus");return 1}
 let cpus=run(h,&ctl,&["0","query","cpu"],true).out;
 if !cpus.trim().is_empty()&&!run(h,&ctl,&["0","release","cpu",cpus.trim_end()],true).ok(){h.diagnostic("warning: failed to release CPUs")}
 if !run(h,&ctl,&["0","release","mem","all"],true).ok(){h.diagnostic("error: releasing memory");return 1}
 if o.retain{return 0}
 for m in ["mcctrl",smp.as_str(),"ihk"] {if loaded(h,m)&&!run(h,&o.rmmod,&[m],true).ok(){h.diagnostic(&format!("error: removing {m}"));return 1}}
 let pids=run(h,"pidof",&["ihkmond"],false).out;if !pids.trim().is_empty(){let mut a=vec!["-9"];a.extend(words(&pids));run(h,"kill",&a,true);}
 irq_restore(h);write(h,"/proc/sys/vm/swappiness","60\n");0
}
