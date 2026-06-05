import ollama
from ollama import chat
import chromadb

llm_model = "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16"
client = chromadb.PersistentClient(path="data/chroma/chroma_db")
collection = client.get_collection(name="guidelines")

query = "how to manage acute asthma attack?"

results = collection.query(
    query_texts=[query],
    include=["documents", "metadatas"],
    n_results=3
)

rag_response = chat(
    model=llm_model,
    messages=[
        {
            "role": "system",
            "content": (
                "You classify triage urgency only."
                "You do not diagnose."
                "You do not prescribe treatment."
                "Use retrieved guidelines only as supporting context."
                "Return structured urgency, rationale, confidence, sources, disclaimer."
            )
        },
        {
            "role": "user",
            "content": (
                f"Question: {query}\n\n"
                "Retrieved Guidelines:\n" +
                "\n\n".join(
                    f"- {doc} (Source: {meta['source']}, Page: {meta['page_number']})"
                    for doc, meta in zip(results["documents"][0], results["metadatas"][0])
                )
            )
        }
    ]
)

print(rag_response.message.content)