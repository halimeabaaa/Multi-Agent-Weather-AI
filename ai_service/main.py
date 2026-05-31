# ai_service/main.py
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from agents.chat_agent import chat_agent_chain
from agents.graph import agent_chain

backend_env_path = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=backend_env_path)

app = FastAPI(title="Weather AI - Multi Agent Service")


class UserProfileSchema(BaseModel):
    username: Optional[str] = "Kullanıcı"
    email: Optional[str] = ""
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    diseases: List[str] = []
    favorite_weather: List[str] = []
    disliked_weather: List[str] = []
    activities: List[str] = []
    blood_type: Optional[str] = ""
    medications: List[str] = []
    allergies: List[str] = []
    health_notes: Optional[str] = ""


class WeatherDataSchema(BaseModel):
    temp: Optional[float] = None
    condition: str = "bilinmiyor"
    pollen: Optional[str] = None
    aqi_value: Optional[int] = None
    aqi_status: Optional[str] = None
    uv_index: Optional[float] = None
    hourly: List[dict] = []
    weather_alerts: List[dict] = []
    city: Optional[str] = None


class AgentInput(BaseModel):
    user_profile: UserProfileSchema
    weather_data: WeatherDataSchema


@app.post("/api/v1/agent/run")
async def run_agent_workflow(payload: AgentInput):
    try:
        initial_state = {
            "user_profile": payload.user_profile.model_dump(),
            "weather_data": payload.weather_data.model_dump(),
            "health_risks": [],
            "calendar_events": [],
            "final_summary": "",
        }
        output = agent_chain.invoke(initial_state)
        summary = output.get("final_summary")
        if not summary:
            raise HTTPException(status_code=502, detail="AI summary is empty")
        return {"success": True, "result": summary}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class ReferenceDateTimeSchema(BaseModel):
    iso_date: str = ""
    today_label: str = ""
    now_time: str = ""
    timezone: str = "Europe/Istanbul"


class ChatInput(BaseModel):
    user_profile: UserProfileSchema
    weather_data: WeatherDataSchema
    calendar_events: List[str] = []
    reference_datetime: ReferenceDateTimeSchema = ReferenceDateTimeSchema()
    history: List[ChatMessageSchema]


@app.post("/api/v1/chat")
async def run_chat_assistant(payload: ChatInput):
    try:
        formatted_messages = []
        for msg in payload.history:
            if msg.role == "user":
                formatted_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted_messages.append(AIMessage(content=msg.content))

        initial_state = {
            "messages": formatted_messages,
            "user_profile": payload.user_profile.model_dump(),
            "weather_data": payload.weather_data.model_dump(),
            "calendar_events": payload.calendar_events,
            "reference_datetime": payload.reference_datetime.model_dump(),
            "response": "",
        }
        output = chat_agent_chain.invoke(initial_state)
        return {"success": True, "response": output["response"]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class GenerateSummaryInput(BaseModel):
    user_id: int
    username: Optional[str] = "Kullanıcı"
    profile: dict
    health: List[str]
    weather: dict
    calendar_events: List[str] = []


@app.post("/api/v1/generate-summary")
async def generate_summary_endpoint(payload: GenerateSummaryInput):
    try:
        initial_state = {
            "user_profile": {
                "username": payload.username,
                "min_temp": payload.profile.get("min_temp"),
                "max_temp": payload.profile.get("max_temp"),
                "diseases": payload.health,
                "favorite_weather": payload.profile.get("favorite_weather", []),
                "disliked_weather": payload.profile.get("disliked_weather", []),
                "activities": payload.profile.get("activities", []),
                "blood_type": payload.profile.get("blood_type", ""),
                "medications": payload.profile.get("medications", []),
                "allergies": payload.profile.get("allergies", []),
                "health_notes": payload.profile.get("health_notes", ""),
            },
            "weather_data": payload.weather,
            "health_risks": payload.health,
            "calendar_events": payload.calendar_events,
            "final_summary": "",
        }
        output = agent_chain.invoke(initial_state)
        summary = output.get("final_summary")
        if not summary:
            raise HTTPException(status_code=502, detail="AI summary is empty")

        risk_level = "high" if output.get("health_risks") else "low"
        return {"risk": risk_level, "summary": summary}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))