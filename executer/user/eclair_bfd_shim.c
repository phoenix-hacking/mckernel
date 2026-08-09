/* BFD accessor shim for Rust-owned eclair. */

#include <bfd.h>

long eclair_bfd_get_symtab_upper_bound_bridge(bfd *abfd)
{
	return bfd_get_symtab_upper_bound(abfd);
}

long eclair_bfd_canonicalize_symtab_bridge(bfd *abfd, asymbol **location)
{
	return bfd_canonicalize_symtab(abfd, location);
}
