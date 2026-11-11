mod eclair_backtrace;mod eclair_native;mod config;
fn main(){println!("spawn {} -k {} -i -l",config::ECLAIR,config::KERNEL);let result=eclair_native::Pty::spawn(config::ECLAIR,config::KERNEL).map_err(|e|e.to_string()).and_then(|mut p|eclair_backtrace::drive(&mut p));if let Err(e)=result{eprintln!("eclair-dump-backtrace: {e}");std::process::exit(1)}}
