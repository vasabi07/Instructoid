from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
)

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


query = "What are the main components of the Transformer architecture as illustrated in the diagram?"
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
query_vector = embeddings.embed_query(query)


results = client.query_points(
    collection_name="user_docs_collection",
    query=query_vector,
    limit=3,
).points


context = []
for res in results:
    doc_type = res.payload.get("doc_type")
    if doc_type in ["text", "table"]:
        context.append(res.payload.get("full_text", ""))
    elif doc_type == "image":
        context.append(f"Image summary: {res.payload.get('summary', '')}")

prompt = f"""You are an AI assistant that answers questions based on the provided context.
Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't.
context: {context}
Question: {query}
"""

response = llm.invoke(prompt)


print("LLM Response:")
print(response.content)
print("\nTop 3 retrieved chunks:")
for i, res in enumerate(results):
    print(f"Result {i+1}:")
    print("Score:", res.score)
    print("Summary:", res.payload.get("summary"))
    print("Doc type:", res.payload.get("doc_type"))
    print("Page num:", res.payload.get("page_num"))
    print("---")
