import streamlit as st
import streamlit.components.v1 as components
import random
import requests
import base64
import re
import hmac
import time
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon=None,
    layout="centered"
)

KOREA_TZ = ZoneInfo("Asia/Seoul")

GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"
GEMINI_MAX_RETRIES = 2

GEMINI_PROMPT_TEMPLATE = """# Role
You are an expert Japanese-Korean lexicographer and kanji etymologist. Your task is to parser and enrich a provided list of Japanese words into a highly structured, educational format.

# Target Format Rules
For EVERY word in the input list, you must output exactly in the following format:

[Japanese Word]
[Korean Meaning]([Yomigana in Hiragana/Katakana])
[Kanji 1] ([Korean Hanja Meaning/Sound]) = [Components Breakdown if applicable] : [Detailed Etymology/Origin Story]
[Kanji 2] ([Korean Hanja Meaning/Sound]) = [Components Breakdown if applicable] : [Detailed Etymology/Origin Story]
... (Repeat for all Kanji in the word)
[Comprehensive explanation of the word's holistic meaning based on its components or origin]

* Constraints for Katakana/Loan Words: If the word is Katakana (e.g., マ신, セットアップ), explain its English origin and its specific IT/contextual meaning instead of Kanji breakdown.

# Output Control & Completeness Metric
1. Do not skip any words. Translate and break down as many as possible within your output token limit.
2. If you cannot complete the entire list due to output token limits, stop gracefully at the last possible word and append the completeness metric at the very end.
3. The completeness metric must state: "완료율: [Completed Count] / [Total Input Count] ([Percentage]%) 완료되었습니다."

# Examples

灰皿
재떨이(はいざら)
灰 (재 회) = 厂 (기슭 엄/손) + 火 (불 화) : 불(火)이 다 타고 남은 찌꺼기를 손(厂)으로 만지는 모습에서 재를 뜻합니다.
皿 (그릇 명) = 음식을 담는 오목한 그릇의 모양을 본뜬 상형자입니다.
담배를 피우고 난 뒤 남은 재(灰)를 털어서 안전하게 담아두는 작은 그릇(皿)을 의미합니다.

制作・する
제작·하다(せいさく・する)
制 (절제할 제/지을 제) = 未 (아닐 미/나뭇가지) + 刂 (칼 도) : 칼(刂)로 나뭇가지(未)를 쳐내어 모양을 다듬고 짓는다는 뜻입니다.
作 (지을 작) = 亻 (사람 인) + 乍 (잠깐 사/옷깃) : 사람(亻)이 옷깃(乍)을 여미고 무언가를 만들어 내는 일에 착수한다는 뜻입니다.
예술 작품이나 도구, 물건 등을 일정한 기준에 맞춰 다듬고(制) 새롭게 만들어 내는(作) 작업을 의미합니다.

マシン
머신, 기계(マシン)
Machine (머신) = 기계 장치를 뜻하는 영어 단어에서 유래했습니다.
컴퓨터, 서버, 혹은 복잡한 부품으로 이루어져 특정한 동력이나 연산을 수행하는 하드웨어 장비를 의미합니다.

# Input Data
Here is the raw list of Japanese words you need to process:
---
{word_list}
---
"""


# ---------------------------
# 1. Session State 초기화
# ---------------------------
def init_session_state() -> None:
    defaults = {
        "words": [],
        "current_files_label": [],

        "study_index": 0,
        "is_studying": False,
        "study_show_hint": False,

        "practice_queue": [],
        "practice_total_count": 0,
        "practice_done_count": 0,
        "current_practice_word": None,
        "is_practicing": False,
        "practice_display_side": 0,
        "practice_mode": "random",
        "practice_show_answer": False,
        "practice_show_hint": False,
        "practice_wrong_words": [],

        "exam_queue": [],
        "current_exam_word": None,
        "is_examining": False,
        "exam_mode": None,
        "exam_total_count": 10,
        "exam_current_number": 0,
        "exam_correct_count": 0,
        "exam_wrong_count": 0,
        "exam_show_answer": False,
        "exam_display_side": 0,
        "exam_total_count_input": 10,
        "exam_wrong_words": [],

        "font_scale": 1.0,
        "theme_mode": "다크 모드",

        "script_lines": [],
        "script_index": 0,
        "is_scripting": False,

        "sidebar_main_cat": None,
        "sidebar_sub_cats": [],
        "sidebar_file_search": "",

        "active_part": None,
        "current_page_select": "학습",

        "favorite_words": {},
        "use_favorites_only": False,

        "toast_queue": [],

        "gemini_raw_input": "",
        "gemini_converted_result": "",
        "manual_wordbook_text_area": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_focus_active() -> bool:
    """학습/연습/시험/지문 중 하나라도 진행 중이면 True. 이 경우 상단 UI를 최소화한다."""
    return (
        st.session_state.is_studying
        or st.session_state.is_practicing
        or st.session_state.is_examining
        or st.session_state.is_scripting
    )


def exit_focus_mode() -> None:
    """진행 중인 세션을 종료하고 전체 UI(제목, 파트 이동, 파일 선택 등)를 다시 보여준다."""
    st.session_state.is_studying = False
    st.session_state.is_practicing = False
    st.session_state.is_examining = False
    st.session_state.is_scripting = False
    st.session_state.active_part = None


def render_exit_button(label: str = "학습 종료하기") -> None:
    """화면 맨 아래에 작게 배치되는 종료 버튼. 누르면 전체 UI로 돌아간다."""
    st.write("")
    left, mid, right = st.columns([3, 2, 3])
    with mid:
        if st.button(label, use_container_width=True, key=f"exit_focus_{label}"):
            exit_focus_mode()
            st.rerun()


def push_toast(message: str, icon: str = "ℹ️") -> None:
    st.session_state.toast_queue.append((message, icon))


def flush_toasts() -> None:
    for message, icon in st.session_state.toast_queue:
        st.toast(message, icon=icon)
    st.session_state.toast_queue = []


def word_key(w: dict) -> str:
    return f"{w['word']}|||{w['meaning']}"


def toggle_favorite(w: dict) -> None:
    key = word_key(w)
    if key in st.session_state.favorite_words:
        del st.session_state.favorite_words[key]
    else:
        st.session_state.favorite_words[key] = w


def is_favorite(w: dict) -> bool:
    return word_key(w) in st.session_state.favorite_words


# ---------------------------
# 2. 글로벌 CSS 스타일
# ---------------------------
def apply_global_style() -> None:
    scale = st.session_state.font_scale
    base = int(16 * scale)

    is_dark = (st.session_state.theme_mode == "다크 모드")
    focus_on = is_focus_active()

    card_bg = "#22222b" if is_dark else "#ffffff"
    border_color = "#38383f" if is_dark else "#e4e4e8"
    text_color = "#f0f0f3" if is_dark else "#1c1c1f"
    word_color = "#8aa6ff" if is_dark else "#4a5fd6"
    hint_bg = "#2a2a33" if is_dark else "#f2f2f6"
    hint_text = "#d8d8de" if is_dark else "#42424a"
    ans_color = "#5fbf7a" if is_dark else "#1f8a44"
    muted_color = "#98989f" if is_dark else "#6b6b72"
    accent_bg = "#1f2233" if is_dark else "#eef0fa"
    accent_text = "#9db2ff" if is_dark else "#3d4ea8"
    sticky_bg = "#1a1a20" if is_dark else "#fafafc"
    fav_color = "#ffcf4d"

    focus_header_css = """
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0.4rem !important; }
    """ if focus_on else ""

    st.markdown(f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');

        html, body, [data-testid="stAppViewContainer"] {{
            font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}

        html {{ font-size: clamp(14px, 1vw + 10px, {base}px); }}

        .block-container {{
            padding-top: 1rem;
            padding-bottom: 1.6rem;
            max-width: 720px;
        }}

        {focus_header_css}

        h1, h2, h3 {{ font-weight: 700 !important; letter-spacing: -0.01em; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to   {{ opacity: 1; }}
        }}

        .sticky-action-bar {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: {sticky_bg};
            padding: 8px 0 8px 0;
            margin-bottom: 6px;
            border-bottom: 1px solid {border_color};
        }}
        .sticky-action-bar .stButton > button {{
            padding-top: 0.55rem !important;
            padding-bottom: 0.55rem !important;
        }}

        .study-card {{
            background: {card_bg};
            border: 1px solid {border_color};
            border-radius: 14px;
            padding: clamp(16px, 3vw, 28px) clamp(14px, 3vw, 24px);
            margin: 10px 0;
            animation: fadeIn 0.25s ease both;
            position: relative;
        }}
        .word-text {{
            font-size: clamp(1.3rem, 2.4vw, 1.7rem) !important;
            font-weight: 700; margin-bottom: 8px; text-align: center;
            color: {word_color};
        }}
        .meaning-text {{ font-size: clamp(1.1rem, 2vw, 1.4rem) !important; color: {text_color}; margin-bottom: 4px; text-align: center; }}
        .hint-box {{
            font-size: clamp(0.92rem, 1.6vw, 1.05rem) !important; color: {hint_text}; background-color: {hint_bg};
            padding: 10px 14px; border-radius: 10px; margin-top: 10px; line-height: 1.6;
        }}
        .qa-compact {{ padding: clamp(14px, 3vw, 22px) clamp(14px, 3vw, 20px) !important; margin: 6px 0 !important; }}
        .qa-compact .test-question {{ padding: 2px 4px 2px 4px !important; }}
        .qa-compact .test-answer {{ margin: 2px 0 4px 0 !important; }}
        .qa-compact .hint-box {{ margin-top: 6px !important; }}
        .hint-box b {{ color: {muted_color}; font-weight: 600; }}
        .script-text {{ font-size: clamp(1.1rem, 2vw, 1.35rem) !important; font-weight: 600; color: {word_color}; text-align: left; line-height: 1.85; }}

        .test-question {{
            font-size: clamp(1.5rem, 4vw, 2.2rem) !important; color: {text_color}; text-align: center; padding: 10px 8px 4px 8px;
            font-weight: 700; word-break: break-word;
        }}
        .test-answer {{
            font-size: clamp(1.05rem, 1.9vw, 1.3rem) !important; text-align: center; color: {ans_color}; font-weight: 700; margin: 2px 0 10px 0;
        }}

        .progress-caption {{ text-align: center; color: {muted_color}; margin-top: 4px; font-size: 0.85rem; }}

        .active-files-box {{
            background: {accent_bg};
            color: {accent_text};
            border-radius: 10px;
            padding: 8px 12px;
            margin: 6px 0 2px 0;
            font-size: 0.8rem;
            line-height: 1.5;
            word-break: break-all;
        }}

        .fav-star {{ color: {fav_color}; font-size: 1.1rem; }}

        .gemini-result-box {{
            background: {hint_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 12px 14px;
            margin-top: 8px;
            white-space: pre-wrap;
            font-size: 0.9rem;
            line-height: 1.6;
            max-height: 420px;
            overflow-y: auto;
        }}

        div[data-testid="stButton"] > button {{
            font-weight: 600 !important; border-radius: 10px !important;
            transition: background-color 0.12s ease !important;
        }}

        div[data-testid="stProgress"] div[role="progressbar"] > div {{
            transition: width 0.4s ease !important;
        }}

        div[data-testid="stCheckbox"] {{ display: flex; justify-content: flex-start; }}
        .file-check-row div[data-testid="stCheckbox"] label p {{
            white-space: nowrap !important;
            overflow-x: auto !important;
        }}

        div[data-testid="stAlert"] {{ border-radius: 10px !important; }}

        div[data-testid="stRadio"] > div {{
            background: {hint_bg};
            border-radius: 12px;
            padding: 4px;
            gap: 2px !important;
        }}
        div[data-testid="stRadio"] label {{
            border-radius: 9px !important;
            padding: 7px 10px !important;
            font-weight: 600 !important;
        }}
        div[data-testid="stRadio"] label:has(input:checked) {{
            background: {word_color} !important;
        }}
        div[data-testid="stRadio"] label:has(input:checked) p {{
            color: #ffffff !important;
        }}
        div[data-testid="stRadio"] input {{ display: none !important; }}

        .cat-group-title {{
            font-weight: 700; font-size: 0.95rem; margin: 10px 0 4px 0; color: {word_color};
        }}

        @media (max-width: 1024px) {{
            .block-container {{ padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
            .mobile-stack div[data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
                gap: 6px !important;
            }}
            .mobile-stack div[data-testid="column"] {{
                width: 100% !important;
                min-width: 100% !important;
                padding: 0 !important;
            }}
        }}

        @media (min-width: 1400px) {{
            .block-container {{ max-width: 820px; }}
        }}
        </style>
    """, unsafe_allow_html=True)


def mobile_stack_container(key: str):
    box = st.container(key=key)
    return box


def sticky_action_bar(key: str):
    st.markdown('<div class="sticky-action-bar">', unsafe_allow_html=True)
    box = st.container(key=key)
    st.markdown('</div>', unsafe_allow_html=True)
    return box


def inject_session_keepalive() -> None:
    components.html("""
        <script>
        const win = window.parent;
        if (!win.hasOwnProperty('_keepalive_attached')) {
            win._keepalive_attached = true;
            setInterval(function() {
                try {
                    fetch(win.location.href, { method: 'GET', cache: 'no-store', mode: 'no-cors' });
                } catch (e) {}
            }, 3 * 60 * 1000);
        }
        </script>
    """, height=0, width=0)


def inject_keyboard_shortcuts() -> None:
    components.html("""
        <script>
        const doc = window.parent.document;
        if (!doc.hasOwnProperty('_shortcuts_attached')) {
            doc._shortcuts_attached = true;
            doc.addEventListener('keydown', function(e) {
                const tag = doc.activeElement.tagName;
                if (['INPUT', 'TEXTAREA'].includes(tag)) return;

                let key = e.key.toLowerCase();
                let buttons = Array.from(doc.querySelectorAll('button'));

                function clickBtn(matches) {
                    let btn = buttons.find(b => matches.some(m => b.innerText.includes(m)));
                    if (btn && !btn.disabled) {
                        btn.click();
                        return true;
                    }
                    return false;
                }

                if (key === ' ') {
                    if (clickBtn(['다음 단어', '정답 확인', '다음 문장'])) {
                        e.preventDefault();
                    }
                }
                else if (key === 'h') { clickBtn(['힌트 보기']); }
                else if (key === 'z') { clickBtn(['완벽함', '맞음']); }
                else if (key === 'x') { clickBtn(['조금 앎', '틀림']); }
                else if (key === 'c') { clickBtn(['헷갈림']); }
                else if (key === 'v') { clickBtn(['모름']); }
                else if (key === 'f') { clickBtn(['즐겨찾기']); }
            });
        }
        </script>
    """, height=0, width=0)


def change_font_scale(amount: float) -> None:
    st.session_state.font_scale = max(0.8, min(2.0, st.session_state.font_scale + amount))


# ---------------------------
# 3. GitHub API 및 캐싱
# ---------------------------
def get_github_headers() -> dict:
    token = str(st.secrets["github_token"]).strip()
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def get_repo_info() -> tuple:
    owner = str(st.secrets["github_owner"]).strip()
    repo = str(st.secrets["github_repo"]).strip()
    branch = str(st.secrets["github_branch"]).strip()
    return owner, repo, branch


def github_status_message(status: int) -> str:
    messages = {
        401: "GitHub 인증에 실패했습니다. github_token 설정을 확인해주세요.",
        403: "GitHub API 요청 한도를 초과했거나 접근 권한이 없습니다. 잠시 후 다시 시도해주세요.",
        404: "요청한 경로를 GitHub 저장소에서 찾을 수 없습니다.",
    }
    return messages.get(status, f"GitHub API 오류가 발생했습니다 (status: {status}).")


@st.cache_data(ttl=300, show_spinner=False)
def github_get_contents(path: str):
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path.strip(), safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return 0, {}
    return response.status_code, response.json() if response.status_code == 200 else {}


def get_dynamic_categories() -> tuple:
    status, data = github_get_contents("word_list")
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "dir"]), None
    return [], github_status_message(status)


def get_subfolders(main_category: str) -> list:
    status, data = github_get_contents(f"word_list/{main_category}")
    if status == 200 and isinstance(data, list):
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return sorted(folders) if folders else []
    return []


def get_txt_files(folder_path: str) -> list:
    status, data = github_get_contents(folder_path)
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "file" and item["name"].lower().endswith(".txt")])
    return []


def get_file_content(repo_file_path: str) -> str:
    status, data = github_get_contents(repo_file_path)
    if status == 200:
        return base64.b64decode(data.get("content", "")).decode("utf-8")
    return ""


def upload_text_to_github(folder_path: str, file_name: str, text_content: str):
    owner, repo, branch = get_repo_info()
    repo_path = f"{str(folder_path).strip()}/{str(file_name).strip()}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}"

    content_b64 = base64.b64encode(text_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Add file: {repo_path}",
        "content": content_b64,
        "branch": branch
    }

    response = requests.put(url, headers=get_github_headers(), json=payload, timeout=30)
    return response, repo_path


def clear_github_cache() -> None:
    st.cache_data.clear()


# ---------------------------
# 3-1. Gemini API 연동 (단어 변환)
# ---------------------------
def get_gemini_api_key() -> str:
    return str(st.secrets.get("gemini_api_key", "")).strip()


def convert_words_with_gemini(raw_words: str) -> tuple:
    """입력한 단어 목록을 Gemini에 보내 지정된 형식으로 변환한다. (결과 텍스트, 에러 메시지) 튜플을 반환."""
    api_key = get_gemini_api_key()
    if not api_key:
        return "", "Secrets에 gemini_api_key가 설정되어 있지 않습니다."
    if not raw_words.strip():
        return "", "변환할 단어를 입력해주세요."

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    prompt = GEMINI_PROMPT_TEMPLATE.format(word_list=raw_words.strip())

    last_error = None
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            text = (response.text or "").strip() if response else ""
            if not text:
                return "", "Gemini가 빈 응답을 반환했습니다. 다시 시도해주세요."
            return text, None
        except ResourceExhausted as e:
            last_error = e
            if attempt < GEMINI_MAX_RETRIES:
                time.sleep(15)
                continue
            return "", (
                "Gemini 무료 할당량을 초과했습니다. 잠시 후 다시 시도하거나, "
                f"Google AI Studio에서 결제를 등록해주세요. (모델: {GEMINI_MODEL_NAME})"
            )
        except Exception as e:
            return "", f"Gemini 호출 중 오류가 발생했습니다: {e}"

    return "", f"Gemini 호출 중 오류가 발생했습니다: {last_error}"


def convert_gemini_output_to_word_format(gemini_text: str) -> str:
    """
    Gemini 출력(단어 / 뜻(요미가나) / 한자 풀이... / 종합 설명)을
    기존 단어장 파싱 형식인 '단어 : 뜻' + 힌트(한자 풀이+종합 설명) 로 변환한다.
    """
    normalized = gemini_text.replace("\r\n", "\n")
    lines = [l for l in normalized.split("\n")]

    blocks = []
    current_block = []
    for line in lines:
        if line.strip() == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue
        if line.strip().startswith("완료율"):
            continue
        current_block.append(line)
    if current_block:
        blocks.append(current_block)

    output_lines = []
    for block in blocks:
        if len(block) < 2:
            continue
        word = block[0].strip()
        meaning_line = block[1].strip()
        hint_lines = block[2:]
        hint_text = "\n".join(l.strip() for l in hint_lines if l.strip())

        output_lines.append(f"{word} : {meaning_line}")
        if hint_text:
            output_lines.append(hint_text)
        output_lines.append("")

    return "\n".join(output_lines).strip()


# ---------------------------
# 4. 단어 파싱 / 지문 파싱 유틸
# ---------------------------
def parse_word_text(text: str) -> list:
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
    parsed_words = []
    i = 0

    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1

        if not block:
            continue

        if ":" in block[0]:
            parts = block[0].split(":", 1)
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if word and meaning:
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) >= 2:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if word and meaning:
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    seen, result = set(), []
    for w in parsed_words:
        key = (w["word"], w["meaning"], w["hint"])
        if key not in seen:
            seen.add(key)
            result.append(w)
    return result


def parse_script_text(text: str) -> list:
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    return [line.strip() for line in lines if line.strip()]


def parse_words_with_validation(text: str) -> tuple:
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
    parsed_words, errors = [], []
    i = 0

    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        block_start = i
        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1

        if not block:
            continue

        if ":" in block[0]:
            parts = block[0].split(":", 1)
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if not word:
                errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
            elif not meaning:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없습니다.")
            else:
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) == 1:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없는 단어입니다.")
            else:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if not word:
                    errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
                elif not meaning:
                    errors.append(f"{block_start + 2}번 줄: 뜻이 없습니다.")
                else:
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    return parsed_words, errors


def make_safe_filename(name: str) -> str:
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_name = str(name).strip()
    for ch in invalid_chars:
        safe_name = safe_name.replace(ch, "_")
    if not safe_name:
        safe_name = "untitled"
    if not safe_name.lower().endswith(".txt"):
        safe_name += ".txt"
    return safe_name


def get_default_title_prefix() -> str:
    korea_now = datetime.now(KOREA_TZ)
    return korea_now.strftime("%Y-%m-%d_")


def build_word_pool(selected_files: list) -> list:
    seen = set()
    pool = []
    for f in selected_files:
        text = get_file_content(f["path"])
        for w in parse_word_text(text):
            key = (w["word"], w["meaning"], w["hint"])
            if key not in seen:
                seen.add(key)
                pool.append(w)
    return pool


def get_session_rng() -> random.Random:
    if "session_rng" not in st.session_state:
        st.session_state.session_rng = random.Random()
    return st.session_state.session_rng


def get_display_side(mode: str) -> int:
    rng = get_session_rng()
    if mode == "random":
        return rng.choice([0, 1])
    return 0 if mode == "meaning_only" else 1


def requeue_position(queue_len: int, level: int) -> int:
    if queue_len <= 1:
        return 0
    ranges = {60: (0.5, 0.8), 40: (0.2, 0.4), 0: (0.05, 0.15)}
    lo, hi = ranges[level]
    lo_idx = max(0, int(queue_len * lo))
    hi_idx = max(lo_idx, int(queue_len * hi))
    return get_session_rng().randint(lo_idx, hi_idx)


def render_active_files_banner() -> None:
    labels = st.session_state.get("current_files_label", [])
    if not labels:
        return
    items = "".join([f"- {lbl}<br>" for lbl in labels])
    st.markdown(
        f"<div class='active-files-box'><b>현재 학습 파일 ({len(labels)}개)</b><br>{items}</div>",
        unsafe_allow_html=True
    )


# ---------------------------
# 5. UI - 사이드바
# ---------------------------
def render_sidebar() -> list:
    with st.sidebar:
        with st.expander("화면 설정", expanded=False):
            new_theme = st.selectbox(
                "테마 선택", ["기본 모드", "다크 모드"],
                index=1 if st.session_state.theme_mode == "다크 모드" else 0,
                key="global_theme_select"
            )
            if new_theme != st.session_state.theme_mode:
                st.session_state.theme_mode = new_theme
                st.rerun()

            col1, col2, col3 = st.columns(3)
            if col1.button("크게", use_container_width=True):
                change_font_scale(0.1); st.rerun()
            if col2.button("작게", use_container_width=True):
                change_font_scale(-0.1); st.rerun()
            if col3.button("초기화", use_container_width=True):
                st.session_state.font_scale = 1.0; st.rerun()

        st.write("---")

        if st.session_state.favorite_words:
            fav_col1, fav_col2 = st.columns([3, 2])
            with fav_col1:
                st.caption(f"즐겨찾기 {len(st.session_state.favorite_words)}개 등록됨")
            with fav_col2:
                st.session_state.use_favorites_only = st.checkbox(
                    "즐겨찾기만 사용", value=st.session_state.use_favorites_only, key="fav_only_checkbox"
                )
            st.write("---")

        if st.session_state.use_favorites_only:
            st.info("즐겨찾기에 등록된 단어만 사용합니다. 아래 파일 선택은 무시됩니다.")
            return list(st.session_state.favorite_words.values())

        st.subheader("학습 자료 선택")

        categories, cat_error = get_dynamic_categories()
        if cat_error:
            st.error(cat_error)
            return []
        if not categories:
            st.error("word_list 폴더를 찾을 수 없습니다.")
            return []

        if st.session_state.sidebar_main_cat not in categories:
            st.session_state.sidebar_main_cat = categories[0]

        main_cat = st.selectbox("1. 대분류 선택", categories, key="sidebar_main_cat")
        sub_folders = get_subfolders(main_cat)

        if sub_folders:
            st.session_state.sidebar_sub_cats = [
                s for s in st.session_state.sidebar_sub_cats if s in sub_folders
            ] or sub_folders
            selected_subs = st.multiselect("2. 세부 카테고리 선택 (예: N2, N3)", sub_folders, key="sidebar_sub_cats")
        else:
            selected_subs = []

        groups = {}
        if sub_folders:
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                files = [{"path": f"{path}/{f}", "label": f"[{sub}] {f}"} for f in get_txt_files(path)]
                groups[sub] = files
        else:
            path = f"word_list/{main_cat}"
            files = [{"path": f"{path}/{f}", "label": f} for f in get_txt_files(path)]
            groups[main_cat] = files

        all_files = [f for files in groups.values() for f in files]
        if not all_files:
            st.warning("선택한 카테고리에 파일이 없습니다.")
            return []

        st.write("**3. 파일 선택**")

        search_term = st.text_input(
            "파일 검색", value=st.session_state.sidebar_file_search,
            placeholder="파일명으로 검색...", key="sidebar_file_search_input"
        )
        st.session_state.sidebar_file_search = search_term

        all_widget_keys = [f"filechk_{f['label']}_widget" for f in all_files]
        for wk in all_widget_keys:
            if wk not in st.session_state:
                st.session_state[wk] = False

        overall_col1, overall_col2 = st.columns(2)
        with overall_col1:
            if st.button("전체 선택", use_container_width=True, key="select_all_files_btn"):
                for wk in all_widget_keys:
                    st.session_state[wk] = True
                st.rerun()
        with overall_col2:
            if st.button("전체 해제", use_container_width=True, key="deselect_all_files_btn"):
                for wk in all_widget_keys:
                    st.session_state[wk] = False
                st.rerun()

        search_lower = search_term.strip().lower()

        for group_name, files in groups.items():
            filtered_files = [f for f in files if search_lower in f["label"].lower()] if search_lower else files
            if not filtered_files:
                continue
            st.markdown(f"<div class='cat-group-title'>{group_name}</div>", unsafe_allow_html=True)

            group_widget_keys = [f"filechk_{f['label']}_widget" for f in filtered_files]
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                if st.button(f"{group_name} 전체 선택", use_container_width=True, key=f"grp_sel_{group_name}"):
                    for wk in group_widget_keys:
                        st.session_state[wk] = True
                    st.rerun()
            with g_col2:
                if st.button(f"{group_name} 전체 해제", use_container_width=True, key=f"grp_desel_{group_name}"):
                    for wk in group_widget_keys:
                        st.session_state[wk] = False
                    st.rerun()

            st.markdown('<div class="file-check-row">', unsafe_allow_html=True)
            for f in filtered_files:
                wk = f"filechk_{f['label']}_widget"
                st.checkbox(f["label"], key=wk)
            st.markdown('</div>', unsafe_allow_html=True)

        selected_labels = [
            f["label"] for f in all_files
            if st.session_state.get(f"filechk_{f['label']}_widget", False)
        ]

        return [f for f in all_files if f["label"] in selected_labels]


def load_data(selected_files: list, is_script: bool = False) -> bool:
    if not selected_files:
        st.warning("사이드바에서 파일을 선택해주세요.")
        return False

    if st.session_state.use_favorites_only and not is_script:
        st.session_state.current_files_label = ["즐겨찾기 단어 모음"]
        pool = list(selected_files)
        get_session_rng().shuffle(pool)
        st.session_state.words = pool
        return True

    st.session_state.current_files_label = [f["label"] for f in selected_files]

    if is_script:
        merged = []
        for f in selected_files:
            text = get_file_content(f["path"])
            merged.extend(parse_script_text(text))
        st.session_state.script_lines = merged
    else:
        pool = build_word_pool(selected_files)
        get_session_rng().shuffle(pool)
        st.session_state.words = pool

    return True


def load_words_from_list(words: list) -> bool:
    if not words:
        st.warning("불러올 단어가 없습니다.")
        return False
    st.session_state.current_files_label = ["오답 노트 다시 보기"]
    pool = list(words)
    get_session_rng().shuffle(pool)
    st.session_state.words = pool
    return True


def render_favorite_toggle_button(w: dict, key_prefix: str) -> None:
    fav = is_favorite(w)
    label = "★ 즐겨찾기 해제" if fav else "☆ 즐겨찾기 추가"
    if st.button(label, use_container_width=True, key=f"{key_prefix}_fav_btn"):
        toggle_favorite(w)
        push_toast("즐겨찾기에서 제거했습니다." if fav else "즐겨찾기에 추가했습니다.", icon="⭐")
        st.rerun()


# ---------------------------
# 6. 학습 파트
# ---------------------------
def render_study_setup() -> None:
    st.header("학습 파트")
    st.caption("단축키: 스페이스바 = 다음 단어, H = 힌트 보기, F = 즐겨찾기")
    selected_files = render_sidebar()

    if st.button("학습 시작", use_container_width=True):
        if load_data(selected_files):
            st.session_state.is_studying = True
            st.session_state.active_part = "study"
            st.session_state.study_index = 0
            st.session_state.study_show_hint = False
            st.rerun()


def render_study_active() -> None:
    if st.session_state.study_index < len(st.session_state.words):
        word_data = st.session_state.words[st.session_state.study_index]
        has_hint = bool(word_data["hint"].strip())

        with sticky_action_bar("study_sticky_bar"):
            b1, b2, b3 = st.columns([2, 2, 2])
            with b1:
                if st.button("다음 단어", use_container_width=True, key="study_next_btn"):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False
                    st.rerun()
            with b2:
                if st.button("힌트 보기", use_container_width=True, disabled=not has_hint, key="study_hint_btn"):
                    st.session_state.study_show_hint = True
                    st.rerun()
            with b3:
                render_favorite_toggle_button(word_data, "study")

        fav_badge = "<span class='fav-star'>★</span> " if is_favorite(word_data) else ""

        st.markdown(f"""
            <div class="study-card qa-compact">
                <div class="word-text">{fav_badge}{word_data['word']}</div>
                <div class="meaning-text">{word_data['meaning']}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.session_state.study_show_hint and has_hint:
            st.markdown(
                f"<div class='hint-box'><b>힌트</b><br>{word_data['hint'].replace(chr(10), '<br>')}</div>",
                unsafe_allow_html=True
            )

        progress = (st.session_state.study_index) / max(1, len(st.session_state.words))
        st.progress(min(1.0, progress))
        st.markdown(
            f"<div class='progress-caption'>진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("모든 단어 학습을 완료했습니다.")
        if st.button("다시 처음부터", use_container_width=True):
            st.session_state.study_index = 0
            st.session_state.study_show_hint = False
            st.rerun()

    render_exit_button("학습 종료하기")


# ---------------------------
# 7. 연습 파트
# ---------------------------
def render_practice_setup() -> None:
    st.header("연습 파트 (망각 곡선 적용)")
    st.caption("단축키: 스페이스바 = 정답(힌트도 함께 표시), H = 힌트, Z=100 X=60 C=40 V=0, F = 즐겨찾기")
    selected_files = render_sidebar()

    with mobile_stack_container("practice_mode_btns"):
        c1, c2, c3 = st.columns(3)
        mode = None
        if c1.button("이름만 연습", use_container_width=True): mode = "word_only"
        if c2.button("뜻만 연습", use_container_width=True): mode = "meaning_only"
        if c3.button("랜덤 연습", use_container_width=True): mode = "random"

    if mode and load_data(selected_files):
        st.session_state.practice_queue = list(st.session_state.words)
        st.session_state.practice_total_count = len(st.session_state.practice_queue)
        st.session_state.practice_done_count = 0
        st.session_state.practice_wrong_words = []
        st.session_state.is_practicing = True
        st.session_state.active_part = "practice"
        st.session_state.practice_mode = mode
        st.session_state.practice_show_answer = False
        st.session_state.practice_show_hint = False

        if st.session_state.practice_queue:
            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
            st.session_state.practice_display_side = get_display_side(mode)
        st.rerun()


def render_practice_active() -> None:
    if st.session_state.current_practice_word:
        cw = st.session_state.current_practice_word
        has_hint = bool(cw["hint"].strip())
        is_ans_shown = st.session_state.practice_show_answer

        with sticky_action_bar("practice_sticky_bar"):
            top1, top2, top3 = st.columns([2, 2, 2])
            with top1:
                if st.button("정답 확인", use_container_width=True, key="practice_check_btn"):
                    st.session_state.practice_show_answer = True
                    st.session_state.practice_show_hint = has_hint
                    st.rerun()
            with top2:
                if st.button("힌트 보기", use_container_width=True, disabled=not has_hint, key="practice_hint_btn"):
                    st.session_state.practice_show_hint = True; st.rerun()
            with top3:
                render_favorite_toggle_button(cw, "practice")

            def apply_score(level: int) -> None:
                if level != 100:
                    pos = requeue_position(len(st.session_state.practice_queue), level)
                    st.session_state.practice_queue.insert(pos, cw)
                    if level in (40, 0):
                        if cw not in st.session_state.practice_wrong_words:
                            st.session_state.practice_wrong_words.append(cw)

                st.session_state.practice_done_count += 1
                st.session_state.practice_show_answer = False
                st.session_state.practice_show_hint = False
                if st.session_state.practice_queue:
                    st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                    st.session_state.practice_display_side = get_display_side(st.session_state.practice_mode)
                else:
                    st.session_state.current_practice_word = None

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                if st.button("완벽함 (100)", disabled=not is_ans_shown, use_container_width=True, key="practice_100"): apply_score(100); st.rerun()
            with s2:
                if st.button("조금 앎 (60)", disabled=not is_ans_shown, use_container_width=True, key="practice_60"): apply_score(60); st.rerun()
            with s3:
                if st.button("헷갈림 (40)", disabled=not is_ans_shown, use_container_width=True, key="practice_40"): apply_score(40); st.rerun()
            with s4:
                if st.button("모름 (0)", disabled=not is_ans_shown, use_container_width=True, key="practice_0"): apply_score(0); st.rerun()

        q_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]
        fav_badge = "<span class='fav-star'>★</span> " if is_favorite(cw) else ""

        card_html = f"<div class='study-card qa-compact'><div class='test-question'>{fav_badge}{q_text}</div>"
        if is_ans_shown:
            card_html += f"<div class='test-answer'>정답: {a_text}</div>"
        if st.session_state.practice_show_hint and has_hint:
            card_html += f"<div class='hint-box'><b>힌트</b><br>{cw['hint'].replace(chr(10), '<br>')}</div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        total = max(1, st.session_state.practice_total_count)
        st.progress(min(1.0, st.session_state.practice_done_count / total))
        st.markdown(
            f"<div class='progress-caption'>완료 {st.session_state.practice_done_count}개, 남은 큐 {len(st.session_state.practice_queue)}개</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("대기열의 모든 연습을 완료했습니다.")

        wrong_words = st.session_state.practice_wrong_words
        if wrong_words:
            st.markdown(f"**헷갈리거나 몰랐던 단어 {len(wrong_words)}개**")
            st.table([{"단어": w["word"], "뜻": w["meaning"]} for w in wrong_words])

            if st.button("오답만 다시 연습하기", use_container_width=True, key="practice_retry_wrong"):
                if load_words_from_list(wrong_words):
                    st.session_state.practice_queue = list(st.session_state.words)
                    st.session_state.practice_total_count = len(st.session_state.practice_queue)
                    st.session_state.practice_done_count = 0
                    st.session_state.practice_wrong_words = []
                    st.session_state.practice_show_answer = False
                    st.session_state.practice_show_hint = False
                    if st.session_state.practice_queue:
                        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                        st.session_state.practice_display_side = get_display_side(st.session_state.practice_mode)
                    st.rerun()
        else:
            st.info("오답 없이 전부 완벽하게 맞혔습니다.")

    render_exit_button("연습 종료하기")


# ---------------------------
# 8. 시험 파트
# ---------------------------
def render_exam_setup() -> None:
    st.header("시험 파트")
    st.caption("단축키: 스페이스바 = 정답 확인(힌트도 함께 표시), Z = 맞음, X = 틀림, F = 즐겨찾기")
    selected_files = render_sidebar()

    total_words = 0
    if selected_files:
        if st.session_state.use_favorites_only:
            total_words = len(selected_files)
        else:
            total_words = len(build_word_pool(selected_files))

    if total_words > 0:
        st.write("---")
        st.subheader("출제 개수 설정")

        current_val = min(st.session_state.exam_total_count_input, total_words)
        st.session_state.exam_total_count_input = current_val

        with mobile_stack_container("exam_count_btns"):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1], vertical_alignment="bottom")
            with col1:
                st.number_input(f"총 출제 개수 (최대 {total_words}개)", min_value=1, max_value=total_words, key="exam_total_count_input")
            with col2:
                if st.button("최대", use_container_width=True):
                    st.session_state.exam_total_count_input = total_words; st.rerun()
            with col3:
                if st.button("+5", use_container_width=True):
                    st.session_state.exam_total_count_input = min(total_words, current_val + 5); st.rerun()
            with col4:
                if st.button("-5", use_container_width=True):
                    st.session_state.exam_total_count_input = max(1, current_val - 5); st.rerun()

        st.write("---")

        with mobile_stack_container("exam_mode_btns"):
            m1, m2, m3 = st.columns(3)
            mode = None
            if m1.button("이름만 시험", use_container_width=True): mode = "word_only"
            if m2.button("뜻만 시험", use_container_width=True): mode = "meaning_only"
            if m3.button("랜덤 시험", use_container_width=True): mode = "random"

        if mode and load_data(selected_files):
            st.session_state.is_examining = True
            st.session_state.active_part = "exam"
            st.session_state.exam_mode = mode
            st.session_state.exam_current_number = 0
            st.session_state.exam_correct_count = 0
            st.session_state.exam_wrong_count = 0
            st.session_state.exam_show_answer = False
            st.session_state.exam_wrong_words = []

            exam_words = list(st.session_state.words)
            actual_count = min(st.session_state.exam_total_count_input, len(exam_words))
            st.session_state.exam_total_count = actual_count
            st.session_state.exam_queue = exam_words[:actual_count]

            if st.session_state.exam_queue:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                st.session_state.exam_display_side = get_display_side(mode)
            st.rerun()


def render_exam_active() -> None:
    if st.session_state.current_exam_word:
        cw = st.session_state.current_exam_word
        has_hint = bool(cw.get("hint", "").strip())
        is_ans_shown = st.session_state.exam_show_answer

        with sticky_action_bar("exam_sticky_bar"):
            top1, top2 = st.columns([3, 2])
            with top1:
                if st.button("정답 확인", use_container_width=True, key="exam_check_btn"):
                    st.session_state.exam_show_answer = True; st.rerun()
            with top2:
                render_favorite_toggle_button(cw, "exam")

            def next_exam(correct: bool = True) -> None:
                if correct:
                    st.session_state.exam_correct_count += 1
                else:
                    st.session_state.exam_wrong_count += 1
                    if cw not in st.session_state.exam_wrong_words:
                        st.session_state.exam_wrong_words.append(cw)

                st.session_state.exam_show_answer = False
                if st.session_state.exam_queue:
                    st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                    st.session_state.exam_current_number += 1
                    st.session_state.exam_display_side = get_display_side(st.session_state.exam_mode)
                else:
                    st.session_state.current_exam_word = None

            c2, c3 = st.columns(2)
            with c2:
                if st.button("맞음", disabled=not is_ans_shown, use_container_width=True, key="exam_correct_btn"): next_exam(True); st.rerun()
            with c3:
                if st.button("틀림", disabled=not is_ans_shown, use_container_width=True, key="exam_wrong_btn"): next_exam(False); st.rerun()

            st.info(f"진행: {st.session_state.exam_current_number}/{st.session_state.exam_total_count}  맞음 {st.session_state.exam_correct_count}  틀림 {st.session_state.exam_wrong_count}")

        q_text = cw["word"] if st.session_state.exam_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.exam_display_side == 0 else cw["word"]
        fav_badge = "<span class='fav-star'>★</span> " if is_favorite(cw) else ""

        card_html = f"<div class='study-card qa-compact'><div class='test-question'>{fav_badge}{q_text}</div>"
        if is_ans_shown:
            card_html += f"<div class='test-answer'>정답: {a_text}</div>"
            if has_hint:
                card_html += f"<div class='hint-box'><b>힌트</b><br>{cw['hint'].replace(chr(10), '<br>')}</div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        total = max(1, st.session_state.exam_total_count)
        st.progress(min(1.0, (st.session_state.exam_current_number - 1) / total))
    else:
        total = max(1, st.session_state.exam_total_count)
        accuracy = round(st.session_state.exam_correct_count / total * 100, 1)

        if accuracy >= 90:
            grade_icon, grade_text = "🏆", "최고 등급! 완벽에 가까운 실력입니다."
        elif accuracy >= 70:
            grade_icon, grade_text = "🎉", "훌륭해요! 조금만 더 다지면 완벽해질 거예요."
        elif accuracy >= 50:
            grade_icon, grade_text = "💪", "절반 이상 맞혔어요. 오답만 다시 훈련해보세요."
        else:
            grade_icon, grade_text = "📖", "복습이 더 필요해요. 오답 노트로 다시 도전해보세요."

        st.success(f"{grade_icon} 시험 종료. 최종 성적: {st.session_state.exam_correct_count} / {st.session_state.exam_total_count} (정답률 {accuracy}%)")
        st.caption(grade_text)

        wrong_words = st.session_state.exam_wrong_words
        if wrong_words:
            st.markdown(f"**오답 목록 ({len(wrong_words)}개)**")
            st.table([{"단어": w["word"], "뜻": w["meaning"]} for w in wrong_words])

            if st.button("오답만 다시 시험보기", use_container_width=True, key="exam_retry_wrong"):
                if load_words_from_list(wrong_words):
                    st.session_state.exam_mode = "random"
                    st.session_state.exam_current_number = 0
                    st.session_state.exam_correct_count = 0
                    st.session_state.exam_wrong_count = 0
                    st.session_state.exam_show_answer = False
                    st.session_state.exam_wrong_words = []
                    exam_words = list(st.session_state.words)
                    st.session_state.exam_total_count = len(exam_words)
                    st.session_state.exam_queue = exam_words
                    if st.session_state.exam_queue:
                        st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                        st.session_state.exam_current_number += 1
                        st.session_state.exam_display_side = get_display_side("random")
                    st.rerun()

    render_exit_button("시험 종료하기")


# ---------------------------
# 9. UI - 단어장 추가 파트 (Gemini 변환 기능 포함)
# ---------------------------
def render_gemini_conversion_section() -> None:
    """단어 목록을 입력하면 Gemini로 변환해서, 아래 '직접 입력해서 저장' 칸에 바로 채워주는 섹션."""
    with st.expander("Gemini로 단어 변환해서 채우기", expanded=False):
        st.caption("한자, 한국어, 히라가나/카타카나 단어를 한 줄에 하나씩 입력하면 Gemini가 뜻·한자 풀이를 붙여서 변환해줍니다.")

        st.session_state.gemini_raw_input = st.text_area(
            "변환할 단어 목록 (한 줄에 하나씩)",
            value=st.session_state.gemini_raw_input,
            height=140,
            placeholder="예:\n自動車\n開発\nサーバー",
            key="gemini_raw_input_area"
        )

        gc1, gc2 = st.columns([2, 1])
        with gc1:
            convert_clicked = st.button("Gemini로 변환하기", use_container_width=True, key="gemini_convert_btn")
        with gc2:
            clear_clicked = st.button("입력 지우기", use_container_width=True, key="gemini_clear_btn")

        if clear_clicked:
            st.session_state.gemini_raw_input = ""
            st.session_state.gemini_converted_result = ""
            st.rerun()

        if convert_clicked:
            with st.spinner("Gemini가 단어를 변환하고 있습니다..."):
                result_text, error_msg = convert_words_with_gemini(st.session_state.gemini_raw_input)
            if error_msg:
                st.error(error_msg)
            else:
                st.session_state.gemini_converted_result = result_text
                push_toast("Gemini 변환이 완료되었습니다.", icon="✨")
                st.rerun()

        if st.session_state.gemini_converted_result:
            st.markdown("**Gemini 변환 결과 (원본)**")
            st.markdown(
                f"<div class='gemini-result-box'>{st.session_state.gemini_converted_result}</div>",
                unsafe_allow_html=True
            )

            if st.button("이 결과를 아래 '직접 입력해서 저장' 칸에 채우기", use_container_width=True, key="gemini_fill_btn"):
                converted = convert_gemini_output_to_word_format(st.session_state.gemini_converted_result)
                if converted:
                    existing = st.session_state.manual_wordbook_text_area.strip()
                    st.session_state.manual_wordbook_text_area = (
                        f"{existing}\n\n{converted}".strip() if existing else converted
                    )
                    push_toast("변환된 단어를 입력칸에 채웠습니다. 내용을 확인한 뒤 저장해주세요.", icon="📋")
                    st.rerun()
                else:
                    st.warning("변환 결과에서 단어를 추출하지 못했습니다. 형식을 확인해주세요.")


def render_wordbook_part() -> None:
    st.header("단어장 관리 (GitHub 연동)")
    st.caption("새로운 단어장 파일(.txt)을 GitHub 저장소에 업로드합니다.")

    _, top_right = st.columns([5, 1])
    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
            push_toast("파일 목록을 새로고침했습니다.", icon="🔄")
            st.rerun()

    categories, cat_error = get_dynamic_categories()
    if cat_error:
        st.error(cat_error)
        return
    if not categories:
        st.error("저장할 폴더 트리를 불러오지 못했습니다.")
        return

    c1, c2 = st.columns(2)
    with c1:
        main_cat = st.selectbox("1. 대분류 선택", categories, key="wb_main_cat")
    with c2:
        sub_folders = get_subfolders(main_cat)
        sub_cat = st.selectbox("2. 하위 폴더 선택", sub_folders, key="wb_sub_cat") if sub_folders else None

    target_folder = f"word_list/{main_cat}/{sub_cat}" if sub_cat else f"word_list/{main_cat}"

    st.caption(f"현재 폴더: {target_folder}")
    with st.expander("현재 폴더에 있는 파일 목록 보기"):
        existing = get_txt_files(target_folder)
        if existing:
            for f in existing:
                st.write(f"- {f}")
        else:
            st.info("비어 있습니다.")

    correct_pw = str(st.secrets.get("upload_password", "")).strip()

    st.write("---")
    tab1, tab2 = st.tabs(["직접 입력해서 저장", "txt 파일 업로드"])

    with tab1:
        render_gemini_conversion_section()

        st.write("---")

        with st.form("manual_wordbook_form"):
            manual_title = st.text_input("파일 제목", value=get_default_title_prefix(), placeholder="예: 2026-07-20_N2")
            manual_text = st.text_area(
                "단어 : 뜻, 다음 줄에 힌트 (또는 단어 / 뜻 / 힌트를 각 줄에)",
                value=st.session_state.manual_wordbook_text_area,
                height=280,
                key="manual_wordbook_text_area"
            )
            manual_pw = st.text_input("업로드 비밀번호", type="password")
            submitted = st.form_submit_button("저장", use_container_width=True)

        if submitted:
            parsed, errors = parse_words_with_validation(manual_text)
            if not hmac.compare_digest(manual_pw, correct_pw):
                st.error("비밀번호가 올바르지 않습니다.")
            elif errors:
                st.error("아래 형식 오류를 수정한 뒤 다시 저장해주세요.")
                for e in errors:
                    st.write(f"- {e}")
            elif not parsed:
                st.warning("저장할 단어가 없습니다.")
            else:
                safe_name = make_safe_filename(manual_title)
                resp, path = upload_text_to_github(target_folder, safe_name, manual_text)
                if resp.status_code in (200, 201):
                    clear_github_cache()
                    st.session_state.gemini_converted_result = ""
                    st.session_state.manual_wordbook_text_area = ""
                    push_toast(f"업로드 완료: {safe_name} ({len(parsed)}개 단어)", icon="✅")
                    st.success(f"업로드 완료: {path} ({len(parsed)}개 단어)")
                    st.rerun()
                else:
                    st.error(f"업로드 실패 (status {resp.status_code}): {resp.text[:200]}")

    with tab2:
        uploaded_file = st.file_uploader("txt 파일 선택", type=["txt"])
        if uploaded_file:
            up_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            with st.form("upload_txt_form"):
                up_title = st.text_input("파일명", value=uploaded_file.name)
                up_pw = st.text_input("비밀번호", type="password")
                up_submitted = st.form_submit_button("저장", use_container_width=True)

            if up_submitted:
                parsed, errors = parse_words_with_validation(up_text)
                if not hmac.compare_digest(up_pw, correct_pw):
                    st.error("비밀번호가 올바르지 않습니다.")
                elif errors:
                    st.error("아래 형식 오류가 있어 업로드를 중단했습니다.")
                    for e in errors:
                        st.write(f"- {e}")
                elif not parsed:
                    st.warning("저장할 단어가 없습니다.")
                else:
                    safe_name = make_safe_filename(up_title)
                    resp, path = upload_text_to_github(target_folder, safe_name, up_text)
                    if resp.status_code in (200, 201):
                        clear_github_cache()
                        push_toast(f"업로드 완료: {safe_name} ({len(parsed)}개 단어)", icon="✅")
                        st.success(f"업로드 완료: {path} ({len(parsed)}개 단어)")
                        st.rerun()
                    else:
                        st.error(f"업로드 실패 (status {resp.status_code}): {resp.text[:200]}")


# ---------------------------
# 10. 지문 한 줄 외우기 파트
# ---------------------------
def render_script_setup() -> None:
    st.header("지문 한 줄 외우기")
    st.caption("대화 및 지문을 순서대로 연상하며 외웁니다. 단축키: 스페이스바 = 다음 문장")
    selected_files = render_sidebar()

    if st.button("대본 학습 시작", use_container_width=True):
        if load_data(selected_files, is_script=True):
            st.session_state.is_scripting = True
            st.session_state.active_part = "script"
            st.session_state.script_index = 0
            st.rerun()


def render_script_active() -> None:
    if st.session_state.script_index < len(st.session_state.script_lines):
        line_text = st.session_state.script_lines[st.session_state.script_index]

        with sticky_action_bar("script_sticky_bar"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("이전 문장", disabled=(st.session_state.script_index == 0), use_container_width=True, key="script_prev_btn"):
                    st.session_state.script_index -= 1
                    st.rerun()
            with c2:
                if st.button("다음 문장", use_container_width=True, key="script_next_btn"):
                    st.session_state.script_index += 1
                    st.rerun()

        st.markdown(f"""
            <div class="study-card qa-compact">
                <div class="script-text">{line_text}</div>
            </div>
        """, unsafe_allow_html=True)

        progress = st.session_state.script_index / max(1, len(st.session_state.script_lines))
        st.progress(min(1.0, progress))
        st.markdown(
            f"<div class='progress-caption'>진행 상황: {st.session_state.script_index + 1} / {len(st.session_state.script_lines)}</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("모든 대본/지문 학습을 완료했습니다.")
        if st.button("다시 처음부터", use_container_width=True):
            st.session_state.script_index = 0
            st.rerun()

    render_exit_button("지문 학습 종료하기")


# ---------------------------
# 11. 메인 실행
# ---------------------------
def render_full_header() -> None:
    st.markdown("""
        <div style="text-align:center; margin-bottom: 4px;">
            <span style="font-size: 1.6rem; font-weight: 800;">단어 암기 프로그램</span>
        </div>
        <div style="text-align:center; color:#8a8a92; font-size:0.85rem; margin-bottom:12px;">
            매일 조금씩, 확실하게 외우기
        </div>
    """, unsafe_allow_html=True)


def main() -> None:
    init_session_state()
    apply_global_style()

    if is_focus_active():
        active_part = st.session_state.active_part
        if active_part == "study":
            render_study_active()
        elif active_part == "practice":
            render_practice_active()
        elif active_part == "exam":
            render_exam_active()
        elif active_part == "script":
            render_script_active()
        else:
            exit_focus_mode()
            st.rerun()
    else:
        render_full_header()

        page = st.radio(
            "파트 이동",
            ["학습", "연습", "시험", "단어장 추가", "지문 외우기"],
            horizontal=True,
            label_visibility="collapsed",
            key="current_page_select"
        )

        if page == "학습":
            render_study_setup()
        elif page == "연습":
            render_practice_setup()
        elif page == "시험":
            render_exam_setup()
        elif page == "단어장 추가":
            render_wordbook_part()
        elif page == "지문 외우기":
            render_script_setup()

    inject_keyboard_shortcuts()
    inject_session_keepalive()
    flush_toasts()


if __name__ == "__main__":
    main()