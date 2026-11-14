// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// SOURCE FRAGMENT ONLY. Compile exact ACTUAL-RUST-BODY.inc unchanged against
// this recorded C provider in a future admitted child; never execute native HLT.
unsafe extern "C" { fn cpu_halt(); }
include!("ACTUAL-RUST-BODY.inc");
