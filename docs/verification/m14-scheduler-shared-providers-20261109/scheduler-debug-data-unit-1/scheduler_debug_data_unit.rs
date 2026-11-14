#![no_std]

#[path = "debug_type.rs"]
mod debug;

#[cfg(process_verbose_data)]
pub(crate) mod process_verbose_data;
