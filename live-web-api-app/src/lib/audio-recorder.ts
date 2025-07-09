// src/lib/audio-recorder.ts

import AudioRecordingWorklet from "./worklets/audio-processing";
import VolMeterWorket from "./worklets/vol-meter";

import { createWorketFromSrc } from "./audioworklet-registry";
import EventEmitter from "eventemitter3";

// This utility function can stay as is.
function arrayBufferToBase64(buffer: ArrayBuffer) {
  var binary = "";
  var bytes = new Uint8Array(buffer);
  var len = bytes.byteLength;
  for (var i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export class AudioRecorder extends EventEmitter {
  stream: MediaStream | undefined;
  // --- CHANGE 1: The AudioContext is now created in the constructor ---
  // It is now a public property, not optional.
  public audioContext: AudioContext;
  source: MediaStreamAudioSourceNode | undefined;
  recording: boolean = false;
  private gainNode: GainNode | undefined;
  recordingWorklet: AudioWorkletNode | undefined;
  vuWorklet: AudioWorkletNode | undefined;

  private starting: Promise<void> | null = null;

  constructor(public sampleRate = 16000) {
    super();
    // Create the AudioContext immediately. This is crucial.
    // We are directly creating it here instead of using the external utility,
    // as it's cleaner to have it self-contained.
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.sampleRate,
    });
    
    // Create gain node for volume control
    try {
      this.gainNode = this.audioContext.createGain();
      if (!this.gainNode) {
        throw new Error("Failed to create gain node");
      }
      this.gainNode.gain.value = 0; // Start with 0 volume
    } catch (error) {
      console.error("Failed to create gain node:", error);
      this.gainNode = undefined;
    }
    
    // If the context is created but not allowed to run, it starts as 'suspended'.
    // We will resume it later with a user gesture.
    if (this.audioContext.state === 'suspended') {
      console.log("AudioContext created in a suspended state. Awaiting user gesture to resume.");
    }
  }

  // --- CHANGE 2: Add a public resume method ---
  /**
   * Resumes the AudioContext if it's in a suspended state.
   * This MUST be called from within a user-initiated event handler (e.g., a click).
   */
  async resume() {
    if (this.audioContext.state === 'suspended') {
      console.log("Resuming AudioContext from user gesture.");
      await this.audioContext.resume();
      console.log("AudioContext state is now:", this.audioContext.state);
    }
  }

  // --- CHANGE 3: Update the start() method ---
  async start() {
    // As a fallback, we can also try to resume here, but the primary resume
    // should happen on the user click.
    await this.resume();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Could not request user media");
    }

    this.starting = new Promise(async (resolve, reject) => {
      try {
        // The context already exists, so we don't create it here.
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.source = this.audioContext.createMediaStreamSource(this.stream);

        const workletName = "audio-recorder-worklet";
        const src = createWorketFromSrc(workletName, AudioRecordingWorklet);

        try {
          await this.audioContext.audioWorklet.addModule(src);
        } catch(e) {
          // Catch errors for adding the same module twice. It's safe to ignore.
          console.warn(`Could not add audio worklet module '${workletName}'. It may already be registered.`, e)
        }

        this.recordingWorklet = new AudioWorkletNode(
          this.audioContext,
          workletName,
        );

        this.recordingWorklet.port.onmessage = async (ev: MessageEvent) => {
          const arrayBuffer = ev.data.data.int16arrayBuffer;
          if (arrayBuffer) {
            const arrayBufferString = arrayBufferToBase64(arrayBuffer);
            this.emit("data", arrayBufferString);
          }
        };

        // Create gain node if it doesn't exist
        if (!this.gainNode) {
          this.gainNode = this.audioContext.createGain();
          if (!this.gainNode) {
            throw new Error("Failed to create gain node");
          }
          this.gainNode.gain.value = 0; // Start with 0 volume
        }

        // Connect source to gain node first
        if (this.source && this.gainNode) {
          this.source.connect(this.gainNode);
        }
        // Then connect gain node to recording worklet
        if (this.gainNode && this.recordingWorklet) {
          this.gainNode.connect(this.recordingWorklet);
        }

        // vu meter worklet
        const vuWorkletName = "vu-meter";
        try {
          await this.audioContext.audioWorklet.addModule(
            createWorketFromSrc(vuWorkletName, VolMeterWorket),
          );
        } catch(e) {
          console.warn(`Could not add audio worklet module '${vuWorkletName}'. It may already be registered.`, e)
        }
        this.vuWorklet = new AudioWorkletNode(this.audioContext, vuWorkletName);
        this.vuWorklet.port.onmessage = (ev: MessageEvent) => {
          this.emit("volume", ev.data.volume);
        };

        // Connect gain node to vu meter worklet
        if (this.gainNode && this.vuWorklet) {
          this.gainNode.connect(this.vuWorklet);
        }
        this.recording = true;
        resolve();
        this.starting = null;
      } catch (error) {
        console.error("Failed to start audio recorder:", error);
        reject(error);
        this.starting = null;
      }
    });
  }

  stop() {
    const handleStop = () => {
      try {
        this.source?.disconnect();
        this.stream?.getTracks().forEach((track) => track.stop());
        this.recording = false; // Set recording to false
        this.stream = undefined;
        this.recordingWorklet = undefined;
        this.vuWorklet = undefined;
        if (this.gainNode) {
          this.gainNode.disconnect();
          this.gainNode = undefined;
        }
      } catch (error) {
        console.error("Error during audio cleanup:", error);
      }
    };
    if (this.starting) {
      this.starting.then(handleStop).finally(() => { this.starting = null; });
      return;
    }
    handleStop();
  }

  setVolume(volume: number): void {
    if (!this.gainNode) {
      console.warn("Cannot set volume: GainNode is not initialized");
      return;
    }
    this.gainNode.gain.value = volume;
  }

  getVolume(): number {
    if (!this.gainNode) {
      console.warn("Cannot get volume: GainNode is not initialized");
      return 0;
    }
    return this.gainNode.gain.value;
  }
}