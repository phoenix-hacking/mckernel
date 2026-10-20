// SPDX-License-Identifier: GPL-2.0-only
//! Sleepable remote attributes with reply progress independent of tree removal.

use super::{
    sysfs_objects::AttributeOps,
    sysfs_request::Client,
    sysfs_rpc::{Call, Exchange, DATA_BYTES, PACKET_BYTES},
    sysfs_setup::SharedData,
};
use core::{
    ptr,
    sync::atomic::{AtomicBool, Ordering},
};
use kernel::{
    prelude::*,
    sync::{new_condvar, new_mutex, Arc, CondVar, Mutex},
};

fn errno(value: i32) -> Error {
    kernel::error::to_result(value).err().unwrap_or(EIO)
}

struct State {
    exchange: Exchange,
    caller: bool,
}

#[pin_data]
pub(crate) struct Remote {
    data: SharedData,
    #[pin]
    state: Mutex<State>,
    #[pin]
    changed: CondVar,
}

impl Remote {
    /// # Safety
    /// data is the exclusive checked shared-data allocation for its exact OS
    /// generation. Its backing allocation and module owner outlive every Arc
    /// returned here, including callbacks and outstanding peer exchanges.
    /// The peer accesses it only for the one published request; no Rust slice
    /// aliases its bytes. No other remote service may claim the same page.
    pub(crate) unsafe fn new(data: SharedData) -> Result<Arc<Self>> {
        if data.bytes != DATA_BYTES
            || data.address == 0
            || data.physical == 0
            || data.address % DATA_BYTES as u64 != 0
            || data.physical % DATA_BYTES as u64 != 0
            || data.address.checked_add(DATA_BYTES as u64).is_none()
            || data.physical.checked_add(DATA_BYTES as u64).is_none()
        {
            return Err(EINVAL);
        }
        Arc::pin_init(
            pin_init!(Self {
                data,
                state <- new_mutex!(State { exchange: Exchange::new(), caller: false }),
                changed <- new_condvar!(),
            }),
            GFP_KERNEL,
        )
    }

    /// Execute only the queue reservation/publication while holding this lock.
    /// The transport callback must not sleep waiting for a peer response or
    /// reacquire this service. An error MUST mean no packet was published;
    /// queue-full may retry later. Notify the guest after this method succeeds.
    pub(crate) fn publish(&self, send: impl FnOnce(&[u8; PACKET_BYTES]) -> Result) -> Result<bool> {
        let mut state = self.state.lock();
        let Some((token, packet)) = state.exchange.outgoing() else {
            return Ok(false);
        };
        send(&packet)?;
        state.exchange.published(token).map_err(errno)?;
        Ok(true)
    }

    pub(crate) fn queued(&self) -> bool {
        self.state.lock().exchange.outgoing().is_some()
    }

    /// The queue consumer must acquire the response publication before this
    /// call. It runs independently of the tree/removal lock and caller waits.
    pub(crate) fn reply(&self, packet: &[u8]) -> Result {
        self.state.lock().exchange.accept(packet).map_err(errno)?;
        self.changed.notify_all();
        Ok(())
    }

    fn call(
        &self,
        client: Client,
        call: Call,
        input: &[u8],
        output: &mut [u8],
        interruptible: bool,
    ) -> Result<usize> {
        let mut state = self.state.lock();
        while state.caller {
            if interruptible {
                if self.changed.wait_interruptible(&mut state) {
                    return Err(EINTR);
                }
            } else {
                self.changed.wait(&mut state);
            }
        }
        state.caller = true;
        // This scope always releases the caller flag, including an interrupted
        // wait, but deliberately retains any outstanding exchange and its data.
        let result = (|| {
            if let Some(token) = state.exchange.token() {
                while !state.exchange.completed(token).map_err(errno)? {
                    if interruptible {
                        if self.changed.wait_interruptible(&mut state) {
                            return Err(EINTR);
                        }
                    } else {
                        self.changed.wait(&mut state);
                    }
                }
                // A preceding caller left on a signal; its completed result is
                // discarded only after the peer has retired that exact token.
                let _ = state.exchange.finish(token).map_err(errno)?;
            }
            let token = state.exchange.begin(client, call).map_err(errno)?;
            if let Call::Store { bytes } = call {
                debug_assert_eq!(bytes, input.len());
                for (index, byte) in input.iter().copied().enumerate() {
                    // SAFETY: begin bounds bytes to this retained page. This
                    // sole caller fills it before publish can acquire the lock.
                    unsafe { ptr::write_volatile((self.data.address as *mut u8).add(index), byte) };
                }
            }
            while !state.exchange.completed(token).map_err(errno)? {
                if interruptible {
                    if self.changed.wait_interruptible(&mut state) {
                        return Err(EINTR);
                    }
                } else {
                    self.changed.wait(&mut state);
                }
            }
            let bytes = state
                .exchange
                .finish(token)
                .map_err(errno)?
                .map_err(errno)?;
            if matches!(call, Call::Show { .. }) {
                for (index, byte) in output.get_mut(..bytes).ok_or(EIO)?.iter_mut().enumerate() {
                    // SAFETY: The matching acquired response retires the peer's
                    // write. The state lock and caller flag exclude a new call
                    // until these bounded volatile reads have completed.
                    *byte =
                        unsafe { ptr::read_volatile((self.data.address as *const u8).add(index)) };
                }
            }
            Ok(bytes)
        })();
        state.caller = false;
        drop(state);
        self.changed.notify_all();
        result
    }
}

/// Keep one construction reference until Tree::create returns. Only successful
/// publication arms guest release; failed Linux adds must not free an instance
/// still owned by the guest that receives the create error.
pub(crate) struct Attribute {
    remote: Arc<Remote>,
    client: Client,
    published: AtomicBool,
}

impl Attribute {
    pub(crate) fn new(remote: Arc<Remote>, client: Client) -> Result<Arc<Self>> {
        if (1..=1000).contains(&client.operations) {
            return Err(EINVAL);
        }
        Ok(Arc::new(
            Self {
                remote,
                client,
                published: AtomicBool::new(false),
            },
            GFP_KERNEL,
        )?)
    }

    pub(crate) fn arm(&self) {
        self.published.store(true, Ordering::Release);
    }
}

impl AttributeOps for Arc<Attribute> {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        self.remote.call(
            self.client,
            Call::Show {
                capacity: output.len(),
            },
            &[],
            output,
            true,
        )
    }

    fn store(&self, input: &[u8]) -> Result<usize> {
        self.remote.call(
            self.client,
            Call::Store { bytes: input.len() },
            input,
            &mut [],
            true,
        )
    }
}

impl Drop for Attribute {
    fn drop(&mut self) {
        if self.published.load(Ordering::Acquire) && self.client.operations != 0 {
            // File owns this Arc until sysfs_remove_file has drained callbacks.
            // Wait uninterruptibly for release: a signal must not let unlink
            // acknowledge while McKernel can still access the instance.
            if let Err(error) = self
                .remote
                .call(self.client, Call::Release, &[], &mut [], false)
            {
                pr_err!(
                    "IHK-SMP: remote sysfs release failed os={} generation={} error={}\n",
                    self.remote.data.owner.slot(),
                    self.remote.data.owner.generation(),
                    error.to_errno()
                );
            }
        }
    }
}
