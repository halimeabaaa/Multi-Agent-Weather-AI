# ai_service/agents/health.py
import os
from openai import OpenAI
from rag.schema import get_weaviate_client
from .state import AgentState

def generate_query_embedding(text):
    """Kullanıcının durumunu aratabilmek için sorgu vektörü üretir"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def health_agent_node(state: AgentState):
    profile = state["user_profile"]
    weather = state["weather_data"]
    diseases = profile.get("diseases", [])
    
    risks = []
    
    if not diseases:
        return {"health_risks": risks}
        
    client = get_weaviate_client()
    
    try:
        collection = client.collections.get("HealthGuideline")
        
        for disease in diseases:
            search_query = f"Hastalık: {disease} Tetikleyici: {weather.get('pollen', 'Normal')}"
            query_vector = generate_query_embedding(search_query)
            
            # 👈 v4 SDK'ya uygun near_vector araması
            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=1
            )
            
            # 👈 v4 nesne okuma yapısı (obj.properties)
            for obj in response.objects:
                recommendation_doc = obj.properties.get("recommendation")
                if recommendation_doc:
                    risks.append(recommendation_doc)
                    
    finally:
        client.close()
        
    return {"health_risks": risks}