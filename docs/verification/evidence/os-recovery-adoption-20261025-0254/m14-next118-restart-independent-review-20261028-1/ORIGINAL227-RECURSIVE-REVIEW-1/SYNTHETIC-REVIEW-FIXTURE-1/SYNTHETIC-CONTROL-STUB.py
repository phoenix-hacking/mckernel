# SYNTHETIC TEST CONTROL ONLY; NEVER AN ACTUAL ACCOUNT OR GUARDIAN CHECK.
from pathlib import Path
import hashlib,json
OPERATION='original227'
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LIMITS=[1793253600,1035704.5689393478,1051042.6959879305]
def configure(row):
 raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
def guard():return [value-600 for value in LIMITS]
def current_cutoffs():return LIMITS
