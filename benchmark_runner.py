"""REPAIR-X pilot: AI-only patch generation, isolated visible/hidden checks.

Only run with trusted local case definitions. Candidate code is executed in a
subprocess; this is NOT a security sandbox for arbitrary untrusted code.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import ast

from dotenv import load_dotenv

load_dotenv()
from benchmark.cases import CASES
from auto_repair import clean_patch_text, replace_function_body
from llm_providers.factory import create_provider
from llm_providers.generate import generate_text

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / 'benchmark_results.jsonl'


def check_tests(candidate, function, assertions, timeout=15):
    """Run one test group in a fresh process; report only pass/fail."""
    with tempfile.TemporaryDirectory(prefix='repairx_bench_') as folder:
        root = Path(folder)
        (root / 'target.py').write_text(candidate, encoding='utf-8')
        checks = 'from target import ' + function + '\n' + '\n'.join(assertions) + '\n'
        (root / 'check.py').write_text(checks, encoding='utf-8')
        try:
            result = subprocess.run(
                [sys.executable, '-B', 'check.py'], cwd=root,
                capture_output=True, text=True, timeout=timeout,
            )
            return result.returncode == 0, (result.stderr or result.stdout)[-1200:]
        except subprocess.TimeoutExpired:
            return False, 'timeout'


def build_prompt(case):
    # Do not include visible/hidden assertions or known-good patches.
    return (
        'Repair the following Python function.\n'
        f"Required behavior: {case['spec']}\n"
        f"Function source:\n{case['source']}\n"
        'Return ONLY a replacement function body, not the def line. '
        'No Markdown fences. Keep Python indentation valid. '
        'Do not add imports, filesystem operations, subprocess, eval or exec.'
    )


def formatting_retry_prompt(case, invalid_body, syntax_error):
    """One formatting-only retry; never expose test assertions."""
    return (
        'Your previous replacement function body was invalid Python.\n'
        f"Function: {case['function']}\n"
        f"Required behavior: {case['spec']}\n"
        f"Original function source:\n{case['source']}\n"
        f"Previous body:\n{invalid_body}\n"
        f"Parser error: {type(syntax_error).__name__}: {syntax_error}\n"
        'Correct ONLY syntax and indentation. Preserve the intended behavior. '
        'Return ONLY the replacement function body, no def line or Markdown. '
        'First top-level statement at column 0; use four spaces per nested level.'
    )


def prepare_candidate(client, model, case):
    """Attempt initial patch and at most one syntax-format retry."""
    raw = generate_text(client, model, build_prompt(case))
    body = clean_patch_text(raw)
    try:
        return replace_function_body(case['source'], case['function'], body), body, 0
    except (SyntaxError, IndentationError) as exc:
        retry_raw = generate_text(client, model, formatting_retry_prompt(case, body, exc))
        retry_body = clean_patch_text(retry_raw)
        return replace_function_body(case['source'], case['function'], retry_body), retry_body, 1


def evaluate_case(client, model, provider, case, run_id):
    start = time.perf_counter()
    record = dict(
        run_id=run_id, timestamp_utc=datetime.now(timezone.utc).isoformat(),
        provider=provider, model=model, case_id=case['id'],
        generated=False, visible_pass=False, hidden_pass=False,
        patch_source='ai', error=None, patch=None, formatting_retries=0,
    )
    try:
        candidate, body, retry_count = prepare_candidate(client, model, case)
        record['formatting_retries'] = retry_count
        record['generated'] = True
        record['patch'] = body
        record['visible_pass'], visible_error = check_tests(
            candidate, case['function'], case['visible']
        )
        # Independent checks are applied even if visible checks fail.
        record['hidden_pass'], hidden_error = check_tests(
            candidate, case['function'], case['hidden']
        )
        if not record['visible_pass']:
            record['error'] = 'visible_validation_failed: ' + visible_error[:300]
        elif not record['hidden_pass']:
            record['error'] = 'hidden_validation_failed: ' + hidden_error[:300]
    except Exception as exc:
        record['error'] = type(exc).__name__ + ': ' + str(exc)[:300]
    record['elapsed_seconds'] = round(time.perf_counter() - start, 3)
    record['correct_by_tests'] = record['visible_pass'] and record['hidden_pass']
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['openai','gemini','groq'])
    parser.add_argument('--case', choices=[c['id'] for c in CASES])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--debug-patches', action='store_true', help='Reserved; patch bodies are recorded in JSONL')
    args = parser.parse_args()
    cases = [c for c in CASES if args.case is None or c['id'] == args.case]
    for case in cases:
        for group_name in ("visible", "hidden"):
            checks = (
                f"from target import {case['function']}\n"
                + "\n".join(case[group_name])
                + "\n"
            )
            try:
                ast.parse(checks)
            except SyntaxError as exc:
                raise RuntimeError(
                    f"Invalid {group_name} tests for {case['id']}: {exc}"
                ) from exc

    # Check that each original fixture fails at least one visible assertion.
    for case in cases:
        passed, _ = check_tests(case['source'], case['function'], case['visible'])
        if passed:
            raise RuntimeError('Original fixture unexpectedly passes: ' + case['id'])

    print(f'Pilot cases: {len(cases)} | original fixtures verified failing')
    if args.dry_run:
        print('DRY RUN: no API calls, no result records written')
        return
    provider = args.provider or os.getenv('LLM_PROVIDER','openai').strip().lower()
    client, model = create_provider(provider)
    run_id = uuid4().hex
    print(f'Provider: {provider} | Model: {model} | Run: {run_id}')
    for case in cases:
        result = evaluate_case(client, model, provider, case, run_id)
        with HISTORY.open('a', encoding='utf-8') as file:
            file.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(f"{case['id']}: visible={result['visible_pass']} "
              f"hidden={result['hidden_pass']} "
              f"time={result['elapsed_seconds']}s "
              f"error={result['error'] or '-'}")
    print('Saved:', HISTORY)
    print('Note: hidden tests provide additional evidence, not proof of semantic correctness.')


if __name__ == '__main__':
    main()
