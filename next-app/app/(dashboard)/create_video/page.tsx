import { auth } from "@/lib/auth";
import { db } from "@/lib/prisma";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import CreateVideoForm from "./create-video-form";
import OpenAI from "openai";
import { title } from "process";
const CreateVideo = async () => {
  const session = await auth.api.getSession({
    headers: await headers()
  });

  if (!session) {
    redirect("/auth/login");
  }
  const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

  const createVideo = async (formData: FormData) => {
    "use server";
    
    const query = formData.get("query") as string;
    
    if (!query?.trim()) {
      throw new Error("Please enter a query");
    }

    try {
      const res = await fetch("http://0.0.0.0:8000/create-video", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();

      const openai_response = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
      { role: "system",  content: "You are a helpful assistant that crafts concise titles. return just the title." },
      { role: "user",    content: `Create a short title for: ${query}` },
            ],
    max_tokens: 12,
        });

      let title = "";
      if (openai_response.choices.length > 0) {
        const titleContent = openai_response.choices[0].message.content;
        title = titleContent ? titleContent.trim() : "";
      }
      // Save to database with user session
      await db.video.create({
        data: {
          query: query,
          videoUrl: data.video_key,
          title: title,
          userId: session.user.id,
        },
      });

      return { success: true, data };
    } catch (error) {
      return { success: false, data: { error: error instanceof Error ? error.message : "An error occurred" } };
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6 text-center">
            Create Video
          </h1>
          <CreateVideoForm createVideoAction={createVideo} />
        </div>
      </div>
    </div>
  );
};

export default CreateVideo;