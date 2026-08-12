"""Generation: answer a question grounded in retrieved context."""

import config
import foundry_client
from retrieval import get_top_chunks

SYSTEM_PROMPT = """\
You are a Q&A assistant for Vera-Finance, an AI-powered personal finance iOS app.
You answer questions using ONLY the context passages provided by the user, with one \
exception: small talk (greetings, introductions, asking what language you can speak, \
asking who you are as an assistant). For small talk, reply briefly and warmly in the \
same language the user used, without inventing any facts about Vera-Finance, and do \
not cite a source.

For every other question, follow these steps:
1. Read the question, then check whether any context passage is topically related to \
the thing the question asks about. The question may be asked in a different language \
than the passages (e.g. a Turkish question about English passages) — that is fine, \
judge relevance by topic, not by matching language or exact wording.
2. If yes: answer using only facts from those passages, in at most 5 sentences or \
5 bullet points, and cite the source file, e.g. (source: features.md). Answer in the \
same language the question was asked in.
3. If no passage is topically related to what's asked (for example a person, price, \
platform, or feature that the passages never mention), reply exactly: "I don't have \
that information."

Never use knowledge from outside the passages about Vera-Finance itself. Never guess facts.
"""

USER_PROMPT = """\
Context passages:
{context}

Question: {question}

Answer:"""


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[source: {chunk['source']}]\n{chunk['content']}" for chunk in chunks
    )


def answer_query(question: str, stream: bool = False) -> str:
    """Retrieve context for the question and generate a grounded answer."""
    question = question.strip()
    if not question:
        return "Please enter a question."

    chunks = get_top_chunks(question, k=config.TOP_K)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT.format(context=build_context(chunks), question=question),
        },
    ]

    client = foundry_client.get_chat_client()
    if stream:
        parts = []
        for chunk in client.complete_streaming_chat(messages):
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                parts.append(content)
                print(content, end="", flush=True)
        answer = "".join(parts)
        sources = _sources_line(answer, chunks)
        if sources:
            print(sources, end="")
        print()
        return answer + sources

    answer = client.complete_chat(messages).choices[0].message.content
    return answer + _sources_line(answer, chunks)


def _sources_line(answer: str, chunks: list[dict]) -> str:
    """Append the retrieved source files, unless the model declined to answer."""
    if "don't have that information" in answer or "(source" in answer:
        return ""
    seen = list(dict.fromkeys(chunk["source"] for chunk in chunks))
    return f"\n(sources: {', '.join(seen)})"


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "What is Vera-Finance?"
    print(answer_query(question))
