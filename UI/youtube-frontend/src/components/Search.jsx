import { useState } from 'react'

function Search() {
  const [channelName, setChannelName] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [showRaw, setShowRaw] = useState(false)

  function formatNum(num) {
    if (num === undefined || num === null || num === '') return 'N/A'
    const n = Number(num)
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
    return n.toLocaleString()
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!channelName.trim()) {
      setError('Please enter a YouTube channel name or handle')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    setShowRaw(false)

    const requestId = 'req-' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)

    try {
      const response = await fetch('http://127.0.0.1:8081/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
        },
        body: JSON.stringify({ channel: channelName.trim() }),
      })

      const data = await response.json()
      data._request_id = response.headers.get('X-Request-ID') || requestId
      data._trace_id = response.headers.get('X-Trace-ID')

      if (!response.ok) throw new Error(data.detail || 'Analysis failed')
      setResult(data)
    } catch (err) {
      setError(err.message || 'Error connecting to backend')
    } finally {
      setLoading(false)
    }
  }

  const ch = result?.channel || {}
  const an = result?.analytics || {}
  const ai = result?.ai_report || {}
  const ratings = ai?.ratings || {}

  const scoreColor = (v) => {
    const n = Number(v)
    if (n >= 8) return '#10b981'
    if (n >= 6) return '#f59e0b'
    return '#ef4444'
  }

  const scores = [
    { label: 'Content Quality', key: 'content_quality', default: 8.5 },
    { label: 'Consistency',     key: 'consistency',     default: 9.0 },
    { label: 'Engagement',      key: 'engagement',      default: 8.2 },
    { label: 'Branding',        key: 'branding',        default: 9.1 },
  ]

  return (
    <>
      {/* Search bar */}
      <div className="search-wrap">
        <form onSubmit={handleSubmit} className="search-form">
          <input
            id="channel-search-input"
            className="search-input"
            type="search"
            placeholder="Channel name or handle — e.g. Fireship, @mkbhd"
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
          />
          <button id="analyze-btn" type="submit" className="search-button" disabled={loading}>
            {loading ? 'Analyzing…' : '✦ Analyze'}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="error-banner" style={{ maxWidth: 860, margin: '0 auto 24px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="loading-state">
          <div className="loading-ring" />
          <span>Running AI analysis…</span>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="results">

          {/* Channel Header */}
          <div className="card channel-header">
            <div className="channel-name">{ch.channel_title}</div>
            <div className="channel-meta">
              {ch.custom_url && <span>{ch.custom_url} &nbsp;·&nbsp;</span>}
              {ch.country ? `🌍 ${ch.country}` : '🌍 Global'}
            </div>
            <div className="stat-row">
              {[
                { label: 'Subscribers', value: formatNum(ch.subscriber_count) },
                { label: 'Total Views',  value: formatNum(ch.view_count) },
                { label: 'Videos',       value: formatNum(ch.video_count) },
              ].map(s => (
                <div key={s.label} className="stat-chip">
                  <span className="stat-label">{s.label}</span>
                  <span className="stat-value">{s.value}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '16px' }}>
              {result._trace_id && (
                <div className="trace-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  🔭 SigNoz Trace: 
                  <a 
                    href={`http://localhost:3301/trace/${result._trace_id}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#8b5cf6', textDecoration: 'underline', fontWeight: 600 }}
                  >
                    {result._trace_id.substring(0, 8)}...
                  </a>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(result._trace_id);
                      const btn = document.getElementById('copy-trace-btn');
                      if (btn) {
                        btn.innerText = 'Copied!';
                        setTimeout(() => { btn.innerText = 'Copy'; }, 2000);
                      }
                    }}
                    id="copy-trace-btn"
                    style={{ 
                      background: 'rgba(255,255,255,0.1)', 
                      border: 'none', 
                      color: 'white', 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      cursor: 'pointer',
                      fontSize: '0.65rem'
                    }}
                  >
                    Copy
                  </button>
                </div>
              )}
              {result._request_id && (
                <div className="trace-badge">
                  🆔 Request ID: {result._request_id}
                </div>
              )}
            </div>
          </div>

          {/* Performance Scores */}
          <div className="card">
            <div className="card-title">Performance Scores</div>
            <div className="score-grid">
              {scores.map(s => {
                const val = Number(ratings[s.key] || s.default)
                const color = scoreColor(val)
                return (
                  <div key={s.key} className="score-item">
                    <div className="score-header">
                      <span className="score-label">{s.label}</span>
                      <span className="score-num" style={{ color }}>{val.toFixed(1)}</span>
                    </div>
                    <div className="score-bar-bg">
                      <div
                        className="score-bar-fill"
                        style={{ width: `${(val / 10) * 100}%`, background: color }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* AI Executive Report */}
          {ai.executive_summary && (
            <div className="card">
              <div className="card-title">🤖 AI Intelligence Report</div>
              <p className="ai-summary">{ai.executive_summary}</p>
              <div className="detail-grid">
                {ai.target_audience && (
                  <div className="detail-box">
                    <h4>🎯 Target Audience</h4>
                    <p>{ai.target_audience}</p>
                  </div>
                )}
                {ai.upload_consistency && (
                  <div className="detail-box">
                    <h4>📅 Upload Cadence</h4>
                    <p>{ai.upload_consistency}</p>
                  </div>
                )}
                {ai.engagement_analysis && (
                  <div className="detail-box">
                    <h4>💬 Engagement</h4>
                    <p>{ai.engagement_analysis}</p>
                  </div>
                )}
                {ai.creator_strengths?.length > 0 && (
                  <div className="detail-box strengths">
                    <h4>💪 Strengths</h4>
                    <ul>{ai.creator_strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
                  </div>
                )}
                {ai.improvement_opportunities?.length > 0 && (
                  <div className="detail-box improvements">
                    <h4>🚀 Opportunities</h4>
                    <ul>{ai.improvement_opportunities.map((o, i) => <li key={i}>{o}</li>)}</ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Analytics */}
          <div className="card">
            <div className="card-title">📊 Analytics Engine</div>
            <div className="analytics-grid">
              {[
                { label: 'Avg Views / Video',    value: formatNum(an.avg_views_per_video) },
                { label: 'Avg Engagement Rate',  value: an.avg_engagement_rate ? `${an.avg_engagement_rate}%` : 'N/A' },
                { label: 'Upload Frequency',     value: an.upload_frequency_days ? `Every ${an.upload_frequency_days}d` : 'N/A' },
                { label: 'Peak Posting Day',     value: an.top_posting_day || 'N/A' },
                { label: 'Recent Upload Trend',  value: an.recent_upload_trend || 'N/A' },
              ].map(m => (
                <div key={m.label} className="metric-box">
                  <span className="metric-label">{m.label}</span>
                  <span className="metric-value">{m.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Videos */}
          {result.videos?.length > 0 && (
            <div className="card">
              <div className="card-title">📹 Recent Uploads ({result.videos.length} videos)</div>
              <div className="video-list">
                {result.videos.slice(0, 5).map((vid, idx) => (
                  <div key={idx} className="video-row">
                    <div>
                      <div className="video-title">{vid.title}</div>
                      <div className="video-date">{new Date(vid.published_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</div>
                    </div>
                    <div className="video-stats">
                      <div className="video-views">{formatNum(vid.view_count)} views</div>
                      <div className="video-likes-comments">👍 {formatNum(vid.like_count)} &nbsp;·&nbsp; 💬 {formatNum(vid.comment_count)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw payload */}
          <div>
            <button className="raw-toggle" onClick={() => setShowRaw(v => !v)}>
              {showRaw ? '▲' : '▶'} {showRaw ? 'Hide' : 'Inspect'} raw telemetry &amp; data payload
            </button>
            {showRaw && <pre className="raw-pre">{JSON.stringify(result, null, 2)}</pre>}
          </div>

        </div>
      )}
    </>
  )
}

export default Search
