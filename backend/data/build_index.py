"""
建立法律語料庫的向量索引。

執行方式：
    cd backend
    python -m data.build_index

執行後會在 CHROMA_PATH 建立 ChromaDB 集合。
"""
import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 必須在 import domain 前設定好 path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from sentence_transformers import SentenceTransformer

from data.crawlers.statute_fetcher import StatuteFetcher
from data.crawlers.laws_for_rag_importer import fetch_related_laws
from data.loaders.judgment_loader import load_judgment_chunks
from data.loaders.arbitration_loader import load_arbitration_chunks

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "labor_law"
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"
CACHE_PATH = Path(__file__).parent / "raw_chunks_cache.json"


def load_all_chunks() -> list[dict]:
    chunks = []

    # 1. 勞基法 + 施行細則
    logger.info("== 爬取勞基法全文 ==")
    for chunk in StatuteFetcher().fetch_chunks():
        chunks.append(chunk.__dict__)

    # 2. 判決（手動 JSON）
    logger.info("== 載入判決資料 ==")
    for chunk in load_judgment_chunks():
        chunks.append(chunk.__dict__)

    # 3. 仲裁決定（手動 JSON）
    logger.info("== 載入仲裁資料 ==")
    for chunk in load_arbitration_chunks():
        chunks.append(chunk.__dict__)

    # 4. 相關法規（最低工資法、性別平等工作法、勞工請假規則等）
    # 來源：jojostarking/law-rag-chatbot（GitHub 靜態 JSON，網路不通時安靜略過）
    logger.info("== 引入相關法規（GitHub）==")
    for chunk in fetch_related_laws():
        chunks.append(chunk.__dict__)

    # 5. 勞動部函釋（2020 年後，最多 8 頁）
    # 來源：laws.mol.gov.tw，需連網；爬取失敗時安靜略過
    logger.info("== 爬取勞動部函釋 ==")
    try:
        from data.crawlers.interpretation_fetcher import InterpretationFetcher
        for chunk in InterpretationFetcher(start_year=2020, max_pages=8).fetch_chunks():
            chunks.append(chunk.__dict__)
    except Exception as e:
        logger.warning("函釋爬取失敗（%s），跳過。RAG 仍可使用法條語料運作。", e)

    return chunks


def build_index(chunks: list[dict]) -> None:
    if not chunks:
        logger.error("No chunks to index!")
        return

    logger.info("== 建立向量索引（%d chunks）==", len(chunks))
    embed_model = SentenceTransformer(EMBED_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # 若已存在則刪除重建（確保索引是最新的）
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # 去重複（以 chunk_id 為準，若重複則加序號）
    seen: dict[str, int] = {}
    deduped = []
    for c in chunks:
        cid = c["chunk_id"]
        if cid in seen:
            seen[cid] += 1
            c = {**c, "chunk_id": f"{cid}_{seen[cid]}"}
        else:
            seen[cid] = 0
        deduped.append(c)
    chunks = deduped
    logger.info("After dedup: %d chunks", len(chunks))

    # 分批 embed（避免記憶體不足）
    BATCH = 64
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        texts = [c["text"] for c in batch]
        embeddings = embed_model.encode(texts, normalize_embeddings=True).tolist()
        collection.add(
            ids=[c["chunk_id"] for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "doc_type": c["doc_type"],
                    "article_no": c["article_no"],
                    "title": c["title"],
                    "source_url": c.get("source_url", ""),
                    "date": c.get("date", ""),
                }
                for c in batch
            ],
        )
        logger.info("  Indexed %d / %d", min(i + BATCH, len(chunks)), len(chunks))

    logger.info("✓ 索引完成，共 %d 筆，存於 %s", len(chunks), CHROMA_PATH)


def main():
    chunks = load_all_chunks()
    logger.info("共取得 %d 個 chunks", len(chunks))

    # 快取原始 chunks（方便 BM25 離線載入，不需重新爬蟲）
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    logger.info("原始 chunks 已快取至 %s", CACHE_PATH)

    build_index(chunks)


if __name__ == "__main__":
    main()
