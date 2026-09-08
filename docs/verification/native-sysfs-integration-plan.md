# Native sysfs integration

Source parent: `96dde3b4461f604ca474809ba3649cbf444da005`.
Target: the pinned Linux `6.12.0-211.44.1.el10_2`, native Rust 1.92 and
revision-3 McKernel image from the completed vDSO service checkpoint.

Both native startup interfaces currently reach `SCD_MSG_SYSFS_REQ_SETUP`
(0x40). Its argument is at IKC packet byte 24. The captured setup request is
1,056 bytes, with buffer physical address at 8, buffer size at 16 and busy at
1,052. The shared data allocation is a separate 4 KiB page. Setup must publish
success only after its real host objects and required files exist. Full boot,
continuing runtime dispatch, applications and shutdown remain the objective.

## Reuse and missing ownership

| Existing body | Decision | Native boundary |
| --- | --- | --- |
| `kernel/rust/sysfs.rs::sysfs_init` and `object_helpers.rs::sysfs_init_body_result` | Retain the existing guest allocation, packet and wait path. | Validate the complete request and buffer against the exact OS generation and exclude queues before any host access or reply. |
| `executer/kernel/mcctrl/rust/mcctrl_helpers.rs::mcctrl_sysfs_req_setup_body_result` | Adapt mapping, setup and release-last completion order. | Its old map callbacks and `sysfsm_setup` depend on C-owned driver objects and unchecked legacy addresses. |
| `mcctrl_sysfs_req_common_body_result`, `mcctrl_sysfs_lookup_i_body_result`, `mcctrl_sysfs_work_main_body_result` | Reuse request ordering, lookup rules and message classification. | Replace raw node-pointer handles with owned native identities; keep dispatch in sleepable context and preserve remote response ordering. |
| `setup_sysfs_files`, `setup_local_snooping_files`, CPU/cache/NUMA topology bodies in the same Rust crate | Adapt their existing file names, values and topology translation. | Existing access bridges depend on legacy `mcctrl_usrdata`, saved topology and C tree mutation. Do not replace them with fabricated topology or an empty setup-complete directory. |
| `executer/kernel/mcctrl/sysfs.c::{sysfsm_setup,mkdir_i,create_i,symlink_i,unlink_i}` | Implement missing native ownership in Rust. | These primary Linux object, allocation and cleanup bodies have no reusable native Rust counterpart. Preserve existing fallback consumers and verify behavior against their actual paths. |
| `host-kernel/native-rust/os_runtime.rs::create_os` and the OS registry | Extend the existing device ownership boundary. | Sysfs must attach to the actual generation-owned `mcos` device, with explicit references and cleanup ordering; no parallel synthetic production device. |
| Pinned Linux `rust/kernel/device.rs`, `lib/kobject.c`, `fs/sysfs/{file,symlink}.c` | Reuse Linux device references, dynamic kobjects and existing sysfs primitives. | There is no safe Rust sysfs wrapper in this source. Linux's dynamic kobject type already provides `kobj_sysfs_ops`; Rust can own a stable `kobj_attribute` and its callback data without adding C code or a new Linux release body. |

## Ownership and validation sequence

First implement the missing directory, attribute and symlink owners. Attribute
data and names must remain stable while Linux can invoke callbacks. File removal
must drain active callbacks before freeing their Rust storage. Callback data
must support concurrent access; every supplied buffer and returned byte count
must stay within the sysfs page/count contract. Parent and symlink-target
references must outlive every registered dependent. Removal must never delete
a different owner's node after a failed duplicate creation or a name reuse.

Verify the exact generated Linux object/callback layout with an independent C
witness, build the actual Rust adapter in a disposable module and exercise
real sysfs reads, writes, duplicate failures, dependent teardown, concurrent
read/removal and module reload. This is the prerequisite object boundary,
not a completed SYSFS_REQ_SETUP exchange or an application test.

Next attach the owners to the existing OS device and add the native tree,
shared-buffer owner and complete setup-file/topology adaptation. Reuse the
existing Rust request/dispatch bodies with generation, extent, queue-alias,
path and handle checks. Verify request failures and publication ordering with
actual-body tests before repeating both actual McKernel startup interfaces.
Only a completed real setup may clear busy. Preserve unsupported next requests
and started owners until continuing host dispatch and shutdown are implemented.

Retain every first validation failure in `kernel.log` and evidence, use the
established isolated four-CPU/12-GiB containers and save coherent checkpoints
to GitHub. Declared staging/contracts/full-suite integration and independent
production acceptance remain required in addition to the prototype evidence.

## Object adapter implementation

`host-kernel/native-rust/sysfs_objects.rs` now owns directory registration,
stable attribute storage and symlinks. It uses Linux's existing `kobj_sysfs_ops`
with the generated `kobj_attribute` layout. Direct `kobject_init_and_add`
preserves add failures such as EEXIST; the convenience
`kobject_create_and_add` loses those error codes. A Rust release callback
reclaims only the boxed kobject allocation after Linux's final reference.
Failed directory adds also release through that callback. Every file/link
holds explicit object references, and failed duplicate creation never owns
or removes the original name. `sysfs_remove_file_ns` drains callbacks before
the attribute name and synchronized Rust operations can drop.

The current consumer is `scripts/tests/fixtures/mckernel_sysfs_objects_verify.rs`,
which includes the exact production source. Module attempts 1/3 pass formatting,
21 independent C/Rust layout values, actual module compilation and ELF/no-SIMD
checks. Attempt 2 also builds the module but fails the userspace fixture's
static libc link; its full inputs/logs are retained. Attempt 3 uses the existing
dynamic libc/loader, with their bytes and dependency report retained for the
disposable guest. Runtime checks and actual OS-device/service integration remain
pending at this implementation checkpoint.
