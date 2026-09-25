from langchain_ollama import OllamaEmbeddings

EMBEDDING_MODEL = "nomic-embed-text"

def get_embedder():
    return OllamaEmbeddings(
        model=EMBEDDING_MODEL
    )

def embed_text(text: str)->list[float]:
    embedder = get_embedder()
    return embedder.embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    embedder = get_embedder()
    return embedder.embed_documents(texts)


#test
if __name__ == "__main__":
    vector = embed_text(
        "Show me transactions made by customers in Cairo"
    )

    print(f"Embedding dimensions: {len(vector)}")
    print(vector[:10])
