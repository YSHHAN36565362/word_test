import streamlit as st
import streamlit.components.v1 as components
import random
import requests
import base64
import re
import calendar
import hmac
from datetime import datetime, date
from urllib.parse import quote
from zoneinfo import ZoneInfo

# ---------------------------
# 기본 페이지 설정
# ---------------------------
st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon="",
    layout="centered"
)

KOREA_TZ = ZoneInfo("Asia/Seoul")


# ---------------------------
# 1. Session State 초기화
# ---------------------------
def init_session_state() -> None:
    """앱 전역에서 사용하는 세션 상태 기본값을 등록한다."""
    defaults = {
        "words": [],

        "study_index": 0,
        "is_studying": False,
        "study_show_hint": False,

        "practice_queue": [],
        "current_practice_word": None,
        "is_practicing": False,
        "practice_display_side": 0,
        "practice_mode": "random",
        "practice_show_answer": False,
        "practice_show_hint": False,

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

        "font_scale": 1.0,
        "theme_mode": "다크 모드",

        "script_lines": [],
        "script_index": 0,
        "is_scripting": False,

        # --- 전역 사이드바(파일/날짜 선택) 상태 ---
        # 파트(학습/연습/시험/...)를 넘나들어도 동일한 key를 쓰기 때문에
        # 어떤 화면으로 이동하든 선택 내용이 그대로 유지된다.
        "sidebar_main_cat": None,
        "sidebar_sub_cats": [],
        "sidebar_today_filter": False,
        "sidebar_file_select": [],
        "sidebar_cal_y": date.today().year,
        "sidebar_cal_m": date.today().month,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------
# 2. 글로벌 CSS 스타일 및 키보드 단축키 스크립트
# ---------------------------
def apply_global_style() -> None:
    """테마/글자크기 설정에 맞춰 전역 CSS(모바일 대응 포함)를 적용한다."""
    scale = st.session_state.font_scale
    base = int(16 * scale)
    large = int(24 * scale)
    huge = int(40 * scale)

    is_dark = (st.session_state.theme_mode == "다크 모드")

    card_bg = "#262730" if is_dark else "#ffffff"
    border_color = "#3a3b45" if is_dark else "#e5e7eb"
    text_color = "#f0f0f0" if is_dark else "#1a1a1a"
    word_color = "#5ac8ff" if is_dark else "#1f77b4"
    hint_bg = "#33343c" if is_dark else "#f1f3f5"
    hint_text = "#e8e8e8" if is_dark else "#333333"
    ans_color = "#4ade80" if is_dark else "#2ca02c"
    shadow_color = "rgba(0,0,0,0.35)" if is_dark else "rgba(0,0,0,0.08)"
    muted_color = "#9a9aa2" if is_dark else "#6b7280"

    st.markdown(f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{ font-size: {base}px !important; }}

        .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 760px; }}

        /* ---------- 카드형 컴포넌트 ---------- */
        .study-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 14px;
            padding: 28px 20px;
            margin: 18px 0;
            box-shadow: 0 2px 10px {shadow_color};
        }}
        .word-text {{ font-size: {large}px !important; font-weight: 700; color: {word_color}; margin-bottom: 8px; text-align: center; }}
        .meaning-text {{ font-size: {large}px !important; color: {text_color}; margin-bottom: 4px; text-align: center; }}
        .hint-box {{
            font-size: {base}px !important; color: {hint_text}; background-color: {hint_bg};
            padding: 12px 14px; border-radius: 10px; margin-top: 12px; line-height: 1.6;
        }}
        .hint-box b {{ color: {muted_color}; }}
        .script-text {{ font-size: {large}px !important; font-weight: 700; color: {word_color}; text-align: left; line-height: 1.9; }}

        .test-question {{ font-size: {huge}px !important; color: {text_color}; text-align: center; padding: 26px 10px 10px 10px; font-weight: 800; }}
        .test-answer {{ font-size: {large}px !important; text-align: center; color: {ans_color}; font-weight: 700; margin: 4px 0 20px 0; }}

        .progress-caption {{ text-align: center; color: {muted_color}; margin-top: 6px; }}

        div[data-testid="stButton"] > button {{
            font-size: {base}px !important; font-weight: 600 !important; border-radius: 10px !important;
        }}

        /* 캘린더 등 날짜 그리드가 촘촘하게 붙도록 */
        div[data-testid="stCheckbox"] {{ display: flex; justify-content: center; }}

        /* ---------- 모바일 대응 ---------- */
        @media (max-width: 640px) {{
            .block-container {{ padding-left: 0.7rem !important; padding-right: 0.7rem !important; padding-top: 1.2rem; }}

            /* 여러 컬럼이 세로로 쌓이지 않고 한 줄을 유지하도록 강제 */
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: nowrap !important;
                gap: 4px !important;
            }}
            div[data-testid="column"] {{
                min-width: 0 !important;
                width: auto !important;
                padding: 0 2px !important;
            }}

            div[data-testid="stButton"] > button {{
                padding: 0.35rem 0.3rem !important;
                font-size: {max(11, int(base * 0.75))}px !important;
                white-space: nowrap;
            }}
            div[data-testid="stCheckbox"] label p {{
                font-size: {max(10, int(base * 0.7))}px !important;
            }}
            .test-question {{ font-size: {int(huge * 0.6)}px !important; padding: 16px 4px !important; }}
            .word-text, .meaning-text {{ font-size: {int(large * 0.8)}px !important; }}
            .study-card {{ padding: 18px 12px; }}
        }}
        </style>
    """, unsafe_allow_html=True)


def inject_keyboard_shortcuts() -> None:
    """스페이스바/H/Z/X/C/V 단축키를 입력창 밖에서만 동작하도록 주입한다."""
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
                else if (key === 'z') { clickBtn(['완벽함', 'O (맞음)']); }
                else if (key === 'x') { clickBtn(['조금 앎', 'X (틀림)']); }
                else if (key === 'c') { clickBtn(['헷갈림']); }
                else if (key === 'v') { clickBtn(['모름']); }
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
    """HTTP 상태 코드를 사람이 이해할 수 있는 에러 메시지로 변환한다."""
    messages = {
        401: "GitHub 인증에 실패했습니다. `github_token` 설정을 확인해주세요.",
        403: "GitHub API 요청 한도를 초과했거나 접근 권한이 없습니다. 잠시 후 다시 시도해주세요.",
        404: "요청한 경로를 GitHub 저장소에서 찾을 수 없습니다.",
    }
    return messages.get(status, f"GitHub API 오류가 발생했습니다 (status: {status}).")


@st.cache_data(ttl=60, show_spinner=False)
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
# 4. 단어 파싱 / 지문 파싱 유틸
# ---------------------------
def parse_word_text(text: str) -> list:
    """'단어 : 뜻 \\n 힌트' 또는 '단어 \\n 뜻 \\n 힌트' 두 형식을 모두 지원해 파싱한다."""
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
    """단어장 업로드 전 형식을 검증하고 (파싱결과, 오류메시지목록)을 반환한다."""
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
    """선택된 파일들을 모두 읽어 (단어,뜻,힌트) 기준으로 전역 중복 제거한 단어 목록을 반환한다.

    '시험 파트에서 보여주는 최대 문항 수'와 '실제 출제되는 고유 단어 수'가
    어긋나지 않도록, 개수 계산과 실제 큐 생성에 반드시 이 함수 하나만 사용한다.
    """
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


def get_display_side(mode: str) -> int:
    """연습/시험 모드에 따라 문제로 무엇을 보여줄지(0=단어, 1=뜻) 결정한다."""
    if mode == "random":
        return random.choice([0, 1])
    return 0 if mode == "meaning_only" else 1


def requeue_position(queue_len: int, level: int) -> int:
    """망각 곡선 알고리즘: 점수(level)에 따라 큐 재삽입 위치를 계산한다."""
    if queue_len <= 1:
        return 0
    ranges = {60: (0.5, 0.8), 40: (0.2, 0.4), 0: (0.05, 0.15)}
    lo, hi = ranges[level]
    lo_idx = max(0, int(queue_len * lo))
    hi_idx = max(lo_idx, int(queue_len * hi))
    return random.randint(lo_idx, hi_idx)


# ---------------------------
# 5. UI - 사이드바 (전역 상태, 캘린더 연동, 파일 선택)
# ---------------------------
def render_sidebar() -> list:
    """모든 파트가 공유하는 전역 사이드바. 파트를 이동해도 선택 상태가 유지된다."""
    with st.sidebar:
        with st.expander("⚙️ 화면 설정", expanded=False):
            new_theme = st.selectbox(
                "테마 선택", ["기본 모드", "다크 모드"],
                index=1 if st.session_state.theme_mode == "다크 모드" else 0,
                key="global_theme_select"
            )
            if new_theme != st.session_state.theme_mode:
                st.session_state.theme_mode = new_theme
                st.rerun()

            col1, col2, col3 = st.columns(3)
            if col1.button("A+", use_container_width=True):
                change_font_scale(0.1); st.rerun()
            if col2.button("A-", use_container_width=True):
                change_font_scale(-0.1); st.rerun()
            if col3.button("초기화", use_container_width=True):
                st.session_state.font_scale = 1.0; st.rerun()

        st.write("---")
        st.subheader("📁 학습 자료 선택")

        categories, cat_error = get_dynamic_categories()
        if cat_error:
            st.error(cat_error)
            return []
        if not categories:
            st.error("word_list 폴더를 찾을 수 없습니다.")
            return []

        # 대분류가 바뀌면 이전 값이 남아 있던 selectbox가 없는 경우를 대비
        if st.session_state.sidebar_main_cat not in categories:
            st.session_state.sidebar_main_cat = categories[0]

        main_cat = st.selectbox("1. 대분류 선택", categories, key="sidebar_main_cat")
        sub_folders = get_subfolders(main_cat)

        # ⚠️ 위젯을 만들기 전에, 더 이상 유효하지 않은 값은 미리 정리한다.
        #    (Streamlit은 위젯 생성 시점에 session_state 값이 옵션 목록에 없으면 오류를 낸다)
        if sub_folders:
            st.session_state.sidebar_sub_cats = [
                s for s in st.session_state.sidebar_sub_cats if s in sub_folders
            ] or sub_folders
            selected_subs = st.multiselect("2. 하위 폴더 선택", sub_folders, key="sidebar_sub_cats")
        else:
            selected_subs = []

        all_files = []
        if sub_folders:
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                for f in get_txt_files(path):
                    all_files.append({"path": f"{path}/{f}", "label": f"[{sub}] {f}"})
        else:
            path = f"word_list/{main_cat}"
            for f in get_txt_files(path):
                all_files.append({"path": f"{path}/{f}", "label": f})

        available_dates = {}
        for f in all_files:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", f["label"])
            if match:
                try:
                    dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                    available_dates.setdefault(dt, []).append(f)
                except ValueError:
                    pass

        today_str = datetime.now(KOREA_TZ).strftime("%Y-%m-%d")
        st.checkbox(f"📅 오늘 날짜만 선택 ({today_str})", key="sidebar_today_filter")

        with st.expander("🗓️ 달력에서 날짜로 찾기", expanded=False):
            today_date = datetime.now(KOREA_TZ).date()

            if st.button("오늘로 이동", use_container_width=True):
                st.session_state.sidebar_cal_y = today_date.year
                st.session_state.sidebar_cal_m = today_date.month
                st.rerun()

            c_y, c_m = st.columns(2)
            with c_y:
                st.selectbox("연도", range(2023, 2031), key="sidebar_cal_y")
            with c_m:
                st.selectbox("월", range(1, 13), key="sidebar_cal_m")

            y = st.session_state.sidebar_cal_y
            m = st.session_state.sidebar_cal_m

            cal = calendar.monthcalendar(y, m)
            weekdays = ["월", "화", "수", "목", "금", "토", "일"]

            w_cols = st.columns(7)
            for i, wd in enumerate(weekdays):
                w_cols[i].markdown(f"<div style='text-align:center;font-weight:600;'>{wd}</div>", unsafe_allow_html=True)

            for week in cal:
                d_cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        d_cols[i].write("")
                    else:
                        dt = date(y, m, day)
                        if dt in available_dates:
                            chk_key = f"cal_chk_{dt}"
                            d_cols[i].checkbox(str(day), key=chk_key, label_visibility="visible")
                        else:
                            d_cols[i].markdown(
                                f"<div style='text-align:center;color:gray;'>{day}</div>",
                                unsafe_allow_html=True
                            )

            if st.button("달력 선택 모두 해제", use_container_width=True):
                for k in [k for k in st.session_state if k.startswith("cal_chk_")]:
                    st.session_state[k] = False
                st.rerun()

        selected_cal_files = []
        for dt, files in available_dates.items():
            if st.session_state.get(f"cal_chk_{dt}", False):
                selected_cal_files.extend(files)

        if st.session_state.sidebar_today_filter or selected_cal_files:
            filtered = []
            if st.session_state.sidebar_today_filter:
                for f in all_files:
                    raw_filename = f["label"].split("] ")[-1] if "] " in f["label"] else f["label"]
                    if raw_filename.startswith(today_str) and f not in filtered:
                        filtered.append(f)
            for f in selected_cal_files:
                if f not in filtered:
                    filtered.append(f)
            all_files = filtered

        if not all_files:
            st.warning("조건에 맞는 파일이 없습니다.")
            return []

        file_labels = [f["label"] for f in all_files]
        # 옵션 목록이 바뀌었을 수 있으니 위젯 생성 전에 유효하지 않은 선택값을 정리
        st.session_state.sidebar_file_select = [
            lbl for lbl in st.session_state.sidebar_file_select if lbl in file_labels
        ] or file_labels

        selected_labels = st.multiselect("3. 최종 파일 확인 및 선택", file_labels, key="sidebar_file_select")

        return [f for f in all_files if f["label"] in selected_labels]


def load_data(selected_files: list, is_script: bool = False) -> bool:
    if not selected_files:
        st.warning("사이드바에서 파일을 선택해주세요.")
        return False

    if is_script:
        merged = []
        for f in selected_files:
            text = get_file_content(f["path"])
            merged.extend(parse_script_text(text))
        st.session_state.script_lines = merged
    else:
        pool = build_word_pool(selected_files)
        random.shuffle(pool)
        st.session_state.words = pool

    return True


# ---------------------------
# 6. UI - 학습 파트
# ---------------------------
def render_study_part() -> None:
    st.header("📖 학습 파트")
    st.caption("💡 단축키: [스페이스바] 다음 단어 · [H] 힌트 보기")
    selected_files = render_sidebar()

    if st.button("🚀 선택한 파일로 학습 시작", use_container_width=True):
        if load_data(selected_files):
            st.session_state.is_studying = True
            st.session_state.study_index = 0
            st.session_state.study_show_hint = False
            st.rerun()

    if st.session_state.is_studying:
        if st.session_state.study_index < len(st.session_state.words):
            word_data = st.session_state.words[st.session_state.study_index]
            has_hint = bool(word_data["hint"].strip())

            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("다음 단어", use_container_width=True):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False
                    st.rerun()
            with c2:
                if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                    st.session_state.study_show_hint = True
                    st.rerun()

            st.markdown(f"""
                <div class="study-card">
                    <div class="word-text">{word_data['word']}</div>
                    <div class="meaning-text">{word_data['meaning']}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.study_show_hint and has_hint:
                st.markdown(
                    f"<div class='hint-box'><b>힌트</b><br>{word_data['hint'].replace(chr(10), '<br>')}</div>",
                    unsafe_allow_html=True
                )

            st.markdown(
                f"<div class='progress-caption'>진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}</div>",
                unsafe_allow_html=True
            )
        else:
            st.success("모든 단어 학습을 완료했습니다!")


# ---------------------------
# 7. UI - 연습 파트
# ---------------------------
def render_practice_part() -> None:
    st.header("📝 연습 파트 (망각 곡선 적용)")
    st.caption("단축키: [스페이스바] 정답 · [H] 힌트 · [Z]100 [X]60 [C]40 [V]0")
    selected_files = render_sidebar()

    def start_practice(next_word):
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0) if st.session_state.practice_queue else None
        st.session_state.practice_display_side = get_display_side(st.session_state.practice_mode)

    c1, c2, c3 = st.columns(3)
    mode = None
    if c1.button("이름만 연습", use_container_width=True): mode = "word_only"
    if c2.button("뜻만 연습", use_container_width=True): mode = "meaning_only"
    if c3.button("랜덤 연습", use_container_width=True): mode = "random"

    if mode and load_data(selected_files):
        st.session_state.practice_queue = list(st.session_state.words)
        st.session_state.is_practicing = True
        st.session_state.practice_mode = mode
        st.session_state.practice_show_answer = False
        st.session_state.practice_show_hint = False

        if st.session_state.practice_queue:
            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
            st.session_state.practice_display_side = get_display_side(mode)
        st.rerun()

    if st.session_state.is_practicing and st.session_state.current_practice_word:
        cw = st.session_state.current_practice_word
        has_hint = bool(cw["hint"].strip())
        is_ans_shown = st.session_state.practice_show_answer

        st.write("---")
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("정답 확인", use_container_width=True):
                st.session_state.practice_show_answer = True; st.rerun()
        with btn2:
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                st.session_state.practice_show_hint = True; st.rerun()

        def apply_score(level: int) -> None:
            if level != 100:
                pos = requeue_position(len(st.session_state.practice_queue), level)
                st.session_state.practice_queue.insert(pos, cw)

            st.session_state.practice_show_answer = False
            st.session_state.practice_show_hint = False
            if st.session_state.practice_queue:
                st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                st.session_state.practice_display_side = get_display_side(st.session_state.practice_mode)
            else:
                st.session_state.current_practice_word = None

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            if st.button("완벽함 (100)", disabled=not is_ans_shown, use_container_width=True): apply_score(100); st.rerun()
        with s2:
            if st.button("조금 앎 (60)", disabled=not is_ans_shown, use_container_width=True): apply_score(60); st.rerun()
        with s3:
            if st.button("헷갈림 (40)", disabled=not is_ans_shown, use_container_width=True): apply_score(40); st.rerun()
        with s4:
            if st.button("모름 (0)", disabled=not is_ans_shown, use_container_width=True): apply_score(0); st.rerun()

        q_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]

        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        if st.session_state.practice_show_hint and has_hint:
            st.markdown(f"<div class='hint-box'><b>힌트</b><br>{cw['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

        st.markdown(
            f"<div class='progress-caption'>남은 큐: {len(st.session_state.practice_queue)}개</div>",
            unsafe_allow_html=True
        )

    elif st.session_state.is_practicing:
        st.success("완벽합니다! 대기열의 모든 연습을 완료했습니다.")


# ---------------------------
# 8. UI - 시험 파트
# ---------------------------
def render_exam_part() -> None:
    st.header("🎯 시험 파트")
    st.caption("단축키: [스페이스바] 정답 확인 · [Z] O 맞음 · [X] X 틀림")
    selected_files = render_sidebar()

    total_words = 0
    if selected_files:
        total_words = len(build_word_pool(selected_files))

    if total_words > 0:
        st.write("---")
        st.subheader("⚙️ 출제 개수 설정")

        current_val = min(st.session_state.exam_total_count_input, total_words)
        st.session_state.exam_total_count_input = current_val

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1], vertical_alignment="bottom")
        with col1:
            st.number_input(f"총 출제 개수 (최대 {total_words}개)", min_value=1, max_value=total_words, key="exam_total_count_input")
        with col2:
            if st.button("최대(MAX)", use_container_width=True):
                st.session_state.exam_total_count_input = total_words; st.rerun()
        with col3:
            if st.button("+5", use_container_width=True):
                st.session_state.exam_total_count_input = min(total_words, current_val + 5); st.rerun()
        with col4:
            if st.button("-5", use_container_width=True):
                st.session_state.exam_total_count_input = max(1, current_val - 5); st.rerun()

        st.write("---")

        m1, m2, m3 = st.columns(3)
        mode = None
        if m1.button("이름만 시험", use_container_width=True): mode = "word_only"
        if m2.button("뜻만 시험", use_container_width=True): mode = "meaning_only"
        if m3.button("랜덤 시험", use_container_width=True): mode = "random"

        if mode and load_data(selected_files):
            st.session_state.is_examining = True
            st.session_state.exam_mode = mode
            st.session_state.exam_current_number = 0
            st.session_state.exam_correct_count = 0
            st.session_state.exam_wrong_count = 0
            st.session_state.exam_show_answer = False

            exam_words = list(st.session_state.words)
            actual_count = min(st.session_state.exam_total_count_input, len(exam_words))
            st.session_state.exam_total_count = actual_count
            st.session_state.exam_queue = exam_words[:actual_count]

            if st.session_state.exam_queue:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                st.session_state.exam_display_side = get_display_side(mode)
            st.rerun()

    if st.session_state.is_examining and st.session_state.current_exam_word:
        cw = st.session_state.current_exam_word
        is_ans_shown = st.session_state.exam_show_answer

        st.write("---")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2.5])
        with c1:
            if st.button("정답 확인", use_container_width=True):
                st.session_state.exam_show_answer = True; st.rerun()

        def next_exam(correct: bool = True) -> None:
            if correct:
                st.session_state.exam_correct_count += 1
            else:
                st.session_state.exam_wrong_count += 1

            st.session_state.exam_show_answer = False
            if st.session_state.exam_queue:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                st.session_state.exam_display_side = get_display_side(st.session_state.exam_mode)
            else:
                st.session_state.current_exam_word = None

        with c2:
            if st.button("O (맞음)", disabled=not is_ans_shown, use_container_width=True): next_exam(True); st.rerun()
        with c3:
            if st.button("X (틀림)", disabled=not is_ans_shown, use_container_width=True): next_exam(False); st.rerun()
        with c4:
            st.info(f"진행: {st.session_state.exam_current_number}/{st.session_state.exam_total_count} · 맞음 {st.session_state.exam_correct_count} · 틀림 {st.session_state.exam_wrong_count}")

        q_text = cw["word"] if st.session_state.exam_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.exam_display_side == 0 else cw["word"]

        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_examining:
        st.success(f"시험 종료! 최종 성적: {st.session_state.exam_correct_count} / {st.session_state.exam_total_count}")


# ---------------------------
# 9. UI - 단어장 추가 파트
# ---------------------------
def render_wordbook_part() -> None:
    st.header("📁 단어장 관리 (GitHub 연동)")
    st.caption("새로운 단어장 파일(.txt)을 GitHub 저장소에 업로드합니다.")

    _, top_right = st.columns([5, 1])
    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
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

    st.caption(f"현재 폴더: `{target_folder}`")
    with st.expander("현재 폴더에 있는 파일 목록 보기"):
        existing = get_txt_files(target_folder)
        if existing:
            for f in existing:
                st.write(f"- {f}")
        else:
            st.info("비어 있습니다.")

    correct_pw = str(st.secrets.get("upload_password", "")).strip()

    st.write("---")
    tab1, tab2 = st.tabs(["✍️ 직접 입력해서 저장", "📄 txt 파일 업로드"])

    with tab1:
        with st.form("manual_wordbook_form"):
            manual_title = st.text_input("파일 제목", value=get_default_title_prefix(), placeholder="예: 2026-07-20_N2")
            manual_text = st.text_area("단어 : 뜻 \\n 힌트  (또는 단어 \\n 뜻 \\n 힌트)", height=250)
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
                        st.success(f"업로드 완료: {path} ({len(parsed)}개 단어)")
                        st.rerun()
                    else:
                        st.error(f"업로드 실패 (status {resp.status_code}): {resp.text[:200]}")


# ---------------------------
# 10. UI - 지문 한 줄 외우기 파트
# ---------------------------
def render_script_part() -> None:
    st.header("🗣️ 지문 한 줄 외우기")
    st.caption("대화 및 지문을 순서대로 연상하며 외웁니다. (단축키: [스페이스바] 다음 문장)")
    selected_files = render_sidebar()

    if st.button("🚀 선택한 파일로 대본 학습 시작", use_container_width=True):
        if load_data(selected_files, is_script=True):
            st.session_state.is_scripting = True
            st.session_state.script_index = 0
            st.rerun()

    if st.session_state.is_scripting:
        if st.session_state.script_index < len(st.session_state.script_lines):
            line_text = st.session_state.script_lines[st.session_state.script_index]

            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⏪ 이전 문장", disabled=(st.session_state.script_index == 0), use_container_width=True):
                    st.session_state.script_index -= 1
                    st.rerun()
            with c2:
                if st.button("다음 문장 ⏭️", use_container_width=True):
                    st.session_state.script_index += 1
                    st.rerun()

            st.markdown(f"""
                <div class="study-card">
                    <div class="script-text">{line_text}</div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(
                f"<div class='progress-caption'>진행 상황: {st.session_state.script_index + 1} / {len(st.session_state.script_lines)}</div>",
                unsafe_allow_html=True
            )
        else:
            st.success("🎉 모든 대본/지문 학습을 완료했습니다!")
            if st.button("⏪ 다시 처음부터", use_container_width=True):
                st.session_state.script_index = 0
                st.rerun()


# ---------------------------
# 11. 메인 실행
# ---------------------------
def main() -> None:
    init_session_state()
    apply_global_style()

    st.title(" 단어 암기 프로그램")

    page = st.radio(
        "파트 이동",
        ["학습", "연습", "시험", "단어장 추가", "지문 외우기"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == "학습":
        render_study_part()
    elif page == "연습":
        render_practice_part()
    elif page == "시험":
        render_exam_part()
    elif page == "단어장 추가":
        render_wordbook_part()
    elif page == "지문 외우기":
        render_script_part()

    inject_keyboard_shortcuts()


if __name__ == "__main__":
    main()