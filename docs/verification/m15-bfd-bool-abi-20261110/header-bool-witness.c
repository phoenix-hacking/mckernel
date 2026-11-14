/* Source-derived C11 type witness only; never linked or executed. */
#include <stdbool.h>
#include <bfd.h>

typedef bool (*m15_check_format_signature)(bfd *, bfd_format);
typedef bool (*m15_section_contents_signature)(bfd *, asection *, void *, file_ptr, bfd_size_type);
_Static_assert(_Generic(&bfd_check_format, m15_check_format_signature: 1, default: 0),
               "selected bfd_check_format must return C bool");
_Static_assert(_Generic(&bfd_get_section_contents, m15_section_contents_signature: 1, default: 0),
               "selected bfd_get_section_contents must return C bool");
_Static_assert(sizeof(bool) == 1, "selected C bool byte width");
_Static_assert(_Alignof(bool) == 1, "selected C bool byte alignment");
