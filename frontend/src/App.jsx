import { useMemo, useState } from 'react'
import { BrainCircuit, FileUp, Search, ShieldCheck } from 'lucide-react'
import { askQuestion, uploadDocument } from './api'

function Metric({ label, value }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="metric">
      <div className="metric-head"><span>{label}</span><strong>{pct}%</strong></div>
      <div className="bar"><div style={{ width: `${pct}%` }} /></div>
    </div>
  )
}

export default function App() {
  const [file, setFile] = useState(null)
  const [uploadedDocument, setUploadedDocument] = useState(null)
  const [tagText, setTagText] = useState('')
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('Ready')
  const [busy, setBusy] = useState(false)

  const tags = useMemo(() => tagText.split(',').map(x => x.trim()).filter(Boolean), [tagText])

  async function doUpload() {
    if (!file) return
    setBusy(true); setStatus('Embedding document…')
    try {
      const r = await uploadDocument(file, tags)
      setUploadedDocument(r)
      setStatus(
        `Indexed ${r.filename} into ${r.chunks} chunks`
      )
    } catch (e) { setStatus(`Upload failed: ${e.message}`) }
    finally { setBusy(false) }
  }

  async function doAsk(e) {
    e.preventDefault()
    if (!question.trim() || !uploadedDocument) return
    setBusy(true); setStatus('Running agent workflow…')
    try {
      const r = await askQuestion(question,4,tags,uploadedDocument?.id)
      setResult(r); setStatus(`Completed via ${r.route}`)
    } catch (e) { setStatus(`Query failed: ${e.message}`) }
    finally { setBusy(false) }
  }

  return (
    <main>
      <header>
        <div className="brand"><BrainCircuit size={30} /><div><h1>Doc Intelligence</h1><p>Agentic RAG · grounded answers · measurable trust</p></div></div>
        <div className="status"><span className="dot" />{status}</div>
      </header>

      <section className="grid">
        <aside className="panel">
          <div className="eyebrow"><FileUp size={16}/> Knowledge base</div>
          <h2>Upload evidence</h2>
          <p>PDF, TXT, Markdown, or CSV. Documents are chunked, embedded, and stored in pgvector.</p>
          <label className="drop">
            <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} accept=".pdf,.txt,.md,.markdown,.csv" />
            <strong>{file ? file.name : 'Choose a document'}</strong>
            <span>{file ? `${(file.size / 1024).toFixed(1)} KB` : 'Click to browse'}</span>
          </label>
          <label className="field">Metadata tags
            <input value={tagText} onChange={e => setTagText(e.target.value)} placeholder="policy, hr, finance" />
          </label>
          <button disabled={!file || busy} onClick={doUpload}>Index document</button>

          <div className="guardrail"><ShieldCheck size={18}/><div><strong>Guardrails active</strong><span>Injection detection · restricted tools · verification routing</span></div></div>
        </aside>

        <section className="workspace panel">
          <div className="eyebrow"><Search size={16}/> Agent workspace</div>
          <h2>Ask across your documents</h2>
          <form onSubmit={doAsk}>
            <textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a factual question, request a summary, or compare documents…" />
            <button disabled={busy || !question.trim()}>Run agentic query</button>
          </form>

          {result && <div className="result">
            <div className="result-meta">
              <span>{result.classification}</span><span>{Math.round(result.confidence * 100)}% confidence</span><span>{result.route}</span>
            </div>
            <div className="answer">{result.answer}</div>
            {!!result.warnings?.length && <div className="warning">{result.warnings.join(' ')}</div>}

            <h3>Evaluation</h3>
            <div className="metrics">
              <Metric label="Retrieval relevance" value={result.metrics.retrieval_relevance}/>
              <Metric label="Faithfulness" value={result.metrics.faithfulness}/>
              <Metric label="Citation accuracy" value={result.metrics.citation_accuracy}/>
              <Metric label="Citation coverage" value={result.metrics.citation_coverage}/>
            </div>

            <h3>Retrieved evidence</h3>
            <div className="citations">{result.citations.map(c => <article key={c.id}>
              <div><strong>[{c.id}] {c.filename}</strong><span>chunk {c.chunk_index} · {Math.round(c.score * 100)}%</span></div>
              <p>{c.excerpt}</p>
            </article>)}</div>
          </div>}
        </section>
      </section>
    </main>
  )
}
