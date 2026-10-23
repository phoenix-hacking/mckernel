from pathlib import Path
import hashlib,json
base=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/capacity-binding-1/producer-implementation-1')
d=base/'real-consumer-1'
seed=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/candidate')
rows=[]
for name in ('pair_collector.c','pair_collector.inc','pair_runtime.inc','pair_launch_expansion_support.inc','pair_launch_expansion_run.inc','pair_trace_retention.inc','pair_assignment.h','pair_round_oracles.h'):
 b=(seed/name).read_bytes(); (d/name).write_bytes(b);rows.append({'path':str(seed/name),'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)})
for name in ('pair_long_producer.h','abi_witness.c','tests.rs'):(d/name).write_bytes((base/name).read_bytes())
s=(base/'pair_long_producer.rs').read_text()
s=s.replace('if (ops.empty)(ctx, round, absolute) != 1 { return Err(Failure::State); }','if (ops.empty)(ctx, round, absolute) != 1 { summary.ownership_complete = 0; return Err(Failure::State); }')
s=s.replace('        serial(ctx, ops, &buffer[..want])?;','        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }\n        serial(ctx, ops, &buffer[..want])?;\n        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }')
s=s.replace('    line!(ctx, ops, "ND_PAIR_LONG_TRACE_END', '    if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }\n    line!(ctx, ops, "ND_PAIR_LONG_TRACE_END')
s=s.replace('    line!(ctx, ops, "ND_PAIR_LONG_COMPLETE', '    if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }\n    line!(ctx, ops, "ND_PAIR_LONG_COMPLETE')
s=s.replace('    summary.completed = 1;', '    if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }\n    summary.completed = 1;')
s=s.replace('//! Production binding must supply', '//! real-consumer-1/long_bridge.inc supplies')
(d/'pair_long_producer.rs').write_text(s)
# Keep fixed TEN source byte-identical: LONG uses separately derived support/retention.
s=(d/'pair_launch_expansion_support.inc').read_text().replace('pair_seen_pids[20]','pair_seen_pids[4096]').replace('pair_seen_tokens[240]','pair_seen_tokens[49152]').replace('pair_seen_pid_count>=20','pair_seen_pid_count>=4096').replace('pair_seen_token_count==240','pair_seen_token_count==49152')
s=s.replace('deleted=0,releases=0,last_errno=-1,terminal=0','deleted=0,releases=0,acks=0,last_errno=-1,terminal=0')
s=s.replace('!terminal || !token || last_errno==0','!terminal || acks!=1 || !token || last_errno==0')
a=s.index('        } else if((mark=strstr(line,"application_process=release "))) {')
b=s.index('        } else if((mark=strstr(line,"application procfs "))) {',a)
s=s[:a]+'''        } else if((mark=strstr(line,"application_process=cleanup_requested "))) {
            int error=0;
            if(sscanf(mark,"application_process=cleanup_requested os=%u generation=%lu pid=%d intent_errno=%d%n",&osid,&generation,&found,&error,&used)!=4)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || error || ++releases!=1))return -1;
        } else if((mark=strstr(line,"application cleanup ACK "))) {
            unsigned long long token=0;int error=0,abandoned=-1;
            if(sscanf(mark,"application cleanup ACK os=%u generation=%lu pid=%d token=%llu errno=%d abandoned=%d%n",&osid,&generation,&found,&token,&error,&abandoned,&used)!=6)return -1;
            if(found==pid && (osid || generation!=1 || mark[used] || !token || error || (abandoned!=0 && abandoned!=1) || ++acks!=1))return -1;
''' +s[b:]
s=s.replace('last_errno || releases!=1','last_errno || releases!=1 || acks!=1')
s=s.replace('#include "pair_trace_retention.inc"','#include "long_trace_retention.inc"')
s=s.replace('int n=klogctl(3,log,sizeof log-1);','int n=long_kernel_snapshot(log,sizeof log-1);')
(d/'long_support.inc').write_text(s)
# LONG file-backed aggregate spool plus authenticated history; one fd, bounded records.
s=(d/'pair_trace_retention.inc').read_text()
s=s.replace('(2u*1024u*1024u)','(256u*1024u*1024u)').replace('pair_trace_records[10]','pair_trace_records[2048]').replace('round<10','round<2048').replace('pair_active_round>=10','pair_active_round>=2048')
s=s.replace('struct stat identity; };','struct stat identity; char path[PATH_MAX]; };')
s=s.replace('strstr(line,"application_process=release ")','strstr(line,"application_process=cleanup_requested ") || strstr(line,"application cleanup ACK ")')
pos=s.index('static int pair_trace_member(')
s=s[:pos]+'''/* Reopen exactly one immutable per-round source at a time; no 2048-fd leak. */
static int long_trace_stat(struct pair_trace_record *r,struct stat *out)
{
    int fd=open(r->path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
    if(fd<0)return -1;
    int bad=fstat(fd,out);if(close(fd))bad=1;return bad?-1:0;
}
'''+s[pos:]
s=s.replace('r->fd<0 || !r->bytes || fstat(r->fd,&current)','!r->bytes || long_trace_stat(r,&current)')
s=s.replace('r->fd<0 || !r->bytes || r->offset!=0','!r->bytes || r->offset!=0').replace('fstat(r->fd,&current)','long_trace_stat(r,&current)')
needle='    r->pids[0]=pair_results[0].pid;'
s=s.replace(needle,'    if(strlen(path)>=sizeof r->path || close(r->fd))return -1;\n    strcpy(r->path,path);r->fd=-1;\n'+needle)
# Only the LONG gate/save/route reuse are needed. Preserve old exporter source separately.
a=s.index('static int pair_trace_publish(');b=s.index('/* Startup route proof',a)
s=s[:a]+s[b:]
(d/'long_trace_retention.inc').write_text(s)
s=(d/'pair_collector.c').read_text()
s=s.replace('#define COLLECTOR_SECONDS 120u','#if defined(ND_PAIR_LONG)\n#define COLLECTOR_SECONDS 7320u\n#else\n#define COLLECTOR_SECONDS 120u\n#endif')
s=s.replace('#include "pair_launch_expansion_support.inc"','#if defined(ND_PAIR_LONG)\n#include "long_provider_decl.inc"\n#include "long_support.inc"\n#else\n#include "pair_launch_expansion_support.inc"\n#endif')
s=s.replace('\nint main(void)','\n#if defined(ND_PAIR_LONG)\n#include "long_bridge.inc"\n#endif\n\nint main(void)')
s=s.replace('    if(pair_run_launch_expansion(console,&safe,&empty))good=0;','    #if defined(ND_PAIR_LONG)\n    if(long_dispatch(console,&safe,&empty))good=0;\n    #else\n    if(pair_run_launch_expansion(console,&safe,&empty))good=0;\n    #endif')
# Existing main final native success exporter must use LONG spool, not TEN exporter.
s=s.replace('pair_trace_publish(console,log,(size_t)n)','long_trace_publish_unused(console,log,(size_t)n)') if False else s
(d/'pair_collector.c').write_text(s)
(d/'RETAINED-SEED-INPUTS.json').write_text(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','inputs':rows,'fixed_ten_files_preserved_except_collector_conditional_hook':True},indent=2)+'\n')
