import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceInputButton } from './VoiceInputButton';

describe('VoiceInputButton Component', () => {
  const mockOnTranscript = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
  });

  it('renders microphone button in idle state', () => {
    render(<VoiceInputButton onTranscript={mockOnTranscript} />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    expect(micBtn).toBeInTheDocument();
    expect(micBtn).toHaveAttribute('title', 'Ask with Voice');
  });

  it('displays error message if Speech Recognition is not supported', async () => {
    render(<VoiceInputButton onTranscript={mockOnTranscript} />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    fireEvent.click(micBtn);

    await waitFor(() => {
      expect(screen.getByTestId('voice-error-toast')).toBeInTheDocument();
      expect(
        screen.getByText('Speech recognition is not supported in this browser.')
      ).toBeInTheDocument();
    });
  });

  it('starts recording and displays Listening overlay when speech recognition starts', async () => {
    class MockSpeechRecognition {
      continuous = false;
      interimResults = false;
      lang = 'en-US';
      onstart: () => void = () => {};
      onresult: (e: any) => void = () => {};
      onerror: (e: any) => void = () => {};
      onend: () => void = () => {};

      start() {
        this.onstart();
      }
      stop() {
        this.onend();
      }
      abort() {
        this.onend();
      }
    }

    (window as any).SpeechRecognition = MockSpeechRecognition;

    render(<VoiceInputButton onTranscript={mockOnTranscript} />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    fireEvent.click(micBtn);

    await waitFor(() => {
      expect(screen.getByTestId('voice-recording-overlay')).toBeInTheDocument();
      expect(screen.getByText('Listening...')).toBeInTheDocument();
      expect(screen.getByText('Speak your question clearly')).toBeInTheDocument();
    });
  });

  it('cancelling recording stops overlay and does not submit transcript', async () => {
    class MockSpeechRecognition {
      onstart: () => void = () => {};
      onend: () => void = () => {};
      start() {
        this.onstart();
      }
      stop() {
        this.onend();
      }
      abort() {
        this.onend();
      }
    }

    (window as any).SpeechRecognition = MockSpeechRecognition;

    render(<VoiceInputButton onTranscript={mockOnTranscript} />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    fireEvent.click(micBtn);

    expect(screen.getByTestId('voice-recording-overlay')).toBeInTheDocument();

    const cancelBtn = screen.getByTitle('Cancel');
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('voice-recording-overlay')).not.toBeInTheDocument();
      expect(mockOnTranscript).not.toHaveBeenCalled();
    });
  });

  it('handles permission denied error gracefully without crashing', async () => {
    class MockSpeechRecognition {
      onstart: () => void = () => {};
      onerror: (e: any) => void = () => {};
      onend: () => void = () => {};
      start() {
        this.onerror({ error: 'not-allowed' });
      }
      stop() {
        this.onend();
      }
      abort() {
        this.onend();
      }
    }

    (window as any).SpeechRecognition = MockSpeechRecognition;

    render(<VoiceInputButton onTranscript={mockOnTranscript} />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    fireEvent.click(micBtn);

    await waitFor(() => {
      expect(screen.getByTestId('voice-error-toast')).toBeInTheDocument();
      expect(screen.getByText('Microphone permission is required.')).toBeInTheDocument();
    });
  });
});
