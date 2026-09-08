// SPDX-License-Identifier: GPL-2.0
//! Physical image request ownership through the traditional prepare reply.

use super::{application_image as wire, application_rpc::Exchange, smp_memory::BootPages};
use kernel::prelude::*;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

fn copy(bytes: &[u8]) -> Result<Vec<u8>> {
    let mut output = Vec::with_capacity(bytes.len(), GFP_KERNEL)?;
    for byte in bytes {
        output.push(*byte, GFP_KERNEL)?;
    }
    Ok(output)
}

struct Buffers {
    descriptor: BootPages,
    _args: BootPages,
    _envs: BootPages,
}

pub(crate) struct Preparation {
    pub(crate) exchange: Exchange,
    pub(crate) input: wire::Input,
    original: Vec<u8>,
    output: Vec<u8>,
    buffers: Option<Buffers>,
    result: Option<i32>,
    pub(crate) thread: u64,
    pub(crate) page_table: u64,
}

impl Preparation {
    pub(crate) fn new(os: i32, bytes: &[u8], cpus: usize, direct_map: u64) -> Result<Self> {
        let input = wire::Input::parse(bytes, cpus).map_err(errno)?;
        let original = copy(&bytes[..input.descriptor])?;
        let output = copy(&original)?;
        let mut descriptor = BootPages::allocate(wire::DESCRIPTOR_CAPACITY, direct_map)?;
        let mut args = BootPages::allocate(input.args, direct_map)?;
        let mut envs = BootPages::allocate(input.envs, direct_map)?;
        args.put(0, &bytes[input.descriptor..input.descriptor + input.args])?;
        envs.put(0, &bytes[input.descriptor + input.args..])?;
        descriptor.put(0, &original)?;
        descriptor.put(wire::ARGS, &args.physical().to_le_bytes())?;
        descriptor.put(wire::ENVS, &envs.physical().to_le_bytes())?;
        descriptor.put(wire::THREAD, &[0; 16])?;
        for section in (wire::HEADER..input.descriptor).step_by(wire::SECTION) {
            descriptor.put(section + 16, &[0; 8])?;
        }
        let exchange =
            Exchange::prepare(os, input.cpu, input.pid, descriptor.physical()).map_err(errno)?;
        Ok(Self {
            exchange,
            input,
            original,
            output,
            buffers: Some(Buffers {
                descriptor,
                _args: args,
                _envs: envs,
            }),
            result: None,
            thread: 0,
            page_table: 0,
        })
    }

    /// Called only after the exact response has retired the peer's mappings.
    /// Keep all three physical owners until then, including after caller exit.
    pub(crate) fn finish(&mut self, mut memory: impl FnMut(u64, usize) -> Result) -> Result {
        let peer = self.exchange.result().ok_or(EBUSY)?;
        let outcome = (|| -> Result {
            kernel::error::to_result(peer)?;
            self.buffers
                .as_ref()
                .ok_or(EIO)?
                .descriptor
                .read_into(&mut self.output)?;
            for offset in [
                0,
                wire::USER_START,
                wire::USER_END,
                wire::ARGS_LEN,
                wire::ENVS_LEN,
            ] {
                if wire::word(&self.output, offset).map_err(errno)?
                    != wire::word(&self.original, offset).map_err(errno)?
                {
                    return Err(errno(-71));
                }
            }
            for offset in [wire::NUM_SECTIONS, wire::CPU, wire::PID] {
                if wire::integer(&self.output, offset).map_err(errno)?
                    != wire::integer(&self.original, offset).map_err(errno)?
                {
                    return Err(errno(-71));
                }
            }
            let thread = wire::word(&self.output, wire::THREAD).map_err(errno)?;
            let table = wire::word(&self.output, wire::PAGE_TABLE).map_err(errno)?;
            if thread < 0xffff_8000_0000_0000 || thread % 8 != 0 || table == 0 || table % 4096 != 0
            {
                return Err(errno(-71));
            }
            memory(table, 4096)?;
            self.thread = thread;
            self.page_table = table;
            let start = wire::word(&self.original, wire::USER_START).map_err(errno)?;
            let end = wire::word(&self.original, wire::USER_END).map_err(errno)?;
            for offset in (wire::HEADER..self.input.descriptor).step_by(wire::SECTION) {
                let section = &self.output[offset..offset + wire::SECTION];
                let old = &self.original[offset..offset + wire::SECTION];
                // Only the relocated VA and newly allocated physical address
                // may change. File geometry and permissions belong to input.
                if section[8..16] != old[8..16] || section[24..] != old[24..] {
                    return Err(errno(-71));
                }
                let address = wire::word(section, 0).map_err(errno)?;
                let length = wire::word(section, 8).map_err(errno)?;
                let physical = wire::word(section, 16).map_err(errno)?;
                let filesz = wire::word(section, 24).map_err(errno)?;
                if address < start || address.checked_add(length).is_none_or(|last| last > end) {
                    return Err(errno(-71));
                }
                if filesz != 0 {
                    let bytes = filesz
                        .checked_add(address & 4095)
                        .and_then(|n| n.checked_add(4095))
                        .ok_or(errno(-75))?
                        & !4095;
                    if physical % 4096 != 0 {
                        return Err(errno(-71));
                    }
                    memory(physical, bytes as usize)?;
                }
            }
            // Keep the user's original opaque addresses in its returned ABI;
            // the physical Linux request buffers are never exposed to it.
            for offset in [wire::ARGS, wire::ENVS] {
                wire::put_word(
                    &mut self.output,
                    offset,
                    wire::word(&self.original, offset).map_err(errno)?,
                )
                .map_err(errno)?;
            }
            Ok(())
        })();
        self.result = Some(outcome.as_ref().err().map_or(0, |error| error.to_errno()));
        // Even an error acknowledgement ends the guest's input-buffer borrow.
        // A malformed success may leave a prepared task; the connection must
        // retain/quarantine that state rather than infer successful retirement.
        drop(self.buffers.take());
        outcome
    }

    pub(crate) fn result(&self) -> Option<i32> {
        self.result
    }

    /// PREPARE's kernel-only caller overwrites these raw kuid/kgid scalars
    /// from its retained credentials. Never borrow a task after dropping RCU.
    pub(crate) fn procfs_credentials(&self) -> Result<(u32, u32)> {
        Ok((
            wire::integer(&self.original, wire::CREDENTIALS).map_err(errno)? as u32,
            wire::integer(&self.original, wire::CREDENTIALS + 16).map_err(errno)? as u32,
        ))
    }

    pub(crate) fn copy_result(&self, output: &mut [u8]) -> Result {
        kernel::error::to_result(self.result.ok_or(EBUSY)?)?;
        output
            .get_mut(..self.output.len())
            .ok_or(EINVAL)?
            .copy_from_slice(&self.output);
        Ok(())
    }

    pub(crate) fn authorize_transfer(&self, physical: u64, length: usize) -> Result {
        kernel::error::to_result(self.result.ok_or(EBUSY)?)?;
        if length == 0 {
            return Err(EINVAL);
        }
        let last = physical.checked_add(length as u64).ok_or(EINVAL)?;
        for section in self.output[wire::HEADER..].chunks_exact(wire::SECTION) {
            let address = wire::word(section, 0).map_err(errno)?;
            let start = wire::word(section, 16).map_err(errno)?;
            let filesz = wire::word(section, 24).map_err(errno)?;
            if filesz == 0 {
                continue;
            }
            let bytes = filesz
                .checked_add(address & 4095)
                .and_then(|n| n.checked_add(4095))
                .ok_or(EINVAL)?
                & !4095;
            let end = start.checked_add(bytes).ok_or(EINVAL)?;
            if physical >= start && last <= end {
                return Ok(());
            }
        }
        Err(EACCES)
    }
}
