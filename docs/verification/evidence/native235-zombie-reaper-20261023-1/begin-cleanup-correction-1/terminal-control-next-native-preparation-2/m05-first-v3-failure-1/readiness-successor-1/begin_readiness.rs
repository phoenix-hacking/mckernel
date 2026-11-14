// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Read-only admission for the frozen M05 one-simple-process-per-epoch producer.
#![no_std]
use core::str::SplitAsciiWhitespace;
unsafe extern "C" { fn abort() -> !; }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { abort() } }

fn number(words: &mut SplitAsciiWhitespace<'_>, key: &str) -> Option<u64> {
    let text=words.next()?.strip_prefix(key)?;
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_digit()) { return None; }
    text.parse().ok()
}
fn signed(words: &mut SplitAsciiWhitespace<'_>, key: &str) -> Option<i32> {
    let text=words.next()?.strip_prefix(key)?;
    let digits=text.strip_prefix('-').unwrap_or(text);
    if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit()) { return None; }
    text.parse().ok()
}
fn end(words: &mut SplitAsciiWhitespace<'_>) -> Result<(),()> {
    if words.next().is_none() {Ok(())} else {Err(())}
}
fn audit(log: &str, epoch: u64) -> Result<bool,()> {
    let mut pid=0;let mut published=false;let mut exited=false;let mut intent=false;
    let mut ack=0;let mut deleted=false;let mut success=false;
    let mut tokens=[0u64;12];let mut used=0;
    for line in log.lines() {
        let (body,smp)=if let Some((prefix,body))=line.split_once("ihk_smp_x86_64: IHK-SMP: ") {
            if !prefix.starts_with("<6>[") { return Err(()); } (body,true)
        } else if let Some((prefix,body))=line.split_once("mcctrl: ") {
            if !prefix.starts_with("<6>[") { return Err(()); } (body,false)
        } else {continue};
        if smp && body.starts_with("shutdown ") {
            let mut w=body[9..].split_ascii_whitespace();
            let os=number(&mut w,"os=").ok_or(())?;
            let generation=number(&mut w,"generation=").ok_or(())?;
            // A public shutdown attempt may already have irreversible effects.
            if os==0 && generation==epoch { return Err(()); }
            continue;
        }
        let (kind,tail)=if smp {
            if let Some(t)=body.strip_prefix("application SCHEDULE ") {(1,t)}
            else if let Some(t)=body.strip_prefix("application procfs published ") {(2,t)}
            else if let Some(t)=body.strip_prefix("application cleanup ACK ") {(5,t)}
            else if let Some(t)=body.strip_prefix("application procfs deleted ") {(6,t)}
            else if let Some(t)=body.strip_prefix("application retirement ") {(7,t)}
            else {continue}
        } else if let Some(t)=body.strip_prefix("application_syscall=delivered ") {(3,t)}
        else if let Some(t)=body.strip_prefix("application_process=cleanup_requested ") {(4,t)}
        else {continue};
        let mut w=tail.split_ascii_whitespace();
        let os=number(&mut w,"os=").ok_or(())?;
        let generation=number(&mut w,"generation=").ok_or(())?;
        let seen=number(&mut w,"pid=").ok_or(())?;
        if os!=0 || generation!=epoch {continue}
        if seen==0 {return Err(())}
        if kind==1 {
            if pid!=0 || number(&mut w,"cpu=")!=Some(0) {return Err(())}
            end(&mut w)?;pid=seen;continue;
        }
        if pid==0 || seen!=pid {return Err(())}
        match kind {
            2=>{if published || exited || number(&mut w,"tid=")!=Some(pid) {return Err(())} end(&mut w)?;published=true;},
            3=>{
                let worker=number(&mut w,"worker=").ok_or(())?;
                let delivery=number(&mut w,"delivery=").ok_or(())?;
                let cpu=number(&mut w,"cpu=").ok_or(())?;
                let syscall=number(&mut w,"number=").ok_or(())?;end(&mut w)?;
                if worker==0 || delivery==0 || cpu!=0 || !published || exited {return Err(())}
                if syscall==231 {exited=true;}
            },
            4=>{if !exited || intent || signed(&mut w,"intent_errno=")!=Some(0) {return Err(())}end(&mut w)?;intent=true;},
            5=>{
                let token=number(&mut w,"token=").ok_or(())?;
                let errno=signed(&mut w,"errno=").ok_or(())?;
                let abandoned=number(&mut w,"abandoned=").ok_or(())?;end(&mut w)?;
                if !intent || ack!=0 || token==0 || errno!=0 || abandoned>1 {return Err(())}ack=token;
            },
            6=>{if ack==0 || deleted || number(&mut w,"tid=")!=Some(pid) {return Err(())}end(&mut w)?;deleted=true;},
            7=>{
                let token=number(&mut w,"token=").ok_or(())?;
                let errno=signed(&mut w,"errno=").ok_or(())?;end(&mut w)?;
                if ack==0 || success || used==tokens.len() || token<=ack ||
                    (used>0 && token<=tokens[used-1]) || (errno!=0 && errno!=-11) {return Err(())}
                tokens[used]=token;used+=1;
                if errno==0 {if !deleted {return Err(())}success=true;}
            },
            _=>return Err(()),
        }
    }
    Ok(pid!=0 && published && exited && intent && ack!=0 && deleted && success)
}

// 1: actual matching retirement0 and full lifecycle join; 0: not ready;
// -1: malformed/conflicting/overflow/incomplete snapshot or shutdown attempted.
// No status is an application/native acceptance or a credit-release operation.
#[no_mangle]
pub unsafe extern "C" fn m05_begin_ready(bytes:*const u8,length:usize,epoch:u64)->i32 {
    if bytes.is_null() || length==0 || length>=262144 || !(epoch==1 || epoch==2) {return -1}
    let data=core::slice::from_raw_parts(bytes,length);
    if data.last()!=Some(&b'\n') || data.contains(&0) || data.contains(&b'\r') {return -1}
    let Ok(text)=core::str::from_utf8(data) else {return -1};
    match audit(text,epoch) {Ok(true)=>1,Ok(false)=>0,Err(())=>-1}
}
