import React, { useState, useEffect, useCallback } from 'react';
import {
  Globe,
  RefreshCw,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  History,
  Loader2,
  X,
  AlertCircle,
  Pause,
  Play,
  Database,
  Activity,
  Info,
} from 'lucide-react';
import type {
  WebsiteSource,
  WebsiteSourceCreate,
  WebsiteSourceUpdate,
  WebsiteSyncHistory,
} from '../types/api';
import {
  listWebsiteSourcesApi,
  createWebsiteSourceApi,
  updateWebsiteSourceApi,
  deleteWebsiteSourceApi,
  triggerSyncApi,
  getSyncHistoryApi,
  pauseSourceSyncApi,
  resumeSourceSyncApi,
} from '../services/sources';

export const AdminSources: React.FC = () => {
  const [sources, setSources] = useState<WebsiteSource[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal states
  const [showModal, setShowModal] = useState<boolean>(false);
  const [editingSource, setEditingSource] = useState<WebsiteSource | null>(null);
  const [formData, setFormData] = useState<WebsiteSourceCreate>({
    name: '',
    base_url: '',
    allowed_domains: '',
    allowed_paths: '',
    active: true,
    sync_interval: '6h',
    max_pages: 50,
  });
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);

  // Syncing state per source
  const [syncingMap, setSyncingMap] = useState<Record<number, boolean>>({});

  // History Drawer state
  const [selectedSourceForHistory, setSelectedSourceForHistory] = useState<WebsiteSource | null>(null);
  const [historyList, setHistoryList] = useState<WebsiteSyncHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  const fetchSources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listWebsiteSourcesApi();
      setSources(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Failed to load website sources.');
      setSources([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  // Periodic polling if any source is syncing
  useEffect(() => {
    const isAnySyncing = Object.values(syncingMap).some((v) => v);
    if (!isAnySyncing) return;

    const interval = setInterval(async () => {
      try {
        const data = await listWebsiteSourcesApi();
        if (Array.isArray(data)) {
          setSources(data);
          const updatedSyncMap = { ...syncingMap };
          data.forEach((s) => {
            if (s.status !== 'SYNCING') {
              updatedSyncMap[s.id] = false;
            }
          });
          setSyncingMap(updatedSyncMap);
        }
      } catch {
        // ignore polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [syncingMap]);

  const handleOpenCreateModal = () => {
    setEditingSource(null);
    setFormData({
      name: '',
      base_url: 'https://mits.ac.in/',
      allowed_domains: 'mits.ac.in',
      allowed_paths: '',
      active: true,
      sync_interval: '6h',
      max_pages: 50,
    });
    setShowModal(true);
  };

  const handleOpenEditModal = (src: WebsiteSource) => {
    setEditingSource(src);
    setFormData({
      name: src.name,
      base_url: src.base_url,
      allowed_domains: src.allowed_domains,
      allowed_paths: src.allowed_paths || '',
      active: src.active,
      sync_interval: src.sync_interval,
      max_pages: src.max_pages,
    });
    setShowModal(true);
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setError(null);
    try {
      if (editingSource) {
        const payload: WebsiteSourceUpdate = {
          name: formData.name,
          base_url: formData.base_url,
          allowed_domains: formData.allowed_domains,
          allowed_paths: formData.allowed_paths,
          active: formData.active,
          sync_interval: formData.sync_interval,
          max_pages: formData.max_pages,
        };
        await updateWebsiteSourceApi(editingSource.id, payload);
        setSuccessMsg(`Source "${formData.name}" updated successfully.`);
      } else {
        await createWebsiteSourceApi(formData);
        setSuccessMsg(`Source "${formData.name}" created and scheduled for automatic sync every ${formData.sync_interval}.`);
      }
      setShowModal(false);
      fetchSources();
    } catch (err: any) {
      setError(err.message || 'Failed to save website source.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteSource = async (src: WebsiteSource) => {
    if (!window.confirm(`Are you sure you want to delete "${src.name}" and all its synchronized documents?`)) {
      return;
    }
    try {
      await deleteWebsiteSourceApi(src.id);
      setSuccessMsg(`Source "${src.name}" deleted.`);
      fetchSources();
    } catch (err: any) {
      setError(err.message || 'Failed to delete source.');
    }
  };

  const handleSyncNow = async (src: WebsiteSource) => {
    setSyncingMap((prev) => ({ ...prev, [src.id]: true }));
    setError(null);
    try {
      await triggerSyncApi(src.id);
      setSuccessMsg(`Emergency sync started for "${src.name}". Crawling and validating content...`);
      fetchSources();
    } catch (err: any) {
      setError(err.message || 'Failed to trigger sync.');
      setSyncingMap((prev) => ({ ...prev, [src.id]: false }));
    }
  };

  const handleToggleAutoSync = async (src: WebsiteSource) => {
    try {
      if (src.auto_sync_enabled !== false) {
        await pauseSourceSyncApi(src.id);
        setSuccessMsg(`Auto-sync paused for "${src.name}".`);
      } else {
        await resumeSourceSyncApi(src.id);
        setSuccessMsg(`Auto-sync resumed for "${src.name}". Periodic crawl scheduled every ${src.sync_interval}.`);
      }
      fetchSources();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle auto-sync.');
    }
  };

  const handleViewHistory = async (src: WebsiteSource) => {
    setSelectedSourceForHistory(src);
    setHistoryLoading(true);
    try {
      const history = await getSyncHistoryApi(src.id);
      setHistoryList(Array.isArray(history) ? history : []);
    } catch (err: any) {
      setError(err.message || 'Failed to load sync history.');
      setHistoryList([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Never';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const totalDocuments = sources.reduce((acc, s) => acc + (s.document_count || 0), 0);
  const anyRunning = sources.some((s) => s.status === 'SYNCING');

  return (
    <div className="admin-sources-page">
      {/* Header */}
      <div className="admin-page-header">
        <div>
          <h2 className="admin-page-title">
            <Globe className="title-icon" size={24} /> Automatic Website Sync
          </h2>
          <p className="admin-page-subtitle">
            CampusAI automatically discovers, validates, and publishes official MITS website content every 6 hours.
            No human approval required — valid content is published automatically.
          </p>
        </div>
        <button className="primary-button" onClick={handleOpenCreateModal}>
          <Plus size={16} /> Add Website Source
        </button>
      </div>

      {/* Automatic Sync Info Banner */}
      <div
        className="auto-sync-info-banner"
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          padding: '14px 18px',
          background: 'rgba(99,102,241,0.08)',
          border: '1px solid rgba(99,102,241,0.25)',
          borderRadius: '10px',
          marginBottom: '24px',
          fontSize: '0.875rem',
          color: 'var(--text-secondary, #6b7280)',
        }}
      >
        <Activity size={18} style={{ color: '#6366f1', flexShrink: 0, marginTop: '1px' }} />
        <div>
          <strong style={{ color: 'var(--text-primary, #111827)' }}>Fully Automatic Operation</strong>
          <br />
          The scheduler runs every 6 hours automatically. Valid MITS content is published instantly.
          404 URLs and invalid sources are automatically rejected. Failed crawls preserve last-known-good data.
          This page is <strong>read-only monitoring</strong> — no approval actions are required.
        </div>
      </div>

      {/* Metrics Summary Bar */}
      <div className="sources-metrics-grid">
        <div className="metric-card">
          <div className="metric-icon-wrap" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}>
            <Globe size={22} />
          </div>
          <div>
            <div className="metric-label">Official Sources</div>
            <div className="metric-value">{sources.length}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-wrap" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
            <Database size={22} />
          </div>
          <div>
            <div className="metric-label">Indexed Documents</div>
            <div className="metric-value">{totalDocuments}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-wrap" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#6366f1' }}>
            <Clock size={22} />
          </div>
          <div>
            <div className="metric-label">Sync Schedule</div>
            <div className="metric-value" style={{ fontSize: '1rem', fontWeight: 600, color: '#10b981' }}>
              Auto (6h)
            </div>
          </div>
        </div>

        <div className="metric-card">
          <div
            className="metric-icon-wrap"
            style={{
              background: anyRunning ? 'rgba(99,102,241,0.1)' : 'rgba(16,185,129,0.1)',
              color: anyRunning ? '#6366f1' : '#10b981',
            }}
          >
            <Activity size={22} />
          </div>
          <div>
            <div className="metric-label">System Status</div>
            <div
              className="metric-value"
              style={{ fontSize: '1rem', fontWeight: 600, color: anyRunning ? '#6366f1' : '#10b981' }}
            >
              {anyRunning ? 'Syncing...' : 'Operational'}
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="banner error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button className="close-banner" onClick={() => setError(null)}>
            <X size={14} />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="banner success-banner">
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
          <button className="close-banner" onClick={() => setSuccessMsg(null)}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Sources Cards List */}
      {loading ? (
        <div className="loading-state">
          <Loader2 className="spin" size={32} />
          <p>Loading configured website sources...</p>
        </div>
      ) : !sources || sources.length === 0 ? (
        <div className="empty-sources-card">
          <Globe size={48} className="empty-icon" />
          <h3>No Website Sources Configured</h3>
          <p>Add the official MITS website URL to automatically sync academic information.</p>
          <button className="primary-button" onClick={handleOpenCreateModal}>
            <Plus size={16} /> Configure First Source
          </button>
        </div>
      ) : (
        <div className="sources-grid">
          {(sources || []).map((src) => {
            const isSyncing = src.status === 'SYNCING' || !!syncingMap[src.id];
            const autoSyncEnabled = src.auto_sync_enabled !== false;
            return (
              <div key={src.id} className={`source-card ${src.status.toLowerCase()}`}>
                <div className="source-card-header">
                  <div className="source-title-group">
                    <div className="source-icon-badge">
                      <Globe size={20} />
                    </div>
                    <div>
                      <h3 className="source-name">{src.name}</h3>
                      <a
                        href={src.base_url}
                        target="_blank"
                        rel="noreferrer"
                        className="source-url-link"
                      >
                        {src.base_url} <ExternalLink size={12} />
                      </a>
                    </div>
                  </div>

                  <div className="source-status-badge" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {isSyncing ? (
                      <span className="status-pill syncing">
                        <Loader2 size={12} className="spin" /> Syncing...
                      </span>
                    ) : src.status === 'ACTIVE' ? (
                      <span className="status-pill active">
                        <CheckCircle2 size={12} /> Connected
                      </span>
                    ) : src.status === 'ERROR' ? (
                      <span className="status-pill error">
                        <AlertTriangle size={12} /> Error
                      </span>
                    ) : (
                      <span className="status-pill idle">
                        <Clock size={12} /> Idle
                      </span>
                    )}

                    <button
                      className={`btn-toggle-sync ${autoSyncEnabled ? 'active' : 'paused'}`}
                      onClick={() => handleToggleAutoSync(src)}
                      title={autoSyncEnabled ? 'Pause automated 6h sync' : 'Resume automated 6h sync'}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '0.75rem',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        border: '1px solid',
                        borderColor: autoSyncEnabled ? '#10b981' : '#f59e0b',
                        color: autoSyncEnabled ? '#10b981' : '#f59e0b',
                        background: 'transparent',
                        cursor: 'pointer',
                      }}
                    >
                      {autoSyncEnabled ? <Pause size={12} /> : <Play size={12} />}
                      {autoSyncEnabled ? 'Auto-Sync ON' : 'Paused'}
                    </button>
                  </div>
                </div>

                <div className="source-details-grid">
                  <div className="detail-item">
                    <span className="detail-label">Allowed Domains:</span>
                    <span className="detail-value mono">{src.allowed_domains}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Sync Interval:</span>
                    <span className="detail-value">Every {src.sync_interval} (Automatic)</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Next Scheduled Sync:</span>
                    <span className="detail-value" style={{ color: autoSyncEnabled ? '#10b981' : '#9ca3af' }}>
                      {autoSyncEnabled ? formatDate(src.next_scheduled_sync_at) : 'Auto-Sync Paused'}
                    </span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Indexed Documents:</span>
                    <span className="detail-value highlight-num">{src.document_count}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Last Sync Started:</span>
                    <span className="detail-value">{formatDate(src.last_checked_at)}</span>
                  </div>

                  <div className="detail-item">
                    <span className="detail-label">Last Successful Sync:</span>
                    <span className="detail-value">{formatDate(src.last_successful_sync_at)}</span>
                  </div>
                </div>

                {src.last_error && (
                  <div className="source-error-box">
                    <AlertTriangle size={14} />
                    <span>{src.last_error}</span>
                  </div>
                )}

                {/* Monitoring note */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.78rem',
                    color: '#9ca3af',
                    padding: '6px 0 2px',
                  }}
                >
                  <Info size={12} />
                  <span>Content is automatically validated and published — no approval needed.</span>
                </div>

                <div className="source-card-footer">
                  <div className="action-buttons-left" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      className="secondary-button sync-btn"
                      onClick={() => handleSyncNow(src)}
                      disabled={isSyncing}
                      title="Trigger an immediate sync (optional — normal operation is fully automatic)"
                    >
                      <RefreshCw size={14} className={isSyncing ? 'spin' : ''} />
                      <span>{isSyncing ? 'Synchronizing...' : 'Sync Now'}</span>
                    </button>

                    <button
                      className="text-button history-btn"
                      onClick={() => handleViewHistory(src)}
                    >
                      <History size={14} />
                      <span>Sync History</span>
                    </button>
                  </div>

                  <div className="action-buttons-right">
                    <button
                      className="icon-button edit-btn"
                      title="Edit Configuration"
                      onClick={() => handleOpenEditModal(src)}
                    >
                      <Edit2 size={16} />
                    </button>
                    <button
                      className="icon-button delete-btn"
                      title="Delete Source"
                      onClick={() => handleDeleteSource(src)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Sync History Modal — Read-Only Monitoring */}
      {selectedSourceForHistory && (
        <div className="modal-backdrop" onClick={() => setSelectedSourceForHistory(null)}>
          <div className="modal-content history-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <History size={20} />
                <div>
                  <h3 style={{ margin: 0 }}>Synchronization History — {selectedSourceForHistory.name}</h3>
                  <small style={{ color: '#9ca3af' }}>
                    Automatic sync log • Read-only monitoring
                  </small>
                </div>
              </div>
              <button className="icon-button" onClick={() => setSelectedSourceForHistory(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {historyLoading ? (
                <div className="loading-state">
                  <Loader2 className="spin" size={24} />
                  <p>Loading execution history...</p>
                </div>
              ) : !historyList || historyList.length === 0 ? (
                <div className="empty-history">
                  <Clock size={32} />
                  <p>No synchronization runs recorded yet for this source.</p>
                </div>
              ) : (
                <div className="history-table-container">
                  <table className="history-table">
                    <thead>
                      <tr>
                        <th>Started At</th>
                        <th>Status</th>
                        <th>Discovered</th>
                        <th>Added</th>
                        <th>Updated</th>
                        <th>Unchanged</th>
                        <th>Failed / Rejected</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(historyList || []).map((h) => (
                        <tr key={h.id}>
                          <td>{formatDate(h.started_at)}</td>
                          <td>
                            <span className={`status-pill ${h.status.toLowerCase()}`}>
                              {h.status}
                            </span>
                          </td>
                          <td>{h.documents_discovered}</td>
                          <td className="text-green font-bold">+{h.documents_added}</td>
                          <td className="text-blue font-bold">~{h.documents_updated}</td>
                          <td className="text-gray">{h.documents_unchanged}</td>
                          <td className={h.documents_failed > 0 ? 'text-red font-bold' : 'text-gray'}>
                            {h.documents_failed}
                          </td>
                          <td className="notes-col">
                            {h.error_message ? (
                              <span className="error-note" title={h.error_message}>
                                {h.error_message}
                              </span>
                            ) : (
                              <span className="success-note">Auto-published successfully</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                className="secondary-button"
                onClick={() => setSelectedSourceForHistory(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Source Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Globe size={20} />
                <h3>{editingSource ? 'Edit Website Source' : 'Add College Website Source'}</h3>
              </div>
              <button className="icon-button" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleModalSubmit} className="source-form">
              <div className="modal-body">
                <div className="form-group">
                  <label htmlFor="source-name">Source Name *</label>
                  <input
                    id="source-name"
                    type="text"
                    required
                    placeholder="e.g. MITS Official Website"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="source-base-url">Base URL (HTTP/HTTPS) *</label>
                  <input
                    id="source-base-url"
                    type="url"
                    required
                    placeholder="https://mits.ac.in/"
                    value={formData.base_url}
                    onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  />
                  <small className="form-hint">
                    Must be a publicly accessible domain. Localhost &amp; private IPs are rejected for security.
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="source-allowed-domains">Allowed Domains (comma-separated) *</label>
                  <input
                    id="source-allowed-domains"
                    type="text"
                    required
                    placeholder="mits.ac.in"
                    value={formData.allowed_domains}
                    onChange={(e) => setFormData({ ...formData, allowed_domains: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="source-allowed-paths">Allowed Paths (optional, comma-separated)</label>
                  <input
                    id="source-allowed-paths"
                    type="text"
                    placeholder="/examinations, /circulars, /regulations"
                    value={formData.allowed_paths || ''}
                    onChange={(e) => setFormData({ ...formData, allowed_paths: e.target.value })}
                  />
                  <small className="form-hint">Leave blank to allow all paths under the domain.</small>
                </div>

                <div className="form-row">
                  <div className="form-group half">
                    <label htmlFor="source-sync-interval">Sync Interval</label>
                    <select
                      id="source-sync-interval"
                      value={formData.sync_interval}
                      onChange={(e) => setFormData({ ...formData, sync_interval: e.target.value })}
                    >
                      <option value="1h">Every 1 Hour</option>
                      <option value="6h">Every 6 Hours</option>
                      <option value="12h">Every 12 Hours</option>
                      <option value="24h">Every 24 Hours</option>
                    </select>
                  </div>

                  <div className="form-group half">
                    <label htmlFor="source-max-pages">Max Pages per Crawl</label>
                    <input
                      id="source-max-pages"
                      type="number"
                      min={5}
                      max={500}
                      value={formData.max_pages}
                      onChange={(e) => setFormData({ ...formData, max_pages: parseInt(e.target.value, 10) || 50 })}
                    />
                  </div>
                </div>

                <div className="form-checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.active}
                      onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                    />
                    <span>Enable Automatic Periodic Synchronization</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowModal(false)}
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 size={16} className="spin" /> Saving...
                    </>
                  ) : editingSource ? (
                    'Save Changes'
                  ) : (
                    'Create Source'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
