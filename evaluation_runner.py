"""REPAIR-X auditable evaluation runner v2.

Local controlled-fixture evaluation ONLY. Model-generated code execution is not sandboxed.
"""
import argparse
import csv
import json
import os
import random
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from benchmark.cases import CASES
from live_recovery import run_case
from llm_providers.factory import create_provider
from llm_providers.generate import generate_text

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'evaluation_trials.jsonl'
TRANSIENT = ('APIConnectionError', 'APITimeoutError', 'RateLimitError',
             'ConnectError', 'ReadTimeout', 'ConnectTimeout', 'TimeoutError',
             'ConnectionError', 'ServiceUnavailableError', 'InternalServerError')


def plan(providers, repeats, cases=CASES):
    if not 1 <= repeats <= 1000:
        raise ValueError('repeats must be 1..1000')
    return [(p, c) for _ in range(repeats) for p in providers for c in cases]


def classify(record):
    if record.get('outcome') == 'ACCEPTED':
        return 'ACCEPTED'
    if record.get('outcome') == 'ERROR':
        return 'INFRASTRUCTURE_ERROR'
    attempts = record.get('attempts') or []
    if attempts and all(a.get('patch') is None and a.get('error') for a in attempts):
        if all(any(t in a['error'] for t in TRANSIENT) for a in attempts):
            return 'INFRASTRUCTURE_ERROR'
    return 'ABSTAINED'


def summarize(records):
    result = {'total_trials': len(records), 'distinct_faults': len({r.get('case_id') for r in records}),
              'outcomes': dict(Counter(classify(r) for r in records)), 'providers': {}}
    for provider in sorted({r.get('provider') for r in records}):
        subset = [r for r in records if r.get('provider') == provider]
        counts = Counter(classify(r) for r in subset)
        valid = counts['ACCEPTED'] + counts['ABSTAINED']
        latency = [float(r['elapsed_seconds']) for r in subset if classify(r) != 'INFRASTRUCTURE_ERROR'
                   and isinstance(r.get('elapsed_seconds'), (int, float))]
        result['providers'][provider] = {
            'trials': len(subset), 'accepted': counts['ACCEPTED'], 'abstained': counts['ABSTAINED'],
            'infrastructure_errors': counts['INFRASTRUCTURE_ERROR'],
            'repair_success_rate_evaluable': round(counts['ACCEPTED']/valid, 4) if valid else None,
            'repair_success_rate_all_scheduled': round(counts['ACCEPTED']/len(subset), 4),
            'mean_latency_s_evaluable': round(statistics.mean(latency), 3) if latency else None,
            'mean_latency_s': round(statistics.mean(latency), 3) if latency else None,
            'median_latency_s_evaluable': round(statistics.median(latency), 3) if latency else None,
            'mean_repair_attempts': round(statistics.mean(len(r.get('attempts', [])) for r in subset), 3),
        }
    return result


def append_jsonl(path, record):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def read_batch(path, batch_id):
    records = []
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue  # interrupted final write; preserve file for manual inspection
            if item.get('evaluation_batch_id') == batch_id:
                records.append(item)
    return records


def is_transient(exc):
    return any(cls.__name__ in TRANSIENT for cls in type(exc).__mro__)


def network_resilient_generator(retries, base_delay):
    def call(client, model, prompt):
        for attempt in range(retries + 1):
            try:
                return generate_text(client, model, prompt)
            except Exception as exc:
                if not is_transient(exc) or attempt == retries:
                    raise
                wait = min(30.0, base_delay * (2 ** attempt)) + random.uniform(0, 0.25)
                print(f'  transient API failure: {type(exc).__name__}; retrying in {wait:.1f}s', flush=True)
                time.sleep(wait)
    return call


def write_report(report_path, summary, batch_id, args, records):
    lines = [
        '# REPAIR-X — Experimental Evaluation Report', '',
        f'Batch ID: `{batch_id}`  ',
        f'Generated (UTC): {datetime.now(timezone.utc).isoformat()}  ',
        f'Protocol: risk-aware recovery v2  ',
        f'Max repair attempts: {args.max_attempts}  ',
        f'Network retries per model request: {args.network_retries}  ',
        '', '## Methodology', '',
        f'- Distinct fault definitions in this batch: **{summary["distinct_faults"]}**.',
        f'- Recorded repair trials: **{summary["total_trials"]}**.',
        '- Trials are repeated runs over a small hand-designed Python fault dataset; repeated trials are **not** unique fault cases.',
        '- Model-generated candidate patches are assessed using a heuristic risk policy and visible/hidden assertions.',
        '- Hidden assertions influence acceptance decisions and are therefore not an independent held-out final test.',
        '- Infrastructure errors are reported separately from genuine repair abstentions.',
        '', '## Results', '',
        '| Provider | Trials | Accepted | Abstained | API/infra errors | Success / evaluable | Mean latency (s) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for p, v in summary['providers'].items():
        success = ('N/A' if v['repair_success_rate_evaluable'] is None else f'{v["repair_success_rate_evaluable"]*100:.1f}%')
        latency = 'N/A' if v['mean_latency_s_evaluable'] is None else f'{v["mean_latency_s_evaluable"]:.3f}'
        lines.append(f'| {p} | {v["trials"]} | {v["accepted"]} | {v["abstained"]} | {v["infrastructure_errors"]} | {success} | {latency} |')
    lines.extend(['', '## Interpretation and limitations', '',
                  '- The observed rates describe these particular trials, not general autonomous repair capability.',
                  '- Provider/model versions, network conditions, sampling variability and rate limits can affect outcomes.',
                  '- Subprocess execution is **not a security sandbox**. Do not expose live execution on public hosting.',
                  '- This report contains observed outcomes only; no unexecuted trials are counted.',
                  '', '## Reproducibility', '',
                  f'- Batch ID: `{batch_id}`',
                  f'- Providers: {", ".join(args.providers)}',
                  f'- Requested repetitions: {args.repeats}',
                  f'- Limit: {args.limit}',
                  f'- Output JSONL: `{args.output.name}`',
                  f'- Trial indices recorded: {len(records)}', ''])
    report_path.write_text('\n'.join(lines), encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Local-only controlled benchmark; API calls may incur charges.')
    ap.add_argument('--providers', nargs='+', choices=['groq', 'gemini', 'openai'], default=['groq'])
    ap.add_argument('--repeats', type=int, default=1)
    ap.add_argument('--max-attempts', type=int, choices=[1, 2, 3], default=3)
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--delay', type=float, default=0.0)
    ap.add_argument('--network-retries', type=int, default=2)
    ap.add_argument('--retry-base-delay', type=float, default=1.5)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--output', type=Path, default=OUT)
    ap.add_argument('--batch-id', default=None, help='Use same ID to resume an interrupted batch')
    ap.add_argument('--resume', action='store_true', help='Skip trial indices already recorded for --batch-id')
    args = ap.parse_args(argv)
    if args.delay < 0 or args.retry_base_delay < 0 or not 0 <= args.network_retries <= 5 or (args.limit is not None and args.limit < 1):
        ap.error('invalid delay/retries/limit')
    if args.resume and not args.batch_id:
        ap.error('--resume requires --batch-id')
    planned = plan(args.providers, args.repeats)
    if args.limit is not None:
        planned = planned[:args.limit]
    print(f'Unique fault definitions: {len({c["id"] for _, c in planned})} | Planned repair trials: {len(planned)} | Max attempts per trial: {args.max_attempts}')
    if args.dry_run:
        return
    if os.getenv('REPAIRX_ALLOW_LOCAL_EXECUTION') != '1':
        ap.error('Set REPAIRX_ALLOW_LOCAL_EXECUTION=1 only in a trusted isolated local environment.')
    batch_id = args.batch_id or uuid4().hex
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = args.output.parent / f'evaluation_manifest_{batch_id}.json'
    spec = {'providers': args.providers, 'repeats': args.repeats, 'limit': args.limit,
            'max_attempts': args.max_attempts, 'case_ids': [c['id'] for _, c in planned],
            'planned_providers': [p for p, _ in planned]}
    if manifest.exists():
        old = json.loads(manifest.read_text(encoding='utf-8'))
        if old != spec:
            ap.error('Existing batch ID has a different plan. Resume with exactly the original options.')
    else:
        if args.resume:
            ap.error('Cannot resume: matching batch manifest not found')
        manifest.write_text(json.dumps(spec, indent=2), encoding='utf-8')
    previous = read_batch(args.output, batch_id)
    if previous and not args.resume:
        ap.error('Batch ID already has results; use --resume to avoid duplicate trials')
    completed = {int(r['trial_index']) for r in previous if 'trial_index' in r}
    records = list(previous)
    clients = {}
    generator = network_resilient_generator(args.network_retries, args.retry_base_delay)
    for index, (provider, case) in enumerate(planned, 1):
        if index in completed:
            print(f'{index}/{len(planned)} SKIP (already recorded)', flush=True)
            continue
        started = time.perf_counter()
        try:
            if provider not in clients:
                clients[provider] = create_provider(provider)
            client, model = clients[provider]
            record = run_case(client, model, provider, case, max_attempts=args.max_attempts, generator=generator)
        except Exception as exc:
            record = {'run_id': uuid4().hex, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                      'provider': provider, 'case_id': case['id'], 'outcome': 'ERROR',
                      'attempts': [], 'error': f'{type(exc).__name__}: {str(exc)[:250]}',
                      'elapsed_seconds': round(time.perf_counter() - started, 3)}
        record.update({'evaluation_batch_id': batch_id, 'trial_index': index,
                       'evaluation_protocol': 'risk_aware_recovery_v2', 'unique_faults_in_dataset': len(CASES)})
        record['evaluation_status'] = classify(record)
        append_jsonl(args.output, record)
        records.append(record)
        print(f'{index}/{len(planned)} {provider} {case["id"]}: {record["evaluation_status"]}', flush=True)
        if args.delay and index < len(planned):
            time.sleep(args.delay)
    records.sort(key=lambda r: r['trial_index'])
    summary = summarize(records)
    stem = f'evaluation_summary_{batch_id[:8]}'
    report = args.output.parent / f'{stem}.json'
    report.write_text(json.dumps({'batch_id': batch_id, 'created_utc': datetime.now(timezone.utc).isoformat(),
                                  'protocol': 'risk_aware_recovery_v2', 'summary': summary}, indent=2), encoding='utf-8')
    write_report(args.output.parent / f'{stem}.md', summary, batch_id, args, records)
    with (args.output.parent / f'{stem}.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['trial_index','provider','model','case_id','evaluation_status','outcome','elapsed_seconds','attempt_count','formatting_retries'])
        writer.writeheader()
        for r in records:
            writer.writerow({'trial_index':r.get('trial_index'),'provider':r.get('provider'),'model':r.get('model'),
                             'case_id':r.get('case_id'),'evaluation_status':classify(r),'outcome':r.get('outcome'),
                             'elapsed_seconds':r.get('elapsed_seconds'),'attempt_count':len(r.get('attempts',[])),
                             'formatting_retries':sum(a.get('formatting_retries',0) for a in r.get('attempts',[]))})
    print('Batch ID:', batch_id)
    print('Summary:', report)
    print('Report:', args.output.parent / f'{stem}.md')
    print('CSV:', args.output.parent / f'{stem}.csv')


if __name__ == '__main__':
    main()
