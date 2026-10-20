/* Exact saved d67e leader results; no CPU/PID/token changes. */
memset(pair_results,0,sizeof pair_results);
{struct result *r=&pair_results[0];r->pid=257;r->status=0;r->clean=1;r->fault=0;r->timeout=0;r->started=32494963145ull;r->reaped=35114193242ull;r->finished=35114302474ull;
memcpy(r->out.data,pair_round_stdout_0,sizeof pair_round_stdout_0);
r->out.kept=387;r->out.observed=387;r->out.eof=1;r->out.eof_ns=34020762094ull;
r->err.kept=0;r->err.observed=0;r->err.eof=1;r->err.eof_ns=34020772989ull;
}
{struct result *r=&pair_results[1];r->pid=256;r->status=0;r->clean=1;r->fault=0;r->timeout=0;r->started=32494446878ull;r->reaped=34115742601ull;r->finished=34115896811ull;
memcpy(r->out.data,pair_round_stdout_1,sizeof pair_round_stdout_1);
r->out.kept=254;r->out.observed=254;r->out.eof=1;r->out.eof_ns=33617897205ull;
r->err.kept=0;r->err.observed=0;r->err.eof=1;r->err.eof_ns=33617821218ull;
}
