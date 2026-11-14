"""Functional OS source-only materialization, no security testing or runtime effect.
Genuine Root parent tool join fills the only missing immutable binding identities.
Root still authors typed ledger/release; independent reviews/publication required.
"""
from pathlib import Path
import argparse,json,hashlib,ast
D=Path(__file__).resolve().parent
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 ap=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);ap.add_argument('--parent-tool-join',type=Path,required=True);ap.add_argument('--parent-tool-join-sha256',required=True);a=ap.parse_args();r=ref(a.parent_tool_join);assert r['sha256']==a.parent_tool_join_sha256
 q=json.loads(a.parent_tool_join.read_text());assert q['author']=='/root'and q['decision']=='ROOT_ATTESTS_OBSERVED_ACTUAL_TOOL_SESSION_JOIN'and q['session_id']==63230 and q['joined']is True and q['returncode']==0 and q['actual_tool_response']['exit_code']==0;assert isinstance(q['actual_tool_response']['chunk_id'],str)and q['actual_tool_response']['chunk_id']
 b=json.loads((D/'BINDINGS.TEMPLATE.NOT-AUTHORITY.json').read_text());b['parent_tool_join']=r;b['parent_tool_chunk_id']=q['actual_tool_response']['chunk_id'];raw=(json.dumps(b,indent=2)+'\n').encode();sha=hashlib.sha256(raw).hexdigest();s=(D/'retire_exact_current119_stopped_container.UNBOUND.py').read_text();anchor='BINDINGS_SHA=None  # Materialize only after genuine Root parent join and typed ledger.';assert s.count(anchor)==1;s=s.replace(anchor,'BINDINGS_SHA='+repr(sha));ast.parse(s)
 for name,data in [('BINDINGS.json',raw),('retire_exact_current119_stopped_container.py',s.encode())]:
  with (D/name).open('xb')as f:f.write(data)
 files=dict(executor=ref(D/'retire_exact_current119_stopped_container.py'),bindings=ref(D/'BINDINGS.json'));files.update({k:b[k]for k in ('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor','wait_status_helper','pre_compatibility_executor')})
 with (D/'RUNTIME-FILES.json').open('x')as f:json.dump(files,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='SOURCE_ONLY_BOUND_AWAIT_PUBLICATION_REVIEW_RELEASE',files=files,runtime_authority=None)))
if __name__=='__main__':main()
