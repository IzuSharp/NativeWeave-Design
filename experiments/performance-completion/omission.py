"""Finite workload accounting counterexample, not a real server benchmark."""
import json, math
arrival=[i for i in range(100)]
service=[100]+[1]*99
finish=[];clock=0
for scheduled,duration in zip(arrival,service):
    clock=max(clock,scheduled)+duration;finish.append(clock)
latency=[end-start for end,start in zip(finish,arrival)]
percentile=lambda values,p:sorted(values)[max(0,math.ceil(len(values)*p)-1)]
assert percentile(service,.99)==1
assert percentile(latency,.99)==100
# HdrHistogram source's expected-interval fill rule, inspected at a fixed commit.
corrected=[]
for duration in service:
    corrected.append(duration)
    missing=duration-1
    while missing>=1:corrected.append(missing);missing-=1
assert len(corrected)==199 and percentile(corrected,.99)==99
print(json.dumps({'kind':'finite_deterministic_accounting_model','unit':'synthetic_ms','requests':100,
 'service_only_p99':percentile(service,.99),'scheduled_arrival_to_completion_p99':percentile(latency,.99),
 'expected_interval_corrected_p99':percentile(corrected,.99),'corrected_observations':len(corrected),
 'checks':3,'claim':'Service time hides queue delay; corrected sampling is not identical to actual scheduled-arrival latency.',
 'limitations':['No real load, CPU, network, RSS or application performance measured.','Single worker, fixed arrivals and finite service times only.']}))
