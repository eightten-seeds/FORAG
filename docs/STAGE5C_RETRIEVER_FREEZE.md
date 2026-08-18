# Stage 5C Retriever Freeze

## Checkpoint

- Commit: `a091688 feat(retrieval): complete Stage 5C evaluation and freeze hybrid retriever`
- Status: DONE / PASS
- Scope: standalone Hybrid Retriever evaluation and freeze

## Frozen Retriever

Architecture:

```text
original question
  → BM25 + Dense
  → Python RRF
  → Cross-Encoder
  → Top5
```

Frozen parameters:

- BM25 TopK=20; existing field boosts frozen
- Dense: `intfloat/multilingual-e5-small`, 384 dimensions, TopK=20, candidates=100
- RRF: K=60, TopN=30, BM25/Dense weights=1.0
- Cross-Encoder: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, CPU, batch size=8
- Final retrieval Top5

## Evaluation

| Split | Evaluable | Success@5 | Recall@5 |
|---|---:|---:|---:|
| DEV | 24 | 12/24 = 50.0% | 50.0% |
| TEST | 16 | 12/16 = 75.0% | 75.0% |

TEST was run after Retriever configuration freeze. No test-driven tuning was performed.

## Query Contract and Boundary

Stage 5C standalone evaluation passes the original question to BM25 and Dense. The existing `HybridRetriever` interfaces may later accept upstream `bm25_query_text`, `brand`, and `technologies` values from Query Analysis, but Query Analysis remains upstream transformation only.

Query Analysis must not modify BM25/Dense TopK, Dense model, RRF, Cross-Encoder, Final Top5, field boosts, or Retriever algorithms. `garment_type`, `issue_type`, and `intent` remain Agent State or later-module fields unless an existing interface explicitly supports them; `care_stage` is not a current Retriever input.

## Raw Artifact and Next Gate

- Local raw artifact: `results/stage5c_retriever_freeze.json`
- Next Gate: Query Analysis
