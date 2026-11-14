// SPDX-License-Identifier: GPL-2.0
//! Standalone source-fixture producer for the native side of FP-0006.
//!
//! This binary exercises the allocation-free Rust dispatcher and registry in
//! userspace.  It is deliberately not a native module runtime, registration,
//! or userspace-reachability test, and its capture cannot award gate credit.

#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod abi;

#[path = "../../../host-kernel/native-rust/os_registry.rs"]
mod os_registry;

#[path = "../../../host-kernel/native-rust/ihk_ioctl.rs"]
mod ihk_ioctl;

use std::env;
use std::fs::{self, File, OpenOptions, Permissions};
use std::io::Write;
use std::os::unix::fs::PermissionsExt;
use std::path::Path;
use std::process;

use abi::IHK_DEVICE_DESTROY_OS;
use ihk_ioctl::{IhkIoctlDispatcher, IoctlError};
use os_registry::{OsRegistry, RegistryError, OS_CAPACITY};

const UNKNOWN_DEVICE_REQUEST: u32 = 0xffff_ffff;
const UNKNOWN_ID: &str = "unknown-device-request-ffffffff-arg0";
const DESTROY_ID: &str = "destroy-known-empty-minor63";
const RAW_RECORDS: &str = concat!(
    "{\"argument\":0,\"request\":4294967295,\"sequence\":0,",
    "\"vector_id\":\"unknown-device-request-ffffffff-arg0\"}\n",
    "{\"argument\":63,\"request\":1124609,\"sequence\":1,",
    "\"vector_id\":\"destroy-known-empty-minor63\"}\n",
);

fn occupied_bitmap(registry: &OsRegistry) -> Result<u64, String> {
    let mut bitmap = 0_u64;
    for minor in 0..OS_CAPACITY {
        match registry.resolve_minor(minor) {
            Ok(_) => bitmap |= 1_u64 << minor,
            Err(RegistryError::NotFound) => {}
            Err(error) => {
                return Err(format!(
                    "registry observation failed at minor {}: {:?}",
                    minor, error
                ));
            }
        }
    }
    Ok(bitmap)
}

fn negative_errno(result: Result<ihk_ioctl::DeviceTransaction<'_>, IoctlError>) -> Result<i32, String> {
    match result {
        Ok(transaction) => {
            drop(transaction);
            Err("negative vector unexpectedly prepared a transaction".to_owned())
        }
        Err(error) => Ok(error.errno()),
    }
}

fn append_ledger(
    output: &mut String,
    sequence: usize,
    vector_id: &str,
    phase: &str,
    bitmap: u64,
) {
    output.push_str(&format!(
        "{{\"minor63_empty\":true,\"occupied_minor_bitmap\":\"{:016x}\",\"occupied_minor_count\":{},\"phase\":\"{}\",\"sequence\":{},\"surface\":\"native-rust-source-fixture\",\"vector_id\":\"{}\"}}\n",
        bitmap,
        bitmap.count_ones(),
        phase,
        sequence,
        vector_id
    ));
}

fn write_member(root: &Path, name: &str, data: &[u8]) -> Result<(), String> {
    let path = root.join(name);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|error| format!("cannot create {}: {}", name, error))?;
    file.set_permissions(Permissions::from_mode(0o444))
        .map_err(|error| format!("cannot set {} mode: {}", name, error))?;
    file.write_all(data)
        .map_err(|error| format!("cannot write {}: {}", name, error))?;
    file.sync_all()
        .map_err(|error| format!("cannot synchronize {}: {}", name, error))?;
    Ok(())
}

fn emit(output: &Path) -> Result<(), String> {
    let metadata = fs::symlink_metadata(output)
        .map_err(|error| format!("capture output directory is unavailable: {}", error))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err("capture output must be a non-symlink directory".to_owned());
    }

    let registry = OsRegistry::new();
    let dispatcher = IhkIoctlDispatcher::new(&registry);
    let mut states = [0_u64; 4];
    states[0] = occupied_bitmap(&registry)?;
    let unknown = negative_errno(dispatcher.prepare_device(UNKNOWN_DEVICE_REQUEST, 0))?;
    states[1] = occupied_bitmap(&registry)?;
    states[2] = occupied_bitmap(&registry)?;
    let destroy = negative_errno(dispatcher.prepare_device(IHK_DEVICE_DESTROY_OS, 63))?;
    states[3] = occupied_bitmap(&registry)?;

    if unknown != -22 || destroy != -22 || states != [0, 0, 0, 0] {
        return Err("standalone source-fixture observation differs from the bounded contract".to_owned());
    }

    let result_records = format!(
        concat!(
            "{{\"errno\":0,\"interface_return\":{},\"normalized_return\":{},",
            "\"sequence\":0,\"surface\":\"native-rust-source-fixture\",",
            "\"vector_id\":\"{}\"}}\n",
            "{{\"errno\":0,\"interface_return\":{},\"normalized_return\":{},",
            "\"sequence\":1,\"surface\":\"native-rust-source-fixture\",",
            "\"vector_id\":\"{}\"}}\n"
        ),
        unknown, unknown, UNKNOWN_ID, destroy, destroy, DESTROY_ID
    );
    let mut ledger_records = String::new();
    append_ledger(&mut ledger_records, 0, UNKNOWN_ID, "before", states[0]);
    append_ledger(&mut ledger_records, 0, UNKNOWN_ID, "after", states[1]);
    append_ledger(&mut ledger_records, 1, DESTROY_ID, "before", states[2]);
    append_ledger(&mut ledger_records, 1, DESTROY_ID, "after", states[3]);

    write_member(output, "raw.jsonl", RAW_RECORDS.as_bytes())?;
    write_member(output, "result.jsonl", result_records.as_bytes())?;
    write_member(
        output,
        "state-ledger.jsonl",
        ledger_records.as_bytes(),
    )?;
    File::open(output)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| format!("cannot synchronize capture directory: {}", error))?;
    Ok(())
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() == 2 && arguments[1] == "--describe" {
        println!(
            "{{\"contract_id\":\"fp-0006-ihk-device-negative-dispatch-v1\",\"native_module_runtime_executed\":false,\"surface\":\"native-rust-source-fixture\",\"tracker_credit\":false}}"
        );
        return;
    }
    if arguments.len() != 2 {
        eprintln!("usage: {} OUTPUT_DIRECTORY", arguments[0]);
        process::exit(64);
    }
    if let Err(error) = emit(Path::new(&arguments[1])) {
        eprintln!("{}", error);
        process::exit(1);
    }
}
