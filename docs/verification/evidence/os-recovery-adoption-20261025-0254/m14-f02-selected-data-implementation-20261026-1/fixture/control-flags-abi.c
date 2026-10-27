/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * PROPOSED HOST fixture; compile/link only after a separate root grant.
 * Include the genuine process.h under the actual selected kernel include/config profile.
 * Link to the candidate actual Rust process_global_storage provider, never C surrogates.
 */
#include <process.h>
#include <assert.h>
#include <limits.h>
#include <stdint.h>

_Static_assert(sizeof(int) == 4, "C int width");
_Static_assert(_Alignof(int) == 4, "C int alignment");

extern int f02_read_control(unsigned int slot);
extern void f02_write_control(unsigned int slot, int value);
extern void *f02_control_address(unsigned int slot);

int main(void)
{
    int *controls[] = { &idle_halt, &allow_oversubscribe, &time_sharing };
    const int defaults[] = { 0, 0, 1 };
    const int values[] = { INT_MIN, -1, 0, 1, INT_MAX };
    for (unsigned int i = 0; i < 3; ++i) {
        assert(*controls[i] == defaults[i]);
        assert(f02_read_control(i) == defaults[i]);
        assert((void *)controls[i] == f02_control_address(i));
        assert((uintptr_t)controls[i] % _Alignof(int) == 0);
        for (unsigned int j = 0; j < sizeof(values) / sizeof(values[0]); ++j) {
            *controls[i] = values[j];
            assert(f02_read_control(i) == values[j]);
            f02_write_control(i, values[sizeof(values) / sizeof(values[0]) - 1 - j]);
            assert(*controls[i] == values[sizeof(values) / sizeof(values[0]) - 1 - j]);
        }
        *controls[i] = defaults[i];
    }
    return 0;
}
