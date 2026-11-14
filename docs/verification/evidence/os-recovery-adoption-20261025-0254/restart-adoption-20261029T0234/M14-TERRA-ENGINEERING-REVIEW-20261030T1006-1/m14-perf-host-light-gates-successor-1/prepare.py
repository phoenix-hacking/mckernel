from pathlib import Path
import hashlib
p=Path(__file__).parent;old=p.parent/'m14-perf-host-light-runner-source-1/perf_two_phase_owner.py';raw=old.read_bytes();assert hashlib.sha256(raw).hexdigest()=='2c7745023574066a5bb63590ace7f6a53d1f4dc85059274598a2bbece9455b68';s=raw.decode();s=s[:s.index('\n# Specific source-only perf compiler/fixture owner.')];(p/'perf_owner.successor.py').write_text(s+'\nimport math\n'+(p/'suffix.txt').read_text())
