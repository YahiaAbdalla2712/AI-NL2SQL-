from qdrant_client import QdrantClient

from embedder import embed_text

QDRANT_CLIENT_URL = "http://localhost:6333"
COLLECTION_NAME = "NL2SQL_schemas"

client = QdrantClient(
    url=QDRANT_CLIENT_URL
) 

def retrieve_schema(
    question: str,
    top_k: int = 5
) -> list[dict]:
    query_vector = embed_text(question)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query = query_vector,
        limit = top_k,
    )

    return [
        point.payload
        for point in results.points
    ]


if __name__ == "__main__":
    question = (
        "Show me the transactions "
        "made by customers in Cairo"
    )

    results = retrieve_schema(
        question=question,
        top_k=5
    )

    print(
        f"\nRetrieved {len(results)} chunks:\n"
    )

    for index, result in enumerate(
        results,
        start=1
    ):
        print("="*70)
        print(f"Result {index}")
        print("="*70)

        print(
            f"Chunk type: {result.get('chunk_type')}"
        )

        print(
            f"Entity: {result.get('entity')}"
        )

        if result.get("column"):
            print(
                f"Column: {result.get('column')}"
            )

        print()
        print(result.get("text"))
        print()    