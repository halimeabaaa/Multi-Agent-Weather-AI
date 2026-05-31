# ai_service/agents/chat_agent.py
import os
from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun # 🎯 İnternet arama motorumuz
from rag.schema import get_weaviate_client
from rag.seeder import generate_embedding

# Chat sürecinin durum (State) yapısı
class ChatState(TypedDict):
    messages: List[BaseMessage]
    user_profile: dict
    weather_data: dict
    calendar_events: List[str]
    reference_datetime: dict
    response: str

def chat_rag_node(state: ChatState):
    """Kullanıcının sorusuna göre hem RAG (Weaviate), hem Web Search yapan ve profili filtreleyen ana düğüm"""
    messages = state["messages"]
    profile = state["user_profile"]
    weather = state["weather_data"]
    calendar_events = state.get("calendar_events") or []
    ref_dt = state.get("reference_datetime") or {}

    last_user_message = messages[-1].content
    current_username = profile.get("username", "Kullanıcı")
    
    # --- 1. KATMAN: RAG (Tıbbi Veritabanı Sorgusu) ---
    client = get_weaviate_client()
    context_medical_doc = ""
    try:
        collection = client.collections.get("HealthGuideline")
        query_vector = generate_embedding(last_user_message)
        weaviate_response = collection.query.near_vector(near_vector=query_vector, limit=1)
        
        if weaviate_response.objects:
            context_medical_doc = weaviate_response.objects[0].properties.get("recommendation", "")
    except Exception as e:
        print(f"Weaviate RAG hatası (Göz ardı ediliyor): {e}")
    finally:
        client.close()

    # --- 2. KATMAN: WEB SEARCH (İnternette Canlı Arama) 🎯 ---
    web_search_results = ""
    try:
        # Arama motorumuzu ateşliyoruz
        search_tool = DuckDuckGoSearchRun()
        
        # Arama kalitesini artırmak için kullanıcının sorusunu anlık hava durumu bağlamıyla genişletip internete soruyoruz
        search_query = f"{last_user_message} hava durumu {weather.get('temp')} derece {weather.get('condition')}"
        web_search_results = search_tool.invoke(search_query)
    except Exception as e:
        print(f"Web Search arama hatası (Göz ardı ediliyor): {e}")

    # --- 3. KATMAN: LLM & PROFIL FILTRESI (Beyin Katmanı) ---
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.environ.get("OPENAI_API_KEY"))

    calendar_block = (
        "\n".join(f"- {ev}" for ev in calendar_events)
        if calendar_events
        else "- Kayıtlı gelecek etkinlik yok."
    )
    hourly = weather.get("hourly") or []
    hourly_block = (
        "\n".join(
            f"- {h.get('time')}: {h.get('temp')}°C, {h.get('condition')}, yağış %{h.get('pop_percent', 0)}"
            for h in hourly[:12]
        )
        if hourly
        else "- Saatlik tahmin yok."
    )
    alerts = weather.get("weather_alerts") or []
    alerts_block = (
        "\n".join(f"- {a.get('title')}: {a.get('message')}" for a in alerts)
        if alerts
        else "- Aktif hava uyarısı yok."
    )

    profile_block = f"""
    Kullanıcı Adı: {current_username}
    E-posta: {profile.get('email') or 'Belirtilmemiş'}
    Sağlık Hassasiyetleri/Hastalıklar: {profile.get('diseases', [])}
    Kan Grubu: {profile.get('blood_type') or 'Belirtilmemiş'}
    Kullandığı İlaçlar: {profile.get('medications', [])}
    Alerjiler: {profile.get('allergies', [])}
    Ek Sağlık Notları: {profile.get('health_notes') or 'Yok'}
    Düzenli Aktiviteler: {profile.get('activities', [])}
    İdeal Sıcaklık Aralığı: {profile.get('min_temp')}-{profile.get('max_temp')}°C
    Sevdiği Havalar: {profile.get('favorite_weather', [])}
    Sevmediği Havalar: {profile.get('disliked_weather', [])}

    Takvim / Planlanan Etkinlikler ({len(calendar_events)} adet):
    {calendar_block}

    Saatlik Hava Tahmini:
    {hourly_block}

    Hava Uyarıları:
    {alerts_block}
    """

    today_label = ref_dt.get("today_label") or "bilinmiyor"
    iso_today = ref_dt.get("iso_date") or ""
    now_time = ref_dt.get("now_time") or ""
    tz_name = ref_dt.get("timezone") or "Europe/Istanbul"

    system_instruction = f"""
    Sen {current_username} adlı kullanıcının kişisel Sağlık, Hava ve Aktivite Asistanısın.
    Aşağıdaki profil veritabanı kaydı SADECE bu kullanıcıya aittir — başka kullanıcıya aitmiş gibi davranma.

    📅 REFERANS TARİH (SUNUCU — KESİNLİKLE BUNU KULLAN, KENDİ TAHMİNİNİ YAPMA):
    - Bugün: {today_label} (ISO: {iso_today})
    - Şu an: {now_time} ({tz_name})
    - Etkinlik sorularında YALNIZCA aşağıdaki takvim listesindeki Tarih satırlarına bak.
    - Kullanıcı belirli bir gün sorarsa (ör. 30 Mayıs), listede o ISO tarih veya Türkçe tarih geçen tüm etkinlikleri say.
    - Listede olmayan tarih için "kayıtlı etkinlik yok" de; başka bir günü "bugün" sanma.

    🔒 TAM PROFİL KAYDI (kendi bilgilerini sorarsa buradan cevapla):
    {profile_block}

    Kendi bilgilerini sorduğunda (kan grubum, ilaçlarım, alerjim, aktivitelerim vb.):
    - Yukarıdaki profilden doğrudan ve net cevap ver.
    - "Bilmiyorum" deme; profilde yoksa "profilinde kayıtlı değil" de.
    
    🌍 MEVCUT CANLI HAVA DURUMU ({weather.get('city', 'Konum')}):
    - Sıcaklık: {weather.get('temp')}°C
    - Hava Durumu: {weather.get('condition')}
    - Polen Seviyesi: {weather.get('pollen', 'Normal')}
    - AQI Hava Kalitesi: {weather.get('aqi_value', 'Bilinmiyor')} ({weather.get('aqi_status', 'Bilinmiyor')})
    - UV Endeksi: {weather.get('uv_index', 'Bilinmiyor')}
    
    📚 İNTERNETTEN ALINAN CANLI ARAMA BİLGİLERİ (WEB SEARCH):
    {web_search_results}
    
    🏥 KLİNİK KILAVUZ BİLGİSİ (Varsa):
    {context_medical_doc}
    
    ⚠️ ÖNEMLİ TALİMATLAR:
    1. Kullanıcı profilindeki NEGATİF ve POZİTİF tercihlere kesinlikle sadık kal. Örneğin; hava 40 dereceyse ve kullanıcı güneşli havalardan NEFRET ediyorsa, internet arama sonuçları aksini söylese bile KESİNLİKLE dışarıda koşu, yürüyüş veya açık hava aktivitesi önerme! Bunun yerine evde/salonda gölge boksu, klimalı alan aktiviteleri tavsiye et.
    2. Gelen internet arama sonuçlarını (Web Search) filtreden geçirerek kullanıcının durumuna uyarla.
    3. Kullanıcıya doğrudan ismiyle ({current_username}) samimi bir şekilde hitap et.
    4. Şefkatli, motive edici, kısa ve Türkçe bir yanıt üret.
    5. Genel tavsiye verme; mutlaka bu kullanıcının ilaç, alerji, aktivite, takvim etkinlikleri ve saatlik hava verisine özel bağla.
    6. Etkinlik veya plan sorulursa takvim listesindeki ilgili tarihteki etkinlikleri tam tarih ve saatle anlat.
    7. "Bugün", "yarın" veya ay/gün adı kullanırken yukarıdaki REFERANS TARİH ile takvim satırlarındaki Tarih alanını eşleştir; model bilginden tarih uydurma.
    """
    
    # Konuşma geçmişini (Hafızayı) ve yeni talimatları birleştirip modele gönderiyoruz
    all_messages = [{"role": "system", "content": system_instruction}]
    for msg in messages:
        if isinstance(msg, HumanMessage):
            all_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            all_messages.append({"role": "assistant", "content": msg.content})
            
    ai_response = llm.invoke(all_messages)
    
    return {"messages": [AIMessage(content=ai_response.content)], "response": ai_response.content}

# Chat grafiğini örüyoruz
chat_workflow = StateGraph(ChatState)
chat_workflow.add_node("chat_rag", chat_rag_node)
chat_workflow.set_entry_point("chat_rag")
chat_workflow.add_edge("chat_rag", END)

chat_agent_chain = chat_workflow.compile()