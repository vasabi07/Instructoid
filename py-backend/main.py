"""
create a orchestrator agent here that gets users query and use tts node, pass the transcription to manim agent
"""
from langgraph.graph import MessagesState
from retriever import retriever
import openai
import httpx
import os
from langgraph.graph import MessagesState, StateGraph, END
from utils.r2 import get_video, upload_video
class State(MessagesState):
    query: str = ""
    time: str = ""
    transcription: str = ""
    video_data: bytes = b""
    audio_data: bytes = b""
    final_video_data: bytes = b""
    video_key: str = ""


#retriever_node
def retriever_node(state: State) -> State:
    response = retriever(state.query)
    state.transcription = response
    return state

#transcription_node
def TTS_node(state: State)-> State:
    response = openai.audio.speech.create(
        model= "tts-1-hd",
        input=state.transcription,
        voice = "shimmer"
    )
    
    # Store audio as bytes
    state.audio_data = response.content
    return state

#manim_node
async def  manim_node(state: State) -> State:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            os.environ.get("MANIM_ENDPOINT"),
            json={"query": state.transcription}
        )
        if response.status_code == 200:
            video_data = response.json()
            state.video_key = video_data.get("video_key", "")
            state.video_data = await get_video(state.video_key)
        else:
            raise Exception(f"Failed to create video: {response.status_code} - {response.text}")
    
    return state

def Stitching_node(state: State) -> State:
    import subprocess
    import tempfile
    
    # Write both video and audio bytes to temp files
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
        temp_video.write(state.video_data)
        video_path = temp_video.name
    
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
        temp_audio.write(state.audio_data)
        audio_path = temp_audio.name
    
    try:
        # Simple ffmpeg command with temp file inputs
        command = [
            "ffmpeg", "-y",
            "-i", video_path,           # Video from temp file
            "-i", audio_path,           # Audio from temp file
            "-c:v", "copy",             # Copy video codec
            "-c:a", "aac",              # Encode audio as AAC
            "-shortest",                # End when shortest stream ends
            "-f", "mp4", "-"            # Output to stdout as bytes
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            check=True
        )
        
        state.final_video_data = result.stdout
        
    finally:
        # Clean up both temp files
        os.unlink(video_path)
        os.unlink(audio_path)
    
    return state

async def upload_video_node(state: State) -> State:
    """upload the video to r2"""
    
    result = await upload_video("final_video.mp4", state.final_video_data)
    state.video_key = result["file_key"]
    
    return state

workflow = StateGraph(State)
workflow.add_node("retriever", retriever_node)
workflow.add_node("tts", TTS_node)  
workflow.add_node("manim", manim_node)
workflow.add_node("stitching", Stitching_node)
workflow.add_node("upload_video", upload_video_node)
workflow.add_edge("retriever", "tts")
workflow.add_edge("tts", "manim")
workflow.add_edge("manim", "stitching")
workflow.add_edge("stitching", "upload_video")
workflow.add_edge("upload_video", END)
workflow.set_entry_point("retriever")

orchestrator_agent = workflow.compile()





