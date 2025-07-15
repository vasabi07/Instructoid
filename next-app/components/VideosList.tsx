// app/videos/VideoList.tsx
"use client";

import { useState } from "react";

import { stream_video, download_video } from "@/app/create/actions";

export interface VideoItem {
  id: string;
  title: string | null;
  createdAt: Date | string;
}

export default function VideoList({ videos }: { videos: VideoItem[] }) {
  const [streamUrl, setStreamUrl]   = useState<string | null>(null);

  const handlePlay = async (id: string) => {
    const url = await stream_video(id);
    if (typeof url === "string") {
      setStreamUrl(url);
    } else {
      setStreamUrl(null);
    }
  };

  const handleDownload = async (id: string) => {
  const url = await download_video(id);
  if (typeof url === "string") {
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `video-${id}.mp4`; 
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
};

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Your Videos</h1>
      <ul className="space-y-2">
        {videos.map((video) => (
          <li
            key={video.id}
            className="bg-white/10 p-4 rounded-lg shadow flex justify-between items-center"
          >
            <div>
              <p className="text-xl">{video.title}</p>
              <p className="text-sm text-gray-400 mt-1">
                Created: {new Date(video.createdAt).toLocaleString()}
              </p>
            </div>
            <div className="space-x-2">
              <button
                onClick={() => handlePlay(video.id)}
                className="btn"
              >
                ▶️ Play
              </button>
              <button
                onClick={() => handleDownload(video.id)}
                className="btn"
              >
                ⬇️ Download
              </button>
            </div>
          </li>
        ))}
      </ul>

      {/* Video player */}
      {streamUrl && (
        <div className="mt-6">
          <video controls src={streamUrl} className="w-full" />
        </div>
      )}
    </div>
  );
}
