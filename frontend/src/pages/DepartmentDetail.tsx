import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, UserCheck, BookOpen, GraduationCap, Users, Loader2, Phone, Mail, ExternalLink } from 'lucide-react';
import { getDepartmentByCodeApi, getDepartmentFacultyApi, type DepartmentItem, type FacultyItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const DepartmentDetail: React.FC = () => {
  const { code } = useParams<{ code: string }>();
  const [department, setDepartment] = useState<DepartmentItem | null>(null);
  const [facultyList, setFacultyList] = useState<FacultyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [facultyLoading, setFacultyLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDetail = async () => {
      if (!code) return;
      try {
        setLoading(true);
        const data = await getDepartmentByCodeApi(code);
        setDepartment(data);
        setLoading(false);

        // Fetch official faculty members for this department
        try {
          setFacultyLoading(true);
          const facs = await getDepartmentFacultyApi(code);
          setFacultyList(facs);
        } catch {
          setFacultyList([]);
        } finally {
          setFacultyLoading(false);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load department details');
        setLoading(false);
        setFacultyLoading(false);
      }
    };
    fetchDetail();
  }, [code]);

  if (loading) {
    return (
      <div className="page-loading-container">
        <Loader2 size={32} className="animate-spin text-emerald-400" />
        <div>Loading department details...</div>
      </div>
    );
  }

  if (error || !department) {
    return (
      <div className="page-error-container">
        <div className="error-title">Department Not Found</div>
        <div className="error-desc">{error || 'The requested academic department does not exist.'}</div>
        <button className="btn-secondary" onClick={() => navigate('/departments')}>
          <ArrowLeft size={16} /> Back to Departments
        </button>
      </div>
    );
  }

  const hodDisplayName = department.hod_name || department.hod;

  return (
    <div className="detail-page-container" data-testid="department-detail-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/departments')}>
          <ArrowLeft size={16} /> Back to All Departments
        </button>
      </div>

      <div className="detail-content-card">
        <div className="detail-top-badges">
          <span className="item-dept-code-tag large">{department.code}</span>
          <span className="dept-school-badge">{department.school || 'School of Engineering'}</span>
        </div>

        <h1 className="detail-page-title">{department.name}</h1>

        <SourceBadge
          sourceName={`MITS Official ${department.name}`}
          sourceUrl={department.source_url || 'https://mits.ac.in/'}
          lastVerifiedAt={department.last_verified_at}
          isValid={department.is_valid !== false}
        />

        {department.description && (
          <div className="detail-body-section">
            <h3>About the Department</h3>
            <p className="detail-body-text">{department.description}</p>
          </div>
        )}

        {/* Head of the Department Card */}
        {hodDisplayName && (
          <div className="detail-hod-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '10px', padding: '1rem 1.25rem', marginTop: '1.25rem' }}>
            <UserCheck size={28} color="#10b981" />
            <div style={{ flex: 1 }}>
              <div className="hod-label" style={{ fontSize: '0.8rem', color: '#10b981', fontWeight: 600, textTransform: 'uppercase' }}>
                Head of the Department (HoD)
              </div>
              <div className="hod-name" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f3f4f6' }}>
                {hodDisplayName}
              </div>
              {department.hod_designation && (
                <div style={{ fontSize: '0.85rem', color: '#9ca3af', marginTop: '2px' }}>
                  {department.hod_designation}
                </div>
              )}
            </div>
            {department.hod_profile_url && (
              <a
                href={department.hod_profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="source-external-link"
                style={{ fontSize: '0.85rem' }}
              >
                Profile <ExternalLink size={13} />
              </a>
            )}
          </div>
        )}

        {/* Official Contact Info */}
        <div className="detail-body-section" style={{ marginTop: '1.25rem' }}>
          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', fontSize: '0.9rem', color: '#9ca3af' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Phone size={15} color="#9ca3af" />
              <span>Phone: <strong style={{ color: '#e5e7eb' }}>{department.phone || 'Not published by MITS'}</strong></span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Mail size={15} color="#9ca3af" />
              <span>Email: <strong style={{ color: '#e5e7eb' }}>{department.email || 'Not published by MITS'}</strong></span>
            </div>
          </div>
        </div>

        {/* Academic Programs */}
        {department.programs && (
          <div className="detail-body-section">
            <div className="section-title-with-icon">
              <GraduationCap size={18} color="#06b6d4" />
              <h3>Academic Programs Offered</h3>
            </div>
            <div className="programs-tags-list">
              {department.programs.split(',').map((prog, i) => (
                <div key={i} className="program-tag-card">
                  {prog.trim()}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Core Courses */}
        {department.courses && (
          <div className="detail-body-section">
            <div className="section-title-with-icon">
              <BookOpen size={18} color="#c084fc" />
              <h3>Key Core Courses & Curriculum</h3>
            </div>
            <div className="courses-tags-list">
              {department.courses.split(',').map((c, i) => (
                <span key={i} className="course-chip">
                  {c.trim()}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Department Faculty Members (Dynamic from MITS Faculty Directory) */}
        <div className="detail-body-section">
          <div className="section-title-with-icon">
            <Users size={18} color="#f59e0b" />
            <h3>Official Department Faculty {facultyList.length > 0 ? `(${facultyList.length} Verified Members)` : ''}</h3>
          </div>
          {facultyLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem', color: '#9ca3af' }}>
              <Loader2 size={20} className="animate-spin text-emerald-400" />
              <span>Loading official faculty records...</span>
            </div>
          ) : facultyList.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem', marginTop: '0.75rem' }}>
              {facultyList.map((fac) => (
                <div
                  key={fac.id}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#f3f4f6', fontSize: '0.95rem' }}>{fac.name}</div>
                  {fac.designation && <div style={{ fontSize: '0.8rem', color: '#10b981' }}>{fac.designation}</div>}
                  {fac.qualification && <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{fac.qualification}</div>}
                  {fac.profile_url && (
                    <a
                      href={fac.profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: '0.75rem', color: '#06b6d4', display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}
                    >
                      View MITS Profile <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="card-empty-state" style={{ padding: '1.5rem', marginTop: '0.75rem' }}>
              <div className="empty-title">No faculty information available.</div>
              <div className="empty-subtext">
                Official faculty directory records are synchronized from the MITS portal.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
