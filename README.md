# REPAIR-X starter prototype

A deliberately small, controlled demonstration of:
- runtime failure reproduced by tests
- OpenAI-assisted diagnosis/repair proposal
- restricted function-body patch surface
- pytest-based validation
- rollback after failed validation
- bounded retry and JSON event history
- Streamlit dashboard

## 1. Create environment (Anaconda Prompt)

```bat
cd path\to\REPAIR-X-starter
conda create -n repairx python=3.11 -y
conda activate repairx
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Put your API key in `.env` as `OPENAI_API_KEY=...`. Never commit `.env`.

## 2. Prove the baseline bug

```bat
python -m pytest -q
```

Expected: one test passes, the zero-denominator test fails.

## 3. Run the healing loop

```bat
python repair_x.py
```

The loop asks the OpenAI API for a constrained function-body patch, validates syntax, runs tests, retains only a passing patch, and restores the original file after a failed attempt. A final failure leaves the original buggy source restored.

## 4. Open dashboard

```bat
streamlit run dashboard.py
```

## 5. Git

```bat
git init
git add .
git commit -m "Initial REPAIR-X controlled prototype"
```

Create a new empty GitHub repository, then follow GitHub's displayed commands to add the remote and push. Do not commit `.env`.

## Research honesty and limitations
- This is a toy, deterministic proof-of-concept, not production-grade autonomous repair.
- A passing test suite is evidence, not proof of semantic correctness.
- The demo has one injected fault class; report results only for runs actually performed.
- Keep execution confined to this project folder. Review any AI-generated code.
- For stronger evaluation, add more fault scenarios, regression tests, a no-LLM baseline, repeated trials, and report failures as well as successes.
