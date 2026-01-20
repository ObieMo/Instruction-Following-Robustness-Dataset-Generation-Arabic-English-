import json
import time
from pathlib import Path
from tqdm import tqdm
import yaml
from dotenv import load_dotenv

from src.llm_client import chat
from src.validate import is_valid_chosen, is_valid_rejected, basic_clean
from src.generate_prompts import write_prompts


def load_jsonl_with_index(path):
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if line.strip():
                yield idx, json.loads(line)


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def load_progress(progress_path: Path):
    if progress_path.exists() and progress_path.stat().st_size > 0:
        return json.loads(progress_path.read_text(encoding="utf-8"))
    return {"last_idx": -1, "saved": 0}


def save_progress(progress_path: Path, last_idx: int, saved: int):
    progress_path.write_text(
        json.dumps({"last_idx": last_idx, "saved": saved}, ensure_ascii=False),
        encoding="utf-8",
    )


def append_final(final_path: Path, prompt: str, chosen: str, rejected: str):
    rec = {
        "prompt": [{"role": "user", "content": prompt}],
        "chosen": [{"role": "assistant", "content": chosen}],
        "rejected": [{"role": "assistant", "content": rejected}],
    }
    with open(final_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def call_with_retry(messages, *, max_tokens, temperature, retries=6, base_sleep=2.0):
    """
    Retries transient connection errors with exponential backoff.
    """
    for attempt in range(retries):
        try:
            return basic_clean(chat(messages, max_tokens=max_tokens, temperature=temperature))
        except Exception as e:
            # Only retry on connection-type failures
            name = e.__class__.__name__.lower()
            msg = str(e).lower()
            retryable = ("connection" in name) or ("timeout" in name) or ("connection" in msg) or ("timed out" in msg)
            if not retryable or attempt == retries - 1:
                raise
            sleep_s = base_sleep * (2 ** attempt)
            time.sleep(sleep_s)
    return ""


def generate_first_answer(prompt, cfg):
    max_tokens = cfg["chosen"]["max_tokens"]
    temperature = cfg["chosen"]["temperature"]
    msgs = [
        {"role": "system", "content": "أنت مساعد مفيد. أجب مباشرة دون أي تفكير ظاهر."},
        {"role": "user", "content": prompt},
    ]
    return call_with_retry(msgs, max_tokens=max_tokens, temperature=temperature)


def regenerate_arabic(prompt, cfg):
    max_tokens = cfg["chosen"]["max_tokens"]
    temperature = cfg["chosen"]["temperature"]
    msgs = [
        {"role": "system", "content": "أنت مساعد مفيد. أجب باللغة العربية فقط دون أي كلمات إنجليزية. أعطِ الجواب النهائي فقط."},
        {"role": "user", "content": prompt},
    ]
    return call_with_retry(msgs, max_tokens=max_tokens, temperature=temperature)


def make_rejected_from_chosen(chosen_ar, cfg):
    max_tokens = cfg["rejected"]["max_tokens"]
    temperature = cfg["rejected"]["temperature"]
    msgs = [
        {
            "role": "system",
            "content": (
                "You are a rewriting engine. Rewrite exactly the provided TEXT into natural English. "
                "Output ONLY the rewritten English text. No questions, no commentary."
            ),
        },
        {"role": "user", "content": f"TEXT:\n{chosen_ar}\n\nENGLISH OUTPUT:"},
    ]
    return call_with_retry(msgs, max_tokens=max_tokens, temperature=temperature)


def judge_relevance_arabic(prompt_ar: str, answer_ar: str, cfg) -> bool:
    j = cfg.get("judge", {}) or {}
    if not j.get("enabled", False):
        return True

    msgs = [
        {"role": "system", "content": "Reply ONLY with YES or NO."},
        {"role": "user", "content": f"Question (Arabic): {prompt_ar}\nAnswer (Arabic): {answer_ar}\nDoes the answer address the question?"},
    ]
    out = call_with_retry(
        msgs,
        max_tokens=int(j.get("max_tokens", 30)),
        temperature=float(j.get("temperature", 0.0)),
    ).upper()
    return out.startswith("YES")


def main():
    load_dotenv()
    cfg = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))

    out_dir = Path(cfg["paths"]["out_dir"])
    ensure_dir(out_dir)

    prompts_path = out_dir / cfg["paths"]["prompts_file"]
    final_path = out_dir / cfg["paths"]["final_file"]
    progress_path = out_dir / "progress.json"

    # Generate prompts if missing/empty
    if (not prompts_path.exists()) or (prompts_path.stat().st_size == 0):
        write_prompts(str(prompts_path), cfg["n_prompts"], seed=42)

    v = cfg["validation"]
    target_final = int(cfg["target_final"])

    # Load progress
    prog = load_progress(progress_path)
    last_idx = int(prog.get("last_idx", -1))
    saved = int(prog.get("saved", 0))

    # If final file doesn't exist but progress says we saved, reset progress (safety)
    if saved > 0 and (not final_path.exists()):
        saved = 0
        last_idx = -1
        save_progress(progress_path, last_idx, saved)

    # Judge config
    j = cfg.get("judge", {}) or {}
    judge_enabled = bool(j.get("enabled", False))
    judge_every_n = int(j.get("every_n", 10))

    pbar = tqdm(desc="Generating triples", total=target_final, initial=saved)

    try:
        for idx, rec in load_jsonl_with_index(prompts_path):
            if idx <= last_idx:
                continue
            if saved >= target_final:
                break

            prompt = rec["prompt"]

            # HYBRID
            first = generate_first_answer(prompt, cfg)
            chosen = ""
            rejected = ""

            if is_valid_chosen(first, min_chars=v["min_chars"], arabic_ratio_min=v["arabic_ratio_min"]):
                chosen = first
            elif is_valid_rejected(first, min_chars=v["min_chars"], english_ratio_min=v["english_ratio_min"]):
                rejected = first

            if not chosen:
                chosen = regenerate_arabic(prompt, cfg)

            if not is_valid_chosen(chosen, min_chars=v["min_chars"], arabic_ratio_min=v["arabic_ratio_min"]):
                last_idx = idx
                save_progress(progress_path, last_idx, saved)
                continue

            if judge_enabled and (saved % judge_every_n == 0):
                if not judge_relevance_arabic(prompt, chosen, cfg):
                    last_idx = idx
                    save_progress(progress_path, last_idx, saved)
                    continue

            if not rejected:
                rejected = ""
                for _ in range(3):
                    rejected = make_rejected_from_chosen(chosen, cfg)
                    if is_valid_rejected(rejected, min_chars=v["min_chars"], english_ratio_min=v["english_ratio_min"]):
                        break
                    rejected = ""
                if not rejected:
                    last_idx = idx
                    save_progress(progress_path, last_idx, saved)
                    continue

            # WRITE IMMEDIATELY (checkpoint!)
            append_final(final_path, prompt, chosen, rejected)
            saved += 1
            last_idx = idx
            save_progress(progress_path, last_idx, saved)
            pbar.update(1)

    finally:
        pbar.close()

    print(f"Done. Saved {saved} triples to {final_path}")
    print(f"Progress checkpoint: {progress_path}")


if __name__ == "__main__":
    main()
