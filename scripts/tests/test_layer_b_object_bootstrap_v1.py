"""Fake-only specification for the inert Layer-B controller."""
from __future__ import annotations
import stat
from run_layer_b_object_bootstrap_v1 import Controller, Lifecycle, State, _make_words, parse_make_dependencies, validate_dependency_output

def test_make_grammar_continuation_escape_dollar_and_controls() -> None:
    target,deps=parse_make_dependencies("x.o: x.c foo\\ bar.h \\\n+ baz$$.h\n")
    assert target=="x.o" and deps==["x.c","foo bar.h","baz$.h"]
    assert _make_words("a\\ b $$")==["a b","$"]
    for bad in ("x.o y.o: x.c","x.o: x.c\ny.o: y.c","no-colon"):
        try: parse_make_dependencies(bad)
        except ValueError: pass
        else: assert False

def test_first_failure_is_immutable_and_cleanup_is_additive() -> None:
    life=Lifecycle(); life.fail("submission error"); life.fail("late query error"); life.cleanup_error("group kill failed")
    assert life.first_failure=="submission error" and life.cleanup_errors==["group kill failed"]

def test_submission_failure_enters_cleanup_and_manager_kills_on_ambiguity() -> None:
    calls=[]; unit="layer-b-native-owner-bootstrap-20260928-10-n.service"
    answers=iter(({"status":1},{"status":0,"properties":{"Id":unit,"ActiveState":"active","CgroupMembers":"7"}},{"status":0},{"status":0,"properties":{"Id":unit,"ActiveState":"inactive","CgroupMembers":""}}))
    def runner(argv,timeout): calls.append(tuple(argv)); return next(answers)
    controller=Controller(unit,runner=runner,clock=lambda:1); controller.submit_once(("submit",)); assert controller.lifecycle.state==State.CLEANUP
    controller.cleanup(31)
    assert any("--signal=SIGKILL" in command for command in calls) and controller.lifecycle.state==State.EVIDENCE

def test_observation_requires_stable_identity_and_exact_success() -> None:
    unit="layer-b-native-owner-bootstrap-20260928-10-n.service"
    def runner(argv,timeout): return {"status":0,"properties":{"Id":unit,"InvocationID":"i","ControlGroup":"/u","ActiveState":"active","SubState":"exited","Result":"success","ExecMainCode":"CLD_EXITED","ExecMainStatus":0,"ExecMainExitTimestampMonotonic":"10"}}
    controller=Controller(unit,runner=runner,clock=lambda:2); controller.lifecycle.state=State.OBSERVE; controller.observe(3)
    assert controller.lifecycle.state==State.CLEANUP and controller.lifecycle.first_failure is None

def test_fake_full_path_reaches_evidence_and_terminal_without_host_commands() -> None:
    """All process/cgroup/filesystem surfaces are injected fakes in this test."""
    unit="layer-b-native-owner-bootstrap-20260928-10-n.service"; root="/review/root"; source="/review/source.c"
    class Node:
        st_mode=stat.S_IFREG|0o644; st_dev=1; st_ino=2; st_size=3; st_mtime_ns=4; st_uid=5; st_gid=6
    class Files:
        def lstat(self,path): return Node()
        def digest(self,path): return "d"
    trace="/usr/lib/gcc/x86_64-linux-gnu/9/cc1 %s %s.i %s.s /usr/bin/as %s.o"%(source,root+"/layer_b_native_owner_v1",root+"/layer_b_native_owner_v1",root+"/layer_b_native_owner_v1")
    terminal={"Id":unit,"InvocationID":"i","ControlGroup":"/u","ActiveState":"active","SubState":"exited","Result":"success","ExecMainCode":"CLD_EXITED","ExecMainStatus":0,"ExecMainExitTimestampMonotonic":"9"}
    replies=iter(({"status":0,"stderr":trace},{"status":0,"properties":terminal},{"status":0},{"status":0,"properties":{"Id":unit,"ControlGroup":"/u","ActiveState":"inactive","CgroupMembers":""}},{"status":0,"properties":{"Id":unit,"ControlGroup":"/u","ActiveState":"inactive","CgroupMembers":""}},{"status":0,"stdout":"ELF64 X86-64 REL (Relocatable file)"},{"status":0,"stdout":"ELF64 X86-64 REL (Relocatable file)"},{"status":0}))
    controller=Controller(unit,runner=lambda argv,timeout:next(replies),clock=lambda:1,filesystem=Files(),cgroup_reader=lambda group:[])
    result=controller.run(root,source,(source,1,2,3,stat.S_IFREG|0o644,4,"d"),2)
    assert result["terminal"]=="PASS_OBJECT_ONLY" and controller.lifecycle.state==State.TERMINAL

def test_dependency_validation_accepts_only_exact_generated_exemptions() -> None:
    class Node:
        st_mode=stat.S_IFREG|0o644; st_dev=1; st_ino=2; st_size=3; st_mtime_ns=4
    class Files:
        def lstat(self,path): return Node()
        def digest(self,path): return "d"
    root="/r"; source="/source.c"; header="/usr/include/stdio.h"
    # A generated-looking include is not exempt unless it is the exact private output.
    ok,errors=validate_dependency_output("/r/layer_b_native_owner_v1.o: /source.c /usr/include/x.o",root,source,[],Files())
    assert not ok and "missing prerequisite baseline: /usr/include/x.o" in errors
