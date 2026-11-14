from pathlib import Path
import hashlib
p=Path(__file__).parent;old=p.parent/'m14-inner-subreeper-source-1/inner_retirement.py';raw=old.read_bytes();assert hashlib.sha256(raw).hexdigest()=='537bd6cfa8e181a7a9e6cd31af84146c06347187047255aa50b41c57bfd95602';s=raw.decode()
def one(a,b):
 global s
 if s.count(a)!=1:raise ValueError(a[:100])
 s=s.replace(a,b,1)
one('import json\n','import json\nimport math\n')
one("'observer_sha256','host_authority_sha256','boot_id','self_identity','views'", "'observer_sha256','host_authority_sha256','caps_authority_sha256','deadline_caps','boot_id','self_identity','views'")
one("and _is_sha(binding['host_authority_sha256']), 'inner operation/hash binding'", "and _is_sha(binding['host_authority_sha256']) and _is_sha(binding['caps_authority_sha256']), 'inner operation/hash binding'")
marker='def _inner_require_binding(binding, fds):\n';idx=s.index(marker)
helper='''# Live values and their external authenticated issuer remain absent in this source.
# The fixed UTC is an upper bound, not a release or a fresh operational clock.
MAX_UTC=1793774133.0

def _positive_finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0

def _check_deadlines(binding, requested=None):
    caps=binding.get('deadline_caps')
    require(isinstance(caps,dict) and set(caps)=={'utc','boot','monotonic'} and all(_positive_finite(x) for x in caps.values()), 'deadline caps unbound or nonfinite')
    require(caps['utc']<=MAX_UTC, 'UTC cutoff widened')
    if requested is not None:
        require(_positive_finite(requested) and requested<=caps['monotonic'], 'requested deadline outside monotonic cap')
    utc=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
    require(all(_positive_finite(x) for x in (utc,boot,mono)) and utc<caps['utc'] and boot<caps['boot'] and mono<caps['monotonic'], 'deadline elapsed or clock unknown')
    if requested is not None:require(mono<requested,'requested deadline elapsed')

'''
s=s[:idx]+helper+s[idx:]
start=s.index('def _host_exchange(phase, payload):');end=s.index('\nclass InnerConfigureOwner:',start)
s=s[:start]+'''def _canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def _host_exchange(phase, payload):
    require(HOST_EXCHANGE is not None, 'authenticated external host exchange unbound')
    original=_canonical_json(payload)
    sent=json.loads(original)
    reply=HOST_EXCHANGE(phase,sent)
    # The transport gets a detached copy. Check both copies after the callback:
    # mutation and an aliased, identically mutated reply never make an ACK valid.
    require(_canonical_json(payload)==original and _canonical_json(sent)==original, 'host callback mutated payload')
    require(isinstance(reply,dict) and set(reply)=={'phase','payload','decision','authority_sha256'}, 'host ack shape')
    require(reply['phase']==phase and _canonical_json(reply['payload'])==original and reply['decision']=='ACK' and _is_sha(reply['authority_sha256']), 'host ack mismatch')
    return reply
''' + s[end:]
one("            _inner_require_binding(self.binding,self.fds)\n            enable_subreaper()", "            _check_deadlines(self.binding)\n            _inner_require_binding(self.binding,self.fds)\n            enable_subreaper()")
one("            self.ready_ack=_host_exchange('READY',ready)\n            require(self.ready_ack", "            self.ready_ack=_host_exchange('READY',ready)\n            _check_deadlines(self.binding)\n            require(self.ready_ack")
one("            self.state='SPAWN_ATTEMPTED'\n            self.process=subprocess.Popen", "            _check_deadlines(self.binding)\n            self.state='SPAWN_ATTEMPTED'\n            self.process=subprocess.Popen")
one("        require(type(absolute_deadline) in (int,float), 'deadline type')\n        try:\n            while True:\n                left=absolute_deadline-time.monotonic()", "        try:\n            _check_deadlines(self.binding,absolute_deadline)\n            while True:\n                _check_deadlines(self.binding,absolute_deadline)\n                left=absolute_deadline-time.monotonic()")
one("            require(time.monotonic()<absolute_deadline,'direct wait crossed deadline')", "            _check_deadlines(self.binding,absolute_deadline)")
one("            require(time.monotonic()<absolute_deadline,'proof crossed deadline')", "            _check_deadlines(self.binding,absolute_deadline)")
one("            self.final_ack=_host_exchange('PROOF',receipt)\n            require(self.final_ack['authority_sha256']==self.ready_ack['authority_sha256'], 'host authority changed')\n            require(time.monotonic()<absolute_deadline,'host ack crossed deadline')", """            self.final_ack=_host_exchange('PROOF',receipt)
            require(hashlib.sha256(_canonical_json(proof)).hexdigest()==receipt['proof_sha256'], 'proof changed during host ACK')
            require(hashlib.sha256(_canonical_json(self.binding)).hexdigest()==self.binding_digest, 'binding changed during host ACK')
            require(self.final_ack['authority_sha256']==self.ready_ack['authority_sha256'], 'host authority changed')
            _check_deadlines(self.binding,absolute_deadline)""")
(p/'inner_retirement.successor.py').write_text(s)
