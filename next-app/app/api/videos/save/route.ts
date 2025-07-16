import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { db } from "@/lib/prisma";
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    // Get session
    const session = await auth.api.getSession({
      headers: request.headers
    });

    if (!session) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { query, video_key } = await request.json();

    if (!query || !video_key) {
      return NextResponse.json({ error: "Missing query or video_key" }, { status: 400 });
    }

    // Generate title using OpenAI
    const openai_response = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: "You are a helpful assistant that crafts concise titles. return just the title." },
        { role: "user", content: `Create a short title for: ${query}` },
      ],
      max_tokens: 12,
    });

    let title = "";
    if (openai_response.choices.length > 0) {
      const titleContent = openai_response.choices[0].message.content;
      title = titleContent ? titleContent.trim() : "";
    }

    // Save to database
    const video = await db.video.create({
      data: {
        query: query,
        videoUrl: video_key,
        title: title,
        userId: session.user.id,
      },
    });

    return NextResponse.json({ 
      success: true, 
      video: { id: video.id, title, query } 
    });
    
  } catch (error) {
    console.error("Error saving video:", error);
    return NextResponse.json(
      { error: "Failed to save video metadata" },
      { status: 500 }
    );
  }
}
