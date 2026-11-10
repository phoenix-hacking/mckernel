// Configured by CMake @ONLY, matching installed SMP paths.
#[derive(Clone)] pub struct Config {pub sbin:String,pub etc:String,pub modules:String,pub kernel:String,pub arch:String,pub buildid:String,pub linux_work_irq:bool,pub trampoline:String}
impl Config {pub fn installed()->Self{Self{sbin:"/usr/local/sbin".into(),etc:"/usr/local/etc".into(),modules:"/usr/local/kmod".into(),kernel:"/usr/local/smp-x86/kernel".into(),arch:"x86_64".into(),buildid:"8d288b8".into(),linux_work_irq:"ON"=="ON",trampoline:std::env::var("IHK_TRAMPOLINE_PHYS").unwrap_or_default()}}}
// Stop uses the independently configured GNUInstallDirs provider path.
impl Config {pub fn installed_stop()->Self{Self{sbin:"/usr/local/sbin".into(),..Self::installed()}}}
