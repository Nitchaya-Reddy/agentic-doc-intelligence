const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function uploadDocument(file, tags) {
  const form = new FormData()
  form.append('file', file)
  form.append('tags', JSON.stringify(tags))
  form.append('metadata', JSON.stringify({ uploaded_from: 'react-ui' }))
  const res = await fetch(`${API}/api/documents/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function askQuestion(
  question,
  topK = 4,
  tags = [],
  documentId = null
) {
  const res = await fetch(`${API}/api/query`, {
    method: 'POST',

    headers: {
      'Content-Type': 'application/json'
    },

    body: JSON.stringify({
      question,

      top_k: topK,

      metadata_filter: {
        tags,
        document_id: documentId
      }
    }),
  })

  if (!res.ok) {
    throw new Error(await res.text())
  }

  return res.json()
}
