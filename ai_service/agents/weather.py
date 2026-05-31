# ai_service/agents/weather.py
import os
from langchain_openai import ChatOpenAI
from .state import AgentState

def weather_agent_node(state: AgentState):
    profile = state["user_profile"]
    weather = state["weather_data"]
    temp = weather.get("temp")
    min_temp = profile.get("min_temp")
    max_temp = profile.get("max_temp")

    range_status = "bilinmiyor"
    if temp is not None and min_temp is not None and max_temp is not None:
        if min_temp > max_temp:
            min_temp, max_temp = max_temp, min_temp
        if min_temp <= temp <= max_temp:
            range_status = "tercih aralığında"
        else:
            dist = min(abs(temp - min_temp), abs(temp - max_temp))
            range_status = "tercih aralığının çok dışında" if dist >= 8 else "tercih aralığının dışında"
    
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    Kullanıcı Tercihleri:
    - İdeal sıcaklık: {profile.get('min_temp')}-{profile.get('max_temp')}°C
    - Sevdiği hava: {profile.get('favorite_weather', [])}
    - Sevmediği hava: {profile.get('disliked_weather', [])}
    - Sevdiği aktiviteler: {profile.get('activities', [])}

    Mevcut Hava:
    - Sıcaklık: {weather.get('temp')}°C
    - Durum: {weather.get('condition')}
    - AQI: {weather.get('aqi_status')} ({weather.get('aqi_value')})
    - UV: {weather.get('uv_index')}
    - Aralık analizi: {range_status}

    Kurallar:
    - 1 cümle yaz.
    - Eğer sıcaklık tercih aralığı dışındaysa bunu açık ve net şekilde olumsuz tonla belirt.
    - Eğer aralık içindeyse olumlu tonla belirt.
    """
    response = llm.invoke(prompt)
    return {"final_summary": f"Hava Analizi: {response.content}"}