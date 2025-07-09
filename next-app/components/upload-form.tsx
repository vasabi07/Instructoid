"use client";

import {getSignedURL,saveDocument} from "@/app/create/actions";


import { useEffect, useState } from "react";
//consider saving to db after processing the file in backend
//handle response from backend after processing the file
//handle error cases in file upload and processing
//show error messages to user in the form
//show success message to user in the form
//show loading state while file is being processed
const UploadForm = () => {
    const [file,setFile] = useState<File | undefined>(undefined);
    const [url, setUrl] = useState<string | undefined>(undefined);
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>)=>{
        setFile(e.target.files?.[0])
      
    }
    const HandleSubmit= async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!file) {
            console.error("No file selected");
            return;
        }
        const file_name = file.name;
        const {signedUrl,file_key} = await getSignedURL(file_name);
        console.log(signedUrl);
        if (!signedUrl || !signedUrl) {
            console.error("Failed to get signed URL");
            return;
        }

        try {
            const response = await fetch(signedUrl, {
            method: "PUT",
            body: file,
            headers: {
                "Content-Type": file.type
            }
        })
        console.log("File upload response:", response);
        } catch (error) {
            console.error("Error uploading file:", error);
            return
        }
        
        const upload_to_db = await saveDocument(file_name, file_key, file.size, file.type);
        if (upload_to_db && "fileKey" in upload_to_db) {
            const key = upload_to_db.fileKey;
            try {
                const response = await fetch("http://0.0.0.0:8000/ingest", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        file_key: key})
                });
                if (!response.ok) {
                    throw new Error("Failed to ingest file");
                }
            } catch (error) {
                
            }
        } else {
            console.error("Failed to save file metadata to database", upload_to_db);
        }
        setFile(undefined);
        setUrl(undefined);
        e.currentTarget.reset();

    }
    useEffect(() => {
        if (file) {
            const newUrl = URL.createObjectURL(file);
            setUrl(newUrl);
            // Clean up to avoid memory leaks
            return () => URL.revokeObjectURL(newUrl);
        } else {
            setUrl(undefined);
        }
    }, [file]);
  return (
    <form onSubmit={HandleSubmit}>
        <label htmlFor="file-upload" className="block text-2xl font-large text-gray-700">
          Upload a file
        </label>
        <input type="file" id="file-upload" name="file-upload" className="mt-1 p-4 block w-full text-sm text-gray-900 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500" onChange={handleChange} />
        {url && file && (
            <div className="mt-2">
                <p className="text-sm text-gray-500">Selected file: {file.name}</p>
                <img src={url} alt="Preview" className="mt-2 max-w-xs rounded-md shadow-md" />
            </div>
        )}
        <button type="submit" className="mt-2 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          Submit
        </button>
    </form>
  )
}

export default UploadForm

//create a form with single field to upload a file
//the form should have a submit button
//file should be shown visually in the form
//on submit first uploaded file reaches python backend for vectorDB to ingest it
//on success, the file should be uploaded to R2 bucket