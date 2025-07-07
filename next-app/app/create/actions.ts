"use server"
import { r2 } from "@/lib/r2Client"
import { PutObjectCommand } from "@aws-sdk/client-s3"
import {getSignedUrl} from "@aws-sdk/s3-request-presigner"
import { auth } from "@/lib/auth";     
import { headers } from "next/headers";
import {v4 as uuid4} from "uuid";
import { db } from "@/lib/prisma";
const createFileKey = (user_id: string,fileName: string) => {

    const uniqueId = uuid4(); 
   const safeName = fileName.replace(/[^a-zA-Z0-9.\-_]/g, "_");
    return `${safeName}_${user_id}.${uniqueId}`;

}
export const getSignedURL =async (file_name:string) => {
    const session  = await auth.api.getSession({
        headers:await headers()
    })
    if (!session) {
        return {"message": "Unauthorized"};
    }
    const file_key = createFileKey(session.user.id,file_name);
    const putObjectCommand = new PutObjectCommand({
        Bucket: process.env.R2_BUCKET,
        Key: file_key
    });

    const signedUrl = await getSignedUrl(r2, putObjectCommand, {
        expiresIn: 60, 
    });
  return {"message": "Hello from the backend, this is a signed URL endpoint.", "signedUrl": signedUrl, "file_key": file_key};
}

export const saveDocument = async (file_name: string, file_key: string, file_size: number, file_type: string) => {
     const session  = await auth.api.getSession({
        headers:await headers()
    })
    if (!session) {
        return {"message": "Unauthorized"};
    }
    const user_id = session.user.id;
    const document = await db.document.create({
        data: {
            userId: user_id,
            fileName: file_name,
            fileKey: file_key,
            fileSize: file_size,
            fileType: file_type
        }
    })

    return document;
}

