# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,re
C=Path(__file__).resolve().parent;P=C.parent;M=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/service-ebusy-sdk-preparation-7/prepared-sdk/CURRENT68-PROCFS-DELETE-INPUT-MAP.json');S=M.parent/'source-modules'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def strip(src):
 return re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),src,flags=re.S)
def calls(src):
 code=strip(src);out=[]
 for match in re.finditer(r'((?:\w+\.)+)fail\s*\(',code):
  start=match.end();stack=['('];args=[];begin=start;i=start
  while stack:
   c=code[i]
   if c in '([{':stack.append(c)
   elif c in ')]}':
    assert {'(':')','[':']','{':'}'}[stack[-1]]==c
    stack.pop()
   elif c==',' and len(stack)==1:args.append(code[begin:i].strip());begin=i+1
   i+=1
  last=code[begin:i-1].strip()
  if last:args.append(last)
  out.append(dict(receiver=match.group(1)[:-1],line=src[:match.start()].count('\n')+1,args=args,source=src[match.start():i]))
 return out
j=json.loads(M.read_text());rows=j['source_identity_rows'];assert len(rows)==68
closure=[];before=[];after=[]
for key,sha,size in rows:
 q=S/key;assert q.stat().st_size==size and pin(q)['sha256']==sha
 original=q.read_text();new=(C/'source/smp_service.rs').read_text() if key=='smp_service.rs' else original
 closure.append(dict(key=key,selected=pin(q),successor=pin(C/'source/smp_service.rs') if key=='smp_service.rs' else pin(q)))
 for dest,src in [(before,original),(after,new)]:
  for call in calls(src):dest.append(dict(key=key,**call))
assert len(before)==len(after)==11,(len(before),len(after))
assert [(r['key'],len(r['args'])) for r in before if len(r['args'])!=2]==[('smp_service.rs',1)]
assert all(len(r['args'])==2 and r['args'][1].startswith('FailureOrigin::') for r in after)
assert all(r['key']=='smp_service.rs' and r['receiver'] in ['self','entry.runtime','self.runtime'] for r in after)
assert sum('FirstPacket' in r['source'] for r in after)==1
for a,b in zip(before,after):
 if len(a['args'])==2:assert a['source']==b['source']
 else:assert a['receiver']==b['receiver']=='self.runtime' and a['args']==b['args'][:1]==['error']
old=(P/'source/smp_service.rs').read_text();new=(C/'source/smp_service.rs').read_text();assert old==(S/'smp_service.rs').read_text()
# Invert exactly four additive changes: no functional body or other caller diff.
inverse=new.replace('    FirstPacket { message: i32 },\n','',1).replace('            Self::FirstPacket { .. } => "first_dispatch",\n','',1)
inverse=inverse.replace('''            if let FailureOrigin::FirstPacket { message } = origin {
                pr_err!("IHK-P os={} g={} d={} port=503 m={:x}\\n",
                    self.owner.slot(), self.owner.generation(), diag, message);
            }
''','',1)
inverse=inverse.replace('''            self.runtime.fail(error, FailureOrigin::FirstPacket {
                message: i32::from_le_bytes(packet[8..12].try_into().unwrap()),
            });''','''            self.runtime.fail(error);''',1)
assert inverse==old
assert new.count('fn fail(&self, error: Error, origin: FailureOrigin)')==1
assert not re.search(r'\bRuntime\s*::\s*fail\b',strip(new))
# New first-packet log consumes the same16-ticket group and uses header8..12.
assert 'if let Some(diag) = diagnostic_ticket(&self.failure_contexts)' in new
line='IHK-P os=4294967295 g=18446744073709551615 d=16 port=503 m=ffffffff\n';assert len(line)+96<=255
fixture=(C/'fixture/diagnostic.rs').read_text();assert 'origins=11' in fixture and 'first_fixture::test();' in fixture and 'FailureOrigin::FirstPacket{message:i32::MIN}' in fixture
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_FINITE68_SOURCE_11_FAIL_CALLER_COVERAGE_NOT_RUST_TYPECHECK',selected_map=pin(M),input_closure=closure,before=before,after=after,callers=11,original_omissions=1,successor_omissions=0,unchanged_prior_ten_calls=True,exact_four_additive_changes_invert_to_failed_preimage=True,new_format_total_bytes_with96prefix=len(line)+96,existing16ticket_budget_unchanged=True,actual_SDK7_successor_compile=None,diagnostic_semantics_only=True,canonical_writes=0)
(C/'ACTUAL-FAIL-CALL-COVERAGE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],callers=11,omissions=0,new_line_plus96=len(line)+96)))
