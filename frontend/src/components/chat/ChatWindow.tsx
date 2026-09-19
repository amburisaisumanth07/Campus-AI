import React, { useRef, useEffect } from 'react';
import { Bot, Sparkles, AlertCircle, Loader2, BookOpen, MessageSquare } from 'lucide-react';
import type { FeedbackRating, ChatUIMessage } from '../../types/api';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';

interface ChatWindowProps {
  messages: ChatUIMessage[];
  activeTitle?: string;
  isLoading: boolean;
  error: string | null;
  onSendMessage: (message: string, department?: string, academicYear?: string) => Promise<void>;
  onFeedback?: (messageId: number, rating: FeedbackRating, comment?: string) => Promise<void>;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  activeTitle,
  isLoading,
  error,
  onSendMessage,
  onFeedback,
  onToggleSidebar,
  isSidebarOpen,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      <header className="chat-window-header">
        <div className="header-title-box">
          <Bot size={22} className="header-bot-icon" />
          <div className="header-text-container">
            <h2>{activeTitle || 'CampusAI Assistant'}</h2>
            <span className="header-subtitle">
              Document-Grounded Student Knowledge System
            </span>
          </div>
        </div>

        {onToggleSidebar && (
          <button
            type="button"
            className={`mobile-chat-history-btn ${isSidebarOpen ? 'active' : ''}`}
            onClick={onToggleSidebar}
            aria-label="Toggle chat history"
            title="Toggle conversation list"
          >
            <MessageSquare size={16} />
            <span className="btn-label">Chats</span>
          </button>
        )}
      </header>

      {error && (
        <div className="chat-error-banner" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <div className="chat-empty-welcome">
            <div className="welcome-avatar">
              <Sparkles size={36} />
            </div>
            <h3>How can CampusAI help you today?</h3>
            <p>
              Ask any question regarding official college rules, academic calendars, examination policies, attendance guidelines, and course requirements.
            </p>

            <div className="sample-prompts">
              <div className="prompt-chip" onClick={() => onSendMessage("What is the minimum attendance requirement for semester exams?")}>
                <BookOpen size={14} />
                <span>"What is the minimum attendance requirement for semester exams?"</span>
              </div>
              <div className="prompt-chip" onClick={() => onSendMessage("What are the pass criteria and grading rules?")}>
                <BookOpen size={14} />
                <span>"What are the pass criteria and grading rules?"</span>
              </div>
              <div className="prompt-chip" onClick={() => onSendMessage("When is the last date for fee payment?")}>
                <BookOpen size={14} />
                <span>"When is the last date for fee payment?"</span>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble key={msg.id || idx} message={msg} onFeedback={onFeedback} />
          ))
        )}

        {isLoading && (
          <div className="message-bubble-wrapper assistant loading">
            <div className="message-avatar">
              <Bot size={18} />
            </div>
            <div className="message-content-box loading-box">
              <Loader2 size={18} className="spin loading-icon" />
              <span>AI is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
    </div>
  );
};
