import React, { useState, useEffect } from 'react';
import { Landmark, MapPin, ExternalLink } from 'lucide-react';
import { getCollegeInfoApi, type CollegeInfoItem } from '../../services/api';

export const CollegeInfoCard: React.FC = () => {
  const [infoList, setInfoList] = useState<CollegeInfoItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchInfo = async () => {
      try {
        setLoading(true);
        const data = await getCollegeInfoApi();
        if (isMounted) setInfoList(data);
      } catch (err) {
        console.error('Failed to load college info:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchInfo();
    return () => {
      isMounted = false;
    };
  }, []);

  const aboutInfo = infoList.find((i) => i.key === 'about_mits');
  const accreditationsInfo = infoList.find((i) => i.key === 'accreditations');

  if (loading) {
    return (
      <div className="dashboard-card" data-testid="college-info-card">
        <div className="card-top-bar">
          <div className="card-title-group">
            <div className="card-icon-box cyan">
              <Landmark size={20} />
            </div>
            <div>
              <h3>College Information</h3>
              <span className="card-subtitle">Official university accreditations & profile</span>
            </div>
          </div>
        </div>
        <div className="card-skeleton-list">
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (!aboutInfo && !accreditationsInfo) {
    return (
      <div className="dashboard-card" data-testid="college-info-card">
        <div className="card-top-bar">
          <div className="card-title-group">
            <div className="card-icon-box cyan">
              <Landmark size={20} />
            </div>
            <div>
              <h3>College Information</h3>
              <span className="card-subtitle">Official university accreditations & profile</span>
            </div>
          </div>
        </div>
        <div className="card-empty-state">
          <div className="empty-subtext">Currently no official information is available.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-card" data-testid="college-info-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box cyan">
            <Landmark size={20} />
          </div>
          <div>
            <h3>College Information</h3>
            <span className="card-subtitle">Official university accreditations & profile</span>
          </div>
        </div>
      </div>

      <div className="college-info-content">
        {aboutInfo && (
          <div className="college-summary-text">{aboutInfo.content}</div>
        )}

        {accreditationsInfo && (
          <div className="college-accreditation-note">
            <strong>Accreditation Status:</strong> {accreditationsInfo.content}
          </div>
        )}

        <div className="college-footer-row">
          <span className="campus-location-label">
            <MapPin size={13} /> Madanapalle, AP, India
          </span>
          <a
            href="https://mits.ac.in/"
            target="_blank"
            rel="noopener noreferrer"
            className="college-web-link"
          >
            mits.ac.in <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
};
