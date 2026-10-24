Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SOURCE ONLY, batch1; no compiler, fixture, subprocess-under-test or native commands run.
No production/file/native/percentage credit. Existing shell selectors remain canonical.

Sources: platform.rs, reboot.rs, stop.rs, mcreboot_main.rs, mcstop_main.rs,
config.rs.in, fixture.rs. All Rust runtime control bodies are in these files.
No project C ABI is called: ihkconfig/ihkosctl/ihkmond executables use precisely
existing public argv groups (0 reserve/release/query cpu|mem, 0 get buildid,
0 destroy N/create; 0 assign cpu|mem, set ikc_map, load, kargs, boot).
Root must select already-frozen Rust CLI candidates and the actual matching
Rust libihk export/default selector. Current fallback remains explicit M15 debt.
Required upstream dependencies are libc umask/geteuid, Rust std and Linux utilities:
sudo (nonroot), taskset, insmod/rmmod, systemctl, tee, rm/rmdir/mkdir, cat, id,
logname, pidof, kill, lsof, getenforce, hostname, sync, lscpu, chown.
insmod remains taskset -c 0 [sudo] insmod, preserving the sudoers utility boundary.
No compile-time external crates, shell eval, Tcl engine, or hidden script bodies.

Owner's exact next fixture profile (root execution only, no commands run here):
Create an empty owned fixture directory; copy all .rs there, excluding config.rs.in.
Render config.rs.in to config.rs with @prefix@=/owned, @ETCDIR@=/owned/etc,
@KMODDIR@=/owned/modules, @MCKERNELDIR@=/owned/kernel, @ARCH@=x86_64,
@BUILDID@=fixture-build, @ENABLE_LINUX_WORK_IRQ_FOR_IKC@=OFF.
Compile: rustc --edition=2021 --test --crate-name m15_boot_fixture fixture.rs -o fixture
Run only that owned fake binary. Its Host implementation records all command calls,
filesystem writes, sleeps and signals as data; it cannot reach Native.
Then link-only both binaries, no execution:
rustc --edition=2021 --crate-name mcreboot -C panic=abort mcreboot_main.rs -o mcreboot.sh
rustc --edition=2021 --crate-name mcstop -C panic=abort mcstop_main.rs -o mcstop+release.sh
Root owns independent build slots, original-reference comparison, integration and
later native execution release. The CMake fragment retains installed names and an
explicit OFF debt path. Never execute either real backend against this host now.

Supported behavior: all reference getopts flags, default node0 half CPUs /512M@0,
monitor options, SELinux refusal, IRQ selection/masks/save/restore, OFP RAM handling,
module load/order, build-id match, retry destroy, CPU/memory/IKC assignments, boot
arguments, device ownership, stop -k/-r/-R, release-all normal stop, irqbalance and
swappiness restoration. Boot ignores trailing operands exactly as reference.
Stop retains reference typo `Proesses still using` for diagnostic compatibility.

Intentional correctness differences, not reference-equivalence claims:
1. Error rollback destroys newly created OS0 and releases only requested reservations
   acquired in this attempt, and unloads only modules loaded by it. The original
   fallthrough rollback queried and released every reserved CPU/memory and removed
   pre-existing modules. Normal explicit reboot/stop still affects all OS instances
   by their existing public contract; this source does NOT authorize running it.
2. A successful fifth destroy attempt is accepted. Original nretry==4 erroneously
   reports failure even when the fifth command succeeds.
3. -R reserves once on a newly loaded SMP module, rather than the reference's two
   reservations of identical memory/CPUs; existing SMP still receives forced reserve.
4. irqbalance selected CPU mask is recomputed when backups already exist. Reference
   reused an unset shell variable on subsequent reboots.
5. IRQ mask parse and write failures fail through owned rollback. Reference Perl
   ignored write statuses. Numeric IRQ search really excludes existing interrupt
   numbers; the reference single-quoted grep '^$i$' never expanded its variable.
6. The reference error label mcos_sys_mounted has no case and skips cleanup. A
   failed irqbalance restart uses the actual acquired-state rollback.
7. Root invokes privileged utilities directly (equivalent privilege); nonroot uses
   sudo exactly on required utility actions. Native retains child error text for
   project CLI/chown errors; top-level missing/invalid option wording is Rust-native.

Scope exclusions: no host mutation, compiler, test execution, module ioctls,
actual boot/stop/release/signal, canonical edits or evidence claims in this batch.
Preserve scratch21, evidence and permanent27:4, ownership and resource releases.
The normal script broad resource release is not campaign cleanup authorization.
