// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Fixed original startup.argv-empty PID1 collector; no runtime profile modes.
#![allow(unsafe_op_in_unsafe_fn)]
#[cfg(not(all(
    target_os = "linux",
    target_arch = "x86_64",
    target_endian = "little",
    target_pointer_width = "64"
)))]
compile_error!("this collector's reviewed FFI profile is Linux x86_64 little-endian only");
#[cfg(test)]
mod host_tests;
mod profile;
mod report;
mod supervisor;
#[cfg(test)]
mod tests;

use profile::{BOOT_ARGV, PAYLOAD_ARGV, PAYLOAD_CWD};
const RAW_LIMIT: usize = 262_144;
use std::ffi::{c_char, c_int, c_void, CString};
use std::fs::{File, OpenOptions};
use std::io::Read;
use std::os::fd::AsRawFd;
use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt};
use supervisor::*;

#[repr(C)]
struct SignalAction {
    handler: extern "C" fn(c_int),
    mask: [u64; 16],
    flags: c_int,
    restorer: Option<extern "C" fn()>,
}
const _: [(); 152] = [(); std::mem::size_of::<SignalAction>()];
const _: [(); 8] = [(); std::mem::align_of::<SignalAction>()];
unsafe extern "C" {
    fn getpid() -> c_int;
    fn geteuid() -> u32;
    fn sigaction(signal: c_int, action: *const SignalAction, old: *mut SignalAction) -> c_int;
    fn sigemptyset(mask: *mut [u64; 16]) -> c_int;
    fn alarm(seconds: u32) -> u32;
    fn pause() -> c_int;
    fn mount(
        source: *const c_char,
        target: *const c_char,
        kind: *const c_char,
        flags: u64,
        data: *const c_void,
    ) -> c_int;
    fn klogctl(action: c_int, buffer: *mut c_char, length: c_int) -> c_int;
    fn syncfs(fd: c_int) -> c_int;
}
extern "C" fn outer_expired(_: c_int) {
    // Same predecessor behavior: PID1 remains alive and the separately bounded
    // host owner rejects missing shutdown. No fallback poweroff after expiry.
    loop {
        unsafe {
            pause();
        }
    }
}
fn remain_pid1() -> ! {
    loop {
        sleep_ms(1000);
    }
}
fn kernel_control(action: i32, level: i32) -> Check<()> {
    if unsafe { klogctl(action, std::ptr::null_mut(), level) } != 0 {
        return Err(format!("kernel log control action {action} failed"));
    }
    Ok(())
}
fn mount_one(kind: &str, path: &str) -> Check<()> {
    let kind = CString::new(kind).unwrap();
    let path = CString::new(path).unwrap();
    // Fixed initramfs-owned mounts; EBUSY is an error as in the predecessor.
    if unsafe {
        mount(
            kind.as_ptr(),
            path.as_ptr(),
            kind.as_ptr(),
            0,
            std::ptr::null(),
        )
    } != 0
    {
        return Err("PID1 mount failed".into());
    }
    Ok(())
}
fn helper(
    tag: &str,
    path: &str,
    argv: &[&str],
    outer: u64,
    safe: &mut bool,
    console: Option<&File>,
) -> Check<()> {
    let timeout = if path == "/bin/native-boot" {
        60_000
    } else {
        10_000
    };
    let result = supervise(path, argv, HELPER_ENV, None, timeout, outer);
    if !result.clean {
        *safe = false;
    }
    let mut bad = result.fault
        || result.timeout
        || !result.clean
        || result.status != 0
        || !result.out.eof
        || !result.err.eof
        || result.out.observed != result.out.data.len() as u64
        || result.err.observed != result.err.data.len() as u64;
    let mut evidence_failed = 0;
    let mut evidence_errno = 0;
    for (bit, name, bytes) in [
        (1, "stdout", result.out.data.as_slice()),
        (2, "stderr", result.err.data.as_slice()),
    ] {
        if save(&format!("/case/evidence/{tag}.{name}"), bytes, outer).is_err() {
            bad = true;
            evidence_failed |= bit;
            if evidence_errno == 0 {
                evidence_errno = std::io::Error::last_os_error().raw_os_error().unwrap_or(5);
            }
        }
    }
    let record = format!(
        "status={} fault={} timeout={} clean={} stage={} errno={}\n",
        result.status,
        result.fault as i32,
        result.timeout as i32,
        result.clean as i32,
        result.child_stage,
        result.child_errno
    );
    if save(
        &format!("/case/evidence/{tag}.status"),
        record.as_bytes(),
        outer,
    )
    .is_err()
    {
        bad = true;
        evidence_failed |= 4;
        if evidence_errno == 0 {
            evidence_errno = std::io::Error::last_os_error().raw_os_error().unwrap_or(5);
        }
    }
    if bad {
        if let Some(console) = console {
            let record = format!(concat!("ND_HELPER_FAILURE {{\"tag\":\"{}\",\"raw_wait_status\":{},\"fault\":{},",
                "\"timeout\":{},\"clean\":{},\"stage\":{},\"errno\":{},\"evidence_failed\":{},\"evidence_errno\":{},",
                "\"started_ns\":{},\"reaped_ns\":{},\"finished_ns\":{}}}\n"), tag, result.status, result.fault as i32,
                result.timeout as i32, result.clean as i32, result.child_stage, result.child_errno,
                evidence_failed, evidence_errno, result.started, result.reaped, result.finished);
            let _ = write_all_bounded(console.as_raw_fd(), record.as_bytes(), outer);
            for (name, stream) in [("stdout", &result.out), ("stderr", &result.err)] {
                let row = format!(
                    "ND_HELPER_STREAM {{\"tag\":\"{tag}\",\"stream\":\"{name}\",\"data\":{}}}\n",
                    report::stream_json(stream)
                );
                let _ = write_all_bounded(console.as_raw_fd(), row.as_bytes(), outer);
            }
        }
        Err(format!("helper {tag} failed"))
    } else {
        Ok(())
    }
}
fn poweroff_forever(console: Option<&File>, outer: u64) -> ! {
    let _ = supervise("/poweroff", &["/poweroff"], HELPER_ENV, None, 2000, outer);
    if let Some(console) = console {
        let _ = write_all_bounded(
            console.as_raw_fd(),
            b"native diagnostic teardown error: poweroff returned\n",
            outer,
        );
    }
    remain_pid1()
}
fn main() {
    if unsafe { getpid() } != 1 || unsafe { geteuid() } != 0 {
        std::process::exit(125);
    }
    let beginning = now_ns();
    if beginning == 0 {
        remain_pid1();
    }
    let outer = beginning + 120_000 * MS;
    // The supported Linux x86_64 libc sigaction layout is explicit and needs
    // the same ordinary HOST ABI qualification as all FFI in this candidate.
    let mut action = SignalAction {
        handler: outer_expired,
        mask: [0; 16],
        flags: 0,
        restorer: None,
    };
    if unsafe { sigemptyset(&mut action.mask) } != 0
        || unsafe { sigaction(14, &action, std::ptr::null_mut()) } != 0
    {
        remain_pid1();
    }
    unsafe {
        alarm(120);
    }
    let mut payload = ResultRecord::default();
    let mut console = None;
    let mut safe = true;
    let mut loaded = 0;
    let mut empty = false;
    let mut saved_level = None;
    let operation = (|| -> Check<()> {
        for (kind, path) in [
            ("proc", "/proc"),
            ("sysfs", "/sys"),
            ("devtmpfs", "/dev"),
            ("debugfs", "/sys/kernel/debug"),
        ] {
            mount_one(kind, path)?;
        }
        console = Some(
            OpenOptions::new()
                .write(true)
                .custom_flags(0x800 | 0x80000)
                .open("/dev/console")
                .map_err(|e| format!("console open: {e}"))?,
        );
        std::fs::DirBuilder::new()
            .mode(0o700)
            .create("/case/evidence")
            .or_else(|e| {
                if e.kind() == std::io::ErrorKind::AlreadyExists {
                    Ok(())
                } else {
                    Err(e)
                }
            })
            .map_err(|e| format!("evidence directory: {e}"))?;
        let mut levels = [0u8; 127];
        let mut printk_file =
            File::open("/proc/sys/kernel/printk").map_err(|e| format!("printk level open: {e}"))?;
        let read_count = printk_file.read(&mut levels);
        let close_result = close_file(printk_file);
        let count = read_count.map_err(|e| format!("printk level read: {e}"))?;
        close_result?;
        if count == 0 {
            return Err("empty printk levels".into());
        }
        let first = std::str::from_utf8(&levels[..count])
            .map_err(|_| "invalid printk level text")?
            .split_whitespace()
            .next()
            .ok_or("missing printk level")?
            .parse::<i32>()
            .map_err(|_| "invalid printk level")?;
        if !(1..=8).contains(&first) {
            return Err("printk level outside original range".into());
        }
        kernel_control(6, 0)?;
        saved_level = Some(first);
        save("/case/evidence/printk.original", &levels[..count], outer)?;
        helper(
            "load-ihk",
            "/sbin/insmod",
            &["insmod", "/modules/ihk.ko"],
            outer,
            &mut safe,
            console.as_ref(),
        )?;
        loaded = 1;
        helper(
            "load-smp",
            "/sbin/insmod",
            &[
                "insmod",
                "/modules/ihk-smp-x86_64.ko",
                "ihk_trampoline=524288",
            ],
            outer,
            &mut safe,
            console.as_ref(),
        )?;
        loaded = 2;
        helper(
            "load-mcctrl",
            "/sbin/insmod",
            &["insmod", "/modules/mcctrl.ko"],
            outer,
            &mut safe,
            console.as_ref(),
        )?;
        loaded = 3;
        helper(
            "boot",
            "/bin/native-boot",
            BOOT_ARGV,
            outer,
            &mut safe,
            console.as_ref(),
        )?;
        payload = supervise(
            "/bin/mcexec",
            PAYLOAD_ARGV,
            PAYLOAD_ENV,
            Some(PAYLOAD_CWD),
            10_000,
            outer,
        );
        if !payload.clean {
            safe = false;
        }
        save("/case/evidence/payload.stdout", &payload.out.data, outer)?;
        save("/case/evidence/payload.stderr", &payload.err.data, outer)?;
        let begin_retirement = now_ns();
        let end = bounded_deadline(begin_retirement + 5000 * MS, outer, 0);
        if begin_retirement == 0 {
            return Err("retirement clock unavailable".into());
        }
        loop {
            let current = now_ns();
            if current == 0 || current >= end {
                return Err("original post-reap retirement deadline".into());
            }
            // Preserve original Cstartup namespace retirement; F05's causal
            // gate, child link and actual lifecycle ACK proof are not selected.
            if startup_retirement_ready(current, end, procfs_empty())? {
                empty = true;
                break;
            }
            sleep_ms(10);
        }
        Ok(())
    })();
    let mut good = operation.is_ok();
    if let Err(error) = operation {
        let _ = save("/case/evidence/collector.failure", error.as_bytes(), outer);
    }
    let teardown = format!(
        "modules_loaded={loaded} processes_reaped={} procfs_empty={} nested_os_retained=1\n",
        safe as i32, empty as i32
    );
    if save("/case/evidence/teardown", teardown.as_bytes(), outer).is_err() {
        good = false;
    }
    // Original startup publishes exactly one unchanged raw klogctl(3) snapshot.
    // There is no F05 incremental observer, gate or reconstructed serial stream.
    let mut kernel_log = vec![0u8; RAW_LIMIT];
    let count = unsafe { klogctl(3, kernel_log.as_mut_ptr().cast(), kernel_log.len() as i32) };
    if count < 0 || count == kernel_log.len() as i32 {
        good = false;
    } else {
        kernel_log.truncate(count as usize);
        if save("/case/evidence/kernel.log", &kernel_log, outer).is_err() {
            good = false;
        }
        if let Some(console) = &console {
            if write_all_bounded(console.as_raw_fd(), &kernel_log, outer).is_err()
                || write_all_bounded(console.as_raw_fd(), b"\n", outer).is_err()
            {
                good = false;
            }
        } else {
            good = false;
        }
    }
    if saved_level.is_none()
        || kernel_control(8, saved_level.unwrap_or(0)).is_err()
        || kernel_control(6, 0).is_err()
    {
        good = false;
    }
    match File::open("/case/evidence") {
        Ok(file) => {
            if unsafe { syncfs(file.as_raw_fd()) } != 0 {
                good = false;
            }
            if close_file(file).is_err() {
                good = false;
            }
        }
        Err(_) => good = false,
    }
    if !good || !safe {
        payload.fault = true;
    }
    payload.finished = now_ns();
    if let Some(console) = &console {
        if safe {
            match report::frame(&payload, empty)
                .and_then(|frame| write_frame_once(console.as_raw_fd(), &frame))
            {
                Ok(()) => (),
                Err(_) => payload.fault = true,
            }
        }
    }
    if let Some(level) = saved_level {
        if kernel_control(8, level).is_err() {
            if let Some(console) = &console {
                let _ = write_all_bounded(
                    console.as_raw_fd(),
                    b"native diagnostic teardown error: printk restoration\n",
                    outer,
                );
            }
            remain_pid1();
        }
    }
    poweroff_forever(console.as_ref(), outer);
}
