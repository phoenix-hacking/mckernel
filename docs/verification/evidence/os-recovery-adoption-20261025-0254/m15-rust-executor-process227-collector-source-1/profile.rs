// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! One source-owned original process-exec-wait235 profile. No runtime case/argv selection.
pub const PAYLOAD_ARGV: &[&str] = &["/bin/mcexec", "-t", "1", "0", "/apps/app"];
pub const PAYLOAD_CWD: &str = "/case/work";
// Exact original process235 boot profile. This differs from the completed
// startup case; the original strict contract explicitly selects oversubscription.
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
