from __future__ import annotations

import time

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "intfloat/multilingual-e5-small"


def average_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    return (last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)


class E5Embedder:
    def __init__(self, model_name: str = MODEL_NAME, device: str = "cpu") -> None:
        self.device = torch.device(device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def encode(self, texts: list[str], batch_size: int = 16) -> tuple[list[list[float]], float]:
        started = time.perf_counter()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = self.tokenizer(texts[start:start + batch_size], padding=True, truncation=True, max_length=512, return_tensors="pt")
            batch = {key: value.to(self.device) for key, value in batch.items()}
            output = average_pool(self.model(**batch).last_hidden_state, batch["attention_mask"])
            output = F.normalize(output, p=2, dim=1)
            vectors.extend(output.cpu().tolist())
        return vectors, time.perf_counter() - started

    def encode_query(self, query_text: str) -> list[float]:
        """Encode one E5 query without changing frozen document embeddings."""
        cleaned_query = query_text.strip()
        if not cleaned_query:
            raise ValueError("query_text must not be empty")
        vectors, _ = self.encode([f"query: {cleaned_query}"])
        return vectors[0]
