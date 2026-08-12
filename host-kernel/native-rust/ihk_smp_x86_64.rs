// SPDX-License-Identifier: (BSD-2-Clause OR GPL-2.0)
//! Native Rust-for-Linux x86_64 IHK SMP module lifecycle.
//!
//! Linux 6.12 does not yet expose module parameters through its Rust
//! `module!` macro.  The six frozen legacy parameters therefore use the same
//! `__param` ABI as `module_param()`, backed by the kernel's exported numeric
//! parameter operations.  Linux's `MODULE_PARAM_PREFIX` is empty for a
//! loadable module and `KBUILD_MODNAME.` for a built-in, so both descriptor
//! names are emitted explicitly.  No project-owned C object participates in
//! this crate.

use kernel::prelude::*;

const IHK_SMP_PARAMETER_COUNT: usize = 6;
const IHK_SMP_DEPENDENCY: &str = "ihk";
const IHK_SMP_IMPORT_NAMESPACE: &str = "MCKERNEL_IHK_V1";

// SAFETY: The provider owns this immutable namespaced byte for its full module
// lifetime. Access is restricted to the dependency-establishing init read.
extern "Rust" {
    #[link_name = "ihk_provider_lifecycle_v1"]
    static IHK_PROVIDER_LIFECYCLE_V1: u8;
}

// This is the x86_64 layout of Linux 6.12's `struct kernel_param`.  Keeping a
// local representation avoids depending on bindgen's unstable anonymous-union
// field name while the size/alignment checks below bind it to the generated
// Rocky kernel type.
#[repr(C)]
union KernelParameterValue {
    arg: *mut core::ffi::c_void,
}

#[repr(C)]
struct KernelParameter {
    name: *const core::ffi::c_char,
    module: *mut kernel::bindings::module,
    ops: *const kernel::bindings::kernel_param_ops,
    permission: u16,
    level: i8,
    flags: u8,
    value: KernelParameterValue,
}

// SAFETY: Each instance is immutable after relocation.  Linux owns access to
// the pointed-to parameter storage and serializes writes with its parameter
// subsystem; Rust code never dereferences these pointers.
unsafe impl Sync for KernelParameter {}

const _: [(); core::mem::size_of::<kernel::bindings::kernel_param>()] =
    [(); core::mem::size_of::<KernelParameter>()];
const _: [(); core::mem::align_of::<kernel::bindings::kernel_param>()] =
    [(); core::mem::align_of::<KernelParameter>()];

macro_rules! numeric_parameter {
    (
        name: $name:ident,
        storage: $storage:ident,
        descriptor: $descriptor:ident,
        rust_type: $rust_type:ty,
        ops: $ops:ident,
        default: $default:literal,
        permission: $permission:literal,
        loadable_name_bytes: $loadable_name_bytes:literal,
        builtin_name_bytes: $builtin_name_bytes:literal,
    ) => {
        #[doc(hidden)]
        // SAFETY: Linux's parameter subsystem is the only writer after module
        // publication and serializes access; Rust never reads this storage.
        static mut $storage: $rust_type = $default;

        #[doc(hidden)]
        #[link_section = "__param"]
        #[used(compiler)]
        static $descriptor: KernelParameter = KernelParameter {
            name: {
                #[cfg(MODULE)]
                const PARAMETER_NAME: &[u8] = $loadable_name_bytes;
                #[cfg(not(MODULE))]
                const PARAMETER_NAME: &[u8] = $builtin_name_bytes;
                PARAMETER_NAME.as_ptr() as *const core::ffi::c_char
            },
            module: THIS_MODULE.as_ptr(),
            // `param_ops_uint` and `param_ops_ulong` are immutable, exported
            // Linux kernel objects with static lifetime.
            ops: core::ptr::addr_of!(kernel::bindings::$ops),
            permission: $permission,
            level: -1,
            flags: 0,
            value: KernelParameterValue {
                arg: core::ptr::addr_of_mut!($storage) as *mut core::ffi::c_void,
            },
        };

        // Make the contract name part of the expansion even though the ABI
        // consumes its explicitly NUL-terminated byte form above.
        const _: &str = stringify!($name);
    };
}

numeric_parameter!(
    name: ihk_phys_start,
    storage: IHK_PHYS_START,
    descriptor: PARAM_IHK_PHYS_START,
    rust_type: core::ffi::c_ulong,
    ops: param_ops_ulong,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_phys_start\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_phys_start\0",
);

numeric_parameter!(
    name: ihk_mem,
    storage: IHK_MEM,
    descriptor: PARAM_IHK_MEM,
    rust_type: core::ffi::c_ulong,
    ops: param_ops_ulong,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_mem\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_mem\0",
);

numeric_parameter!(
    name: ihk_cores,
    storage: IHK_CORES,
    descriptor: PARAM_IHK_CORES,
    rust_type: core::ffi::c_uint,
    ops: param_ops_uint,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_cores\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_cores\0",
);

numeric_parameter!(
    name: ihk_start_irq,
    storage: IHK_START_IRQ,
    descriptor: PARAM_IHK_START_IRQ,
    rust_type: core::ffi::c_uint,
    ops: param_ops_uint,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_start_irq\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_start_irq\0",
);

numeric_parameter!(
    name: ihk_ikc_irq_core,
    storage: IHK_IKC_IRQ_CORE,
    descriptor: PARAM_IHK_IKC_IRQ_CORE,
    rust_type: core::ffi::c_uint,
    ops: param_ops_uint,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_ikc_irq_core\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_ikc_irq_core\0",
);

numeric_parameter!(
    name: ihk_trampoline,
    storage: IHK_TRAMPOLINE,
    descriptor: PARAM_IHK_TRAMPOLINE,
    rust_type: core::ffi::c_ulong,
    ops: param_ops_ulong,
    default: 0,
    permission: 0o644,
    loadable_name_bytes: b"ihk_trampoline\0",
    builtin_name_bytes: b"ihk_smp_x86_64.ihk_trampoline\0",
);

// Linux 6.12's Rust `module!` macro cannot emit namespace-import or parameter
// metadata.  These paired records match `MODULE_IMPORT_NS()`,
// `MODULE_PARM_DESC()`, and `module_param()` for loadable and built-in
// configurations.  `modpost` derives the single `depends=ihk` record from the
// provider-anchor relocation above; emitting it here would create a duplicate.
macro_rules! modinfo_pair {
    ($loadable_name:ident, $builtin_name:ident, $loadable:literal, $builtin:literal) => {
        #[cfg(MODULE)]
        #[doc(hidden)]
        #[link_section = ".modinfo"]
        #[used(compiler)]
        static $loadable_name: [u8; $loadable.len()] = *$loadable;

        #[cfg(not(MODULE))]
        #[doc(hidden)]
        #[link_section = ".modinfo"]
        #[used(compiler)]
        static $builtin_name: [u8; $builtin.len()] = *$builtin;
    };
}

modinfo_pair!(
    SMP_IMPORT_NS_MODINFO,
    SMP_BUILTIN_IMPORT_NS_MODINFO,
    b"import_ns=MCKERNEL_IHK_V1\0",
    b"ihk_smp_x86_64.import_ns=MCKERNEL_IHK_V1\0"
);

modinfo_pair!(
    IHK_PHYS_START_PARM_MODINFO,
    IHK_PHYS_START_BUILTIN_PARM_MODINFO,
    b"parm=ihk_phys_start:IHK reserved physical memory start address\0",
    b"ihk_smp_x86_64.parm=ihk_phys_start:IHK reserved physical memory start address\0"
);
modinfo_pair!(
    IHK_PHYS_START_TYPE_MODINFO,
    IHK_PHYS_START_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_phys_start:ulong\0",
    b"ihk_smp_x86_64.parmtype=ihk_phys_start:ulong\0"
);
modinfo_pair!(
    IHK_MEM_PARM_MODINFO,
    IHK_MEM_BUILTIN_PARM_MODINFO,
    b"parm=ihk_mem:IHK reserved memory in MBs\0",
    b"ihk_smp_x86_64.parm=ihk_mem:IHK reserved memory in MBs\0"
);
modinfo_pair!(
    IHK_MEM_TYPE_MODINFO,
    IHK_MEM_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_mem:ulong\0",
    b"ihk_smp_x86_64.parmtype=ihk_mem:ulong\0"
);
modinfo_pair!(
    IHK_CORES_PARM_MODINFO,
    IHK_CORES_BUILTIN_PARM_MODINFO,
    b"parm=ihk_cores:IHK reserved CPU cores\0",
    b"ihk_smp_x86_64.parm=ihk_cores:IHK reserved CPU cores\0"
);
modinfo_pair!(
    IHK_CORES_TYPE_MODINFO,
    IHK_CORES_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_cores:uint\0",
    b"ihk_smp_x86_64.parmtype=ihk_cores:uint\0"
);
modinfo_pair!(
    IHK_START_IRQ_PARM_MODINFO,
    IHK_START_IRQ_BUILTIN_PARM_MODINFO,
    b"parm=ihk_start_irq:IHK IKC IPI to be scanned from this IRQ vector\0",
    b"ihk_smp_x86_64.parm=ihk_start_irq:IHK IKC IPI to be scanned from this IRQ vector\0"
);
modinfo_pair!(
    IHK_START_IRQ_TYPE_MODINFO,
    IHK_START_IRQ_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_start_irq:uint\0",
    b"ihk_smp_x86_64.parmtype=ihk_start_irq:uint\0"
);
modinfo_pair!(
    IHK_IKC_IRQ_CORE_PARM_MODINFO,
    IHK_IKC_IRQ_CORE_BUILTIN_PARM_MODINFO,
    b"parm=ihk_ikc_irq_core:Target CPU of IHK IKC IRQ\0",
    b"ihk_smp_x86_64.parm=ihk_ikc_irq_core:Target CPU of IHK IKC IRQ\0"
);
modinfo_pair!(
    IHK_IKC_IRQ_CORE_TYPE_MODINFO,
    IHK_IKC_IRQ_CORE_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_ikc_irq_core:uint\0",
    b"ihk_smp_x86_64.parmtype=ihk_ikc_irq_core:uint\0"
);
modinfo_pair!(
    IHK_TRAMPOLINE_PARM_MODINFO,
    IHK_TRAMPOLINE_BUILTIN_PARM_MODINFO,
    b"parm=ihk_trampoline:IHK trampoline page physical address\0",
    b"ihk_smp_x86_64.parm=ihk_trampoline:IHK trampoline page physical address\0"
);
modinfo_pair!(
    IHK_TRAMPOLINE_TYPE_MODINFO,
    IHK_TRAMPOLINE_BUILTIN_TYPE_MODINFO,
    b"parmtype=ihk_trampoline:ulong\0",
    b"ihk_smp_x86_64.parmtype=ihk_trampoline:ulong\0"
);

module! {
    type: IhkSmpModule,
    name: "ihk_smp_x86_64",
    license: "Dual BSD/GPL",
}

struct IhkSmpModule;

impl kernel::Module for IhkSmpModule {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        // SAFETY: The provider exports this immutable byte in the declared
        // namespace.  The volatile read keeps the relocation as an actual
        // module dependency; the value itself has no behavioral meaning.
        let _ = unsafe {
            core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1))
        };
        pr_info!(
            "lifecycle=load parameters={} dependency={} import_namespace={}\n",
            IHK_SMP_PARAMETER_COUNT,
            IHK_SMP_DEPENDENCY,
            IHK_SMP_IMPORT_NAMESPACE,
        );
        Ok(Self)
    }
}

impl Drop for IhkSmpModule {
    fn drop(&mut self) {
        pr_info!(
            "lifecycle=unload parameters={} dependency={} import_namespace={}\n",
            IHK_SMP_PARAMETER_COUNT,
            IHK_SMP_DEPENDENCY,
            IHK_SMP_IMPORT_NAMESPACE,
        );
    }
}
