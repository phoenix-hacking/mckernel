# Owned low-memory trampoline prerequisite

Retain the McKernel startup/real-mode assembly, `smp_startup.rs::PageTablePlan`,
the loaded image and its existing Linux page owners. Retain the exact OS token,
IHK operation mutex, CPU reservation table and native IRQ producer/transport.
This prerequisite supplies only a Linux memory-region owner; it does not start
a CPU or replace those owners.

The pinned Linux `arch/x86/realmode/init.c::reserve_real_mode` reserves the
entire first MiB after allocating Linux's trampoline. Normal `GFP_DMA` page
allocation therefore cannot provide a separate sub-MiB page. The fallback's
overwriting of Linux's own trampoline is not the ownership model for this work.
Linux's E820 resource setup also marks every sub-MiB E820 range busy, including
ordinary `memmap=4K$...` reservations; a reserved descriptor is not a free lease.

Investigate a page removed explicitly from the Linux E820 RAM map using the
existing `memmap=4K%0x80000-1` parser in the disposable guest. The original
firmware map must describe every byte as RAM, the current E820 map must contain
no overlapping entry of any type, and Linux's resource manager must grant an
exclusive region before any mapping or write. This excludes Linux's real-mode
allocation because the carve-out precedes `reserve_real_mode`. Use only the
bounded 64-KiB-to-640-KiB conventional-memory window, excluding BIOS low data,
ROM and MMIO ranges. This is an isolated QEMU prerequisite, not hardware
acceptance or permission to select an arbitrary physical hole.

The exact Linux Rust crate has no safe resource-request or E820 wrapper.
Adapt its existing exported `e820__mapped_raw_any`, `e820__mapped_any`,
`__request_region`, `__release_region`, `ioremap_cache` and `iounmap` APIs in
the Rust verification fixture. No Linux source change, private symbol lookup
or project C helper is needed. A data-only C witness checks their exact
signatures and scalar ABI; its object is never linked into the Rust module.

The new fixture owns an exclusive resource lease and mapping with ordered
RAII cleanup. Check the original firmware coverage byte by byte because the
exported predicate proves overlap rather than full-range containment. Verify
normal-map rejection without writes, ordinary-reserved-map rejection, successful
exclusive acquisition in the explicit carve-out, overlapping-lease rejection,
all-page pattern readbacks, release/reacquisition, and two module lifetimes.
Keep the final mapping alive through module init and release it before the
unload marker. No CPU may execute or reference this page during these tests.

After this passes, reuse the tested owner body in the native SMP boot adapter
and bind its resource/OS/IRQ lifetimes in the declared stage. Integrate exact
boot parameters and the preserved assembly into that owner, publish Booting
before any INIT/SIPI, and retain all owners after uncertain startup until a
proven CPU stop. Real McKernel readiness, IKC, workloads, Rust/assembly-only
completion and independent acceptance remain required.
