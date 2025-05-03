// src/pages/RewrittenNews.tsx

import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'

interface RewrittenData {
  id: string
  rewritten_title: string
  rewritten_body: string
}

export default function RewrittenNews() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<RewrittenData | null>(null)
  const [status, setStatus] = useState<'loading' | 'inProgress' | 'error' | 'ready'>('loading')

  useEffect(() => {
    if (!id) return

    const check = async () => {
      try {
        // Звертаємось до проксі: Vite перенаправить /rewritten/:id → http://news_api:8000/rewritten/:id
        const res = await fetch(`/rewritten/${id}`)

        if (res.status === 202) {
          setStatus('inProgress')
          // через 3 секунди повторимо
          setTimeout(check, 3000)
          return
        }
        if (res.status === 404) {
          setStatus('error')
          console.error('404: rewritten not found')
          return
        }
        if (!res.ok) {
          setStatus('error')
          console.error(`Error fetching rewritten: ${res.status}`)
          return
        }

        const json = await res.json()
        setData({
          id: json.id,
          rewritten_title: json.rewritten_title,
          rewritten_body: json.rewritten_body,
        })
        setStatus('ready')
      } catch (e) {
        console.error(e)
        setStatus('error')
      }
    }

    check()
  }, [id])

  if (status === 'loading') {
    return <p>Loading...</p>
  }
  if (status === 'inProgress') {
    return <p>AI is rewriting the article... Please wait ⏳</p>
  }
  if (status === 'error' || !data) {
    return <p>Something went wrong or not found.</p>
  }

  // status === 'ready'
  return (
    <article className="prose max-w-none p-4">
      <h1>{data.rewritten_title}</h1>
      {data.rewritten_body.split('\n\n').map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </article>
  )
}
