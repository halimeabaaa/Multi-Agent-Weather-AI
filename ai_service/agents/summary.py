# ai_service/agents/summary.py
import os
from langchain_openai import ChatOpenAI
from .state import AgentState


def summary_agent_node(state: AgentState):
    profile = state["user_profile"]
    weather = state["weather_data"]
    weather_analysis = state["final_summary"]
    health_risks = ", ".join(state["health_risks"]) if state["health_risks"] else "Belirgin risk kaydı yok"
    calendar_events = state.get("calendar_events") or []
    calendar_block = (
        "\n".join(f"- {ev}" for ev in calendar_events)
        if calendar_events
        else "Yakın takvimde kayıtlı gelecek etkinlik yok."
    )
    event_count = len(calendar_events)

    hourly = weather.get("hourly") or []
    hourly_block = (
        "\n".join(
            f"- {h.get('time')}: {h.get('temp')}°C, {h.get('condition')} "
            f"(yağış ihtimali %{h.get('pop_percent', 0)})"
            for h in hourly[:12]
        )
        if hourly
        else "Saatlik tahmin yok."
    )
    alerts = weather.get("weather_alerts") or []
    alerts_block = (
        "\n".join(f"- [{a.get('title')}]: {a.get('message')}" for a in alerts)
        if alerts
        else "Saatlik bazda acil hava uyarısı yok."
    )

    min_temp = profile.get("min_temp")
    max_temp = profile.get("max_temp")
    temp = weather.get("temp")
    username = profile.get("username") or "kullanıcı"

    range_rule = "Tercih aralığı bilgisi eksik."
    if min_temp is not None and max_temp is not None and temp is not None:
        if min_temp > max_temp:
            min_temp, max_temp = max_temp, min_temp
        if min_temp <= temp <= max_temp:
            range_rule = (
                f"Sıcaklık {temp}°C, kullanıcının tercih aralığı [{min_temp}, {max_temp}] içinde. "
                "Olumlu ve motive edici konuş."
            )
        else:
            delta = min(abs(temp - min_temp), abs(temp - max_temp))
            if delta >= 8:
                range_rule = (
                    f"Sıcaklık {temp}°C, tercih aralığı [{min_temp}, {max_temp}] dışında ve fark yüksek ({delta}°C). "
                    "Net uyarı ver; açık hava aktivitesini sınırla."
                )
            else:
                range_rule = (
                    f"Sıcaklık {temp}°C, tercih aralığı [{min_temp}, {max_temp}] dışında (fark {delta}°C). "
                    "Dengeli ama temkinli ol."
                )

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
Sen {username} adlı kullanıcıya özel kişisel sağlık ve hava asistanısın. Genel geçer cümleler KULLANMA.

Hava analizi: {weather_analysis}
Sağlık kayıtları: {health_risks}
Mevcut hava: {temp}°C, {weather.get('condition')}
Sıcaklık kuralı: {range_rule}

Kullanıcı profili (bireysel veriler — mutlaka kullan):
- Sevdiği hava: {profile.get('favorite_weather', [])}
- Sevmediği hava: {profile.get('disliked_weather', [])}
- Aktiviteler: {profile.get('activities', [])}
- Hastalık/hassasiyet: {profile.get('diseases', [])}
- Kan grubu: {profile.get('blood_type') or 'belirtilmemiş'}
- İlaçlar: {profile.get('medications', [])}
- Alerjiler: {profile.get('allergies', [])}
- Sağlık notları: {profile.get('health_notes') or 'yok'}

Takvim — toplam {event_count} gelecek etkinlik (HEPSİNİ say, isim ve saatleriyle an):
{calendar_block}

Saatlik hava (önümüzdeki saatler):
{hourly_block}

Tedbir uyarıları (varsa özete mutlaka yansıt):
{alerts_block}

Kurallar:
- Türkçe, 4-6 cümle, samimi ama net.
- Kullanıcıya adıyla veya "sen" diye hitap et.
- İlaç, alerji, kan grubu veya aktivite varsa en az birine doğrudan atıf yap.
    - Takvimde {event_count} etkinlik varsa tam sayıyı söyle; her birinin adını ve saatini mümkünse tek tek an.
    - Yağış uyarısı varsa tedbir cümlelerini özete ekle (şemsiye, plan değişikliği vb.).
- "Dikkatli olun", "genel olarak" gibi belirsiz ifadelerden kaçın; somut öneri ver.
"""
    response = llm.invoke(prompt)
    return {"final_summary": response.content}
