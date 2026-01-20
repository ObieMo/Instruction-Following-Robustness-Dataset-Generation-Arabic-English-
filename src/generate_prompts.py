import json
import random
from pathlib import Path

# Goal: generate MANY diverse Arabic prompts that *naturally* tempt English drift
# without explicitly asking for English. We keep it Arabic vs English only.

# Dialect-ish frames (Levantine-ish)
DIALECT_FRAMES = [
    "شو بتعرف عن {x}؟ اشرحلي بسرعة.",
    "فهمني {x} كأني عمري 12 سنة.",
    "يعني شو قصة {x}؟ عطيني مثال بسيط.",
    "بدي شرح مختصر عن {x} وبس.",
    "اختصرلي فكرة {x} بكلمتين وبعدين شرح صغير.",
    "شو الفرق بين {x} و{y}؟ جاوبني ببساطة.",
    "ليش {x} مهم؟",
    "اعطيني 3 نقاط عن {x}.",
]

# MSA frames
MSA_FRAMES = [
    "ماذا تعرف عن {x}؟ اشرح باختصار.",
    "عرّف {x} واذكر مثالاً واحداً.",
    "اشرح مفهوم {x} بطريقة مبسطة.",
    "قارن بين {x} و {y} باختصار.",
    "لماذا يُستخدم {x}؟ أجب بإيجاز.",
    "اكتب ثلاث نقاط تلخص {x}.",
    "لخّص فكرة {x} في فقرة قصيرة.",
    "اذكر 5 أمثلة تتعلق بـ {x}.",
]

# More "generic" real-life prompt styles (still Arabic)
GENERIC_FRAMES = [
    # daily life / travel / culture (non-sensitive)
    "اكتب نصيحة قصيرة لشخص أول مرة بيزور {place}.",
    "شو الأشياء اللي لازم ينتبهلها الواحد لما يسافر على {place}؟",
    "اقترح 3 أماكن لازم الواحد يشوفها في {place} (بشكل عام).",
    "اشرح باختصار ليش {place} مشهورة.",
    # study/work
    "اعطيني خطة بسيطة لأتعلم {skill} خلال أسبوعين.",
    "شو أفضل طريقة أبدأ فيها {skill} للمبتدئين؟",
    "اكتب نقاط سريعة عن أخطاء شائعة في {skill}.",
    # writing / summarization
    "لخّص الفكرة التالية بجملة واحدة: {topic}.",
    "حوّل هالفكرة لنقاط: {topic}.",
    "اكتب مقدمة قصيرة عن: {topic}.",
    # comparisons
    "قارن بين {x} و {y} من حيث الاستخدام بشكل بسيط.",
    "شو الفرق بين {x} و {y}؟",
]

PLACES = [
    "لندن", "برلين", "بودابست", "دبي", "باريس", "نيويورك", "اسطنبول", "روما",
]

SKILLS = [
    "البرمجة", "كتابة السيرة الذاتية", "إدارة الوقت", "تعلّم لغة جديدة", "تحسين النطق بالإنجليزي",
    "Docker", "CI/CD", "Python", "Machine Learning", "REST API",
]

TOPICS = [
    "العمل عن بعد", "تنظيم الوقت", "التعلّم الذاتي", "التشتت والتركيز", "القراءة اليومية",
    "كيف تتعلم بسرعة", "أهمية النوم", "التخطيط للأهداف", "الالتزام بالعادات",
]

# Confusion triggers (Arabic transliterations + English tokens)
TECH_TERMS = [
    # translussian Arabic letters (loanwords)
    "الديناميك", "الستاتيكا", "الكونترول", "الكاليبرايشن", "الفييدباك",
    "الموديل", "الديب ليرنينغ", "الترانسفورمر", "الأتنشن", "الريغريشن",
    "الكلسترينغ", "الأوبجيكت ديتكشن", "الترَيكينغ", "الديب فيك", "البرومبت",
    # mixed tokens
    "REST API", "GraphQL", "GPU", "Docker", "Kubernetes", "CI/CD", "LLM", "Python",
]

PAIR_TERMS = [
    ("الديب ليرنينغ", "المشين ليرنينغ"),
    ("REST API", "GraphQL"),
    ("Docker", "Kubernetes"),
    ("الترانسفورمر", "RNN"),
    ("GPU", "CPU"),
]

def choose_frame() -> str:
    # Weighted selection to keep variety
    r = random.random()
    if r < 0.35:
        return random.choice(MSA_FRAMES)
    if r < 0.65:
        return random.choice(DIALECT_FRAMES)
    return random.choice(GENERIC_FRAMES)

def make_prompt() -> str:
    frame = choose_frame()

    # Sometimes comparison
    if ("{y}" in frame) or (random.random() < 0.18):
        x, y = random.choice(PAIR_TERMS)
        # ensure frame has placeholders; if not, force a compare frame
        if "{y}" not in frame:
            frame = random.choice([
                "قارن بين {x} و {y} باختصار.",
                "شو الفرق بين {x} و {y}؟ جاوبني ببساطة.",
                "وضح الفرق بين {x} و {y} مع مثال صغير.",
            ])
        return frame.format(x=x, y=y)

    # Otherwise single slot {x}
    # Mix between tech triggers and generic topics/skills/places
    roll = random.random()
    if roll < 0.45:
        x = random.choice(TECH_TERMS)
    elif roll < 0.70:
        x = random.choice(SKILLS)
    else:
        x = random.choice(TOPICS)

    # Fill other placeholders if present
    if "{place}" in frame:
        place = random.choice(PLACES)
        return frame.format(place=place, x=x, topic=random.choice(TOPICS), skill=random.choice(SKILLS), y=random.choice(TECH_TERMS))
    if "{topic}" in frame:
        return frame.format(topic=random.choice(TOPICS), x=x, y=random.choice(TECH_TERMS), place=random.choice(PLACES), skill=random.choice(SKILLS))
    if "{skill}" in frame:
        return frame.format(skill=random.choice(SKILLS), x=x, y=random.choice(TECH_TERMS), place=random.choice(PLACES), topic=random.choice(TOPICS))

    # default:
    return frame.format(x=x)

def write_prompts(out_path: str, n: int, seed: int = 42):
    random.seed(seed)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for _ in range(n):
            p = make_prompt().strip()
            # Safety: skip empty prompt
            if not p:
                continue
            rec = {"prompt": p}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    write_prompts(args.out, args.n, args.seed)
