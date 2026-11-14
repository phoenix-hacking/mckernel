"""Scoped user linger and short inhibitor readiness checks; no model operations."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


INHIBIT_WHAT = "idle:sleep:handle-lid-switch"


def _binary(name):
    path = shutil.which(name)
    if not path or not Path(path).is_absolute():
        raise RuntimeError(name + " requires an available absolute executable; no fallback")
    return path


def _run(command, operation):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, shell=False, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError(operation + " could not complete within the supported local permission path") from None
    if result.returncode != 0:
        # Raw command output may contain host/account details; do not propagate it.
        raise RuntimeError(operation + " failed; check the local user manager and permissions")
    return result.stdout


def check_linger():
    """Read only; unknown output never becomes permission to enable anything."""
    uid = os.getuid()
    if type(uid) is not int or uid < 0:
        raise RuntimeError("Current numeric user identity is unavailable")
    output = _run([_binary("loginctl"), "--no-ask-password", "show-user", str(uid),
                   "--property=Linger", "--value"], "Reading current-user linger")
    value = output.strip()
    if value not in {"yes", "no"}:
        raise RuntimeError("Current-user linger is unknown; expected an explicit yes or no")
    return {"enabled": value == "yes", "uid": uid}


def ensure_linger():
    """Explicit start/install only: enable this user's manager survival and prove it."""
    before = check_linger()
    if before["enabled"]:
        return dict(before, changed=False)
    _run([_binary("loginctl"), "--no-ask-password", "enable-linger", str(before["uid"])],
         "Enabling current-user linger")
    after = check_linger()
    if after["uid"] != before["uid"] or not after["enabled"]:
        raise RuntimeError("Current-user linger enablement was not verified")
    return dict(after, changed=True)


def probe_inhibition():
    """Acquire then release a short lock, proving permission without permanent policy."""
    if not sys.executable or not Path(sys.executable).is_absolute():
        raise RuntimeError("The inhibition probe requires the current absolute Python executable")
    # Older supported systemd-inhibit versions have no --no-ask-password
    # option. The bounded subprocess already has stdin disconnected.
    _run([_binary("systemd-inhibit"), "--what=" + INHIBIT_WHAT, "--mode=block",
          "--who=McKernel readiness",
          "--why=Verify overnight idle sleep and lid inhibition", "--",
          sys.executable, "-B", "-c", "pass"], "Noninteractive overnight inhibition probe")
    return {"verified": True, "what": INHIBIT_WHAT, "mode": "block", "persistent": False}
