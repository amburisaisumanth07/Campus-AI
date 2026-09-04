import React, { useState } from 'react';
import { Send, Loader2, Filter } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string, department?: string, academicYear?: string) => Promise<void>;
  isLoading: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading }) => {
  const [text, setText] = useState<string>('');
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [department, setDepartment] = useState<string>('');
  const [academicYear, setAcademicYear] = useState<string>('');

  const trimmed = text.trim();
  const canSend = trimmed.length > 0 && !isLoading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSend) return;

    const messageToSend = trimmed;
    setText('');
    await onSendMessage(
      messageToSend,
      department.trim() || undefined,
      academicYear.trim() || undefined
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      {showFilters && (
        <div className="chat-filters-panel">
          <div className="filter-group">
            <label htmlFor="dept-select">Department Filter:</label>
            <input
              id="dept-select"
              type="text"
              placeholder="e.g. Computer Science, Academic Cell"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="year-select">Academic Year Filter:</label>
            <input
              id="year-select"
              type="text"
              placeholder="e.g. 2025-2026, 2026"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
            />
          </div>
        </div>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <button
          type="button"
          className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
          onClick={() => setShowFilters((prev) => !prev)}
          title="Filter retrieval search by Department or Academic Year"
          aria-label="Toggle RAG metadata search filters"
        >
          <Filter size={18} />
        </button>

        <textarea
          className="chat-textarea"
          placeholder="Ask CampusAI anything about college regulations, attendance, exams, fees..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={1}
          maxLength={4000}
        />

        <button
          type="submit"
          className="send-button"
          disabled={!canSend}
          aria-label="Send message"
        >
          {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
};
