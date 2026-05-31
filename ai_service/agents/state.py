# ai_service/agents/state.py
from typing import TypedDict, List

class AgentState(TypedDict):
    user_profile: dict
    weather_data: dict
    health_risks: List[str]
    calendar_events: List[str]
    final_summary: str