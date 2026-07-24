import Search from './Search'

function Home() {
  return (
    <main className="app-shell">
      <section className="hero-card">
        <h1>YouTube Channel Explorer</h1>
        <p>Search a channel name or handle and inspect the details returned by the Python backend.</p>
        <Search />
      </section>
    </main>
  )
}

export default Home
