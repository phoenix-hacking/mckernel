Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SOURCE ONLY batch3 original-reference fixture. Python AST parse only performed;
no shell/fixture/candidate/compiler/subprocess-under-test executed by this worker.

This complements batch1's owned fake unit fixture with two real-reference-shell
comparisons: boot existing modules/resources with explicit -c2-3/-otester and
stop -R retain modules. The original reference is copied to a new owned fixture,
configured identically, and instrumented only to redirect /proc,/sys,/dev,/run
paths to that owned tree. Frozen canonical references are read, never written.
Fake Linux/project commands have no ioctl/module/signal effects. Signals and
unexpected cleanup are rejected; fake tee/cat/mkdir check owned path ancestry.
No privileged/root action occurs, no real sudo is called. Reference Linux text
utilities read only owned files, and native Rust Host is never instantiated.

Exact next root-owned profile after batch1 owned fake fixture passes:
Stage batch1 fixture.rs/platform.rs/reboot.rs/stop.rs/rendered config.rs alongside
this reference_driver.rs. Compile only owned fake driver:
rustc --edition=2021 --crate-name m15_boot_reference reference_driver.rs -o reference-driver
Then root may execute:
python3 compare_reference.py --reference-root /home/holden/mckernel --rust-fake ABS_OWNED/reference-driver --output ABS_NEW_OWNED_RESULT_DIR
Output directory must be new; original stdout/stderr/logs and complete selected
public command argv pairs are retained. Comparator asserts exact public
project CLI/module command order/argv, not a weakened success-only result.
All Linux discovery calls/ownership helpers remain available in full raw logs.
Reference-retained implementation defects intentionally corrected in batch1
are covered by separate Rust tests and README distinctions, not falsely
called equivalent by these two happy-path comparisons.

Not production acceptance; source selection/default/link/native remain root
integration obligations. Preserve scratch21/evidence/permanent27:4 and all
existing ownership/resource release controls. No host cleanup authority.
