// Lightweight React hook to subscribe to a Server-Sent Events (SSE) URL
// with automatic reconnect/backoff and an optional WebSocket fallback.
import { useEffect, useRef, useState } from 'react'

function wait(ms) {
  return new Promise((res) => setTimeout(res, ms))
}

export default function useEventSource(url, { websocketFallbackUrl = null, maxRetries = 6 } = {}) {
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([])
  const esRef = useRef(null)
  const wsRef = useRef(null)
  const stopped = useRef(false)

  useEffect(() => {
    stopped.current = false

    let retries = 0

    const connectSSE = async () => {
      if (stopped.current) return
      try {
        const es = new EventSource(url)
        esRef.current = es
        setConnected(true)
        es.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data)
            setMessages((m) => [...m, data])
          } catch (err) {
            // push raw data if JSON parse fails
            setMessages((m) => [...m, { raw: ev.data }])
          }
        }
        es.onerror = async (err) => {
          // Close and attempt reconnect with backoff
          try { es.close() } catch (_) {}
          setConnected(false)
          esRef.current = null
          if (stopped.current) return
          if (retries >= maxRetries) {
            // Give up and possibly trigger fallback
            if (websocketFallbackUrl) {
              connectWebSocket()
            }
            return
          }
          const backoff = Math.min(1000 * 2 ** retries, 30000)
          retries += 1
          await wait(backoff)
          if (!stopped.current) connectSSE()
        }
      } catch (err) {
        setConnected(false)
        if (websocketFallbackUrl) connectWebSocket()
      }
    }

    const connectWebSocket = () => {
      if (!websocketFallbackUrl) return
      try {
        const ws = new WebSocket(websocketFallbackUrl)
        wsRef.current = ws
        ws.onopen = () => setConnected(true)
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data)
            setMessages((m) => [...m, data])
          } catch (err) {
            setMessages((m) => [...m, { raw: ev.data }])
          }
        }
        ws.onclose = () => setConnected(false)
        ws.onerror = () => setConnected(false)
      } catch (err) {
        setConnected(false)
      }
    }

    // Start with SSE
    connectSSE()

    return () => {
      stopped.current = true
      try { if (esRef.current) esRef.current.close() } catch (_) {}
      try { if (wsRef.current) wsRef.current.close() } catch (_) {}
      esRef.current = null
      wsRef.current = null
    }
  }, [url, websocketFallbackUrl, maxRetries])

  const clear = () => setMessages([])

  return { connected, messages, clear }
}
