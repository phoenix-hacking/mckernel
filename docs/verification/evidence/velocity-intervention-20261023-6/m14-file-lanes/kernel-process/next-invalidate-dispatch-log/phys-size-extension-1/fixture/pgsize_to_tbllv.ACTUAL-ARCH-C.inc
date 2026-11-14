int pgsize_to_tbllv(size_t pgsize)
{
	switch (pgsize) {
	case PTL1_SIZE:	return 1;
	case PTL2_SIZE:	return 2;
	case PTL3_SIZE:	return 3;
	case PTL4_SIZE:	return 4;
	default:
		return 0;
	}
}
