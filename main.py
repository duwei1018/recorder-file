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
