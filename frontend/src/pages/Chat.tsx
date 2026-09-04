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
  const handleNewConversation = async () => {
    if (!token) return;
    try {
      setError(null);
      const newConv = await createConversationApi(token, 'New Chat');
      setConversations((prev) => [newConv, ...prev]);
      setActiveId(newConv.id);
      setMessages([]);
    } catch (err: any) {
      console.error("Error creating new conversation:", err);
      // Fallback to resetting active session
      setActiveId(null);
      setMessages([]);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (convId: number) => {
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
  };

  // Send message
  const handleSendMessage = async (
    userText: string,
    department?: string,
    academicYear?: string
  ) => {
    if (!token || !userText.trim() || isSending) return;

    setError(null);
    setIsSending(true);

    // Optimistically show user message
    const tempUserMsg = {
      role: 'user' as const,
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

      // Update active conversation ID
      if (resp.conversation_id) {
        setActiveId(resp.conversation_id);
      }

      // Add assistant response with citations
      const assistantMsg = {
        id: resp.message_id,
        conversation_id: resp.conversation_id,
        role: 'assistant' as const,
        content: resp.answer,
        citations: resp.sources,
        grounded: resp.grounded,
        retrieval_error: resp.retrieval_error,
        generation_error: resp.generation_error,
        status: resp.status,
      };

      setMessages((prev) => {
        // Replace temp message if server returned user_message
        const cleaned = prev.slice(0, prev.length - 1);
        const actualUserMsg = resp.user_message
          ? {
              id: resp.user_message.id,
              conversation_id: resp.user_message.conversation_id,
              role: 'user' as const,
              content: resp.user_message.content,
              created_at: resp.user_message.created_at,
            }
          : tempUserMsg;

        return [...cleaned, actualUserMsg, assistantMsg];
      });

      // Refresh conversation list in sidebar
      loadConversations();
    } catch (err: any) {
      console.error("Error sending chat message:", err);
      setError(err.message || "Unable to send message to CampusAI. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  // Process initial query passed from Student Dashboard
  useEffect(() => {
    const query = (location.state as any)?.initialQuery;
    if (query && token && !initialQueryProcessedRef.current && !isSending) {
      initialQueryProcessedRef.current = true;
      handleSendMessage(query);
    }
  }, [location.state, token, handleSendMessage]);

  // Submit feedback
  const handleFeedback = async (messageId: number, rating: FeedbackRating, comment?: string) => {
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
  };

  const activeConv = conversations.find((c) => c.id === activeId);

  return (
    <div className="chat-page-container">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelectConversation={selectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isLoading={isConversationsLoading}
      />

      <ChatWindow
        messages={messages}
        activeTitle={activeConv?.title}
        isLoading={isSending}
        error={error}
        onSendMessage={handleSendMessage}
        onFeedback={handleFeedback}
      />
    </div>
  );
};
