from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ingest import get_file, upsert_to_qdrant
from pydantic import BaseModel

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, or specify a list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

class IngestRequest(BaseModel):
    file_key: str  # URL of the file to be ingested
    


@app.get("/")
async def root():
    return {"message": "Welcome to the Instructoid API!"}

@app.post("/ingest")
async def ingest(request: IngestRequest):
    """havent handled the response in client side"""
    file_key = request.file_key
    if not file_key:
        return {"error": "file_key is required in the request body."}
    filename = await get_file(file_key)
    if not filename:
        return {"error": "Failed to retrieve the file."}
    ingestion_status = upsert_to_qdrant(filename)
    if ingestion_status:
        return {"message": "File ingested successfully.", "file": filename}
    else:
        return {"error": "Failed to ingest the file."}
    



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
