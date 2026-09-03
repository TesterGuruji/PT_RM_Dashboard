"""
Pipeline Demand AI Assistant Package.
Provides natural-language question answering grounded strictly on PipelineDemand_Details.csv.
"""

from .assistant import PipelineAIAssistant, ask_pipeline_assistant

__all__ = ["PipelineAIAssistant", "ask_pipeline_assistant"]
