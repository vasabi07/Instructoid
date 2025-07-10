import { auth } from "@/lib/auth"
import { db } from "@/lib/prisma"
import { headers } from "next/headers"


const Documents =async () => {
    const session  = await auth.api.getSession({
        headers:await headers()
    })
    if (!session) {
        return {"message": "Unauthorized"};
    }
    const user_id = session.user.id;
    const documents = await db.document.findMany({
        where: {
            userId: user_id
        },
        orderBy: {
            createdAt: "desc"
        }
    })

  return (
    <div>{documents && (
        <div className="p-4">
          <h1 className="text-2xl font-bold mb-4">Your Documents</h1>
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li key={doc.id} className="bg-white/10 p-4 rounded-lg shadow">
                <a href={`https://your-bucket-url/${doc.fileKey}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                  {doc.fileName}
                </a>
                <p className="text-sm text-gray-400 mt-1">{doc.fileType} - {Math.round(doc.fileSize / 1024)} KB</p>
              </li>
            ))}
          </ul>
        </div>
    )}</div>
  )
}

export default Documents