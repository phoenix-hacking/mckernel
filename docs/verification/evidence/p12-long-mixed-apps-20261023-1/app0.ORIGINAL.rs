// Fixed finite supported-profile regression batch. Original case bodies retained.
mod file_roundtrip {
// Real Rust std file-state diagnostic; fixed expected bytes frozen independently.
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::os::fd::IntoRawFd;
extern "C" { fn close(fd: i32) -> i32; }
fn invalid(message: &str) -> io::Error { io::Error::new(io::ErrorKind::Other, message) }
fn require(condition: bool, message: &str) -> io::Result<()> {
    if condition { Ok(()) } else { Err(invalid(message)) }
}
fn checked_close(file: File) -> io::Result<()> {
    // Sole ownership transferred out of File; exactly one close, never retried.
    let fd = file.into_raw_fd();
    if unsafe { close(fd) } != 0 { return Err(io::Error::last_os_error()); }
    Ok(())
}
pub fn run() -> io::Result<()> {
    let path = "rust-file-roundtrip.bin";
    let mut file = OpenOptions::new().read(true).write(true).create_new(true).open(path)?;
    file.write_all(b"0123456789ABCDEF")?;
    require(file.stream_position()? == 16 && file.metadata()?.len() == 16, "initial position or length")?;
    require(file.seek(SeekFrom::Start(4))? == 4, "absolute seek")?;
    file.write_all(b"wxyz")?;
    require(file.seek(SeekFrom::Current(2))? == 10, "relative seek")?;
    require(file.seek(SeekFrom::End(-4))? == 12, "end-relative seek")?;
    let mut suffix = [0u8; 4];
    file.read_exact(&mut suffix)?;
    require(suffix == *b"CDEF" && file.stream_position()? == 16, "end-relative suffix")?;

    file.set_len(10)?;
    require(file.metadata()?.len() == 10 && file.stream_position()? == 16, "shrink changed cursor or wrong length")?;
    let mut eof = [0u8; 1];
    require(file.read(&mut eof)? == 0, "shrink EOF at retained cursor")?;
    require(file.seek(SeekFrom::Start(0))? == 0, "rewind after shrink")?;
    let mut prefix = [0u8; 10];
    file.read_exact(&mut prefix)?;
    require(prefix == *b"0123wxyz89" && file.read(&mut eof)? == 0, "shrink content or EOF")?;

    file.set_len(14)?;
    require(file.metadata()?.len() == 14 && file.stream_position()? == 10, "growth changed cursor or wrong length")?;
    let mut extension = [0xffu8; 4];
    file.read_exact(&mut extension)?;
    require(extension == [0; 4] && file.stream_position()? == 14, "grown bytes not zero or wrong cursor")?;
    require(file.seek(SeekFrom::End(-3))? == 11, "seek grown tail")?;
    file.write_all(&[0xaa, 0xbb, 0xcc])?;
    require(file.seek(SeekFrom::Start(0))? == 0, "rewind final")?;
    let mut observed = [0u8; 14];
    file.read_exact(&mut observed)?;
    require(observed == *b"0123wxyz89\0\xaa\xbb\xcc", "final exact contents")?;
    require(file.read(&mut eof)? == 0 && file.stream_position()? == 14, "final EOF or cursor")?;

    let error = match file.seek(SeekFrom::Current(-15)) {
        Err(error) => error,
        Ok(_) => return Err(invalid("negative seek unexpectedly succeeded")),
    };
    require(error.raw_os_error() == Some(22) && error.kind() == io::ErrorKind::InvalidInput, "negative seek errno or kind")?;
    require(file.stream_position()? == 14 && file.metadata()?.len() == 14, "failed seek changed cursor or length")?;
    require(file.seek(SeekFrom::Start(0))? == 0, "rewind after failed seek")?;
    file.read_exact(&mut observed)?;
    require(observed == *b"0123wxyz89\0\xaa\xbb\xcc", "failed seek changed bytes")?;
    require(file.read(&mut eof)? == 0 && file.stream_position()? == 14, "post-error EOF or cursor")?;
    file.sync_all()?;
    checked_close(file)?;
    fs::remove_file(path)?;
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == io::ErrorKind::NotFound && error.raw_os_error() == Some(2) => {},
        _ => return Err(invalid("cleanup path still present or unexpected error")),
    }
    println!("rust-file-roundtrip initial=16 overwrite=4 shrink=10 grow=14 zeros=4 tail=aabbcc invalid_seek=22 cursor=14 checked_close=1 removed=1");
    Ok(())
}

}
mod mixed_std {
// Derived from practical_rust_std_app.rs; standalone future diagnostic payload.
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::os::fd::IntoRawFd;
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

extern "C" { fn close(fd: i32) -> i32; }

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::Other, message)
}

fn checked_close(file: File) -> io::Result<()> {
    // Transfer sole descriptor ownership out of File before the one close call.
    // Never retry: an interrupted close can already have released the descriptor.
    let fd = file.into_raw_fd();
    if unsafe { close(fd) } != 0 { return Err(io::Error::last_os_error()); }
    Ok(())
}

pub fn run() -> io::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let fault = match args.as_slice() {
        [] => "",
        [flag, kind] if flag == "--negative-control" &&
            ["memory", "checksum", "thread"].contains(&kind.as_str()) => kind.as_str(),
        _ => return Err(invalid("unsupported arguments")),
    };
    let expected = [1024005u64, 1024090, 1024175];
    let mut total = 0u64;
    for round in 0..3usize {
        let mut data: Vec<u8> = (0..8193).map(|i| ((i * 37 + 11 + round * 13) % 251) as u8).collect();
        if round == 0 && fault == "memory" { data[4096] ^= 1; }
        // Check every byte through an independent recurrence, plus frozen sums.
        let mut value = 11 + round * 13;
        for &byte in &data {
            if usize::from(byte) != value { return Err(invalid("memory pattern differs")); }
            value = (value + 37) % 251;
        }
        if data.iter().map(|&b| u64::from(b)).sum::<u64>() != expected[round] {
            return Err(invalid("memory checksum differs"));
        }
        let path = format!("mixed-rust-std-{}-{round}.bin", std::process::id());
        let mut output = OpenOptions::new().write(true).create_new(true).open(&path)?;
        output.write_all(&data)?;
        output.sync_all()?;
        checked_close(output)?;
        let mut input = File::open(&path)?;
        let mut observed = vec![0u8; data.len()];
        input.read_exact(&mut observed)?;
        let mut eof = [0u8; 1];
        if input.read(&mut eof)? != 0 { return Err(invalid("file EOF missing")); }
        checked_close(input)?;
        if round == 0 && fault == "checksum" { observed[4096] ^= 1; }
        let sum = observed.iter().map(|&b| u64::from(b)).sum::<u64>();
        if sum != expected[round] { return Err(invalid("file checksum differs")); }
        if observed != data { return Err(invalid("file bytes differ")); }
        fs::remove_file(&path)?;
        match fs::metadata(&path) {
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            _ => return Err(invalid("removed file absence uncertain")),
        }
        total += sum;

        // Alternating ownership forces real std Condvar wait/notify and joins.
        let state = Arc::new((Mutex::new((0usize, 0u32)), Condvar::new()));
        let mut handles = Vec::new();
        for id in 0..2usize {
            let shared = Arc::clone(&state);
            match thread::Builder::new().stack_size(262144).spawn(move || -> io::Result<()> {
                let (lock, ready) = &*shared;
                for _ in 0..128 {
                    let mut guard = lock.lock().map_err(|_| invalid("mutex poisoned"))?;
                    while guard.0 != id {
                        guard = ready.wait(guard).map_err(|_| invalid("wait mutex poisoned"))?;
                    }
                    guard.1 += 1;
                    guard.0 = 1 - id;
                    ready.notify_one();
                }
                Ok(())
            }) {
                Ok(handle) => handles.push(handle),
                Err(error) => {
                    eprintln!("thread spawn failed: {error}");
                    std::process::exit(1);
                }
            }
        }
        let mut first_error = None;
        for handle in handles {
            match handle.join() {
                Ok(Ok(())) => {}
                Ok(Err(error)) => { first_error.get_or_insert(error); }
                Err(_) => { first_error.get_or_insert_with(|| invalid("worker panicked")); }
            }
        }
        if let Some(error) = first_error { return Err(error); }
        let mut guard = state.0.lock().map_err(|_| invalid("final mutex poisoned"))?;
        if round == 0 && fault == "thread" { guard.1 += 1; }
        if *guard != (0, 256) { return Err(invalid("thread counter differs")); }
    }
    println!("mixed rounds=3 bytes_each=8193 checksum_total={total}");
    println!("files=3 checked_closes=6 reopened=3 eof=3 removed=3");
    println!("joined_threads=6 turns_each=128 counter_total=768");
    Ok(())
}

}
fn main() -> std::io::Result<()> {
    if let Err(e)=pair_pin() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }

    if std::env::args_os().len() != 1 {
        return Err(std::io::Error::new(std::io::ErrorKind::InvalidInput, "batch accepts no arguments"));
    }
    println!("batch begin cases=2 mixed_rounds=3");
    file_roundtrip::run()?;
    mixed_std::run()?;
    println!("batch pass cases=2 checked_closes=7 removed=4 joined_threads=6");
    Ok(())
}

// Linux x86_64/McKernel ABI. Called before any accepted body or worker spawn.
fn pair_pin() -> Result<(), String> {
    use std::arch::asm;
    unsafe fn raw(n: usize, p: *mut u8) -> isize {
        let r: isize;
        asm!("syscall", inlateout("rax") n => r, in("rdi") 0usize,
             in("rsi") 128usize, in("rdx") p, lateout("rcx") _, lateout("r11") _, options(nostack));
        r
    }
    let text=std::env::var("PAIR_CPU").map_err(|_| "missing PAIR_CPU")?;
    let cpu:usize=text.parse().map_err(|_| "invalid PAIR_CPU")?;
    if cpu>=1024 || cpu.to_string()!=text { return Err("noncanonical PAIR_CPU".into()); }
    let mut mask=[0u8;128];
    let n=unsafe {raw(204,mask.as_mut_ptr())};
    if n<=0 || n>128 || mask[cpu/8]&(1<<(cpu%8))==0 { return Err("assigned CPU not inherited".into()); }
    let mut one=[0u8;128]; one[cpu/8]=1<<(cpu%8);
    if unsafe {raw(203,one.as_mut_ptr())}!=0 { return Err("setaffinity failed".into()); }
    mask.fill(0);
    let n=unsafe {raw(204,mask.as_mut_ptr())};
    if n<=0 || n>128 || mask!=one { return Err("exact assigned CPU not confirmed".into()); }
    Ok(())
}
