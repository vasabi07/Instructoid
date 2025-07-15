from langchain_core.tools import tool
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings

from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

import pprint
import os
from dotenv import load_dotenv

load_dotenv()
llm = init_chat_model(model="gpt-4.1-mini",model_provider="openai")
llm_better = init_chat_model(model="o4-mini-2025-04-16", model_provider="openai")

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)



def retriever(query: str, time: str = "30 seconds") -> str:
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

    answering_prompt = f"""You are an AI assistant that answers questions based on the provided context.
    Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't.
    context: {context}
    Question: {query}
    """

    
    transcription_prompt = f"""
You are a precise AI assistant tasked with generating a natural-sounding transcription based on the provided context and the user's query.

Your job is to generate a concise, coherent, and easy-to-speak script that will be converted directly into audio using text-to-speech. The response should:

- Stay strictly within the information given in the context.
- Sound human-like and fluent.
- Fit naturally within the given time limit.
- Avoid technical jargon unless explicitly required by the question.
- Not include any system messages, disclaimers, or instructions.

Respond only with the transcription text.

---
Context:
{context}

Question:
{query}

Target duration:
{time}
"""


    return llm_better.invoke(transcription_prompt)

if __name__ == "__main__":
    query = "how to write a document?"
    response = retriever(query)
    pprint.pprint(response.content)


"""
need to create 2 prompts. 
one for video generation and one for answering 
"""