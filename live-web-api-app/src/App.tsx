/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useEffect, useRef, useState } from "react";
import "./App.scss";
import { LiveAPIProvider } from "./contexts/LiveAPIContext";
import SidePanel from "./components/side-panel/SidePanel";
import { Altair } from "./components/altair/Altair";
import VirtualTeacher from "./components/VirtualTeacher/VirtualTeacher"; // Import the new component
import FlipCameraAndroidIcon from "@mui/icons-material/FlipCameraAndroid";

import ControlTray from "./components/control-tray/ControlTray";
import cn from "classnames";
import { Box, IconButton } from "@mui/material"; // Import Box for layout
import { useWebcam } from "./hooks/use-webcam";
import { useScreenCapture } from "./hooks/use-screen-capture";
import VoiceSelector from "./components/settings-dialog/VoiceSelector";

const API_KEY = process.env.REACT_APP_GEMINI_API_KEY as string;
if (typeof API_KEY !== "string") {
  throw new Error("set REACT_APP_GEMINI_API_KEY in .env");
}

const host = "generativelanguage.googleapis.com";
const uri = `wss://${host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent`;

function App() {
  // this video reference is used for displaying the active stream, whether that is the webcam or screen capture
  // feel free to style as you see fit
  const videoRef = useRef<HTMLVideoElement>(null);
  // const videoStreams = [useWebcam(), useScreenCapture()];
  // const [webcam, screenCapture] = videoStreams;
  // console.log(webcam, screenCapture,"wwwwwwwwwwwwwwwwwwwsswebcam, sssssssssssssssssssssssscreenCapture")

  // either the screen capture, the video or null, if null we hide it
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("environment");
  const [streamType, setStreamType] = useState<"camera" | "screen" | "unknown">("unknown");

  function detectStreamType(stream: MediaStream): "camera" | "screen" | "unknown" {
    const videoTrack = stream.getVideoTracks()[0];
    if (!videoTrack) return "unknown";

    const settings = videoTrack.getSettings();
    const label = videoTrack.label.toLowerCase();

    // DisplaySurface is defined only for screen captures
    if ((settings as any).displaySurface) {
      return "screen";
    }

    if (
      label.includes("screen") ||
      label.includes("display") ||
      label.includes("window") ||
      label.includes("monitor")
    ) {
      return "screen";
    }

    if (
      label.includes("camera") ||
      label.includes("facetime") ||
      label.includes("webcam") ||
      label.includes("back") ||
      label.includes("front") ||
      label.includes("hd") ||
      label.includes("usb")
    ) {
      return "camera";
    }
    return "camera";
  }


  const handleStreamChange = (stream: MediaStream | null) => {
    setVideoStream(stream);
    if (stream) {
      setStreamType(detectStreamType(stream));
    } else {
      setStreamType("unknown");
    }
  };


  const startCamera = async (mode: "user" | "environment") => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setVideoStream(stream);
      setFacingMode(mode);

    } catch (err) {
      console.error("Error accessing camera:", err);
    }
  };

  const flipCamera = () => {
    const newMode = facingMode === "user" ? "environment" : "user";
    startCamera(newMode);
  };


  return (
    <div className="App">
      <LiveAPIProvider url={uri} apiKey={API_KEY}>
        <div className="streaming-console">
          <Box sx={{
            display: { xs: 'none', md: 'block' }
          }}>
            <SidePanel />
          </Box>          <main>
            <Box sx={{
              display: 'flex',
              flexDirection: 'column', // Stack elements vertically
              flexGrow: 1,            // Take available space
              overflow: 'hidden',     // Prevent content overflow
              position: 'relative',   // For ControlTray positioning
              width: '100%',          // Ensure full width
            }}>

              <video
                className={cn("stream-preview", {
                  hidden: !videoStream, // Hide if no stream
                })}
                ref={videoRef}
                autoPlay
                playsInline
                muted // Important for autoplay
                style={{
                  position: 'absolute',
                  top: '10px',
                  right: '10px',
                  width: '450px', // Adjust size as needed
                  height: 'auto',
                  zIndex: 10, // Above VT content
                  border: '2px solid black',
                  borderRadius: '8px',
                  backgroundColor: 'black', // Background for when stream loads
                }}
              />

              {videoStream && streamType === "camera" && (
                <IconButton
                  onClick={flipCamera}
                  sx={{
                    position: "absolute",
                    top: 12,
                    right: 12,
                    zIndex: 20,
                    backgroundColor: "rgba(255,255,255,0.8)",
                    border: "1px solid #ccc",
                    "&:hover": {
                      backgroundColor: "rgba(255,255,255,1)",
                    },
                  }}
                >
                  <FlipCameraAndroidIcon />
                </IconButton>
              )}
              <VirtualTeacher />
              <ControlTray
                videoRef={videoRef}
                supportsVideo={true}
                onVideoStreamChange={handleStreamChange}
                enableEditingSettings={true}
              >
                {/* Additional custom buttons can go here */}
              </ControlTray>

            </Box>
          </main>

        </div>
      </LiveAPIProvider>
    </div>
  );
}

export default App;

