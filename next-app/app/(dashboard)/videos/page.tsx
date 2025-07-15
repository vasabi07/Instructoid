import { auth } from "@/lib/auth"
import { db } from "@/lib/prisma"
import { headers } from "next/headers"
import VideosList from "@/components/VideosList"




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
        },
        select: {
            id: true,
            title: true,
            createdAt: true
        }
    })

  return (
    <VideosList videos={videos} />
  )
}

export default Videos