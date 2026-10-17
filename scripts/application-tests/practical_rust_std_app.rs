use std::cell::Cell;
use std::collections::BTreeMap;
use std::fs::{self, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::sync::{Arc, Barrier, Mutex};
use std::thread;

thread_local! {
    static TLS_VALUE: Cell<u32> = const { Cell::new(0) };
}

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::Other, message)
}

fn main() -> io::Result<()> {
    let data: Vec<u8> = (0..8193).map(|i| ((i * 37 + 11) % 251) as u8).collect();
    let checksum: u64 = data.iter().map(|&byte| u64::from(byte)).sum();

    let path = format!("practical-rust-std-{}.bin", std::process::id());
    let mut file = OpenOptions::new().read(true).write(true).create_new(true).open(&path)?;
    file.write_all(&data)?;
    file.sync_all()?;
    if file.seek(SeekFrom::Start(0))? != 0 {
        return Err(invalid("file rewind failed"));
    }
    let mut observed = Vec::new();
    file.read_to_end(&mut observed)?;
    if observed != data {
        return Err(invalid("file bytes differ"));
    }
    let mut eof = [0u8; 1];
    if file.read(&mut eof)? != 0 {
        return Err(invalid("file EOF missing"));
    }
    // Drop closes the handle; Rust's File drop cannot report close errors.
    drop(file);
    fs::remove_file(&path)?;
    match fs::metadata(&path) {
        Err(error) if error.kind() == io::ErrorKind::NotFound => {}
        _ => return Err(invalid("removed file remains or absence is uncertain")),
    }

    let text = String::from("rust std rust files threads std rust");
    let mut words = BTreeMap::new();
    for word in text.split_whitespace() {
        *words.entry(word.to_owned()).or_insert(0u32) += 1;
    }
    let word_counts = words.iter().map(|(word, count)| format!("{word}:{count}"))
        .collect::<Vec<_>>().join(" ");

    TLS_VALUE.with(|value| value.set(77));
    let barrier = Arc::new(Barrier::new(3));
    let counter = Arc::new(Mutex::new(0u32));
    let mut handles = Vec::new();
    for id in 0..2u32 {
        let barrier = Arc::clone(&barrier);
        let counter = Arc::clone(&counter);
        let spawned = thread::Builder::new().name(format!("std-worker-{id}"))
            .stack_size(262144).spawn(move || -> io::Result<bool> {
                TLS_VALUE.with(|value| value.set(1000 + id));
                barrier.wait();
                for _ in 0..1000 {
                    let mut count = counter.lock().map_err(|_| invalid("counter mutex poisoned"))?;
                    *count += 1;
                }
                Ok(TLS_VALUE.with(|value| value.get() == 1000 + id))
            });
        match spawned {
            Ok(handle) => handles.push(handle),
            Err(error) => {
                // An already spawned worker may be waiting at the barrier.
                // Fail the whole process rather than wait for a missing peer.
                eprintln!("thread spawn failed: {error}");
                std::process::exit(1);
            }
        }
    }
    barrier.wait();
    let mut tls_ok = true;
    let mut first_error = None;
    for handle in handles {
        match handle.join() {
            Ok(Ok(ok)) => tls_ok &= ok,
            Ok(Err(error)) => { first_error.get_or_insert(error); }
            Err(_) => { first_error.get_or_insert_with(|| invalid("worker panicked")); }
        }
    }
    if let Some(error) = first_error {
        return Err(error);
    }
    let count = *counter.lock().map_err(|_| invalid("counter mutex poisoned"))?;
    let parent_tls_ok = TLS_VALUE.with(|value| value.get() == 77);
    if count != 2000 || !tls_ok || !parent_tls_ok {
        return Err(invalid("thread counter or TLS differs"));
    }

    println!("vec bytes={} checksum={checksum}", data.len());
    println!("file roundtrip=1 eof=1 removed=1");
    println!("words {word_counts}");
    println!("threads=2 counter=2000 tls=1 parent_tls=1");
    Ok(())
}
