# utils/llm.py
"""
Ollama 调用封装：统一重试逻辑 + 超长文本分块处理
"""
import time
from utils.logger import log


def call_llm(system: str, user_text: str, cfg: dict) -> str:
    """
    调用 Ollama。
    超过 chunk_chars 时自动按段落分块，分批调用后合并结果。
    失败时自动重试最多 max_retries 次。
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("请先执行: pip install openai")

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg.get("api_key", "ollama"))
    chunk_size = cfg.get("chunk_chars", 3000)

    if len(user_text) > chunk_size * 1.2:
        chunks = _split_by_paragraph(user_text, chunk_size)
        log.info(f"  文本 {len(user_text)} 字，分 {len(chunks)} 块处理")
        parts = []
        for i, chunk in enumerate(chunks, 1):
            log.info(f"  处理第 {i}/{len(chunks)} 块...")
            parts.append(_call_with_retry(client, cfg, system, chunk))
        return "\n\n".join(parts)

    return _call_with_retry(client, cfg, system, user_text)


def _split_by_paragraph(text: str, max_chars: int) -> list:
    paragraphs = text.split("\n")
    chunks, cur = [], ""
    for para in paragraphs:
        if len(cur) + len(para) > max_chars and cur:
            chunks.append(cur.strip())
            cur = para + "\n"
        else:
            cur += para + "\n"
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def _call_with_retry(client, cfg: dict, system: str, user: str) -> str:
    max_retries = cfg.get("max_retries", 3)
    timeout = cfg.get("timeout", 300)
    model = cfg["model"]

    for attempt in range(1, max_retries + 1):
        try:
            log.info(f"  调用 Ollama（第 {attempt} 次）...")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=timeout,
                temperature=0.3,
            )
            result = resp.choices[0].message.content.strip()
            log.info(f"  返回 {len(result)} 字")
            return result
        except Exception as e:
            log.warning(f"  调用失败（第 {attempt} 次）: {e}")
            if attempt < max_retries:
                wait = attempt * 8
                log.info(f"  等待 {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Ollama 调用失败，已重试 {max_retries} 次: {e}") from e
