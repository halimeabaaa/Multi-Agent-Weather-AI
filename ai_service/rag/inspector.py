# ai_service/rag/inspector.py
from rag.schema import get_weaviate_client

def inspect_database():
    client = get_weaviate_client()
    try:
        collection = client.collections.get("HealthGuideline")
        
        # Veritabanındaki nesneleri (vektörleriyle birlikte) çekiyoruz
        response = collection.iterator(include_vector=True)
        
        print("\n--- WEAVIATE VERİTABANI İÇERİĞİ ---")
        for obj in response:
            print(f"\n🆔 ID: {obj.uuid}")
            print(f"🤒 Hastalık: {obj.properties.get('condition')}")
            print(f"⚡ Tetikleyici: {obj.properties.get('trigger')}")
            print(f"📜 Kılavuz: {obj.properties.get('recommendation')}")
            
            # Vektörün ilk 5 sayısını gösterelim (1536 tanenin hepsi terminali doldurmasın diye)
            vector = obj.vector.get("default")
            if vector:
                print(f"🔢 Vektör (İlk 5 Boyut): {vector[:5]}... (Toplam Uzunluk: {len(vector)})")
            print("-" * 35)
            
    finally:
        client.close()

if __name__ == "__main__":
    inspect_database()