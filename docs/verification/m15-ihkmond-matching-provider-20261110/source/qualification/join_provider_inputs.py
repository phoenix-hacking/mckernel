import hashlib, json, os, pathlib, stat, subprocess
P = pathlib.Path
out = P("/output")
def identity(name):
    p = P(name)
    value = p.read_bytes()
    actual = p.stat()
    assert stat.S_ISREG(actual.st_mode)
    return {"path": name, "resolved_path": str(p.resolve(strict=True)), "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
assert os.readlink("/qualified-libudev/libudev.so") == "libudev.so.1"
assert os.readlink("/qualified-libudev/libudev.so.1") == "/usr/lib64/libudev.so.1"
runtime = identity("/qualified-libudev/libudev.so")
assert runtime["resolved_path"] == "/usr/lib64/libudev.so.1.7.10"
assert runtime["bytes"] == 299640 and runtime["sha256"] == "034fd62bb884d5ee2244966e96db2a40970de1a423f75057380fae67ea9d0cce"
header = identity("/usr/include/libudev.h")
assert header["bytes"] == 9798 and header["sha256"] == "bd5dcd4efe29f79c1c43f3b1d8cfbdb7cc359b51b3d1edeb1676f799496e159d"
ihklib = identity("/qualified-ihklib/libihk.so")
assert ihklib["bytes"] == 12095128 and ihklib["sha256"] == "b7bcafd0923de851cd04b3934207e7217065e28434e95e505d4ed5fd4bfc96c2"
compiler = identity('/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc')
assert compiler["sha256"] == "70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09"
libcap = identity("/usr/lib64/libcap.so.2")
argv = ["/usr/bin/rpm", "-qf", "--qf", "%{NAME}|%{EPOCHNUM}|%{VERSION}|%{RELEASE}|%{ARCH}\n", "/usr/lib64/libcap.so.2"]
child = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
(out / "libcap-owner.stdout").write_bytes(child.stdout)
(out / "libcap-owner.stderr").write_bytes(child.stderr)
assert child.returncode == 0
report = {"status": "PASS_ACTUAL_SIGNED_HEADER_PRIVATE_LINK_NAMESPACE_TO_INSTALLED_RUNTIME_AND_MATCHED_INPUTS", "header_private_package": header, "runtime_installed_image": runtime, "ihklib_matching_DSO": ihklib, "real_compiler": compiler, "new_libcap_dependency": libcap, "libcap_owner_command": {"argv": argv, "returncode": child.returncode, "wait_joined": True}, "library_API_main_service_executed": False}
(out / "PROVIDER-INPUTS.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps(report, sort_keys=True))
