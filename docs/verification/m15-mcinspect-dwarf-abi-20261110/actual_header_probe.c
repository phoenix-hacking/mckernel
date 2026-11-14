#include <stddef.h>
#include <stdio.h>
#include "/home/holden/mckernel/executer/user/lib/libdwarf/libdwarf/libdwarf/libdwarf.h.in"

typedef int (*tag_contract)(unsigned int, const char **);
_Static_assert(__builtin_types_compatible_p(__typeof__(&dwarf_get_TAG_name), tag_contract), "actual TAG prototype must be unsigned");
typedef int (*loclist_contract)(Dwarf_Attribute, Dwarf_Locdesc ***, Dwarf_Signed *, Dwarf_Error *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&dwarf_loclist_n), loclist_contract), "actual loclist prototype differs");
typedef int (*cu_contract)(Dwarf_Debug, Dwarf_Bool, Dwarf_Unsigned *, Dwarf_Half *, Dwarf_Off *, Dwarf_Half *, Dwarf_Half *, Dwarf_Half *, Dwarf_Sig8 *, Dwarf_Unsigned *, Dwarf_Unsigned *, Dwarf_Error *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&dwarf_next_cu_header_c), cu_contract), "actual CU header prototype differs");
#define FACT(name, expression) printf("pub const " name ": usize = %zu;\n", (size_t)(expression))
int main(void) {
    FACT("C_SIG_SIZE", sizeof(Dwarf_Sig8));
    FACT("C_SIG_ALIGN", _Alignof(Dwarf_Sig8));
    FACT("C_SIG_SIGNATURE_OFFSET", offsetof(Dwarf_Sig8, signature));
    FACT("C_SIG_SIGNATURE_SIZE", sizeof(((Dwarf_Sig8 *)0)->signature));
    FACT("C_SIG_SIGNATURE_ALIGN", _Alignof(__typeof__(((Dwarf_Sig8 *)0)->signature)));
    FACT("C_LOC_SIZE", sizeof(Dwarf_Loc));
    FACT("C_LOC_ALIGN", _Alignof(Dwarf_Loc));
    FACT("C_LOC_LR_ATOM_OFFSET", offsetof(Dwarf_Loc, lr_atom));
    FACT("C_LOC_LR_ATOM_SIZE", sizeof(((Dwarf_Loc *)0)->lr_atom));
    FACT("C_LOC_LR_ATOM_ALIGN", _Alignof(__typeof__(((Dwarf_Loc *)0)->lr_atom)));
    FACT("C_LOC_LR_NUMBER_OFFSET", offsetof(Dwarf_Loc, lr_number));
    FACT("C_LOC_LR_NUMBER_SIZE", sizeof(((Dwarf_Loc *)0)->lr_number));
    FACT("C_LOC_LR_NUMBER_ALIGN", _Alignof(__typeof__(((Dwarf_Loc *)0)->lr_number)));
    FACT("C_LOC_LR_NUMBER2_OFFSET", offsetof(Dwarf_Loc, lr_number2));
    FACT("C_LOC_LR_NUMBER2_SIZE", sizeof(((Dwarf_Loc *)0)->lr_number2));
    FACT("C_LOC_LR_NUMBER2_ALIGN", _Alignof(__typeof__(((Dwarf_Loc *)0)->lr_number2)));
    FACT("C_LOC_LR_OFFSET_OFFSET", offsetof(Dwarf_Loc, lr_offset));
    FACT("C_LOC_LR_OFFSET_SIZE", sizeof(((Dwarf_Loc *)0)->lr_offset));
    FACT("C_LOC_LR_OFFSET_ALIGN", _Alignof(__typeof__(((Dwarf_Loc *)0)->lr_offset)));
    FACT("C_DESC_SIZE", sizeof(Dwarf_Locdesc));
    FACT("C_DESC_ALIGN", _Alignof(Dwarf_Locdesc));
    FACT("C_DESC_LD_LOPC_OFFSET", offsetof(Dwarf_Locdesc, ld_lopc));
    FACT("C_DESC_LD_LOPC_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_lopc));
    FACT("C_DESC_LD_LOPC_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_lopc)));
    FACT("C_DESC_LD_HIPC_OFFSET", offsetof(Dwarf_Locdesc, ld_hipc));
    FACT("C_DESC_LD_HIPC_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_hipc));
    FACT("C_DESC_LD_HIPC_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_hipc)));
    FACT("C_DESC_LD_CENTS_OFFSET", offsetof(Dwarf_Locdesc, ld_cents));
    FACT("C_DESC_LD_CENTS_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_cents));
    FACT("C_DESC_LD_CENTS_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_cents)));
    FACT("C_DESC_LD_S_OFFSET", offsetof(Dwarf_Locdesc, ld_s));
    FACT("C_DESC_LD_S_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_s));
    FACT("C_DESC_LD_S_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_s)));
    FACT("C_DESC_LD_FROM_LOCLIST_OFFSET", offsetof(Dwarf_Locdesc, ld_from_loclist));
    FACT("C_DESC_LD_FROM_LOCLIST_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_from_loclist));
    FACT("C_DESC_LD_FROM_LOCLIST_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_from_loclist)));
    FACT("C_DESC_LD_SECTION_OFFSET_OFFSET", offsetof(Dwarf_Locdesc, ld_section_offset));
    FACT("C_DESC_LD_SECTION_OFFSET_SIZE", sizeof(((Dwarf_Locdesc *)0)->ld_section_offset));
    FACT("C_DESC_LD_SECTION_OFFSET_ALIGN", _Alignof(__typeof__(((Dwarf_Locdesc *)0)->ld_section_offset)));
    FACT("C_UINT_SIZE", sizeof(unsigned int));
    FACT("C_UINT_ALIGN", _Alignof(unsigned int));
    return 0;
}
