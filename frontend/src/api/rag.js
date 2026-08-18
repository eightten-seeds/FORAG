const defaultBaseUrl = 'http://127.0.0.1:8000'
const configuredBaseUrl = import.meta.env?.VITE_API_BASE_URL

export class RAGApiError extends Error {
  constructor(message, { status = null, code = null } = {}) {
    super(message)
    this.name = 'RAGApiError'
    this.status = status
    this.code = code
  }
}

function normalizeBaseUrl(baseUrl) {
  return (baseUrl || defaultBaseUrl).trim().replace(/\/+$/, '')
}

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new RAGApiError('后端返回了无法解析的响应。', { status: response.status })
  }

  const payload = await response.json()
  if (!response.ok) {
    const detail = payload?.detail
    const message = typeof detail?.message === 'string'
      ? detail.message
      : '后端暂时无法完成此次请求。'
    throw new RAGApiError(message, {
      status: response.status,
      code: typeof detail?.code === 'string' ? detail.code : null,
    })
  }
  return payload
}

export function createRagApi({
  baseUrl = configuredBaseUrl,
  fetchImpl = globalThis.fetch,
} = {}) {
  const apiBaseUrl = normalizeBaseUrl(baseUrl)

  async function request(path, options = {}) {
    try {
      const response = await fetchImpl(`${apiBaseUrl}${path}`, options)
      return await parseResponse(response)
    } catch (error) {
      if (error instanceof RAGApiError) {
        throw error
      }
      throw new RAGApiError('无法连接后端，请确认服务已启动。')
    }
  }

  return {
    chat(question) {
      return request('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
    },
    getHealth() {
      return request('/api/health')
    },
    getMetrics() {
      return request('/api/metrics')
    },
  }
}

export const ragApi = createRagApi()
