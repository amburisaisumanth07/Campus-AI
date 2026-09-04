import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { ChatPage } from './Chat';
import * as api from '../services/api';
import * as authContext from '../context/AuthContext';

vi.mock('../services/api', () => ({
  listConversationsApi: vi.fn(),
  createConversationApi: vi.fn(),
  getConversationDetailApi: vi.fn(),
  deleteConversationApi: vi.fn(),
  sendChatMessageApi: vi.fn(),
  submitFeedbackApi: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const renderChatPage = () =>
  render(
    <MemoryRouter>
      <ChatPage />
    </MemoryRouter>
  );

describe('ChatPage Component', () => {
  const mockToken = 'mock-jwt-token-123';
  const mockUser = { id: 1, name: 'Student Test', email: 'student@campusai.edu', role: 'STUDENT', is_active: true, created_at: '', updated_at: '' };

  beforeEach(() => {
    vi.clearAllMocks();
    (authContext.useAuth as any).mockReturnValue({
      token: mockToken,
      user: mockUser,
      isAuthenticated: true,
    });
    (api.listConversationsApi as any).mockResolvedValue({
      items: [
        {
          id: 10,
          user_id: 1,
          title: 'Attendance Queries',
          created_at: '2026-08-17T10:00:00Z',
          updated_at: '2026-08-17T10:05:00Z',
          message_count: 2,
        },
      ],
      total: 1,
    });
    (api.getConversationDetailApi as any).mockResolvedValue({
      id: 10,
      user_id: 1,
      title: 'Attendance Queries',
      created_at: '2026-08-17T10:00:00Z',
      updated_at: '2026-08-17T10:05:00Z',
      messages: [
        {
          id: 101,
          conversation_id: 10,
          role: 'user',
          content: 'What is the attendance rule?',
          citations: null,
          feedback: null,
          created_at: '2026-08-17T10:01:00Z',
        },
        {
          id: 102,
          conversation_id: 10,
          role: 'assistant',
          content: 'Minimum 75% attendance is required.',
          citations: [
            {
              document_id: 1,
              title: 'Academic Handbook 2026',
              page_number: 12,
              source_pages: [12],
              snippet: 'Minimum attendance required is 75%.',
            },
          ],
          feedback: null,
          created_at: '2026-08-17T10:02:00Z',
        },
      ],
    });
  });

  it('renders Chat page and loads conversation list', async () => {
    renderChatPage();

    expect(screen.getByText(/CampusAI Assistant/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Attendance Queries')).toBeInTheDocument();
    });
  });

  it('allows user to select an existing conversation and view history & citations', async () => {
    renderChatPage();

    await waitFor(() => {
      expect(screen.getByText('Attendance Queries')).toBeInTheDocument();
    });

    const convItem = screen.getByText('Attendance Queries');
    fireEvent.click(convItem);

    await waitFor(() => {
      expect(screen.getByText('What is the attendance rule?')).toBeInTheDocument();
      expect(screen.getByText('Minimum 75% attendance is required.')).toBeInTheDocument();
      expect(screen.getByText(/Sources/i)).toBeInTheDocument();
    });

    // Expand citations
    const citationsBtn = screen.getByText(/Sources/i);
    fireEvent.click(citationsBtn);

    await waitFor(() => {
      expect(screen.getByText('Academic Handbook 2026')).toBeInTheDocument();
      expect(screen.getByText('Page 12')).toBeInTheDocument();
      expect(screen.getByText(/"Minimum attendance required is 75%."/i)).toBeInTheDocument();
    });
  });

  it('allows typing a message and prevents empty submissions', async () => {
    renderChatPage();

    const textarea = screen.getByPlaceholderText(/Ask CampusAI anything/i);
    const sendBtn = screen.getByRole('button', { name: /Send message/i });

    expect(sendBtn).toBeDisabled();

    fireEvent.change(textarea, { target: { value: '   ' } });
    expect(sendBtn).toBeDisabled();

    fireEvent.change(textarea, { target: { value: 'What are the pass marks?' } });
    expect(sendBtn).not.toBeDisabled();
  });

  it('sends message to Chat API, displays loading state, and renders assistant response', async () => {
    (api.sendChatMessageApi as any).mockResolvedValue({
      conversation_id: 20,
      message_id: 202,
      status: 'SUCCESS',
      answer: 'Pass mark is 40% in each subject.',
      grounded: true,
      retrieval_count: 1,
      sources: [
        {
          document_id: 2,
          title: 'Examination Regulations',
          page_number: 5,
          source_pages: [5],
          snippet: 'Candidates must score 40% to pass.',
        },
      ],
      user_message: {
        id: 201,
        conversation_id: 20,
        role: 'user',
        content: 'What are the pass marks?',
        created_at: '2026-08-17T11:00:00Z',
      },
      assistant_message: {
        id: 202,
        conversation_id: 20,
        role: 'assistant',
        content: 'Pass mark is 40% in each subject.',
        citations: [],
        created_at: '2026-08-17T11:01:00Z',
      },
    });

    renderChatPage();

    const textarea = screen.getByPlaceholderText(/Ask CampusAI anything/i);
    const sendBtn = screen.getByRole('button', { name: /Send message/i });

    fireEvent.change(textarea, { target: { value: 'What are the pass marks?' } });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(api.sendChatMessageApi).toHaveBeenCalledWith(mockToken, {
        conversation_id: undefined,
        message: 'What are the pass marks?',
        department: undefined,
        academic_year: undefined,
      });
      expect(screen.getByText('Pass mark is 40% in each subject.')).toBeInTheDocument();
      expect(screen.getByText(/Grounded Answer/i)).toBeInTheDocument();
    });
  });

  it('renders friendly error banner when Chat API fails', async () => {
    (api.sendChatMessageApi as any).mockRejectedValue(new Error('Network error. Unable to connect.'));

    renderChatPage();

    const textarea = screen.getByPlaceholderText(/Ask CampusAI anything/i);
    const sendBtn = screen.getByRole('button', { name: /Send message/i });

    fireEvent.change(textarea, { target: { value: 'Is college open tomorrow?' } });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/Network error. Unable to connect./i)).toBeInTheDocument();
    });
  });

  it('allows user to start a new chat', async () => {
    renderChatPage();

    const newChatBtn = screen.getByRole('button', { name: /New Chat/i });
    fireEvent.click(newChatBtn);

    await waitFor(() => {
      expect(screen.getByText(/How can CampusAI help you today\?/i)).toBeInTheDocument();
    });
  });

  it('allows user to submit thumbs-up feedback for assistant message', async () => {
    (api.submitFeedbackApi as any).mockResolvedValue({
      id: 1,
      message_id: 102,
      user_id: 1,
      rating: 'thumbs_up',
      comment: null,
      created_at: '2026-08-17T10:03:00Z',
    });

    renderChatPage();

    await waitFor(() => {
      expect(screen.getByText('Attendance Queries')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Attendance Queries'));

    await waitFor(() => {
      expect(screen.getByText('Minimum 75% attendance is required.')).toBeInTheDocument();
    });

    const thumbsUpBtn = screen.getByRole('button', { name: /Mark answer as helpful/i });
    fireEvent.click(thumbsUpBtn);

    await waitFor(() => {
      expect(api.submitFeedbackApi).toHaveBeenCalledWith(mockToken, {
        message_id: 102,
        rating: 'thumbs_up',
        comment: undefined,
      });
    });
  });
});
