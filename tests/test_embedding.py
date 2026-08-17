from types import SimpleNamespace

import torch

from backend.app.knowledge.embedding import average_pool
from backend.app.knowledge.embedding import E5Embedder


def test_average_pool_ignores_padding_and_normalizes_shape():
    hidden = torch.tensor([[[1.0, 0.0], [3.0, 0.0], [100.0, 100.0]]])
    mask = torch.tensor([[1, 1, 0]])
    pooled = average_pool(hidden, mask)
    assert torch.allclose(pooled, torch.tensor([[2.0, 0.0]]))


def test_encode_uses_attention_mask_pooling_and_l2_normalization_without_model_download():
    class FakeTokenizer:
        def __call__(self, *args, **kwargs):
            return {
                "input_ids": torch.tensor([[1, 2, 0]]),
                "attention_mask": torch.tensor([[1, 1, 0]]),
            }

    class FakeModel:
        def __call__(self, **kwargs):
            return SimpleNamespace(
                last_hidden_state=torch.tensor([[[1.0, 0.0], [3.0, 0.0], [100.0, 100.0]]])
            )

    embedder = object.__new__(E5Embedder)
    embedder.device = torch.device("cpu")
    embedder.tokenizer = FakeTokenizer()
    embedder.model = FakeModel()

    vectors, _ = embedder.encode(["query: test"])
    vector = torch.tensor(vectors[0])
    assert torch.allclose(vector, torch.tensor([1.0, 0.0]))
    assert torch.allclose(vector.norm(p=2), torch.tensor(1.0))


def test_e5_query_helper_adds_query_prefix_without_reembedding_documents(monkeypatch):
    embedder = object.__new__(E5Embedder)
    calls = []

    def fake_encode(texts, batch_size=16):
        calls.append((texts, batch_size))
        return [[0.5] * 384], 0.01

    monkeypatch.setattr(embedder, "encode", fake_encode)
    assert embedder.encode_query("  我的冲锋衣不挂水珠  ") == [0.5] * 384
    assert calls == [(["query: 我的冲锋衣不挂水珠"], 16)]
