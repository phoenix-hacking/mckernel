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

fn main() -> io::Result<()> {
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
