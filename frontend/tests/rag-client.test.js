import assert from 'node:assert/strict'
import test from 'node:test'

import { RAGApiError, createRagApi } from '../src/api/rag.js'
import { createRequestGate, formatRequestSeconds, presentBusinessStatus } from '../src/views/chatPresentation.js'

function jsonResponse(payload, { status = 200 } = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

test('API client sends the public question contract and maps ChatResponse', async () => {
  let call
  const api = createRagApi({
    baseUrl: 'http://backend.test/',
    fetchImpl: async (url, options) => {
      call = { url, options }
      return jsonResponse({ final_response: {}, evidence: [], trace: {} })
    },
  })

  const response = await api.chat('care question')
  assert.equal(call.url, 'http://backend.test/api/chat')
  assert.equal(call.options.method, 'POST')
  assert.deepEqual(JSON.parse(call.options.body), { question: 'care question' })
  assert.deepEqual(response, { final_response: {}, evidence: [], trace: {} })
})

test('API client maps backend failures without exposing raw payloads', async () => {
  const api = createRagApi({
    fetchImpl: async () => jsonResponse({ detail: { code: 'workflow_failed', message: '暂时不可用' } }, { status: 503 }),
  })
  await assert.rejects(api.getHealth(), (error) => error instanceof RAGApiError && error.status === 503 && error.code === 'workflow_failed')
})

test('business statuses and unavailable metrics have safe frontend presentation', () => {
  assert.equal(presentBusinessStatus('answered').title, '护理建议')
  assert.equal(presentBusinessStatus('needs_more_information').title, '需要补充信息')
  assert.equal(presentBusinessStatus('insufficient_evidence').title, '当前证据不足')
  assert.equal(formatRequestSeconds(13008), '13.0 秒')
})

test('request gate prevents duplicate submission until completion', () => {
  const gate = createRequestGate()
  assert.equal(gate.begin(), true)
  assert.equal(gate.begin(), false)
  gate.end()
  assert.equal(gate.begin(), true)
})
