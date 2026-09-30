import importlib.util,json,stat,tempfile
from pathlib import Path
import pytest
SRC=Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-e8bece7f-source-evidence-cleanup-20260930.py";s=importlib.util.spec_from_file_location("e8",SRC);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def ok():return {"lsof":{"returncode":1,"output":"","stderr":""},"mount":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n"},"docker":{"returncode":0,"output":json.dumps({"ID":m.EXPECTED_CONTAINER,"State":"exited","Names":"mckernel-exact-retained"})}}
def test_pins():assert m.CANDIDATE_COMMIT.startswith("e8bece7f") and m.CANDIDATE_IDENTITY=="1831:5111900"
def test_census_ok():m.validate_census(ok())
@pytest.mark.parametrize("k",["lsof","mount","docker"])
def test_census_failures(k):
 c=ok();c[k]["returncode"]=2
 with pytest.raises(SystemExit):m.validate_census(c)
def test_open_reference():
 c=ok();c["lsof"]["output"]="COMMAND PID\nx 1\n"
 with pytest.raises(SystemExit):m.validate_census(c)
def test_nested_mount():
 c=ok();c["mount"]["output"]+="/dev/x ext4 1:2 /nested\n"
 with pytest.raises(SystemExit):m.validate_census(c)
def test_running_container():
 c=ok();c["docker"]["output"]+="\n"+json.dumps({"State":"running","Names":"mckernel-exact-8"})
 with pytest.raises(SystemExit):m.validate_census(c)
def test_retained_container_absent_or_live():
 for output in ("",json.dumps({"ID":m.EXPECTED_CONTAINER,"State":"running","Names":"mckernel-exact-retained"})):
  c=ok();c["docker"]["output"]=output
  with pytest.raises(SystemExit):m.validate_census(c)
def test_no_replace(tmp_path):
 p=tmp_path/"x";m.write(p,{"a":1})
 with pytest.raises(SystemExit):m.write(p,{"a":2})
def test_apply_bad_plan():
 with pytest.raises(SystemExit):m.apply({"schema":"bad","status":"AUDIT_PASS"})
def test_packet_preserves_deltas():
    text=SRC.read_text(); assert "nested_ihk_deltas_preserved" in text and "container_removal" in text and "p.unlink()" in text
