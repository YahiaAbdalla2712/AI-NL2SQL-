import json
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import(
    Distance,
    VectorParams,
    PointStruct,
)

from embedder import embed_documents

QDRANT_CLIENT_URL = "http://localhost:6333"
COLLECTION_NAME = "NL2SQL_schemas"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_PATH = Path(
    PROJECT_ROOT
    / "app"
    / "data"
    / "semantic_chunks"
    / "semantic_chunks.json"
)

def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(
            f"Semantic chunks not found: {CHUNKS_PATH}"
        )
    with CHUNKS_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def get_client() -> QdrantClient:
    return QdrantClient(
        url = QDRANT_CLIENT_URL
    )    

def create_data_collection(
    client: QdrantClient,
    vector_size: int
):
    existing = [
        collection.name
        for collection in client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size = vector_size,
                distance=Distance.COSINE,
            ),
        )

        print(
            f"Created collection: {COLLECTION_NAME}"
        )
    else:
        print(
            f"Collection already exists: {COLLECTION_NAME}"
        )    


def index_chunks():

    chunks = load_chunks()

    print(
        f"Loaded {len(chunks)} chunks."
    )

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    print("Generating embeddings...")

    vectors = embed_documents(texts)

    print(
        f"Generated {len(vectors)} embeddings."
    )

    vector_size = len(vectors[0])

    client = get_client()

    create_data_collection(
        client,
        vector_size
    )

    points = []

    for index, (chunk, vector) in enumerate(
        zip(chunks, vectors)
    ):
        points.append(
            PointStruct(
                id=index,
                vector=vector,
                payload=chunk
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points = points,
    )    

    print(
        f"Indexed {len(points)} chunks "
        f"into {COLLECTION_NAME}"
    )

if __name__ == "__main__":
    index_chunks() 