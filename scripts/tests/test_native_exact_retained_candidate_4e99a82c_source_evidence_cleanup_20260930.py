import importlib.util,json,os
from pathlib import Path
import pytest
SRC=Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-4e99a82c-source-evidence-cleanup-20260930.py";s=importlib.util.spec_from_file_location("p",SRC);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def clean():return {"lsof":{"returncode":1,"output":"","stderr":""},"mount":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n"},"nested_mounts":[],"docker":{"returncode":0,"output":json.dumps({"ID":m.CONTAINER_ID[:12],"Names":m.CONTAINER_NAME,"State":"exited"})},"inspect":{"returncode":0,"output":json.dumps({"Status":"exited","Pid":0,"ExitCode":1,"OOMKilled":False}),"stderr":""}}
def test_binding():assert m.COMMIT.startswith("4e99a82c") and m.ID=="1831:3693246"
def test_clean():m.validate(clean())
@pytest.mark.parametrize("k",["lsof","mount","docker","inspect"])
def test_fail_closed(k):
 c=clean();c[k]["returncode"]=2
 with pytest.raises(SystemExit):m.validate(c)
def test_nested_mount_and_paused_state():
 c=clean();c["nested_mounts"]=[str(m.ROOT/"mounted")]
 with pytest.raises(SystemExit):m.validate(c)
 c=clean();c["docker"]["output"]=json.dumps({"ID":m.CONTAINER_ID[:12],"Names":m.CONTAINER_NAME,"State":"paused"})
 with pytest.raises(SystemExit):m.validate(c)
def test_live_reference_and_terminal_state():
 c=clean();c["lsof"]["output"]="COMMAND PID\nrace 2\n"
 with pytest.raises(SystemExit):m.validate(c)
 c=clean();c["inspect"]["output"]=json.dumps({"Status":"exited","Pid":1,"ExitCode":1,"OOMKilled":False})
 with pytest.raises(SystemExit):m.validate(c)
def test_filters_and_read_only_contract():
 t=SRC.read_text()
 for token in ("os.unlink","os.rmdir","os.remove","os.replace","def apply","--apply","--result","docker rm","container_removal"):assert token not in t
 assert "p.is_symlink()" in t and "s.st_nlink!=1" in t and "protected()" in t
def test_short_write_and_collision(tmp_path,monkeypatch):
 p=tmp_path/"plan";real=os.write
 def short(fd,data):return real(fd,data[:1])
 monkeypatch.setattr(m.os,"write",short);m.publish(p,{"status":"AUDIT_PASS"})
 with pytest.raises(SystemExit):m.publish(p,{"status":"AUDIT_PASS"})
def test_protected_inputs():
 assert any("exportset-24" in str(x) for x in m.PROTECTED);assert any("libdwarf" in str(x) for x in m.PROTECTED);assert any("nightly" in str(x) for x in m.PROTECTED)
