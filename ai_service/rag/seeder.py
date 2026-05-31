# ai_service/rag/seeder.py
import os
from openai import OpenAI
from rag.schema import get_weaviate_client
from dotenv import load_dotenv
from pathlib import Path

backend_env_path = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=backend_env_path)
# Bizim sığlığı kıracak gerçek dünya tıbbi kılavuz simülasyonlarımız
MEDICAL_DATA = [
    {
        "condition": "Alerjik Rinit",
        "trigger": "Yüksek Polen",
        "recommendation": "Klinik Kılavuz: Yüksek polen dönemlerinde alerjik rinit hastalarının dış ortam aktivitelerini kısıtlaması, dışarı çıkarken HEPA filtreli maske kullanması ve eve dönüşte mutlaka duş alarak polenleri vücudundan uzaklaştırması klinik olarak önerilir."
    },
    {
        "condition": "Astım",
        "trigger": "Aşırı Soğuk",
        "recommendation": "WHO Astım Rehberi: 5°C altındaki sıcaklıklar bronşiyal spazmları tetikler. Astım hastalarının dışarı çıkarken atkı ile ağızlarını kapatarak havayı ısıtarak solumaları ve kurtarıcı inhalerlerini yanlarında bulundurmaları şarttır."
    }
]

def generate_embedding(text):
    """Metni yapay zekanın anlayacağı 1536 boyutlu bir sayı dizisine (Vektöre) çevirir"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def seed_database():
    client = get_weaviate_client()
    try:
        collection = client.collections.get("HealthGuideline")
        
        print("Tıbbi dökümanlar vektörleştiriliyor ve Weaviate'e yükleniyor...")
        
        # ai_service/rag/seeder.py içindeki ilgili alan:

        for item in MEDICAL_DATA:
            # Aratacağımız ana metni birleştirip vektörünü çıkarıyoruz
            combined_text = f"Hastalık: {item['condition']} Tetikleyici: {item['trigger']}"
            vector = generate_embedding(combined_text)
            
            # 👈 ESKİSİ: collection.insert(
            # 👈 YENİSİ: collection.data.insert( olarak güncellendi
            collection.data.insert(
                properties={
                    "condition": item["condition"],
                    "trigger": item["trigger"],
                    "recommendation": item["recommendation"]
                },
                vector=vector
            )
            print(f"👉 {item['condition']} kılavuzu başarıyla eklendi.")
            
        print("✅ Yükleme başarıyla tamamlandı!")
    finally:
        client.close()

if __name__ == "__main__":
    seed_database()