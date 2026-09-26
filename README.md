# Performance Test Resourcing Dashboard - AI Assistant

A high-performance Streamlit dashboard for managing Performance Testing resourcing with an embedded **AI Assistant** grounded strictly on `PipelineDemand_Details.csv`.

---

## 🌟 Architecture Overview

The AI Assistant follows a **structured, data-grounded query architecture** designed to minimize latency, prevent hallucinations, and optimize LLM token usage:

```
User Question
      ↓
Streamlit Chat UI (st.chat_message / st.chat_input)
      ↓
Hybrid Query Parser (Deterministic Fast-Path + LLM Structured Query)
      ↓
JSON Structured Query Plan
      ↓
Safe Pandas Query Executor (Allowlisted Columns & Operators, No eval/exec)
      ↓
PipelineDemand_Details.csv
      ↓
Computed Verified Results (Aggregations, Counts, Filtered Rows)
      ↓
Grounded Response Synthesizer + Source Attribution
      ↓
User
```

---

## 🔒 Strict Data Grounding & Security

1. **Single Source of Truth**: All factual answers originate exclusively from `PipelineDemand_Details.csv`.
2. **Zero Hallucination / Out-of-Domain Guard**: If a query asks about something not present in the dataset (or outside business context), the assistant responds with:
   > *"I couldn't find enough information in the Pipeline Demand data to answer that question."*
3. **Prompt Injection Protection**: CSV content and user inputs are strictly treated as untrusted data. No instructions within data records are executed.
4. **Controlled Execution**: Zero dynamic code execution (`no eval()`, `no exec()`, no dynamic SQL). All queries run through an allowlisted pandas execution engine.
5. **Source Attribution**: Every answer ends with: `📊 Source: PipelineDemand_Details.csv`.

---

## 🚀 Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):

```bash
cp .env.example .env
```

Set your preferred LLM provider and API key:

```env
# Provider: gemini | openai | groq
LLM_PROVIDER=gemini

# Google Gemini API Key (Free tier from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

*Note: The assistant features a deterministic fast-path layer that immediately answers standard analytical queries even without an external API key.*

### 3. Launch the Dashboard
```bash
streamlit run app.py
```

---

## 💡 Supported Query Types & Examples

| Query Category | Example Questions |
|---|---|
| **Counts** | *"How many demands are there?"*, *"How many open demands?"*, *"How many invalid demands?"* |
| **Filtering** | *"Show all open demands"*, *"Show all demands assigned to Venkat"*, *"Show all unassigned demands"* |
| **Dates** | *"How many demands start in July 2026?"*, *"Show demands starting in September 2026"* |
| **Ranking** | *"Which resource level has the highest demand?"*, *"Which Sector PT lead has the most demands?"* |
| **Group By / Distribution** | *"Give me the demand count by status"*, *"Show distribution of demands by client"* |
| **Summary** | *"Give me a summary of the pipeline"*, *"Summarize the current demand situation"* |
| **Comparison** | *"Compare Staff 2 and Senior 3"*, *"Compare open vs invalid demands"* |
| **Lookup** | *"Show demand 5678"*, *"Who is the Sector PT lead for demand 5678?"* |

---

## 📁 Project Structure

```
RMDashboard/
├── app.py                      # Main Streamlit dashboard (Table, Filters, Metrics, AI Assistant)
├── PipelineDemand_Details.csv  # Single source of truth CSV dataset
├── ai_assistant/               # Modular AI Assistant Package
│   ├── __init__.py             # Exports PipelineAIAssistant and ask_pipeline_assistant
│   ├── prompts.py              # System prompts, JSON schemas, injection safeguards
│   ├── query_parser.py         # Hybrid deterministic & LLM structured query parser
│   ├── query_executor.py       # Safe, validated Pandas query engine (No eval/exec)
│   ├── llm_client.py           # Unified multi-provider client (Gemini, OpenAI, Groq)
│   └── assistant.py            # Main coordinator and markdown response formatter
├── requirements.txt            # Project dependencies
├── .env.example                # Example environment variables
└── README.md                   # This documentation file
```
