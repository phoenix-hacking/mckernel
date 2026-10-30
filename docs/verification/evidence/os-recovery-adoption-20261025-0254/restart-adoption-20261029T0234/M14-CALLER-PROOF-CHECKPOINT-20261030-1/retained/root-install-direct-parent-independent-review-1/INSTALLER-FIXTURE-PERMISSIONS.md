# Installer role fixture permission-view correction

Functional McKernel OS/apps and Rust/assembly migration only; no security
testing. Source analysis only; no tests, privilege or operation performed.

The role-budget-2 StatProxy changes all directory modes by adding other
execute. The fixture root is created mode 0700, so the proxy presents it as
0701 and actual install_source_closure.dir_identity(private=True) correctly
refuses it. This is a fixture-view failure, not a production permission fix.

Capture the staged operation root's actual st_dev and st_ino before installing
the fstat proxy. When the stat row refers to that exact directory, expose its
real st_mode unchanged; do not force 0700. Keep the existing fixture-only
traversability adjustment for other directory inodes, preserving the synthetic
UID view and file modes. Keep the production private-root and ancestor guards
unchanged. Do not chmod actual ancestors or change an execution limit.

Targeted synthetic regression: the exact root's real 0700 stays 0700 and the
actual private identity check accepts it; 0701 stays 0701 and that same check
refuses it; a different device or inode receives the ordinary fixture view;
other directory traverse handling is preserved; regular-file modes remain
unchanged. Review the exact successor, then execute only the previously failed
installer scenario in a fresh result. The retained parent and keeper passes
remain evidence for their original source/view and are not rerun without a
relevant change. All results remain partial, with no native or operation
release.
