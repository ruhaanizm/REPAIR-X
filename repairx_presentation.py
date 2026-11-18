"""REPAIR-X presentation dashboard (read-only; no generated code execution).
Run: streamlit run repairx_presentation.py
"""
import json
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent
BENCHMARK_PATH = ROOT / 'benchmark_results.jsonl'
LIVE_PATH = ROOT / 'live_recovery_results.jsonl'
DEMO_PATH = ROOT / 'recovery_demo_report.json'


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return [], []
    records, warnings = [], []
    for line_no, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError('record must be a JSON object')
            records.append(item)
        except (ValueError, json.JSONDecodeError) as exc:
            warnings.append(f'Line {line_no}: {exc}')
    return records, warnings


def group_runs(records):
    groups = {}
    for record in records:
        if record.get('run_id') and record.get('case_id'):
            groups.setdefault(record['run_id'], []).append(record)
    return groups


def summarize_benchmark(records):
    if not records:
        return {}
    times = [float(r['elapsed_seconds']) for r in records
             if isinstance(r.get('elapsed_seconds'), (int, float))]
    return {
        'cases': len(records),
        'visible': sum(r.get('visible_pass') is True for r in records),
        'both': sum(r.get('visible_pass') is True and r.get('hidden_pass') is True for r in records),
        'retry_cases': sum(int(r.get('formatting_retries') or 0) > 0 for r in records),
        'mean_s': mean(times) if times else None,
        'median_s': median(times) if times else None,
    }


def summarize_live(records):
    return {
        'runs': len(records),
        'accepted': sum(r.get('outcome') == 'ACCEPTED' for r in records),
        'abstained': sum(r.get('outcome') == 'ABSTAINED' for r in records),
        'attempts': sum(len(r.get('attempts', [])) for r in records),
    }


def main():
    import streamlit as st
    import pandas as pd
    from benchmark.cases import CASES

    st.set_page_config(page_title='REPAIR-X | Command Center', page_icon='🛠️', layout='wide')
    st.title('REPAIR-X')
    st.caption('Risk-Aware Adaptive AI System for Software Fault Diagnosis, Repair & Recovery')
    st.info('Controlled Python prototype. Candidate code is evaluated in temporary subprocesses, NOT a security sandbox. '
            'Passing additional withheld checks does not prove semantic correctness.')

    benchmark, bench_warnings = load_jsonl(BENCHMARK_PATH)
    live, live_warnings = load_jsonl(LIVE_PATH)
    for name, warnings in [('Benchmark', bench_warnings), ('Live recovery', live_warnings)]:
        if warnings:
            st.warning(f'{name}: {len(warnings)} malformed history lines skipped.')

    tab1, tab2, tab3, tab4 = st.tabs(['Live AI recovery', 'Model comparison', 'Recovery policy', 'Architecture & demo'])
    case_lookup = {case['id']: case for case in CASES}

    with tab1:
        st.subheader('Live risk-aware recovery history')
        if not live:
            st.warning('No live recovery records found. Run: python live_recovery.py --provider groq --case divide_zero')
        else:
            summary = summarize_live(live)
            cols = st.columns(4)
            for col, (name, value) in zip(cols, [('Runs', summary['runs']), ('Accepted', summary['accepted']),
                                                 ('Abstained', summary['abstained']), ('Total attempts', summary['attempts'])]):
                col.metric(name, value)
            choices = sorted(live, key=lambda r: r.get('timestamp_utc', ''), reverse=True)
            selected = st.selectbox('Inspect recorded repair', range(len(choices)),
                format_func=lambda i: f"{choices[i].get('provider','?')} · {choices[i].get('case_id','?')} · "
                                      f"{choices[i].get('outcome','?')} · {choices[i].get('run_id','')[:8]}")
            record = choices[selected]
            case = case_lookup.get(record.get('case_id'))
            left, right = st.columns(2)
            with left:
                st.markdown('**Original faulty function**')
                st.code(case['source'] if case else '# Original source unavailable', language='python')
                if case:
                    st.markdown('**Expected behavior**')
                    st.write(case['spec'])
            with right:
                st.markdown('**Recovery outcome**')
                if record.get('outcome') == 'ACCEPTED':
                    st.success('ACCEPTED — candidate passed policy and both test groups')
                else:
                    st.error('ABSTAINED — no candidate accepted')
                st.write('Provider:', record.get('provider'), ' | Model:', record.get('model'))
                st.write('Time:', record.get('elapsed_seconds'), 's | Original unchanged:', record.get('original_unchanged'))
            for attempt in record.get('attempts', []):
                risk = attempt.get('risk') or {}
                with st.expander(f"Attempt {attempt.get('attempt')} · {attempt.get('decision','REJECT')} · "
                                 f"Risk {risk.get('level','UNKNOWN')} ({risk.get('score','?')})", expanded=True):
                    st.code(attempt.get('patch') or '# No patch', language='python')
                    st.write('Visible checks:', attempt.get('visible_pass'), ' | Additional withheld checks:',
                             attempt.get('hidden_pass'), ' | Formatting retries:', attempt.get('formatting_retries', 0))
                    st.write('Risk reasons:', ', '.join(risk.get('reasons', [])) or 'None flagged')
                    if attempt.get('error'):
                        st.caption('Failure: ' + str(attempt['error'])[:400])
            st.download_button('Export selected live report', json.dumps(record, indent=2),
                               file_name='repairx_live_report.json', mime='application/json')

    with tab2:
        st.subheader('Three-model benchmark')
        st.warning('Old runs include a broken test fixture or different retry policies. Select only matched, corrected runs. '
                   'The historical records do not contain a reliable benchmark version.')
        runs = group_runs(benchmark)
        if not runs:
            st.info('No benchmark history found. Run python benchmark_runner.py --provider groq')
        else:
            chosen = []
            providers = sorted({group[0].get('provider','unknown') for group in runs.values()})
            for provider in providers:
                options = [(rid, group) for rid, group in runs.items() if group[0].get('provider') == provider]
                options.sort(key=lambda pair: pair[1][0].get('timestamp_utc',''), reverse=True)
                # Default to latest 10-case run; user must verify comparability.
                preferred = next((i for i, (_, g) in enumerate(options) if len(g) == 10), 0)
                labels = ['Exclude'] + [f"{g[0].get('timestamp_utc','')[:19]} · {len(g)} cases · {rid[:8]}" for rid,g in options]
                choice = st.selectbox(f'{provider.upper()} run', range(len(labels)), index=preferred+1,
                                      format_func=lambda i: labels[i])
                if choice:
                    chosen.append((provider, *options[choice-1]))
            if chosen:
                sets = [frozenset(r['case_id'] for r in group) for _, _, group in chosen]
                comparable = len(set(sets)) == 1 and all(len(group) == len(case_set)
                                      for (_, _, group), case_set in zip(chosen, sets))
                if not comparable:
                    st.error('Different case sets or duplicate cases detected: do not compare these runs directly.')
                rows, detail = [], []
                for provider, rid, group in chosen:
                    summary = summarize_benchmark(group)
                    rows.append({'Provider': provider, 'Model': group[0].get('model',''), 'Cases': summary['cases'],
                                 'Visible pass %': round(100*summary['visible']/summary['cases'],1),
                                 'Both groups pass %': round(100*summary['both']/summary['cases'],1),
                                 'Formatting retry cases': summary['retry_cases'],
                                 'Mean latency (s)': round(summary['mean_s'],3) if summary['mean_s'] is not None else None,
                                 'Median latency (s)': round(summary['median_s'],3) if summary['median_s'] is not None else None})
                    for r in group:
                        detail.append({'Provider': provider, 'Case': r['case_id'], 'Visible': r.get('visible_pass'),
                                       'Withheld': r.get('hidden_pass'), 'Retries': r.get('formatting_retries',0),
                                       'Latency (s)': r.get('elapsed_seconds'), 'Error': r.get('error')})
                st.dataframe(rows, use_container_width=True, hide_index=True)
                if comparable:
                    frame = pd.DataFrame(rows).set_index('Provider')
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption('Test pass rate (%)')
                        st.bar_chart(frame[['Visible pass %','Both groups pass %']])
                    with c2:
                        st.caption('Mean and median latency (seconds)')
                        st.bar_chart(frame[['Mean latency (s)','Median latency (s)']])
                st.markdown('**Case-level evidence**')
                st.dataframe(detail, use_container_width=True, hide_index=True)
                st.download_button('Export selected benchmark runs', json.dumps(
                    [r for _, _, group in chosen for r in group], indent=2),
                    file_name='repairx_benchmark_selection.json', mime='application/json')

    with tab3:
        st.subheader('Risk and recovery controller')
        st.write('The risk policy uses Python AST checks, patch-size heuristics, sensitive-call detection, '
                 'validation outcomes and an optional diagnosis-confidence input. It is not a security guarantee.')
        st.code('python recovery_demo.py --mode recover\npython recovery_demo.py --mode reject\npython recovery_demo.py --mode high-risk', language='bat')
        if DEMO_PATH.exists():
            try:
                report = json.loads(DEMO_PATH.read_text(encoding='utf-8'))
                st.caption('Latest scripted controller demonstration (not a live AI run)')
                st.json(report, expanded=False)
            except (OSError, json.JSONDecodeError) as exc:
                st.warning(f'Could not read scripted demo report: {exc}')
        st.markdown('**Policy interpretation**')
        st.write('ACCEPT requires both test groups to pass and heuristic risk below the rejection threshold. '
                 'Rejected temporary candidates are discarded. After at most three attempts the controller abstains.')

    with tab4:
        st.subheader('How REPAIR-X works')
        st.code('Faulty Python function\n    ↓\nLLM candidate patch (Groq / Gemini / OpenAI)\n    ↓\nSyntax validation → optional formatting retry\n    ↓\nPre-execution risk screen\n    ↓\nVisible + additional withheld checks (temporary process)\n    ↓\nRisk policy → ACCEPT / REJECT\n    ↓\nUp to 3 attempts → ABSTAIN if unsuccessful\n    ↓\nJSONL experiment history → this dashboard')
        st.markdown('**Live demo commands (run in Anaconda Prompt, not inside Streamlit)**')
        st.code('python -m pytest -q\npython live_recovery.py --provider groq --case divide_zero\npython live_recovery.py --provider gemini --case divide_zero\nstreamlit run repairx_presentation.py', language='bat')
        st.caption('This UI reads local JSONL files; it does not initiate model calls or execute generated patches. '
                   'The prototype preserves original fixtures rather than deploying accepted patches to production.')


if __name__ == '__main__':
    main()
