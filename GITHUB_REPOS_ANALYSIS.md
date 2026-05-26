# GitHub 勞基法相關 Repo 分析報告

## 1. BossBuster (Pelly0524) — 本專案母 repo
**URL:** https://github.com/Pelly0524/BossBuster

### 資料內容
- 台灣勞基法條文及相關法規
- LINE Bot + RAG 系統架構

### 資料格式
- 根目錄結構簡潔：README、.gitignore、boss_buster_bot/ 目錄
- **無獨立 data/ 或 corpus/ 目錄**（法條資料應在 boss_buster_bot/ 內或待補充）

### 資料版本
- 未在 API 回應中顯示具體時間（需檢查 git log）

### 特點
- 專注 LINE 整合與 RAG 應用
- 資料結構單純，適合作為專案基底
- **關鍵問題**：內部無可見資料目錄，可能尚未實現完整資料層

---

## 2. LamaIndexRAG (jaujye)
**URL:** https://github.com/jaujye/LamaIndexRAG

### 資料內容
- **多領域法律資料**：勞基法、食品安全法、民法
- 自動爬取台灣司法院網站
- 統一 LegalArticle 資料模型（章節、條號、條文、中繼資料）

### 資料格式
- 結構化：config/, src/, docs/, scripts/, results/ 等目錄
- **向量化存儲**：ChromaDB（不直接暴露原始檔案）
- OpenAI embedding
- 資料應在 src/ 內處理

### 資料版本
- main.py / main_legacy.py / ultrathink.py 表示持續開發
- **相對活躍**

### 特點
- 多法律領域通用設計
- 向量檢索 + LLM 生成
- 設計較為成熟，但需 OpenAI API

---

## 3. Law-Chatbot (sway-maker)
**URL:** https://github.com/sway-maker/Law-Chatbot

### 資料內容
- 勞基法條文（文本檔案逐行儲存）
- Q&A 評估資料集（labor_law_qa.docx）

### 資料格式
- **TXT 檔案**：法條原文逐行結構
- **DOCX 檔案**：labor_law_qa.docx（含約 200 個 Q&A 評估資料）
- **混合檢索**：BM25 全文搜尋 + FAISS 向量 + RRF 融合
- **LLM**：Gemma-3-4B-it（開源、本地可運行）

### 資料版本
- 簡潔結構：File/、image/、interface.py、main_code.py
- **資料目錄不透明**（File/ 內容具體結構需深入探查）

### 特點
- **專注勞基法單一領域**（與本專案最接近）
- 結合全文檢索 + 向量檢索（混合策略）
- 包含 K-Fold 驗證機制（評估模型效能）
- 開源 LLM，無 API 費用

---

## 4. law-rag-chatbot (jojostarking)
**URL:** https://github.com/jojostarking/law-rag-chatbot

### 資料內容
- **完整台灣法律資料庫**（勞基法、民法、刑法等）
- **直接暴露原始資料檔**

### 資料格式
- **TXT 格式**：law.txt（656 KB）
- **JSON 格式**：laws_for_rag.json（862 KB）
  - 結構化法律條文，含中文名稱、法律編號
  - 可直接解析和展示
- **Python 腳本**：parse_laws.py（解析）、build_db.py（建庫）、rag_query.py（查詢）
- **向量化**：ChromaDB + Gemini API

### 資料版本
- 檔案大小（656 KB + 862 KB）表示內容豐富
- **最可能為最新版本**（2023 後修正待驗證）

### 特點
- **最完整且易用的資料檔**（可直接下載 JSON/TXT）
- 雙格式存儲（易於檢索和展示）
- 直接暴露原始資料，利於二次開發
- 完整的解析 + 建庫 + 查詢 pipeline

---

## 資料對比表

| 項目 | BossBuster | LamaIndexRAG | Law-Chatbot | law-rag-chatbot |
|------|-----------|-------------|-----------|-----------------|
| **資料完整性** | 低（待實現） | 中（多領域） | 中（勞基法） | **高（全法律）** |
| **資料格式** | 待定 | 向量DB | TXT + DOCX | **TXT + JSON** |
| **施行細則** | 不明 | 不明 | 可能包含 | **待驗證** |
| **函釋** | 不明 | 不明 | 不明 | **待驗證** |
| **判例** | 不明 | 不明 | 不明 | **待驗證** |
| **下載便利性** | 低 | 低 | 低 | **高** |
| **活躍度** | 不明 | 活躍 | 不明 | 待驗證 |

---

## 立即行動建議

### 第一優先：驗證 law-rag-chatbot 資料
```bash
# 下載並查看 laws_for_rag.json 前 100 行
# 檢查項目：
# 1. 是否包含施行細則（多出 3 萬筆以上）
# 2. 是否包含函釋（會有 interpret/decree 標籤）
# 3. 是否包含判例（會有 case law / ruling 標籤）
# 4. 資料版本欄位內容（修正年月）
```

### 第二優先：檢視 Law-Chatbot 的 Q&A 資料集
```bash
# 下載 labor_law_qa.docx
# 評估其 Q&A 涵蓋範圍，作為本專案驗證集參考
```

### 第三優先：深入 BossBuster 內部
```bash
# 確認 boss_buster_bot/ 目錄是否已有法條資料層
# 若無，可考慮參考 law-rag-chatbot 的 JSON 格式
```

---

## 200 字以內版本（各 repo 簡報）

**BossBuster**（本體）：LINE Bot RAG 框架，無可見資料目錄，侷限性未明。

**LamaIndexRAG**：多領域法律通用系統（勞基法、食安、民法），向量DB 架構，需 OpenAI API。

**Law-Chatbot**：勞基法專用，TXT 格式法條 + DOCX 評估資料，BM25+FAISS 混合檢索，開源 Gemma LLM，最接近需求。

**law-rag-chatbot**：完整台灣法律庫，直接提供 laws_for_rag.json（862 KB）與 law.txt，資料最豐富且易用，涵蓋多法律領域，版本待驗證。
