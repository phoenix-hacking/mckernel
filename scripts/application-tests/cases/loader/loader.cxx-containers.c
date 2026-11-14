#include <iostream>
#include <numeric>
#include <string>
#include <vector>

struct Counted { static int destroyed; int value; explicit Counted(int v) : value(v) {} ~Counted() { ++destroyed; } };
int Counted::destroyed = 0;
int main() {
    std::vector<Counted> values; values.emplace_back(2); values.emplace_back(4); values.emplace_back(6);
    std::string text = "mckernel"; int sum = 0; for (const auto &v : values) sum += v.value;
    bool valid = sum == 12 && text == "mckernel" && values.size() == 3;
    values.clear(); bool destruction = Counted::destroyed >= 3;
    std::cout << "elements=2,4,6 sum=" << sum << " text=" << text << " destructors=" << Counted::destroyed << " valid=" << (valid && destruction) << '\n';
    return (valid && destruction) ? 0 : 1;
}
