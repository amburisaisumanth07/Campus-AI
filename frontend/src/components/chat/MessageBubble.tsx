import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, CheckCircle2, Bot, User as UserIcon, AlertCircle } from 'lucide-react';
import type { FeedbackRating, ChatUIMessage } from '../../types/api';
import { CitationList } from './CitationList';
import { MarkdownRenderer } from './MarkdownRenderer';

interface MessageBubbleProps {
  message: ChatUIMessage;
  onFeedback?: (messageId: number, rating: FeedbackRating, comment?: string) => Promise<void>;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onFeedback }) => {
  const isUser = message.role === 'user';
  const [currentRating, setCurrentRating] = useState<FeedbackRating | null>(
    message.feedback?.rating || null
  );
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);
  const [showCommentBox, setShowCommentBox] = useState<boolean>(false);
  const [commentText, setCommentText] = useState<string>('');

  const handleRatingClick = async (rating: FeedbackRating) => {
    if (!message.id || !onFeedback || isSubmittingFeedback) return;
    
    // Toggle off if already selected
    if (currentRating === rating) {
      return;
    }

    try {
      setIsSubmittingFeedback(true);
      await onFeedback(message.id, rating);
      setCurrentRating(rating);
      if (rating === 'thumbs_down') {
        setShowCommentBox(true);
      } else {
        setShowCommentBox(false);
      }
    } catch (err) {
      console.error("Feedback error:", err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.id || !onFeedback || !currentRating) return;
    try {
      setIsSubmittingFeedback(true);
      await onFeedback(message.id, currentRating, commentText.trim());
      setShowCommentBox(false);
    } catch (err) {
      console.error("Comment feedback error:", err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  return (
    <div className={`message-bubble-wrapper ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? <UserIcon size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content-box">
        <div className="message-header">
          <span className="sender-name">{isUser ? 'You' : 'CampusAI'}</span>
          {!isUser && (
            <div className="message-status-badges">
              {message.status === 'SUCCESS' && message.grounded && (
                <span className="grounded-badge" title="Grounded in official college documents">
                  <CheckCircle2 size={12} /> Grounded Answer
                </span>
              )}
              {message.status === 'NO_CONTEXT' && (
                <span className="status-badge warning" title="No official documents found for this query">
                  <AlertCircle size={12} /> Unverified / Fallback
                </span>
              )}
              {message.status === 'RETRIEVAL_ERROR' && (
                <span className="status-badge error" title="Failed to retrieve context">
                  <AlertCircle size={12} /> Retrieval Error
                </span>
              )}
              {message.status === 'LLM_ERROR' && (
                <span className="status-badge error" title="Language generation failed">
                  <AlertCircle size={12} /> Generation Error
                </span>
              )}
            </div>
          )}
        </div>

        <div className="message-text">
          {isUser ? (
            message.content
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {!isUser && message.id && onFeedback && (
          <div className="message-actions">
            <div className="feedback-buttons">
              <button
                type="button"
                className={`feedback-btn thumbs-up ${currentRating === 'thumbs_up' ? 'active' : ''}`}
                onClick={() => handleRatingClick('thumbs_up')}
                disabled={isSubmittingFeedback}
                aria-label="Mark answer as helpful"
                title="Helpful"
              >
                <ThumbsUp size={14} />
              </button>

              <button
                type="button"
                className={`feedback-btn thumbs-down ${currentRating === 'thumbs_down' ? 'active' : ''}`}
                onClick={() => handleRatingClick('thumbs_down')}
                disabled={isSubmittingFeedback}
                aria-label="Mark answer as not helpful"
                title="Not helpful"
              >
                <ThumbsDown size={14} />
              </button>
            </div>

            {showCommentBox && (
              <form className="feedback-comment-form" onSubmit={handleCommentSubmit}>
                <input
                  type="text"
                  placeholder="Optional: Tell us what was missing or incorrect..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  maxLength={500}
                />
                <button type="submit" disabled={isSubmittingFeedback}>
                  Submit
                </button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
