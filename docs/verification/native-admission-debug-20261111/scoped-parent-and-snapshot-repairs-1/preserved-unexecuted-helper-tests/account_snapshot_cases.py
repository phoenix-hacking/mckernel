"""Actual complete helper under controlled lowest record/time effects only."""
import ast
import copy
import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-code-package-preparation-sdk-max-1/a2f-fixed30-normal-operation-proposal-1/correction-1/account-snapshot-correction-1/ROOT-ISSUE-AND-EXECUTE-ONCE.py')
SOURCE_SHA='dece20d578bf7a71e4b369ce221ab7d23904da210f76f6757a30e7bea51700ab'
COHERENCE_PREFIX="fresh same-run account event/controller/credit snapshot did not stabilize: "
class LocalReads:
    def __init__(self,case):
        self.queues={key:copy.deepcopy(case[key]) for key in ("states","protocols","ledgers","times")}
        self.calls={key:0 for key in ("state","protocol","ledger","time")};self.trace=[]
    def take(self,label,key):
        self.calls[label]+=1;self.trace.append(label)
        if not self.queues[key]:raise AssertionError("controlled "+label+" read script exhausted")
        return self.queues[key].pop(0)
    def clock(self):return self.take("time","times")
    def repo(self):return LocalPath(self,"/CONTROLLED_REPO")
class LocalPath:
    def __init__(self,lower,path):self.lower=lower;self.path=PurePosixPath(path)
    def __truediv__(self,part):return LocalPath(self.lower,self.path/part)
    @property
    def parent(self):return LocalPath(self.lower,self.path.parent)
    def __str__(self):return str(self.path)
    def read_bytes(self):
        p=str(self.path)
        if p=="/CONTROLLED_REPO/.git/os-autopilot/state.json":value=self.lower.take("state","states")
        elif p=="/CONTROLLED_REPO/.git/os-autopilot/credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json":value=self.lower.take("ledger","ledgers")
        else:raise AssertionError("unexpected controlled file read: "+p)
        return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    def open(self,mode):
        assert mode=="rb" and str(self.path)=="/CONTROLLED_REPO/.git/os-autopilot/runs/20261110T060029Z-3fe88dab/protocol.jsonl"
        rows=self.lower.take("protocol","protocols")
        return io.BytesIO(b"".join((json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode() for row in rows))
def execute(unit,case):
    lower=LocalReads(case)
    ns={"__name__":"actual_account_snapshot_three_definitions","REPO":lower.repo(),"json":json,"datetime":datetime,"time":SimpleNamespace(time=lower.clock),"Decimal":Decimal,"InvalidOperation":InvalidOperation}
    exec(compile(copy.deepcopy(unit),str(SOURCE),"exec"),ns)
    result=dict(name=case["name"],outcome=None,exception=None,message=None,diagnostic=None,returned=None)
    try:
        state,usage,credit,observed=ns["current_account_snapshot"]()
        result.update(outcome="pure_data_returned",returned=dict(state=state,usage=usage,credit=credit,observed_timestamp=observed))
    except Exception as error:
        message=str(error);diagnostic=None
        if type(error) is AssertionError and message.startswith(COHERENCE_PREFIX):
            diagnostic=json.loads(message[len(COHERENCE_PREFIX):]);message=None
        result.update(outcome="refused",exception=type(error).__name__,message=message,diagnostic=diagnostic)
    result.update(calls=lower.calls,read_trace=lower.trace,scripts_remaining={name:len(lower.queues[key]) for name,key in (("state","states"),("protocol","protocols"),("ledger","ledgers"),("time","times"))},live_account_queries_or_writes=0)
    return result
def main():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    tree=ast.parse(raw.decode(),filename=str(SOURCE));names={"amount","available_balance","current_account_snapshot"}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(functions)==3
    unit=ast.Module(body=functions,type_ignores=[])
    cases=json.loads((HERE/"CONTROLLED-READ-CASES.json").read_text())["cases"]
    actual=[execute(unit,case) for case in cases]
    print(json.dumps(dict(scope="ACTUAL_ACCOUNT_SNAPSHOT_HELPER_CONTROLLED_LOWER_ONLY",issuer_or_account_or_source_state_or_credit_ledger_executed_or_mutated=False,cases=actual),sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
