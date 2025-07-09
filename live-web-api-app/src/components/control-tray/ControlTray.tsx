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

import cn from "classnames";
import { memo, ReactNode, RefObject, useEffect, useRef, useState } from "react";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { UseMediaStreamResult } from "../../hooks/use-media-stream-mux";
import { useScreenCapture } from "../../hooks/use-screen-capture";
import { useWebcam } from "../../hooks/use-webcam";
import { AudioRecorder } from "../../lib/audio-recorder";
import AudioPulse from "../audio-pulse/AudioPulse";
import "./control-tray.scss";
import SettingsDialog from "../settings-dialog/SettingsDialog";
import VoiceSelector from "../settings-dialog/VoiceSelector";
import FlipCameraAndroidIcon from '@mui/icons-material/FlipCameraAndroid';

export type ControlTrayProps = {
  videoRef: RefObject<HTMLVideoElement>;
  children?: ReactNode;
  supportsVideo: boolean;
  onVideoStreamChange?: (stream: MediaStream | null) => void;
  enableEditingSettings?: boolean;
};

type MediaStreamButtonProps = {
  isStreaming: boolean;
  onIcon: string;
  offIcon: string;
  start: () => Promise<any>;
  stop: () => any;
};

/**
 * button used for triggering webcam or screen-capture
 */
const MediaStreamButton = memo(
  ({ isStreaming, onIcon, offIcon, start, stop }: MediaStreamButtonProps) =>
    isStreaming ? (
      <button className="action-button" onClick={stop}>
        <span className="material-symbols-outlined">{onIcon}</span>
      </button>
    ) : (
      <button className="action-button" onClick={start}>
        <span className="material-symbols-outlined">{offIcon}</span>
      </button>
    )
);

function ControlTray({
  videoRef,
  children,
  onVideoStreamChange = () => { },
  supportsVideo,
  enableEditingSettings,
}: ControlTrayProps) {
  const videoStreams = [useWebcam(), useScreenCapture()];
  const [activeVideoStream, setActiveVideoStream] =
    useState<MediaStream | null>(null);
  const [videoInputDevices, setVideoInputDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [webcam, screenCapture] = videoStreams;
  const [inVolume, setInVolume] = useState(0);
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [muted, setMuted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [photoData, setPhotoData] = useState<string | null>(null);
  const [isFrontCamera, setIsFrontCamera] = useState(true);
  const cameraVideoRef = useRef<HTMLVideoElement>(null);
  const renderCanvasRef = useRef<HTMLCanvasElement>(null);
  const connectButtonRef = useRef<HTMLButtonElement>(null);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user');
  const { client, connected, connect, disconnect, volume } =
    useLiveAPIContext();

  useEffect(() => {
    // This effect runs whenever cameraStream changes.
    if (cameraStream && cameraVideoRef.current) {
      // If we have a stream and a video element, connect them.
      cameraVideoRef.current.srcObject = cameraStream;
      cameraVideoRef.current.play().catch(err => {
        // It's good practice to catch potential errors from play()
        console.error("Video play failed:", err);
      });
    } else if (!cameraStream && cameraVideoRef.current) {
      // If the stream is gone, clean up the video element.
      cameraVideoRef.current.srcObject = null;
    }
  }, [cameraStream]); // The dependency array is key!

  const initializeCamera = async (mode: 'user' | 'environment') => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
    }
    const constraints: MediaStreamConstraints = {
      video: { facingMode: mode }, // REMOVED: width and height constraints
      audio: false,
    };
    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream;
        await cameraVideoRef.current.play();
      }
      setCameraStream(stream);
    } catch (err) {
      console.error('Error initializing camera:', err);
      alert('Could not access the camera. Please check permissions.');
    }
  };

  const cleanupCamera = () => {
    // Stop all tracks on the stream to release the camera hardware.
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => {
        track.stop();
      });
    }
    // Clear the state variable, which will trigger the useEffect to clean the video element.
    setCameraStream(null);
    // Clear any captured photo data.
    setPhotoData(null);
  };

  const switchCamera = async () => {
    setPhotoData(null);
    const newFacingMode = facingMode === 'user' ? 'environment' : 'user';
    setFacingMode(newFacingMode);
    await initializeCamera(newFacingMode);
  };

  const takePhoto = async () => {
    if (!cameraVideoRef.current || !cameraStream) return;

    const video = cameraVideoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg');
      setPhotoData(dataUrl);
      if (connected) {
        const base64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
        client.sendRealtimeInput([{ mimeType: "image/jpeg", data: base64 }]);
      }
    }
  };

  useEffect(() => {
    const updateIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    updateIsMobile();
    window.addEventListener('resize', updateIsMobile);
    return () => window.removeEventListener('resize', updateIsMobile);
  }, []);

  useEffect(() => {
    if (!connected && connectButtonRef.current) {
      connectButtonRef.current.focus();
    }
  }, [connected]);
  useEffect(() => {
    document.documentElement.style.setProperty(
      "--volume",
      `${Math.max(5, Math.min(inVolume * 200, 8))}px`
    );
  }, [inVolume]);

  useEffect(() => {
    const onData = (base64: string) => {
      client.sendRealtimeInput([
        {
          mimeType: "audio/pcm;rate=16000",
          data: base64,
        },
      ]);
    };

    // iOS specific audio initialization
    const initAudio = async () => {
      if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !muted) {
        try {
          // Create a new audio context
          const audioContext = new AudioContext();
          
          // Create a dummy oscillator node to ensure audio context starts
          const oscillator = audioContext.createOscillator();
          oscillator.connect(audioContext.destination);
          oscillator.start();
          oscillator.stop();
          
          // Request audio permissions
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
              channelCount: 1,
              sampleRate: 16000
            }
          });
          
          // Create a source node from the stream
          const source = audioContext.createMediaStreamSource(stream);
          
          // Create gain node to control volume
          const gainNode = audioContext.createGain();
          gainNode.gain.value = 0; // Set to 0 to prevent echo
          
          // Connect stream to gain node
          source.connect(gainNode);
          gainNode.connect(audioContext.destination);
        } catch (error) {
          console.error('iOS audio initialization failed:', error);
        }
      }
    };

    if (connected && !muted && audioRecorder) {
      initAudio();
      audioRecorder.on("data", onData).on("volume", setInVolume).start();
    } else {
      audioRecorder.stop();
    }
    return () => {
      audioRecorder.off("data", onData).off("volume", setInVolume);
    };
  }, [connected, client, muted, audioRecorder]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = activeVideoStream;
    }

    let timeoutId = -1;

    function sendVideoFrame() {
      const video = videoRef.current;
      const canvas = renderCanvasRef.current;

      if (!video || !canvas) {
        return;
      }

      const ctx = canvas.getContext("2d")!;
      canvas.width = video.videoWidth * 0.25;
      canvas.height = video.videoHeight * 0.25;
      if (canvas.width + canvas.height > 0) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        const base64 = canvas.toDataURL("image/jpeg", 1.0);
        const data = base64.slice(base64.indexOf(",") + 1, Infinity);
        client.sendRealtimeInput([{ mimeType: "image/jpeg", data }]);
      }
      if (connected) {
        timeoutId = window.setTimeout(sendVideoFrame, 1000 / 0.5);
      }
    }
    if (connected && activeVideoStream !== null) {
      requestAnimationFrame(sendVideoFrame);
    }
    return () => {
      clearTimeout(timeoutId);
    };
  }, [connected, activeVideoStream, client, videoRef]);

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((devices) => {
      const videoInputs = devices.filter(device => device.kind === "videoinput");
      setVideoInputDevices(videoInputs);
      if (videoInputs.length > 0) {
        setSelectedDeviceId(videoInputs[0].deviceId);
      }
    });
  }, []);

  const changeStreams = (next?: UseMediaStreamResult) => async () => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoInputs = devices.filter(device => device.kind === "videoinput");
    setVideoInputDevices(videoInputs);

    if (next) {
      const constraints =
        next === webcam && selectedDeviceId
          ? { video: { deviceId: { exact: selectedDeviceId } }, audio: false }
          : undefined;

      console.log(constraints, "constraints constraints")
      const mediaStream = await next.start(constraints);

      setActiveVideoStream(mediaStream);
      onVideoStreamChange(mediaStream);
    } else {
      setActiveVideoStream(null);
      onVideoStreamChange(null);
    }

    videoStreams.filter((msr) => msr !== next).forEach((msr) => msr.stop());
  };

  const stopAndCleanupCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
    if (cameraVideoRef.current) {
      cameraVideoRef.current.srcObject = null;
    }
    setPhotoData(null);
  };

  const handleConnectClick = async () => {
    if (connected) {
      disconnect();
    } else {
      // This is the crucial part for iOS/Safari.
      // We resume the audio context from a direct user action.
      await audioRecorder.resume();
      connect();
    }
  };

  // Initialize audio recorder when component mounts
  useEffect(() => {
    if (!audioRecorder) return;

    const initializeAudio = async () => {
      try {
        // Initialize audio context and gain node
        await audioRecorder.resume();
        await audioRecorder.start();
      } catch (error) {
        console.error('Failed to initialize audio:', error);
      }
    };

    if (connected) {
      initializeAudio();
    }

    return () => {
      audioRecorder.stop();
    };
  }, [connected, audioRecorder]);

  const handleMicPress = async (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!connected || !audioRecorder) return;
    
    try {
      // Ensure audio context is resumed
      await audioRecorder.resume();
      audioRecorder.setVolume(1.0);
    } catch (error) {
      console.error('Failed to resume audio context:', error);
    }
  };

  const handleMicRelease = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!connected || !audioRecorder) return;
    audioRecorder.setVolume(0);
  };

  const handleMicLeave = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!connected || !audioRecorder) return;
    audioRecorder.setVolume(0);
  };

  return (
    <section className="control-tray">
      {cameraStream && (
        <div className="camera-preview-container">
          <button className="action-button close-button" onClick={stopAndCleanupCamera} style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}>
            <span className="material-symbols-outlined">close</span>
          </button>
          {photoData && (
            <div className="captured-photo-container">
              <img src={photoData} alt="Captured" className="captured-photo" />
              <button className="action-button close-button" onClick={() => setPhotoData(null)} style={{ position: 'absolute', top: 8, right: 8, zIndex: 11 }}>
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
          )}
          <video
            ref={cameraVideoRef}
            autoPlay
            playsInline
            muted
            className="camera-video"
            style={{ transform: facingMode === 'user' ? 'scaleX(-1)' : 'scaleX(1)' }}
          />
          <button className="action-button camera-button" onClick={takePhoto} disabled={!connected}>
            <span className="material-symbols-outlined">camera_alt</span>
          </button>
          <button className="action-button camera-button" onClick={switchCamera} disabled={!connected}>
            <FlipCameraAndroidIcon />
          </button>
        </div>
      )}
      <canvas style={{ display: "none" }} ref={renderCanvasRef} />
      <nav className={cn("actions-nav", { disabled: !connected })}>
        <button
          className={cn("action-button mic-button")}
          onMouseDown={handleMicPress}
          onMouseUp={handleMicRelease}
          onMouseLeave={handleMicLeave}
          onTouchStart={handleMicPress}
          onTouchEnd={handleMicRelease}
        >
          <span className="material-symbols-outlined filled">
            {audioRecorder?.getVolume() > 0 ? "mic" : "mic_off"}
          </span>
        </button>
        {/* <button
          className={cn("action-button mic-button")}
          onMouseDown={() => setMuted(false)}
          onMouseUp={() => setMuted(true)}
          onMouseLeave={() => setMuted(true)}
          onTouchStart={() => setMuted(false)}
          onTouchEnd={() => setMuted(true)}
        >
          <span className="material-symbols-outlined filled">
            {muted ? "mic_off" : "mic"}
          </span>
        </button> */}


        {!muted && connected && <MicListeningModal />}

        <div className="action-button no-action outlined">
          <AudioPulse volume={volume} active={connected} hover={false} />
        </div>
        {isMobile ? (
          <>

            <button
              className="action-button camera-button"
              onClick={() => cameraStream ? cleanupCamera() : initializeCamera(facingMode)}
            // onTouchStart={() => cameraStream ? cleanupCamera() : initializeCamera(facingMode)}
            // onTouchEnd={() => cameraStream ? cleanupCamera() : initializeCamera(facingMode)}
            >
              <span className="material-symbols-outlined filled">
                {cameraStream ? 'stop' : 'camera_alt'}
              </span>
            </button>
          </>

        ) : supportsVideo && (
          <>
            <MediaStreamButton
              isStreaming={screenCapture.isStreaming}
              start={changeStreams(screenCapture)}
              stop={changeStreams()}
              onIcon="cancel_presentation"
              offIcon="present_to_all"
            />
            <MediaStreamButton
              isStreaming={webcam.isStreaming}
              start={changeStreams(webcam)}
              stop={changeStreams()}
              onIcon="videocam_off"
              offIcon="videocam"
            />
          </>
        )}
        {children}
      </nav>

      <div className={cn("connection-container", { connected })}>
        <div className="connection-button-container">
          <button
            ref={connectButtonRef}
            className={cn("action-button connect-toggle", { connected })}
            onClick={connected ? disconnect : connect}
          >
            <span className="material-symbols-outlined filled">
              {connected ? "pause" : "play_arrow"}
            </span>
          </button>
        </div>
        <span className="text-indicator">Streaming</span>
      </div>
      {enableEditingSettings ? <SettingsDialog /> : ""}


      {webcam.isStreaming && videoInputDevices.length > 1 && (
        <select
          value={selectedDeviceId || ""}
          onChange={(e) => {
            setSelectedDeviceId(e.target.value);
            // Restart webcam with new device
            changeStreams(webcam)();
          }}
          className="camera-selector"
        >
          {videoInputDevices.map((device) => (
            <option key={device.deviceId} value={device.deviceId}>
              {device.label || `Camera ${device.deviceId}`}
            </option>
          ))}
        </select>
      )}
    </section>
  );
}

export default memo(ControlTray);

const MicListeningModal = () => (
  <div className="mic-listening-modal">
    <span className="material-symbols-outlined mic-icon">mic</span>
    <span className="mic-text">Listening...</span>
  </div>
);