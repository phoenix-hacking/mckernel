int pte_is_fileoff(pte_t *ptep, size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return !!(*ptep & PFL1_FILEOFF);
	case PTL2_SIZE:	return !!(*ptep & PFL2_FILEOFF);
	case PTL3_SIZE:	return !!(*ptep & PFL3_FILEOFF);
	default:
		return !!(*ptep & PTATTR_FILEOFF);
	}
}
