# Recorder-File — Claude Code 执行文档

> 将此文档发给 Claude Code，它会按顺序完整执行所有步骤。
> 执行前请确认：Ollama 已运行，Python 3.12 已安装。

---

## 执行目标

在 `C:\Users\Administrator\recorder-file\` 目录下创建完整的行业研究录音处理系统，包含：
- 模块化项目结构（pipeline / utils 层）
- 完整可运行的三步流水线（Whisper 转录 + Ollama 对话整理 + 摘要提炼）
- 统一配置文件（config.yaml）
- 断点续跑 + 自动重试机制
- 知识库层和推理层的预留接口（空模块，后续激活）
- PowerShell 启动脚本

---

## 第一步：创建项目目录结构

```bash
mkdir C:\Users\Administrator\recorder-file
cd C:\Users\Administrator\recorder-file
mkdir pipeline knowledge inference utils
```

为每个子目录创建 `__init__.py`：

```bash
echo "" > pipeline\__init__.py
echo "" > knowledge\__init__.py
echo "" > inference\__init__.py
echo "" > utils\__init__.py
```

---

## 第二步：创建 config.yaml

在 `C:\Users\Administrator\recorder-file\config.yaml` 创建以下内容：

```yaml
paths:
  # 录音文件输入目录（本地或 UNC 网络路径）
  input_dir: "\\\\192.168.3.100\\homes\\duwei\\行业研究\\录音待转换"
  # 输出目录
  output_dir: "\\\\192.168.3.100\\homes\\duwei\\行业研究\\访谈纪要"
  # 知识库存储位置（阶段二激活）
  knowledge_dir: "C:\\Users\\Administrator\\recorder-file\\knowledge_db"

whisper:
  model: medium          # tiny / base / small / medium / large-v3
  language: zh
  fp16: false            # CPU 推理设 false

ollama:
  base_url: "http://localhost:11434/v1"
  api_key: "ollama"
  model: "qwen2.5:14b"  # 按 ollama list 实际填写
  timeout: 300
  max_retries: 3
  chunk_chars: 3000

cache_file: "C:\\Users\\Administrator\\recorder-file\\processed_cache.json"

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

## 第三步：创建 utils/logger.py

```python
# utils/logger.py
import logging
import sys
from pathlib import Path

def setup_logger(log_file: str = "C:\\Users\\Administrator\\recorder-file\\agent.log") -> logging.Logger:
    logger = logging.getLogger("recorder_file")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger

log = setup_logger()
```

---

## 第四步：创建 utils/cache.py

```python
# utils/cache.py
import json
import hashlib
from pathlib import Path

def file_id(path: Path) -> str:
    """根据文件路径和大小生成唯一 ID"""
    return hashlib.md5(f"{path}|{path.stat().st_size}".encode()).hexdigest()

def load_cache(cache_path: str) -> dict:
    p = Path(cache_path)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}

def save_cache(cache: dict, cache_path: str):
    Path(cache_path).write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

---

## 第五步：创建 utils/llm.py

```python
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
```

---

## 第六步：创建 pipeline/transcribe.py

```python
# pipeline/transcribe.py
"""
Step 1：使用 Whisper 将音频文件转录为文字。
模型全局缓存，批量处理时只加载一次。
"""
import sys
from pathlib import Path
from datetime import datetime
from utils.logger import log

_model_cache: dict = {}


def transcribe(audio_path: Path, cfg: dict) -> str:
    """转录音频，返回纯文字字符串"""
    try:
        import whisper
    except ImportError:
        log.error("请先执行: pip install openai-whisper")
        sys.exit(1)

    model_name = cfg["whisper"]["model"]

    if model_name not in _model_cache:
        log.info(f"  加载 Whisper [{model_name}]（首次需下载，请稍候）...")
        _model_cache[model_name] = whisper.load_model(model_name)

    model = _model_cache[model_name]
    log.info(f"  开始转录: {audio_path.name}")

    result = model.transcribe(
        str(audio_path),
        language=cfg["whisper"].get("language", "zh"),
        verbose=False,
        fp16=cfg["whisper"].get("fp16", False),
    )
    text = result["text"].strip()
    log.info(f"  转录完成，共 {len(text)} 字")
    return text


def run(audio_path: Path, output_dir: Path, cfg: dict) -> str:
    """执行 Step 1，落盘并返回文字内容"""
    text = transcribe(audio_path, cfg)
    out_path = output_dir / f"{audio_path.stem}_1_原始转录.md"
    out_path.write_text(
        f"# 原始转录 — {audio_path.stem}\n\n"
        f"> 转录时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{text}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return text
```

---

## 第七步：创建 pipeline/dialogue.py

```python
# pipeline/dialogue.py
"""
Step 2：将原始转录文字整理成问答对话格式。
"""
from pathlib import Path
from datetime import datetime
from utils.llm import call_llm
from utils.logger import log

SYSTEM = """你是一位专业的访谈记录整理员。
将原始录音转录文字整理成清晰的问答对话格式。

规则：
- 识别提问者（研究员/分析师）和受访者（行业专家/公司人员）
- 格式：
  **【提问】** 问题内容
  **【受访】** 回答内容
- 若无法区分说话人，按话题分段并加小标题
- 修正明显口语错误，保留原意、专业术语和数字
- 输出纯 Markdown，不加任何额外解释"""


def run(raw_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> str:
    log.info("  整理对话格式...")
    prompt = f"请将以下转录文字整理成对话格式：\n\n{raw_text}"
    dialogue = call_llm(SYSTEM, prompt, cfg["ollama"])

    out_path = output_dir / f"{audio_stem}_2_对话整理.md"
    out_path.write_text(
        f"# 访谈对话 — {audio_stem}\n\n"
        f"> 整理时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{dialogue}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return dialogue
```

---

## 第八步：创建 pipeline/summarize.py

```python
# pipeline/summarize.py
"""
Step 3：从对话中提炼五维结构化研究摘要。
"""
from pathlib import Path
from datetime import datetime
from utils.llm import call_llm
from utils.logger import log

SYSTEM = """你是一位专业的行业研究分析师。
从访谈对话中提炼关键信息，生成结构化研究摘要。

严格按以下格式输出 Markdown（五个部分，缺失的写"暂无明确提及"）：

## 一、核心观点
- （每条一行，3-5条）

## 二、关键数据
（具体数字、比例、时间节点、金额）

## 三、行业现状
（市场规模、竞争格局、供需关系、上下游）

## 四、风险与挑战
（受访者提及的风险点、政策影响、竞争压力）

## 五、后续关注点
（值得深入研究的问题、需要验证的假设）"""


def run(dialogue_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> str:
    log.info("  提炼研究摘要...")
    prompt = f"请根据以下访谈对话提炼关键信息：\n\n{dialogue_text}"
    summary = call_llm(SYSTEM, prompt, cfg["ollama"])

    out_path = output_dir / f"{audio_stem}_3_研究摘要.md"
    out_path.write_text(
        f"# 研究摘要 — {audio_stem}\n\n"
        f"> 提炼时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{summary}\n\n"
        f"---\n\n"
        f"## 附：完整对话\n\n{dialogue_text}",
        encoding="utf-8",
    )
    log.info(f"  已保存: {out_path.name}")
    return summary
```

---

## 第九步：创建 pipeline/classify.py（预留模块）

```python
# pipeline/classify.py
"""
Step 4：智能分类打标签（预留，阶段二激活）
当前版本：空实现，不影响主流程运行
"""
from pathlib import Path
from utils.logger import log


def run(summary_text: str, audio_stem: str, output_dir: Path, cfg: dict) -> dict:
    """
    TODO（阶段二）：
    1. 让 Ollama 从摘要中提取：行业、公司名、核心话题
    2. 按分类在 output_dir 下创建子目录
    3. 将三个 Markdown 文件复制/移动到对应子目录
    返回：{"industry": "...", "company": "...", "topics": [...]}
    """
    log.info("  [classify] 分类模块预留，暂未激活")
    return {}
```

---

## 第十步：创建知识库预留模块

### knowledge/store.py

```python
# knowledge/store.py
"""
ChromaDB 本地向量库接口（预留，阶段二激活）
"""
from utils.logger import log


class KnowledgeStore:
    """
    TODO（阶段二）：
    import chromadb
    self.client = chromadb.PersistentClient(path=cfg["paths"]["knowledge_dir"])
    self.collection = self.client.get_or_create_collection("research_docs")
    """
    def __init__(self, cfg: dict):
        log.info("  [KnowledgeStore] 知识库模块预留，暂未激活")

    def add_document(self, doc_id: str, text: str, metadata: dict):
        pass

    def query(self, query_text: str, n_results: int = 5) -> list:
        return []
```

### knowledge/indexer.py

```python
# knowledge/indexer.py
"""
文档嵌入 + 索引构建（预留，阶段二激活）
"""
from pathlib import Path
from utils.logger import log


def index_directory(directory: Path, store, cfg: dict):
    """
    TODO（阶段二）：
    遍历目录下所有 Markdown 文件（包括 Recorder-File 的 info-collector 的文档）
    调用 ollama embed 生成嵌入向量
    写入 KnowledgeStore
    """
    log.info(f"  [indexer] 索引模块预留：{directory}")
```

### knowledge/retriever.py

```python
# knowledge/retriever.py
"""
语义检索（预留，阶段二激活）
"""
from utils.logger import log


def retrieve(query: str, store, n: int = 5) -> list:
    """
    TODO（阶段二）：
    从 KnowledgeStore 检索与 query 最相关的 n 条文档片段
    返回：[{"text": "...", "source": "...", "score": 0.xx}, ...]
    """
    log.info(f"  [retriever] 检索模块预留: {query}")
    return []
```

---

## 第十一步：创建推理预留模块

### inference/engine.py

```python
# inference/engine.py
"""
跨文档推理印证引擎（预留，阶段三激活）
"""
from utils.logger import log


def cross_document_inference(new_summary: str, related_docs: list, cfg: dict) -> str:
    """
    TODO（阶段三）：
    system: 你是行业研究分析师，对比新访谈与历史文档，找出印证/矛盾/新发现
    user: 新访谈摘要 + 检索到的历史文档片段
    输出：结构化印证报告
    """
    log.info("  [inference] 推理引擎预留，暂未激活")
    return ""
```

### inference/query.py

```python
# inference/query.py
"""
命令行语义查询接口（预留，阶段三激活）
"""
from utils.logger import log


def query_knowledge(question: str, store, cfg: dict) -> str:
    """
    TODO（阶段三）：
    python main.py --query "某公司的毛利率趋势"
    → 检索相关文档片段 → Ollama 综合回答 → 输出含来源引用的答案
    """
    log.info(f"  [query] 查询接口预留: {question}")
    return "查询接口尚未激活，请等待阶段三实现。"
```

---

## 第十二步：创建 main.py

```python
# main.py
"""
Recorder-File — 主入口
用法见 README 或 python main.py --help
"""
import sys
import argparse
import textwrap
import urllib.request
from pathlib import Path
from datetime import datetime

import yaml

from utils.logger import log
from utils.cache import file_id, load_cache, save_cache
import pipeline.transcribe as step1
import pipeline.dialogue  as step2
import pipeline.summarize as step3


# ── 配置加载 ─────────────────────────────────────────────
def load_config(config_path: str = "C:\\Users\\Administrator\\recorder-file\\config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 环境检查 ─────────────────────────────────────────────
def check_env(cfg: dict) -> bool:
    ok = True
    input_dir = Path(cfg["paths"]["input_dir"])
    if not input_dir.exists():
        log.error(f"输入目录不存在: {input_dir}")
        log.error("请检查网络共享是否已挂载，或 VPN 是否已连接")
        ok = False

    try:
        base = cfg["ollama"]["base_url"].replace("/v1", "").rstrip("/")
        urllib.request.urlopen(base, timeout=5)
        log.info(f"Ollama 在线  模型: {cfg['ollama']['model']}")
    except Exception:
        log.warning("Ollama 未响应，请确认 `ollama serve` 已运行")
        log.warning("若使用 LM Studio，请修改 config.yaml 中的 base_url")

    return ok


# ── 单文件流水线 ──────────────────────────────────────────
def process_file(audio_path: Path, output_dir: Path, cfg: dict, start_step: int) -> bool:
    stem = audio_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path      = output_dir / f"{stem}_1_原始转录.md"
    dialogue_path = output_dir / f"{stem}_2_对话整理.md"

    try:
        # Step 1
        if start_step <= 1:
            log.info(f"[Step 1] 语音转文字: {audio_path.name}")
            raw_text = step1.run(audio_path, output_dir, cfg)
        else:
            if not raw_path.exists():
                log.error(f"找不到原始转录文件，请从 --step 1 重新开始")
                return False
            raw_text = "\n\n".join(raw_path.read_text(encoding="utf-8").split("\n\n")[2:])
            log.info(f"[Step 1] 读取已有转录: {raw_path.name}")

        # Step 2
        if start_step <= 2:
            log.info(f"[Step 2] 整理对话格式")
            dialogue_text = step2.run(raw_text, stem, output_dir, cfg)
        else:
            if not dialogue_path.exists():
                log.error(f"找不到对话整理文件，请从 --step 2 重新开始")
                return False
            dialogue_text = "\n\n".join(dialogue_path.read_text(encoding="utf-8").split("\n\n")[2:])
            log.info(f"[Step 2] 读取已有对话: {dialogue_path.name}")

        # Step 3
        if start_step <= 3:
            log.info(f"[Step 3] 提炼研究摘要")
            step3.run(dialogue_text, stem, output_dir, cfg)

        log.info(f"[完成] {audio_path.name}")
        return True

    except Exception as e:
        log.error(f"[失败] {audio_path.name}: {e}", exc_info=True)
        return False


# ── 主流程 ────────────────────────────────────────────────
def run(args):
    cfg = load_config()
    input_dir  = Path(args.input  or cfg["paths"]["input_dir"])
    output_dir = Path(args.output or cfg["paths"]["output_dir"])
    start_step = int(args.step)

    log.info("=" * 55)
    log.info("Recorder-File  v1.0")
    log.info("=" * 55)

    if not check_env(cfg):
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 修改配置中的 model（命令行参数优先）
    if args.model:
        cfg["whisper"]["model"] = args.model

    # 找音频文件
    if args.file:
        audio_files = [Path(args.file)]
        if not audio_files[0].exists():
            log.error(f"文件不存在: {args.file}")
            sys.exit(1)
    else:
        audio_files = []
        for ext in cfg.get("audio_extensions", [".mp3", ".wav", ".m4a"]):
            audio_files.extend(input_dir.glob(f"*{ext}"))
            audio_files.extend(input_dir.glob(f"*{ext.upper()}"))
        audio_files = sorted(set(audio_files))

    if not audio_files:
        log.warning(f"在 {input_dir} 中未找到音频文件")
        return

    log.info(f"找到 {len(audio_files)} 个文件，从 Step {start_step} 开始")

    cache = load_cache(cfg["cache_file"])
    success = skipped = failed = 0

    for audio_path in audio_files:
        fid = file_id(audio_path)
        if cache.get(fid, {}).get("done") and not args.force and start_step == 1:
            log.info(f"跳过（已完成）: {audio_path.name}")
            skipped += 1
            continue

        ok = process_file(audio_path, output_dir, cfg, start_step)
        if ok:
            cache[fid] = {"file": audio_path.name, "done": True,
                          "processed_at": datetime.now().isoformat()}
            save_cache(cache, cfg["cache_file"])
            success += 1
        else:
            failed += 1

    log.info("=" * 55)
    log.info(f"完成 | 成功:{success}  跳过:{skipped}  失败:{failed}")
    log.info(f"输出目录: {output_dir}")


# ── CLI ───────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Recorder-File 行业研究录音处理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        示例：
          python main.py                            # 处理所有新文件
          python main.py --file 访谈.mp3            # 只处理单个文件
          python main.py --step 2                   # 从对话整理步骤开始
          python main.py --step 3 --force           # 重新生成所有摘要
          python main.py --model large-v3           # 使用更大的 Whisper 模型
        """),
    )
    p.add_argument("--input",  "-i", help="输入目录（覆盖 config.yaml）")
    p.add_argument("--output", "-o", help="输出目录（覆盖 config.yaml）")
    p.add_argument("--file",   "-F", help="只处理指定的单个音频文件")
    p.add_argument("--step",   "-s", choices=["1","2","3"], default="1",
                   help="从哪步开始：1=转录(默认) 2=对话整理 3=摘要提炼")
    p.add_argument("--force",  "-f", action="store_true", help="强制重新处理所有文件")
    p.add_argument("--model",  "-m", help="Whisper 模型 (tiny/base/small/medium/large-v3)")
    args = p.parse_args()
    run(args)
```

---

## 第十三步：创建 requirements.txt

```
openai-whisper>=20231117
openai>=1.0.0
PyYAML>=6.0
tqdm>=4.0.0
```

---

## 第十四步：创建 启动.ps1

```powershell
# 启动.ps1 — 双击运行
$PythonExe = "py -3.12"
$ScriptDir = "C:\Users\Administrator\recorder-file"

Set-Location $ScriptDir

Write-Host "[Recorder-File]" -ForegroundColor Cyan
Write-Host ""
Write-Host "1  处理所有新文件"
Write-Host "2  强制重新处理所有文件"
Write-Host "3  只处理单个文件"
Write-Host "4  从 Step 2（对话整理）续跑"
Write-Host "5  从 Step 3（摘要提炼）续跑"
Write-Host ""
$c = (Read-Host "选项").Trim()

switch ($c) {
    "1" { Invoke-Expression "$PythonExe main.py" }
    "2" { Invoke-Expression "$PythonExe main.py --force" }
    "3" {
        $f = (Read-Host "文件完整路径").Trim().Trim('"')
        Invoke-Expression "$PythonExe main.py --file `"$f`""
    }
    "4" { Invoke-Expression "$PythonExe main.py --step 2 --force" }
    "5" { Invoke-Expression "$PythonExe main.py --step 3 --force" }
    default { Invoke-Expression "$PythonExe main.py" }
}

Write-Host ""
Write-Host "完成。日志: C:\Users\Administrator\recorder-file\agent.log" -ForegroundColor Green
pause
```

---

## 第十五步：安装依赖并验证

执行以下命令安装依赖：

```bash
py -3.12 -m pip install openai-whisper openai PyYAML tqdm
```

验证安装：

```bash
py -3.12 -c "import whisper; import openai; import yaml; print('所有依赖安装成功')"
```

---

## 第十六步：测试运行

### 用本地文件测试（不依赖网络共享）

```bash
cd C:\Users\Administrator\recorder-file
py -3.12 main.py --file "C:\path\to\test_audio.mp3" --output "C:\Users\Administrator\recorder-file\test_output"
```

### 正式运行

```bash
py -3.12 main.py
```

或双击 `启动.ps1`。

---

## 验证检查清单

Claude Code 执行完成后，请确认以下文件存在：

```
C:\Users\Administrator\recorder-file\
├── main.py                     ✓
├── config.yaml                 ✓
├── requirements.txt            ✓
├── 启动.ps1                    ✓
├── pipeline\
│   ├── __init__.py             ✓
│   ├── transcribe.py           ✓
│   ├── dialogue.py             ✓
│   ├── summarize.py            ✓
│   └── classify.py             ✓（预留）
├── knowledge\
│   ├── __init__.py             ✓
│   ├── store.py                ✓（预留）
│   ├── indexer.py              ✓（预留）
│   └── retriever.py            ✓（预留）
├── inference\
│   ├── __init__.py             ✓
│   ├── engine.py               ✓（预留）
│   └── query.py                ✓（预留）
└── utils\
    ├── __init__.py             ✓
    ├── logger.py               ✓
    ├── cache.py                ✓
    └── llm.py                  ✓
```

---

## 常见问题

**Q: config.yaml 里的模型名怎么填？**
运行 `ollama list`，把第一列的模型名填入 `ollama.model`

**Q: 网络路径访问失败？**
先在资源管理器确认可以打开 `\\192.168.3.100\homes\duwei\`，再运行脚本

**Q: Whisper 下载模型很慢？**
medium 模型约 1.5GB，首次需要联网下载，之后完全离线

**Q: 某步失败了怎么续跑？**
`python main.py --step 2` 从对话整理开始，`--step 3` 从摘要开始，不需要重新转录
