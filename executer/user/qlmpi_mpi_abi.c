#include "mpi.h"

int qlmpi_pmpi_init(int *argc, char ***argv)
{
	return PMPI_Init(argc, argv);
}

void qlmpi_pmpi_init_fortran(int *ierr)
{
	extern void pmpi_init_(int *ierr) __attribute__((__weak__));

	if (!pmpi_init_) {
		*ierr = MPI_ERR_OTHER;
		return;
	}

	pmpi_init_(ierr);
}

int qlmpi_mpi_comm_rank_world(int *rank)
{
	return MPI_Comm_rank(MPI_COMM_WORLD, rank);
}

int qlmpi_mpi_success_value(void)
{
	return MPI_SUCCESS;
}
