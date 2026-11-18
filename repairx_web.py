"""REPAIR-X Public BYOK Code Reviewer (non-executing).

Deploy from the original GitHub repository. API keys are accepted per session
and used only to contact the fixed, selected model provider. Uploaded code and
model output are never executed, persisted to disk, or sent to GitHub.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st
from openai import OpenAI

from repairx_web_core import (
    GEMINI_MODELS, MODEL_OPTIONS, UploadError, build_candidate, decode_upload,
    functions, repair_prompt, screen_candidate, static_diagnostics, unified_diff,
)

ROOT = Path(__file__).resolve().parent
SUMMARY_PATH = ROOT / 'web_assets' / 'evaluation_summary.json'
GITHUB_REPO = 'https://github.com/ruhaanizm/REPAIR-X'
ENDPOINTS = {
    'groq': 'https://api.groq.com/openai/v1',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/',
}

CSS = '''
<style>
.stApp {background:radial-gradient(ellipse at 15% 8%, #122647 0%, #050a18 58%); color:#e0efff;}
[data-testid="stHeader"] {background:rgba(3,8,22,.8);}
.rx-hero {border:1px solid #18dbef66;border-radius:20px;padding:25px 30px;
  background:linear-gradient(135deg,#07192d,#0d0f2e 60%,#141032);box-shadow:0 0 38px #00dffe19;margin-bottom:18px;}
.rx-tag {letter-spacing:.25em;color:#40f6ff;font-size:11px;font-weight:700;}
.rx-title {font-size:clamp(36px,4vw,56px);color:#e9feff;letter-spacing:.05em;font-weight:900;
  text-shadow:0 0 24px #05bddd66;margin:2px 0;}
.rx-sub {color:#98afc7;font-size:15px;}
.rx-card {border:1px solid #1c4261;background:#081b31b8;border-radius:14px;padding:18px;margin:9px 0;}
.rx-number {font-size:26px;font-weight:800;color:#52f0ff;}
.rx-label {font-size:12px;letter-spacing:.09em;color:#96abc6;}
.stButton>button[kind="primary"] {background:linear-gradient(100deg,#06b6d4,#635bff);color:white;border:0;font-weight:750;box-shadow:0 0 18px #15bdd450;}
.stTextInput input,.stTextArea textarea {background:#091729;color:#e6f7ff;}
</style>
'''


def _client(provider: str, key: str) -> OpenAI:
    # Fixed endpoint list. Never allow URLs or keys through environment variables.
    kw = dict(api_key=key, timeout=35.0, max_retries=0)
    if provider in ENDPOINTS:
        kw['base_url'] = ENDPOINTS[provider]
    return OpenAI(**kw)


def _ask(provider: str, model: str, key: str, prompt: str) -> str:
    client = _client(provider, key)
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=1500,
    )
    if not response.choices or not isinstance(response.choices[0].message.content, str):
        raise UploadError('Provider returned no text response.')
    return response.choices[0].message.content


def _headline():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('''<div class="rx-hero"><div class="rx-tag">◉ AUTONOMOUS REPAIR · CONTROLLED REVIEW</div>
      <div class="rx-title">⚡ REPAIR-X</div>
      <div class="rx-sub">Bring your own API key · Inspect a Python fault · Generate a proposed patch · Review risk and code differences</div>
      </div>''', unsafe_allow_html=True)


def _summary():
    if not SUMMARY_PATH.is_file():
        st.info('Published experiment summary is not bundled with this deployment.')
        return
    try:
        d = json.loads(SUMMARY_PATH.read_text(encoding='utf-8'))
        summary = d['summary']
    except (ValueError, OSError, KeyError, TypeError):
        st.warning('Benchmark summary cannot be read.')
        return
    st.caption(f"Recorded research batch: {d.get('batch_id','')[:12]} · {summary['distinct_faults']} distinct faults · {summary['total_trials']} repair trials")
    cols = st.columns(3)
    for col, (name,p) in zip(cols, sorted(summary['providers'].items())):
        with col:
            st.metric(name.title(), f"{p['accepted']}/{p['trials']}", f"{p['mean_latency_s']:.3f} s mean")
    st.info('The historical benchmark uses Gemini 3.1 Flash-Lite. Alternative models in the reviewer are NOT included in those results.')


def _show_result(result: dict, source: str, filename: str, target: str, sha256: str):
    """Show only session-local results; keys are never part of the result record."""
    provider, model = result['provider'], result['model']
    patched, assessment, elapsed = result['patched'], result['assessment'], result['elapsed']
    st.markdown(f'### {provider.title()} · `{model}`')
    st.metric('Preliminary risk level', assessment['level'], str(assessment['score']) + '/100')
    st.caption('Risk reasons: ' + (', '.join(assessment['reasons']) or 'No structural flags'))
    st.warning('Static checks only. No candidate code was run; tests have NOT passed. Do not deploy proposed changes without review and testing.')
    st.code(unified_diff(source, patched, filename), language='diff')
    d1, d2 = st.columns(2)
    with d1:
        st.download_button('Download proposed .py file', patched.encode('utf-8'),
                           file_name=filename, mime='text/x-python', key=f'download_{provider}')
    with d2:
        report = {'provider': provider, 'model': model, 'function': target,
                  'source_sha256': sha256, 'status': 'UNTESTED_PROPOSAL',
                  'risk': assessment, 'elapsed_seconds': elapsed}
        st.download_button('Download diagnostic summary', json.dumps(report, indent=2),
                           file_name=f'repairx_{provider}_review.json',
                           mime='application/json', key=f'json_{provider}')


def main():
    st.set_page_config(page_title='REPAIR-X | BYOK Code Reviewer', page_icon='⚡', layout='wide')
    _headline()
    st.caption('Source code: ' + GITHUB_REPO + ' · This public interface does not run or import uploaded code.')
    tab1, tab2, tab3 = st.tabs(['⚡ Live Code Reviewer', '📊 Verified Experiments', '🛡️ How it works & security'])
    # Render informational tabs first so the public showcase works before an upload.
    with tab2:
        st.subheader('REPAIR-X Verified Evaluation')
        _summary()
        st.markdown('The 300 accepted repairs represent repeated trials across 10 predefined fault scenarios. They are not 300 unique faults or proof of correctness for arbitrary uploaded files.')
    with tab3:
        st.markdown('''### What the deployed reviewer actually does
1. Parses an uploaded **Python source file**, without executing it.
2. Extracts top-level functions and static inspection hints.
3. Uses the **repair-agent role** through a user-selected LLM and user-supplied key.
4. Reconstructs the proposed patch, performs Python syntax checks and uses REPAIR-X's existing heuristic risk policy.
5. Displays a **unified diff** and allows a proposed patch download. **No testing or acceptance decision occurs on public hosting.**

### Project modules
- `incident_classifier.py`: rule-based fault diagnosis from an exception type.
- `risk_controller.py`: transparent AST/diff-based risk screening.
- `live_recovery.py` and `benchmark_runner.py`: **local-only** controlled verification and bounded retries.
- `evaluation_runner.py`: local multi-provider experiment records, not accessible from this public UI.

### Security model
Uploaded files are held in memory, not imported, executed or persisted. API keys are accepted through password inputs and are not written to files or records. The provider will receive the selected code. Use **non-sensitive code** and disposable/restricted API keys; the hosting service operates the server and necessarily receives the submitted inputs. No production security or semantic correctness guarantee is claimed.''')
        st.markdown(f'[View implementation on GitHub]({GITHUB_REPO})')

    with tab1:
        st.warning('Privacy: Your API key and selected code are transmitted through this hosted app to the chosen LLM provider. Use a restricted/disposable key and non-sensitive code. The app does not store them in files or send them to GitHub. The hosting operator can still access server-side traffic.')
        uploaded = st.file_uploader('Upload buggy Python file (.py, ≤64 KiB)', type=['py'], accept_multiple_files=False)
        if uploaded is None:
            st.info('Upload a Python source file to begin. You may inspect syntax and static diagnostics without an API key.')
            return
        try:
            source = decode_upload(uploaded.name, uploaded.getvalue())
            info = static_diagnostics(source)
            funcs = functions(source)
        except UploadError as exc:
            st.error(str(exc))
            return
        if not funcs:
            st.error('No top-level Python function found. This reviewer supports top-level functions only.')
            return
        a,b,c = st.columns(3)
        a.metric('Python syntax', 'VALID')
        b.metric('Top-level functions', len(funcs))
        c.metric('Static review hints', len(info['warnings']))
        with st.expander('Original source / static diagnostics', expanded=True):
            left,right = st.columns([3,2])
            with left:
                st.code(source, language='python', line_numbers=True)
            with right:
                st.caption('SHA-256 ' + info['sha256'][:16] + '…')
                if info['warnings']:
                    for w in info['warnings']:
                        st.write(f"Line {w['line']} · {w['rule']} — {w['detail']}")
                else:
                    st.success('No issues matched our limited heuristics (not a correctness guarantee).')
        target = st.selectbox('Select function to repair', [f.name for f in funcs])
        behavior = st.text_area('Describe expected behavior (required)',
                                placeholder='Example: Return None if the denominator is zero; otherwise divide normally.', height=95)
        traceback_text = st.text_area('Error / traceback (optional)', height=90,
                                      placeholder='Example: ZeroDivisionError: division by zero')
        if traceback_text:
            from incident_classifier import classify_fault
            exception = info.get('exception_type') or ''
            import re
            types = re.findall(r'\b([A-Za-z_]\w*(?:Error|Exception))\s*:', traceback_text)
            exception = types[-1] if types else exception
            if exception:
                st.caption('Rule-based incident classification: ' + classify_fault(exception, traceback_text[:1500])['fault_category'])
        st.markdown('#### Model configuration')
        compare = st.toggle('Compare multiple LLM providers', value=False)
        providers = st.multiselect('Select providers', ['groq','openai','gemini'], default=['groq','openai','gemini']) if compare else [st.selectbox('Provider', ['groq','openai','gemini'])]
        setup = []
        for provider in providers:
            c1, c2 = st.columns([2, 3])
            with c1:
                model = st.selectbox(provider.title() + ' model', MODEL_OPTIONS[provider], key='model_'+provider)
            with c2:
                key = st.text_input(provider.title() + ' API key (BYOK)', type='password', key='key_'+provider,
                                    help='Used for this request only; do not commit or share the key.')
            setup.append((provider,model,key))
        if not st.checkbox('I understand that the uploaded source will be sent to my chosen provider(s).', value=False):
            st.caption('Explicit confirmation is required before an external API request.')
            consent = False
        else:
            consent = True
        run = st.button('⚡ GENERATE & SCREEN PATCH', type='primary', width='stretch', disabled=not consent)
        if run:
            if not setup or not all(key.strip() for _,_,key in setup):
                st.error('Enter a key for each selected provider.')
                return
            try:
                prompt = repair_prompt(source, target, behavior, traceback_text)
            except UploadError as exc:
                st.error(str(exc))
                return
            results = []
            for provider, model, key in setup:
                st.markdown(f'#### Processing {provider.title()} · `{model}`')
                with st.status('Running actual model request and static review...', expanded=True) as status:
                    start = time.perf_counter()
                    st.write('1 / 4 · Source syntax and selected function verified')
                    st.write('2 / 4 · Sending code to selected provider')
                    try:
                        raw = _ask(provider, model, key, prompt)
                        st.write('3 / 4 · Model response received; parsing proposed patch')
                        try:
                            patched, body = build_candidate(source, target, raw)
                        except UploadError:
                            st.write('Formatting-only retry requested')
                            retry = (prompt + '\nYour previous output was invalid as a function body. '
                                     'Return a syntactically valid body only.\nPrevious output:\n' + raw[:1200])
                            raw = _ask(provider, model, key, retry)
                            patched, body = build_candidate(source, target, raw)
                        assessment = screen_candidate(source, patched)
                        elapsed = round(time.perf_counter() - start, 3)
                        st.write('4 / 4 · Parsed candidate and applied structural risk screening')
                        status.update(label=f'Candidate prepared in {elapsed}s — NOT test-validated', state='complete')
                    except Exception as exc:
                        status.update(label='Provider request or candidate parsing failed', state='error')
                        st.error('Unable to produce a reviewable patch: ' + type(exc).__name__)
                        continue
                results.append({'provider': provider, 'model': model, 'patched': patched,
                                'assessment': assessment, 'elapsed': elapsed})
            # Session memory persists only candidate outputs for refresh/download;
            # no API key, prompts or traceback are saved in this structure.
            st.session_state['rx_reviews'] = {'sha256': info['sha256'], 'target': target,
                                              'results': results}
        saved = st.session_state.get('rx_reviews', {})
        if saved.get('sha256') == info['sha256'] and saved.get('target') == target:
            for result in saved.get('results', []):
                _show_result(result, source, uploaded.name, target, info['sha256'])

if __name__ == '__main__':
    main()
