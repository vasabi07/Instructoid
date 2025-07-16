"use client";

import { getSignedURL, saveDocument } from "@/app/create/actions";
import { getSession } from "@/lib/auth-client";
import { useEffect, useState } from "react";

const UploadForm = () => {
  const [file, setFile] = useState<File | undefined>(undefined);
  const [url, setUrl] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0]);
    setSuccess(null);
    setError(null);
  };

  const HandleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSuccess(null);
    setError(null);

    if (!file) {
      setError("No file selected");
      return;
    }
    setLoading(true);
    try {
      const file_name = file.name;
      const { signedUrl, file_key } = await getSignedURL(file_name);
      if (!signedUrl || !file_key) {
        setError("Failed to get signed URL");
        setLoading(false);
        return;
      }
      const uploadRes = await fetch(signedUrl, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type,
        },
      });
      if (!uploadRes.ok) {
        setError("Error uploading file to storage");
        setLoading(false);
        return;
      }
      const upload_to_db = await saveDocument(
        file_name,
        file_key,
        file.size,
        file.type
      );
      if (upload_to_db && "fileKey" in upload_to_db) {
        const key = upload_to_db.fileKey;
        try {
          await getSession({
            fetchOptions: {
              onSuccess: async (ctx) => {
                const jwt = ctx.response.headers.get("set-auth-jwt");
                
                try {
                  const response = await fetch("http://0.0.0.0:8000/ingest", {
                    method: "POST",
                    headers: {
                      "authorization": `Bearer ${jwt}`,
                      "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ file_key: key }),
                  });
                  if (!response.ok) {
                    setError("Failed to ingest file in backend");
                    setLoading(false);
                    return;
                  }
                  const data = await response.json();
                  if (data && data.message) {
                    setSuccess("Ingestion successful!");
                  } else {
                    setError("Ingestion failed: " + (data.error || "Unknown error"));
                  }
                } catch (fetchErr) {
                  setError("Error contacting backend for ingestion");
                  setLoading(false);
                }
              },
            },
          });
        } catch (err) {
          setError("Error getting session");
          setLoading(false);
        }
      } else {
        setError("Failed to save file metadata to database");
      }
    } catch (error) {
      setError("Unexpected error: " + (error as Error).message);
    } finally {
      setLoading(false);
      setFile(undefined);
      setUrl(undefined);
      e.currentTarget.reset();
    }
  };

  useEffect(() => {
    if (file) {
      const newUrl = URL.createObjectURL(file);
      setUrl(newUrl);
      return () => URL.revokeObjectURL(newUrl);
    } else {
      setUrl(undefined);
    }
  }, [file]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-indigo-50 to-white p-4">
      <form
        onSubmit={HandleSubmit}
        className="bg-white shadow-xl rounded-lg p-8 w-full max-w-md border border-gray-200"
      >
        <h2 className="text-3xl font-bold text-indigo-700 mb-6 text-center">
          Upload a File for Ingestion
        </h2>
        <label
          htmlFor="file-upload"
          className="block text-lg font-medium text-gray-700 mb-2"
        >
          Choose a file
        </label>
        <input
          type="file"
          id="file-upload"
          name="file-upload"
          className="mb-4 block w-full text-sm text-gray-900 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
          onChange={handleChange}
        />
        {url && file && (
          <div className="mb-4 flex flex-col items-center">
            <p className="text-sm text-gray-500 mb-2">
              Selected file: <span className="font-semibold">{file.name}</span>
            </p>
            {file.type.startsWith("image/") && (
              <img
                src={url}
                alt="Preview"
                className="mt-2 max-w-xs rounded-md shadow-md border border-gray-200"
              />
            )}
          </div>
        )}
        <button
          type="submit"
          className="w-full mt-2 inline-flex items-center justify-center px-4 py-2 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-60"
          disabled={loading}
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg
                className="animate-spin h-5 w-5 mr-2 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8z"
                ></path>
              </svg>
              Processing...
            </span>
          ) : (
            "Submit"
          )}
        </button>
        {success && (
          <div className="mt-4 p-3 rounded bg-green-100 text-green-800 text-center border border-green-200">
            {success}
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 rounded bg-red-100 text-red-800 text-center border border-red-200">
            {error}
          </div>
        )}
      </form>
    </div>
  );
};

export default UploadForm;
