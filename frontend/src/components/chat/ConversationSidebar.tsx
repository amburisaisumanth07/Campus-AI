import React from 'react';
import { MessageSquare, Plus, Trash2, Sparkles, Loader2 } from 'lucide-react';
import type { ConversationResponse } from '../../types/api';

interface ConversationSidebarProps {
  conversations: ConversationResponse[];
  activeId: number | null;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  isLoading: boolean;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isLoading,
}) => {
  return (
    <div className="chat-sidebar">
      <div className="sidebar-top">
        <button
          type="button"
          className="new-chat-button"
          onClick={onNewConversation}
          disabled={isLoading}
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="conversation-list-header">
        <span>Recent Conversations</span>
        {isLoading && <Loader2 size={14} className="spin" />}
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="sidebar-empty">
            <Sparkles size={20} className="empty-sparkle" />
            <p>No recent chats.</p>
            <span className="sub-empty">Start a new chat to ask CampusAI!</span>
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = activeId === conv.id;
            return (
              <div
                key={conv.id}
                className={`conversation-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectConversation(conv.id);
                  }
                }}
              >
                <MessageSquare size={16} className="conv-icon" />
                <div className="conv-details">
                  <span className="conv-title">{conv.title || 'Untitled Conversation'}</span>
                  <span className="conv-date">
                    {new Date(conv.updated_at || conv.created_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                </div>

                <button
                  type="button"
                  className="delete-conv-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Delete this conversation session?')) {
                      onDeleteConversation(conv.id);
                    }
                  }}
                  aria-label={`Delete conversation ${conv.title}`}
                  title="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
