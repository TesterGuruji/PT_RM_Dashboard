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

### `app.py` (single ~1200-line script)
- `FILES` dict defines the modules shown in the sidebar radio: `"Pipeline Demands"` → `PipelineDemand_Details.csv`, `"DST Bench Resources"` → `DST_Bench.csv`, `"DST Soon To Bench Resources"` → `DST_SoonTobench.csv`, each with its expected column list. Adding a module means adding a `FILES` entry **and** a new `elif selection == ...` branch.
- Each module branch is a KPI strip (`render_kpis`) followed by three `st.tabs`: **Overview** (Plotly charts in keyed `st.container(border=True, key="card-...")` cards), **Records** (filters/search → `st.data_editor` in edit mode → save), **AI Assistant** (chat). The DST block duplicates the Pipeline block with `_dst`-suffixed widget keys/session-state names; keep keys unique when editing either. Code in the Records tab computes `display_df`, which the AI tab (later in the script) uses as its filtered context.
- `load_data` is `@st.cache_data` (keyed on file mtime) and fills NaN with `'Unassigned'` for display. Saving from the data editor writes **directly back to the CSV** after `restore_blank_cells` (undoes the display fill) and `restore_integer_columns` (keeps `10` from becoming `10.0`), then `load_data.clear()` + `st.rerun()`.
- Theming: native widgets are themed in `.streamlit/config.toml` (light theme, Inter, navy sidebar via `[theme.sidebar]`); the `<style>` block at the top of `app.py` only styles the custom HTML components (`.kpi`, `.app-header`, `.notice`, sidebar cards) and `div[class*="st-key-card-"]` containers.
- Chart helpers (`style_figure`, `status_breakdown_chart`, `monthly_level_chart`, `bench_aging_chart`) share one Plotly style and are rendered with `show_chart` (`theme=None`, so Streamlit doesn't restyle them). Colours are fixed per entity: `PIPELINE_STATUS_COLORS` / `DST_STATUS_COLORS` (the DST stages are an ordered light→dark blue ramp) and `LEVEL_COLORS` (one colour per resource level across the app); the Records table tints Status cells from the same maps via `status_cell_style`.
- **DST Soon To Bench** (module 3) differs from the other two: `DST_SoonTobench.csv` headers may carry stray spaces, so the branch strips `raw_df.columns` and saves with `restore_blank_cells(..., strip_headers=True)` (the file is rewritten with trimmed headers). Urgency is derived, never stored: `add_release_columns` (in `ai_assistant/soon_to_bench_assistant.py`, shared with the app) computes `Days To Release` from `End Date` vs today and buckets it into `RELEASE_WINDOWS`, coloured with the reserved status colours in `RELEASE_WINDOW_COLORS`. The computed columns appear only in read mode, never in the editor or the saved CSV. Its widget/session keys use the `_stb` suffix.
- The assistant is re-instantiated each rerun with `working_df` — the currently filtered view if filters are active, otherwise the full dataset. Chat history lives in `st.session_state.ai_chat_history` / `dst_ai_chat_history`.

### `ai_assistant/` package
Both assistants use the same two-tier flow in `answer_question()`:
1. **Primary: LLM grounded answer** — `LLMClient.generate_grounded_answer()` serializes the *entire* dataframe (`df.to_string()`) into the system prompt and asks the LLM to answer from it. Used whenever an API key is available.
2. **Fallback: deterministic engine** (no key, or LLM error/empty response):
   - `PipelineAIAssistant` (`assistant.py`): `QueryParser` (regex fast-path, then `LLMClient.generate_json_query`) → JSON query plan → `QueryExecutor` (allowlisted columns/operations/operators from `prompts.py`, no `eval`/`exec`) → `_format_computed_output`.
   - `DSTBenchAIAssistant` (`dst_assistant.py`): self-contained regex/keyword rules in `_eval_deterministic`; does not use the parser/executor.
   - `SoonToBenchAIAssistant` (`soon_to_bench_assistant.py`): same pattern as DST; it passes today's date plus the computed release columns to the LLM so date questions ("releasing in the next 30 days") work.

Note: the README's architecture diagram describes only the parser→executor path; in the code, that path is the fallback, not the primary one.

- `llm_client.py`: provider auto-detection (explicit `LLM_PROVIDER`, else first key found among Gemini → OpenAI → Groq). Calls `load_dotenv(override=True)` on every `is_available()` check, so `.env` edits take effect without restart.
- `query_parser.py` hardcodes domain vocab (`SECTOR_LEADS`, `RESOURCE_LEVELS`, `CLIENTS`, `SECTORS`) matching current CSV contents — update these when the data's categorical values change.
- Grounding conventions to preserve: out-of-scope answers return the fixed fallback message (`FALLBACK_NOT_FOUND_MESSAGE` / `DST_FALLBACK_MESSAGE`), and every response ends with the `📊 Source: <file>.csv` citation.

### Data files
- `PipelineDemand_Details.csv`, `DST_Bench.csv` — live data for modules 1 and 2 (mutated by the UI).
- `DST_SoonTobench.csv` — live data for module 3.
- `GDS_PTMembers.csv`, `resource_data-original copy.csv` — not currently wired into `app.py`.
- Column name `Cousellor Name` in `DST_Bench.csv` is misspelled; `FILES` uses the misspelling, and the DST filter accepts either spelling. Renaming the column requires updating both.

`collector-config.yaml` is an OpenTelemetry collector config (OTLP → debug exporter); nothing in the app currently emits telemetry to it.
