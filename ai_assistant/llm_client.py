"""
Unified LLM Client Supporting Google Gemini, OpenAI, and Groq.
Provides data-grounded question answering and structured query generation.
"""

import os
import json
import re
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from .prompts import (
    STRUCTURED_QUERY_SYSTEM_PROMPT,
    RESPONSE_SYNTHESIS_SYSTEM_PROMPT,
    FALLBACK_NOT_FOUND_MESSAGE,
    SOURCE_CITATION
)

load_dotenv(override=True)

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
# Generous enough for markdown tables listing every record
MAX_OUTPUT_TOKENS = 4096

class LLMClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "").lower()
        self.model = model
        self._detect_provider_and_keys()

    def _detect_provider_and_keys(self):
        """Auto-detects active provider and API key if not explicitly set."""
        load_dotenv(override=True)
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()

        if not self.provider:
            if self.gemini_key:
                self.provider = "gemini"
            elif self.openai_key:
                self.provider = "openai"
            elif self.groq_key:
                self.provider = "groq"
            else:
                self.provider = "gemini"

        if not self.model:
            if self.provider == "gemini":
                self.model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
            elif self.provider == "openai":
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            elif self.provider == "groq":
                self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def is_available(self) -> bool:
        """Returns True if an API key is available for the configured provider."""
        self._detect_provider_and_keys()
        if self.provider == "gemini":
            return bool(self.gemini_key)
        elif self.provider == "openai":
            return bool(self.openai_key)
        elif self.provider == "groq":
            return bool(self.groq_key)
        return False

    def generate_grounded_answer(
        self, 
        user_question: str, 
        df: pd.DataFrame, 
        source_name: str = "PipelineDemand_Details.csv",
        dataset_description: str = ""
    ) -> Optional[str]:
        """
        Sends user question directly to LLM with complete file context and strict grounding rules.
        """
        if not self.is_available() or df.empty:
            return None

        # Build clean string representation of the dataset
        df_records_str = df.to_string(index=False)
        total_count = len(df)
        cols_str = ", ".join(df.columns.tolist())

        system_instruction = f"""You are an expert Performance Testing Resource Management AI Assistant.
You answer user questions strictly based on the provided dataset from `{source_name}`.

DATASET INFORMATION:
- Source File: `{source_name}`
- Total Records: {total_count}
- Columns: {cols_str}
{f"- Description: {dataset_description}" if dataset_description else ""}

CURRENT DATASET RECORDS:
{df_records_str}

STRICT OPERATIONAL RULES:
1. Answer factually and accurately using ONLY the data records shown above.
2. If the user asks for counts, specific values, status lists, summaries, comparisons, or rankings, perform the calculation accurately from the data.
3. If the user's question cannot be answered from the provided records (e.g. asking about unrelated topics like recipes, code generation, outside companies, weather), politely reply:
   "I couldn't find enough information in the {source_name} data to answer that question."
4. Structure your answer cleanly with GitHub-flavored Markdown:
   - Use bold for key metrics and numbers.
   - Use markdown tables for lists of records when appropriate.
   - Use bullet points for summaries and comparisons.
5. End every response with:
   📊 Source: {source_name}
"""

        prompt = f"User Question: \"{user_question}\""

        try:
            response = self._call_llm(
                system_instruction=system_instruction,
                prompt=prompt,
                temperature=0.1
            )
            if response and response.strip():
                resp_text = response.strip()
                citation = f"📊 Source: {source_name}"
                if citation not in resp_text:
                    resp_text += f"\n\n{citation}"
                return resp_text
        except Exception as e:
            print(f"[LLMClient generate_grounded_answer error]: {e}")
            return None

        return None

    def generate_json_query(self, user_question: str) -> Optional[Dict[str, Any]]:
        """
        Sends the user question to LLM to produce a structured JSON query object.
        """
        if not self.is_available():
            return None

        prompt = f"User Question: \"{user_question}\"\n\nReturn JSON structured query:"

        raw_response = self._call_llm(
            system_instruction=STRUCTURED_QUERY_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.0
        )

        if not raw_response:
            return None

        return self._extract_json(raw_response)

    def _call_llm(self, system_instruction: str, prompt: str, temperature: float = 0.0) -> Optional[str]:
        """Dispatches LLM call to appropriate backend with automatic fallback on model errors."""
        self._detect_provider_and_keys()
        try:
            if self.provider == "gemini":
                return self._call_gemini(system_instruction, prompt, temperature)
            elif self.provider == "openai":
                return self._call_openai(system_instruction, prompt, temperature)
            elif self.provider == "groq":
                return self._call_groq(system_instruction, prompt, temperature)
        except Exception as e:
            print(f"[LLMClient Error] {self.provider}: {e}")
            # If the configured Gemini model is unavailable, retry once with the stable default
            if self.provider == "gemini" and self.model != DEFAULT_GEMINI_MODEL:
                try:
                    return self._call_gemini_with_model(DEFAULT_GEMINI_MODEL, system_instruction, prompt, temperature)
                except Exception as ex2:
                    print(f"[LLMClient Gemini Fallback Error]: {ex2}")
            return None
        return None

    def _call_gemini(self, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        return self._call_gemini_with_model(self.model, system_instruction, prompt, temperature)

    def _call_gemini_with_model(self, model_name: str, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.gemini_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=MAX_OUTPUT_TOKENS
            )
        )
        return response.text if response and response.text else None

    def _call_openai(self, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        import openai
        client = openai.OpenAI(api_key=self.openai_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=MAX_OUTPUT_TOKENS
        )
        return response.choices[0].message.content

    def _call_groq(self, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        from groq import Groq
        client = Groq(api_key=self.groq_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=MAX_OUTPUT_TOKENS
        )
        return response.choices[0].message.content

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON object from text even if enclosed in markdown code fences."""
        try:
            clean_text = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
            clean_text = re.sub(r"^```\s*", "", clean_text, flags=re.MULTILINE)
            clean_text = re.sub(r"```$", "", clean_text, flags=re.MULTILINE).strip()
            
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                json_str = clean_text[start:end+1]
                return json.loads(json_str)
        except Exception:
            pass
        return None
