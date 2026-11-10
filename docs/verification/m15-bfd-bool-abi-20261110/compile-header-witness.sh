#!/usr/bin/bash
set -euo pipefail
umask 077
if test -n "$(/usr/bin/find /capture -mindepth 1 -maxdepth 1 -print -quit)"; then
  /usr/bin/printf '%s\n' 'fresh private capture required' >&2
  exit 64
fi
/usr/bin/mkdir /capture/tmp
export TMPDIR=/capture/tmp
/usr/bin/sha256sum --check --strict /input/native-inputs.sha256 > /capture/input-identity.stdout 2> /capture/input-identity.stderr
/usr/bin/cc -std=c11 -Wall -Wextra -Werror -fsyntax-only /input/header-bool-witness.c > /capture/header-witness.stdout 2> /capture/header-witness.stderr
/usr/bin/printf '%s\n' 'C_HEADER_BOOL_SIGNATURES_PASS_COMPILE_ONLY'
