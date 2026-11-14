// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! One fixed valid idle mcinspect profile; generic process supervision is reused.
pub const PAYLOAD_ARGV: &[&str] = &["/case/tools/mcinspect", "--kernel=/images/mckernel.img", "--ps"];
pub const REFERENCE_ARGV: &[&str] = &["/case/tools/mcinspect-reference", "--kernel=/images/mckernel.img", "--ps"];
pub const PAYLOAD_CWD: &str = "/case/work";
// Reuse the matched working native boot tuple. No original235 app is launched.
pub const BOOT_ARGV: &[&str] = &["/bin/native-boot", "hidos", "allow_oversubscribe"];

pub fn argv_json() -> String {
    // All values are these fixed ASCII source literals, with no runtime arguments. There is no caller-provided text or general JSON/argv parser.
    let mut json = String::from("[");
    for (index, argument) in PAYLOAD_ARGV.iter().enumerate() {
        if index != 0 {
            json.push(',');
        }
        json.push('"');
        json.push_str(argument);
        json.push('"');
    }
    json.push(']');
    json
}
