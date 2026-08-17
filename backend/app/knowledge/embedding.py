from __future__ import annotations

import time

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "intfloat/multilingual-e5-small"


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
            output = self.model(**batch).last_hidden_state[:, 0]
            output = F.normalize(output, p=2, dim=1)
            vectors.extend(output.cpu().tolist())
        return vectors, time.perf_counter() - started
