"""Live UI event hooks around the existing REPAIR-X engine.

Only events actually observed by the generator/validator are emitted.  This
is not a secure execution environment; use controlled local fixtures only.
"""
from live_recovery import run_case
from llm_providers.generate import generate_text
from benchmark_runner import check_tests


def run_with_events(client, model, provider, case, emit, max_attempts=3,
                    generator=generate_text, validator=check_tests):
    """Execute the unchanged repair controller with observable call boundaries."""
    emit('provider', f'Provider selected: {provider} / {model}')
    counts = {'generation': 0, 'validation': 0}

    def observed_generator(c, m, prompt):
        counts['generation'] += 1
        n = counts['generation']
        emit('generation_start', f'LLM request {n} started')
        try:
            result = generator(c, m, prompt)
        except Exception as exc:
            emit('generation_error', f'LLM request {n} failed: {type(exc).__name__}')
            raise
        emit('generation_end', f'LLM response {n} received')
        return result

    def observed_validator(source, function, assertions):
        counts['validation'] += 1
        n = counts['validation']
        emit('validation_start', f'Validation group {n} started')
        try:
            passed, error = validator(source, function, assertions)
        except Exception as exc:
            emit('validation_error', f'Validation group {n} errored: {type(exc).__name__}')
            raise
        emit('validation_end', f'Validation group {n}: {"PASS" if passed else "FAIL"}')
        return passed, error

    record = run_case(client, model, provider, case, max_attempts=max_attempts,
                      generator=observed_generator, validator=observed_validator)
    for attempt in record['attempts']:
        risk = attempt.get('risk') or {}
        emit('decision', f'Attempt {attempt["attempt"]}: {attempt["decision"]}; risk {risk.get("level", "N/A")}')
    emit('complete', f'Final outcome: {record["outcome"]}')
    return record
