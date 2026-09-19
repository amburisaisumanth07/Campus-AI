import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  RefreshCw,
  Search,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Database,
  Layers,
  BookOpen,
} from 'lucide-react';
import { getInstitutionalCoverageApi, type CoverageResponse } from '../services/coverage';

export const AdminCoverage: React.FC = () => {
  const [data, setData] = useState<CoverageResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterMode, setFilterMode] = useState<'all' | 'covered' | 'pending'>('all');

  const fetchCoverage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getInstitutionalCoverageApi();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load institutional knowledge coverage');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCoverage();
  }, [fetchCoverage]);

  const filteredCategories = (data?.categories || []).filter((item) => {
    const matchesSearch =
      item.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.model.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.coverage_area.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (filterMode === 'covered') return item.count > 0;
    if (filterMode === 'pending') return item.count === 0;
    return true;
  });

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '48px' }}>
      {/* Navigation Tabs Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', borderBottom: '1px solid #e2e8f0', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 800, margin: '0 0 6px 0', color: '#0f172a' }}>
            MITS Knowledge Coverage Dashboard
          </h1>
          <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
            Live status of normalized relational records and document grounding across all 35 institutional domains.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link
            to="/admin"
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              color: '#334155',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: 500,
              backgroundColor: '#fff',
            }}
          >
            Documents
          </Link>
          <Link
            to="/admin/sources"
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              color: '#334155',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: 500,
              backgroundColor: '#fff',
            }}
          >
            Website Sources
          </Link>
          <button
            onClick={fetchCoverage}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              backgroundColor: '#2563eb',
              color: '#fff',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '14px', borderRadius: '8px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            <span>TOTAL DOMAINS</span>
            <Layers size={18} color="#2563eb" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: '#0f172a' }}>
            {data?.total_categories ?? 35}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
            Comprehensive institutional scope
          </div>
        </div>

        <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            <span>ACTIVE COVERAGE</span>
            <ShieldCheck size={18} color="#16a34a" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: '#16a34a' }}>
            {data?.covered_categories ?? 0} <span style={{ fontSize: '16px', fontWeight: 500, color: '#64748b' }}>/ 35</span>
          </div>
          <div style={{ fontSize: '12px', color: '#16a34a', marginTop: '4px', fontWeight: 500 }}>
            {data?.coverage_percentage ?? 0}% coverage rate
          </div>
        </div>

        <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            <span>STRUCTURED RECORDS</span>
            <Database size={18} color="#8b5cf6" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: '#0f172a' }}>
            {data?.total_records?.toLocaleString() ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
            Normalized relational database entities
          </div>
        </div>

        <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            <span>VECTOR INDEX BASE</span>
            <BookOpen size={18} color="#ea580c" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 800, color: '#0f172a' }}>
            9,466
          </div>
          <div style={{ fontSize: '12px', color: '#ea580c', marginTop: '4px', fontWeight: 500 }}>
            Chroma Cloud (892 ready documents)
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ position: 'relative', flex: '1', minWidth: '260px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search categories, models, or topics (e.g., Attendance, HOD, Library)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 36px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setFilterMode('all')}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: filterMode === 'all' ? '1px solid #2563eb' : '1px solid #cbd5e1',
              backgroundColor: filterMode === 'all' ? '#eff6ff' : '#ffffff',
              color: filterMode === 'all' ? '#1d4ed8' : '#64748b',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            All (35)
          </button>
          <button
            onClick={() => setFilterMode('covered')}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: filterMode === 'covered' ? '1px solid #16a34a' : '1px solid #cbd5e1',
              backgroundColor: filterMode === 'covered' ? '#f0fdf4' : '#ffffff',
              color: filterMode === 'covered' ? '#15803d' : '#64748b',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Covered ({data?.covered_categories ?? 0})
          </button>
          <button
            onClick={() => setFilterMode('pending')}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              border: filterMode === 'pending' ? '1px solid #d97706' : '1px solid #cbd5e1',
              backgroundColor: filterMode === 'pending' ? '#fffbeb' : '#ffffff',
              color: filterMode === 'pending' ? '#b45309' : '#64748b',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            Pending Sync ({35 - (data?.covered_categories ?? 0)})
          </button>
        </div>
      </div>

      {/* Coverage Table */}
      <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              <th style={{ padding: '12px 16px', width: '50px' }}>#</th>
              <th style={{ padding: '12px 16px' }}>Category & Domain</th>
              <th style={{ padding: '12px 16px' }}>Database Entity</th>
              <th style={{ padding: '12px 16px' }}>Coverage Scope</th>
              <th style={{ padding: '12px 16px', textAlign: 'center' }}>Live Records</th>
              <th style={{ padding: '12px 16px', textAlign: 'center' }}>Status</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {filteredCategories.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '14px' }}>
                  No categories match the current filter.
                </td>
              </tr>
            ) : (
              filteredCategories.map((item) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '14px 16px', color: '#94a3b8', fontSize: '13px', fontWeight: 600 }}>
                    {item.id}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '14px' }}>
                      {item.category}
                    </div>
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <code style={{ background: '#f1f5f9', padding: '3px 6px', borderRadius: '4px', fontSize: '12px', color: '#0369a1', fontFamily: 'monospace' }}>
                      {item.model}
                    </code>
                  </td>
                  <td style={{ padding: '14px 16px', color: '#475569', fontSize: '13px', maxWidth: '300px' }}>
                    {item.coverage_area}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '3px 8px',
                        borderRadius: '12px',
                        fontWeight: 700,
                        fontSize: '12px',
                        backgroundColor: item.count > 0 ? '#dcfce7' : '#fef3c7',
                        color: item.count > 0 ? '#15803d' : '#92400e',
                      }}
                    >
                      {item.count}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                    {item.count > 0 ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#16a34a', fontSize: '12px', fontWeight: 600 }}>
                        <CheckCircle2 size={14} /> Active
                      </span>
                    ) : (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#d97706', fontSize: '12px', fontWeight: 600 }}>
                        <AlertCircle size={14} /> Ready to Sync
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        color: '#2563eb',
                        textDecoration: 'none',
                        fontSize: '13px',
                        fontWeight: 500,
                      }}
                    >
                      <span>mits.ac.in</span>
                      <ExternalLink size={12} />
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
