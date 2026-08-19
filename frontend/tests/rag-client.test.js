import assert from 'node:assert/strict'
import test from 'node:test'

import { createRagApi } from '../src/api/rag.js'
import {
  computeProcessSummary,
  createRequestGate,
  formatRequestSeconds,
  presentBusinessStatus,
  presentEvidenceSemantics,
} from '../src/views/chatPresentation.js'

test('API client sends the public question contract and maps ChatResponse', async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'http://127.0.0.1:8000/api/chat')
    assert.equal(init.method, 'POST')
    assert.deepEqual(JSON.parse(init.body), {
      question: 'GORE-TEX 冲锋衣应该怎么洗？',
    })

    return {
      ok: true,
      status: 200,
      headers: {
        get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null),
      },
      json: async () => ({
        query: 'GORE-TEX 冲锋衣应该怎么洗？',
        final_response: {
          answer: '使用温水机洗 [E1]。',
          status: 'answered',
          sources: [
            {
              evidence_id: 'E1',
              source_title: 'GORE-TEX Care',
              section_title: 'Washing',
              source_url: 'https://example.com/care',
            },
          ],
        },
        evidence: [
          {
            rank: 1,
            source_title: 'GORE-TEX Care',
            section_title: 'Washing',
            chunk_id: 'c1',
            content: 'Wash in warm water.',
          },
        ],
        trace: {
          retrieval_pass_count: 1,
          rewrite_count: 0,
          evidence_grade: 'sufficient',
          final_route: 'ready_for_generation',
          final_status: 'answered',
          retrieval_passes: [
            {
              pass_index: 0,
              query_used: 'GORE-TEX 冲锋衣 洗涤',
              bm25_count: 20,
              dense_count: 20,
              rrf_count: 30,
              reranked_count: 5,
            },
          ],
        },
      }),
    }
  }

  const client = createRagApi({ fetchImpl })
  const res = await client.chat('GORE-TEX 冲锋衣应该怎么洗？')
  assert.equal(res.final_response.status, 'answered')
  assert.equal(res.evidence.length, 1)
  assert.equal(res.trace.retrieval_pass_count, 1)
})

test('API client maps backend failures without exposing raw payloads', async () => {
  const fetchImpl = async () => ({
    ok: false,
    status: 500,
    headers: {
      get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null),
    },
    json: async () => ({ detail: { message: 'Internal engine failure' } }),
  })

  const client = createRagApi({ fetchImpl })
  await assert.rejects(
    async () => {
      await client.chat('test query')
    },
    (err) => {
      assert.equal(err.status, 500)
      assert.equal(err.message, 'Internal engine failure')
      return true
    },
  )
})

test('business statuses and unavailable metrics have safe frontend presentation', () => {
  assert.equal(presentBusinessStatus('answered').title, '已根据当前证据生成回答')
  assert.equal(presentBusinessStatus('needs_more_information').title, '需要补充信息')
  assert.equal(presentBusinessStatus('insufficient_evidence').title, '当前知识库证据不足')
  assert.equal(presentBusinessStatus('unknown_status').title, '请求已完成')
  assert.equal(formatRequestSeconds(1250), '1.3 秒')
})

test('request gate prevents duplicate submission until completion', () => {
  const gate = createRequestGate()
  assert.equal(gate.begin(), true)
  assert.equal(gate.begin(), false)
  gate.end()
  assert.equal(gate.begin(), true)
})

test('evidence semantics distinguishes between cited evidence and candidate-only retrieval', () => {
  // 1. Answered with evidence
  const answeredSemantics = presentEvidenceSemantics('answered', 5)
  assert.equal(answeredSemantics.tabTitle, '检索证据')
  assert.equal(answeredSemantics.isCandidateOnly, false)
  assert.match(answeredSemantics.note, /本次回答所依据的核心官方资料切片/)

  // 2. Needs more info with candidate evidence
  const needsInfoSemantics = presentEvidenceSemantics('needs_more_information', 5)
  assert.equal(needsInfoSemantics.tabTitle, '候选检索结果')
  assert.equal(needsInfoSemantics.isCandidateOnly, true)
  assert.match(needsInfoSemantics.note, /缺少面料、品牌或洗标等必要信息/)

  // 3. Insufficient evidence with candidates
  const insufficientSemantics = presentEvidenceSemantics('insufficient_evidence', 3)
  assert.equal(insufficientSemantics.tabTitle, '已检索资料')
  assert.equal(insufficientSemantics.isCandidateOnly, true)
  assert.match(insufficientSemantics.note, /拒绝未经证实的推测/)

  // 4. Zero evidence terminal state
  const zeroEvidenceSemantics = presentEvidenceSemantics('insufficient_evidence', 0)
  assert.equal(zeroEvidenceSemantics.tabTitle, '检索证据')
  assert.equal(zeroEvidenceSemantics.isCandidateOnly, false)
  assert.match(zeroEvidenceSemantics.note, /当前没有可展示的检索证据/)
})

test('computeProcessSummary reflects truthful execution path without faking', () => {
  // Direct single-pass
  const direct = computeProcessSummary({ rewrite_count: 0 }, 'answered')
  assert.equal(direct.type, 'direct')
  assert.equal(direct.tag, '单轮命中')
  assert.match(direct.text, /单轮混合检索/)

  // Rewrite two-pass
  const rewrite = computeProcessSummary({ rewrite_count: 1 }, 'answered')
  assert.equal(rewrite.type, 'rewrite')
  assert.equal(rewrite.tag, '改写重检')
  assert.match(rewrite.text, /触发改写/)

  // Needs info
  const needsInfo = computeProcessSummary({ rewrite_count: 0 }, 'needs_more_information')
  assert.equal(needsInfo.type, 'needs_info')
  assert.equal(needsInfo.tag, '需要信息')

  // Insufficient
  const insufficient = computeProcessSummary({ rewrite_count: 0 }, 'insufficient_evidence')
  assert.equal(insufficient.type, 'insufficient')
  assert.equal(insufficient.tag, '证据不足')

  // Null trace
  assert.equal(computeProcessSummary(null, 'answered'), null)
})

test('API client maps official metrics response', async () => {
  const fetchImpl = async (url) => {
    assert.equal(url, 'http://127.0.0.1:8000/api/metrics')
    return {
      ok: true,
      status: 200,
      headers: {
        get: (h) => (h.toLowerCase() === 'content-type' ? 'application/json' : null),
      },
      json: async () => ({
        available: true,
        metrics: {
          test_samples: 16,
          success_at_5: 87.5,
          recall_at_5: 87.5,
          claim_recall: 77.9,
          context_precision: 41.2,
          faithfulness: 81.4,
          system_commit: '52e9a1f',
          official_run_id: 'stage14_official_attempt2_52e9a1f',
        },
      }),
    }
  }

  const client = createRagApi({ fetchImpl })
  const res = await client.getMetrics()
  assert.equal(res.available, true)
  assert.equal(res.metrics.recall_at_5, 87.5)
  assert.equal(res.metrics.context_precision, 41.2)
})
