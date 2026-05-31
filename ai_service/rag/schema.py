# ai_service/rag/schema.py
import os
import weaviate


def get_weaviate_client():
    host = os.getenv("WEAVIATE_HOST", "localhost")
    return weaviate.connect_to_custom(
        http_host=host,
        http_port=int(os.getenv("WEAVIATE_HTTP_PORT", "8080")),
        http_secure=False,
        grpc_host=host,
        grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
        grpc_secure=False,
    )
