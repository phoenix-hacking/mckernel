void pte_make_fileoff(off_t off, enum ihk_mc_pt_attribute ptattr,
		      size_t pgsize, pte_t *ptep)
{
	uint64_t attr;

	attr = ptattr & ~PAGE_MASK;

	switch (pgsize) {
	case PTL1_SIZE:	attr |= PFL1_FILEOFF;			break;
	case PTL2_SIZE:	attr |= PFL2_FILEOFF | PFL2_SIZE;	break;
	case PTL3_SIZE:	attr |= PFL3_FILEOFF | PFL3_SIZE;	break;
	default:
		attr |= PTATTR_FILEOFF;
		break;
	}
	*ptep = (off & PAGE_MASK) | attr;
}
