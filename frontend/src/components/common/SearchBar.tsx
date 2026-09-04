import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, X, Bell, Calendar, GraduationCap, Building2, Briefcase, ChevronRight } from 'lucide-react';
import { searchCollegeApi, type SearchResultItem } from '../../services/api';

export const SearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const res = await searchCollegeApi(query.trim());
        setResults(res.results || []);
        setIsOpen(true);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (linkUrl: string) => {
    setIsOpen(false);
    setQuery('');
    navigate(linkUrl);
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'announcement':
        return <Bell size={14} className="search-icon-announcement" />;
      case 'calendar':
        return <Calendar size={14} className="search-icon-calendar" />;
      case 'examination':
        return <GraduationCap size={14} className="search-icon-exam" />;
      case 'department':
        return <Building2 size={14} className="search-icon-dept" />;
      case 'placement':
        return <Briefcase size={14} className="search-icon-placement" />;
      default:
        return <Search size={14} />;
    }
  };

  return (
    <div className="global-search-container" ref={dropdownRef} data-testid="global-search">
      <div className="search-input-wrapper">
        <Search size={18} className="search-input-icon" />
        <input
          type="text"
          className="search-input-field"
          placeholder="Search official announcements, exams, calendar, departments..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
        />
        {loading && <Loader2 size={16} className="search-spinner animate-spin" />}
        {query && !loading && (
          <button
            type="button"
            className="search-clear-btn"
            onClick={() => {
              setQuery('');
              setResults([]);
              setIsOpen(false);
            }}
          >
            <X size={15} />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="search-dropdown-menu" data-testid="search-results-dropdown">
          <div className="search-dropdown-header">
            <span>Search Results ({results.length})</span>
            <span className="search-hint">Press ESC to close</span>
          </div>

          {results.length === 0 ? (
            <div className="search-no-results">
              No official information found matching &quot;{query}&quot;.
            </div>
          ) : (
            <div className="search-results-list">
              {results.map((item) => (
                <div
                  key={`${item.type}-${item.id}`}
                  className="search-result-item"
                  onClick={() => handleSelect(item.link_url)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="search-item-icon-box">{getTypeIcon(item.type)}</div>
                  <div className="search-item-content">
                    <div className="search-item-title-row">
                      <span className="search-item-title">{item.title}</span>
                      {item.category && <span className="search-item-badge">{item.category}</span>}
                    </div>
                    {item.description && <div className="search-item-desc">{item.description}</div>}
                  </div>
                  <ChevronRight size={16} className="search-item-arrow" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
