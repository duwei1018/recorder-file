# Recorder-File — 方案设计文档

**版本**：v1.0  
**适用环境**：Windows 本地，Python 3.12，Ollama（Qwen），Whisper  
**目标**：将录音访谈自动转化为结构化研究文档，并与历史知识库形成推理印证

---

## 一、系统目标

### 核心三步（立即实现）
1. **转录**：录音文件 → 原始文字（Whisper 本地，完全离线）
2. **对话整理**：原始文字 → 问答对话格式（Qwen / Ollama）
3. **内容提炼**：对话 → 五维结构化摘要（Qwen / Ollama）

### 扩展功能（预留接口，后续激活）
4. **智能分类**：按行业 / 公司 / 话题自动打标签，归档到对应子目录
5. **知识库索引**：所有文档嵌入向量，构建本地语义检索库（ChromaDB）
6. **跨文档推理**：新访谈 × info-collector (Recorder-File) 历史文档 → 印证 / 矛盾 / 新发现

---

## 二、技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| 语音转录 | openai-whisper（medium模型） | 本地离线，中文效果好 |
| 大语言模型 | Qwen via Ollama | 已有本地部署，OpenAI兼容接口 |
| 向量数据库 | ChromaDB（本地文件存储） | 零服务依赖，数据存本机 |
| 文本嵌入 | ollama embed（nomic-embed-text） | 本地嵌入，不上传数据 |
| 配置管理 | YAML（config.yaml） | 所有参数集中管理 |
| 输出格式 | Markdown | 兼容 Obsidian，方便后续查看 |

---

## 三、项目结构

```
recorder-file/
│
├── main.py                  # 统一入口，命令行解析
├── config.yaml              # 所有配置（路径、模型名、参数）
├── requirements.txt         # Python 依赖
│
├── pipeline/                # 核心处理流水线
│   ├── __init__.py
│   ├── transcribe.py        # Step 1：Whisper 语音转录
│   ├── dialogue.py          # Step 2：对话格式整理
│   ├── summarize.py         # Step 3：结构化摘要提炼
│   └── classify.py          # Step 4：智能分类打标（预留）
│
├── knowledge/               # 知识库层（预留，后续激活）
│   ├── __init__.py
│   ├── store.py             # ChromaDB 读写接口
│   ├── indexer.py           # 文档嵌入 + 索引构建
│   └── retriever.py         # 语义检索
│
├── inference/               # 推理印证层（预留，后续激活）
│   ├── __init__.py
│   ├── engine.py            # 跨文档推理（调 Ollama）
│   └── query.py             # 命令行查询接口
│
├── utils/
│   ├── __init__.py
│   ├── cache.py             # 处理状态缓存（断点续跑）
│   ├── logger.py            # 统一日志
│   └── llm.py               # Ollama 调用封装（重试 + 分块）
│
└── 启动.ps1                  # Windows PowerShell 快捷启动脚本
```

---

## 四、数据流设计

```
录音文件（.mp3 / .m4a / .wav）
    │
    ▼
[Step 1] transcribe.py
    Whisper medium 模型
    输出：{文件名}_1_原始转录.md
    │
    ▼
[Step 2] dialogue.py
    Qwen via Ollama
    Prompt：识别提问者/受访者，整理为【提问】/【受访】格式
    输出：{文件名}_2_对话整理.md
    │
    ▼
[Step 3] summarize.py
    Qwen via Ollama
    输出五个维度：核心观点 / 关键数据 / 行业现状 / 风险挑战 / 后续关注点
    输出：{文件名}_3_研究摘要.md
    │
    ▼
[Step 4 预留] classify.py
    自动打标签（行业、公司、话题）
    按标签归档到子目录
    │
    ▼
[知识库 预留] indexer.py
    将三个 Markdown 文件嵌入向量
    存入本地 ChromaDB
    │
    ▼
[推理 预留] engine.py
    检索历史相关文档
    Qwen 做跨文档印证分析
    输出：印证报告（新发现 / 一致 / 矛盾）
```

---

## 五、输出文件规范

每个录音文件处理后，在输出目录生成：

```
访谈纪要/
├── {文件名}_1_原始转录.md
│     # Whisper 逐字输出，保留原始错误，供校对
│
├── {文件名}_2_对话整理.md
│     # 格式：
│     # **【提问】** 你们目前的毛利率大概在什么水平？
│     # **【受访】** 今年大概在 38% 左右，去年是 42%，主要受原材料...
│
└── {文件名}_3_研究摘要.md
      # 包含五维摘要 + 完整对话附录
      # ## 一、核心观点
      # ## 二、关键数据
      # ## 三、行业现状
      # ## 四、风险与挑战
      # ## 五、后续关注点
      # ---
      # ## 附：完整对话
```

---

## 六、稳定性设计

| 问题 | 解决方案 |
|------|---------|
| Whisper 每次重新加载 | 全局模型缓存，批量只加载一次 |
| Ollama 长文本超时 | 按段落分块（3000字/块），分批调用后合并 |
| 中途崩溃重启 | cache.json 记录每步完成状态，支持 `--step 2` 续跑 |
| 网络路径断开 | 启动时检查路径可访问性，明确报错 |
| Ollama 服务未启动 | 启动时 health check，给出具体提示 |
| 重复处理 | 按文件路径+大小的 MD5 跳过已完成文件 |

---

## 七、命令行接口

```bash
# 处理所有新文件
python main.py

# 只处理单个文件
python main.py --file "访谈20250327.mp3"

# 从指定步骤续跑（Step 1/2/3）
python main.py --step 2

# 强制重新处理所有文件
python main.py --force

# 使用更大的 Whisper 模型
python main.py --model large-v3

# 激活知识库索引（后续功能）
python main.py --index

# 跨文档推理查询（后续功能）
python main.py --query "这家公司的毛利率趋势如何"
```

---

## 八、config.yaml 结构

```yaml
paths:
  input_dir: "\\\\192.168.3.100\\homes\\duwei\\行业研究\\录音待转换"
  output_dir: "\\\\192.168.3.100\\homes\\duwei\\行业研究\\访谈纪要"
  knowledge_dir: "C:\\Users\\Administrator\\recorder-file\\knowledge_db"   # ChromaDB 存储位置

whisper:
  model: medium          # tiny / base / small / medium / large-v3
  language: zh

ollama:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5:14b"  # 按 ollama list 实际填写
  timeout: 300
  max_retries: 3
  chunk_chars: 3000      # 超过此字数自动分块

cache_file: "processed_cache.json"

audio_extensions:
  - .mp3
  - .wav
  - .m4a
  - .mp4
  - .flac
  - .ogg
  - .wma
  - .aac
```

---

## 九、未来扩展路线图

### 阶段一（现在）
- [x] 三步流水线（转录 → 对话 → 摘要）
- [x] 断点续跑 + 缓存
- [x] Ollama 分块重试

### 阶段二（1-2个月后）
- [ ] 智能分类：Qwen 自动判断行业 / 公司 / 话题，归档到子目录
- [ ] 本地向量库：ChromaDB + nomic-embed-text 嵌入所有文档
- [ ] info-collector (Recorder-File) 文档接入：将现有研究文档一并索引

### 阶段三（之后）
- [ ] 跨文档推理：新访谈自动检索历史相关内容，生成印证报告
- [ ] 命令行语义查询：`--query "某公司毛利率"` 返回所有相关访谈片段
- [ ] 矛盾检测：同一话题在不同访谈中的说法差异自动标注
- [ ] Web UI（可选）：Gradio 本地前端，拖入录音即处理

---

## 十、依赖清单

```
# requirements.txt
openai-whisper>=20231117
openai>=1.0.0
PyYAML>=6.0
chromadb>=0.4.0          # 阶段二激活
tqdm>=4.0.0
```

安装命令：
```bash
py -3.12 -m pip install openai-whisper openai PyYAML tqdm
```
