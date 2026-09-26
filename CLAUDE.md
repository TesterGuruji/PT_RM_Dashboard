# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements.txt
cp .env.example .env          # set LLM_PROVIDER (gemini|openai|groq) and matching *_API_KEY / *_MODEL
streamlit run app.py          # serves on :8501
```

There is no test suite, linter, or build step. To exercise the AI assistants without the UI:

```bash
python -c "from ai_assistant import ask_pipeline_assistant; print(ask_pipeline_assistant('How many open demands?')['response'])"
python -c "from ai_assistant import ask_dst_bench_assistant; print(ask_dst_bench_assistant('Who has the longest bench days?')['response'])"
```

Unset the API key (or set `LLM_PROVIDER` to a provider with no key) to force the deterministic fallback path.

## Architecture

Streamlit dashboard for Performance Testing resource management, backed entirely by CSV files in the repo root (no database). Run from the repo root — all CSV paths are relative.

### `app.py` (single ~1600-line script)
- `FILES` dict defines the modules shown in the sidebar radio: `"Pipeline Demands"` → `PipelineDemand_Details.csv`, `"DST Bench Resources"` → `DST_Bench.csv`, each with its expected column list. Adding a module means adding a `FILES` entry **and** a new `elif selection == ...` branch.
- Each module branch is a large, mostly parallel block: KPI cards → Plotly charts → filters/search → `st.data_editor` table (edit mode) → AI assistant chat. The DST block duplicates the Pipeline block with `_dst`-suffixed widget keys/session-state names; keep keys unique when editing either.
- `load_data` is `@st.cache_data` and fills NaN with `'Unassigned'`. Edits made in the data editor are written **directly back to the CSV** (`to_csv`), then `load_data.clear()` + `st.rerun()`.
- Styling is a big inline `<style>` block at the top plus lots of `st.markdown(..., unsafe_allow_html=True)` HTML snippets.
- The assistant is re-instantiated each rerun with `working_df` — the currently filtered view if filters are active, otherwise the full dataset. Chat history lives in `st.session_state.ai_chat_history` / `dst_ai_chat_history`.

### `ai_assistant/` package
Both assistants use the same two-tier flow in `answer_question()`:
1. **Primary: LLM grounded answer** — `LLMClient.generate_grounded_answer()` serializes the *entire* dataframe (`df.to_string()`) into the system prompt and asks the LLM to answer from it. Used whenever an API key is available.
2. **Fallback: deterministic engine** (no key, or LLM error/empty response):
   - `PipelineAIAssistant` (`assistant.py`): `QueryParser` (regex fast-path, then `LLMClient.generate_json_query`) → JSON query plan → `QueryExecutor` (allowlisted columns/operations/operators from `prompts.py`, no `eval`/`exec`) → `_format_computed_output`.
   - `DSTBenchAIAssistant` (`dst_assistant.py`): self-contained regex/keyword rules in `_eval_deterministic`; does not use the parser/executor.

Note: the README's architecture diagram describes only the parser→executor path; in the code, that path is the fallback, not the primary one.

- `llm_client.py`: provider auto-detection (explicit `LLM_PROVIDER`, else first key found among Gemini → OpenAI → Groq). Calls `load_dotenv(override=True)` on every `is_available()` check, so `.env` edits take effect without restart.
- `query_parser.py` hardcodes domain vocab (`SECTOR_LEADS`, `RESOURCE_LEVELS`, `CLIENTS`, `SECTORS`) matching current CSV contents — update these when the data's categorical values change.
- Grounding conventions to preserve: out-of-scope answers return the fixed fallback message (`FALLBACK_NOT_FOUND_MESSAGE` / `DST_FALLBACK_MESSAGE`), and every response ends with the `📊 Source: <file>.csv` citation.

### Data files
- `PipelineDemand_Details.csv`, `DST_Bench.csv` — live data for the two modules (mutated by the UI).
- `GDS_PTMembers.csv`, `DST_SoonTobench.csv`, `resource_data-original copy.csv` — not currently wired into `app.py`.
- Column name `Cousellor Name` in `DST_Bench.csv` is misspelled; `FILES` uses the misspelling, and the DST filter accepts either spelling. Renaming the column requires updating both.

`collector-config.yaml` is an OpenTelemetry collector config (OTLP → debug exporter); nothing in the app currently emits telemetry to it.
