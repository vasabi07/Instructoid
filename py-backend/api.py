from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from ingest import upsert_to_qdrant
from pydantic import BaseModel
from utils.r2 import get_file
from langchain_core.messages import HumanMessage
app = FastAPI()
from retriever import retriever
from main import orchestrator_agent
from utils.authMiddleware import AuthMiddleware
import requests
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Be more specific
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class IngestRequest(BaseModel):
    file_key: str  
    
class VideoRequest(BaseModel):
    query: str
    aspect_ratio: str = "horizontal"  # default to horizontal
    video_length: int = 30  # default to 30 seconds

app.add_middleware(AuthMiddleware)


@app.get("/")
async def root():
    return {"message": "Welcome to the Instructoid API!"}


@app.post("/ingest")
async def ingest(request_data: IngestRequest, request: Request):
    """havent handled the response in client side"""
    # Get user from middleware
    user = request.state.user
    user_id = user.get("sub") if user else None
    
    file_key = request_data.file_key
    if not file_key:
        return {"error": "file_key is required in the request body."}
    filename = await get_file(file_key)
    if not filename:
        return {"error": "Failed to retrieve the file."}
    ingestion_status = upsert_to_qdrant(filename)
    if ingestion_status:
        return {"message": "File ingested successfully.", "file": filename, "user_id": user_id}
    else:
        return {"error": "Failed to ingest the file."}
    
@app.post("/chat")
async def chat(query: str, request: Request):
    """Handles the chat query and returns the response."""
    # Get user from middleware
    user = request.state.user
    user_id = user.get("sub") if user else None
    
    if not query:
        return {"error": "Query is required."}
    
    response = retriever(query)
    
    return {"response": response, "user_id": user_id}
@app.post("/create-video")
async def create_video(video_request: VideoRequest, request: Request):
    """Handles the video creation request."""
    # Get user from middleware
    user = request.state.user
    user_id = user.get("sub") if user else None
    
    if not video_request.query:
        return {"error": "Query is required."}
    
    print(f"Creating video for user {user_id}: {video_request.query}")
    print(f"Aspect ratio: {video_request.aspect_ratio}, Length: {video_request.video_length}s")
    
    initial_state = {
        "query": video_request.query,
        "aspect_ratio": video_request.aspect_ratio,
        "video_length": video_request.video_length,
        "messages": []  
    }
    response = await orchestrator_agent.ainvoke(initial_state)
    print(response["video_key"])
    return {
        "video_key": response["video_key"], 
        "message": "Video created successfully.", 
        "user_id": user_id,
        "aspect_ratio": video_request.aspect_ratio,
        "video_length": video_request.video_length
    }
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
