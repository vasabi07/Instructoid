"use client";

import { useState } from "react";
import { getSession } from "@/lib/auth-client";
import {createVideoFormSchema} from "@/lib/z"
const CreateVideoForm = () => {
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setResponse(null);
    setIsLoading(true);

    const formData = new FormData(e.currentTarget);
    const validationResult = createVideoFormSchema.safeParse({
    query: formData.get("query"),
    aspectRatio: formData.get("aspectRatio"),
    videoLength: parseInt(formData.get("videoLength") as string) || 30,
  });

    if (!validationResult.success) {
      const errors = validationResult.error.issues.map(issue => issue.message).join(", ");
      setError(errors);
      setIsLoading(false);
      return;
    }

    const validatedData = validationResult.data;

    try {
      await getSession({
        fetchOptions: {
          onSuccess: async (ctx) => {
            const jwt = ctx.response.headers.get("set-auth-jwt");
            
            if (!jwt) {
              setError("Failed to get authentication token");
              setIsLoading(false);
              return;
            }

            try {
              // Call Python backend with JWT
              const res = await fetch("http://0.0.0.0:8000/create-video", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${jwt}`,
                },
                body: JSON.stringify({ 
                  query: validatedData.query,
                  aspect_ratio: validatedData.aspectRatio,
                  video_length: validatedData.videoLength
                }),
              });

              if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
              }

              const data = await res.json();

              // Call Next.js API to generate title and save to DB
              const saveRes = await fetch("/api/videos/save", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  query: validatedData.query,
                  video_key: data.video_key,
                }),
              });

              if (!saveRes.ok) {
                throw new Error("Failed to save video metadata");
              }

              const saveData = await saveRes.json();
              setResponse({ ...data, ...saveData });
              
              e.currentTarget.reset();
              
            } catch (fetchErr) {
              setError("Error creating video: " + (fetchErr instanceof Error ? fetchErr.message : "Unknown error"));
            } finally {
              setIsLoading(false);
            }
          },
          onError: () => {
            setError("Failed to get session");
            setIsLoading(false);
          }
        },
      });
    } catch (err) {
      setError("Authentication error: " + (err instanceof Error ? err.message : "Unknown error"));
      setIsLoading(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label
            htmlFor="query"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Enter your query
          </label>
          <textarea
            id="query"
            name="query"
            placeholder="Describe the video you want to create..."
            className="w-full px-4 py-3 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none h-32"
            disabled={isLoading}
            required
          />
        </div>

        <div>
          <label
            htmlFor="aspectRatio"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Aspect Ratio
          </label>
          <select
            id="aspectRatio"
            name="aspectRatio"
            className="w-full px-4 py-3 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            disabled={isLoading}
            required
            defaultValue=""
          >
            <option value="" disabled>Select aspect ratio</option>
            <option value="16:9">Horizontal (Youtube video)</option>
            <option value="9:16">Vertical (Shorts)</option>
            <option value="1:1">Vertical (Instagram)</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="videoLength"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Video Length (seconds)
          </label>
          <input
            type="number"
            id="videoLength"
            name="videoLength"
            min="10"
            max="300"
            defaultValue="30"
            placeholder="30"
            className="w-full px-4 py-3 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            disabled={isLoading}
          />
          <p className="text-sm text-gray-500 mt-1">
            Duration between 10-300 seconds (default: 30)
          </p>
        </div>
        
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-indigo-600 text-white py-3 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <div className="flex items-center justify-center">
              <svg
                className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
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
              Creating Video...
            </div>
          ) : (
            "Create Video"
          )}
        </button>
      </form>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {response && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-green-400"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Video Created Successfully!</h3>
              <div className="mt-2 text-sm text-green-700">
                <pre className="whitespace-pre-wrap overflow-auto max-h-96">
                  {JSON.stringify(response, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default CreateVideoForm;
