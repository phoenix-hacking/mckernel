Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The original d02c publisher remains held and byte-identical. Its retained copy and
the parent's reported independent finding are preserved. Use only the separately
named publish_bfd_release.approval-correction1.NOT-RELEASED.py for this bounded
correction. Existing query/source/profile/owner/helper and24-test evidence remain
unchanged. No corrected source, fixture, root command or publication has run.

The defect was that matching review file hashes supplied no decision semantics.
The correction requires two parsed independent PASS records before publication.
Both must name the established independent reviewer and implementation_ownership
must be false. A FAIL, null decision, placeholder/extra fields, missing schema,
wrong source/profile/helper/publisher/request binding or wrong payload stops before
freshness checks or root document writes. Hash verification and JSON parsing use
the same stable input bytes.

The finite review formats follow the existing status=PASS, payload_sha256,
reviewer and implementation_ownership exact-payload precedent. Their precise
required fields are in SOURCE-APPROVAL.CORRECTION1.NULL.json and
EXECUTION-APPROVAL.CORRECTION1.NULL.json. These contain null decisions and are not
approvals. Source approval binds the already accepted owner/helper/profile. The
execution approval additionally binds this corrected publisher, the actual request
core, the actual source-approval file hash and the exact execution-payload file
SHA256. Actual review records must be independently issued; none is fabricated here.

The exact payload is constructed by expected_payload() from the fixed accepted
profile, actual unreleased request/facts and hash-bound source-review/outer-join
references. It binds the BFD image/limits/jobs/inner argv and profile-bound mounts;
the retained CPU0/AS2GiB owner argv with its existing19800-second container deadline;
actual facts/request/wholejoin byte references; and the exact three future root
publication documents, paths and hashes. Source-only payload construction starts
no owner or container and grants no control-profile expansion.

Publication hashes use the accepted owner's exact sort_keys/indent2/newline
serialization. The released request is fully predicted, including its future root
release reference, while its original core remains unchanged. The execution review
is outside the payload, avoiding a review/payload self-hash cycle. After approvals,
the accepted owner's real same-boot/120s/fresh24GiB consumer runs before the first
publication. Each O_EXCL/fsync publication is then checked against its approved
predicted hash. No new observation time is created; partial publications remain
retained on failure. No native/global/compile lease is modified by preparation.

test_publisher_approval_correction1.py contains nine unexecuted pure test methods:
valid digest-bound PASS with the real freshness consumer; hash-matching FAIL
source/execution records; null/placeholder records; changed exact payload despite
a matching changed digest; wrong digests/changed file bytes; mismatched source,
profile, publisher and request bindings; expired genuine observation; comparison
of predicted bytes against the accepted owner serializer; and FAIL/null release
template status. It forbids subprocess and Docker construction. Only temporary
private fixture data is written when a dispatcher later grants execution. Its
positive records are explicit test fixtures, never actual campaign approvals.

No fixture execution or CPU reservation has been made. The proposed next fixture
is one existing CPU0 pure profile: AS512MiB, CPU10s, wall30+5s, FSIZE16MiB,
FD128, core0, using accepted990 owned capture/direct join/group absence/closed
streams. The dispatcher alone may grant and execute it. A first unexpected failure
is retained and reported without a silent correction or retry; this is the one
bounded correction for the reported approval family.

ROOT-BFD-PUBLISH-ARGV.CORRECTION1.PENDING.json contains the corrected exact argv
shape. The old eight actual arguments remain pending and two more bind the actual
exact execution-payload path/hash. Every actual query, facts, source/execution
approval, payload, release and runtime reference remains null here. The current
capture-controller identity supplied by the parent and the running CPU6 union job
are not converted into a CPU6 clearance or query-context declaration by this work.
