"""
Unified LLM Client Supporting Google Gemini, OpenAI, and Groq.
Handles structured query generation and natural-language synthesis.
"""

import os
import json
import re
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from .prompts import (
    STRUCTURED_QUERY_SYSTEM_PROMPT,
    RESPONSE_SYNTHESIS_SYSTEM_PROMPT,
    FALLBACK_NOT_FOUND_MESSAGE,
    SOURCE_CITATION
)

load_dotenv()

class LLMClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "").lower()
        self.model = model
        self._detect_provider_and_keys()

    def _detect_provider_and_keys(self):
        """Auto-detects active provider and API key if not explicitly set."""
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
                # Prefer fast lightweight flash models
                self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            elif self.provider == "openai":
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            elif self.provider == "groq":
                self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def is_available(self) -> bool:
        """Returns True if an API key is available for the configured provider."""
        if self.provider == "gemini":
            return bool(self.gemini_key)
        elif self.provider == "openai":
            return bool(self.openai_key)
        elif self.provider == "groq":
            return bool(self.groq_key)
        return False

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

    def generate_natural_response(self, user_question: str, computed_result: Dict[str, Any]) -> str:
        """
        Generates a concise, grounded natural-language response based on computed data results.
        """
        if not self.is_available():
            # Fallback to direct template formatter if LLM is unavailable
            return self._fallback_template_response(user_question, computed_result)

        if computed_result.get("status") == "unsupported" or computed_result.get("empty", False):
            return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}"

        prompt = f"""
User Question: "{user_question}"

Computed Results from PipelineDemand_Details.csv:
{json.dumps(computed_result, indent=2, default=str)}

Please provide a clear, concise natural language answer based STRICTLY on the above computed results.
"""

        response = self._call_llm(
            system_instruction=RESPONSE_SYNTHESIS_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.1
        )

        if not response or FALLBACK_NOT_FOUND_MESSAGE in response:
            return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}"

        # Ensure citation is included
        if SOURCE_CITATION not in response:
            response = f"{response.strip()}\n\n{SOURCE_CITATION}"

        return response

    def _call_llm(self, system_instruction: str, prompt: str, temperature: float = 0.0) -> Optional[str]:
        """Dispatches LLM call to appropriate backend."""
        try:
            if self.provider == "gemini":
                return self._call_gemini(system_instruction, prompt, temperature)
            elif self.provider == "openai":
                return self._call_openai(system_instruction, prompt, temperature)
            elif self.provider == "groq":
                return self._call_groq(system_instruction, prompt, temperature)
        except Exception as e:
            # Handle model deprecation/version fallback if necessary
            if self.provider == "gemini" and ("404" in str(e) or "not found" in str(e).lower()):
                try:
                    # Try fallback model
                    fallback_model = "gemini-1.5-flash" if self.model != "gemini-1.5-flash" else "gemini-2.0-flash"
                    return self._call_gemini_with_model(fallback_model, system_instruction, prompt, temperature)
                except Exception:
                    pass
            print(f"[LLMClient Error] {self.provider}: {e}")
            return None
        return None

    def _call_gemini(self, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        return self._call_gemini_with_model(self.model, system_instruction, prompt, temperature)

    def _call_gemini_with_model(self, model_name: str, system_instruction: str, prompt: str, temperature: float) -> Optional[str]:
        import google.generativeai as genai
        genai.configure(api_key=self.gemini_key)
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature, "max_output_tokens": 1024}
        )
        response = model.generate_content(prompt)
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
            max_tokens=1024
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
            max_tokens=1024
        )
        return response.choices[0].message.content

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extracts JSON object from text even if enclosed in markdown code fences."""
        try:
            # Strip code blocks
            clean_text = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
            clean_text = re.sub(r"^```\s*", "", clean_text, flags=re.MULTILINE)
            clean_text = re.sub(r"```$", "", clean_text, flags=re.MULTILINE).strip()
            
            # Find the first { and last }
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                json_str = clean_text[start:end+1]
                return json.loads(json_str)
        except Exception:
            pass
        return None

    def _fallback_template_response(self, question: str, result: Dict[str, Any]) -> str:
        """Deterministic response formatter when LLM is unavailable."""
        if result.get("status") == "unsupported" or result.get("empty", False):
            return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}"

        op = result.get("operation")
        if op == "count":
            count = result.get("count", 0)
            desc = result.get("description", "matching pipeline demands")
            return f"There are **{count}** {desc}.\n\n{SOURCE_CITATION}"
        elif op == "filter":
            records = result.get("records", [])
            count = len(records)
            if count == 0:
                return f"No matching records found in Pipeline Demand data.\n\n{SOURCE_CITATION}"
            return f"Found **{count}** matching pipeline demand(s).\n\n{SOURCE_CITATION}"
        elif op == "rank":
            rank_data = result.get("rank_data", [])
            if rank_data:
                top_item = rank_data[0]
                return f"**{top_item['name']}** has the highest demand with **{top_item['count']}** records.\n\n{SOURCE_CITATION}"
        elif op == "summary":
            return f"**Pipeline Summary:** Total demands: **{result.get('total_demands')}**, Open: **{result.get('open_demands')}**, Invalid: **{result.get('invalid_demands')}**, Awaiting Confirmation: **{result.get('awaiting_confirmation')}**.\n\n{SOURCE_CITATION}"

        return f"{FALLBACK_NOT_FOUND_MESSAGE}\n\n{SOURCE_CITATION}"
