import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  listConversationsApi,
  createConversationApi,
  getConversationDetailApi,
  deleteConversationApi,
  sendChatMessageApi,
  submitFeedbackApi,
} from '../services/api';
import type {
  ConversationResponse,
  ChatUIMessage,
  FeedbackRating,
} from '../types/api';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { ChatWindow } from '../components/chat/ChatWindow';

export const ChatPage: React.FC = () => {
  const { token } = useAuth();
  const location = useLocation();
  const initialQueryProcessedRef = useRef(false);

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatUIMessage[]>([]);

  const [isConversationsLoading, setIsConversationsLoading] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);

  // Fetch conversation list
  const loadConversations = useCallback(async () => {
    if (!token) return;
    try {
      setIsConversationsLoading(true);
      setError(null);
      const res = await listConversationsApi(token);
      setConversations(res.items || []);
    } catch (err: any) {
      console.error("Error loading conversations:", err);
      setError(err.message || "Failed to load chat history. Please try again.");
    } finally {
      setIsConversationsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load selected conversation details and messages
  const selectConversation = useCallback(
    async (convId: number) => {
      if (!token) return;
      setActiveId(convId);
      setError(null);
      setIsMobileSidebarOpen(false);
      try {
        const detail = await getConversationDetailApi(token, convId);
        setMessages(
          detail.messages.map((m) => ({
            id: m.id,
            conversation_id: m.conversation_id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            citations: m.citations,
            feedback: m.feedback,
            created_at: m.created_at,
          }))
        );
      } catch (err: any) {
        console.error(`Error loading conversation ${convId}:`, err);
        setError(err.message || "Failed to load conversation messages.");
      }
    },
    [token]
  );

  // Create new conversation explicitly
  const handleNewConversation = useCallback(async () => {
    if (!token) return;
    try {
      setError(null);
      setIsMobileSidebarOpen(false);
      const newConv = await createConversationApi(token, 'New Chat');
      setConversations((prev) => [newConv, ...prev]);
      setActiveId(newConv.id);
      setMessages([]);
    } catch (err: any) {
      console.error("Error creating new conversation:", err);
      setActiveId(null);
      setMessages([]);
    }
  }, [token]);

  // Delete conversation
  const handleDeleteConversation = useCallback(async (convId: number) => {
    if (!token) return;
    try {
      setError(null);
      await deleteConversationApi(token, convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeId === convId) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (err: any) {
      console.error(`Error deleting conversation ${convId}:`, err);
      setError(err.message || "Failed to delete conversation.");
    }
  }, [token, activeId]);

  // Send message - strictly isolated local chat loading, never triggers auth
  const handleSendMessage = useCallback(async (
    userText: string,
    department?: string,
    academicYear?: string
  ) => {
    if (!token || !userText.trim() || isSending) return;

    setError(null);
    setIsSending(true);

    // Optimistically append user message to chat UI
    const tempUserMsg: ChatUIMessage = {
      role: 'user',
      content: userText,
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const resp = await sendChatMessageApi(token, {
        conversation_id: activeId || undefined,
        message: userText,
        department,
        academic_year: academicYear,
      });

      if (resp.conversation_id) {
        setActiveId(resp.conversation_id);
      }

      const assistantMsg: ChatUIMessage = {
        id: resp.message_id,
        conversation_id: resp.conversation_id,
        role: 'assistant',
        content: resp.answer,
        citations: resp.sources,
        grounded: resp.grounded,
        retrieval_error: resp.retrieval_error,
        generation_error: resp.generation_error,
        status: resp.status,
      };

      setMessages((prev) => {
        const cleaned = prev.slice(0, prev.length - 1);
        const actualUserMsg: ChatUIMessage = resp.user_message
          ? {
              id: resp.user_message.id,
              conversation_id: resp.user_message.conversation_id,
              role: 'user',
              content: resp.user_message.content,
              created_at: resp.user_message.created_at,
            }
          : tempUserMsg;

        return [...cleaned, actualUserMsg, assistantMsg];
      });

      // Refresh sidebar conversation list
      loadConversations();
    } catch (err: any) {
      console.error("Error sending chat message:", err);
      if (err.message && (err.message.includes('401') || err.message.toLowerCase().includes('unauthorized'))) {
        setError("Your session has expired. Please log in again.");
      } else {
        setError(err.message || "Unable to send message to CampusAI. Please try again.");
      }
    } finally {
      setIsSending(false);
    }
  }, [token, activeId, isSending, loadConversations]);

  // Process initial query passed from Student Dashboard (supports both initialMessage and initialQuery)
  useEffect(() => {
    const rawState = location.state as any;
    const query = rawState?.initialMessage || rawState?.initialQuery;
    if (query && token && !initialQueryProcessedRef.current) {
      initialQueryProcessedRef.current = true;
      handleSendMessage(query);
    }
  }, [location.state, token, handleSendMessage]);

  // Submit feedback
  const handleFeedback = useCallback(async (messageId: number, rating: FeedbackRating, comment?: string) => {
    if (!token) return;
    try {
      const fb = await submitFeedbackApi(token, {
        message_id: messageId,
        rating,
        comment,
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId ? { ...msg, feedback: fb } : msg
        )
      );
    } catch (err: any) {
      console.error("Feedback error:", err);
      setError(err.message || "Failed to submit feedback.");
    }
  }, [token]);

  const activeConv = conversations.find((c) => c.id === activeId);

  return (
    <div className={`chat-page-container ${isMobileSidebarOpen ? 'mobile-sidebar-open' : ''}`}>
      {/* Mobile backdrop for chat history drawer */}
      {isMobileSidebarOpen && (
        <div
          className="chat-sidebar-backdrop"
          onClick={() => setIsMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <div className={`chat-sidebar-wrapper ${isMobileSidebarOpen ? 'open' : ''}`}>
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          onSelectConversation={selectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isLoading={isConversationsLoading}
        />
      </div>

      <ChatWindow
        messages={messages}
        activeTitle={activeConv?.title}
        isLoading={isSending}
        error={error}
        onSendMessage={handleSendMessage}
        onFeedback={handleFeedback}
        onToggleSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
        isSidebarOpen={isMobileSidebarOpen}
      />
    </div>
  );
};
