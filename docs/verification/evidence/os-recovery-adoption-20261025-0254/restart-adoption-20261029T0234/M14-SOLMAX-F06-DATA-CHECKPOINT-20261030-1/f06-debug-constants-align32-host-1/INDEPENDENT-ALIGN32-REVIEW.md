# Independent align32 HOST object review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

**PASS for exact align32 HOST object bytes and storage properties.** New Rust object `fbfa4e9ac742c48f875f9903a65078cd142ceea8f0d9c5f3550d61c9899f0071` contains one global OBJECT `debug_constants`, size96, writable allocated initialized `.ldata.debug_constants`, symbol offset0 and section alignment32. No relocation owns its bytes. Its exact 96 bytes equal the earlier Rust object and the rehashed retained HOST13 C and historical SDK14 C objects. The twelve words are `8128, 7848, 7872, 7920, 64, 4208, 4328, 4304, 4184, 456, 20, 18446744073709551615`. Historical SDK byte equality does not prove matching SDK source/config.

Retained `INDEPENDENT-ALIGN32-OBSERVATIONS.json` SHA-256 `3d09dadf302c48a34f831ce3ce0b7b5791710123f8122bf5051cc6ef7b572eb7` binds all four actual object hashes, exact 96-byte slices, symbol and section metadata, relocations and all depfile paths. The actual Rust depfile has 144 distinct references; all resolve to the fresh admitted 163 source files or retained 69 external inputs and match exact admitted bytes, with no extra entries. The reused selected C object SHA-256 `173c7e9add4afcb48e5a889064bdf4d7ff888ce43f807dee15ee84f7df380dfa` matches its already reviewed no-FUNC/no-OBJECT binding.

The compile result records exit0 and runner 2775497/birth113977630, post-terminal PGID2775496 observed empty and CPU6/4-GiB planning share released. The 8-aligned prior object and evidence are preserved. Read-only checking reused the pinned original ELF nodes and Python3.8 under CPU0/512MiB/30CPU/45+5wall/nofile128/fsize8MiB/core0; no produced code, compiler, root, Docker or native operation was run by this reviewer.

A separately admitted exact HOST link may consume these two objects, then must observe final unique symbol, final address alignment and actual consumers. This does not establish default/SDK/original389, complete ABI or consumer lifecycle, native behavior or C retirement. The generic_c direct-TID/terminate_host and execve transfer/ACK holds, all UNKNOWN, included-only and original ceilings remain unchanged.
