/* Build-only exact modern BFD ABI witnesses; no runtime C implementation. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&bfd_set_section_size),
    bfd_boolean (*)(asection *, bfd_size_type)), "selected modern BFD size setter ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&bfd_set_section_flags),
    bfd_boolean (*)(asection *, flagword)), "selected modern BFD flags setter ABI");
