from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin phù hợp trong tài liệu."

        context_blocks = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source") or metadata.get("source_url") or metadata.get("doc_id") or result.get("id", "unknown")
            context_blocks.append(f"[{index}] Source: {source}\n{result['content']}")

        context = "\n\n".join(context_blocks)
        prompt = (
            "Dựa chỉ trên ngữ cảnh sau, trả lời câu hỏi.\n"
            "Nếu không tìm thấy thông tin, hãy nói không tìm thấy trong tài liệu.\n"
            "Khi có thể, hãy trích dẫn số nguồn dạng [1], [2].\n\n"
            f"{context}\n\n"
            f"Câu hỏi: {question}\n"
            "Câu trả lời:"
        )
        return self.llm_fn(prompt)
