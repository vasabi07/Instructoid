import { auth } from "@/lib/auth"
import { db } from "@/lib/prisma"
import { headers } from "next/headers"


const Videos = async () => {
    const session  = await auth.api.getSession({
        headers:await headers()
    })
    if (!session) {
        return {"message": "Unauthorized"};
    }
    const user_id = session.user.id;
    const videos = await db.video.findMany({
        where: {
            userId: user_id
        },
        orderBy: {
            createdAt: "desc"
        }
    })

  return (
    <div>{videos && (
        <div className="p-4">
          <h1 className="text-2xl font-bold mb-4">Your Videos</h1>
          <ul className="space-y-2">
            {videos.map((video) => (
              <li key={video.id} className="bg-white/10 p-4 rounded-lg shadow">
                <a href={video.videoUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                  {video.query}
                </a>
                <p className="text-sm text-gray-400 mt-1">Created: {new Date(video.createdAt).toLocaleDateString()}</p>
              </li>
            ))}
          </ul>
        </div>
    )}</div>
  )
}

export default Videos