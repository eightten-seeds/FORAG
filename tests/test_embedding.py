import torch

from backend.app.knowledge.embedding import average_pool


def test_average_pool_ignores_padding_and_normalizes_shape():
    hidden = torch.tensor([[[1.0, 0.0], [3.0, 0.0], [100.0, 100.0]]])
    mask = torch.tensor([[1, 1, 0]])
    pooled = average_pool(hidden, mask)
    assert torch.allclose(pooled, torch.tensor([[2.0, 0.0]]))
