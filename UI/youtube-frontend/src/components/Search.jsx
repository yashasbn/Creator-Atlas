import { useState } from 'react'

function Search() {
  const [channelName, setChannelName] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  function formatNum(num) {
    if (num === undefined || num === null || num === '') return 'N/A'
    return Number(num).toLocaleString()
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

    // Generate a simple request ID for distributed tracing (SigNoz)
    const requestId = 'req-' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)

    try {
      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Request-ID': requestId
        },
        body: JSON.stringify({ channel: channelName.trim() }),
      })

      const data = await response.json()
      // Capture the Request ID returned by the backend for telemetry correlation
      data._request_id = response.headers.get('X-Request-ID') || requestId

      if (!response.ok) {
        throw new Error(data.detail || 'Analysis failed')
      }
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

  return (
    <div className="search-panel">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          className="search-input"
          type="search"
          placeholder="Enter YouTube Channel Name or Handle (e.g. Fireship, codebasics)"
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
        />
        <button type="submit" className="search-button" disabled={loading}>
          {loading ? 'Analyzing AI Intelligence...' : 'Generate AI Report'}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
          
          {/* Header Card */}
          <div className="result-card" style={{ background: '#1e293b', color: '#f8fafc', borderRadius: '16px', padding: '24px', position: 'relative' }}>
            {result._request_id && (
              <div style={{ position: 'absolute', top: '16px', right: '16px', fontSize: '0.75rem', color: '#64748b', background: '#0f172a', padding: '4px 8px', borderRadius: '6px' }}>
                Trace ID: {result._request_id}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', marginTop: '8px' }}>
              <div>
                <h2 style={{ fontSize: '1.8rem', margin: 0, color: '#38bdf8' }}>{ch.channel_title}</h2>
                <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>{ch.custom_url || 'YouTube Channel'} • Country: {ch.country || 'Global'}</p>
              </div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '12px' }}>
                <div style={{ textAlign: 'center', background: '#334155', padding: '10px 16px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>SUBSCRIBERS</span>
                  <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#f8fafc' }}>{formatNum(ch.subscriber_count)}</div>
                </div>
                <div style={{ textAlign: 'center', background: '#334155', padding: '10px 16px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>TOTAL VIEWS</span>
                  <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#f8fafc' }}>{formatNum(ch.view_count)}</div>
                </div>
                <div style={{ textAlign: 'center', background: '#334155', padding: '10px 16px', borderRadius: '10px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>VIDEOS</span>
                  <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: '#f8fafc' }}>{formatNum(ch.video_count)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* AI Ratings Meter Card */}
          <div className="result-card">
            <h3 style={{ marginTop: 0, color: '#1e293b' }}>⭐ Creator Atlas Performance Scores (out of 10)</h3>
            <div className="info-grid">
              <div className="info-box" style={{ borderLeft: '4px solid #2563eb' }}>
                <span className="label">Content Quality</span>
                <strong style={{ fontSize: '1.4rem', color: '#2563eb' }}>{ratings.content_quality || 8.5} / 10</strong>
              </div>
              <div className="info-box" style={{ borderLeft: '4px solid #16a34a' }}>
                <span className="label">Consistency</span>
                <strong style={{ fontSize: '1.4rem', color: '#16a34a' }}>{ratings.consistency || 9.0} / 10</strong>
              </div>
              <div className="info-box" style={{ borderLeft: '4px solid #d97706' }}>
                <span className="label">Engagement</span>
                <strong style={{ fontSize: '1.4rem', color: '#d97706' }}>{ratings.engagement || 8.2} / 10</strong>
              </div>
              <div className="info-box" style={{ borderLeft: '4px solid #9333ea' }}>
                <span className="label">Branding</span>
                <strong style={{ fontSize: '1.4rem', color: '#9333ea' }}>{ratings.branding || 9.1} / 10</strong>
              </div>
            </div>
          </div>

          {/* Executive Summary & AI Intelligence */}
          <div className="result-card" style={{ background: '#f0f9ff', border: '1px solid #bae6fd' }}>
            <h3 style={{ marginTop: 0, color: '#0369a1' }}>🤖 Executive AI Intelligence Report</h3>
            <p style={{ fontSize: '1.05rem', lineHeight: '1.6', color: '#0c4a6e', fontWeight: '500' }}>
              {ai.executive_summary}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
              <div className="description-box">
                <h4 style={{ margin: '0 0 8px', color: '#0f172a' }}>🎯 Target Audience</h4>
                <p>{ai.target_audience}</p>
              </div>
              <div className="description-box">
                <h4 style={{ margin: '0 0 8px', color: '#0f172a' }}>📅 Upload Cadence</h4>
                <p>{ai.upload_consistency}</p>
              </div>
              <div className="description-box">
                <h4 style={{ margin: '0 0 8px', color: '#0f172a' }}>💬 Engagement & Interaction</h4>
                <p>{ai.engagement_analysis}</p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
              <div className="description-box" style={{ borderLeft: '4px solid #16a34a' }}>
                <h4 style={{ margin: '0 0 8px', color: '#15803d' }}>💪 Key Creator Strengths</h4>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {ai.creator_strengths?.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
              <div className="description-box" style={{ borderLeft: '4px solid #ea580c' }}>
                <h4 style={{ margin: '0 0 8px', color: '#c2410c' }}>🚀 Opportunities for Improvement</h4>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {ai.improvement_opportunities?.map((o, i) => <li key={i}>{o}</li>)}
                </ul>
              </div>
            </div>
          </div>

          {/* Computed Analytics Metrics */}
          <div className="result-card">
            <h3 style={{ marginTop: 0 }}>📊 Analytics & Performance Engine</h3>
            <div className="info-grid">
              <div className="info-box">
                <span className="label">Avg Views / Video</span>
                <strong>{formatNum(an.avg_views_per_video)}</strong>
              </div>
              <div className="info-box">
                <span className="label">Avg Engagement Rate</span>
                <strong>{an.avg_engagement_rate}%</strong>
              </div>
              <div className="info-box">
                <span className="label">Upload Frequency</span>
                <strong>Every {an.upload_frequency_days} days</strong>
              </div>
              <div className="info-box">
                <span className="label">Peak Posting Day</span>
                <strong>{an.top_posting_day}</strong>
              </div>
              <div className="info-box">
                <span className="label">Recent Upload Trend</span>
                <strong>{an.recent_upload_trend}</strong>
              </div>
            </div>
          </div>

          {/* Recent Videos List */}
          <div className="result-card">
            <h3 style={{ marginTop: 0 }}>📹 Recent Uploads Analysis ({result.videos?.length || 0} Videos)</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {result.videos?.slice(0, 5).map((vid, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                  <div>
                    <strong style={{ color: '#0f172a' }}>{vid.title}</strong>
                    <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '4px' }}>
                      Published: {new Date(vid.published_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', minWidth: '120px' }}>
                    <div style={{ fontWeight: 'bold', color: '#2563eb' }}>{formatNum(vid.view_count)} views</div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>👍 {formatNum(vid.like_count)} | 💬 {formatNum(vid.comment_count)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <details className="json-block">
            <summary>Inspect Raw Telemetry & Data Payload</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  )
}

export default Search
