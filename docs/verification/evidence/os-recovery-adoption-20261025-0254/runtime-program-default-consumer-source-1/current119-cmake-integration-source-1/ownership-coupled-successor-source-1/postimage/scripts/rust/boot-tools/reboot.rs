// Based on mcreboot-smp.sh.in; Copyright RIKEN AICS 2014, Fujitsu Ltd. 2018.
// Functional McKernel OS/apps migration only; no security testing.
use crate::{config::Config,platform::*};
#[derive(Clone,Debug,PartialEq)]pub struct Options {pub mem:String,pub cpus:String,pub ikc:String,pub facility:String,pub owner:Option<String>,pub redirect:String,pub interval:String,pub irq:String,pub dump:String,pub extra:String,pub turbo:bool,pub safe:bool,pub halt:bool,pub oversubscribe:bool,pub sharing:bool,pub reserve:bool}
impl Default for Options {fn default()->Self{Self{mem:"512M@0".into(),cpus:String::new(),ikc:String::new(),facility:"LOG_LOCAL6".into(),owner:None,redirect:"0".into(),interval:"-1".into(),irq:String::new(),dump:"24".into(),extra:String::new(),turbo:false,safe:false,halt:false,oversubscribe:false,sharing:true,reserve:false}}}
pub fn parse(args:&[String])->Result<Options,String>{let mut o=Options::default();let mut i=0;while i<args.len(){let a=&args[i];if a=="--"||!a.starts_with('-')||a=="-"{break}let mut chars=a[1..].char_indices();while let Some((n,ch))=chars.next(){match ch{'s'=>o.safe=true,'t'=>o.turbo=true,'h'=>o.halt=true,'O'=>o.oversubscribe=true,'R'=>o.reserve=true,'f'|'o'|'k'|'c'|'m'|'r'|'q'|'e'|'d'|'i'|'T'=>{let start=n+2;let v=if start<a.len(){a[start..].to_string()}else{i+=1;args.get(i).ok_or_else(||format!("option requires an argument -- {ch}"))?.clone()};match ch{'f'=>o.facility=v,'o'=>o.owner=Some(v),'k'=>o.redirect=v,'c'=>o.cpus=v,'m'=>o.mem=v,'r'=>o.ikc=v,'q'=>o.irq=v,'e'=>o.extra=v,'d'=>o.dump=v,'i'=>o.interval=v,'T'=>match v.as_str(){"1"=>o.sharing=true,"0"=>o.sharing=false,_=>{}},_=>{}}break},_=>return Err(format!("invalid option -- {ch}"))}}i+=1;}Ok(o)}
#[derive(Default)]struct Acquired {ihk:bool,smp:bool,mcctrl:bool,mem:bool,cpu:bool,os:bool,irq_saved:bool,irq_stopped:bool}
fn reserve(h:&mut dyn Host,ctl:&str,kind:&str,value:&str)->bool{run(h,ctl,&["0","reserve",kind,value],true).ok()}
fn fail(h:&mut dyn Host,c:&Config,o:&Options,a:&Acquired,oldmask:u32,irq_used:bool,message:&str)->i32{
 h.diagnostic(message);let ctl=format!("{}/ihkconfig",c.sbin);
 // Roll back only state acquired by this attempt. Successful reboot still targets
 // every existing OS, just as the original public command specifies.
 if a.os&&!run(h,&ctl,&["0","destroy","0"],true).ok(){h.diagnostic("warning: failed to destroy LWK instance 0")}
 if a.mcctrl&&!run(h,"rmmod",&["mcctrl"],true).ok(){h.diagnostic("warning: failed to remove mcctrl")}
 for (owned,kind,value,label) in [(a.cpu,"cpu",o.cpus.as_str(),"CPUs"),(a.mem,"mem",o.mem.as_str(),"memory")] {if owned&&!run(h,&ctl,&["0","release",kind,value],true).ok(){h.diagnostic(&format!("warning: failed to release {label}"))}}
 for (owned,module) in [(a.smp,format!("ihk_smp_{}",c.arch)),(a.ihk,"ihk".into())]{if owned&&!run(h,"rmmod",&[&module],true).ok(){h.diagnostic(&format!("warning: failed to remove {module}"))}}
 h.umask(oldmask);if a.irq_saved&&irq_used{restore_saved_affinities(h);if h.file(IRQ_CONFIG){irq_restore(h);}else{run(h,"rm",&["-rf",IRQ_SAVE],true);}}if a.irq_stopped&&irq_used{if !run(h,"systemctl",&["start","irqbalance.service"],true).ok(){h.diagnostic("warning: failed to start irqbalance")}}1
}
pub fn cpu_set(text:&str)->Result<Vec<usize>,String>{let mut out=Vec::new();for part in text.trim().split(','){let mut r=part.split('-');let a=r.next().unwrap_or("").parse::<usize>().map_err(|_|"invalid CPU list")?;let b=match r.next(){Some(v)=>v.parse::<usize>().map_err(|_|"invalid CPU range")?,None=>a};if r.next().is_some()||a>b||b>1_048_575{return Err("invalid CPU range".into())}out.extend(a..=b)}out.sort_unstable();out.dedup();Ok(out)}
pub fn masks(cpus:&str,count:usize)->Result<(Vec<u32>,String,String),String>{if count==0||count>1_048_576{return Err("invalid CPU count".into())}let mut mask=vec![0u32;(count+31)/32];for cpu in cpu_set(cpus)?{if cpu>=count{return Err("CPU exceeds topology".into())}mask[cpu/32]|=1<<(cpu%32)}let fmt=|invert:bool|->String{mask.iter().enumerate().rev().map(|(i,v)|{let bits=if invert{!v}else{*v};let width=if i==mask.len()-1&&count%32!=0{(count%32+3)/4}else{8};let bits=if i==mask.len()-1&&count%32!=0{bits&((1u32<<(count%32))-1)}else{bits};format!("{bits:0width$x}")}).collect::<Vec<_>>().join(",")};let selected=fmt(false);let inverse=fmt(true);Ok((mask,selected,inverse))}
fn affinity_hit(text:&str,mask:&[u32])->bool{let words=text.trim().split(',').rev().collect::<Vec<_>>();mask.iter().enumerate().any(|(i,m)|words.get(i).and_then(|s|u32::from_str_radix(s,16).ok()).unwrap_or(0)&m!=0)}
fn restore_saved_affinities(h:&mut dyn Host){for irq in entries(h,&format!("{IRQ_SAVE}/proc/irq")){let f=format!("/proc/irq/{irq}/smp_affinity");if let Ok(s)=h.read(&format!("{IRQ_SAVE}{f}")){write(h,&f,&s);}}}
fn node_memory(h:&mut dyn Host,node:u32)->Vec<String>{let base=format!("/sys/devices/system/node/node{node}");entries(h,&base).into_iter().filter(|s|s.starts_with("memory")).map(|s|format!("{base}/{s}/online")).filter(|s|h.file(s)).collect()}
fn ofp_memory(h:&mut dyn Host){let hostname=run(h,"hostname",&[],false).out;let b=hostname.as_bytes();let ofp=b.windows(9).any(|v|v[0]==b'c'&&v[1..5].iter().all(u8::is_ascii_digit)&&&v[5..9]==b".ofp");if !ofp{return}let online=h.read("/sys/devices/system/node/online").unwrap_or_default();match online.trim(){"0-7"=>{for node in 0..4{let files=node_memory(h,node);for v in ["0\n","1\n"]{for f in &files{write(h,f,v);}}}for v in ["0\n","1\n"]{for node in 4..8{for f in node_memory(h,node){write(h,&f,v);}}}},"0-1"=>{let files=node_memory(h,1);for v in ["0\n","1\n"]{for f in &files{write(h,f,v);}}},_=>{}}}
pub fn execute(h:&mut dyn Host,c:&Config,options:&Options)->i32{
 let mut o=options.clone();let mut acquired=Acquired::default();let oldmask=h.umask(0);h.umask(oldmask);
 let enforcing=run(h,"getenforce",&[],false);if enforcing.ok()&&enforcing.out.trim().eq_ignore_ascii_case("enforcing"){h.diagnostic("error: SELinux must not be enabled when running McKernel (update /etc/selinux/config or see setenforce)");return 1}
 let owner=o.owner.clone().unwrap_or_else(||{let user=run(h,"id",&["-un"],false).out.trim_end().to_string();if user=="root"{run(h,"logname",&[],false).out.trim_end().into()}else{user}});
 let irq_used=run(h,"systemctl",&["status","irqbalance.service"],false).ok();let ctl=format!("{}/ihkconfig",c.sbin);let osctl=format!("{}/ihkosctl",c.sbin);
 let pids=run(h,"pidof",&["ihkmond"],false).out;if !pids.trim().is_empty(){let mut a=vec!["-9"];a.extend(words(&pids));run(h,"kill",&a,true);}
 if o.redirect!="0"||o.interval!="-1"{run(h,&format!("{}/ihkmond",c.sbin),&["-f",&o.facility,"-k",&o.redirect,"-i",&o.interval],true);}
 if o.cpus.is_empty(){let topology=run(h,"lscpu",&["--parse"],false).out;let cpus=topology.lines().filter(|l|!l.starts_with('#')).filter_map(|l|{let v=l.split(',').collect::<Vec<_>>();if v.len()>3&&v[3]=="0"{Some(v[0].to_string())}else{None}}).collect::<Vec<_>>();o.cpus=cpus.iter().skip(cpus.len()-cpus.len()/2).cloned().collect::<Vec<_>>().join(",");if o.cpus.is_empty(){h.diagnostic("error: no available CPUs on NUMA node 0?");return 1}}
 run(h,"systemctl",&["stop","irqbalance.service"],true);acquired.irq_stopped=true;let mut selected=String::new();
 macro_rules! error {($msg:expr)=>{return fail(h,c,&o,&acquired,oldmask,irq_used,$msg)}}
 if irq_used{let topology=run(h,"lscpu",&[],false).out;let count=topology.lines().find_map(|l|l.strip_prefix("CPU(s):").and_then(|v|v.trim().parse::<usize>().ok())).unwrap_or(0);selected=match masks(&o.cpus,count){Ok((_,mask,_))=>mask,Err(_)=>error!("error: modifying /proc/irq/*/smp_affinity")};}
 if irq_used&&!h.exists(IRQ_SAVE){acquired.irq_saved=true;
  for irq in entries(h,"/proc/irq"){let f=format!("/proc/irq/{irq}/smp_affinity");if !h.file(&f){continue}let dest=format!("{IRQ_SAVE}{f}");let parent=dest.rsplit_once('/').unwrap().0;run(h,"mkdir",&["-p",parent],true);let text=run(h,"cat",&[&f],true);if !text.ok()||!write(h,&dest,&text.out){error!("error: saving /proc/irq/*/smp_affinity")}}
  let topology=run(h,"lscpu",&[],false).out;let count=topology.lines().find_map(|l|l.strip_prefix("CPU(s):").and_then(|v|v.trim().parse::<usize>().ok())).unwrap_or(0);let (mask,s,inv)=match masks(&o.cpus,count){Ok(v)=>v,Err(_)=>error!("error: modifying /proc/irq/*/smp_affinity")};selected=s;
  for irq in entries(h,"/proc/irq"){let f=format!("/proc/irq/{irq}/smp_affinity");if let Ok(text)=h.read(&f){if affinity_hit(&text,&mask)&&!write(h,&f,&format!("{inv}\n")){error!("error: modifying /proc/irq/*/smp_affinity")}}}
 }
 h.umask(oldmask&2);
 if !loaded(h,"ihk"){if !run(h,"insmod",&[&format!("{}/ihk.ko",c.modules)],true).ok(){error!("error: loading ihk")}acquired.ihk=true;}
 write(h,"/proc/sys/vm/swappiness","100\n");if run(h,"sync",&[],true).ok(){write(h,"/proc/sys/vm/drop_caches","3\n");}write(h,"/proc/sys/vm/compact_memory","1\n");run(h,"sync",&[],true);
 let smp=format!("ihk_smp_{}",c.arch);
 if !loaded(h,&smp){if o.irq.is_empty()&&!c.linux_work_irq{let interrupts=h.read("/proc/interrupts").unwrap_or_default();for irq in 64..=255{if !h.exists(&format!("/proc/irq/{irq}"))&&!interrupts.lines().any(|l|l.split(':').next().unwrap_or("").trim()==irq.to_string()){o.irq=irq.to_string();break}}if o.irq.is_empty(){error!("error: no IRQ available")}}
  let module=format!("{}/ihk-smp-{}.ko",c.modules,c.arch);let mut args=vec![module];if !o.irq.is_empty(){args.push(format!("ihk_start_irq={}",o.irq))}if !c.trampoline.is_empty(){args.push(format!("ihk_trampoline={}",c.trampoline))}args.push("ihk_ikc_irq_core=0".into());let refs=args.iter().map(String::as_str).collect::<Vec<_>>();if !run(h,"insmod",&refs,true).ok(){error!(&format!("error: loading ihk-smp-{}",c.arch))}acquired.smp=true;ofp_memory(h);
  if !reserve(h,&ctl,"mem",&o.mem){error!("error: reserving memory")}acquired.mem=true;if !reserve(h,&ctl,"cpu",&o.cpus){error!("error: reserving CPUs")}acquired.cpu=true;
 }
 if o.reserve&&!acquired.smp{if !reserve(h,&ctl,"mem",&o.mem){error!("error: reserving memory")}acquired.mem=true;if !reserve(h,&ctl,"cpu",&o.cpus){error!("error: reserving CPUs")}acquired.cpu=true;}
 if !loaded(h,"mcctrl"){if !run(h,"insmod",&[&format!("{}/mcctrl.ko",c.modules)],true).ok(){error!("error: inserting mcctrl.ko")}acquired.mcctrl=true;}
 let buildid=run(h,&ctl,&["0","get","buildid"],true).out.trim_end().to_string();if buildid!=c.buildid{error!(&format!("IHK build-id ({buildid}) didn't match McKernel build-id ({}).",c.buildid))}
 for dev in devices(h,"mcos"){let index=&dev[9..];if !destroy(h,&ctl,index){error!(&format!("error: destroying LWK instance {index} failed"))}}
 if !run(h,&ctl,&["0","create"],true).ok(){error!("error: creating OS instance")}acquired.os=true;
 if !run(h,&osctl,&["0","assign","cpu",&o.cpus],true).ok(){error!("error: assign CPUs")}
 if !o.ikc.is_empty()&&!run(h,&osctl,&["0","set","ikc_map",&o.ikc],true).ok(){error!("error: assign CPUs")}
 if !run(h,&osctl,&["0","assign","mem",&o.mem],true).ok(){error!("error: assign memory")}
 let image=format!("{}/mckernel.img",c.kernel);if !run(h,&osctl,&["0","load",&image],true).ok(){error!(&format!("error: loading kernel image: {image}"))}
 let kargs=format!("hidos {} {} {} dump_level={} {} {} {}",if o.turbo{"turbo"}else{""},if o.safe{"safe_kernel_map"}else{""},if o.halt{"idle_halt"}else{""},o.dump,o.extra,if o.oversubscribe{"allow_oversubscribe"}else{""},if o.sharing{"time_sharing"}else{""});
 if !run(h,&osctl,&["0","kargs",&kargs],true).ok(){error!("error: setting kernel arguments")}
 if !run(h,&osctl,&["0","boot"],true).ok(){error!("error: booting")}
 let mut devs=devices(h,"mcd");if devs.is_empty(){devs.push("/dev/mcd*".into())}let os=devices(h,"mcos");if os.is_empty(){devs.push("/dev/mcos*".into())}else{devs.extend(os)}let mut chown=vec![owner];chown.extend(devs);if !run(h,"chown",&chown.iter().map(String::as_str).collect::<Vec<_>>(),true).ok(){h.diagnostic("warning: failed to chown device files")}
 if irq_used{let interrupts=h.read("/proc/interrupts").unwrap_or_default();let ban=interrupts.lines().filter(|l|l.trim_end().ends_with("IHK-SMP")).filter_map(|l|l.split(':').next().map(str::trim)).collect::<String>();let template=h.read(&format!("{}/irqbalance_mck.in",c.etc)).unwrap_or_default();write(h,"/run/sysconfig/irqbalance_mck",&template.replace("%mask%",&selected).replace("%banirq%",&ban));run(h,"mkdir",&["/run/systemd/system/irqbalance.service.d"],true);write(h,IRQ_CONFIG,"[Service]\nEnvironmentFile=\nEnvironmentFile=/run/sysconfig/irqbalance_mck\n");run(h,"systemctl",&["daemon-reload"],true);if !run(h,"systemctl",&["restart","irqbalance.service"],true).ok(){error!("error: restarting irqbalance with mckernelconfig")}}
 h.umask(oldmask);0
}
