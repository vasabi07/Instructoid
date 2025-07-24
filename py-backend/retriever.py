import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
import json
import pprint

load_dotenv()

# Pydantic model for structured output
class SegmentedTranscripts(BaseModel):
    intro_transcript: str = Field(description="Introduction segment transcript (5 seconds)")
    main_transcript: str = Field(description="Main content segment transcript (20+ seconds)")
    conclusion_transcript: str = Field(description="Conclusion segment transcript (5 seconds)")

llm = init_chat_model(model="gpt-4o-mini", model_provider="openai")
llm_better = init_chat_model(model="o1-mini", model_provider="openai")

# Create structured output version
structured_llm = llm.with_structured_output(SegmentedTranscripts)

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

def preprocess_query(query: str) -> str:
    """Use LLM to extract the core educational topic from video creation queries"""
    
    extraction_prompt = f"""
Extract the core educational topic from this query, removing any video creation instructions.

Query: "{query}"

Return only the core topic/subject that should be searched for in educational documents.

Examples:
- "create a video on photosynthesis" → "photosynthesis"
- "make a video about Newton's laws of motion" → "Newton's laws of motion"
- "generate a video on organic chemistry reactions" → "organic chemistry reactions"
- "all the laws of gravity" → "all the laws of gravity"

Core topic:"""

    try:
        response = llm.invoke(extraction_prompt)
        cleaned = response.content.strip().strip('"').strip("'")
        
        # Fallback if extraction seems to have failed
        if len(cleaned) < 3 or cleaned.lower() == "core topic":
            return query
            
        print(f"Original query: '{query}' → Cleaned query: '{cleaned}'")
        return cleaned
        
    except Exception as e:
        print(f"Error in query extraction: {e}")
        return query



def retriever(query: str, time: str = "30 seconds") -> dict:
    # Clean up the query for better semantic search
    cleaned_query = preprocess_query(query)
    print(f"Original query: '{query}' → Cleaned query: '{cleaned_query}'")
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vector = embeddings.embed_query(cleaned_query)


    results = client.query_points(
        collection_name="user_docs_collection",
        query=query_vector,
        limit=5,
    ).points

    # Check if we have any relevant results based on similarity score
    # Qdrant returns scores, we can set a minimum threshold
    relevant_results = [res for res in results if res.score > 0.5]  # Lowered threshold for better matching
    
    context = []
    for res in relevant_results:
        doc_type = res.payload.get("doc_type")
        if doc_type in ["text", "table"]:
            context.append(res.payload.get("full_text", ""))
        elif doc_type == "image":
            context.append(f"Image summary: {res.payload.get('summary', '')}")

    # Early return if no relevant context found
    print(f"Found {len(results)} total results, {len(relevant_results)} relevant results")
    pprint.pprint(context)
    if not context or all(not ctx.strip() for ctx in context):
        return {
            "intro_transcript": "I apologize, but I don't have relevant information about this topic in the documents you've uploaded.",
            "main_transcript": "To provide you with accurate educational content, I would need relevant documents or materials that cover this specific topic. Please upload documents related to your query and try again.",
            "conclusion_transcript": "Once you upload relevant documents, I'll be able to create comprehensive educational content based on that information."
        }

    # Calculate timing for each segment
    total_time = int(time.replace(" seconds", "").replace("s", "")) if isinstance(time, str) else time
    intro_time = min(10, total_time // 6)  # 5 seconds max for intro
    main_time = total_time - intro_time - 5  # Main content gets most time
    conclusion_time = 10  # Always 5 seconds for conclusion
    
    segmented_prompt = f"""
You are an expert educational content creator. Based on the provided context and user query, create a comprehensive educational script divided into 3 distinct segments.

**Context:**
{context}

**Topic:** {query}

**Total Duration:** {total_time} seconds
- Segment 1 (Introduction): ~{intro_time} seconds
- Segment 2 (Main Content): ~{main_time} seconds  
- Segment 3 (Conclusion): ~{conclusion_time} seconds

Create a detailed, comprehensive explanation that covers:
1. **Introduction**: Brief overview and key concept introduction
2. **Main Content**: Detailed explanation with examples, processes, or key details from the context
3. **Conclusion**: Summary and key takeaways

**Requirements:**
- Stay strictly within the information given in the context
- Each segment should flow naturally into the next
- Use clear, educational language appropriate for students
- Include specific details and examples from the context
- Make it comprehensive and informative
- Sound human-like and fluent for text-to-speech
- No system messages or disclaimers
- Each segment should be self-contained but part of the whole
"""

    try:
        # Use structured output instead of manual JSON parsing
        segments = structured_llm.invoke(segmented_prompt)
        
        # Convert Pydantic model to dict
        return segments.model_dump()
        
    except Exception as e:
        print(f"Error generating structured output: {e}")
        # Fallback to simple format
        return {
            "intro_transcript": f"Let's explore {query}. This is an important topic that we'll break down step by step.",
            "main_transcript": f"The main concepts of {query} involve understanding the fundamental principles and applications in this field. Based on the available information, we can see that this topic has significant relevance and importance.",
            "conclusion_transcript": f"In summary, {query} is a crucial concept that has wide-ranging applications and importance. Understanding this topic will help you build a strong foundation for further learning."
        }

if __name__ == "__main__":
    query = "who is msdhoni?"
    response = retriever(query)
    print(json.dumps(response, indent=2))


"""
need to create 2 prompts. 
one for video generation and one for answering 
"""