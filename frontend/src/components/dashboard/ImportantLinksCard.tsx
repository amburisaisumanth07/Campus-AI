import React, { useState, useEffect } from 'react';
import { Link2, ExternalLink, Globe, GraduationCap, BookOpen, Laptop, Briefcase, UserCheck, ShieldCheck } from 'lucide-react';
import { getImportantLinksApi, type ImportantLinkItem } from '../../services/api';

export const ImportantLinksCard: React.FC = () => {
  const [links, setLinks] = useState<ImportantLinkItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchLinks = async () => {
      try {
        setLoading(true);
        const data = await getImportantLinksApi();
        if (isMounted) setLinks(data);
      } catch (err) {
        console.error('Failed to load important links:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchLinks();
    return () => {
      isMounted = false;
    };
  }, []);

  const getLinkIcon = (iconName?: string | null) => {
    switch (iconName) {
      case 'Globe':
        return <Globe size={15} color="#3b82f6" />;
      case 'UserCheck':
        return <UserCheck size={15} color="#10b981" />;
      case 'GraduationCap':
        return <GraduationCap size={15} color="#f59e0b" />;
      case 'BookOpen':
        return <BookOpen size={15} color="#8b5cf6" />;
      case 'Laptop':
        return <Laptop size={15} color="#06b6d4" />;
      case 'Briefcase':
        return <Briefcase size={15} color="#ec4899" />;
      case 'ShieldCheck':
        return <ShieldCheck size={15} color="#14b8a6" />;
      default:
        return <Link2 size={15} color="#a855f7" />;
    }
  };

  return (
    <div className="dashboard-card" data-testid="important-links-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box violet">
            <Link2 size={20} />
          </div>
          <div>
            <h3>Important Links</h3>
            <span className="card-subtitle">Verified institutional portals & student tools</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="card-skeleton-list">
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
        </div>
      ) : links.length === 0 ? (
        <div className="card-empty-state">
          <div className="empty-subtext">Currently no links available.</div>
        </div>
      ) : (
        <div className="card-links-grid">
          {links.map((link) => (
            <a
              key={link.id}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="verified-portal-link"
              title={link.description || link.title}
            >
              <div className="portal-link-left">
                {getLinkIcon(link.icon)}
                <div className="portal-link-text">
                  <div className="portal-link-title">{link.title}</div>
                  {link.description && <div className="portal-link-desc">{link.description}</div>}
                </div>
              </div>
              <ExternalLink size={13} className="portal-link-arrow" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
};
