from groq import Groq

from .config import GROQ_API_KEY, GROQ_MODEL

SYSTEM_PROMPT = (
    "You are the answer-generation stage of a Retrieval-Augmented Generation demo. "
    "Answer the user's question using ONLY the numbered context chunks provided below. "
    "Cite the source document and page for any claim, like (source: FILE, p.N). "
    "If the context does not contain enough information to answer, say so explicitly "
    "instead of guessing."
)


class LLMError(RuntimeError):
    pass


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not GROQ_API_KEY:
        raise LLMError(
            "GROQ_API_KEY is not set. Add it to backend/.env before asking questions."
        )

    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        context_blocks.append(
            f"[{i}] source: {meta['source']}, page {meta['page_number']}\n{chunk['text']}"
        )
    context = "\n\n".join(context_blocks)

    user_prompt = f"Context chunks:\n\n{context}\n\nQuestion: {question}"

    client = Groq(api_key=GROQ_API_KEY)
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        raise LLMError(f"Groq request failed: {exc}") from exc

    return completion.choices[0].message.content
