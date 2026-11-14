# Descriptor planning for direct install

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
These are conservative planning allowances based on the selected source and
partial mock measurements, not measured production peaks. The operation profile
keeps the hard and soft 256-FD limits. The driver refuses more than 16 initially
open FDs before it creates its reservation/captures. Root must separately review
the ancestry, conditional writer paths and actual inherited descriptors.

| Role | Measured live peak, baseline 16 | Added planning allowance | Planned total including observer |
| --- | ---: | ---: | ---: |
| Parent | 132 | 100 | 233 |
| Keeper | 120 | 100 | 221 |
| Installer | 96 | 100 | 197 |

The extra 100 slots are deliberately not treated as observed: parent source has
two context passes with seven opened receipt/release leaves per pass (14), a
post-proof journal/two capture/result group (4), two 3-FD custody transfers,
lease, two pidfds and control socket (at most 10), four bootstrap/helper leaves,
resident-caller and reservation/capture/transient allowance and additional residual room. Keeper
and installer allowances cover unmeasured phase-zero/issuer receipts, inherited
channel and capture descriptors, output directory/journal, the 23 retained
installed readbacks, one active writer and transient opens. This is a reviewable
allocation, not proof every failure or import branch fits: actual SCM_RIGHTS,
parent/keeper lifetimes, output/freeze, exceptions and runtime imports were not
executed in those tests. A real EMFILE, ambiguous close or unproved join remains
UNKNOWN with the reservation charged; there is no retry or profile widening.
