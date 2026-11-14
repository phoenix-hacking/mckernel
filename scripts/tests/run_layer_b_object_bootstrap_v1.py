"""Fail-closed, injectable controller for the Layer-B object-only packet.

Importing this module is inert: no host inspection, root creation, compiler or
manager command. A reviewed dispatcher alone provides runner/clock/filesystem.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import re
import stat
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

APPROVED_ROOTS = ("/usr/lib/gcc/x86_64-linux-gnu/9/include", "/usr/include/x86_64-linux-gnu", "/usr/include")
SOURCE_SHA256 = "2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc"
TEST_SHA256 = "427f6133497ce0706fce39d9e52051542821bc6deab29d27322733c927efd63d"
UNIT_RE = re.compile(r"^layer-b-native-owner-bootstrap-20260928-10-([A-Za-z0-9-]+)\\.service$")
GENERATED = frozenset((".i", ".s", ".o", ".d"))
TOOL_PATHS = ("/usr/bin/gcc", "/usr/lib/gcc/x86_64-linux-gnu/9/cc1", "/usr/bin/as", "/usr/bin/env", "/usr/bin/prlimit", "/usr/bin/timeout", "/usr/bin/systemd-run", "/usr/bin/systemctl", "/usr/bin/journalctl", "/usr/bin/readelf", "/usr/bin/objdump")

class State(str, Enum):
    PRECHECK="PRECHECK"; SUBMIT_ONCE="SUBMIT_ONCE"; OBSERVE="OBSERVE"; CLEANUP="CLEANUP"; EVIDENCE="EVIDENCE"; TERMINAL="TERMINAL"

@dataclass(frozen=True)
class Entry:
    spelling: str; kind: str; mode: int=0; uid: int=-1; gid: int=-1; size: int=0
    digest: str|None=None; target: str|None=None; hops: tuple[str,...]=(); canonical: str|None=None
    external_directory: bool=False; device: int=0; inode: int=0

@dataclass
class Lifecycle:
    state: State=State.PRECHECK; first_failure: str|None=None
    cleanup_errors: list[str]=field(default_factory=list); evidence_errors: list[str]=field(default_factory=list)
    responses: list[Mapping[str,Any]]=field(default_factory=list); stopped: bool=False; terminal: str|None=None
    def fail(self, reason: str) -> None:
        if self.first_failure is None: self.first_failure=reason
    def cleanup_error(self, reason: str) -> None: self.cleanup_errors.append(reason)

def _digest(path: str, opener: Callable[...,Any]=open) -> str:
    digest=hashlib.sha256()
    with opener(path,"rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()

def _inside(path: str, roots: Sequence[str]) -> bool:
    return any(path==root or path.startswith(root.rstrip(os.sep)+os.sep) for root in roots)

def _kind(mode: int) -> str:
    return "symlink" if stat.S_ISLNK(mode) else "file" if stat.S_ISREG(mode) else "directory" if stat.S_ISDIR(mode) else "other"

class LocalFilesystem:
    lstat=staticmethod(os.lstat); readlink=staticmethod(os.readlink); listdir=staticmethod(os.listdir)
    isdir=staticmethod(os.path.isdir); exists=staticmethod(os.path.lexists); digest=staticmethod(_digest)

def _component_resolution(path: str, fs: Any, roots: Sequence[str]) -> tuple[tuple[str,...],str|None,bool]:
    """Resolve each link component; a broken path/loop is never canonical."""
    pending=os.path.normpath(path); hops=[]; seen=set()
    for _ in range(80):
        absolute=os.path.isabs(pending); parts=[x for x in pending.split(os.sep) if x and x!="."]
        cursor=os.sep if absolute else ""; replaced=False
        for index, part in enumerate(parts):
            cursor=os.path.join(cursor,part) if cursor else part
            try: node=fs.lstat(cursor)
            except OSError: return tuple(hops),None,False
            if not stat.S_ISLNK(node.st_mode): continue
            if cursor in seen: return tuple(hops+[cursor]),None,False
            seen.add(cursor); hops.append(cursor)
            target=fs.readlink(cursor); tail=parts[index+1:]
            pending=os.path.normpath(os.path.join(target,*tail) if os.path.isabs(target) else os.path.join(os.path.dirname(cursor),target,*tail))
            replaced=True; break
        if not replaced: return tuple(hops),os.path.normpath(pending),_inside(os.path.normpath(pending),roots)
    return tuple(hops),None,False

def inventory_roots(roots: Sequence[str]=APPROVED_ROOTS, fs: Any=None) -> tuple[list[Entry],list[str]]:
    """lstat walk retaining spellings/device+inode, excluded links and walk errors."""
    fs=LocalFilesystem() if fs is None else fs; entries=[]; errors=[]; walked=set()
    def visit(spelling: str) -> None:
        try: node=fs.lstat(spelling)
        except OSError as exc: errors.append("lstat "+spelling+": "+str(exc)); return
        kind=_kind(node.st_mode)
        if kind=="symlink":
            try: target=fs.readlink(spelling)
            except OSError as exc: errors.append("readlink "+spelling+": "+str(exc)); target=None
            hops,canonical,within=_component_resolution(spelling,fs,roots)
            external=bool(canonical and fs.isdir(canonical) and not within)
            entries.append(Entry(spelling,kind,node.st_mode,node.st_uid,node.st_gid,node.st_size,target=target,hops=hops,canonical=canonical,external_directory=external,device=node.st_dev,inode=node.st_ino)); return
        entries.append(Entry(spelling,kind,node.st_mode,node.st_uid,node.st_gid,node.st_size,fs.digest(spelling) if kind=="file" else None,canonical=os.path.normpath(spelling),device=node.st_dev,inode=node.st_ino))
        key=(node.st_dev,node.st_ino)
        if kind!="directory" or key in walked: return
        walked.add(key)
        try: names=sorted(fs.listdir(spelling))
        except OSError as exc: errors.append("walk "+spelling+": "+str(exc)); return
        for name in names: visit(os.path.join(spelling,name))
    for root in roots: visit(root)
    return entries,errors

def _make_words(text: str) -> list[str]:
    """Finite Make grammar: continuation becomes whitespace, escapes and $$ work."""
    words=[]; buf=[]; i=0
    while i<len(text):
        char=text[i]
        if char=="\\" and i+1<len(text):
            nxt=text[i+1]
            if nxt=="\n":
                if buf: words.append("".join(buf)); buf=[]
            else: buf.append(nxt)
            i+=2; continue
        if char=="$" and i+1<len(text) and text[i+1]=="$": buf.append("$"); i+=2; continue
        if char in " \t\r\n":
            if buf: words.append("".join(buf)); buf=[]
        else: buf.append(char)
        i+=1
    if buf: words.append("".join(buf))
    return words

def parse_make_dependencies(text: str) -> tuple[str,list[str]]:
    """Exactly one unescaped rule and target; reject malformed multi-rule input."""
    rule=text.replace("\\\r\n"," ").replace("\\\n"," "); colon=-1; escaped=False
    for i,char in enumerate(rule):
        if escaped: escaped=False; continue
        if char=="\\": escaped=True; continue
        if char==":":
            if colon>=0: raise ValueError("dependency file has multiple rules")
            colon=i
    if colon<=0 or "\n" in rule[colon+1:].strip(" \t"): raise ValueError("dependency file must contain one rule")
    targets=_make_words(rule[:colon]); deps=_make_words(rule[colon+1:])
    if len(targets)!=1 or not deps: raise ValueError("dependency file must have one target and prerequisites")
    return targets[0],deps

def identity(path: str, fs: Any=None) -> tuple[str,int,int,int,int,int,str]:
    fs=LocalFilesystem() if fs is None else fs; node=fs.lstat(path)
    if not stat.S_ISREG(node.st_mode): raise ValueError("source is not a regular file")
    return os.path.normpath(path),node.st_dev,node.st_ino,node.st_size,node.st_mode,node.st_mtime_ns,fs.digest(path)

def classify_prerequisites(entries: Sequence[str], baseline: Sequence[Entry], source: str, roots: Sequence[str]=APPROVED_ROOTS, fs: Any=None, generated: Sequence[str]=()) -> tuple[bool,list[str]]:
    fs=LocalFilesystem() if fs is None else fs; by_path={entry.spelling:entry for entry in baseline}; errors=[]; seen_source=0
    for raw in entries:
        spelling=os.path.normpath(raw)
        if spelling==source: seen_source+=1; continue
        # Only the four recorded private outputs are exempt, never an arbitrary
        # header merely because its spelling has a generated-looking suffix.
        if spelling in {os.path.normpath(item) for item in generated}: continue
        hops,canonical,within=_component_resolution(spelling,fs,roots)
        if canonical is None: errors.append("broken or cyclic prerequisite: "+spelling); continue
        if not within: errors.append("prerequisite outside approved roots: "+spelling); continue
        if any(entry.external_directory and entry.spelling in hops for entry in baseline): errors.append("consumed excluded external link: "+spelling); continue
        entry=by_path.get(spelling)
        if entry is None or entry.kind!="file": errors.append("missing prerequisite baseline: "+spelling); continue
        try:
            node=fs.lstat(spelling); unchanged=(node.st_dev,node.st_ino,node.st_mode,node.st_size,fs.digest(spelling))==(entry.device,entry.inode,entry.mode,entry.size,entry.digest)
        except OSError: unchanged=False
        if not unchanged: errors.append("changed prerequisite baseline: "+spelling)
    if seen_source!=1: errors.append("source prerequisite must occur exactly once")
    return not errors,errors

def validate_dependency_output(text: str, root: str, source: str, baseline: Sequence[Entry], fs: Any=None) -> tuple[bool,list[str]]:
    """Validate the one expected Make rule and exact generated-output exemptions."""
    base=os.path.join(root,"layer_b_native_owner_v1")
    target,deps=parse_make_dependencies(text)
    errors=[] if target==base+".o" else ["dependency target is not exact object output"]
    ok,dependency_errors=classify_prerequisites(deps,baseline,source,fs=fs,generated=(base+".i",base+".s",base+".o",base+".d"))
    return ok and not errors,errors+dependency_errors

def validate_preflight(root: str, source: str, unit: str, expected_tools: Mapping[str,str], fs: Any=None, unit_probe: Callable[[str],Mapping[str,Any]]|None=None) -> tuple[bool,list[str],tuple[Any,...]|None]:
    """Read-only, exclusive preflight; it deliberately does not create anything."""
    fs=LocalFilesystem() if fs is None else fs; errors=[]
    if not os.path.isabs(root) or os.path.normpath(root)!=root or fs.exists(root): errors.append("root is not canonical absent")
    if not UNIT_RE.fullmatch(unit): errors.append("unit nonce/service spelling is invalid")
    if set(expected_tools)!=set(TOOL_PATHS): errors.append("tool set is not exact")
    for tool in TOOL_PATHS:
        try:
            node=fs.lstat(tool)
            if not stat.S_ISREG(node.st_mode) or fs.digest(tool)!=expected_tools.get(tool): errors.append("tool identity mismatch: "+tool)
        except OSError: errors.append("missing tool: "+tool)
    if unit_probe is not None:
        try: probe=unit_probe(unit)
        except Exception as exc: errors.append("unit preflight error: "+str(exc)); probe={}
        if probe.get("LoadState") not in ("not-found","not loaded",None) or probe.get("Id")==unit: errors.append("unit is not absent")
    try: source_identity=identity(source,fs)
    except (OSError,ValueError) as exc: errors.append("source identity error: "+str(exc)); source_identity=None
    return not errors,errors,source_identity

def artifact_inventory(root: str, fs: Any=None) -> tuple[list[Entry],list[str]]:
    """Retain a non-following output-tree inventory for evidence, including tmp."""
    return inventory_roots((root,),fs)

def object_argv(root: str, source: str, unit: str) -> list[str]:
    if not os.path.isabs(root) or os.path.normpath(root)!=root or not os.path.isabs(source) or os.path.normpath(source)!=source or not UNIT_RE.fullmatch(unit): raise ValueError("canonical absolute root/source and exact service unit required")
    base=os.path.join(root,"layer_b_native_owner_v1")
    return ["/usr/bin/timeout","--signal=TERM","--kill-after=1s","10s","/usr/bin/systemd-run","--user","--unit="+unit,"--service-type=exec","--working-directory="+root,"--property=RemainAfterExit=yes","--property=Restart=no","--property=KillMode=control-group","--property=RuntimeMaxSec=60s","--property=TimeoutStartSec=10s","--property=TimeoutStopSec=5s","--property=SendSIGKILL=yes","--property=UMask=0077","--property=StandardInput=null","--property=StandardOutput=file:"+root+"/logs/unit.stdout","--property=StandardError=file:"+root+"/logs/unit.stderr","--","/usr/bin/env","-i","LC_ALL=C","LANG=C","HOME="+root+"/home","TMPDIR="+root+"/tmp","PATH=/usr/bin:/bin","/usr/bin/prlimit","--core=0:0","--cpu=55:55","--nofile=256:256","--fsize=67108864:67108864","--as=536870912:536870912","--","/usr/bin/gcc","-v","-std=c11","-O2","-Wall","-Wextra","-Werror","-fno-pie","-pthread","-nostdinc","-isystem",APPROVED_ROOTS[0],"-isystem",APPROVED_ROOTS[1],"-isystem",APPROVED_ROOTS[2],"-save-temps=obj","-MD","-MF",base+".d","-MT",base+".o","-c",source,"-o",base+".o"]

def _ok(result: Mapping[str,Any]) -> bool: return not result.get("timed_out") and int(result.get("status",0))==0

def validate_compiler_trace(stderr: str, source: str, root: str) -> list[str]:
    base=os.path.join(root,"layer_b_native_owner_v1"); needed=("/usr/lib/gcc/x86_64-linux-gnu/9/cc1",source,base+".i",base+".s","/usr/bin/as",base+".o")
    errors=["compiler trace missing: "+item for item in needed if item not in stderr]
    if any(token in stderr for token in ("collect2"," /usr/bin/ld"," -plugin"," -specs=")): errors.append("compiler trace includes forbidden link/plugin/spec")
    return errors

def parse_static_object(readelf: Mapping[str,Any], objdump: Mapping[str,Any]) -> list[str]:
    text=str(readelf.get("stdout",""))+"\n"+str(objdump.get("stdout","")); errors=[]
    if not _ok(readelf) or not _ok(objdump): errors.append("static inspection command failed")
    if "ELF64" not in text or "X86-64" not in text or "REL (Relocatable file)" not in text: errors.append("object is not ELF64 x86-64 ET_REL")
    return errors

@dataclass
class Controller:
    unit: str; runner: Callable[[Sequence[str],float],Mapping[str,Any]]|None=None; clock: Callable[[],float]=time.monotonic; filesystem: Any=None; cgroup_reader: Callable[[str],Sequence[str]]|None=None; lifecycle: Lifecycle=field(default_factory=Lifecycle); invocation_id: str|None=None; control_group: str|None=None; source_pre: tuple[Any,...]|None=None
    def _run(self, argv: Sequence[str], seconds: float) -> Mapping[str,Any]:
        if self.runner is None: raise RuntimeError("no reviewed dispatcher runner supplied")
        try: return self.runner(tuple(argv),seconds)
        except Exception as exc: return {"status":125,"error":str(exc),"timed_out":False}
    def submit_once(self, argv: Sequence[str]) -> Mapping[str,Any]:
        if self.lifecycle.state!=State.PRECHECK: raise RuntimeError("submission is not first state")
        self.lifecycle.state=State.SUBMIT_ONCE; result=self._run(argv,11.0)
        if _ok(result): self.lifecycle.state=State.OBSERVE
        else: self.lifecycle.fail("submission error or timeout"); self.lifecycle.state=State.CLEANUP
        return result
    def observe(self, deadline: float) -> Mapping[str,Any]:
        if self.lifecycle.state!=State.OBSERVE: raise RuntimeError("not observing")
        result=self._run(("/usr/bin/systemctl","--user","show",self.unit),3.0); self.lifecycle.responses.append(result); response=result.get("properties",result)
        if not _ok(result): self.lifecycle.fail("query error or timeout")
        if response.get("Id")!=self.unit or not response.get("InvocationID") or not response.get("ControlGroup"): self.lifecycle.fail("missing or ambiguous unit identity")
        elif self.invocation_id is None: self.invocation_id=str(response["InvocationID"]); self.control_group=str(response["ControlGroup"])
        elif response.get("InvocationID")!=self.invocation_id or response.get("ControlGroup")!=self.control_group: self.lifecycle.fail("changed unit identity")
        active,sub=response.get("ActiveState"),response.get("SubState")
        success=active=="active" and sub=="exited" and response.get("Result")=="success" and str(response.get("ExecMainCode")) in ("1","CLD_EXITED") and str(response.get("ExecMainStatus"))=="0" and bool(response.get("ExecMainExitTimestampMonotonic"))
        pending=active=="activating" or (active=="active" and sub=="running")
        if not success and not pending: self.lifecycle.fail("unexpected unit terminal state")
        if self.clock()>deadline: self.lifecycle.fail("observation deadline")
        if success or self.lifecycle.first_failure: self.lifecycle.state=State.CLEANUP
        return response
    def cleanup(self, deadline: float) -> None:
        if self.lifecycle.state!=State.CLEANUP: raise RuntimeError("not cleanup")
        stop=self._run(("/usr/bin/systemctl","--user","stop",self.unit),8.0); self.lifecycle.stopped=_ok(stop); ambiguous=not self.lifecycle.stopped
        query=self._run(("/usr/bin/systemctl","--user","show",self.unit),3.0); props=query.get("properties",query); members=[]
        if self.control_group:
            if self.cgroup_reader is None: ambiguous=True; members=["uninspectable"]
            else:
                try: members=list(self.cgroup_reader(self.control_group))
                except Exception as exc: ambiguous=True; members=["uninspectable"]; self.lifecycle.cleanup_error("cgroup reconciliation error: "+str(exc))
        live=props.get("ActiveState") in ("activating","active","deactivating") or bool(props.get("CgroupMembers")) or bool(members)
        if not _ok(query) or props.get("Id")!=self.unit or (self.control_group and props.get("ControlGroup") not in (self.control_group,"")): ambiguous=True
        if ambiguous or live:
            kill=self._run(("/usr/bin/systemctl","--user","--signal=SIGKILL","--kill-who=all","kill",self.unit),3.0)
            if not _ok(kill): self.lifecycle.cleanup_error("manager-side group kill failed")
        final=self._run(("/usr/bin/systemctl","--user","show",self.unit),3.0); final_props=final.get("properties",final); inactive=final_props.get("ActiveState")=="inactive" or final_props.get("LoadState") in ("not-found","not loaded")
        final_members=[]
        if self.control_group and self.cgroup_reader is not None:
            try: final_members=list(self.cgroup_reader(self.control_group))
            except Exception: final_members=["uninspectable"]
        if not _ok(final) or not inactive or final_props.get("CgroupMembers") or final_members: self.lifecycle.fail("FAIL_UNRESOLVED")
        if self.clock()>deadline: self.lifecycle.fail("FAIL_UNRESOLVED cleanup budget exhausted")
        self.lifecycle.state=State.EVIDENCE
    def evidence(self, root: str, source: str) -> dict[str,Any]:
        if self.lifecycle.state!=State.EVIDENCE: raise RuntimeError("not evidence")
        record={"unit":self.unit,"responses":list(self.lifecycle.responses),"source_pre_identity":self.source_pre,"first_failure":self.lifecycle.first_failure,"cleanup_errors":list(self.lifecycle.cleanup_errors)}
        if self.lifecycle.first_failure is None:
            readelf=self._run(("/usr/bin/readelf","-h","-S","-s",os.path.join(root,"layer_b_native_owner_v1.o")),6.0); objdump=self._run(("/usr/bin/objdump","-f",os.path.join(root,"layer_b_native_owner_v1.o")),6.0); record["inspection"]={"readelf":readelf,"objdump":objdump}
            for error in parse_static_object(readelf,objdump): self.lifecycle.fail(error)
        record["journal"]=self._run(("/usr/bin/journalctl","--user","-u",self.unit,"--no-pager","-o","short-monotonic"),6.0); record["source_post_identity"]=identity(source,self.filesystem)
        self.lifecycle.state=State.TERMINAL; self.lifecycle.terminal="FAIL" if self.lifecycle.first_failure else "PASS_OBJECT_ONLY"; record["first_failure"]=self.lifecycle.first_failure; record["terminal"]=self.lifecycle.terminal
        return record
    def run(self, root: str, source: str, source_pre: tuple[Any,...], deadline: float) -> dict[str,Any]:
        self.source_pre=source_pre; submission=self.submit_once(object_argv(root,source,self.unit))
        if self.lifecycle.state==State.OBSERVE:
            for error in validate_compiler_trace(str(submission.get("stderr","")),source,root): self.lifecycle.fail(error)
            if self.lifecycle.first_failure: self.lifecycle.state=State.CLEANUP
        if self.lifecycle.state==State.OBSERVE: self.observe(deadline)
        if self.lifecycle.state==State.CLEANUP: self.cleanup(self.clock()+30.0)
        if identity(source,self.filesystem)!=source_pre: self.lifecycle.fail("source post identity changed")
        return self.evidence(root,source)

def execute(args: argparse.Namespace, runner: Any=None) -> None:
    if not args.execute or args.source_sha256!=SOURCE_SHA256 or args.test_sha256!=TEST_SHA256: raise PermissionError("--execute and exact source/test hashes are mandatory")
    if runner is None: raise RuntimeError("no reviewed dispatcher runner supplied")
    raise RuntimeError("controller execution requires separately reviewed dispatcher preflight")

def main(argv: Sequence[str]|None=None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--execute",action="store_true"); parser.add_argument("--source-sha256"); parser.add_argument("--test-sha256"); execute(parser.parse_args(argv)); return 0
