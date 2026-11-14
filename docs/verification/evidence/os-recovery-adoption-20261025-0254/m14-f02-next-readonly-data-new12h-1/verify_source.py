"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source provenance and reconstruction checks; no compiler or fixture execution.
"""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'SOURCE-ONLY.json').read_text());s=m['symbol']
c=(P/'preimages/process.c').read_text();nc=(P/'candidate/process.c').read_text()
table=re.search(r'const struct sched_runqueue_offsets '+s+r' = \{.*?\n\};',c,re.S).group()
replacement='#ifdef MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE\nextern const struct sched_runqueue_offsets '+s+';\n#else\n#line '+str(m['logical_line_start'])+'\n'+table+'\n#endif\n#line '+str(m['logical_line_after'])+'\n'
assert nc.replace(replacement,table+'\n',1)==c
old=(P/'preimages/sched_helpers.rs').read_text();new=(P/'candidate/sched_helpers.rs').read_text();fragment=(P/'runqueue_storage.FRAGMENT.rs').read_text()
assert new.replace(fragment,'',1).replace('const fn sched_runqueue_offsets()','fn sched_runqueue_offsets()',1)==old
assert len(m['fields'])==26 and len(bytes.fromhex(m['bytes_hex']))==208
# All original C initializer expressions appear unchanged in the frozen oracle.
assert table.replace(s,'original_C_runqueue_offsets') in (P/'fixture/oracle.c').read_text()
assert 'unsafe' not in fragment and 'link_section' not in fragment and 'used' not in fragment
# No whole-file rewrite or GNU_RETAIN/debug/callback modification.
for p in ['candidate/process.c','candidate/sched_helpers.rs']:
 assert (P/p).exists()
print('PASS exact private C/Rust reconstruction;26 frozen actual artifact words;original C oracle retained;no compiler/workload run')
