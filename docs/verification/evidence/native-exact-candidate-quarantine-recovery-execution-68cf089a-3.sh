#!/usr/bin/env bash
# DRAFT: exactly two packet pins follow the independently reviewed final basis/helper.
set -Eeuo pipefail
REPO=/home/holden/mckernel
HELPER=$REPO/docs/verification/evidence/native-exact-candidate-quarantine-recover-68cf089a-3.py
FINAL_HELPER_SHA=__REPLACE_WITH_FINAL_RECOVERY3_HELPER_SHA256__
RELEASE_SHA=UNSET-REQUIRES-INDEPENDENT-RECOVERY3-RELEASE-SHA256
die(){ echo "FAIL-CLOSED: $*" >&2; exit 1; }
[[ "$EUID" -ne 0 ]] || die root-launch-prohibited
[[ "$FINAL_HELPER_SHA" =~ ^[0-9a-f]{64}$ ]] || die draft-helper-pin
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{64}$ ]] || die draft-release-pin
[[ -f "$HELPER" && ! -L "$HELPER" ]] || die helper-path
[[ "$(sha256sum "$HELPER" | awk '{print $1}')" == "$FINAL_HELPER_SHA" ]] || die helper-hash
cd "$REPO"
# Python validates fetched HEAD/upstream and git-show for exactly the four
# template/final inputs; unrelated preexisting dirty work is allowed.
# It creates exclusive O_EXCL/no-follow evidence, substantive fresh capacity,
# retained/evaluated process evidence, boot/time/source/root/history preflight.
# It does not invoke privilege or Docker.
python3 -B "$HELPER" --prepare-packet
# The capture wrapper opens every stdout/stderr output O_EXCL|O_NOFOLLOW and
# fsyncs them on either result. Exactly one sanitized sudo invocation occurs;
# Docker ps/inspect and the observer run within that bounded root helper.
set +e
python3 -B "$HELPER" --run-command \
    /usr/bin/sudo -A /usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent \
    /usr/bin/setsid --wait /usr/bin/timeout --signal=TERM --kill-after=10s 900s \
    /usr/bin/python3 -B "$HELPER"
rc=$?
# Do not let a failed helper skip the durable return code/evidence flush.
python3 -B "$HELPER" --finish-packet "$rc"
finish_rc=$?
set -e
[[ "$rc" -eq 0 && "$finish_rc" -eq 0 ]] || die "recovery-failed rc=$rc finish_rc=$finish_rc"
