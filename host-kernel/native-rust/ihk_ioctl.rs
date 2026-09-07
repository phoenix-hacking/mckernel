// SPDX-License-Identifier: GPL-2.0
//! Allocation-free decoder and transaction core for the first IHK ioctls.
//!
//! The native os_runtime adapter connects this allocation-free transaction
//! core to the frozen scalar create, destroy and status ioctls. The adapter
//! owns Linux registration and memory; this core owns decoding and rollback.
//!
//! A caller must complete the provider, kmsg and device-model work
//! before calling `commit_after_external_success`.  Dropping a transaction on
//! any earlier failure restores the registry automatically.

use super::abi::{
    ABI_LONG_BITS, IHK_DEVICE_CREATE_OS, IHK_DEVICE_DESTROY_OS, IHK_OS_QUERY_STATUS,
    IHK_OS_STATUS,
};
use super::os_registry::{
    DestroyGuard, OsHandle, OsRegistry, OsStatus, RegistryError, ReservationGuard, OS_CAPACITY,
};

const ENOENT: i32 = 2;
const ENOMEM: i32 = 12;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EOVERFLOW: i32 = 75;
const ESTALE: i32 = 116;
const EUCLEAN: i32 = 117;

// These describe the attached native adapter, not acceptance or gate credit.
// Status/create/destroy are scalar operations and never dereference arguments.
pub(crate) const NATIVE_DEVICE_REGISTRATION_SUPPORTED: bool = true;
pub(crate) const NATIVE_FILE_OPERATIONS_SUPPORTED: bool = true;
pub(crate) const NATIVE_IOCTL_CALLBACK_SUPPORTED: bool = true;
pub(crate) const USER_COPY_REACHABLE_FROM_IOCTL: bool = false;

const _: [(); 64] = [(); ABI_LONG_BITS as usize];
const _: [(); 64] = [(); OS_CAPACITY];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DeviceIoctl {
    CreateOs { provider_arg: u64 },
    DestroyOs { minor: usize },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum OsIoctl {
    QueryStatus,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum IoctlError {
    InvalidArgument,
    MissingOs,
    Capacity,
    Busy,
    Overflow,
    StaleHandle,
    Corrupt,
}

impl IoctlError {
    pub(crate) const fn errno(self) -> i32 {
        match self {
            Self::InvalidArgument => -EINVAL,
            Self::MissingOs => -ENOENT,
            Self::Capacity => -ENOMEM,
            Self::Busy => -EBUSY,
            Self::Overflow => -EOVERFLOW,
            Self::StaleHandle => -ESTALE,
            Self::Corrupt => -EUCLEAN,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DeviceReply {
    Created(OsHandle),
    Destroyed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ExternalFailure {
    CreateOrSetup(i32),
    DestroyShutdown(i32),
    DestroyProvider(i32),
}

impl DeviceReply {
    /// Frozen ioctl return value: created minor, or zero after destruction.
    pub(crate) const fn return_value(self) -> i64 {
        match self {
            Self::Created(handle) => handle.minor() as i64,
            Self::Destroyed => 0,
        }
    }

    pub(crate) const fn created_handle(self) -> Option<OsHandle> {
        match self {
            Self::Created(handle) => Some(handle),
            Self::Destroyed => None,
        }
    }
}

enum DeviceTransactionInner<'a> {
    Create {
        provider_arg: u64,
        reservation: ReservationGuard<'a>,
    },
    Destroy {
        handle: OsHandle,
        destruction: DestroyGuard<'a>,
    },
}

/// A registry change held unpublished until all external legacy work succeeds.
pub(crate) struct DeviceTransaction<'a> {
    inner: DeviceTransactionInner<'a>,
}

impl DeviceTransaction<'_> {
    pub(crate) const fn decoded(&self) -> DeviceIoctl {
        match &self.inner {
            DeviceTransactionInner::Create { provider_arg, .. } => DeviceIoctl::CreateOs {
                provider_arg: *provider_arg,
            },
            DeviceTransactionInner::Destroy { handle, .. } => DeviceIoctl::DestroyOs {
                minor: handle.minor(),
            },
        }
    }

    pub(crate) const fn handle(&self) -> OsHandle {
        match &self.inner {
            DeviceTransactionInner::Create { reservation, .. } => reservation.handle(),
            DeviceTransactionInner::Destroy { handle, .. } => *handle,
        }
    }

    /// The initial native adapter cannot stop CPUs or retire boot mappings.
    /// Require the status captured by the exclusive destruction guard, rather
    /// than a separate observation that could race a future boot transition.
    pub(crate) fn require_unbooted_destroy(&self) -> Result<(), IoctlError> {
        match &self.inner {
            DeviceTransactionInner::Destroy { destruction, .. } => {
                match destruction.status().map_err(map_registry_error)? {
                    OsStatus::NotBooted => Ok(()),
                    _ => Err(IoctlError::Busy),
                }
            }
            DeviceTransactionInner::Create { .. } => Err(IoctlError::InvalidArgument),
        }
    }

    /// Consume a failed external transaction while preserving legacy errno.
    ///
    /// Create/setup and forced-shutdown failures propagate.  The frozen
    /// destroy path maps only a provider `destroy_os` failure to `-EINVAL`.
    /// Invalid transaction/stage pairings also fail closed with `-EINVAL`.
    /// In every case the contained registry guard rolls back as `self` drops.
    pub(crate) fn abort_external_failure(self, failure: ExternalFailure) -> i32 {
        match (&self.inner, failure) {
            (DeviceTransactionInner::Create { .. }, ExternalFailure::CreateOrSetup(errno)) => {
                errno
            }
            (DeviceTransactionInner::Destroy { .. }, ExternalFailure::DestroyShutdown(errno)) => {
                errno
            }
            (DeviceTransactionInner::Destroy { .. }, ExternalFailure::DestroyProvider(_)) => {
                -EINVAL
            }
            _ => -EINVAL,
        }
    }

    /// Publish the registry change after provider/device-model success.
    pub(crate) fn commit_after_external_success(self) -> Result<DeviceReply, IoctlError> {
        match self.inner {
            DeviceTransactionInner::Create { reservation, .. } => reservation
                .commit()
                .map(DeviceReply::Created)
                .map_err(map_registry_error),
            DeviceTransactionInner::Destroy { destruction, .. } => destruction
                .commit()
                .map(|()| DeviceReply::Destroyed)
                .map_err(map_registry_error),
        }
    }
}

pub(crate) struct IhkIoctlDispatcher<'a> {
    registry: &'a OsRegistry,
}

impl<'a> IhkIoctlDispatcher<'a> {
    pub(crate) const fn new(registry: &'a OsRegistry) -> Self {
        Self { registry }
    }

    /// Decode a frozen device ioctl without dereferencing the scalar argument.
    pub(crate) const fn decode_device(
        request: u32,
        argument: u64,
    ) -> Result<DeviceIoctl, IoctlError> {
        match request {
            IHK_DEVICE_CREATE_OS => Ok(DeviceIoctl::CreateOs {
                provider_arg: argument,
            }),
            IHK_DEVICE_DESTROY_OS => {
                if argument >= OS_CAPACITY as u64 {
                    Err(IoctlError::InvalidArgument)
                } else {
                    Ok(DeviceIoctl::DestroyOs {
                        minor: argument as usize,
                    })
                }
            }
            _ => Err(IoctlError::InvalidArgument),
        }
    }

    /// Decode the two frozen status aliases.  Both return the status directly.
    pub(crate) const fn decode_os(request: u32) -> Result<OsIoctl, IoctlError> {
        match request {
            IHK_OS_QUERY_STATUS | IHK_OS_STATUS => Ok(OsIoctl::QueryStatus),
            _ => Err(IoctlError::InvalidArgument),
        }
    }

    /// Reserve the registry side of a create or destroy transaction.
    pub(crate) fn prepare_device(
        &'a self,
        request: u32,
        argument: u64,
    ) -> Result<DeviceTransaction<'a>, IoctlError> {
        match Self::decode_device(request, argument)? {
            DeviceIoctl::CreateOs { provider_arg } => {
                let reservation = self.registry.reserve().map_err(map_registry_error)?;
                Ok(DeviceTransaction {
                    inner: DeviceTransactionInner::Create {
                        provider_arg,
                        reservation,
                    },
                })
            }
            DeviceIoctl::DestroyOs { minor } => {
                let handle = self
                    .registry
                    .resolve_minor(minor)
                    .map_err(map_legacy_destroy_lookup_error)?;
                let destruction = self
                    .registry
                    .begin_destroy(handle)
                    .map_err(map_registry_error)?;
                Ok(DeviceTransaction {
                    inner: DeviceTransactionInner::Destroy {
                        handle,
                        destruction,
                    },
                })
            }
        }
    }

    /// Return an OS status by generation-tagged open identity.
    ///
    /// The frozen status commands have no pointed-to argument and perform no
    /// copy-from-user or copy-to-user operation; their status is the ioctl
    /// return value itself.
    pub(crate) fn dispatch_os(
        &self,
        handle: OsHandle,
        request: u32,
        _argument: u64,
    ) -> Result<i64, IoctlError> {
        match Self::decode_os(request)? {
            OsIoctl::QueryStatus => self
                .registry
                .snapshot(handle)
                .map(|snapshot| snapshot.status as i64)
                .map_err(map_registry_error),
        }
    }
}

const fn map_registry_error(error: RegistryError) -> IoctlError {
    match error {
        RegistryError::NotFound => IoctlError::MissingOs,
        RegistryError::Capacity => IoctlError::Capacity,
        RegistryError::Busy => IoctlError::Busy,
        RegistryError::InvalidMinor | RegistryError::InvalidTransition => {
            IoctlError::InvalidArgument
        }
        RegistryError::GenerationExhausted | RegistryError::ReferenceOverflow => {
            IoctlError::Overflow
        }
        RegistryError::StaleHandle => IoctlError::StaleHandle,
        RegistryError::Corrupt => IoctlError::Corrupt,
    }
}

const fn map_legacy_destroy_lookup_error(error: RegistryError) -> IoctlError {
    match error {
        RegistryError::NotFound | RegistryError::InvalidMinor => IoctlError::InvalidArgument,
        other => map_registry_error(other),
    }
}
