import importlib.util,json,tempfile
from pathlib import Path
import pytest
SRC=Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-e1c5e4e2-source-evidence-cleanup-20260930.py";s=importlib.util.spec_from_file_location("e1",SRC);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def ok():return {"lsof":{"returncode":1,"output":"","stderr":""},"mount":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n"},"docker":{"returncode":0,"output":json.dumps({"ID":m.CONTAINER_ID[:12],"Names":m.CONTAINER_NAME,"State":"exited"})},"retained_inspect":{"returncode":0,"output":json.dumps({"Status":"exited","Pid":0,"ExitCode":1,"OOMKilled":False}),"stderr":""}}
def test_pins():assert m.COMMIT.startswith("e1c5e4e2") and m.ID=="1831:4587522"
def test_census():m.validate(ok())
@pytest.mark.parametrize("k",["lsof","mount","docker","retained_inspect"])
def test_each_census_error(k):
 c=ok();c[k]["returncode"]=2
 with pytest.raises(SystemExit):m.validate(c)
def test_lsof_row():
 c=ok();c["lsof"]["output"]="COMMAND PID\nx 1\n"
 with pytest.raises(SystemExit):m.validate(c)
def test_mount_extra():
 c=ok();c["mount"]["output"]+="/dev/x ext4 1:2 /nested\n"
 with pytest.raises(SystemExit):m.validate(c)
def test_container():
 c=ok();c["docker"]["output"]+="\n"+json.dumps({"State":"running","Names":"mckernel-exact-x"})
 with pytest.raises(SystemExit):m.validate(c)
def test_retained_container_required_and_terminal():
 c=ok();c["docker"]["output"]=""
 with pytest.raises(SystemExit):m.validate(c)
 for key,value in (("Status","running"),("Pid",1),("ExitCode",0),("OOMKilled",True)):
  c=ok();state=json.loads(c["retained_inspect"]["output"]);state[key]=value;c["retained_inspect"]["output"]=json.dumps(state)
  with pytest.raises(SystemExit):m.validate(c)
def test_plan_schema():
 with pytest.raises(SystemExit):m.apply({"schema":"bad","status":"AUDIT_PASS"})
def test_packet_protects_archives():assert len(m.ARCHIVES)==2 and "container_removal" in SRC.read_text()
def test_packet_preserves_nested_ihk():assert "nested_ihk_deltas_preserved" in SRC.read_text()
def test_packet_audit_apply_split():assert "--apply" in SRC.read_text()
def test_packet_fsynchronize():assert "os.fsync" in SRC.read_text()
def test_packet_no_replace_wording():assert "nlink" in SRC.read_text()
def test_candidate_path():assert "scratch-4" in str(m.ROOT)
def test_failure_bound():assert m.FAILURE.name.endswith("failure-20260930.json")
def test_no_container_remove():assert "docker rm" not in SRC.read_text()
def test_durable_write_no_replace(tmp_path):
 p=tmp_path/"plan.json";m.write(p,{"a":1})
 with pytest.raises(SystemExit):m.write(p,{"a":2})
