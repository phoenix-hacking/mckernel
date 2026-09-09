#include <iostream>
#include <stdexcept>

struct Guard { static int destroyed; ~Guard() { ++destroyed; } };
int Guard::destroyed = 0;
static void throw_typed() { Guard inner; throw std::runtime_error("fixture"); }
int main() {
    Guard outer; bool caught = false; std::string message;
    try { throw_typed(); } catch (const std::runtime_error &e) { caught = true; message = e.what(); }
    bool valid = caught && message == "fixture" && Guard::destroyed == 1;
    std::cout << "caught=" << caught << " message=" << message << " inner_destructor=" << Guard::destroyed << " valid=" << valid << '\n';
    return valid ? 0 : 1;
}
