"""REPAIR-X visual command center. Replay is safe; live execution is local-only opt-in."""
import difflib
import html
import json
import os
from pathlib import Path
from statistics import mean

from repairx_presentation import load_jsonl
from neon_theme import CSS, hero, event_html

ROOT = Path(__file__).resolve().parent




def diff_text(original, patched):
    return '\n'.join(difflib.unified_diff(original.splitlines(), patched.splitlines(), fromfile='buggy.py', tofile='candidate.py', lineterm=''))


def summarize_batch(rows):
    out = []
    for provider in sorted({r.get('provider', '') for r in rows}):
        subset = [r for r in rows if r.get('provider') == provider]
        times = [r['elapsed_seconds'] for r in subset if isinstance(r.get('elapsed_seconds'), (float, int))]
        out.append({'Provider': provider, 'Trials': len(subset), 'Accepted': sum(r.get('outcome') == 'ACCEPTED' for r in subset), 'Abstained': sum(r.get('outcome') == 'ABSTAINED' for r in subset), 'Mean latency (s)': round(mean(times), 3) if times else None})
    return out


def stage(title, desc, index):
    import streamlit as st
    st.markdown(f'<div class="rx-step"><span class="rx-index">{index:02d}</span><div><strong>{html.escape(title)}</strong><div class="rx-muted">{html.escape(desc)}</div></div></div>', unsafe_allow_html=True)


def show_record(record, case):
    import streamlit as st
    from auto_repair import replace_function_body
    st.caption(f"Run {record.get('run_id','-')} · {record.get('provider','-')} · {record.get('model','-')}")
    stage('OBSERVE', f"Selected controlled fixture: {case['id']}", 1)
    stage('DIAGNOSE', case['spec'], 2)
    st.markdown('#### Original faulty function')
    st.code(case['source'], language='python')
    for i, a in enumerate(record.get('attempts', []), 1):
        st.markdown(f'#### Attempt {i}')
        stage('GENERATE PATCH', f"Model returned a candidate; formatting retries: {a.get('formatting_retries',0)}", 3)
        patch = a.get('patch')
        if patch:
            st.code(patch, language='python')
            try:
                patched = replace_function_body(case['source'], case['function'], patch)
                with st.expander('Inspect source diff', expanded=True):
                    st.code(diff_text(case['source'], patched), language='diff')
            except Exception as e:
                st.warning(f'Candidate could not be parsed: {type(e).__name__}')
        risk = a.get('risk') or {}
        stage('RISK ASSESSMENT', f"{risk.get('level','N/A')} risk · score {risk.get('score','N/A')} · {', '.join(risk.get('reasons',[])) or 'No flagged conditions'}", 4)
        stage('VALIDATE', f"Visible: {'PASS' if a.get('visible_pass') else 'FAIL'} · Additional withheld: {'PASS' if a.get('hidden_pass') else 'FAIL'}", 5)
        decision = a.get('decision', 'REJECT')
        stage('DECIDE', f"{decision} · {a.get('error') or 'No validation error'}", 6)
    outcome = record.get('outcome', 'UNKNOWN')
    st.success(f'Final decision: {outcome}') if outcome == 'ACCEPTED' else st.warning(f'Final decision: {outcome}')
    st.caption('Original fixture unchanged. Rejected temporary candidates are discarded, not Git-rolled-back. Heuristic risk checks and subprocesses are not a security sandbox.')


def main():
    import streamlit as st
    import pandas as pd
    from benchmark.cases import CASES
    st.set_page_config(page_title='REPAIR-X | AI Command Center', page_icon='⚡', layout='wide')
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(hero(), unsafe_allow_html=True)
    bench, bw = load_jsonl(ROOT / 'benchmark_results.jsonl')
    live, lw = load_jsonl(ROOT / 'live_recovery_results.jsonl')
    batch, ew = load_jsonl(ROOT / 'evaluation_trials.jsonl')
    for w in bw + lw + ew:
        st.warning(w)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric('Distinct benchmark faults', len(CASES))
    m2.metric('Recorded live runs', len(live))
    m3.metric('Live accepted', sum(x.get('outcome') == 'ACCEPTED' for x in live))
    m4.metric('Batch repair trials', len(batch))
    t1,t2,t3,t4 = st.tabs(['⚡ Live / Replay', '📊 Evaluation Lab', '🛡️ Risk & Recovery', '🧩 Architecture'])
    with t1:
        left,right = st.columns([1,2], gap='large')
        with left:
            st.subheader('Repair controls')
            case_id = st.selectbox('Fault scenario', [c['id'] for c in CASES])
            provider = st.selectbox('LLM provider', ['groq','gemini','openai'])
            case = next(c for c in CASES if c['id'] == case_id)
            st.info(case['spec'])
            mode = st.radio('Execution mode', ['Replay recorded trace', 'Run real AI repair (local only)'])
            chosen = None
            if mode == 'Replay recorded trace':
                candidates = [r for r in live if r.get('case_id') == case_id]
                if candidates:
                    chosen = st.selectbox('Recorded run', candidates, format_func=lambda r: f"{r.get('provider')} · {r.get('outcome')} · {r.get('timestamp_utc','')[:19]}")
                else:
                    st.warning('No recorded live trace for this fault. Choose another case or run locally.')
            else:
                st.warning('Local-only developer mode. Never enable on a public host: subprocess validation is NOT a sandbox.')
                if os.getenv('REPAIRX_ALLOW_LOCAL_EXECUTION') != '1':
                    st.error('Disabled. Set REPAIRX_ALLOW_LOCAL_EXECUTION=1 in your local terminal, then restart Streamlit.')
                elif st.button('INITIATE LIVE REPAIR', type='primary', width="stretch"):
                    from llm_providers.factory import create_provider
                    from live_recovery import HISTORY
                    from neon_live import run_with_events
                    with st.status('Executing real model calls and controlled validations...', expanded=True) as status:
                        events = []
                        event_area = st.empty()
                        def emit(kind, message):
                            events.append((kind, message))
                            event_area.markdown(event_html(events), unsafe_allow_html=True)
                        emit('start', f'Selected controlled fixture: {case_id}')
                        st.write('Connecting to provider...')
                        try:
                            client, model = create_provider(provider)
                            st.write(f'Connected to {model}; running bounded recovery...')
                            chosen = run_with_events(client, model, provider, case, emit)
                            with HISTORY.open('a', encoding='utf-8') as f:
                                f.write(json.dumps(chosen, ensure_ascii=False) + '\n')
                            status.update(label=f"Run finished: {chosen['outcome']}", state='complete')
                        except Exception as e:
                            status.update(label='Run failed', state='error')
                            st.error(f'{type(e).__name__}: {str(e)[:240]}')
            st.caption('Live console shows actual model-request and validation boundaries as they occur. Risk and attempt decisions are displayed after the controller returns. No simulated progress or arbitrary-code sandboxing.')
        with right:
            st.subheader('Execution trace')
            if chosen:
                show_record(chosen, case)
            else:
                st.markdown('<div class="rx-panel">Select a recorded run to inspect its full repair trace.</div>', unsafe_allow_html=True)
    with t2:
        st.subheader('Evaluation laboratory')
        st.caption('10 distinct fault definitions. Repeated trials are not unique faults. Never equate pytest tests with repair trials.')
        if batch:
            st.dataframe(pd.DataFrame(summarize_batch(batch)), width="stretch", hide_index=True)
            st.bar_chart(pd.DataFrame(summarize_batch(batch)).set_index('Provider')[['Accepted','Abstained']])
            st.download_button('Export raw trial records', '\n'.join(json.dumps(r) for r in batch), 'evaluation_trials.jsonl', 'application/json')
        else:
            st.info('No batch evaluation results yet. Use evaluation_runner.py locally to generate auditable trials.')
        st.markdown('#### Existing 10-case pilot')
        if bench:
            groups = {}
            for r in bench:
                groups.setdefault((r.get('provider'),r.get('run_id')), []).append(r)
            selected = st.selectbox('Recorded pilot run', list(groups), format_func=lambda k: f'{k[0]} · {k[1][:8]} · {len(groups[k])} cases')
            records = groups[selected]
            st.metric('Both test groups passed', f"{sum(r.get('visible_pass') and r.get('hidden_pass') for r in records)}/{len(records)}")
            columns = [
                "case_id",
                "visible_pass",
                "hidden_pass",
                "elapsed_seconds",
                "formatting_retries",
            ]

            df = pd.DataFrame(records).reindex(columns=columns)

            df["formatting_retries"] = (
                pd.to_numeric(df["formatting_retries"], errors="coerce")
                .fillna(0)
                .astype(int)
            )

            st.dataframe(df, width="stretch", hide_index=True)
    with t3:
        st.subheader('Risk policy')
        st.markdown('Risk scores are **heuristic indicators**, not formal proofs of safety. High-risk candidate patterns can be blocked before validation.')
        st.code('python recovery_demo.py --mode recover\npython recovery_demo.py --mode reject\npython recovery_demo.py --mode high-risk', language='bash')
        p = ROOT / 'recovery_demo_report.json'
        if p.exists():
            try:
                report = json.loads(p.read_text(encoding='utf-8'))
                st.json(report, expanded=False)
            except (ValueError, OSError):
                st.warning('Unable to parse recorded recovery report.')
    with t4:
        st.subheader('Actual implemented workflow')
        for i,(name,desc) in enumerate([
            ('Observe','Select a predefined faulty Python function'),
            ('Generate','Call a selected external LLM for a replacement function body'),
            ('Parse','Attempt syntax repair if formatting is invalid'),
            ('Pre-screen','Heuristic risk check before executing candidate'),
            ('Validate','Execute visible and additional withheld assertions in temporary subprocesses'),
            ('Decide','Accept if checks pass and risk policy allows; otherwise retry up to three times'),
            ('Record','Append auditable JSONL result; preserve original fixture')],1):
            stage(name,desc,i)
        st.warning('Current scope: controlled Python functions. No hardened sandbox, unrestricted repository repair, or proven production self-healing.')

if __name__ == '__main__':
    main()
