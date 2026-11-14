#!/usr/bin/env python3
"""Resolve IHK's own revision in vendored and historical submodule checkouts."""
import argparse
import os
from pathlib import Path
import subprocess

if __package__:
    from . import native_rust_exact_build_offline as provenance
else:
    import native_rust_exact_build_offline as provenance


class SourceLayoutError(RuntimeError):
    pass


def git_output(repo, *args):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                       GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(repo), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=environment)
    if result.returncode:
        raise SourceLayoutError(result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expect', required=True, help='exact expected IHK commit')
    args = parser.parse_args()
    try:
        layout, revision = provenance.ihk_source_identity(args.repo, git_output)
        if revision != args.expect:
            raise SourceLayoutError('IHK source revision differs from expected commit')
    except (OSError, UnicodeError, SourceLayoutError, provenance.BuildError) as error:
        parser.exit(1, 'IHK source identity refused: ' + str(error) + '\n')
    print(revision + ' (' + layout + ')')


if __name__ == '__main__':
    main()
