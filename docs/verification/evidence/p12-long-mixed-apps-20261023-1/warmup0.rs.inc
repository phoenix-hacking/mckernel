// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod long_warmup {
    use std::fs::{self, File, OpenOptions};
    use std::io::{self, Read, Seek, SeekFrom, Write};
    use std::os::fd::IntoRawFd;
    use std::path::PathBuf;
    use std::sync::{Arc, Condvar, Mutex};
    use std::time::{Duration, Instant};
    extern "C" { fn close(fd: i32) -> i32; }
    fn invalid(s: &str) -> io::Error { io::Error::new(io::ErrorKind::Other, s) }
    struct Workspace { root: PathBuf, files: Vec<PathBuf>, active: bool }
    impl Workspace {
        fn cleanup(&mut self) -> io::Result<()> {
            for p in &self.files {
                match fs::remove_file(p) {
                    Ok(()) => {},
                    Err(e) if e.kind() == io::ErrorKind::NotFound => {},
                    Err(e) => return Err(e),
                }
            }
            fs::remove_dir(&self.root)?;
            self.active = false;
            if self.root.try_exists()? { return Err(invalid("LONG workspace retained")); }
            Ok(())
        }
    }
    impl Drop for Workspace {
        fn drop(&mut self) {
            if self.active {
                for p in &self.files { let _ = fs::remove_file(p); }
                let _ = fs::remove_dir(&self.root);
            }
        }
    }
    fn worker(id: usize, mut file: File, gate: Arc<(Mutex<(bool, bool)>, Condvar)>) -> io::Result<u64> {
        let mut data = vec![0u8; 8193];
        let mut observed = vec![0u8; 8193];
        {
            let (lock, cv) = &*gate;
            let mut state = lock.lock().map_err(|_| invalid("LONG gate poisoned"))?;
            while !state.0 { state = cv.wait(state).map_err(|_| invalid("LONG gate wait poisoned"))?; }
            if state.1 { return Err(invalid("LONG peer spawn failed")); }
        }
        // Setup is outside the timed interval. Every iteration performs memory
        // generation/checking and genuine seek/write/read/EOF file operations.
        let begin = Instant::now();
        let mut rounds = 0u64;
        loop {
            let seed = (11 + id * 13 + (rounds % 251) as usize) % 251;
            for (i, byte) in data.iter_mut().enumerate() { *byte = ((i * 37 + seed) % 251) as u8; }
            std::hint::black_box(&mut data);
            let mut expected = seed;
            for &byte in &data {
                if usize::from(byte) != expected { return Err(invalid("LONG memory pattern")); }
                expected = (expected + 37) % 251;
            }
            file.seek(SeekFrom::Start(0))?;
            file.write_all(&data)?;
            if file.metadata()?.len() != data.len() as u64 { return Err(invalid("LONG file length")); }
            file.seek(SeekFrom::Start(0))?;
            file.read_exact(&mut observed)?;
            let mut eof = [0u8; 1];
            if observed != data || file.read(&mut eof)? != 0 { return Err(invalid("LONG file contents or EOF")); }
            rounds = rounds.checked_add(1).ok_or_else(|| invalid("LONG round overflow"))?;
            if begin.elapsed() >= Duration::from_secs(3) { break; }
        }
        file.sync_all()?;
        let fd = file.into_raw_fd();
        if unsafe { close(fd) } != 0 { return Err(io::Error::last_os_error()); }
        if rounds == 0 || begin.elapsed() < Duration::from_secs(3) { return Err(invalid("LONG work interval")); }
        Ok(rounds)
    }
    pub fn run() -> io::Result<()> {
        let root = PathBuf::from(format!("p12-long-mixed-app0-{}", std::process::id()));
        fs::create_dir(&root)?;
        let mut workspace = Workspace { root, files: Vec::new(), active: true };
        let mut files = Vec::new();
        for id in 0..2 {
            let p = workspace.root.join(format!("worker{id}.bin"));
            workspace.files.push(p.clone());
            files.push(OpenOptions::new().read(true).write(true).create_new(true).open(p)?);
        }
        let gate = Arc::new((Mutex::new((false, false)), Condvar::new()));
        let mut handles = Vec::new();
        let mut error = None;
        for (id, file) in files.into_iter().enumerate() {
            let shared = Arc::clone(&gate);
            match std::thread::Builder::new().name(format!("long-mixed-{id}")).stack_size(2 * 1024 * 1024).spawn(move || worker(id, file, shared)) {
                Ok(handle) => handles.push(handle),
                Err(e) => { error = Some(e); break; },
            }
        }
        {
            let mut state = gate.0.lock().map_err(|_| invalid("LONG start gate poisoned"))?;
            *state = (true, error.is_some());
            gate.1.notify_all();
        }
        for handle in handles {
            match handle.join() {
                Ok(Ok(rounds)) if rounds > 0 => {},
                Ok(Ok(_)) => { error.get_or_insert_with(|| invalid("LONG no work")); },
                Ok(Err(e)) => { error.get_or_insert(e); },
                Err(_) => { error.get_or_insert_with(|| invalid("LONG worker panic")); },
            }
        }
        let cleanup = workspace.cleanup();
        if let Some(e) = error { return Err(e); }
        cleanup
    }
}

fn main() -> std::io::Result<()> {
    if let Err(e) = pair_pin() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }
    long_warmup::run()?;
    original_main()
}
