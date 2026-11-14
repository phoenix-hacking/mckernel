"""Materialize exact historical inputs without changing the working source."""

import subprocess
import tempfile
from pathlib import Path


REVIEWED_DESCENDANT = "24a151fef5b9fcf303fdbb8cf9762340cd4100fd"


def reviewed_checkout(source_repo, paths):
    directory = tempfile.TemporaryDirectory(prefix="rk007-reviewed-descendant-")
    repo = Path(directory.name) / "repo"
    try:
        commands = (
            ["git", "clone", "--quiet", "--shared", "--no-checkout", str(source_repo), str(repo)],
            ["git", "-C", str(repo), "update-ref", "--no-deref", "HEAD", REVIEWED_DESCENDANT],
            ["git", "-C", str(repo), "read-tree", REVIEWED_DESCENDANT],
            ["git", "-C", str(repo), "checkout-index", "--"] + sorted(set(paths)),
        )
        for command in commands:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return directory, repo
    except Exception:
        directory.cleanup()
        raise
