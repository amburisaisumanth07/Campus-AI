import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Square, X, Loader2, AlertCircle } from 'lucide-react';

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  variant?: 'inline' | 'card' | 'standalone';
  className?: string;
  isRecordingExternal?: boolean;
  onRecordingStateChange?: (isRecording: boolean) => void;
}

// Window type extension for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export const VoiceInputButton: React.FC<VoiceInputProps> = ({
  onTranscript,
  variant = 'inline',
  className = '',
  isRecordingExternal = false,
  onRecordingStateChange,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);

  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  useEffect(() => {
    if (isRecordingExternal && !isRecording) {
      startRecording();
    }
  }, [isRecordingExternal]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    setErrorMessage(null);
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMessage('Speech recognition is not supported in this browser.');
      return;
    }

    try {
      // Check microphone permission
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          // Stop track immediately to free device for SpeechRecognition
          stream.getTracks().forEach((track) => track.stop());
        } catch (err: any) {
          if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            setErrorMessage('Microphone permission is required.');
            return;
          }
        }
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsRecording(true);
        setIsProcessing(false);
        setDuration(0);
        if (onRecordingStateChange) onRecordingStateChange(true);

        timerRef.current = setInterval(() => {
          setDuration((prev) => prev + 1);
        }, 1000);
      };

      recognition.onresult = (event: any) => {
        setIsProcessing(true);
        const transcript = event.results[0][0].transcript;
        if (transcript && transcript.trim()) {
          onTranscript(transcript.trim());
        }
        stopRecording();
      };

      recognition.onerror = (event: any) => {
        if (timerRef.current) clearInterval(timerRef.current);
        setIsRecording(false);
        setIsProcessing(false);
        if (onRecordingStateChange) onRecordingStateChange(false);

        if (event.error === 'not-allowed') {
          setErrorMessage('Microphone permission is required.');
        } else if (event.error === 'no-speech') {
          setErrorMessage('No speech detected. Please speak clearly into your microphone.');
        } else {
          setErrorMessage(`Speech recognition error: ${event.error || 'Please try again.'}`);
        }
      };

      recognition.onend = () => {
        if (timerRef.current) clearInterval(timerRef.current);
        setIsRecording(false);
        setIsProcessing(false);
        if (onRecordingStateChange) onRecordingStateChange(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to start microphone.');
      setIsRecording(false);
      setIsProcessing(false);
      if (onRecordingStateChange) onRecordingStateChange(false);
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
    setIsRecording(false);
    setIsProcessing(false);
    if (onRecordingStateChange) onRecordingStateChange(false);
  };

  const cancelRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
    }
    setIsRecording(false);
    setIsProcessing(false);
    setErrorMessage(null);
    if (onRecordingStateChange) onRecordingStateChange(false);
  };

  // If in recording state, render the active voice modal/overlay
  return (
    <>
      {/* Trigger Button */}
      {variant === 'inline' ? (
        <button
          type="button"
          className={`voice-mic-inline-btn ${isRecording ? 'recording' : ''} ${className}`}
          onClick={isRecording ? stopRecording : startRecording}
          title={isRecording ? 'Stop recording' : 'Ask with Voice'}
          aria-label="Voice input"
        >
          {isRecording ? <MicOff size={18} className="mic-pulse" /> : <Mic size={18} />}
        </button>
      ) : variant === 'card' ? (
        <div
          className="dashboard-action-card voice-card"
          onClick={startRecording}
          role="button"
          tabIndex={0}
        >
          <div className="action-card-icon-wrap mic-purple">
            <Mic size={24} />
          </div>
          <div className="action-card-text">
            <h4>Ask with Voice</h4>
            <p>Speak your question directly to CampusAI</p>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className={`primary-button voice-standalone-btn ${className}`}
          onClick={startRecording}
        >
          <Mic size={18} /> Ask with Voice
        </button>
      )}

      {/* Active Recording State Banner / Modal */}
      {isRecording && (
        <div className="voice-recording-overlay" data-testid="voice-recording-overlay">
          <div className="voice-recording-card">
            <div className="voice-pulse-circle">
              <Mic size={32} className="mic-listening-icon" />
            </div>

            <div className="voice-recording-info">
              <span className="recording-indicator-dot"></span>
              <h4>Listening...</h4>
              <p className="voice-subtext">Speak your question clearly</p>
              <div className="voice-duration">{formatDuration(duration)}</div>
            </div>

            {/* Visual Waveform Effect */}
            <div className="voice-waveform">
              <span className="wave-bar bar-1"></span>
              <span className="wave-bar bar-2"></span>
              <span className="wave-bar bar-3"></span>
              <span className="wave-bar bar-4"></span>
              <span className="wave-bar bar-5"></span>
              <span className="wave-bar bar-6"></span>
              <span className="wave-bar bar-7"></span>
              <span className="wave-bar bar-8"></span>
            </div>

            <div className="voice-action-controls">
              <button
                type="button"
                className="voice-stop-btn"
                onClick={stopRecording}
                title="Done speaking"
              >
                <Square size={16} /> Stop &amp; Ask
              </button>
              <button
                type="button"
                className="voice-cancel-btn"
                onClick={cancelRecording}
                title="Cancel"
              >
                <X size={16} /> Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Processing State */}
      {isProcessing && (
        <div className="voice-recording-overlay">
          <div className="voice-recording-card processing">
            <Loader2 size={32} className="spin" />
            <h4>Converting speech...</h4>
            <p className="voice-subtext">Preparing your question for CampusAI</p>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {errorMessage && (
        <div className="voice-error-toast" data-testid="voice-error-toast">
          <div className="error-icon-wrap">
            <AlertCircle size={18} />
          </div>
          <span>{errorMessage}</span>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setErrorMessage(null)}
          >
            <X size={14} />
          </button>
        </div>
      )}
    </>
  );
};
