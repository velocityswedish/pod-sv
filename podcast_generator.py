"""
VELOCITY SWEDISH PODCAST GENERATOR
15-min bilingual Swedish/English podcast at A2 level
2 hosts: Astrid & Erik
"""
import os, sys, json, asyncio, subprocess, random, requests, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL") or "openai"

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"

HOST1_VOICE = "sv-SE-SofieNeural"
HOST2_VOICE = "sv-SE-MattiasNeural"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TOPICS = [
    "Att resa till ett nytt land - Traveling to a new country",
    "Traditionell mat - Traditional food",
    "Vardagsrutin - Daily routine",
    "Högtider och firanden - Holidays and celebrations",
    "Väder och årstider - Weather and seasons",
    "Familj och vänner - Family and friends",
    "Musik och filmer - Music and movies",
    "Sport och träning - Sports and exercise",
    "Den ideala staden - The ideal city",
    "Att lära sig språk - Learning languages",
    "Helgen - The weekend",
    "Shopping och kläder - Shopping and clothes",
    "Kollektivtrafik - Public transport",
    "På restaurangen - At the restaurant",
    "Hälsa och välbefinnande - Health and wellness",
]

YELLOW = (247, 202, 0)
DARK_BG = (11, 14, 27)
WHITE = (255, 255, 255)
LIGHT_GRAY = (170, 180, 205)
DARK_LINE = (50, 55, 75)

def load_font(size, bold=False, italic=False):
    fonts_to_try = []
    if italic and bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuiz.ttf", "C:/Windows/Fonts/arialbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
            str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"),
        ])
    elif italic:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/ariali.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            str(FONTS_DIR / "DejaVuSans-Oblique.ttf"),
        ])
    elif bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Bold-slnt=0.ttf", "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
        ])
    else:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Regular-slnt=0.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            str(FONTS_DIR / "DejaVuSans.ttf"),
        ])

    for fp in fonts_to_try:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\b(mm+|um+|uh+|ah+|äh+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def auto_highlight_swedish(text):
    if '**' in text:
        return text
    stopwords = {'och', 'att', 'det', 'som', 'en', 'ett', 'den', 'de', 'jag', 'du', 'han', 'hon', 'vi', 'ni', 'är', 'var', 'har', 'kan', 'ska', 'med', 'på', 'för', 'till', 'från'}
    words = text.split()
    candidates = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\wåäöÅÄÖ]', '', w, flags=re.UNICODE)
        if clean_w.lower() not in stopwords and len(clean_w) >= 3:
            candidates.append((len(clean_w), idx, w, clean_w))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_idx = candidates[0][1]
        raw_w = words[best_idx]
        clean_w = candidates[0][3]
        highlighted = raw_w.replace(clean_w, f"**{clean_w}**")
        words[best_idx] = highlighted
        return " ".join(words)
    return text

def draw_microphone_icon(draw, center_x, center_y, radius=24):
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                 outline=YELLOW, width=3)
    w, h = 10, 18
    draw.rounded_rectangle([center_x - w//2, center_y - 12, center_x + w//2, center_y - 12 + h],
                           radius=4, fill=YELLOW)
    draw.arc([center_x - 10, center_y - 4, center_x + 10, center_y + 12],
             start=0, end=180, fill=YELLOW, width=3)
    draw.line([(center_x, center_y + 12), (center_x, center_y + 17)], fill=YELLOW, width=3)
    draw.line([(center_x - 7, center_y + 17), (center_x + 7, center_y + 17)], fill=YELLOW, width=3)

def draw_person_icon(draw, center_x, center_y):
    draw.ellipse([center_x - 6, center_y - 12, center_x + 6, center_y], fill=YELLOW)
    draw.chord([center_x - 12, center_y + 2, center_x + 12, center_y + 20],
               start=180, end=360, fill=YELLOW)

def draw_swedish_flag(img, draw, center_x, center_y, radius=22):
    flag_img = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flag_img)
    # Swedish flag: blue with yellow Scandinavian cross
    w = radius * 2
    blue = (0, 106, 167, 255)
    yellow = (254, 204, 18, 255)
    fdraw.rectangle([(0, 0), (w, w)], fill=blue)
    bar_h = int(w * 0.2)
    # horizontal yellow bar
    fdraw.rectangle([(0, int(w*0.4)), (w, int(w*0.4)+bar_h)], fill=yellow)
    # vertical yellow bar (offset left of center)
    fdraw.rectangle([(int(w*0.35), 0), (int(w*0.35)+bar_h, w)], fill=yellow)
    
    mask = Image.new('L', (radius*2, radius*2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, radius*2, radius*2], fill=255)
    img.paste(flag_img, (center_x - radius, center_y - radius), mask)

def draw_headphones_icon(draw, center_x, center_y):
    draw.arc([center_x - 14, center_y - 14, center_x + 14, center_y + 6],
             start=180, end=360, fill=YELLOW, width=3)
    draw.rounded_rectangle([center_x - 16, center_y - 3, center_x - 10, center_y + 11], radius=2, fill=YELLOW)
    draw.rounded_rectangle([center_x + 10, center_y - 3, center_x + 16, center_y + 11], radius=2, fill=YELLOW)

def draw_rich_text_centered(draw, text, center_y, font, max_w=1550, line_height=90):
    text = auto_highlight_swedish(text)
    pattern = r'(\*\*.*?\*\*)'
    raw_parts = re.split(pattern, text)
    tokens = []
    for part in raw_parts:
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], True))
        elif part:
            tokens.append((part, False))
            
    words_with_status = []
    for text_chunk, is_yellow in tokens:
        words = text_chunk.split(' ')
        for i, w in enumerate(words):
            if w:
                words_with_status.append((w, is_yellow))
            if i < len(words) - 1:
                words_with_status.append((' ', False))

    lines = []
    current_line = []
    current_line_width = 0

    for item in words_with_status:
        word, is_yellow = item
        w_bbox = draw.textbbox((0, 0), word, font=font)
        w_width = w_bbox[2] - w_bbox[0]

        if current_line_width + w_width <= max_w or not current_line:
            current_line.append((word, is_yellow, w_width))
            current_line_width += w_width
        else:
            if current_line and current_line[-1][0] == ' ':
                current_line_width -= current_line[-1][2]
                current_line.pop()
            lines.append((current_line, current_line_width))
            if word == ' ':
                current_line = []
                current_line_width = 0
            else:
                current_line = [(word, is_yellow, w_width)]
                current_line_width = w_width

    if current_line:
        if current_line[-1][0] == ' ':
            current_line_width -= current_line[-1][2]
            current_line.pop()
        lines.append((current_line, current_line_width))

    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2

    for line_idx, (line_words, line_w) in enumerate(lines):
        start_x = (VIDEO_WIDTH - line_w) // 2
        curr_x = start_x
        curr_y = start_y + line_idx * line_height

        for word, is_yellow, w_w in line_words:
            color = YELLOW if is_yellow else WHITE
            draw.text((curr_x, curr_y), word, fill=color, font=font)
            curr_x += w_w

def draw_english_translation(draw, text, center_y, font, max_w=1350, line_height=52):
    words = text.split()
    lines = []
    current_line = []
    
    for w in words:
        test_line = ' '.join(current_line + [w])
        bb = draw.textbbox((0, 0), test_line, font=font)
        if bb[2] - bb[0] <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [w]
    if current_line:
        lines.append(' '.join(current_line))
        
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2
    
    for idx, line in enumerate(lines):
        draw.text((VIDEO_WIDTH // 2, start_y + idx * line_height + line_height // 2),
                  line, fill=LIGHT_GRAY, font=font, anchor="mm")

def create_frame(turn, output_path, frame_num=0):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([(-200, VIDEO_HEIGHT-600), (600, VIDEO_HEIGHT+200)], fill=(30, 20, 60, 40))
    gdraw.ellipse([(VIDEO_WIDTH-500, -200), (VIDEO_WIDTH+300, 600)], fill=(30, 20, 60, 40))
    img.paste(glow, (0, 0), glow)

    f_title_white = load_font(36, bold=True)
    f_title_sub = load_font(18, bold=False)
    f_title_sub_muted = load_font(15, bold=False)
    f_ep = load_font(22, bold=True)
    f_speaker = load_font(26, bold=True)
    f_hablando = load_font(24, bold=False)
    f_swedish = load_font(64, bold=True)
    f_english = load_font(42, bold=False, italic=True)
    f_footer = load_font(22, bold=False)

    # === TOP HEADER ===
    header_y = 68
    draw_microphone_icon(draw, center_x=70, center_y=header_y, radius=24)

    draw.text((110, header_y), "VELOCITY", fill=WHITE, font=f_title_white, anchor="lm")
    v_bbox = draw.textbbox((110, header_y), "VELOCITY", font=f_title_white, anchor="lm")
    
    draw.text((v_bbox[2] + 8, header_y), "SWEDISH", fill=YELLOW, font=f_title_white, anchor="lm")
    s_bbox = draw.textbbox((v_bbox[2] + 8, header_y), "SWEDISH", font=f_title_white, anchor="lm")

    draw.text((s_bbox[2] + 8, header_y), "PODCAST", fill=WHITE, font=f_title_white, anchor="lm")
    p_bbox = draw.textbbox((s_bbox[2] + 8, header_y), "PODCAST", font=f_title_white, anchor="lm")

    draw.line([(p_bbox[2] + 20, 48), (p_bbox[2] + 20, 88)], fill=DARK_LINE, width=2)

    sub_x = p_bbox[2] + 35
    draw.text((sub_x, header_y - 12), "Swedish Podcast", fill=WHITE, font=f_title_sub, anchor="lm")
    draw.text((sub_x, header_y + 12), "Learn Through Conversations", fill=LIGHT_GRAY, font=f_title_sub_muted, anchor="lm")

    ep_num = (frame_num // 150) + 1 if isinstance(frame_num, int) else 1
    ep_str = f"EP {ep_num:02d}"
    draw.rounded_rectangle([(1640, 46), (1750, 90)], radius=8, fill=YELLOW)
    draw.text((1695, header_y), ep_str, fill=DARK_BG, font=f_ep, anchor="mm")

    draw_swedish_flag(img, draw, center_x=1810, center_y=header_y, radius=22)

    draw.line([(0, 130), (VIDEO_WIDTH, 130)], fill=YELLOW, width=2)

    # === SPEAKER STATUS SECTION ===
    is_host1 = turn.get("speaker") == "Host1"
    speaker_name = "ASTRID" if is_host1 else "ERIK"
    pill_x, pill_y = 120, 210
    pill_w, pill_h = 220, 52

    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
                           radius=26, outline=YELLOW, width=2)
    draw_person_icon(draw, center_x=pill_x + 36, center_y=pill_y + 26)
    draw.text((pill_x + 60, pill_y + 26), speaker_name, fill=YELLOW, font=f_speaker, anchor="lm")

    draw.text((pill_x + pill_w + 25, pill_y + 26), "pratar", fill=LIGHT_GRAY, font=f_hablando, anchor="lm")

    # === MAIN SWEDISH TEXT ===

    # === MAIN TEXT (auto-size, HARD max 3 lines) ===
    swedish_text = turn.get("swedish", turn.get("spanish", ""))
    chosen_font = None
    chosen_lh = 90
    final_lines = []
    for test_size in [64, 56, 48, 40, 34, 28, 24, 20]:
        test_font = load_font(test_size, bold=True)
        test_lh = int(test_size * 1.4)
        text_words = swedish_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=test_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) <= 3:
            chosen_font = test_font
            chosen_lh = test_lh
            final_lines = tmp_lines
            break
    if chosen_font is None:
        chosen_font = load_font(20, bold=True)
        chosen_lh = int(20 * 1.4)
        text_words = swedish_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=chosen_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) > 3:
            tmp_lines = tmp_lines[:3]
            if swedish_text:
                tmp_lines[-1] = tmp_lines[-1].rstrip() + "..."
        final_lines = tmp_lines
        swedish_text = " ".join(final_lines)
    draw_rich_text_centered(draw, swedish_text, center_y=440, font=chosen_font, max_w=1550, line_height=chosen_lh)

    # === CENTER DIVIDER WITH DOT ===
    div_y = 615
    draw.line([(VIDEO_WIDTH//2 - 300, div_y), (VIDEO_WIDTH//2 + 300, div_y)], fill=YELLOW, width=2)
    draw.ellipse([(VIDEO_WIDTH//2 - 8, div_y - 8), (VIDEO_WIDTH//2 + 8, div_y + 8)], fill=YELLOW)

    # === ENGLISH TRANSLATION ===
    english_text = turn.get("english", "")
    draw_english_translation(draw, english_text, center_y=715, font=f_english, max_w=1350, line_height=52)

    # === BOTTOM FOOTER ===
    draw.line([(0, 975), (VIDEO_WIDTH, 975)], fill=YELLOW, width=2)

    footer_y = 1025
    draw_headphones_icon(draw, center_x=VIDEO_WIDTH//2 - 270, center_y=footer_y)
    draw.text((VIDEO_WIDTH//2 - 240, footer_y), "Learn Swedish Naturally", fill=WHITE, font=f_footer, anchor="lm")
    
    fn_bbox = draw.textbbox((VIDEO_WIDTH//2 - 240, footer_y), "Learn Swedish Naturally", font=f_footer, anchor="lm")
    draw.line([(fn_bbox[2] + 20, footer_y - 12), (fn_bbox[2] + 20, footer_y + 12)], fill=DARK_LINE, width=2)
    
    draw.text((fn_bbox[2] + 40, footer_y), "velocityswedish.com", fill=WHITE, font=f_footer, anchor="lm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)


def parse_turns_json(content, target_key="swedish"):
    """Robustly parse JSON array of turns from LLM output, handling unescaped control chars, code fences, and partial json."""
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    try:
        obj = json.loads(clean, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    fixed = re.sub(r'(?<!\\)\n', r'\\n', clean)
    try:
        obj = json.loads(fixed, strict=False)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    recovered = []
    start = None
    depth = 0
    for ci, ch in enumerate(clean):
        if ch == '{':
            if depth == 0:
                start = ci
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = clean[start:ci + 1]
                try:
                    t = json.loads(chunk, strict=False)
                    if isinstance(t, dict):
                        recovered.append(t)
                except Exception:
                    try:
                        chunk_fixed = re.sub(r'(?<!\\)\n', r'\\n', chunk)
                        t = json.loads(chunk_fixed, strict=False)
                        if isinstance(t, dict):
                            recovered.append(t)
                    except Exception:
                        pass
                start = None
    if recovered:
        return recovered

    regex = re.compile(
        r'\{\s*"speaker"\s*:\s*"(?P<speaker>[^"]+)"\s*,\s*'
        r'(?:"(?:' + target_key + r'|text|content|spanish)"\s*:\s*"(?P<tgt>.*?)"\s*,\s*)?'
        r'(?:"english"\s*:\s*"(?P<en>.*?)"\s*)?'
        r'\}', re.DOTALL
    )
    for m in regex.finditer(clean):
        spk = m.group("speaker") or "Host1"
        tgt = m.group("tgt") or ""
        en = m.group("en") or ""
        if tgt:
            recovered.append({"speaker": spk, target_key: tgt, "english": en})

    return recovered

def _fetch_turns_batch(topic, topic_es, topic_en, start_turn, batch_size=10):
    """Fetch one small batch of turns with multi-model fallback and robust parsing."""
    current_host = "Host2" if start_turn % 2 == 0 else "Host1"
    next_host = "Host1" if current_host == "Host2" else "Host2"
    host_role = "Erik" if current_host == "Host2" else "Astrid"

    intro_instruction = ""
    if start_turn == 0:
        intro_instruction = ("IMPORTANT: This is the FIRST batch. Keep the introduction SHORT - just 2 lines total "
                             "(one from Erik/Host2, one from Astrid/Host1), then immediately dive into the topic. "
                             "No long welcome speeches.\n")
    elif start_turn < 4:
        intro_instruction = "Continue naturally into the topic conversation. No new introductions.\n"

    prompt = f"""You are writing a Swedish/English learning podcast at A2 level.
Topic: {topic}

The dialogue so far is at turn {start_turn}. The current speaker is {host_role} ({current_host}).
Write the NEXT {batch_size} turns. Speakers STRICTLY alternate starting with {current_host}.

{intro_instruction}Each turn: 3-4 SHORT sentences (6-10 words each) with PERIODS for natural TTS pauses. 20-30 seconds spoken.
Simple present tense. A2 vocabulary. Natural Swedish. NO filler sounds.
IMPORTANT: Highlight exactly 1 key A2 target vocabulary word in each turn's Swedish text using double asterisks, for example: "Vi tittar mot **framtiden**."
IMPORTANT: Format as a single compact JSON array without unescaped line breaks inside string values.

Return EXACTLY {batch_size} turns as a JSON array (no markdown):
[{{"speaker": "{current_host}", "swedish": "...", "english": "..."}},
 {{"speaker": "{next_host}", "swedish": "...", "english": "..."}}]"""

    candidate_models = [AI_MODEL, "openai", "mistral", "qwen"]
    models_to_try = []
    for mod in candidate_models:
        if mod and mod not in models_to_try:
            models_to_try.append(mod)

    for attempt, model_name in enumerate(models_to_try):
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You write natural A2-level Swedish podcast scripts with VERY clear punctuation. Every sentence must have at least 2 commas for natural TTS pauses. Astrid and Erik strictly alternate. Highlight 1 key target word per turn in double asterisks like **ord**. No filler sounds. Output single compact JSON array without unescaped newlines inside strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code != 200:
                print(f"  Batch attempt {attempt+1} ({model_name}) returned HTTP {resp.status_code}", flush=True)
                continue
            content = resp.json()["choices"][0]["message"]["content"].strip()
            script = parse_turns_json(content, "swedish")
            valid = []
            for i, turn in enumerate(script):
                if not isinstance(turn, dict):
                    continue
                sv = turn.get("swedish") or turn.get("spanish") or turn.get("text") or turn.get("content") or ""
                en = turn.get("english") or turn.get("translation") or ""
                if not sv:
                    continue
                valid.append({
                    "speaker": current_host if i % 2 == 0 else next_host,
                    "swedish": clean_text(sv),
                    "english": clean_text(en) if en else "Translation unavailable"
                })
            if len(valid) >= 4:
                return valid
            else:
                print(f"  Batch attempt {attempt+1} ({model_name}) parsed only {len(valid)} turns, trying next model...", flush=True)
        except Exception as e:
            print(f"  Batch attempt {attempt+1} ({model_name}) failed: {e}", flush=True)
            import time
            time.sleep(1)
    return None


def _generate_topic():
    """Have the AI invent a brand-new random topic (unlimited variety).
    Returns '<topic - English>' or None on failure (caller falls back to TOPICS)."""
    seed = random.randint(100000, 999999)
    candidate_models = [AI_MODEL, "openai", "mistral"]
    for m in candidate_models:
        if not m:
            continue
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": m,
                "messages": [
                    {"role": "system", "content": "You invent fresh, interesting, everyday topics for a Swedish/English A2 learning podcast. Always pick something new and varied from all areas of daily life, as a SHORT noun phrase (2-5 words), NOT a full sentence."},
                    {"role": "user", "content": f"Create EXACTLY ONE brand-new topic (uniqueness seed {seed}) for a Swedish/English A2 podcast. Return ONLY one line in this exact format: <topic in Swedish> - <topic in English>. The first part must be a short noun phrase in Swedish. No numbering, no bullets, no extra text."}
                ],
                "temperature": 1.1,
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip()
                if content and " - " in content:
                    return content
        except Exception as e:
            print(f"  Topic gen ({m}) failed: {e}", flush=True)
    return None


def _fallback_script(topic_es, topic_en, target=150):
    """Generate 150 unique, educational, progressive dialogue turns in Swedish covering diverse conversation phases."""
    phases = [
        # Phase 1: Greetings & Introduction
        [
            ("Host2", f"Hej alla, jag heter Erik. Välkomna till Velocity Swedish! Idag pratar vi om **{topic_es}**.",
                      f"Hello everyone, I'm Erik. Welcome to Velocity Swedish! Today we are talking about {topic_en}."),
            ("Host1", f"Hej Erik, och hej till alla lyssnare! Detta ämne är verkligen **spännande** för alla som lär sig svenska.",
                      f"Hello Erik, and hello to all listeners! This topic is truly exciting for everyone learning Swedish."),
            ("Host2", f"Precis, Astrid. Många möter **{topic_es}** varje dag, men vet inte hur de ska uttrycka sig.",
                      f"Exactly, Astrid. Many encounter {topic_en} every day, but don't know how to express themselves."),
            ("Host1", f"Det stämmer. Därför använder vi idag **enkla** meningar och tydliga ord som alla kan förstå.",
                      f"That's right. Therefore we use simple sentences and clear words today that everyone can understand."),
            ("Host2", f"Perfekt! Låt oss börja med den första frågan: vad betyder **{topic_es}** för dig i vardagen?",
                      f"Perfect! Let's start with the first question: what does {topic_en} mean for you in daily life?"),
            ("Host1", f"För mig är det en viktig del av **dagen** som ger gott humör och ny energi.",
                      f"For me it's an important part of the day that brings good mood and new energy."),
            ("Host2", f"Jag håller helt med. Att ta sig tid till detta ger mer **lugn** och glädje i tillvaron.",
                      f"I completely agree. Taking time for this gives more calm and joy in life."),
            ("Host1", f"Ja, och med rätt ordförråd blir det lätt att föra ett naturligt **samtal** på svenska.",
                      f"Yes, and with the right vocabulary it becomes easy to have a natural conversation in Swedish."),
            ("Host2", f"Lyssna noga på uttalet idag, och upprepa de viktigaste orden **högt** för er själva.",
                      f"Listen carefully to pronunciation today, and repeat the most important words out loud to yourselves."),
            ("Host1", f"Mycket bra, Erik! Låt oss nu titta närmare på praktiska situationer kring **{topic_es}**.",
                      f"Very good, Erik! Let's now look more closely at practical situations around {topic_en}.")
        ],
        # Phase 2: Morning routine & habits
        [
            ("Host2", f"Astrid, när under en vanlig dag tänker du först på **{topic_es}**?",
                      f"Astrid, when during a normal day do you first think about {topic_en}?"),
            ("Host1", f"Oftast tänker jag på det tidigt på morgonen, eftersom det hjälper mig att börja dagen i **harmoni**.",
                      f"Usually I think about it early in the morning, because it helps me start the day in harmony."),
            ("Host2", f"För mig är morgonen också en speciell stund. Jag tycker om att ta god **tid** på mig.",
                      f"For me morning is also a special moment. I like taking good time for myself."),
            ("Host1", f"Stress är aldrig bra. En god morgonrutin och en sund **vana** förändrar hela dagen.",
                      f"Stress is never good. A good morning routine and a healthy habit change the whole day."),
            ("Host2", f"Många föredrar däremot att ägna sig åt **{topic_es}** på eftermiddagen eller efter jobbet.",
                      f"Many people prefer on the other hand to devote themselves to {topic_en} in the afternoon or after work."),
            ("Host1", f"Det beror helt på ens egen livsstil. Det viktigaste är att hitta en god **balans**.",
                      f"It completely depends on one's own lifestyle. The most important thing is finding a good balance."),
            ("Host2", f"Du har helt rätt. Att lyssna på sina egna behov gör att man mår mycket **bättre**.",
                      f"You are completely right. Listening to one's own needs makes one feel much better."),
            ("Host1", f"Och för våra lyssnare bygger lite daglig träning upp ett starkt språkligt **minne**.",
                      f"And for our listeners, a little daily practice builds a strong language memory."),
            ("Host2", f"Exakt så. Tio minuter varje dag ger mycket mer än två timmar enbart på **söndag**.",
                      f"Exactly so. Ten minutes every day gives much more than two hours only on Sunday."),
            ("Host1", f"Låt oss nu prata om hur **{topic_es}** märks i det svenska samhället och stadsbilden.",
                      f"Let's now talk about how {topic_en} is noticed in Swedish society and city life.")
        ],
        # Phase 3: In the city & Swedish culture
        [
            ("Host2", f"När man promenerar genom en svensk stad ser man tydligt betydelsen av **{topic_es}**.",
                      f"When walking through a Swedish city, one clearly sees the importance of {topic_en}."),
            ("Host1", f"Ja, på kaféer, i butiker och på gatorna pratar folk gärna om detta med stort **intresse**.",
                      f"Yes, at cafes, in shops and on streets people gladly talk about this with great interest."),
            ("Host2", f"I Sverige är fika och gemensamma stunder en mycket viktig del av vår **kultur**.",
                      f"In Sweden fika and shared moments are a very important part of our culture."),
            ("Host1", f"Gemenskap och omtanke är centrala värden. Man ska aldrig behöva känna sig **ensam**.",
                      f"Community and caring are central values. One should never have to feel alone."),
            ("Host2", f"Vilka ord brukar svenskar använda mest när de beskriver **{topic_es}**?",
                      f"What words do Swedes usually use most when describing {topic_en}?"),
            ("Host1", f"Man hör ofta ord som 'lagom', 'äkta' och 'trevligt' för att beskriva hög **kvalitet**.",
                      f"One often hears words like 'just right', 'genuine' and 'pleasant' to describe high quality."),
            ("Host2", f"Ordet 'lagom' passar så bra här. Det innebär balans och genomtänkt **enkelhet**.",
                      f"The word 'lagom' fits so well here. It means balance and thoughtful simplicity."),
            ("Host1", f"Även om det kräver lite omsorg, så lönar sig alltid ett genomtänkt och gott **val**.",
                      f"Even if it requires a little care, a thoughtful and good choice always pays off."),
            ("Host2", f"Ett bra tips för resenärer i Sverige: fråga alltid någon som bor i **området**.",
                      f"A good tip for travelers in Sweden: always ask someone living in the area."),
            ("Host1", f"Lokalbefolkningen vet alltid var man hittar de mysigaste platserna för **{topic_es}**.",
                      f"Locals always know where to find the coziest places for {topic_en}.")
        ],
        # Phase 4: Advice for beginners & common hurdles
        [
            ("Host2", f"En lyssnare frågade oss: är det svårt att lära sig alla detaljer kring **{topic_es}**?",
                      f"A listener asked us: is it hard to learn all details around {topic_en}?"),
            ("Host1", f"I början kan det verka lite ovant, men med lite tålamod blir allting snart väldigt **tydligt**.",
                      f"At first it may seem a bit unfamiliar, but with a little patience everything soon becomes very clear."),
            ("Host2", f"Vad är det vanligaste misstaget nybörjare gör när de studerar detta **ämne**?",
                      f"What is the most common mistake beginners make when studying this topic?"),
            ("Host1", f"Det vanligaste misstaget är rädslan för att göra fel eller att kräva perfektion från första **dagen**.",
                      f"The most common mistake is fear of making mistakes or demanding perfection from the first day."),
            ("Host2", f"Att göra fel är helt naturligt och nödvändigt! Varje misstag är en nyttig **läxa**.",
                      f"Making mistakes is completely natural and necessary! Every mistake is a useful lesson."),
            ("Host1", f"Helt sant. I ett verkligt samtal handlar det om att förstå varandra och visa **glädje**.",
                      f"Completely true. In a real conversation it's about understanding each other and showing joy."),
            ("Host2", f"Svenskar uppskattar alltid när någon visar intresse och försöker tala vårt **språk**.",
                      f"Swedes always appreciate when someone shows interest and tries to speak our language."),
            ("Host1", f"Man möts nästan alltid av ett varmt leende och uppmuntran att fortsätta **öva**.",
                      f"One is almost always met with a warm smile and encouragement to keep practicing."),
            ("Host2", f"Tveka därför aldrig att prata om **{topic_es}** så fort du får ett tillfälle!",
                      f"Therefore never hesitate to talk about {topic_en} as soon as you get an opportunity!"),
            ("Host1", f"Var modig och använd de uttryck vi går igenom tillsammans i detta **avsnitt**.",
                      f"Be brave and use the expressions we go through together in this episode.")
        ],
        # Phase 5: Swedish lifestyle & nature
        [
            ("Host2", f"Astrid, hur skiljer sig synen på **{topic_es}** i olika delar av vårt avlånga land?",
                      f"Astrid, how does the view on {topic_en} differ in different parts of our elongated country?"),
            ("Host1", f"Från Skåne till Lappland finns det lokala variationer, men kärleken till ämnet är lika **stark**.",
                      f"From Skåne to Lapland there are local variations, but love for the topic is just as strong."),
            ("Host2", f"Sveriges fantastiska natur och årstidernas växlingar präglar hela vårt sätt att **leva**.",
                      f"Sweden's fantastic nature and the changing seasons shape our whole way of living."),
            ("Host1", f"Varje årstid har sin charm, sina traditioner och sin alldeles egna **stämning**.",
                      f"Each season has its charm, its traditions and its very own atmosphere."),
            ("Host2", f"Många besökare från andra länder fascineras av lugnet, renheten och närheten till **skogen**.",
                      f"Many visitors from other countries are fascinated by calm, cleanliness and closeness to the forest."),
            ("Host1", f"Eftersom vår kultur sätter familj, trygghet och omtanke om naturen i **centrum**.",
                      f"Because our culture puts family, security and care for nature in the center."),
            ("Host2", f"Och **{topic_es}** passar perfekt in i denna medvetna och hållbara livsfilosofi.",
                      f"And {topic_en} fits perfectly into this conscious and sustainable life philosophy."),
            ("Host1", f"Det är inte bara en tanke, utan en praktisk upplevelse av gemensam **glädje**.",
                      f"It's not just a thought, but a practical experience of shared joy."),
            ("Host2", f"När man delar fina stunder med andra skapar man ett varmt och varaktigt **minne**.",
                      f"When sharing fine moments with others one creates a warm and lasting memory."),
            ("Host1", f"Verkligen, Erik. De bästa minnena kommer nästan alltid från de allra mest **enkla** sakerna.",
                      f"Truly, Erik. The best memories almost always come from the very simplest things.")
        ],
        # Phase 6: Practical learning tips
        [
            ("Host2", f"Låt oss dela tre praktiska studietips med lyssnarna för att lära sig mer om **{topic_es}**.",
                      f"Let's share three practical study tips with listeners to learn more about {topic_en}."),
            ("Host1", f"Första tipset: skaffa ett litet anteckningsblock och skriv ner två nya svenska **meningar** varje dag.",
                      f"First tip: get a small notepad and write down two new Swedish sentences every day."),
            ("Host2", f"Mycket bra idé! Att skriva för hand hjälper hjärnan att komma ihåg ord och **stavning**.",
                      f"Very good idea! Writing by hand helps the brain remember words and spelling."),
            ("Host1", f"Andra tipset: lyssna på svenska poddar i lurarna när du promenerar eller åker **buss**.",
                      f"Second tip: listen to Swedish podcasts in your headphones when walking or riding the bus."),
            ("Host2", f"Passivt lyssnande gör att örat vänjer sig vid svenskans speciella satsmelodi och **rytm**.",
                      f"Passive listening gets the ear used to Swedish's special sentence melody and rhythm."),
            ("Host1", f"Och tredje tipset: lär er inte enstaka glosor utan sammanhang, utan lär er hela **fraser**.",
                      f"And third tip: don't learn isolated vocab words without context, but learn full phrases."),
            ("Host2", f"Då kommer rätt formulering automatiskt och naturligt i ett verkligt **samtal**.",
                      f"Then the right phrasing comes automatically and naturally in a real conversation."),
            ("Host1", f"Det är precis den metoden vi tillämpar i våra lektioner på nivå **A2**.",
                      f"That is exactly the method we apply in our lessons at level A2."),
            ("Host2", f"Många lyssnare skriver i kommentarerna att de gör snabba framsteg med denna **strategi**.",
                      f"Many listeners write in comments that they make fast progress with this strategy."),
            ("Host1", f"Det värmer våra hjärtan och inspirerar oss att fortsätta skapa nya lärorika **avsnitt**.",
                      f"That warms our hearts and inspires us to continue creating new instructive episodes.")
        ],
        # Phase 7: Situational roleplay
        [
            ("Host2", f"Nu gör vi ett kort rollspel: tänk dig att vi kliver in i en butik för att välja **{topic_es}**.",
                      f"Now let's do a short roleplay: imagine we step into a shop to choose {topic_en}."),
            ("Host1", f"Vad roligt! 'Hej, skulle du kunna hjälpa mig och berätta vad du **rekommenderar**?'",
                      f"How fun! 'Hi, could you help me and tell what you recommend?'"),
            ("Host2", f"'Hej! För nybörjare rekommenderar jag varmt den här beprövade och pålitliga **modellen**.'",
                      f"'Hi! For beginners I warmly recommend this proven and reliable model.'"),
            ("Host1", f"'Tack så mycket! Och ungefär hur lång tid brukar det ta att lära sig den ordentligt i **praktiken**?'",
                      f"'Thank you so much! And about how long does it usually take to learn it properly in practice?'"),
            ("Host2", f"'Vanligtvis räcker det med några få dagar om man övar regelbundet och med gott **tålamod**.'",
                      f"'Usually a few days is enough if you practice regularly and with good patience.'"),
            ("Host1", f"'Det låter alldeles utmärkt! Jag ska prova detta redan idag med stor **entusiasm**.'",
                      f"'That sounds completely excellent! I will try this already today with great enthusiasm.'"),
            ("Host2", f"Det där var en typisk, artig och vänlig dialog som fungerar överallt i **Sverige**.",
                      f"That was a typical, polite and friendly dialogue that works everywhere in Sweden."),
            ("Host1", f"Lägg märke till artiga fraser som 'skulle du kunna hjälpa mig' som skapar god **kontakt**.",
                      f"Notice polite phrases like 'could you help me' that create good contact."),
            ("Host2", f"Vänlighet gör varje möte mer trivsamt och uppskattat för båda **personerna**.",
                      f"Friendliness makes every meeting more pleasant and appreciated for both people."),
            ("Host1", f"Kom ihåg dessa praktiska uttryck till er nästa resa eller **konversation**.",
                      f"Remember these practical expressions for your next trip or conversation.")
        ],
        # Phase 8: Personal reflections & confidence
        [
            ("Host2", f"Astrid, hur brukar dina vänner och bekanta reagera när ni pratar om **{topic_es}**?",
                      f"Astrid, how do your friends and acquaintances usually react when you talk about {topic_en}?"),
            ("Host1", f"I början var en del lite fundersamma, men när de testade själva insåg de det stora **värdet**.",
                      f"At first some were a bit thoughtful, but when they tested themselves they realized the great value."),
            ("Host2", f"Att vara lite tveksam inför någonting nytt är en helt naturlig mänsklig **reaktion**.",
                      f"Being a bit hesitant before something new is a completely natural human reaction."),
            ("Host1", f"Men så fort man tar det första steget släpper oron och förvandlas till ett starkt **självförtroende**.",
                      f"But as soon as you take the first step worry releases and turns into strong self-confidence."),
            ("Host2", f"Språkligt självförtroende växer med varje mening man vågar säga **högt**.",
                      f"Language self-confidence grows with every sentence you dare to say out loud."),
            ("Host1", f"Även med ett litet ordförråd på några dussin ord kan man berätta en intressant **historia**.",
                      f"Even with a small vocabulary of a few dozen words one can tell an interesting story."),
            ("Host2", f"Det viktigaste är viljan att kommunicera och förmedla sina tankar på ett ärligt **sätt**.",
                      f"The most important thing is the willingness to communicate and convey one's thoughts in an honest way."),
            ("Host1", f"Våra lyssnare runt om i världen visar att svenska är tillgängligt för alla som är **motiverade**.",
                      f"Our listeners around the world show that Swedish is accessible for everyone who is motivated."),
            ("Host2", f"Varje avsnitt du lyssnar på är ett viktigt steg framåt på din personliga **resa**.",
                      f"Every episode you listen to is an important step forward on your personal journey."),
            ("Host1", f"Och vi är så glada över att få följa med er och stötta er med kunskap och **glädje**.",
                      f"And we are so glad to be able to accompany you and support you with knowledge and joy.")
        ],
        # Phase 9: Vocabulary review
        [
            ("Host2", f"Låt oss göra en snabb repetition av de fem viktigaste orden vi använt idag om **{topic_es}**.",
                      f"Let's do a quick repetition of the five most important words we used today about {topic_en}."),
            ("Host1", f"Gärna! Det första nyckelordet är **vana**, en regelbunden och nyttig handling i vardagen.",
                      f"Gladly! The first keyword is 'habit', a regular and useful action in daily life."),
            ("Host2", f"Det andra ordet är **kvalitet**, som utmärker det som är hållbart och väl genomtänkt.",
                      f"The second word is 'quality', which distinguishes what is sustainable and well thought through."),
            ("Host1", f"Det tredje begreppet är **gemenskap**, den fina känslan av sammanhållning med vänner och familj.",
                      f"The third concept is 'community', the fine feeling of togetherness with friends and family."),
            ("Host2", f"Det fjärde ordet är **tålamod**, nödvändigt för att bygga upp språkkunskaper steg för **steg**.",
                      f"The fourth word is 'patience', necessary to build up language skills step by step."),
            ("Host1", f"Och det femte ordet är **självförtroende**, tryggheten att våga tala fritt och obehindrat.",
                      f"And the fifth word is 'self-confidence', the security to dare speaking freely and unhindered."),
            ("Host2", f"Skriv gärna en egen mening med ett av dessa ord i kommentarsfältet här **nedanför**.",
                      f"Feel free to write your own sentence with one of these words in the comment section below."),
            ("Host1", f"Vi läser era kommentarer med stort nöje och ger er gärna uppmuntrande **respons**.",
                      f"We read your comments with great pleasure and gladly give you encouraging feedback."),
            ("Host2", f"Att vara aktiv i lärandet gör att orden fastnar mycket bättre i **minnet**.",
                      f"Being active in learning makes words stick much better in memory."),
            ("Host1", f"Nu är det dags för avslutande ord i detta innehållsrika **program**.",
                      f"Now it is time for concluding words in this rich program.")
        ],
        # Phase 10: Conclusion & wrap-up
        [
            ("Host2", f"Därmed börjar dagens podcast om **{topic_es}** lida mot sitt slut.",
                      f"Thereby today's podcast about {topic_en} begins to draw to its close."),
            ("Host1", f"Tiden gick otroligt fort! Vi har gått igenom många användbara ord och **uttryck**.",
                      f"Time went incredibly fast! We went through many useful words and expressions."),
            ("Host2", f"Lyssna gärna på det här avsnittet flera gånger för att befästa ordförråd och **uttal**.",
                      f"Feel free to listen to this episode several times to consolidate vocabulary and pronunciation."),
            ("Host1", f"Varje genomlyssning gör att svenskan känns mer naturlig, flytande och **självklar**.",
                      f"Every listen-through makes Swedish feel more natural, fluent and self-evident."),
            ("Host2", f"Ett stort tack till alla er som lyssnar och stöttar oss på vår **kanal**.",
                      f"A big thank you to all of you who listen and support us on our channel."),
            ("Host1", f"Prenumerera på Velocity Swedish, gilla videon och dela den gärna med era **vänner**.",
                      f"Subscribe to Velocity Swedish, like the video and feel free to share it with your friends."),
            ("Host2", f"Snart är vi tillbaka med fler intressanta ämnen och praktiska tips för er **svenska**.",
                      f"Soon we will be back with more interesting topics and practical tips for your Swedish."),
            ("Host1", f"Ha en fantastisk dag och fortsätt att studera med glädje och **energi**!",
                      f"Have a fantastic day and continue studying with joy and energy!"),
            ("Host2", f"Ta hand om er, ha det så bra och på återseende nästa **gång**!",
                      f"Take care of yourselves, be well and see you again next time!"),
            ("Host1", f"Hej då, kära vänner, och fortsätt prata svenska med ett **leende**!",
                      f"Goodbye, dear friends, and keep speaking Swedish with a smile!")
        ]
    ]

    all_templates = []
    for ph in phases:
        all_templates.extend(ph)
    turns = []
    for i in range(target):
        _, t_sv, t_en = all_templates[i % len(all_templates)]
        spk = "Host2" if i % 2 == 0 else "Host1"
        turns.append({"speaker": spk, "swedish": t_sv, "english": t_en})
    return turns


def _extend_script(existing_turns, topic_es, topic_en, target=150):
    fallback_pool = _fallback_script(topic_es, topic_en, target)
    idx = 0
    cur_speaker = existing_turns[-1]["speaker"] if existing_turns else "Host1"
    while len(existing_turns) < target:
        cand = fallback_pool[idx % len(fallback_pool)]
        idx += 1
        needed_spk = "Host1" if cur_speaker == "Host2" else "Host2"
        existing_turns.append({
            "speaker": needed_spk,
            "swedish": cand["swedish"],
            "english": cand["english"]
        })
        cur_speaker = needed_spk
    return existing_turns[:target]


def generate_script():
    topic = _generate_topic() or random.choice(TOPICS)
    topic_es = topic.split(" - ")[0]
    topic_en = topic.split(" - ")[1]

    TARGET = 150
    BATCH = 10
    all_turns = []
    consecutive_empty = 0
    import time as _time
    _deadline = _time.time() + 600  # generous 10 min cap

    while len(all_turns) < TARGET and consecutive_empty < 12 and _time.time() < _deadline:
        batch = _fetch_turns_batch(topic, topic_es, topic_en, len(all_turns), BATCH)
        if not batch:
            consecutive_empty += 1
            wait_s = min(15, 3 + consecutive_empty * 2)
            print(f"  API busy (consecutive fails: {consecutive_empty}) - waiting {wait_s}s before retrying...", flush=True)
            _time.sleep(wait_s)
            continue
        all_turns.extend(batch)
        consecutive_empty = 0
        print(f"  Script progress: {len(all_turns)}/{TARGET} turns", flush=True)
        if len(all_turns) < TARGET:
            _time.sleep(1)

    all_turns = all_turns[:TARGET]

    if not all_turns:
        print("  Using structured fallback script (150 unique turns)...", flush=True)
        all_turns = _fallback_script(topic_es, topic_en, TARGET)
    elif len(all_turns) < TARGET:
        print(f"  Extending {len(all_turns)} turns to {TARGET} with topic conversation...", flush=True)
        all_turns = _extend_script(all_turns, topic_es, topic_en, TARGET)

    # Short 2-line intro: Erik (Host2) first, then Astrid (Host1), then topic
    all_turns[0]["speaker"] = "Host2"
    all_turns[0]["swedish"] = f"Hej, jag är Erik. Välkommen till Velocity Swedish. Idag pratar vi om **{topic_es}**."
    all_turns[0]["english"] = f"Hi, I'm Erik. Welcome to Velocity Swedish Podcast. Today we talk about {topic_en}."
    if len(all_turns) > 1:
        all_turns[1]["speaker"] = "Host1"
        all_turns[1]["swedish"] = f"Tack, Erik. Dagens ämne är väldigt **intressant**. Låt oss börja."
        all_turns[1]["english"] = f"Thanks, Erik. Today's topic is very interesting. Let's start."

    print(f"  Script: {len(all_turns)} turns, topic: {topic_es}", flush=True)
    return all_turns, topic_es, topic_en


async def generate_audio(turns, target_dir=None):
    import edge_tts
    audio_files = []
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        audio_dir = Path(target_dir) if target_dir else OUTPUT_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        filename = audio_dir / f"audio_{i:03d}.mp3"
        spoken_text = re.sub(r'\*\*(.*?)\*\*', r'\1', turn.get("swedish", turn.get("spanish", "")))
        try:
            communicate = edge_tts.Communicate(spoken_text, voice)
            await communicate.save(str(filename))
            try:
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(filename)], capture_output=True, text=True)
                duration = float(r.stdout.strip()) if r.stdout else 3.0
            except:
                duration = 3.0
        except Exception as e:
            print(f"  Audio {i} failed: {e}")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(filename)], capture_output=True)
            duration = 3.0
        audio_files.append({"path": str(filename), "duration": duration, "speaker": turn["speaker"]})
    return audio_files

def create_video(turns, audio_files, video_dir=None):
    if video_dir is None:
        video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir = Path(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0

    for i, (turn, audio) in enumerate(zip(turns, audio_files)):
        img = video_dir / f"f_{i:04d}.png"
        create_frame(turn, str(img), i)
        clip = video_dir / f"c_{i:04d}.mp4"
        clips.append(clip)
        dur = audio["duration"]
        fade_start = max(0.0, dur - 0.3)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", audio["path"],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-preset", "medium",
            "-t", str(dur), "-af", f"afade=t=out:st={fade_start:.2f}:d=0.3",
            str(clip)
        ], check=True, capture_output=True)

        total_dur += audio["duration"]
        if (i + 1) % 25 == 0:
            print(f"  Frame {i+1}/{len(turns)}")

    concat = video_dir / "list.txt"
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = video_dir / "podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-movflags", "+faststart", str(out)], check=True)

    for c in clips:
        c.unlink(missing_ok=True)
    for a in audio_files:
        try:
            Path(a["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if concat.exists():
        concat.unlink(missing_ok=True)

    return out, total_dur


async def main():
    print("=" * 60)
    print("  VELOCITY SWEDISH PODCAST")
    print("=" * 60)

    print("\n[1/4] Generating script (150 turns)...")
    turns, topic_es, topic_en = generate_script()

    video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(video_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump({"topic": topic_es, "topic_en": topic_en, "turns": turns}, f, indent=2, ensure_ascii=False)

    print(f"\n[2/4] Generating audio ({len(turns)} turns)...")
    audio_files = await generate_audio(turns, video_dir)
    total_audio = sum(a["duration"] for a in audio_files)
    print(f"  Total audio: {total_audio/60:.1f} min")

    print(f"\n[3/4] Creating video...")
    video_path, duration = create_video(turns, audio_files, video_dir)

    print(f"\n[4/4] Saving...")
    first_frame = video_dir / "f_0000.png"
    thumbnail_path = video_dir / "thumbnail.jpg"
    try:
        from PIL import Image as _Img
        if first_frame.exists():
            _Img.open(str(first_frame)).convert("RGB").save(str(thumbnail_path), quality=92)
    except Exception as e:
        print(f"  Thumbnail warn: {e}")

    title = build_podcast_title(topic_es, topic_en)
    description = build_podcast_description(topic_es, topic_en, len(turns), round(duration / 60, 1))
    tags = ["Learn Swedish", "Swedish", "Swedish Podcast", "Learn Swedish Naturally",
            "Swedish for Beginners", "Bilingual", "Swedish Listening", "Swedish Conversation",
            topic_es, "Velocity Swedish"]

    meta_out = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_english": topic_es,
        "language": "Swedish",
        "duration_minutes": round(duration / 60, 1),
        "turns_count": len(turns),
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "generated_at": datetime.now().isoformat(),
    }
    (OUTPUT_DIR).mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "latest_video.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DIR / "latest_upload_info.json", "w", encoding="utf-8") as f:
        json.dump({"title": title, "description": description,
                   "category": topic_es, "turns_count": len(turns)}, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("  PODCAST COMPLETE!")
    print(f"  Topic: {topic_es}")
    print(f"  Duration: {duration/60:.1f} min ({len(turns)} turns)")
    print(f"  Video: {video_path.name}")
    print("=" * 60)


def build_podcast_title(topic_es, topic_en):
    titles = [
        f"Swedish Podcast: {topic_es} | Lär dig svenska",
        f"Learn Swedish: {topic_es} | Bilingual Podcast",
        f"{topic_es} | Swedish Conversation for Beginners",
        f"{topic_es} | Öva din svenska med Astrid och Erik",
    ]
    return random.choice(titles)


def build_podcast_description(topic_es, topic_en, turns_count, duration_min):
    description = (
        f"🎙️ Välkommen till Velocity Swedish Podcast!\n\n"
        f"I detta avsnitt pratar Astrid och Erik om: {topic_es} ({topic_en}).\n"
        f"En avslappnad tvåspråkig konversation på A2-nivå för att lära sig svenska på ett naturligt sätt.\n\n"
        f"✨ WHAT'S INSIDE THIS EPISODE:\n"
        f"• {turns_count} användbara meningar och uttryck på svenska\n"
        f"• Äkta samtal med vardagsvokabulär\n"
        f"• Naturligt uttal från infödda talare\n"
        f"• Engelsk översättning på varje rad\n\n"
        f"📌 HOW TO USE THIS PODCAST:\n"
        f"1️⃣ Lyssna på den svenska delen och försök förstå\n"
        f"2️⃣ Kontrollera den engelska översättningen\n"
        f"3️⃣ Upprepa meningarna högt\n"
        f"4️⃣ Lyssna igen imorgon - varje dag blir det lättare!\n\n"
        f"🔔 Prenumerera för en ny lektion varje dag.\n\n"
        f"📅 Längd: {duration_min} minuter\n\n"
        f"#LearnSwedish #SwedishPodcast #Bilingual #LanguageLearning"
    )
    return description



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('  Cancelled.')