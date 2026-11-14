//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private current provider composition; actual ABI generation precedes compilation.

#[path = "accepted_host_root.assigned_memory_dependency_join.rs"]
mod accepted_cpu_memory;

#[path = "ihklib_mcstat_shared_readable.rs"]
mod ihklib_mcstat;

#[path = "ihklib_eventfd.rs"]
mod owned_eventfd;

#[path = "ihklib_perf.rs"]
mod perf_pages;

#[path = "ihklib_dump.rs"]
mod dump_correctness;

// Existing Rust rusage layout: the paired C witness checks the actual headers.
const _: [(); 16_568] = [(); core::mem::size_of::<ihklib_mcstat::IhkOsRusage>()];

#[path = "ihklib_cli_parsers_ikc_shared.rs"]
mod ihklib_cli_parsers;

#[path = "ihklib_ikc.rs"]
mod ihklib_ikc;

#[path = "ihklib_status_kmsg.rs"]
mod ihklib_status_kmsg;

#[path = "ihklib_mcstat_memory_shared_parser.rs"]
mod ihklib_mcstat_memory;

#[path = "ihklib_runtime_state.rs"]
mod runtime_state;

use accepted_cpu_memory::{ihklib_device_open, IhkCpuReq};

#[path = "ihklib_os_cpu.rs"]
mod os_cpu;

#[path = "ihklib_os_instance_lifecycle.rs"]
mod os_instances;

#[path = "ihklib_os_load_boot.rs"]
mod os_load_boot;

#[path = "ihklib_kmsg_control.rs"]
mod kmsg_control;

#[path = "ihklib_shutdown_freeze.rs"]
mod shutdown_freeze;

#[path = "ihklib_configuration_report.rs"]
mod configuration_report;

#[path = "ihklib_ikc_map.rs"]
mod ikc_map;

#[path = "ihklib_os_kargs.rs"]
mod os_kargs;

#[path = "ihklib_environment.rs"]
mod environment;

#[path = "ihklib_raw_strings.rs"]
mod raw_strings;

#[path = "ihklib_create_os_environment.rs"]
mod create_os_environment;

#[path = "ihklib_legacy_data.rs"]
mod legacy_data;

#[path = "public_export_signatures.rs"]
mod public_export_signatures;

#[path = "private_export_signatures.rs"]
mod private_export_signatures;
