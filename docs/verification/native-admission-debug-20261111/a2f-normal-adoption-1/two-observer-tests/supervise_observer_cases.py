"""Two controlled-lower executions of the complete actual observer function."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

SOURCE=Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-code-package-preparation-sdk-max-1/a2f-fixed30-normal-operation-proposal-1/prepare_current.py')
SOURCE_SHA='2cc2a3f78a4d8ababe75e2078f888e463e7ffe0ec236f063055e4783c3ad564b'
MIB=1024**2
class Lower:
    def __init__(self, error_before_roles):
        self.error_before_roles=error_before_roles;self.iteration=0
        self.counts={k:0 for k in ("boot","mono","utc","aggregate","caller_rss","process_points","children_reads","late_points","waitpid","captures","fsync","poll")}
        self.writes=[];self.durable=[];self.pending=[];self.poll_timeouts=[];self.latch_errors=[];self.registration=None;self.roles_at_second_iteration=None
        self.bootstrap="CONTROLLED_BOOTSTRAP_BYTES";self.wait_literal="CONTROLLED_WAIT_BYTES"
        prefix=b"/usr/bin/python3\0-I\0-B\0-c\0"
        raw={7001:b"/usr/bin/sudo\0-A\0",7002:prefix+self.bootstrap.encode()+b"\0",7003:prefix+self.bootstrap.encode()+b"\0",7004:prefix+self.wait_literal.encode()+b"\0"}
        self.rows={p:dict(pid=p,ppid=p-1,birth=str(p-6000),pgrp=7004 if p==7004 else 7001,uid=1000 if p==7001 else 0,rss_bytes=MIB,cmdline_sha256=hashlib.sha256(raw[p]).hexdigest()) for p in raw}
        self.raw=raw;self.children={7001:"7002",7002:"7003",7003:"7004",7004:""}
    def boot(self,domain):
        assert domain=="CONTROLLED_BOOT";self.iteration+=1;self.counts["boot"]+=1
        if self.iteration==2:self.roles_at_second_iteration=sorted(self.durable)
        if self.iteration>3:raise AssertionError("bounded controlled loop exhausted")
        return self.iteration
    def mono(self):self.counts["mono"]+=1;return self.iteration
    def utc(self):self.counts["utc"]+=1;return self.iteration
    def aggregate(self):
        self.counts["aggregate"]+=1
        return 4*1024**3+1 if not self.error_before_roles and self.iteration==2 else MIB
    def rss(self):
        self.counts["caller_rss"]+=1
        return 513*MIB if not self.error_before_roles and self.iteration==3 else 16*MIB
    def point(self,pid):
        self.counts["process_points"]+=1
        if len(self.durable)==3:self.counts["late_points"]+=1;raise ValueError("unexpected late subtree point read")
        if self.error_before_roles:raise ValueError("OBS_ERROR_"+"x"*600)
        assert pid in self.rows
        return copy.deepcopy(self.rows[pid]),self.raw[pid]
    def path(self,path):
        exact={"/proc/%d/task/%d/children"%(p,p):v for p,v in self.children.items()}
        assert path in exact
        lower=self
        class ControlledChildren:
            def open(self,mode):
                assert mode=="r";lower.counts["children_reads"]+=1
                return io.StringIO(exact[path])
        return ControlledChildren()
    def write(self,run,name,raw):
        assert run=="CONTROLLED_RUN" and name not in self.writes
        value=json.loads(raw);self.writes.append(name)
        if name.startswith("OBSERVED-"):
            assert value["status"]=="POINT_OBSERVATION_ONLY" and value["nonce_authority"] is None
            assert value["identity"]==self.rows[value["identity"]["pid"]]
            self.pending.append(value["role"])
        elif name!="CALLER-TERMINAL.json":raise AssertionError("unexpected controlled write "+name)
    def fsync(self,run):
        assert run=="CONTROLLED_RUN";self.counts["fsync"]+=1
        self.durable.extend(self.pending);self.pending=[]
    def register(self,fd,mask):assert self.registration is None;self.registration=[fd,mask]
    def poll(self,timeout):
        self.counts["poll"]+=1;self.poll_timeouts.append(timeout)
        return [(84,1)] if self.error_before_roles or self.iteration==3 else []
    def waitpid(self,pid,flags):
        self.counts["waitpid"]+=1;assert pid==7001 and flags==1
        return pid,0
    def capture(self,record,run,name):
        self.counts["captures"]+=1;assert run=="CONTROLLED_RUN" and record==name
        return dict(name=name,state="CONTROLLED_CAPTURE_ENDPOINT_ONLY",device=1,inode=1,length=0,sha256=hashlib.sha256(b"").hexdigest()),b""
    def stop(self,error):self.latch_errors.append(str(error));self.latch.failure=str(error)
    def forbidden_sleep(self,_):raise AssertionError("unexpected unresolved controlled wait branch")

def run_case(functions,error_before_roles):
    env=Lower(error_before_roles);ns={"__name__":"actual_observer_two_branch_projection","json":json,"hashlib":hashlib,"BUDGET":4*1024**3}
    exec(compile(copy.deepcopy(functions),str(SOURCE),"exec"),ns)
    ns.update(time=SimpleNamespace(CLOCK_BOOTTIME="CONTROLLED_BOOT",clock_gettime_ns=env.boot,monotonic_ns=env.mono,time_ns=env.utc,sleep=env.forbidden_sleep),select=SimpleNamespace(poll=lambda:env,POLLIN=1,POLLHUP=16,POLLERR=8,POLLNVAL=32),os=SimpleNamespace(fsync=env.fsync,waitpid=env.waitpid,WNOHANG=1),Path=env.path,proc_snapshot=env.point,overhead=env.aggregate,caller_rss=env.rss,write_new=env.write,capture_close_and_hash=env.capture)
    env.latch=SimpleNamespace(failure=None,fail=env.stop)
    request=dict(deadline_boot_ns=100,deadline_mono_ns=100,utc_cap_ns=3)
    actual=dict(sudo_overhead_observed_bytes=MIB,sudo_overhead_reserved_bytes=64*MIB)
    result=ns["supervise"]("CONTROLLED_RUN",env.latch,object(),7001,84,"1001","stdout.capture","stderr.capture",env.bootstrap,env.wait_literal,request,actual)
    return dict(name="before_roles_error_context_retained" if error_before_roles else "after_three_durable_roles_points_stop_guards_continue",status=result["status"],timed_out=result["timed_out"],resource_unknown=result["resource_unknown"],observed_roles=sorted(result["observed_roles"]),durable_roles=sorted(env.durable),roles_at_second_iteration=env.roles_at_second_iteration,counters=env.counts,poll_timeouts=env.poll_timeouts,poll_registration=env.registration,writes=env.writes,observation_errors=result["observation_errors"],observation_error_lengths=[len(v) for v in result["observation_errors"]],caller_peak_rss_bytes=result["caller_peak_rss_bytes"],host_control_observed_peak_bytes=result["host_control_observed_peak_bytes"],observation_scope=result["host_control_observation_scope"],sudo_direct_wait_status=result["sudo_direct_wait_status"],data_error=result["data_error"],verified_data=result["verified_data"],full_proof_source=result["full_proof_source"],latch_errors=env.latch_errors,native_release=result["native_release"],native_currentfree=result["native_currentfree"],reservation_release=result["reservation_release"])

def main():
    raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    tree=ast.parse(raw.decode(),filename=str(SOURCE))
    names={"fail","digest","canon","unique","owned_tree","identify_roles","parse_captured_data","supervise"}
    chosen=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(chosen)==len(names)
    budget=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=="BUDGET" for v in n.targets)]
    assert len(budget)==1
    functions=ast.Module(body=chosen+budget,type_ignores=[])
    observations=[run_case(functions,False),run_case(functions,True)]
    print(json.dumps(dict(scope="CONTROLLED_LOWER_ACTUAL_SUPERVISE_TWO_BRANCHES_ONLY",actual_live_process_proc_files_clocks_captures_or_install_used=False,cases=observations),sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
