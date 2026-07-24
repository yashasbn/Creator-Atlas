import { useState } from 'react'

function Search() {
  const [channelName, setChannelName] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  function formatNumber(value) {
    if (value === undefined || value === null || value === '') return 'Not available'
    return Number(value).toLocaleString()
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!channelName.trim()) {
      setError('Please enter a channel name')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

  // In production it fetches from backend server
    try {
      const response = await fetch('http://127.0.0.1:8000/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_name: channelName.trim() }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed')
      }

      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="search-panel">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          className="search-input"
          type="search"
          placeholder="Enter a channel name or handle"
          value={channelName}
          onChange={(event) => setChannelName(event.target.value)}
        />
        <button type="submit" className="search-button" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <div className="result-card">
          <h2>Channel Overview</h2>

          <div className="info-grid">
            <div className="info-box">
              <span className="label">Title</span>
              <strong>{result.channel_title || 'Not available'}</strong>
            </div>
            <div className="info-box">
              <span className="label">Channel ID</span>
              <strong>{result.channel_id || 'Not available'}</strong>
            </div>
            <div className="info-box">
              <span className="label">Subscribers</span>
              <strong>{formatNumber(result.subscriber_count)}</strong>
            </div>
            <div className="info-box">
              <span className="label">Videos</span>
              <strong>{formatNumber(result.video_count)}</strong>
            </div>
            <div className="info-box">
              <span className="label">Views</span>
              <strong>{formatNumber(result.view_count)}</strong>
            </div>
            <div className="info-box">
              <span className="label">Country</span>
              <strong>{result.country || 'Not available'}</strong>
            </div>
          </div>

          <div className="description-box">
            <h3>Description</h3>
            <p>{result.description || 'No description provided.'}</p>
          </div>

          {result.person_info?.found && (
            <div className="description-box">
              <h3>Person Info</h3>
              <p><strong>Name:</strong> {result.person_info.title || 'Unknown'}</p>
              <p><strong>Summary:</strong> {result.person_info.extract || 'No summary available.'}</p>
            </div>
          )}

          <details className="json-block">
            <summary>View raw JSON</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  )
}

export default Search
