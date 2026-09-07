// SPDX-License-Identifier: GPL-2.0
//! Standalone source-fixture producer for the native FP-0006 status aliases.
//!
//! The private userspace registry is populated and moved to RUNNING only as
//! fixture setup.  No create-ioctl behavior, module runtime, registration,
//! reachability, gate result, or tracker credit is claimed by this program.

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
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::Path;
use std::process;

use abi::{IHK_OS_QUERY_STATUS, IHK_OS_STATUS};
use ihk_ioctl::IhkIoctlDispatcher;
use os_registry::{OsRegistry, OsStatus};

const RUNNING: i64 = 5;
const SURFACE: &str = "native-rust-source-fixture";
const VECTOR_COUNT: usize = 4;

struct Vector {
    id: &'static str,
    request: u32,
    argument: u64,
}

const VECTORS: [Vector; VECTOR_COUNT] = [
    Vector {
        id: "query-status-arg0",
        request: IHK_OS_QUERY_STATUS,
        argument: 0,
    },
    Vector {
        id: "query-status-arg-u64-max",
        request: IHK_OS_QUERY_STATUS,
        argument: u64::MAX,
    },
    Vector {
        id: "status-alias-arg0",
        request: IHK_OS_STATUS,
        argument: 0,
    },
    Vector {
        id: "status-alias-arg-u64-max",
        request: IHK_OS_STATUS,
        argument: u64::MAX,
    },
];

const RAW_RECORDS: &str = concat!(
    "{\"argument\":0,\"request\":1124867,\"sequence\":0,",
    "\"vector_id\":\"query-status-arg0\"}\n",
    "{\"argument\":18446744073709551615,\"request\":1124867,",
    "\"sequence\":1,\"vector_id\":\"query-status-arg-u64-max\"}\n",
    "{\"argument\":0,\"request\":1124884,\"sequence\":2,",
    "\"vector_id\":\"status-alias-arg0\"}\n",
    "{\"argument\":18446744073709551615,\"request\":1124884,",
    "\"sequence\":3,\"vector_id\":\"status-alias-arg-u64-max\"}\n",
);

fn append_ledger(
    output: &mut String,
    sequence: usize,
    phase: &str,
    status: i64,
) {
    output.push_str(&format!(
        "{{\"minor\":0,\"phase\":\"{}\",\"sequence\":{},\"status\":{},\"status_name\":\"RUNNING\",\"surface\":\"{}\",\"vector_id\":\"{}\"}}\n",
        phase, sequence, status, SURFACE, VECTORS[sequence].id
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
    let metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect {}: {}", name, error))?;
    if !metadata.is_file()
        || metadata.nlink() != 1
        || metadata.permissions().mode() & 0o7777 != 0o444
        || metadata.len() != data.len() as u64
    {
        return Err(format!("{} publication identity differs", name));
    }
    Ok(())
}

fn emit(output: &Path) -> Result<(), String> {
    let metadata = fs::symlink_metadata(output)
        .map_err(|error| format!("capture output directory is unavailable: {}", error))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err("capture output must be a non-symlink directory".to_owned());
    }

    let registry = OsRegistry::new();
    let handle = registry
        .reserve()
        .map_err(|error| format!("private setup reservation failed: {:?}", error))?
        .commit()
        .map_err(|error| format!("private setup commit failed: {:?}", error))?;
    if handle.minor() != 0 {
        return Err("private setup did not select minor zero".to_owned());
    }
    registry
        .transition(handle, OsStatus::Booting)
        .and_then(|()| registry.transition(handle, OsStatus::Running))
        .map_err(|error| format!("private setup transition failed: {:?}", error))?;

    let dispatcher = IhkIoctlDispatcher::new(&registry);
    let mut result_records = String::new();
    let mut ledger_records = String::new();
    for (sequence, vector) in VECTORS.iter().enumerate() {
        let before = registry
            .snapshot(handle)
            .map_err(|error| format!("pre-vector snapshot failed: {:?}", error))?;
        let interface_return = dispatcher
            .dispatch_os(handle, vector.request, vector.argument)
            .map_err(|error| format!("status dispatch failed: {:?}", error))?;
        let after = registry
            .snapshot(handle)
            .map_err(|error| format!("post-vector snapshot failed: {:?}", error))?;
        if before != after
            || before.status != OsStatus::Running
            || interface_return != RUNNING
        {
            return Err("status vector changed state or returned a non-RUNNING value".to_owned());
        }
        result_records.push_str(&format!(
            "{{\"errno\":0,\"interface_return\":{},\"normalized_return\":{},\"sequence\":{},\"surface\":\"{}\",\"vector_id\":\"{}\"}}\n",
            interface_return,
            interface_return,
            sequence,
            SURFACE,
            vector.id
        ));
        append_ledger(&mut ledger_records, sequence, "before", before.status as i64);
        append_ledger(&mut ledger_records, sequence, "after", after.status as i64);
    }

    write_member(output, "raw.jsonl", RAW_RECORDS.as_bytes())?;
    write_member(output, "result.jsonl", result_records.as_bytes())?;
    write_member(output, "state-ledger.jsonl", ledger_records.as_bytes())?;
    File::open(output)
        .and_then(|directory| directory.sync_all())
        .map_err(|error| format!("cannot synchronize capture directory: {}", error))?;
    Ok(())
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() == 2 && arguments[1] == "--describe" {
        println!(
            "{{\"contract_id\":\"fp-0006-ihk-os-status-alias-v1\",\"gate_pass\":false,\"native_module_runtime_executed\":false,\"surface\":\"native-rust-source-fixture\",\"tracker_credit\":false}}"
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
