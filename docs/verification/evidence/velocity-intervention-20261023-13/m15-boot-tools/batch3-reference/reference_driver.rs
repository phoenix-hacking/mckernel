// Functional McKernel OS/apps migration only; no security testing.
// Stage alongside frozen batch1 fixture.rs and its modules, not the native mains.
include!("fixture.rs");
fn main(){let scenario=std::env::args().nth(1).expect("boot-existing or stop-retain");let mut h=Fake::ready();let rc=match scenario.as_str(){"boot-existing"=>{let o=reboot::parse(&args(&["-c2-3","-otester"])).unwrap();reboot::execute(&mut h,&config(),&o)},"stop-retain"=>stop::execute(&mut h,&config(),&stop::parse(&args(&["-R"])).unwrap()),_=>panic!("unsupported scenario")};for call in h.calls{print!("{}",call.program);for arg in call.args{assert!(!arg.contains('\t')&&!arg.contains('\n'));print!("\t{arg}");}println!();}std::process::exit(rc)}
