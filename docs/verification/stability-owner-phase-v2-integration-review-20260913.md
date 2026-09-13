# Owner-phase-v2 integration source review

The reviewed controller waits for the original launcher to become waitable and
both actual output pipes to reach EOF before requesting the first terminal
owner snapshot. It retains the original PID with `WNOWAIT`, checks its original
start ticks, and uses the existing minimum of the input-plus-15-second and
overall-90-second deadlines. The final deadline check follows the final
`waitid` observation and event recording. The boundary does not require exit
zero or interpret launcher exit as payload success.

The exact reviewed inputs are:

| Input | SHA-256 |
| --- | --- |
| `scripts/tests/fixtures/stability-transport-fault/owner-phase-v2/controller.c` | `7b1115f4c744d32bb085f23b515e35bcfab4cf0efa6f2e3cb5827742876511e2` |
| `scripts/tests/prepare_stability_fault_guest.py` | `6b7135c77f1c9bc5f82c5de3626aad1f86b72e5b72b9d803e99f32bc615ad67f` |
| `scripts/tests/run_stability_transport_guest.py` | `3215065d832d18638bd3901c530d5a6bdd89569b6643ea6cd6c0162a804a0d7d` |

The controller addition is at lines 865–896 and its terminal-only invocation is
at line 979. The preparer selects the separately bound v2 build at lines
129–138 and copies its recorded output while checking loader dependencies.
The runner requires the selected application to be closed and quarantined in
both terminal snapshots at lines 422–428. The existing typed phase validation,
full Terminal/TerminalPlusFive inventory equality, physical response oracle,
counter contract, emergency handling and later cleanup remain in force.

The independent controller and wiring reviews found no remaining definite
source defect in these deltas. Their complete original directories, including
all reviewed source files, patches, reconstructed prior source and the copied
controller build record, are retained in the accompanying archive. This
publication independently rechecks those retained byte identities and the
exact original-to-final source differences. The wiring review's older files
are retained as its checkpoint inputs for commit
`befee507c2a042b58dd558d414df5ba0bd2e4ad7`; this publication does not independently
establish their membership in that Git commit.

The controller review initially rejected a source identity mismatch when the
root lane changed the diagnostic split during capture. That failed capture
created no output directory and overwrote no retained source. The retained
`controller.reviewed1059.reconstructed.c` is explicitly reconstructed by
reversing only that final diagnostic split. Its hash matches the earlier read,
but it is not an original copied file. The final split preserves a failed
`task_ticks` call's actual errno and returns `ESTALE` only after a successful
read with different ticks. The exact v1 controller and header remain retained
and byte-equal to the v2 original and header respectively.

The pinned Linux exit and native owner source trace supports waiting for this
boundary before snapshotting. Source ordering alone does not prove native
owner safety or the actual terminal state. The fifth guest's original changing
`APP.closed` inventory remains a failure; this review does not revise it.

Root separately reported and archived the pinned eight-case actual Linux
boundary harness PASS in
[the terminal integration checkpoint](stability-terminal-integration-20260913-1.md).
Its [retention map](stability-terminal-integration-20260913-1.json) binds the full
build, harness and original guest-failure captures. This source-review lane ran
no compiler, test helper or guest, and did not revalidate the compiled binary.
The harness result is infrastructure evidence. Transport, catalog application
and production acceptance remain false in this publication.

The accompanying
[source-review record](stability-owner-phase-v2-integration-review-20260913.json)
contains all identities, source-difference checks and complete archive member
mapping. The existing v2 README remains an unchanged historical source-candidate
document; later build or test results are linked separately.
