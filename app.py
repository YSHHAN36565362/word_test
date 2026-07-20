import streamlit as st
import random
import requests
import base64
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo


# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon="📚",
    layout="centered"
)


# ---------------------------
# Session State
# ---------------------------
def init_session_state():
    """세션 동안 유지할 상태값들을 초기화합니다.

    Streamlit은 위젯을 누를 때마다 스크립트를 다시 실행하므로,
    학습 진행 상태를 유지하려면 st.session_state에 저장해야 합니다.
    이 상태는 같은 접속 세션 동안 유지되고, 새로고침/탭 종료 시 초기화됩니다.
    """
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
        "show_answer": False,
        "practice_show_hint": False,

        "exam_show_answer": False,
        "exam_queue": [],
        "exam_source_words": [],
        "current_exam_word": None,
        "is_examining": False,
        "exam_mode": None,
        "exam_total_count": 10,
        "exam_current_number": 0,
        "exam_correct_count": 0,
        "exam_wrong_count": 0,
        "exam_display_side": 0,
        "exam_total_count_input": 10,

        # 모바일 표시 크기 상태
        "mobile_font_scale": 1.0,   # 0.9 ~ 1.4
        "mobile_button_scale": 1.0, # 0.9 ~ 1.4
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------
# Mobile accessibility UI
# ---------------------------
def increase_mobile_scale():
    st.session_state.mobile_font_scale = min(1.4, round(st.session_state.mobile_font_scale + 0.1, 1))
    st.session_state.mobile_button_scale = min(1.4, round(st.session_state.mobile_button_scale + 0.1, 1))


def decrease_mobile_scale():
    st.session_state.mobile_font_scale = max(0.9, round(st.session_state.mobile_font_scale - 0.1, 1))
    st.session_state.mobile_button_scale = max(0.9, round(st.session_state.mobile_button_scale - 0.1, 1))


def reset_mobile_scale():
    st.session_state.mobile_font_scale = 1.0
    st.session_state.mobile_button_scale = 1.0


def render_mobile_toolbar():
    """상단 모바일 접근성 도구 막대.

    transform scale 대신 모바일에서만 폰트와 버튼 크기를 키우는 CSS를 사용합니다.
    이 방식이 레이아웃 깨짐이 적고 더 자연스럽습니다.
    """
    font_scale = st.session_state.mobile_font_scale
    button_scale = st.session_state.mobile_button_scale

    base_font = 16 * font_scale
    small_font = 14 * font_scale
    large_font = 24 * font_scale
    question_font = 40 * font_scale
    answer_font = 30 * font_scale
    exam_question_font = 42 * font_scale

    button_height = int(44 * button_scale)
    button_font = 16 * font_scale
    input_font = 16 * font_scale

    st.markdown(
        f"""
        <style>
        @media (max-width: 768px) {{
            .block-container {{
                padding-top: 0.8rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }}

            html, body, [data-testid="stAppViewContainer"] {{
                font-size: {base_font}px !important;
            }}

            p, li, label, div, span {{
                font-size: {base_font}px;
            }}

            .mobile-caption {{
                font-size: {small_font}px !important;
                color: #666;
                margin-bottom: 0.6rem;
            }}

            .study-word {{
                font-size: {large_font}px !important;
            }}

            .practice-question {{
                font-size: {question_font}px !important;
                text-align: center;
                padding: 20px;
            }}

            .practice-answer {{
                font-size: {answer_font}px !important;
                text-align: center;
                color: gray;
                padding: 10px;
            }}

            .exam-question {{
                font-size: {exam_question_font}px !important;
                text-align: center;
                padding: 28px;
            }}

            .exam-answer {{
                font-size: {answer_font}px !important;
                text-align: center;
                color: gray;
                padding: 12px;
            }}

            div[data-testid="stButton"] > button,
            .stFormSubmitButton > button {{
                min-height: {button_height}px !important;
                font-size: {button_font}px !important;
                font-weight: 600 !important;
                border-radius: 10px !important;
            }}

            .stFormSubmitButton > button p {{
                font-size: {button_font}px !important;
            }}

            div[data-baseweb="select"] * {{
                font-size: {input_font}px !important;
            }}

            input, textarea, [data-testid="stNumberInput"] input {{
                font-size: {input_font}px !important;
            }}

            [data-testid="stSidebar"] * {{
                font-size: {small_font}px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    top1, top2, top3, top4 = st.columns([1, 1, 1, 2])
    with top1:
        st.button("글자 크게", on_click=increase_mobile_scale, use_container_width=True)
    with top2:
        st.button("글자 작게", on_click=decrease_mobile_scale, use_container_width=True)
    with top3:
        st.button("기본 크기", on_click=reset_mobile_scale, use_container_width=True)
    with top4:
        st.caption(
            f"모바일 크기: 글자 {int(font_scale * 100)}% / 버튼 {int(button_scale * 100)}%"
        )

    st.markdown(
        "<div class='mobile-caption'>모바일에서 글씨나 버튼이 작게 보이면 위 버튼으로 조절하세요.</div>",
        unsafe_allow_html=True
    )


# ---------------------------
# Word parsing
# ---------------------------
def parse_word_text(text):
    """빈 줄 기준 블록 파싱.

    지원 형식 1)
    단어
    뜻
    힌트 1
    힌트 2

    지원 형식 2)
    단어: 뜻
    힌트 1
    힌트 2
    """
    normalized_text = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized_text.split("\n")

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
            word = parts[0].strip()
            meaning = parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""

            if word and meaning:
                parsed_words.append({
                    "word": word,
                    "meaning": meaning,
                    "hint": hint
                })
        else:
            if len(block) >= 2:
                word = block[0]
                meaning = block[1]
                hint = "\n".join(block[2:])

                if word and meaning:
                    parsed_words.append({
                        "word": word,
                        "meaning": meaning,
                        "hint": hint
                    })

    return parsed_words


def parse_words_with_validation(text):
    """단어장 업로드/저장 전 형식 검사용 파서입니다."""
    normalized_text = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized_text.split("\n")

    parsed_words = []
    errors = []
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
            word = parts[0].strip()
            meaning = parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""

            if not word and not meaning:
                errors.append(f"{block_start + 1}번 줄: 단어와 뜻이 모두 비어 있습니다.")
            elif not word:
                errors.append(f"{block_start + 1}번 줄: 단어가 비어 있습니다.")
            elif not meaning:
                errors.append(f"{block_start + 1}번 줄: 뜻이 비어 있습니다.")
            else:
                parsed_words.append({
                    "word": word,
                    "meaning": meaning,
                    "hint": hint
                })
        else:
            if len(block) == 1:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없는 단어입니다.")
            else:
                word = block[0]
                meaning = block[1]
                hint = "\n".join(block[2:])

                if not word:
                    errors.append(f"{block_start + 1}번 줄: 단어가 비어 있습니다.")
                elif not meaning:
                    errors.append(f"{block_start + 2}번 줄: 뜻이 비어 있습니다.")
                else:
                    parsed_words.append({
                        "word": word,
                        "meaning": meaning,
                        "hint": hint
                    })

    return parsed_words, errors


# ---------------------------
# Helpers
# ---------------------------
def make_safe_filename_part(name):
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_name = str(name).strip()

    for ch in invalid_chars:
        safe_name = safe_name.replace(ch, "_")

    safe_name = safe_name.replace("\n", " ").replace("\r", " ")
    safe_name = " ".join(safe_name.split())

    if not safe_name:
        safe_name = "untitled"

    return safe_name


def make_manual_filename_from_title(full_title):
    safe_title = make_safe_filename_part(full_title).strip()

    if not safe_title:
        safe_title = "untitled"

    if not safe_title.lower().endswith(".txt"):
        safe_title = f"{safe_title}.txt"

    return safe_title


def get_default_manual_title_prefix():
    korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
    return korea_now.strftime("%Y.%m.%d_%H.%M_")


# ---------------------------
# GitHub API
# ---------------------------
def get_github_headers():
    token = str(st.secrets["github_token"]).strip()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }


def get_repo_info():
    owner = str(st.secrets["github_owner"]).strip()
    repo = str(st.secrets["github_repo"]).strip()
    branch = str(st.secrets["github_branch"]).strip()
    return owner, repo, branch


def encode_github_path(path):
    return quote(str(path).strip(), safe="/")


@st.cache_data(ttl=120, max_entries=256, show_spinner=False)
def github_get_contents_cached(path):
    """GitHub contents API 응답 캐시.

    반복적인 폴더/파일 조회를 줄여서 여러 사용자가 접속해도
    불필요한 API 호출이 많아지지 않도록 합니다.
    """
    owner, repo, branch = get_repo_info()
    encoded_path = encode_github_path(path)
    encoded_branch = quote(branch, safe="")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded_path}?ref={encoded_branch}"
    response = requests.get(url, headers=get_github_headers(), timeout=30)
    return response.status_code, response.json() if response.content else {}


@st.cache_data(ttl=120, max_entries=64, show_spinner=False)
def get_github_all_folders_recursive(base_path="word_list"):
    collected = []

    def walk_folder(path):
        status_code, data = github_get_contents_cached(path)

        if status_code != 200:
            raise Exception(f"{path} 조회 실패 (상태 코드: {status_code})")

        if not isinstance(data, list):
            return

        for item in data:
            if item.get("type") == "dir":
                folder_path = item.get("path")
                collected.append(folder_path)
                walk_folder(folder_path)

    walk_folder(base_path)
    collected.sort()
    return collected


@st.cache_data(ttl=120, max_entries=64, show_spinner=False)
def get_github_folders(base_path="word_list"):
    try:
        folders = get_github_all_folders_recursive(base_path)
        return folders, None
    except Exception as e:
        return [], f"GitHub 폴더 목록 조회 중 오류가 발생했습니다: {e}"


@st.cache_data(ttl=120, max_entries=256, show_spinner=False)
def get_github_txt_files(folder_path):
    try:
        status_code, data = github_get_contents_cached(folder_path)

        if status_code != 200:
            return [], f"선택한 폴더의 파일 목록을 불러오지 못했습니다. 상태 코드: {status_code}"

        txt_files = []
        if isinstance(data, list):
            for item in data:
                if item.get("type") == "file" and item.get("name", "").lower().endswith(".txt"):
                    txt_files.append(item.get("name"))

        txt_files.sort()
        return txt_files, None

    except Exception as e:
        return [], f"파일 목록 조회 중 오류가 발생했습니다: {e}"


@st.cache_data(ttl=120, max_entries=512, show_spinner=False)
def get_github_file_text(repo_file_path):
    status_code, data = github_get_contents_cached(repo_file_path)

    if status_code != 200:
        raise Exception(f"GitHub 파일을 불러오지 못했습니다. 상태 코드: {status_code}")

    content_b64 = data.get("content", "").replace("\n", "")
    if not content_b64:
        raise Exception("GitHub 파일 내용이 비어 있습니다.")

    return base64.b64decode(content_b64).decode("utf-8")


def clear_github_cache():
    st.cache_data.clear()


def upload_text_to_github(folder_path, file_name, text_content):
    owner, repo, branch = get_repo_info()
    repo_path = f"{str(folder_path).strip()}/{str(file_name).strip()}"
    encoded_path = encode_github_path(repo_path)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded_path}"

    content_b64 = base64.b64encode(text_content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"Add word list: {repo_path}",
        "content": content_b64,
        "branch": branch
    }

    response = requests.put(url, headers=get_github_headers(), json=payload, timeout=30)
    return response, repo_path


# ---------------------------
# State helpers
# ---------------------------
def load_first_practice_word():
    """연습 시작 시 첫 문제를 가져옵니다."""
    if len(st.session_state.practice_queue) > 0:
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
        set_next_practice_display_side()
    else:
        st.session_state.current_practice_word = None


def start_practice(mode):
    """연습 시작 공통 함수.

    중복 로직을 줄여 유지보수를 쉽게 합니다.
    """
    if len(st.session_state.words) == 0:
        st.warning("먼저 파일을 선택해 주세요.")
        return

    st.session_state.practice_mode = mode

    if len(st.session_state.practice_queue) == 0:
        st.session_state.practice_queue = list(st.session_state.words)

    st.session_state.is_practicing = True
    st.session_state.show_answer = False
    st.session_state.practice_show_hint = False
    load_first_practice_word()


def reset_exam_state():
    """시험 상태 초기화."""
    st.session_state.is_examining = False
    st.session_state.exam_mode = None
    st.session_state.exam_queue = []
    st.session_state.current_exam_word = None
    st.session_state.exam_current_number = 0
    st.session_state.exam_correct_count = 0
    st.session_state.exam_wrong_count = 0
    st.session_state.exam_show_answer = False
    st.session_state.exam_display_side = 0


# ---------------------------
# Study / Practice / Exam logic
# ---------------------------
def load_next_exam_question():
    if len(st.session_state.exam_queue) > 0:
        st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
        st.session_state.exam_current_number += 1
        st.session_state.exam_show_answer = False

        if st.session_state.exam_mode == "meaning_only":
            st.session_state.exam_display_side = 0
        elif st.session_state.exam_mode == "word_only":
            st.session_state.exam_display_side = 1
        else:
            st.session_state.exam_display_side = random.choice([0, 1])
    else:
        st.session_state.current_exam_word = None
        st.session_state.is_examining = False


def start_exam(mode):
    if len(st.session_state.exam_source_words) == 0:
        st.warning("먼저 파일을 선택해 단어를 불러와 주세요.")
        return

    total_words = len(st.session_state.exam_source_words)
    requested_count = st.session_state.exam_total_count

    if requested_count < 1:
        st.warning("시험 개수는 1개 이상이어야 합니다.")
        return

    actual_count = min(requested_count, total_words)

    exam_words = list(st.session_state.exam_source_words)
    random.shuffle(exam_words)
    st.session_state.exam_queue = exam_words[:actual_count]

    st.session_state.is_examining = True
    st.session_state.exam_mode = mode
    st.session_state.exam_current_number = 0
    st.session_state.exam_correct_count = 0
    st.session_state.exam_wrong_count = 0
    st.session_state.exam_show_answer = False

    load_next_exam_question()


def set_next_practice_display_side():
    if st.session_state.practice_mode == "meaning_only":
        st.session_state.practice_display_side = 0
    elif st.session_state.practice_mode == "word_only":
        st.session_state.practice_display_side = 1
    else:
        st.session_state.practice_display_side = random.choice([0, 1])


def move_to_next_practice_word():
    """현재 문제를 처리한 뒤 다음 문제로 이동합니다."""
    st.session_state.show_answer = False
    st.session_state.practice_show_hint = False

    if len(st.session_state.practice_queue) > 0:
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
        set_next_practice_display_side()
    else:
        st.session_state.current_practice_word = None


def get_random_position_by_percent(n, start_ratio, end_ratio):
    if n <= 0:
        return 0

    start_idx = int(n * start_ratio)
    end_idx = int(n * end_ratio)

    start_idx = max(0, min(start_idx, n))
    end_idx = max(0, min(end_idx, n))

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx

    return random.randint(start_idx, end_idx)


def handle_practice_score(level):
    """연습 평가 결과에 따라 단어를 큐 뒤쪽 적절한 위치에 재삽입합니다."""
    current_word = st.session_state.current_practice_word
    if current_word is None:
        return

    n = len(st.session_state.practice_queue)

    if level == 100:
        pass
    elif level == 60:
        pos = get_random_position_by_percent(n, 0.6, 0.8)
        st.session_state.practice_queue.insert(pos, current_word)
    elif level == 40:
        pos = get_random_position_by_percent(n, 0.3, 0.5)
        st.session_state.practice_queue.insert(pos, current_word)
    elif level == 0:
        pos = get_random_position_by_percent(n, 0.1, 0.2)
        st.session_state.practice_queue.insert(pos, current_word)

    move_to_next_practice_word()


def load_words_from_github_file(selected_folder, selected_file):
    repo_file_path = f"{selected_folder}/{selected_file}"
    text = get_github_file_text(repo_file_path)
    return parse_word_text(text)


# ---------------------------
# UI Parts
# ---------------------------
def render_study_part():
    st.header("학습 파트")

    folders, folder_error = get_github_folders("word_list")

    if folder_error:
        st.error(folder_error)
        return

    if not folders:
        st.warning("GitHub의 word_list 아래에 선택 가능한 폴더가 없습니다.")
        return

    selected_folder = st.selectbox("학습할 폴더를 선택하세요", folders, key="study_folder_select")

    txt_files, files_error = get_github_txt_files(selected_folder)
    if files_error:
        st.error(files_error)
        return

    if not txt_files:
        st.warning("선택한 폴더에 txt 파일이 없습니다.")
        return

    selected_file = st.selectbox("학습할 텍스트 파일을 선택하세요", txt_files, key="study_file_select")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("파일 선택하기", use_container_width=True):
            try:
                st.session_state.words = load_words_from_github_file(selected_folder, selected_file)
                st.session_state.study_index = 0
                st.session_state.is_studying = False
                st.session_state.study_show_hint = False
                st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
            except Exception as e:
                st.error(f"파일 선택 중 오류가 발생했습니다: {e}")

    with col2:
        if st.button("랜덤으로 섞기", use_container_width=True):
            if len(st.session_state.words) > 0:
                random.shuffle(st.session_state.words)
                st.session_state.study_index = 0
                st.session_state.study_show_hint = False
                st.success("단어 목록이 랜덤으로 섞였습니다!")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with col3:
        if st.button("학습하기", use_container_width=True):
            if len(st.session_state.words) > 0:
                st.session_state.is_studying = True
                st.session_state.study_index = 0
                st.session_state.study_show_hint = False
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    if len(st.session_state.words) > 0 and st.session_state.is_studying:
        st.write("---")

        if st.session_state.study_index < len(st.session_state.words):
            current_word = st.session_state.words[st.session_state.study_index]
            has_hint = bool(current_word.get("hint", "").strip())

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("다음", key="study_next_btn", use_container_width=True):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False

            with col_btn2:
                if st.button("힌트 보기", key="study_hint_btn", use_container_width=True, disabled=not has_hint):
                    st.session_state.study_show_hint = True

            if st.session_state.study_index < len(st.session_state.words):
                current_word = st.session_state.words[st.session_state.study_index]

                st.markdown(
                    f"<div class='study-word'>단어: {current_word['word']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div class='study-word'>의미: {current_word['meaning']}</div>",
                    unsafe_allow_html=True
                )

                if st.session_state.study_show_hint and current_word.get("hint", "").strip():
                    st.info(f"힌트:\n{current_word['hint']}")
            else:
                st.success("모두 학습했습니다.")
        else:
            st.success("모두 학습했습니다.")


def render_practice_part():
    st.header("연습 파트")

    folders, folder_error = get_github_folders("word_list")

    if folder_error:
        st.error(folder_error)
        return

    if not folders:
        st.warning("GitHub의 word_list 아래에 선택 가능한 폴더가 없습니다.")
        return

    selected_folder = st.selectbox("연습할 폴더를 선택하세요", folders, key="practice_folder_select")

    txt_files, files_error = get_github_txt_files(selected_folder)
    if files_error:
        st.error(files_error)
        return

    if not txt_files:
        st.warning("선택한 폴더에 txt 파일이 없습니다.")
        return

    selected_file = st.selectbox("파일을 선택하세요.", txt_files, key="practice_file_select")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("파일 선택하기", key="practice_load", use_container_width=True):
            try:
                st.session_state.words = load_words_from_github_file(selected_folder, selected_file)
                st.session_state.practice_queue = list(st.session_state.words)
                st.session_state.is_practicing = False
                st.session_state.current_practice_word = None
                st.session_state.show_answer = False
                st.session_state.practice_show_hint = False
                st.session_state.practice_mode = "random"
                st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
            except Exception as e:
                st.error(f"파일 선택 중 오류가 발생했습니다: {e}")

    with col2:
        if st.button("단어 랜덤으로 섞기", use_container_width=True):
            if len(st.session_state.practice_queue) > 0:
                random.shuffle(st.session_state.practice_queue)
                st.session_state.is_practicing = False
                st.session_state.current_practice_word = None
                st.session_state.show_answer = False
                st.session_state.practice_show_hint = False
                st.session_state.practice_mode = "random"
                st.success("연습 단어가 랜덤으로 섞였습니다!")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with col3:
        if st.button("연습 준비", use_container_width=True):
            if len(st.session_state.words) > 0:
                if len(st.session_state.practice_queue) == 0:
                    st.session_state.practice_queue = list(st.session_state.words)

                st.session_state.is_practicing = False
                st.session_state.current_practice_word = None
                st.session_state.show_answer = False
                st.session_state.practice_show_hint = False
                st.success("연습 준비가 완료되었습니다. 아래에서 연습 방식을 선택해 주세요.")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    st.write("")
    mode_col1, mode_col2, mode_col3 = st.columns(3)

    with mode_col1:
        if st.button("단어 이름만 연습하기", use_container_width=True):
            start_practice("word_only")

    with mode_col2:
        if st.button("단어 뜻만 연습하기", use_container_width=True):
            start_practice("meaning_only")

    with mode_col3:
        if st.button("랜덤으로 연습하기", use_container_width=True):
            start_practice("random")

    if st.session_state.is_practicing:
        st.write("---")

        if st.session_state.current_practice_word is not None:
            has_hint = bool(st.session_state.current_practice_word.get("hint", "").strip())
            score_col1, hint_col, score_col2, score_col3, score_col4, score_col5 = st.columns(6)

            with score_col1:
                if st.button("정답", use_container_width=True):
                    st.session_state.show_answer = True

            with hint_col:
                if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                    st.session_state.practice_show_hint = True

            with score_col2:
                if st.button("100%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(100)

            with score_col3:
                if st.button("60%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(60)

            with score_col4:
                if st.button("40%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(40)

            with score_col5:
                if st.button("0%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(0)

            st.write("---")

            if st.session_state.current_practice_word is not None:
                if st.session_state.practice_display_side == 0:
                    question_text = st.session_state.current_practice_word["word"]
                    answer_text = st.session_state.current_practice_word["meaning"]
                else:
                    question_text = st.session_state.current_practice_word["meaning"]
                    answer_text = st.session_state.current_practice_word["word"]

                st.markdown(
                    f"<div class='practice-question'>문제: {question_text}</div>",
                    unsafe_allow_html=True
                )

                if st.session_state.practice_show_hint and has_hint:
                    st.info(f"힌트:\n{st.session_state.current_practice_word['hint']}")

                if st.session_state.show_answer:
                    st.markdown(
                        f"<div class='practice-answer'>정답: {answer_text}</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.success("모든 연습을 완료했습니다.")
        else:
            st.success("모든 연습을 완료했습니다.")


def render_exam_part():
    st.header("시험 파트")

    folders, folder_error = get_github_folders("word_list")

    if folder_error:
        st.error(folder_error)
        return

    if not folders:
        st.warning("GitHub의 word_list 아래에 선택 가능한 폴더가 없습니다.")
        return

    selected_folder = st.selectbox("시험할 폴더를 선택하세요", folders, key="exam_folder_select")

    txt_files, files_error = get_github_txt_files(selected_folder)
    if files_error:
        st.error(files_error)
        return

    if not txt_files:
        st.warning("선택한 폴더에 txt 파일이 없습니다.")
        return

    selected_file_exam = st.selectbox("시험할 파일을 선택하세요", txt_files, key="exam_file_select")

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.2, 1.2, 1.2, 1.6], vertical_alignment="bottom")

    with top_col1:
        if st.button("파일 선택하기", key="exam_load", use_container_width=True):
            try:
                loaded_words = load_words_from_github_file(selected_folder, selected_file_exam)
                st.session_state.words = loaded_words
                st.session_state.exam_source_words = list(loaded_words)
                reset_exam_state()
                st.session_state.exam_total_count_input = min(
                    max(1, len(st.session_state.exam_source_words)),
                    st.session_state.exam_total_count_input
                )
                st.success(f"'{selected_file_exam}'에서 {len(loaded_words)}개의 단어를 성공적으로 불러왔습니다!")
            except Exception as e:
                st.error(f"파일 선택 중 오류가 발생했습니다: {e}")

    with top_col2:
        if st.button("단어 랜덤으로 섞기", key="exam_shuffle", use_container_width=True):
            if len(st.session_state.exam_source_words) > 0:
                random.shuffle(st.session_state.exam_source_words)
                reset_exam_state()
                st.success("시험 단어가 랜덤으로 섞였습니다!")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with top_col3:
        if st.button("시험 준비", key="exam_ready", use_container_width=True):
            if len(st.session_state.exam_source_words) > 0:
                reset_exam_state()
                st.success("시험 준비가 완료되었습니다. 아래에서 시험 방식을 선택해 주세요.")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with top_col4:
        max_count = max(1, len(st.session_state.exam_source_words)) if len(st.session_state.exam_source_words) > 0 else 1

        if st.session_state.exam_total_count_input > max_count:
            st.session_state.exam_total_count_input = max_count

        inner_col1, inner_col2 = st.columns([2.2, 1])

        with inner_col1:
            st.number_input(
                "시험 개수 선택하기",
                min_value=1,
                max_value=max_count,
                step=1,
                key="exam_total_count_input"
            )

        with inner_col2:
            st.write("")
            if st.button("max", key="exam_count_max_btn", use_container_width=True):
                st.session_state.exam_total_count_input = max_count

        st.session_state.exam_total_count = st.session_state.exam_total_count_input

    st.write("")
    mode_col1, mode_col2, mode_col3 = st.columns(3)

    with mode_col1:
        if st.button("단어 이름만 시험 보기", use_container_width=True):
            start_exam("word_only")

    with mode_col2:
        if st.button("단어 뜻만 시험 보기", use_container_width=True):
            start_exam("meaning_only")

    with mode_col3:
        if st.button("랜덤으로 시험 보기", use_container_width=True):
            start_exam("random")

    if st.session_state.current_exam_word is not None:
        st.write("---")

        action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1, 2])

        with action_col1:
            if st.button("정답", key="exam_show_answer_btn", use_container_width=True):
                st.session_state.exam_show_answer = True

        with action_col2:
            if st.button("O", key="exam_o_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                st.session_state.exam_correct_count += 1
                load_next_exam_question()

        with action_col3:
            if st.button("X", key="exam_x_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                st.session_state.exam_wrong_count += 1
                load_next_exam_question()

        with action_col4:
            total = st.session_state.exam_total_count
            current = st.session_state.exam_current_number
            remain = total - (st.session_state.exam_correct_count + st.session_state.exam_wrong_count)
            st.info(
                f"진행중: {current}/{total}  |  남음: {remain}  |  맞음: {st.session_state.exam_correct_count}  |  틀림: {st.session_state.exam_wrong_count}"
            )

        st.write("---")

        if st.session_state.current_exam_word is not None:
            if st.session_state.exam_display_side == 0:
                question_text = st.session_state.current_exam_word["word"]
                answer_text = st.session_state.current_exam_word["meaning"]
            else:
                question_text = st.session_state.current_exam_word["meaning"]
                answer_text = st.session_state.current_exam_word["word"]

            st.markdown(
                f"<div class='exam-question'>문제: {question_text}</div>",
                unsafe_allow_html=True
            )

            if st.session_state.exam_show_answer:
                st.markdown(
                    f"<div class='exam-answer'>정답: {answer_text}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.success(
                f"시험이 완료되었습니다. 맞음 {st.session_state.exam_correct_count}개, 틀림 {st.session_state.exam_wrong_count}개입니다."
            )

    elif not st.session_state.is_examining:
        if st.session_state.exam_current_number > 0:
            total_answered = st.session_state.exam_correct_count + st.session_state.exam_wrong_count
            if total_answered == st.session_state.exam_total_count:
                st.success(
                    f"시험이 완료되었습니다. 맞음 {st.session_state.exam_correct_count}개, 틀림 {st.session_state.exam_wrong_count}개입니다."
                )


def render_wordbook_part():
    st.header("단어장 파트")
    st.caption("사용자는 직접 txt 파일을 업로드하거나 내용을 입력해 새 단어장을 만들 수 있습니다. 삭제는 GitHub 관리자만 할 수 있습니다.")

    _, top_right = st.columns([5, 1])

    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
            st.success("GitHub 목록 캐시를 새로고침했습니다.")

    folders, folder_error = get_github_folders("word_list")

    if folder_error:
        st.error(folder_error)
        return

    if not folders:
        st.warning("GitHub의 word_list 아래에 선택 가능한 폴더가 없습니다. 관리자에게 폴더를 먼저 만들어 달라고 요청해 주세요.")
        return

    selected_folder = st.selectbox("저장할 폴더를 선택하세요", folders, key="wordbook_folder_select")
    existing_files, files_error = get_github_txt_files(selected_folder)

    st.write("### 현재 폴더의 기존 txt 파일 목록")
    if files_error:
        st.warning(files_error)
    elif existing_files:
        for name in existing_files:
            st.write(f"- {name}")
    else:
        st.info("이 폴더에는 아직 txt 파일이 없습니다.")

    st.write("---")

    upload_tab, manual_tab = st.tabs(["txt 파일 업로드", "직접 입력해서 저장"])

    with upload_tab:
        st.subheader("txt 파일 업로드")
        uploaded_file = st.file_uploader("txt 파일을 업로드하세요", type=["txt"], key="wordbook_txt_upload")

        if uploaded_file is not None:
            uploaded_text = None

            try:
                uploaded_text = uploaded_file.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                try:
                    uploaded_text = uploaded_file.getvalue().decode("cp949")
                except Exception:
                    st.error("txt 파일 인코딩을 읽지 못했습니다. UTF-8 또는 CP949 형식인지 확인해 주세요.")

            if uploaded_text is not None:
                parsed_words, errors = parse_words_with_validation(uploaded_text)

                st.write(f"검사 결과: 정상 단어 {len(parsed_words)}개")

                if errors:
                    st.error("형식 오류가 있습니다.")
                    for err in errors:
                        st.write(f"- {err}")
                else:
                    st.success("형식 검사를 통과했습니다.")

                if parsed_words:
                    st.write("### 미리보기")
                    st.table(parsed_words[:min(20, len(parsed_words))])

                with st.form("upload_txt_form"):
                    upload_title = st.text_input("저장할 제목을 입력하세요", placeholder="예: 정보처리기사 실기 오답노트")
                    upload_password_input = st.text_input("업로드 비밀번호", type="password")
                    upload_submitted = st.form_submit_button("GitHub에 저장하기", use_container_width=True)

                    if upload_submitted:
                        if not upload_title.strip():
                            st.warning("저장할 제목을 입력해 주세요.")
                        elif len(parsed_words) == 0:
                            st.warning("저장할 정상 단어가 없습니다.")
                        elif errors:
                            st.warning("형식 오류를 먼저 수정한 뒤 저장해 주세요.")
                        elif upload_password_input != str(st.secrets["upload_password"]).strip():
                            st.error("업로드 비밀번호가 올바르지 않습니다.")
                        else:
                            final_file_name = make_manual_filename_from_title(upload_title)
                            response, repo_path = upload_text_to_github(selected_folder, final_file_name, uploaded_text)

                            if response.status_code in [200, 201]:
                                clear_github_cache()
                                st.success(f"GitHub에 저장되었습니다: {repo_path}")
                            else:
                                st.error(f"GitHub 저장 실패: {response.status_code}")
                                try:
                                    st.code(response.json())
                                except Exception:
                                    st.text(response.text)

    with manual_tab:
        st.subheader("직접 입력해서 저장")

        default_title_prefix = get_default_manual_title_prefix()

        with st.form("manual_wordbook_form"):
            manual_title = st.text_input(
                "저장할 제목을 입력하세요",
                value=default_title_prefix,
                placeholder="예: 2026.07.17_15.11_일본어 오답"
            )
            manual_text = st.text_area(
                "단어장을 입력하세요",
                height=300,
                placeholder="예시 1)\napple\n사과\n\nbanana\n바나나\n\n예시 2)\napple: 사과\nbanana: 바나나"
            )
            manual_password_input = st.text_input("업로드 비밀번호", type="password")
            manual_submitted = st.form_submit_button("형식 검사 및 GitHub에 저장하기", use_container_width=True)

        if manual_submitted:
            parsed_words, errors = parse_words_with_validation(manual_text)

            st.write(f"검사 결과: 정상 단어 {len(parsed_words)}개")

            if errors:
                st.error("형식 오류가 있습니다.")
                for err in errors:
                    st.write(f"- {err}")
            else:
                st.success("형식 검사를 통과했습니다.")

            if parsed_words:
                st.write("### 미리보기")
                st.table(parsed_words[:min(20, len(parsed_words))])

            if not manual_title.strip():
                st.warning("저장할 제목을 입력해 주세요.")
            elif manual_title.strip() == default_title_prefix.strip():
                st.warning("제목 뒤의 자유 내용을 입력해 주세요.")
            elif not manual_text.strip():
                st.warning("단어장 내용을 입력해 주세요.")
            elif len(parsed_words) == 0:
                st.warning("저장할 정상 단어가 없습니다.")
            elif errors:
                st.warning("형식 오류를 먼저 수정한 뒤 다시 저장해 주세요.")
            elif manual_password_input != str(st.secrets["upload_password"]).strip():
                st.error("업로드 비밀번호가 올바르지 않습니다.")
            else:
                final_file_name = make_manual_filename_from_title(manual_title)
                response, repo_path = upload_text_to_github(selected_folder, final_file_name, manual_text)

                if response.status_code in [200, 201]:
                    clear_github_cache()
                    st.success(f"GitHub에 저장되었습니다: {repo_path}")
                else:
                    st.error(f"GitHub 저장 실패: {response.status_code}")
                    try:
                        st.code(response.json())
                    except Exception:
                        st.text(response.text)


# ---------------------------
# Main
# ---------------------------
def main():
    init_session_state()
    render_mobile_toolbar()

    st.title("단어 암기 프로그램")
    st.caption("세션이 유지되는 동안 학습/연습/시험 진행 상태가 유지됩니다. 브라우저 새로고침이나 탭 종료 시에는 초기화됩니다.")

    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ["학습", "연습", "시험", "단어장"])

    if page == "학습":
        render_study_part()
    elif page == "연습":
        render_practice_part()
    elif page == "시험":
        render_exam_part()
    elif page == "단어장":
        render_wordbook_part()


if __name__ == "__main__":
    main()