import streamlit as st
import random
import requests
import base64
import re
import calendar
from datetime import datetime, date, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon="📚",
    layout="centered"
)

# ---------------------------
# Session State
# ---------------------------
def init_session_state():
    now = datetime.now()

    defaults = {
        "words": [],
        "loaded_words_snapshot": [],

        "study_index": 0,
        "is_studying": False,
        "study_show_hint": False,

        "practice_queue": [],
        "practice_queue_snapshot": [],
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

        "font_scale": 1.0,
        "button_scale": 1.0,
        "big_button_mode": False,

        "selected_files_study": [],
        "selected_files_practice": [],
        "selected_files_exam": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def keep_session_keys():
    protected_keys = [
        "words", "loaded_words_snapshot", "study_index", "is_studying", "study_show_hint",
        "practice_queue", "practice_queue_snapshot", "current_practice_word", "is_practicing",
        "practice_display_side", "practice_mode", "show_answer", "practice_show_hint",
        "exam_show_answer", "exam_queue", "exam_source_words", "current_exam_word",
        "is_examining", "exam_mode", "exam_total_count", "exam_current_number",
        "exam_correct_count", "exam_wrong_count", "exam_display_side", "exam_total_count_input",
        "font_scale", "button_scale", "big_button_mode",
        "selected_files_study", "selected_files_practice", "selected_files_exam"
    ]
    for key in protected_keys:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]

def restore_if_words_disappeared():
    if len(st.session_state.words) == 0 and len(st.session_state.loaded_words_snapshot) > 0:
        st.session_state.words = list(st.session_state.loaded_words_snapshot)
    if len(st.session_state.practice_queue) == 0 and st.session_state.is_practicing:
        if st.session_state.current_practice_word is None and len(st.session_state.practice_queue_snapshot) > 0:
            st.session_state.practice_queue = list(st.session_state.practice_queue_snapshot)
    if len(st.session_state.exam_source_words) == 0 and st.session_state.is_examining:
        if len(st.session_state.words) > 0:
            st.session_state.exam_source_words = list(st.session_state.words)

# ---------------------------
# Font / Style
# ---------------------------
def increase_font_scale():
    st.session_state.font_scale = min(1.8, round(st.session_state.font_scale + 0.1, 1))
    st.session_state.button_scale = min(1.8, round(st.session_state.button_scale + 0.1, 1))

def decrease_font_scale():
    st.session_state.font_scale = max(0.8, round(st.session_state.font_scale - 0.1, 1))
    st.session_state.button_scale = max(0.8, round(st.session_state.button_scale - 0.1, 1))

def reset_font_scale():
    st.session_state.font_scale = 1.0
    st.session_state.button_scale = 1.0
    st.session_state.big_button_mode = False

def toggle_big_button_mode():
    st.session_state.big_button_mode = not st.session_state.big_button_mode

def apply_global_style():
    font_scale = st.session_state.font_scale
    button_scale = st.session_state.button_scale
    big_button_mode = st.session_state.big_button_mode

    if big_button_mode:
        button_scale = max(button_scale, 1.35)
        font_scale = max(font_scale, 1.1)

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
        html, body, [data-testid="stAppViewContainer"] {{ font-size: {base_font}px !important; }}
        p, li, label, div, span {{ font-size: {base_font}px; }}
        .study-word {{ font-size: {large_font}px !important; line-height: 1.5; word-break: keep-all; margin-bottom: 0.5rem; text-align: center; }}
        .practice-question {{ font-size: {question_font}px !important; text-align: center; padding: 20px; line-height: 1.5; word-break: keep-all; }}
        .practice-answer {{ font-size: {answer_font}px !important; text-align: center; color: gray; padding: 10px; line-height: 1.5; word-break: keep-all; }}
        .exam-question {{ font-size: {exam_question_font}px !important; text-align: center; padding: 28px; line-height: 1.5; word-break: keep-all; }}
        .exam-answer {{ font-size: {answer_font}px !important; text-align: center; color: gray; padding: 12px; line-height: 1.5; word-break: keep-all; }}
        div[data-testid="stButton"] > button, .stFormSubmitButton > button {{
            min-height: {button_height}px !important; font-size: {button_font}px !important; font-weight: 700 !important; border-radius: 12px !important;
        }}
        </style>
        """, unsafe_allow_html=True
    )

# ---------------------------
# GitHub API & Caching
# ---------------------------
def get_github_headers():
    token = str(st.secrets["github_token"]).strip()
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def get_repo_info():
    owner = str(st.secrets["github_owner"]).strip()
    repo = str(st.secrets["github_repo"]).strip()
    branch = str(st.secrets["github_branch"]).strip()
    return owner, repo, branch

def encode_github_path(path):
    return quote(str(path).strip(), safe="/")

@st.cache_data(ttl=120, max_entries=256, show_spinner=False)
def github_get_contents_cached(path):
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encode_github_path(path)}?ref={quote(branch, safe='')}"
    response = requests.get(url, headers=get_github_headers(), timeout=30)
    return response.status_code, response.json() if response.content else {}

@st.cache_data(ttl=120, show_spinner=False)
def get_dynamic_main_categories():
    status, data = github_get_contents_cached("word_list")
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "dir"])
    return []

@st.cache_data(ttl=120, show_spinner=False)
def get_subfolders(main_category):
    status, data = github_get_contents_cached(f"word_list/{main_category}")
    if status == 200 and isinstance(data, list):
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return sorted(folders) if folders else ["(하위 폴더 없음)"]
    return ["(하위 폴더 없음)"]

@st.cache_data(ttl=120, max_entries=256, show_spinner=False)
def get_github_txt_files(folder_path):
    try:
        status_code, data = github_get_contents_cached(folder_path)
        if status_code != 200: return []
        if isinstance(data, list):
            return sorted([item.get("name") for item in data if item.get("type") == "file" and item.get("name", "").lower().endswith(".txt")])
        return []
    except Exception:
        return []

@st.cache_data(ttl=120, max_entries=512, show_spinner=False)
def get_github_file_text(repo_file_path):
    status_code, data = github_get_contents_cached(repo_file_path)
    if status_code != 200: raise Exception(f"GitHub 파일을 불러오지 못했습니다. (코드: {status_code})")
    content_b64 = data.get("content", "").replace("\n", "")
    return base64.b64decode(content_b64).decode("utf-8")

# ---------------------------
# Parsing Logic (3줄 힌트 지원)
# ---------------------------
def parse_word_text(text):
    normalized_text = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized_text.split("\n")
    parsed_words = []
    i = 0
    while i < len(lines):
        while i < len(lines) and not lines[i].strip(): i += 1
        if i >= len(lines): break
        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1
        if not block: continue
        
        if ":" in block[0]:
            parts = block[0].split(":", 1)
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if word and meaning: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) >= 2:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if word and meaning: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
    return parsed_words

def deduplicate_words(words):
    seen = set()
    result = []
    for item in words:
        key = (item.get("word", "").strip(), item.get("meaning", "").strip(), item.get("hint", "").strip())
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

# ---------------------------
# Sidebar UI Controls
# ---------------------------
def render_sidebar_controls(prefix):
    with st.sidebar:
        st.write("---")
        st.subheader("⚙️ 설정 및 파일 선택")
        
        # 1. 글자 크기 조절
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("A+", key=f"{prefix}_font_plus", use_container_width=True): increase_font_scale(); st.rerun()
        with c2:
            if st.button("A-", key=f"{prefix}_font_minus", use_container_width=True): decrease_font_scale(); st.rerun()
        with c3:
            if st.button("기본", key=f"{prefix}_font_reset", use_container_width=True): reset_font_scale(); st.rerun()

        # 2. 동적 대분류 선택 (폴더명 자동 인식)
        categories = get_dynamic_main_categories()
        if not categories:
            st.warning("word_list 폴더를 찾을 수 없습니다.")
            return []

        main_cat = st.selectbox("대분류 (폴더) 선택", categories, key=f"{prefix}_main_cat")
        
        # 3. 하위 폴더 및 파일 다중 선택 (콤보박스)
        subfolders = get_subfolders(main_cat)
        
        all_txt_files = []
        if subfolders and subfolders[0] != "(하위 폴더 없음)":
            selected_subs = st.multiselect("하위 폴더 선택", subfolders, default=subfolders, key=f"{prefix}_sub_cat")
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                files = get_github_txt_files(path)
                for f in files: all_txt_files.append({"folder": path, "file": f, "label": f"[{sub}] {f}"})
        else:
            path = f"word_list/{main_cat}"
            files = get_github_txt_files(path)
            for f in files: all_txt_files.append({"folder": path, "file": f, "label": f})

        if not all_txt_files:
            st.info("선택한 폴더에 txt 파일이 없습니다.")
            return []

        # 콤보박스(multiselect) 형태로 원하는 파일 선택
        file_labels = [item["label"] for item in all_txt_files]
        selected_labels = st.multiselect("학습할 파일 선택", file_labels, default=file_labels, key=f"{prefix}_file_select")
        
        selected_items = [item for item in all_txt_files if item["label"] in selected_labels]
        return selected_items

def load_and_start(prefix, selected_items, mode="random"):
    if not selected_items:
        st.warning("사이드바에서 파일을 하나 이상 선택해 주세요.")
        return False

    merged_words = []
    for item in selected_items:
        text = get_github_file_text(f"{item['folder']}/{item['file']}")
        merged_words.extend(parse_word_text(text))
    
    merged_words = deduplicate_words(merged_words)
    random.shuffle(merged_words)
    
    st.session_state.words = list(merged_words)
    st.session_state.loaded_words_snapshot = list(merged_words)
    
    if prefix == "study":
        st.session_state.study_index = 0
        st.session_state.is_studying = True
        st.session_state.study_show_hint = False
    elif prefix == "practice":
        st.session_state.practice_queue = list(st.session_state.words)
        st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)
        st.session_state.is_practicing = True
        st.session_state.show_answer = False
        st.session_state.practice_show_hint = False
        st.session_state.practice_mode = mode
        if len(st.session_state.practice_queue) > 0:
            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
            st.session_state.practice_display_side = random.choice([0, 1]) if mode == "random" else (0 if mode=="meaning_only" else 1)
    elif prefix == "exam":
        st.session_state.exam_source_words = list(st.session_state.words)
        st.session_state.is_examining = True
        st.session_state.exam_mode = mode
        st.session_state.exam_current_number = 0
        st.session_state.exam_correct_count = 0
        st.session_state.exam_wrong_count = 0
        st.session_state.exam_show_answer = False
        
        exam_words = list(st.session_state.exam_source_words)
        random.shuffle(exam_words)
        actual_count = min(st.session_state.exam_total_count_input, len(exam_words))
        st.session_state.exam_total_count = actual_count
        st.session_state.exam_queue = exam_words[:actual_count]
        
        if len(st.session_state.exam_queue) > 0:
            st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
            st.session_state.exam_current_number += 1
            st.session_state.exam_display_side = random.choice([0, 1]) if mode == "random" else (0 if mode=="meaning_only" else 1)
            
    return True

# ---------------------------
# Main Views
# ---------------------------
def render_study_part():
    st.header("학습 파트")
    selected_items = render_sidebar_controls("study")
    
    if st.button("선택한 파일로 학습 시작", use_container_width=True):
        if load_and_start("study", selected_items): st.rerun()

    st.write("---")
    if st.session_state.is_studying and st.session_state.study_index < len(st.session_state.words):
        current_word = st.session_state.words[st.session_state.study_index]
        
        # 버튼을 상단에 고정
        c1, c2 = st.columns(2)
        with c1:
            if st.button("다음 단어", use_container_width=True):
                st.session_state.study_index += 1
                st.session_state.study_show_hint = False
                st.rerun()
        with c2:
            has_hint = bool(current_word.get("hint", "").strip())
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                st.session_state.study_show_hint = True
                st.rerun()
                
        st.write("---")
        # 단어 카드 출력 영역
        st.markdown(f"<div class='study-word'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='study-word'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)
        if st.session_state.study_show_hint and has_hint:
            st.info(f"힌트:\n{current_word['hint']}")
            
    elif st.session_state.is_studying:
        st.success("모든 학습을 완료했습니다.")

def render_practice_part():
    st.header("연습 파트")
    selected_items = render_sidebar_controls("practice")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        if st.button("이름만 연습", use_container_width=True): load_and_start("practice", selected_items, "word_only")
    with m2:
        if st.button("뜻만 연습", use_container_width=True): load_and_start("practice", selected_items, "meaning_only")
    with m3:
        if st.button("랜덤 연습", use_container_width=True): load_and_start("practice", selected_items, "random")

    st.write("---")
    
    if st.session_state.is_practicing and st.session_state.current_practice_word is not None:
        cw = st.session_state.current_practice_word
        has_hint = bool(cw.get("hint", "").strip())
        is_answered = st.session_state.show_answer

        # 1. 정답 / 힌트 버튼 (상단)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("정답 확인", use_container_width=True):
                st.session_state.show_answer = True; st.rerun()
        with c2:
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                st.session_state.practice_show_hint = True; st.rerun()
        
        # 2. 점수 버튼 (정답을 봐야 활성화)
        s1, s2, s3, s4 = st.columns(4)
        
        def process_score(level):
            n = len(st.session_state.practice_queue)
            if level == 60: st.session_state.practice_queue.insert(max(0, int(n*0.6)), cw)
            elif level == 40: st.session_state.practice_queue.insert(max(0, int(n*0.3)), cw)
            elif level == 0: st.session_state.practice_queue.insert(max(0, int(n*0.1)), cw)
            
            st.session_state.show_answer = False
            st.session_state.practice_show_hint = False
            if len(st.session_state.practice_queue) > 0:
                st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                st.session_state.practice_display_side = random.choice([0, 1]) if st.session_state.practice_mode == "random" else (0 if st.session_state.practice_mode=="meaning_only" else 1)
            else:
                st.session_state.current_practice_word = None
                
        with s1: 
            if st.button("100%", disabled=not is_answered, use_container_width=True): process_score(100); st.rerun()
        with s2: 
            if st.button("60%", disabled=not is_answered, use_container_width=True): process_score(60); st.rerun()
        with s3: 
            if st.button("40%", disabled=not is_answered, use_container_width=True): process_score(40); st.rerun()
        with s4: 
            if st.button("0%", disabled=not is_answered, use_container_width=True): process_score(0); st.rerun()

        st.write("---")
        
        # 3. 단어 카드 (하단 고정)
        question_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        answer_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]

        st.markdown(f"<div class='practice-question'>문제: {question_text}</div>", unsafe_allow_html=True)
        if st.session_state.practice_show_hint and has_hint:
            st.info(f"힌트:\n{cw['hint']}")
        if is_answered:
            st.markdown(f"<div class='practice-answer'>정답: {answer_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_practicing:
        st.success("모든 연습을 완료했습니다.")

def render_exam_part():
    st.header("시험 파트")
    selected_items = render_sidebar_controls("exam")
    
    with st.sidebar:
        st.number_input("시험 개수", min_value=1, value=st.session_state.exam_total_count_input, key="exam_total_count_input")
    
    m1, m2, m3 = st.columns(3)
    with m1:
        if st.button("이름만 시험", use_container_width=True): load_and_start("exam", selected_items, "word_only")
    with m2:
        if st.button("뜻만 시험", use_container_width=True): load_and_start("exam", selected_items, "meaning_only")
    with m3:
        if st.button("랜덤 시험", use_container_width=True): load_and_start("exam", selected_items, "random")

    st.write("---")

    if st.session_state.is_examining and st.session_state.current_exam_word is not None:
        cw = st.session_state.current_exam_word
        is_answered = st.session_state.exam_show_answer

        # 1. 제어 버튼 상단 고정
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2.5])
        with c1:
            if st.button("정답 확인", use_container_width=True): st.session_state.exam_show_answer = True; st.rerun()
        
        def process_exam(correct=True):
            if correct: st.session_state.exam_correct_count += 1
            else: st.session_state.exam_wrong_count += 1
            st.session_state.exam_show_answer = False
            
            if len(st.session_state.exam_queue) > 0:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                st.session_state.exam_display_side = random.choice([0, 1]) if st.session_state.exam_mode == "random" else (0 if st.session_state.exam_mode=="meaning_only" else 1)
            else:
                st.session_state.current_exam_word = None
                
        with c2:
            if st.button("O (맞음)", disabled=not is_answered, use_container_width=True): process_exam(True); st.rerun()
        with c3:
            if st.button("X (틀림)", disabled=not is_answered, use_container_width=True): process_exam(False); st.rerun()
        with c4:
            tot = st.session_state.exam_total_count
            cur = st.session_state.exam_current_number
            st.info(f"진행: {cur}/{tot} | 맞음: {st.session_state.exam_correct_count} | 틀림: {st.session_state.exam_wrong_count}")

        st.write("---")
        
        # 2. 시험 카드 하단 고정
        question_text = cw["word"] if st.session_state.exam_display_side == 0 else cw["meaning"]
        answer_text = cw["meaning"] if st.session_state.exam_display_side == 0 else cw["word"]

        st.markdown(f"<div class='exam-question'>문제: {question_text}</div>", unsafe_allow_html=True)
        if is_answered:
            st.markdown(f"<div class='exam-answer'>정답: {answer_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_examining:
        st.success(f"시험 종료! 맞음: {st.session_state.exam_correct_count} | 틀림: {st.session_state.exam_wrong_count}")


def main():
    init_session_state()
    keep_session_keys()
    restore_if_words_disappeared()
    apply_global_style()

    st.title("단어 암기 프로그램")
    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ["학습", "연습", "시험"])

    if page == "학습":
        render_study_part()
    elif page == "연습":
        render_practice_part()
    elif page == "시험":
        render_exam_part()

if __name__ == "__main__":
    main()