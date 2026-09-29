#!/usr/bin/env bash
# DRAFT only.  This wrapper has no execution authority and must fail before
# invoking Python, sudo, Docker, or touching any packet output.
set -Eeuo pipefail
RELEASE_SHA_REQUIRED=RELEASE_SHA_REQUIRED
OBSERVER_SHA_REQUIRED=OBSERVER_SHA_REQUIRED
PACKET_SHA_REQUIRED=PACKET_SHA_REQUIRED
TEST_SHA_REQUIRED=TEST_SHA_REQUIRED
die() { echo "DRAFT_NOT_RELEASED: $*" >&2; exit 1; }
[[ "$RELEASE_SHA_REQUIRED" =~ ^[0-9a-f]{64}$ ]] || die release-sentinel
[[ "$OBSERVER_SHA_REQUIRED" =~ ^[0-9a-f]{64}$ ]] || die observer-sentinel
[[ "$PACKET_SHA_REQUIRED" =~ ^[0-9a-f]{64}$ ]] || die packet-sentinel
[[ "$TEST_SHA_REQUIRED" =~ ^[0-9a-f]{64}$ ]] || die test-sentinel
die independent-execution-release-required
