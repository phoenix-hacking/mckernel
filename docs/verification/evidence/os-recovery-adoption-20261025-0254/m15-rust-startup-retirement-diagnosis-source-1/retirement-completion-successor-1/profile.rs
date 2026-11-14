// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! One source-owned original startup profile. No runtime case/argv selection.
pub const PAYLOAD_ARGV: &[&str] = &["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"];
pub const PAYLOAD_CWD: &str = "/case/work";
// This is the original Cstartup #else invocation. F05's process-only hidos /
// allow_oversubscribe arguments are deliberately not selected for startup.
pub const BOOT_ARGV: &[&str] = &["/bin/native-boot"];

pub fn argv_json() -> String {
    // All values are these fixed ASCII source literals, including one empty
    // element. There is no caller-provided text or general JSON/argv parser.
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
