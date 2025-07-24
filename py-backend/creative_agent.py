import os
import asyncio
import subprocess
import tempfile
from typing import List, Tuple

import openai
import httpx
import requests
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langgraph.graph import MessagesState, StateGraph, END
from utils.r2 import upload_video, get_video

# ---------------------- Helper functions ----------------------

async def tts_with_length(text: str) -> Tuple[bytes, float]:
    """Generate TTS and return (audio_bytes, duration_seconds)."""
    import asyncio
    
    def _generate_tts():
        return openai.audio.speech.create(
            model="tts-1-hd", input=text, voice="shimmer"
        ).content
    
    # Run TTS in thread pool for async support
    loop = asyncio.get_event_loop()
    audio_bytes = await loop.run_in_executor(None, _generate_tts)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    # probe duration
    duration = float(
        subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", tmp_path
        ]).strip()
    )
    os.unlink(tmp_path)
    return audio_bytes, duration


async def generate_image_video(content: str, duration: float, aspect: str) -> bytes:
    """Generate optimized image with focused prompt and convert to video."""
    # Use smaller sizes for cost optimization
    size = {"16:9": "1024x1024", "9:16": "1024x1024", "1:1": "1024x1024"}.get(aspect, "1024x1024")
    
    # Generate focused image prompt
    focused_prompt = await generate_focused_image_prompt(content)
    
    img_url = openai.images.generate(
        model="dall-e-3",
        prompt=focused_prompt,
        size=size,
        quality="standard",  # Changed from hd for cost savings
        n=1,
    ).data[0].url
    img_data = requests.get(img_url).content
    
    print(f"📸 Image downloaded: {len(img_data)} bytes")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_file:
        img_file.write(img_data)
        img_path = img_file.name

    try:
        # Determine output resolution based on aspect ratio
        if aspect == "16:9":
            scale = "1920:1080"
        elif aspect == "9:16":
            scale = "1080:1920"
        else:
            scale = "1080:1080"
            
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path,
            "-vf", f"scale={scale}",
            "-t", f"{duration:.3f}",
            "-r", "30",  # Fixed 30fps
            "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p",  # Optimized quality
            "-preset", "fast",  # Faster encoding
            "-movflags", "frag_keyframe+empty_moov", "-f", "mp4", "pipe:1"
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        print(f"✅ Video generated: {len(result.stdout)} bytes, {duration}s")
        return result.stdout
    finally:
        os.unlink(img_path)


def mux_audio_video(video_b: bytes, audio_b: bytes, idx: int) -> str:
    """Mux perfectly‑matched A/V without re‑encoding video."""
    with tempfile.NamedTemporaryFile(suffix=f"_{idx}.mp4", delete=False) as v:
        v.write(video_b); v_path = v.name
    with tempfile.NamedTemporaryFile(suffix=f"_{idx}.mp3", delete=False) as a:
        a.write(audio_b); a_path = a.name
    out_path = tempfile.NamedTemporaryFile(suffix=f"_mux_{idx}.mp4", delete=False).name
    subprocess.run([
        "ffmpeg", "-y", "-i", v_path, "-i", a_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path
    ], check=True)
    os.unlink(v_path); os.unlink(a_path)
    return out_path


def concat_paths(paths: List[str]) -> bytes:
    """Concat clips with re-encoding for compatibility."""
    concat_txt = "\n".join([f"file '{p}'" for p in paths])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(concat_txt); list_path = f.name
    
    # Create temporary output file
    output_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    
    try:
        # Use re-encoding to temporary file instead of pipe
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", output_path
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        
        # Read the output file
        with open(output_path, 'rb') as f:
            video_data = f.read()
        
        print(f"✅ Final video concatenated: {len(video_data)} bytes")
        return video_data
        
    finally:
        # Cleanup
        os.unlink(list_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
        for p in paths: 
            if os.path.exists(p):
                os.unlink(p)

# ---------------------- Creative Content Generation ----------------------

async def generate_creative_content(topic: str, video_length: int) -> dict:
    """Generate creative educational content without relying on user documents."""
    llm = init_chat_model(model="gpt-4o-mini", model_provider="openai")
    
    content_prompt = f"""
You are an expert educational content creator with deep knowledge across all subjects.

Create comprehensive, engaging educational content about: "{topic}"

Requirements:
- Total video duration: {video_length} seconds
- Create an introduction (~5 seconds of narration)
- Create detailed main content (~{video_length - 10} seconds of narration)
- Create a conclusion (~5 seconds of narration)
- Use your extensive knowledge base - be accurate and informative
- Make it engaging and suitable for educational videos
- Include specific examples, facts, and explanations
- Sound natural and conversational for text-to-speech

Return your response in this exact JSON format:
{{
    "intro_transcript": "Introduction text here...",
    "main_transcript": "Detailed main content here...",
    "conclusion_transcript": "Conclusion text here..."
}}
"""

    try:
        response = llm.invoke(content_prompt)
        content_text = response.content.strip()
        
        # Try to parse as JSON
        import json
        try:
            content_data = json.loads(content_text)
            return content_data
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            print("⚠️ JSON parsing failed, using fallback content generation")
            return generate_fallback_content(topic, video_length)
            
    except Exception as e:
        print(f"⚠️ Error in creative content generation: {e}")
        return generate_fallback_content(topic, video_length)


def generate_fallback_content(topic: str, video_length: int) -> dict:
    """Fallback content generation when LLM fails."""
    return {
        "intro_transcript": f"Welcome to our educational video about {topic}. Let's explore this fascinating subject together.",
        "main_transcript": f"The topic of {topic} is fundamental to understanding many concepts in science and education. Through careful study and observation, researchers have discovered important principles that help us understand how {topic} works in our world. These discoveries have practical applications and continue to influence modern thinking.",
        "conclusion_transcript": f"In summary, {topic} is a crucial concept that helps us understand our world better. Thank you for learning with us today."
    }

# ---------------------- Data Models ----------------------
class Segment(BaseModel):
    duration: float
    content: str
    audio_data: bytes = b""
    video_data: bytes = b""

class CreativeOrchestratorState(MessagesState):
    query: str = ""
    video_length: int = 30
    aspect_ratio: str = "16:9"

    intro_transcript: str = ""
    main_transcript: str = ""
    conclusion_transcript: str = ""

    segments: List[Segment] = []
    video_without_subtitles: bytes = b""
    final_video_data: bytes = b""
    video_key: str = ""

# ---------------------- Nodes ----------------------

async def creative_retrieve_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Generate creative content based on the query topic using LLM knowledge."""
    query = state.get('query') or state.query
    video_length = state.get('video_length') or state.video_length
    
    print(f"🎨 Generating creative content for: {query}")
    content_data = await generate_creative_content(query, video_length)
    
    state['intro_transcript'] = content_data["intro_transcript"]
    state['main_transcript'] = content_data["main_transcript"]
    state['conclusion_transcript'] = content_data["conclusion_transcript"]
    
    print("✅ Creative content generated successfully")
    return state


def creative_plan_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Plan the video segments for creative content."""
    main_transcript = state.get('main_transcript') or state.main_transcript
    video_length = state.get('video_length') or state.video_length
    
    llm = init_chat_model(model="gpt-4o-mini", model_provider="openai")
    prompt = (
        f"Split this educational content into 2‑4 narration segments totaling ~{video_length - 10}s. "
        "Each segment should be self-contained but flow naturally together. "
        "Return JSON list of {duration:int, content:str}.\n\n" + main_transcript
    )
    
    class S(BaseModel): 
        duration: int
        content: str
        
    class P(BaseModel): 
        segments: List[S]
        
    try:
        plan = llm.with_structured_output(P).invoke(prompt)
        segments = [Segment(duration=s.duration, content=s.content) for s in plan.segments]
        state['segments'] = segments
        print(f"📋 Planned {len(segments)} segments")
        return state
    except Exception as e:
        print(f"⚠️ Planning error, using fallback: {e}")
        # Fallback: create 2 segments from main content
        content_length = len(main_transcript)
        mid_point = content_length // 2
        
        # Find a good breaking point near the middle
        break_point = main_transcript.find('. ', mid_point)
        if break_point == -1:
            break_point = mid_point
            
        segment1_content = main_transcript[:break_point + 1].strip()
        segment2_content = main_transcript[break_point + 1:].strip()
        
        duration_per_segment = (video_length - 10) // 2
        
        segments = [
            Segment(duration=duration_per_segment, content=segment1_content),
            Segment(duration=duration_per_segment, content=segment2_content)
        ]
        state['segments'] = segments
        return state


async def creative_process_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Process all segments in parallel for better performance"""
    
    segments = state.get('segments') or state.segments
    aspect_ratio = state.get('aspect_ratio') or state.aspect_ratio
    
    async def process_single_segment(segment: Segment, index: int) -> Segment:
        """Process audio and video for a single segment"""
        print(f"🎬 Processing creative segment {index+1}: {segment.content[:50]}...")
        
        # Step 1: Generate audio first to get the exact duration
        audio_data, actual_duration = await tts_with_length(segment.content)
        
        # Step 2: Generate video using the audio duration
        video_data = await generate_image_video(segment.content, actual_duration, aspect_ratio)
        
        # Create updated segment with results
        updated_segment = Segment(
            duration=actual_duration,  # Use actual audio duration for perfect sync
            content=segment.content,
            audio_data=audio_data,
            video_data=video_data
        )
        
        print(f"✅ Completed creative segment {index+1}: {actual_duration:.2f}s")
        return updated_segment
    
    # Process all segments in parallel while maintaining order
    tasks = [
        process_single_segment(segment, i) 
        for i, segment in enumerate(segments)
    ]
    
    # Wait for all segments to complete (order preserved by asyncio.gather)
    processed_segments = await asyncio.gather(*tasks)
    
    state['segments'] = processed_segments
    return state


async def creative_stitch_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Stitch intro + segments + conclusion together with parallel processing"""
    temp_paths = []

    async def create_intro():
        intro_transcript = state.get('intro_transcript') or state.intro_transcript
        query = state.get('query') or state.query
        aspect_ratio = state.get('aspect_ratio') or state.aspect_ratio
        
        # Step 1: Generate audio first to get the exact duration
        intro_aud, intro_len = await tts_with_length(intro_transcript)
        
        # Step 2: Generate video using the audio duration
        intro_vid = await generate_image_video(f"Creative educational introduction about {query} - inspiring, modern, engaging visual", intro_len, aspect_ratio)
        
        return mux_audio_video(intro_vid, intro_aud, 0)

    async def create_conclusion():
        conclusion_transcript = state.get('conclusion_transcript') or state.conclusion_transcript
        query = state.get('query') or state.query
        aspect_ratio = state.get('aspect_ratio') or state.aspect_ratio
        
        # Step 1: Generate audio first to get the exact duration
        concl_aud, concl_len = await tts_with_length(conclusion_transcript)
        
        # Step 2: Generate video using the audio duration
        concl_vid = await generate_image_video(f"Creative educational conclusion about {query} - thoughtful, summary, inspiring finish", concl_len, aspect_ratio)
        
        return mux_audio_video(concl_vid, concl_aud, 999)

    try:
        # Create intro and conclusion in parallel
        intro_task = asyncio.create_task(create_intro())
        conclusion_task = asyncio.create_task(create_conclusion())
        
        # Process segment muxing in parallel
        def mux_segment(segment, index):
            return mux_audio_video(segment.video_data, segment.audio_data, index + 1)
        
        segments = state.get('segments') or state.segments
        loop = asyncio.get_event_loop()
        segment_tasks = [
            loop.run_in_executor(None, mux_segment, segment, i)
            for i, segment in enumerate(segments)
        ]
        
        # Wait for all to complete
        intro_path = await intro_task
        segment_paths = await asyncio.gather(*segment_tasks)
        conclusion_path = await conclusion_task
        
        # Build final path list in correct order
        all_paths = [intro_path] + segment_paths + [conclusion_path]
        temp_paths.extend(all_paths)
        
        # Concatenate all videos WITHOUT subtitles first
        final_video_data = concat_paths(all_paths)
        
        # Store the video without subtitles
        state['video_without_subtitles'] = final_video_data
        return state
        
    except Exception as e:
        # Cleanup on error
        for path in temp_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise e


async def creative_subtitle_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Add subtitles to the completed creative video with precise timing"""
    
    print("🎬 Generating creative video subtitles with precise timing...")
    
    # Get the video without subtitles
    video_without_subs = state.get('video_without_subtitles') or state.video_without_subtitles
    
    # Build precise subtitle timing using actual segment durations
    segments = state.get('segments') or state.segments
    intro_transcript = state.get('intro_transcript') or state.intro_transcript
    conclusion_transcript = state.get('conclusion_transcript') or state.conclusion_transcript
    
    # Generate SRT with actual measured durations
    srt_content = await generate_subtitles(segments, intro_transcript, conclusion_transcript)
    
    print("🎬 Adding subtitles to creative video...")
    final_video_with_subs = add_subtitles_to_video(video_without_subs, srt_content)
    
    state['final_video_data'] = final_video_with_subs
    
    # Clean up intermediate video data to save memory
    if 'video_without_subtitles' in state:
        del state['video_without_subtitles']
    
    return state


async def creative_upload_node(state: CreativeOrchestratorState) -> CreativeOrchestratorState:
    """Upload the final creative video."""
    final_video_data = state.get('final_video_data') or state.final_video_data
    res = await upload_video("creative_educational_video.mp4", final_video_data)
    state['video_key'] = res["file_key"]
    return state

# ---------------------- Shared Functions ----------------------

async def generate_focused_image_prompt(content: str) -> str:
    """Generate a focused, specific image prompt from educational content."""
    llm = init_chat_model(model="gpt-4o-mini", model_provider="openai")
    
    prompt_instruction = f"""
You are an expert at creating focused, clean image prompts for educational illustrations.

Given this educational content: "{content}"

Create a SINGLE, specific image prompt that:
1. Shows ONE main concept or scene from the content
2. Is clean, minimal, and uncluttered
3. Focuses on the most important visual element
4. Uses simple, clear visual language
5. Avoids text, labels, or complex diagrams
6. Should be creative and visually appealing

Examples:
- Content: "Newton observed an apple falling from a tree due to gravity"
  → Prompt: "A single red apple falling from a green apple tree, with a person in historical clothing observing from below, simple outdoor scene"

- Content: "Photosynthesis occurs when sunlight hits green leaves"
  → Prompt: "A single green leaf with golden sunlight rays hitting it, clean white background"

- Content: "The water cycle involves evaporation from oceans"
  → Prompt: "Blue ocean water with transparent water vapor rising upward, minimal clean illustration"

Generate ONLY the focused image prompt (no explanations):"""

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: llm.invoke(prompt_instruction)
        )
        focused_prompt = response.content.strip()
        print(f"🎨 Generated focused prompt: {focused_prompt[:60]}...")
        return focused_prompt
    except Exception as e:
        print(f"⚠️ Error generating focused prompt: {e}")
        # Fallback to a simple prompt
        return f"Creative educational illustration showing {content[:50]}"


async def generate_subtitles(segments: List[Segment], intro_transcript: str, conclusion_transcript: str) -> str:
    """Generate SRT subtitle file from segments with proper timing"""
    
    def format_srt_time(seconds):
        """Format seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def split_text_for_subtitles(text: str, max_chars: int = 60) -> List[str]:
        """Split text into subtitle-friendly chunks"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_chars and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    srt_content = []
    current_time = 0.0
    subtitle_index = 1
    
    # Process intro
    if intro_transcript and intro_transcript.strip():
        intro_chunks = split_text_for_subtitles(intro_transcript)
        intro_duration = 5.0  # Default
        chunk_duration = intro_duration / len(intro_chunks)
        
        for chunk in intro_chunks:
            end_time = current_time + chunk_duration
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{format_srt_time(current_time)} --> {format_srt_time(end_time)}")
            srt_content.append(chunk)
            srt_content.append("")
            
            current_time = end_time
            subtitle_index += 1
    
    # Process main segments
    for segment in segments:
        text_chunks = split_text_for_subtitles(segment.content)
        chunk_duration = segment.duration / len(text_chunks)
        
        for chunk in text_chunks:
            end_time = current_time + chunk_duration
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{format_srt_time(current_time)} --> {format_srt_time(end_time)}")
            srt_content.append(chunk)
            srt_content.append("")
            
            current_time = end_time
            subtitle_index += 1
    
    # Process conclusion
    if conclusion_transcript and conclusion_transcript.strip():
        conclusion_chunks = split_text_for_subtitles(conclusion_transcript)
        conclusion_duration = 5.0  # Default
        chunk_duration = conclusion_duration / len(conclusion_chunks)
        
        for chunk in conclusion_chunks:
            end_time = current_time + chunk_duration
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{format_srt_time(current_time)} --> {format_srt_time(end_time)}")
            srt_content.append(chunk)
            srt_content.append("")
            
            current_time = end_time
            subtitle_index += 1
    
    return "\n".join(srt_content)


def add_subtitles_to_video(video_data: bytes, srt_content: str) -> bytes:
    """Add burned-in subtitles to video using ffmpeg"""
    
    # Write video to temp file
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
        video_file.write(video_data)
        video_path = video_file.name
    
    # Write SRT to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix=".srt", delete=False, encoding='utf-8') as srt_file:
        srt_file.write(srt_content)
        srt_path = srt_file.name
    
    # Output with subtitles
    output_path = tempfile.NamedTemporaryFile(suffix="_with_subs.mp4", delete=False).name
    
    try:
        # Escape the SRT path for Windows compatibility
        escaped_srt_path = srt_path.replace('\\', '\\\\').replace(':', '\\:')
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={escaped_srt_path}:force_style='FontName=Arial,FontSize=15,PrimaryColour=&Hffffff,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1'",
            "-c:a", "copy", "-preset", "fast", "-crf", "23",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, check=True)
        
        # Read the final video with subtitles
        with open(output_path, 'rb') as f:
            final_video = f.read()
            
        print(f"✅ Creative video subtitles added: {len(final_video)} bytes")
        return final_video
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Creative subtitle error: {e.stderr.decode() if e.stderr else str(e)}")
        # Return original video if subtitle addition fails
        print("Returning original creative video without subtitles")
        return video_data
        
    finally:
        # Cleanup
        for path in [video_path, srt_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)

# ---------------------- Creative Graph ----------------------
creative_flow = StateGraph(CreativeOrchestratorState)
creative_flow.add_node("creative_retrieve", creative_retrieve_node)
creative_flow.add_node("creative_plan", creative_plan_node)
creative_flow.add_node("creative_process", creative_process_node)
creative_flow.add_node("creative_stitch", creative_stitch_node)
creative_flow.add_node("creative_subtitle", creative_subtitle_node)
creative_flow.add_node("creative_upload", creative_upload_node)
creative_flow.add_edge("creative_retrieve", "creative_plan")
creative_flow.add_edge("creative_plan", "creative_process")
creative_flow.add_edge("creative_process", "creative_stitch")
creative_flow.add_edge("creative_stitch", "creative_subtitle")
creative_flow.add_edge("creative_subtitle", "creative_upload")
creative_flow.add_edge("creative_upload", END)
creative_flow.set_entry_point("creative_retrieve")
creative_agent = creative_flow.compile()

# ---------------------- CLI test ----------------------
if __name__ == "__main__":
    async def _test_creative():
        st = CreativeOrchestratorState(
            query="quantum physics and wave-particle duality", 
            video_length=45, 
            aspect_ratio="16:9"
        )
        res = await creative_agent.ainvoke(st)
        print("Creative Video key:", res.get('video_key', 'not found'))
    
    asyncio.run(_test_creative())
