"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual proposed read-only /info function with fixture-only HTTP/socket observations.
No socket connection, Docker API request, root command or workload is executed.
"""
from pathlib import Path
from unittest.mock import patch
import importlib.util, json, os, resource, struct

D=Path(__file__).resolve().parent
assert os.sched_getaffinity(0)=={0}
assert resource.getrlimit(resource.RLIMIT_AS)[0]<=512*2**20
spec=importlib.util.spec_from_file_location('proposed_query_fixture',D/'query_daemon_filesystem.NOT-EXECUTED.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
results=[]
for name,updates,error in [
    ('effective-local-root',{},False),
    ('activation-listener-recorded',{'peer':(1,0,0)},False),
    ('nonroot-peer',{'peer':(2036,1000,1000)},True),
    ('HTTP-error',{'status':500},True),
    ('unexpected-encoding',{'encoding':'gzip'},True),
    ('missing-root',{'body':b'{}'},True),
    ('nonstring-root',{'body':b'{"DockerRootDir":17}'},True),
    ('response-bound',{'body':b'x'*(2*2**20+1)},True),
]:
    case=dict(peer=(2036,0,0),status=200,encoding=None,body=b'{"DockerRootDir":"/var/lib/docker"}')
    case.update(updates);calls=[];closed=[]
    class FakeSocket:
        def __init__(self,family,kind):assert (family,kind)==(q.socket.AF_UNIX,q.socket.SOCK_STREAM)
        def settimeout(self,value):assert value==15
        def connect(self,path):assert path=='/var/run/docker.sock';calls.append(('connect',path))
        def getsockopt(self,level,key,count):
            assert (level,key,count)==(q.socket.SOL_SOCKET,q.socket.SO_PEERCRED,12)
            return struct.pack('3i',*case['peer'])
        def close(self):closed.append(True)
    class FakeResponse:
        status=case['status']
        def getheader(self,key):assert key=='Content-Encoding';return case['encoding']
        def read(self,count):assert count==2*2**20+1;return case['body']
    class FakeHTTP:
        def __init__(self,host,timeout):assert (host,timeout)==('localhost',15);self.sock=None
        def request(self,method,path,headers):
            assert (method,path)==('GET','/info')
            assert headers=={'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
            self.connect();calls.append(('request',method,path))
        def getresponse(self):return FakeResponse()
        def close(self):
            if self.sock is not None:self.sock.close()
    with patch.object(q.http.client,'HTTPConnection',FakeHTTP),patch.object(q.socket,'socket',FakeSocket):
        try:
            root,receipt=q.effective_root()
        except (RuntimeError,ValueError):assert error,name
        else:
            assert not error and root=='/var/lib/docker',name
            assert receipt['configuration_or_plugin_reads'] is False
            assert receipt['peer_pid_matches_observed_daemon']==(case['peer'][0]==2036)
    assert closed==[True],name
    results.append(dict(name=name,result='PASS_REFUSE' if error else 'PASS_OBSERVE'))
report=dict(scope=__doc__.splitlines()[0],status='PASS_8_ACTUAL_EFFECTIVE_ROOT_OBSERVATION_FIXTURES',
            observations=results,root_query_executions=0,socket_connections=0,workloads=0,
            physical_allocation_bound=False,execution_release='NOT_RELEASED')
(D/'READONLY-QUERY-FIXTURE-RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],count=len(results))))
