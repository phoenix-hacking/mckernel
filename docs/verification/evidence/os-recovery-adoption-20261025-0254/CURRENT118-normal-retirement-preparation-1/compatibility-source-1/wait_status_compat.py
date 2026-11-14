"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Decode an existing wait4 terminal status on the recorded Python3.8 interpreter.
No wait, process creation, signals, custody changes or runtime authority.
"""
import os

def waitstatus_to_exitcode(status):
 """Preserve subprocess exit-code convention; refuse nonterminal wait states."""
 if os.WIFEXITED(status):
  return os.WEXITSTATUS(status)
 if os.WIFSIGNALED(status):
  return -os.WTERMSIG(status)
 raise ValueError('wait status is neither exited nor signaled')
