Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is a source-only successor of the completed HOST19 runner. Its ten commands
cover fresh F03 counter callbacks and the F06 controlled allocation/free fixture.
No HOST19 command or output is reused. F06 metadata C exception is not adopted.

Root API: prepare one fresh CPU6 exclusion observation using the supplied schema,
then one exact grant using ROOT-GRANT.SCHEMA.NOT-A-GRANT.json. Root supplies a fresh
32-hex nonce, current observed job/memory reservations, current times and a finite
expiry. Set authorized=true only after independent source/profile review. Issuance
and CPU6 observation must be less than180seconds old at entry. This runner consumes
its fresh capture root exactly once, before the first child; interrupted prefixes
remain retained and are never resumed/replayed by this runner.

Run explicitly after that review/grant (replace placeholders with exact hashes):

    /usr/bin/python3 -B run_new12h_host.py --profile /absolute/PROFILE.NOT-GRANTED.json --profile-sha256 PROFILE_SHA --grant /absolute/ROOT-GRANT.json --grant-sha256 GRANT_SHA

No default profile/grant dispatch exists. Every command rechecks input/profile/
grant bytes, resident account, actual parent guardian, all inherited cutoffs,
90seconds remaining, CPU6 affinity, original memory floors and host/scratch floors.
Root retains responsibility for campaign-wide CPU6 exclusion and aggregate current
reservations. The grant pins that fresh Root observation; source code does not
invent physical clearance or grant another heavy operation.

The original e8b84de3 admission's20GiB memory floor and HOST19's stricter23357213694B
floor remain. The new adapter replaces expired account/thread/window checks with
reviewed v2 guard1f152; it also checks HOST16GiB plus full2GiB output reserve and
scratch12GiB. It does not import or execute the old admission main.

Capture remains exact helper990807ab: creator birth, blocked fork-to-owner signal
window, bounded retirement, direct join, group absence and closed stream hashing.
Each child retains CPU6, AS2GiB, CPU60s, FSIZE64MiB, core0, wall90s. Streams keep the
helper's32MiB cap. Failures preserve the full prefix and stop immediately.

Pure verification: /usr/bin/python3 -B test_runner_policy.py. Eight controls passed;
no actual compiler/fixture/ordinary operation was run during preparation.
