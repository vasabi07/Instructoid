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
    response = retriever(state["query"])
    state["transcription"] = response.content

    return state

#transcription_node
def TTS_node(state: State)-> State:
    response = openai.audio.speech.create(
        model= "tts-1-hd",
        input=state["transcription"],
        voice = "shimmer"
    )
    
    # Store audio as bytes
    state["audio_data"] = response.content
    return state

#manim_node
async def  manim_node(state: State) -> State:
    timeout_config = httpx.Timeout(
        connect=30.0,    # Connection timeout
        read=360.0,      # Read timeout (6 minutes)
        write=30.0,      # Write timeout
        pool=30.0        # Pool timeout
    )
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        response = await client.post(
            os.environ.get("MANIM_ENDPOINT"),
            json={"query": state["transcription"]}
        )
        if response.status_code == 200:
            video_data = response.json()
            state["video_key"] = video_data.get("video_key", "")
            state["video_data"] = await get_video(state["video_key"])
        else:
            raise Exception(f"Failed to create video: {response.status_code} - {response.text}")
    
    return state

def Stitching_node(state: State) -> State:
    import subprocess, tempfile, os

    # Write video & audio bytes out to temp files
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tv:
        tv.write(state["video_data"])
        video_path = tv.name
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as ta:
        ta.write(state["audio_data"])
        audio_path = ta.name

    try:
        video_size = os.path.getsize(video_path)
        audio_size = os.path.getsize(audio_path)
        print(f"Video size: {video_size}, Audio size: {audio_size}")
        if not video_size or not audio_size:
            raise Exception(f"Empty file: video={video_size}, audio={audio_size}")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-movflags", "+frag_keyframe+empty_moov",  # <-- enables streaming mp4
            "-shortest",
            "-f", "mp4",
            "pipe:1"                                   # <-- write to stdout
        ]
        print("Running:", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, check=False)

        if result.returncode != 0:
            print("ffmpeg stderr:", result.stderr.decode())
            print("ffmpeg stdout:", result.stdout.decode())
            raise Exception(f"ffmpeg failed ({result.returncode})")

        state["final_video_data"] = result.stdout
        print(f"Final video bytes: {len(result.stdout)}")

    finally:
        for p in (video_path, audio_path):
            if os.path.exists(p):
                os.unlink(p)

    return state

async def upload_video_node(state: State) -> State:
    """upload the video to r2"""
    
    result = await upload_video("final_video.mp4", state["final_video_data"])
    state["video_key"] = result["file_key"]
    
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

if __name__ == "__main__":
    response = retriever_node(State(query="What is transformers in attention?"))
    print(response["transcription"])  # Access transcription directly





