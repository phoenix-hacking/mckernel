/* BFD accessor shim for Rust-owned mcinspect. */

#include <bfd.h>

long mcinspect_bfd_get_symtab_upper_bound_bridge(bfd *abfd)
{
	return bfd_get_symtab_upper_bound(abfd);
}

long mcinspect_bfd_canonicalize_symtab_bridge(bfd *abfd, asymbol **location)
{
	return bfd_canonicalize_symtab(abfd, location);
}
