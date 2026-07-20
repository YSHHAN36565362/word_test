import streamlit as st
import random
import requests
import base64
import re
from datetime import datetime
from urllib.parse import quote

# ---------------------------
# 기본 페이지 설정
# ---------------------------
st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon="📚",
    layout="centered"
)

# ---------------------------
# 1. Session State 초기화 (위젯 Key와 분리)
# ---------------------------
def init_session_state():
    defaults = {
        # 전역 단어 리스트
        "words": [],
        "loaded_words_snapshot": [],

        # 학습 파트 상태
        "study_index": 0,
        "is_studying": False,
        "study_show_hint": False,

        # 연습 파트 상태
        "practice_queue": [],
        "current_practice_word": None,
        "is_practicing": False,
        "practice_display_side": 0,
        "practice_mode": "random",
        "practice_show_answer": False,
        "practice_show_hint": False,

        # 시험 파트 상태
        "exam_queue": [],
        "exam_source_words": [],
        "current_exam_word": None,
        "is_examining": False,
        "exam_mode": None,
        "exam_total_count": 10,
        "exam_current_number": 0,
        "exam_correct_count": 0,
        "exam_wrong_count": 0,
        "exam_show_answer": False,
        "exam_display_side": 0,

        # UI 설정 상태
        "font_scale": 1.0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ---------------------------
# 2. 글로벌 CSS 스타일 (글자 크기 조절 및 고정 레이아웃)
# ---------------------------
def apply_global_style():
    scale = st.session_state.font_scale
    base = int(16 * scale)
    large = int(24 * scale)
    huge = int(40 * scale)
    
    st.markdown(f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{ font-size: {base}px !important; }}
        p, li, div, span {{ font-size: {base}px; }}
        
        /* 단어 카드 스타일 */
        .study-card {{
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }}
        .word-text {{ font-size: {large}px !important; font-weight: bold; color: #1f77b4; margin-bottom: 10px; }}
        .meaning-text {{ font-size: {large}px !important; margin-bottom: 10px; }}
        .hint-text {{ font-size: {base}px !important; color: #d62728; background-color: #ffe8e8; padding: 10px; border-radius: 5px; }}
        
        /* 연습/시험 큰 글씨 */
        .test-question {{ font-size: {huge}px !important; text-align: center; padding: 30px 10px; font-weight: bold; }}
        .test-answer {{ font-size: {large}px !important; text-align: center; color: #2ca02c; font-weight: bold; margin-bottom: 20px; }}
        
        /* 버튼 텍스트 강제 크기 지정 */
        div[data-testid="stButton"] > button {{ font-size: {base}px !important; }}
        </style>
    """, unsafe_allow_html=True)

def change_font_scale(amount):
    st.session_state.font_scale = max(0.8, min(2.0, st.session_state.font_scale + amount))

# ---------------------------
# 3. GitHub API 및 캐싱
# ---------------------------
def get_github_headers():
    token = str(st.secrets["github_token"]).strip()
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

def get_repo_info():
    owner = str(st.secrets["github_owner"]).strip()
    repo = str(st.secrets["github_repo"]).strip()
    branch = str(st.secrets["github_branch"]).strip()
    return owner, repo, branch

@st.cache_data(ttl=60, show_spinner=False)
def github_get_contents(path):
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path.strip(), safe='/')}?ref={quote(branch)}"
    response = requests.get(url, headers=get_github_headers(), timeout=15)
    return response.status_code, response.json() if response.status_code == 200 else {}

def get_dynamic_categories():
    """word_list 하위 폴더들을 대분류로 가져옴 (예: _Japanese, IT)"""
    status, data = github_get_contents("word_list")
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "dir"])
    return []

def get_subfolders(main_category):
    """대분류 하위의 폴더들을 가져옴"""
    status, data = github_get_contents(f"word_list/{main_category}")
    if status == 200 and isinstance(data, list):
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return sorted(folders) if folders else []
    return []

def get_txt_files(folder_path):
    """특정 경로의 txt 파일 목록 반환"""
    status, data = github_get_contents(folder_path)
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "file" and item["name"].lower().endswith(".txt")])
    return []

def get_file_content(repo_file_path):
    """파일 텍스트 내용 다운로드"""
    status, data = github_get_contents(repo_file_path)
    if status == 200:
        return base64.b64decode(data.get("content", "")).decode("utf-8")
    return ""

# ---------------------------
# 4. 단어 파싱 로직 (3줄 힌트 지원 및 중복 제거)
# ---------------------------
def parse_word_text(text):
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
    parsed_words = []
    i = 0
    
    while i < len(lines):
        # 빈 줄 건너뛰기
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines): break
        
        # 블록 단위로 묶기
        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1
            
        if not block: continue
        
        # 1줄에 콜론(:)이 있는 경우 (단어 : 뜻 \n 힌트...)
        if ":" in block[0]:
            parts = block[0].split(":", 1)
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if word and meaning: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
            
        # 줄바꿈으로 구분된 경우 (단어 \n 뜻 \n 힌트...)
        else:
            if len(block) >= 2:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if word and meaning: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
                
    # 중복 제거
    seen = set()
    result = []
    for w in parsed_words:
        key = (w["word"], w["meaning"], w["hint"])
        if key not in seen:
            seen.add(key)
            result.append(w)
            
    return result

# ---------------------------
# 5. UI - 사이드바 설정 및 폴더 감지
# ---------------------------
def render_sidebar():
    with st.sidebar:
        st.subheader("⚙️ 화면 설정")
        col1, col2, col3 = st.columns(3)
        if col1.button("A+", use_container_width=True): change_font_scale(0.1); st.rerun()
        if col2.button("A-", use_container_width=True): change_font_scale(-0.1); st.rerun()
        if col3.button("기본", use_container_width=True): st.session_state.font_scale = 1.0; st.rerun()
        
        st.write("---")
        st.subheader("📁 학습 파일 선택")
        
        categories = get_dynamic_categories()
        if not categories:
            st.error("word_list 폴더를 찾을 수 없습니다.")
            return []
            
        main_cat = st.selectbox("1. 대분류 선택", categories)
        sub_folders = get_subfolders(main_cat)
        
        all_files = []
        if sub_folders:
            selected_subs = st.multiselect("2. 하위 폴더 선택", sub_folders, default=sub_folders)
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                for f in get_txt_files(path):
                    all_files.append({"path": f"{path}/{f}", "label": f"[{sub}] {f}"})
        else:
            path = f"word_list/{main_cat}"
            for f in get_txt_files(path):
                all_files.append({"path": f"{path}/{f}", "label": f})
                
        if not all_files:
            st.warning("txt 파일이 없습니다.")
            return []
            
        file_labels = [f["label"] for f in all_files]
        selected_labels = st.multiselect("3. 파일 선택", file_labels, default=file_labels)
        
        return [f for f in all_files if f["label"] in selected_labels]

def load_data(selected_files):
    if not selected_files:
        st.warning("사이드바에서 파일을 선택해주세요.")
        return False
        
    merged = []
    for f in selected_files:
        text = get_file_content(f["path"])
        merged.extend(parse_word_text(text))
        
    random.shuffle(merged)
    st.session_state.words = merged
    return True

# ---------------------------
# 6. UI - 학습 파트
# ---------------------------
def render_study_part(selected_files):
    st.header("📖 학습 파트")
    
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
            # 상단 고정 컨트롤 버튼
            c1, c2 = st.columns(2)
            with c1:
                if st.button("다음 단어 ⏭️", use_container_width=True):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False # 다음 단어로 가면 힌트 가림
                    st.rerun()
            with c2:
                if st.button("힌트 보기 💡", use_container_width=True, disabled=not has_hint):
                    st.session_state.study_show_hint = True
                    st.rerun()
                    
            # 하단 고정 카드 영역
            st.markdown(f"""
                <div class="study-card">
                    <div class="word-text">단어: {word_data['word']}</div>
                    <div class="meaning-text">의미: {word_data['meaning']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 힌트가 토글되었을 때만 표시
            if st.session_state.study_show_hint and has_hint:
                st.markdown(f"<div class='hint-text'><strong>힌트:</strong><br>{word_data['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                
            st.caption(f"진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}")
        else:
            st.success("🎉 모든 단어 학습을 완료했습니다!")

# ---------------------------
# 7. UI - 연습 파트
# ---------------------------
def render_practice_part(selected_files):
    st.header("📝 연습 파트")
    
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
            st.session_state.practice_display_side = random.choice([0,1]) if mode == "random" else (0 if mode == "meaning_only" else 1)
        st.rerun()

    if st.session_state.is_practicing and st.session_state.current_practice_word:
        cw = st.session_state.current_practice_word
        has_hint = bool(cw["hint"].strip())
        is_ans_shown = st.session_state.practice_show_answer
        
        st.write("---")
        # 1. 정답 / 힌트 버튼 (항상 위)
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("정답 확인 👁️", use_container_width=True):
                st.session_state.practice_show_answer = True
                st.rerun()
        with btn2:
            if st.button("힌트 보기 💡", use_container_width=True, disabled=not has_hint):
                st.session_state.practice_show_hint = True
                st.rerun()
                
        # 2. 채점 버튼 (정답 확인 전에 무조건 비활성화)
        st.caption("※ 정답을 확인해야 자가 채점 버튼을 누를 수 있습니다.")
        s1, s2, s3, s4 = st.columns(4)
        
        def apply_score(level):
            n = len(st.session_state.practice_queue)
            if level == 60: st.session_state.practice_queue.insert(max(0, int(n*0.6)), cw)
            elif level == 40: st.session_state.practice_queue.insert(max(0, int(n*0.3)), cw)
            elif level == 0: st.session_state.practice_queue.insert(max(0, int(n*0.1)), cw)
            
            st.session_state.practice_show_answer = False
            st.session_state.practice_show_hint = False
            
            if st.session_state.practice_queue:
                st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                pmode = st.session_state.practice_mode
                st.session_state.practice_display_side = random.choice([0,1]) if pmode == "random" else (0 if pmode == "meaning_only" else 1)
            else:
                st.session_state.current_practice_word = None
                
        with s1:
            if st.button("완벽함 (100)", disabled=not is_ans_shown, use_container_width=True): apply_score(100); st.rerun()
        with s2:
            if st.button("조금 앎 (60)", disabled=not is_ans_shown, use_container_width=True): apply_score(60); st.rerun()
        with s3:
            if st.button("헷갈림 (40)", disabled=not is_ans_shown, use_container_width=True): apply_score(40); st.rerun()
        with s4:
            if st.button("모름 (0)", disabled=not is_ans_shown, use_container_width=True): apply_score(0); st.rerun()

        # 3. 단어 문제/정답 영역 (카드 하단 고정)
        q_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]
        
        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        
        if st.session_state.practice_show_hint and has_hint:
            st.markdown(f"<div class='hint-text' style='margin-top: 10px;'><strong>힌트:</strong><br>{cw['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_practicing:
        st.success("🎉 모든 연습을 완료했습니다!")

# ---------------------------
# 8. 메인 실행 함수
# ---------------------------
def main():
    init_session_state()
    apply_global_style()
    
    st.title("단어 암기 프로그램")
    selected_files = render_sidebar()
    
    # 탭 방식으로 학습/연습/시험 분리 (사이드바 메뉴 대신 상단 탭 사용 시 더 깔끔함)
    tab1, tab2 = st.tabs(["📖 학습", "📝 연습 (채점)"])
    
    with tab1:
        render_study_part(selected_files)
        
    with tab2:
        render_practice_part(selected_files)

if __name__ == "__main__":
    main()