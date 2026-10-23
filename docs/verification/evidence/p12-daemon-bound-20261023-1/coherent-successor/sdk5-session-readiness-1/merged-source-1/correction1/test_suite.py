"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import runpy
H=Path(__file__).resolve().parent
for name in ['test_merged_hooks.py','test_long_integration.py']:
 try:runpy.run_path(str(H/name),run_name='__main__')
 except SystemExit as exc:
  if exc.code:raise
