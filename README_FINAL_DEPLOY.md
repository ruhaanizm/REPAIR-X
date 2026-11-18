# REPAIR-X final release: deployment and supervisor demo

**Release date:** 18 November 2026. Based on `REPAIR-X-starter(10).zip`.

## What is new

- `repairx_web.py`: the public Neon bring-your-own-key (BYOK) code reviewer, directly deployed from the same original GitHub repository. There is no second repository or remote code-fetch system.
- `repairx_web_core.py`: safe, pure-Python parsing, top-level-function discovery, static inspection, non-executing patch construction and preliminary risk assessment, importing existing `risk_controller.py` and `incident_classifier.py`.
- `web_assets/evaluation_summary.json`: curated, **historical** 300-trial result for the public showcase. Not an inference about a newly uploaded file.
- `tests/test_public_reviewer.py`: 12 regression tests.
- `.streamlit/config.toml`: dark neon accents.
- `examples/demo_bug.py`, `examples/missing_key.py`: non-sensitive presentation samples.
- `.gitignore`: ignore local trial logs, API keys and Streamlit secrets, track source code and the curated summary.

The existing `live_recovery.py`, `evaluation_runner.py`, local demo, repair engine and benchmark are **not modified**. The public web reviewer performs no test execution. It **does not** run uploaded or model-generated Python files, import uploaded files, install packages, invoke shells, or write proposed patches back to GitHub.

## 1. Install the update into the original GitHub repository

In Anaconda Prompt (Windows):

```bat
cd /d D:\MINOR_PROJECT\REPAIR-X-starter
conda activate repairx
git status --short
```

Extract `REPAIR-X-FINAL-BYOK-RELEASE.zip` elsewhere, and copy the **contents** into your existing REPAIR-X folder, allowing the updated `.gitignore` to replace the old one. The ZIP is an **overlay**, not a replacement for the full source archive. It does not contain a `.git` directory, credentials or virtual environment.

Check the files exist at the expected paths:

```bat
dir repairx_web.py
dir repairx_web_core.py
```

```bat
python -m pytest -q
```

Previous verified baseline: **61** passed. This package adds 12 new tests; target **73 passed** in your Conda environment. The new 12 core tests passed here, but the historical 61 could not be rerun in the build environment because required Streamlit/OpenAI dependencies were unavailable there.

## 2. Run the public-facing BYOK application locally

```bat
streamlit run repairx_web.py --server.address 127.0.0.1
```

In the browser, go to the URL shown by Streamlit (normally `http://localhost:8501`).

1. Upload a **UTF-8** `.py` file (max 64 KiB), with at least one top-level function and valid Python syntax.
2. Inspect static rule-based diagnostic hints; these are NOT verified runtime defects.
3. Pick the function to review.
4. Enter expected behavior (required) and optionally an exception traceback.
5. Select Groq/Qwen, OpenAI, or Gemini. Optionally enable side-by-side provider comparison.
6. Enter your *own* disposable/restricted API key in the password field; agree to transmission to the selected provider.
7. Click **GENERATE & SCREEN PATCH**. The real model request is visible by its status, followed by a generated code diff and preliminary structural risk score.
8. Download the proposed `.py` and review/test it **outside** the public app.

**Privacy warning:** Streamlit receives the entered key and code server-side to relay the selected model request. This application never saves them to its own files, databases or GitHub, but the hosting operator and chosen model provider must be trusted. The model provider may retain/process the code according to its terms. Do not upload private code or use high-privilege keys in a public demonstration. Public hosting does not guarantee security or abuse prevention. API calls may incur charges.

### Supported scope

- Standalone, syntactically valid Python source with a single selected top-level function.
- Dynamic behavior is NOT inferred from AST alone.
- New import statements in suggested function bodies are rejected for manual review.
- A failed provider request is reported; we do not spoof success.
- No testing, runtime fault reproduction, CI execution, code sandboxing or automatic GitHub commit of the proposed patch.

## 3. GitHub tracking and final commit

Important finding: the uploaded snapshot includes a `.git` folder with `HEAD` at `80a8b6d`. New dashboard and evaluation source files were untracked in **that archive**. Other tracked changes were whitespace/line-endings only when compared with its embedded HEAD.

Your actual local repo may differ; always verify `git status` locally.

After installing and testing, stage the historical untracked implementation and final release files **explicitly**:

```bat
git add .gitignore README_FINAL_DEPLOY.md repairx_web.py repairx_web_core.py web_assets/evaluation_summary.json .streamlit/config.toml tests/test_public_reviewer.py examples/demo_bug.py examples/missing_key.py
git add evaluation_runner.py neon_live.py neon_theme.py repairx_command_center.py repairx_presentation.py
git add tests/test_evaluation_v2.py tests/test_neon_upgrade.py tests/test_repairx_presentation.py tests/test_upgrade.py
git diff --cached --check
git status --short
git diff --cached --stat
```

Before committing, inspect `git diff --cached --name-only`. None of `.env`, provider credentials, API request payloads, `evaluation_trials.jsonl`, or private user uploads should be staged.

```bat
git commit -m "Ship BYOK public code reviewer and track final evaluation dashboards"
git push origin main
git status -sb
git log -1 --oneline
```

**Do not run `git add -A` blindly**, because historical logs and user files may contain sensitive data. Your local `.git` is necessary for tracking but never upload it in ZIPs.

The generated experiment summary in `web_assets/` is version-controlled. Full raw records are preserved locally outside Git; do not claim those are Git-tracked unless you separately review and commit a sanitized, approved dataset.

## 4. Deploy from your existing REPAIR-X GitHub repository

1. Push the commit above to `https://github.com/ruhaanizm/REPAIR-X`.
2. Open <https://share.streamlit.io/> and connect your GitHub account.
3. Select repository `ruhaanizm/REPAIR-X`, branch `main`.
4. Set main file / entry point to **`repairx_web.py`** at the repository root.
5. Leave Streamlit secrets blank: this is a BYOK app. Set no `REPAIRX_ALLOW_LOCAL_EXECUTION` flag on the host.
6. Deploy, then check the assigned `*.streamlit.app` URL from a private browser window. No public link can be predicted before deployment.
7. Test with a disposable key and a public/non-sensitive sample `.py` file. Verify that the system displays `NOT test-validated` and the diff.

`requirements.txt` already includes Streamlit, OpenAI SDK, python-dotenv and pytest. Only the first two are needed by the new public entry point, but reusing the repository dependencies is simplest.

### Smoke test file: `examples/demo_bug.py` (included in the upgrade ZIP)

```python
def safe_divide(a, b):
    return a / b
```

Expected behavior field: `Return None if the denominator is zero, otherwise divide a by b.`

Possible error field: `ZeroDivisionError: division by zero`

Run a request using Qwen, then inspect its proposed patch. Results depend on provider availability and model behavior.

## 5. Live supervisor demo: recommended order

### Screen A: Public BYOK reviewer (2–3 min)

- Open the deployed URL and show that it comes from the original GitHub repository.
- Upload `demo_bug.py`, select `safe_divide`, specify expected behavior and exception.
- Select model and enter a **disposable personal key**; don't expose the key on the projector.
- Click **GENERATE & SCREEN PATCH**. Explain AST parsing, prompt generation, patch reconstruction, risk heuristic, and downloadable proposed result.
- State clearly: **no uploaded code execution and no runtime pass/fail claim**.

### Screen B: Controlled local validation engine (2–3 min)

```bat
cd /d D:\MINOR_PROJECT\REPAIR-X-starter
conda activate repairx
set REPAIRX_ALLOW_LOCAL_EXECUTION=1
streamlit run repairx_command_center.py --server.address 127.0.0.1
```

In the original Neon Command Center, select the `divide_zero` controlled case and Groq, then run live recovery. This runs actual model requests and controlled subprocess validation. Do not expose the local demo server publicly, and do not run uploaded user code through it.

### Screen C: Safety/recovery and evaluation (3–4 min)

Use a second terminal:

```bat
python recovery_demo.py --mode recover
python recovery_demo.py --mode reject
python recovery_demo.py --mode high-risk
```

These are deliberately **scripted** demonstrations, not live LLM retries. Show failed candidate rejection, bounded retries, abstention and original-source preservation. Then show the 300-trial recorded pilot from the dashboard or public summary.

### Offline fallback

Keep the original report PDF, the 300-trial charts, a screenshot of the public app, and the local scripted demonstrations ready in case of API/network issues.

## 6. Gemini model choice — current options

Your 300-trial benchmark evaluated **`gemini-3.1-flash-lite`**, with 100/100 accepted, mean latency ~7.602s and median latency ~2.498s. Groq ~0.683s mean and OpenAI ~1.016s mean. All provider results pertain only to the existing 10 small controlled cases, repeated 10 times; do not claim production accuracy.

Google's current official Gemini pricing page lists **free-tier standard input/output** (subject to quotas and account eligibility) for `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` as of 18 Nov 2026. Higher-quality Flash models may be slower, not faster. Their access and limits must be checked in Google AI Studio for the particular key.

**Recommendation:** leave historical model selection unchanged in the published benchmark. In the new public reviewer, Gemini defaults to `gemini-3.8-flash` and allows switching back to `gemini-3.1-flash-lite` or trying the other models. For an apples-to-apples controlled comparison using the existing benchmark runner:

```bat
set GEMINI_MODEL=gemini-3.8-flash
python evaluation_runner.py --providers gemini --repeats 1 --limit 10 --delay 2
set GEMINI_MODEL=gemini-3.1-flash-lite
```

Run this only locally in your environment with the Gemini key configured. Record the new batch ID and explain that this is a **separate experiment**; do not merge it into the historical 300-trial dataset. Retry or compare on identical cases/conditions when possible. A new model is not automatically better or equally fast.

Official references: <https://ai.google.dev/gemini-api/docs/models>, <https://ai.google.dev/gemini-api/docs/pricing>, <https://ai.google.dev/gemini-api/docs/rate-limits>.

## 7. How many agents were actually implemented?

**One LLM-powered agent role** — the repair candidate generator; choose one of three external model providers. The source does not implement several independently orchestrated LLM agents or a learned multi-agent framework.

It also contains **four deterministic supporting roles/components**:

1. **Incident classification (`incident_classifier.py`)** — maps observed exception types into fault categories and repair strategy suggestions using explicit rules.
2. **Risk assessment (`risk_controller.py`)** — scores structural changes, sensitive calls, changed signatures and validation outcomes.
3. **Validation (`benchmark_runner.py`)** — performs controlled visible/withheld test assertions in temporary subprocesses; local only.
4. **Recovery control (`live_recovery.py`)** — orchestrates bounded retries, rejects candidates or abstains without overwriting the original fixture.

These are **five logical stages**, not five independent AI agents. Some reports may use the phrase "multi-agent-inspired modular pipeline"; the more technically defensible description is **"single-LLM, modular risk-aware automated repair framework"**.

## 8. Deliverable status

- ZIP created, review core tests pass.
- Public live model calls **not tested in this build environment** (no user API credentials).
- Full historical test suite was **previously verified by the user (61 passed)**; current build environment lacks the packages needed to rerun all legacy tests.
- No GitHub push or Streamlit deployment has been performed from here; those require your accounts and must be completed with the steps above.
