from neon_live import run_with_events
from neon_theme import CSS, hero, event_html
from benchmark.cases import CASES


def test_theme_is_self_contained_and_branded():
    assert 'rx-hero' in CSS and 'REPAIR' in hero()


def test_event_html_escapes_untrusted_text():
    out = event_html([('generation_error', '<script>alert(1)</script>')])
    assert '<script>' not in out and '&lt;script&gt;' in out


def test_observed_recovery_emits_real_boundaries():
    case = next(c for c in CASES if c['id'] == 'divide_zero')
    events = []
    def generator(client, model, prompt):
        return 'if b == 0:\n    return None\nreturn a / b'
    def validator(source, function, assertions):
        return True, ''
    result = run_with_events(None, 'mock', 'mock', case, lambda k,m: events.append((k,m)),
                             max_attempts=1, generator=generator, validator=validator)
    assert result['outcome'] == 'ACCEPTED'
    kinds = [k for k,_ in events]
    assert kinds.count('generation_start') == 1
    assert kinds.count('validation_start') == 2
    assert kinds[-1] == 'complete'
