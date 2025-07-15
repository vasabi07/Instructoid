import { auth } from "@/lib/auth";
import { db } from "@/lib/prisma";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import CreateVideoForm from "./create-video-form";

const CreateVideo = async () => {
  const session = await auth.api.getSession({
    headers: await headers()
  });

  if (!session) {
    redirect("/auth/login");
  }

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
      
      // Save to database with user session
      await db.video.create({
        data: {
          query: query,
          videoUrl: data.video_key,
          userId: session.user.id,
        },
      });

      return { success: true, data };
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : "An error occurred");
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