"""Read-only REPAIR-X pilot benchmark dashboard.

Run: streamlit run benchmark_dashboard.py
Only compares explicitly selected run IDs. Historical runs may use different
fixtures or retry policies; do not combine them without verifying comparability.
"""
import json
from pathlib import Path
from statistics import mean, median

import streamlit as st

HISTORY = Path(__file__).resolve().parent / 'benchmark_results.jsonl'


def load_records(path=HISTORY):
    if not Path(path).exists():
        return [], []
    records, errors = [], []
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict) or not obj.get('run_id') or not obj.get('case_id'):
                raise ValueError('missing run_id or case_id')
            records.append(obj)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f'Line {number}: {exc}')
    return records, errors


def group_runs(records):
    groups = {}
    for record in records:
        groups.setdefault(record['run_id'], []).append(record)
    return groups


def summarize(records):
    if not records:
        return {}
    durations = [float(r['elapsed_seconds']) for r in records if isinstance(r.get('elapsed_seconds'), (int, float))]
    return {
        'cases': len(records),
        'visible': sum(r.get('visible_pass') is True for r in records),
        'hidden': sum(r.get('visible_pass') is True and r.get('hidden_pass') is True for r in records),
        'format_retries': sum(int(r.get('formatting_retries') or 0) for r in records),
        'retry_cases': sum(int(r.get('formatting_retries') or 0) > 0 for r in records),
        'mean_s': mean(durations) if durations else None,
        'median_s': median(durations) if durations else None,
    }


def main():
    st.set_page_config(page_title='REPAIR-X | Benchmark', layout='wide')
    st.title('REPAIR-X · Research Benchmark')
    st.caption('AI-only candidate validation. Hidden-test pass ≠ proven semantic correctness.')
    records, errors = load_records()
    if errors:
        st.warning(f'{len(errors)} malformed history line(s) skipped.')
        with st.expander('Read errors'):
            st.code('\n'.join(errors))
    if not records:
        st.info('No benchmark history found. Run python benchmark_runner.py --provider groq first.')
        return
    runs = group_runs(records)
    rows = []
    for run_id, group in runs.items():
        first = group[0]
        rows.append({'run_id': run_id, 'provider': first.get('provider','?'),
                     'model': first.get('model','?'), 'timestamp': first.get('timestamp_utc',''),
                     'cases': len(group), 'case_set': frozenset(r['case_id'] for r in group)})
    rows.sort(key=lambda r: r['timestamp'], reverse=True)
    st.warning('Earlier pilot runs included a broken hidden test and/or different retry policies. Select only comparable runs. The dashboard does not infer benchmark version from old records.')
    chosen = []
    for provider in sorted(set(r['provider'] for r in rows)):
        options = [r for r in rows if r['provider'] == provider]
        default = next((r for r in options if r['cases'] == 10), options[0])
        choice = st.selectbox(f'{provider.upper()} run', [None] + [r['run_id'] for r in options],
                              index=1 + options.index(default),
                              format_func=lambda rid: 'Exclude' if rid is None else next(
                                  f"{r['timestamp'][:19]} · {r['cases']} cases · {rid[:8]}" for r in options if r['run_id'] == rid))
        if choice:
            chosen.append(choice)
    if not chosen:
        st.info('Select at least one run.')
        return
    sets = [frozenset(r['case_id'] for r in runs[rid]) for rid in chosen]
    if len(set(sets)) > 1:
        st.error('Selected runs have different case sets. Do not compare their pass rates directly.')
    if any(len(runs[rid]) != len(sets[i]) for i, rid in enumerate(chosen)):
        st.error('At least one selected run contains duplicate case IDs. Review before comparing.')
    comparison = []
    for rid in chosen:
        group = runs[rid]
        s = summarize(group)
        comparison.append({'Provider': group[0].get('provider','?'), 'Model': group[0].get('model','?'),
                           'Run ID': rid[:12], 'Cases': s['cases'],
                           'Visible pass %': round(100*s['visible']/s['cases'], 1),
                           'Both test groups %': round(100*s['hidden']/s['cases'], 1),
                           'Formatting retry cases': s['retry_cases'],
                           'Total formatting retries': s['format_retries'],
                           'Mean latency (s)': round(s['mean_s'],3) if s['mean_s'] is not None else None,
                           'Median latency (s)': round(s['median_s'],3) if s['median_s'] is not None else None})
    st.subheader('Run comparison')
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    import pandas as pd
    frame = pd.DataFrame(comparison).set_index('Provider')
    left, right = st.columns(2)
    with left:
        st.caption('Visible and additional withheld-test pass rates (%)')
        st.bar_chart(frame[['Visible pass %', 'Both test groups %']])
    with right:
        st.caption('Mean and median elapsed time (seconds)')
        st.bar_chart(frame[['Mean latency (s)', 'Median latency (s)']])
    st.subheader('Case-level records')
    detail = []
    for rid in chosen:
        for rec in runs[rid]:
            detail.append({'provider': rec.get('provider'), 'case': rec.get('case_id'),
                           'visible': rec.get('visible_pass'), 'hidden': rec.get('hidden_pass'),
                           'formatting_retries': rec.get('formatting_retries', 0),
                           'elapsed_s': rec.get('elapsed_seconds'), 'error': rec.get('error'),
                           'run_id': rid})
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button('Export selected records (JSON)', json.dumps(
        [rec for rid in chosen for rec in runs[rid]], indent=2),
        file_name='repairx_selected_benchmark.json', mime='application/json')
    st.caption('Limitations: one run per model does not establish statistical significance; elapsed time includes network/API effects; no token or cost tracking yet. Do not execute model-generated code outside an isolated environment.')


if __name__ == '__main__':
    main()
