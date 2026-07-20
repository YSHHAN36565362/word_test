import streamlit as st
import streamlit.components.v1 as components
import random
import requests
import base64
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

# ---------------------------
# 기본 페이지 설정
# ---------------------------
st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon="📚",
    layout="centered"
)

# ---------------------------
# 1. Session State 초기화
# ---------------------------
def init_session_state():
    defaults = {
        "words": [],
        "loaded_words_snapshot": [],

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
        "exam_total_count_input": 10,

        "font_scale": 1.0,
        
        # ****** 연속 수정 안내: 다크 모드/기본 모드 상태 저장 변수 추가 (기본값을 다크 모드로 설정)
        "theme_mode": "다크 모드",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ---------------------------
# 2. 글로벌 CSS 스타일 및 키보드 단축키 스크립트
# ---------------------------
def apply_global_style():
    scale = st.session_state.font_scale
    base = int(16 * scale)
    large = int(24 * scale)
    huge = int(40 * scale)
    
    # ****** 연속 수정 안내: 현재 선택된 테마에 맞춰 색상을 동적으로 변경합니다.
    is_dark = (st.session_state.theme_mode == "다크 모드")
    
    card_bg = "#262730" if is_dark else "#f8f9fa"
    text_color = "#ffffff" if is_dark else "#000000"
    word_color = "#4db8ff" if is_dark else "#1f77b4" # 다크모드일 땐 더 밝은 파란색
    hint_bg = "#3a3b40" if is_dark else "#e9ecef"    # 힌트 배경을 눈이 편안한 회색 계열로 변경
    hint_text = "#eeeeee" if is_dark else "#333333"  # 빨간 힌트 글씨 제거
    ans_color = "#45c95c" if is_dark else "#2ca02c"
    shadow_color = "rgba(0,0,0,0.5)" if is_dark else "rgba(0,0,0,0.1)"
    
    st.markdown(f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{ font-size: {base}px !important; }}
        p, li, div, span {{ font-size: {base}px; }}
        
        /* 단어 카드 스타일 */
        .study-card {{
            background-color: {card_bg};
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 2px 2px 5px {shadow_color};
        }}
        .word-text {{ font-size: {large}px !important; font-weight: bold; color: {word_color}; margin-bottom: 10px; text-align: center; }}
        .meaning-text {{ font-size: {large}px !important; color: {text_color}; margin-bottom: 10px; text-align: center; }}
        .hint-text {{ font-size: {base}px !important; color: {hint_text}; background-color: {hint_bg}; padding: 10px; border-radius: 5px; margin-top: 10px; }}
        
        /* 연습/시험 큰 글씨 */
        .test-question {{ font-size: {huge}px !important; color: {text_color}; text-align: center; padding: 30px 10px; font-weight: bold; }}
        .test-answer {{ font-size: {large}px !important; text-align: center; color: {ans_color}; font-weight: bold; margin-bottom: 20px; }}
        
        /* 버튼 텍스트 강제 크기 지정 */
        div[data-testid="stButton"] > button {{ font-size: {base}px !important; font-weight: 600 !important; }}
        </style>
    """, unsafe_allow_html=True)

def inject_keyboard_shortcuts():
    """자바스크립트를 주입하여 Z, X, C, V, H, Spacebar 단축키 활성화"""
    components.html("""
        <script>
        const doc = window.parent.document;
        if (!doc.hasOwnProperty('_shortcuts_attached')) {
            doc._shortcuts_attached = true;
            doc.addEventListener('keydown', function(e) {
                // 입력창(텍스트박스)에서 타이핑 중일 때는 단축키 작동 방지
                const tag = doc.activeElement.tagName;
                if (['INPUT', 'TEXTAREA'].includes(tag)) return;
                
                let key = e.key.toLowerCase();
                let buttons = Array.from(doc.querySelectorAll('button'));
                
                // 지정된 텍스트가 포함된 버튼을 찾아 클릭해주는 함수
                function clickBtn(matches) {
                    let btn = buttons.find(b => matches.some(m => b.innerText.includes(m)));
                    if (btn && !btn.disabled) {
                        btn.click();
                        return true;
                    }
                    return false;
                }
                
                if (key === ' ') { 
                    if (clickBtn(['다음 단어', '정답 확인'])) {
                        e.preventDefault(); // 스페이스바 화면 스크롤 방지
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
    status, data = github_get_contents("word_list")
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "dir"])
    return []

def get_subfolders(main_category):
    status, data = github_get_contents(f"word_list/{main_category}")
    if status == 200 and isinstance(data, list):
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return sorted(folders) if folders else []
    return []

def get_txt_files(folder_path):
    status, data = github_get_contents(folder_path)
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "file" and item["name"].lower().endswith(".txt")])
    return []

def get_file_content(repo_file_path):
    status, data = github_get_contents(repo_file_path)
    if status == 200:
        return base64.b64decode(data.get("content", "")).decode("utf-8")
    return ""

def upload_text_to_github(folder_path, file_name, text_content):
    owner, repo, branch = get_repo_info()
    repo_path = f"{str(folder_path).strip()}/{str(file_name).strip()}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}"
    
    content_b64 = base64.b64encode(text_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Add word list: {repo_path}",
        "content": content_b64,
        "branch": branch
    }
    
    response = requests.put(url, headers=get_github_headers(), json=payload, timeout=30)
    return response, repo_path

def clear_github_cache():
    st.cache_data.clear()

# ---------------------------
# 4. 단어 파싱 및 검증 유틸 (3줄 힌트 지원)
# ---------------------------
def parse_word_text(text):
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
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
                
    seen, result = set(), []
    for w in parsed_words:
        key = (w["word"], w["meaning"], w["hint"])
        if key not in seen:
            seen.add(key)
            result.append(w)
    return result

def parse_words_with_validation(text):
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
    parsed_words, errors = [], []
    i = 0
    
    while i < len(lines):
        while i < len(lines) and not lines[i].strip(): i += 1
        if i >= len(lines): break
        
        block_start = i
        block = []
        while i < len(lines) and lines[i].strip():
            block.append(lines[i].strip())
            i += 1
            
        if not block: continue

        if ":" in block[0]:
            parts = block[0].split(":", 1)
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""

            if not word: errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
            elif not meaning: errors.append(f"{block_start + 1}번 줄: 뜻이 없습니다.")
            else: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) == 1:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없는 단어입니다.")
            else:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                
                if not word: errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
                elif not meaning: errors.append(f"{block_start + 2}번 줄: 뜻이 없습니다.")
                else: parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    return parsed_words, errors

def make_safe_filename(name):
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_name = str(name).strip()
    for ch in invalid_chars:
        safe_name = safe_name.replace(ch, "_")
    if not safe_name: safe_name = "untitled"
    if not safe_name.lower().endswith(".txt"): safe_name += ".txt"
    return safe_name

def get_default_title_prefix():
    korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
    return korea_now.strftime("%Y-%m-%d_")

# ---------------------------
# 5. UI - 사이드바 (오늘 날짜 필터 적용 및 테마 선택)
# ---------------------------
def render_sidebar(prefix):
    with st.sidebar:
        st.subheader("⚙️ 화면 설정")
        
        # ****** 연속 수정 안내: 다크/기본 모드를 선택할 수 있는 콤보박스 추가
        new_theme = st.selectbox(
            "테마 선택", 
            ["기본 모드", "다크 모드"], 
            index=1 if st.session_state.theme_mode == "다크 모드" else 0,
            key=f"{prefix}_theme_select"
        )
        if new_theme != st.session_state.theme_mode:
            st.session_state.theme_mode = new_theme
            st.rerun()
            
        st.write("") # 간격 띄우기
        
        col1, col2, col3 = st.columns(3)
        if col1.button("A+", use_container_width=True): change_font_scale(0.1); st.rerun()
        if col2.button("A-", use_container_width=True): change_font_scale(-0.1); st.rerun()
        if col3.button("크기 초기화", use_container_width=True): st.session_state.font_scale = 1.0; st.rerun()
        
        st.write("---")
        st.subheader("📁 파일 선택")
        
        today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
        show_today_only = st.checkbox(f"📅 오늘 날짜만 선택 ({today_str})", key=f"{prefix}_today_filter")
        
        categories = get_dynamic_categories()
        if not categories:
            st.error("word_list 폴더를 찾을 수 없습니다.")
            return []
            
        main_cat = st.selectbox("1. 대분류 선택", categories, key=f"{prefix}_main_cat")
        sub_folders = get_subfolders(main_cat)
        
        all_files = []
        if sub_folders:
            selected_subs = st.multiselect("2. 하위 폴더 선택", sub_folders, default=sub_folders, key=f"{prefix}_sub_cat")
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                for f in get_txt_files(path):
                    all_files.append({"path": f"{path}/{f}", "label": f"[{sub}] {f}"})
        else:
            path = f"word_list/{main_cat}"
            for f in get_txt_files(path):
                all_files.append({"path": f"{path}/{f}", "label": f})
                
        if show_today_only:
            filtered = []
            for f in all_files:
                raw_filename = f["label"].split("] ")[-1] if "] " in f["label"] else f["label"]
                if raw_filename.startswith(today_str):
                    filtered.append(f)
            all_files = filtered
                
        if not all_files:
            st.warning("조건에 맞는 txt 파일이 없습니다.")
            return []
            
        file_labels = [f["label"] for f in all_files]
        selected_labels = st.multiselect("3. 파일 선택", file_labels, default=file_labels, key=f"{prefix}_file_select")
        
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
def render_study_part():
    st.header("학습 파트")
    st.caption("💡 단축키: [스페이스바] 다음 단어 / [H] 힌트 보기")
    selected_files = render_sidebar("study")
    
    if st.button("선택한 파일로 학습 시작", use_container_width=True):
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
                if st.button("다음 단어 ⏭️", use_container_width=True):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False
                    st.rerun()
            with c2:
                if st.button("힌트 보기 💡", use_container_width=True, disabled=not has_hint):
                    st.session_state.study_show_hint = True
                    st.rerun()
                    
            st.markdown(f"""
                <div class="study-card">
                    <div class="word-text">{word_data['word']}</div>
                    <div class="meaning-text">{word_data['meaning']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.study_show_hint and has_hint:
                st.markdown(f"<div class='hint-text'><strong>힌트:</strong><br>{word_data['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                
            st.caption(f"진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}")
        else:
            st.success("모든 단어 학습을 완료했습니다!")

# ---------------------------
# 7. UI - 연습 파트 (망각 곡선 적용)
# ---------------------------
def render_practice_part():
    st.header("연습 파트 (망각 곡선 적용)")
    st.caption("단축키: [스페이스바] 정답 / Capslock 이용시 편리 / [H] 힌트 / [Z] 100 / [X] 60 / [C] 40 / [V] 0")
    selected_files = render_sidebar("practice")
    
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
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("정답 확인 👁️", use_container_width=True):
                st.session_state.practice_show_answer = True
                st.rerun()
        with btn2:
            if st.button("힌트 보기 💡", use_container_width=True, disabled=not has_hint):
                st.session_state.practice_show_hint = True
                st.rerun()
                
        s1, s2, s3, s4 = st.columns(4)
        def apply_score(level):
            n = len(st.session_state.practice_queue)
            if level == 60: pos = random.randint(int(n * 0.5), int(n * 0.8)) if n > 1 else 0; st.session_state.practice_queue.insert(pos, cw)
            elif level == 40: pos = random.randint(int(n * 0.2), int(n * 0.4)) if n > 1 else 0; st.session_state.practice_queue.insert(pos, cw)
            elif level == 0: pos = random.randint(max(1, int(n * 0.05)), max(1, int(n * 0.15))) if n > 1 else 0; st.session_state.practice_queue.insert(pos, cw)
            
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

        q_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]
        
        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        
        if st.session_state.practice_show_hint and has_hint:
            st.markdown(f"<div class='hint-text'><strong>힌트:</strong><br>{cw['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_practicing:
        st.success("완벽합니다! 대기열의 모든 연습을 완료했습니다.")

# ---------------------------
# 8. UI - 시험 파트
# ---------------------------
def render_exam_part():
    st.header("시험 파트")
    st.caption("단축키: [스페이스바] 정답 확인 / CapsLock 시 편리 / [Z] O 맞음 / [X] X 틀림")
    selected_files = render_sidebar("exam")
    
    total_words = 0
    if selected_files:
        temp = []
        for f in selected_files:
            text = get_file_content(f["path"])
            temp.extend(parse_word_text(text))
        total_words = len({ (w["word"], w["meaning"], w["hint"]) for w in temp })
    
    if total_words > 0:
        st.write("---")
        st.subheader("⚙️ 출제 개수 설정")
        
        current_val = st.session_state.exam_total_count_input
        if current_val > total_words:
            current_val = total_words
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
                st.session_state.exam_display_side = random.choice([0,1]) if mode == "random" else (0 if mode == "meaning_only" else 1)
            st.rerun()

    if st.session_state.is_examining and st.session_state.current_exam_word:
        cw = st.session_state.current_exam_word
        is_ans_shown = st.session_state.exam_show_answer

        st.write("---")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2.5])
        with c1:
            if st.button("정답 확인", use_container_width=True):
                st.session_state.exam_show_answer = True; st.rerun()
        
        def next_exam(correct=True):
            if correct: st.session_state.exam_correct_count += 1
            else: st.session_state.exam_wrong_count += 1
            
            st.session_state.exam_show_answer = False
            if st.session_state.exam_queue:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                pmode = st.session_state.exam_mode
                st.session_state.exam_display_side = random.choice([0,1]) if pmode == "random" else (0 if pmode == "meaning_only" else 1)
            else:
                st.session_state.current_exam_word = None
                
        with c2:
            if st.button("O (맞음)", disabled=not is_ans_shown, use_container_width=True): next_exam(True); st.rerun()
        with c3:
            if st.button("X (틀림)", disabled=not is_ans_shown, use_container_width=True): next_exam(False); st.rerun()
        with c4:
            st.info(f"진행: {st.session_state.exam_current_number}/{st.session_state.exam_total_count} | 맞음: {st.session_state.exam_correct_count} | 틀림: {st.session_state.exam_wrong_count}")

        q_text = cw["word"] if st.session_state.exam_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.exam_display_side == 0 else cw["word"]

        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_examining:
        st.success(f"시험 종료! 최종 성적: {st.session_state.exam_correct_count} / {st.session_state.exam_total_count}")

# ---------------------------
# 9. UI - 단어장 파트
# ---------------------------
def render_wordbook_part():
    st.header("📁 단어장 관리 (Github 연동)")
    st.caption("새로운 단어장 파일(.txt)을 깃허브 저장소에 업로드합니다.")

    _, top_right = st.columns([5, 1])
    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
            st.success("캐시 새로고침 완료")
            st.rerun()

    categories = get_dynamic_categories()
    if not categories:
        st.error("저장할 폴더 트리를 불러오지 못했습니다.")
        return
        
    c1, c2 = st.columns(2)
    with c1: main_cat = st.selectbox("1. 대분류 선택", categories, key="wb_main_cat")
    with c2: 
        sub_folders = get_subfolders(main_cat)
        sub_cat = st.selectbox("2. 하위 폴더 선택", sub_folders, key="wb_sub_cat") if sub_folders else None

    target_folder = f"word_list/{main_cat}/{sub_cat}" if sub_cat else f"word_list/{main_cat}"
    
    st.write(f"**현재 폴더 구조:** `{target_folder}`")
    with st.expander("현재 폴더에 있는 파일 목록 보기"):
        existing = get_txt_files(target_folder)
        if existing:
            for f in existing: st.write(f"- {f}")
        else:
            st.info("비어 있습니다.")

    st.write("---")
    tab1, tab2 = st.tabs(["✍️ 직접 입력해서 저장", "📄 txt 파일 업로드"])

    with tab1:
        with st.form("manual_wordbook_form"):
            manual_title = st.text_input("파일 제목", value=get_default_title_prefix(), placeholder="예: 2026-07-20_N2_오답노트")
            manual_text = st.text_area("단어장 내용 (단어/뜻/힌트 순서)", height=250, placeholder="단어\n뜻\n이 단어는 이러이러합니다 (힌트)\n\n다음단어\n다음뜻")
            manual_pw = st.text_input("업로드 비밀번호", type="password")
            
            if st.form_submit_button("형식 검사 및 저장", use_container_width=True):
                parsed, errors = parse_words_with_validation(manual_text)
                if errors:
                    st.error("형식 오류가 있습니다. 수정 후 다시 시도하세요.")
                    for err in errors: st.write(f"- {err}")
                elif not parsed:
                    st.warning("저장할 단어가 없습니다.")
                elif manual_pw != str(st.secrets.get("upload_password", "")).strip():
                    st.error("비밀번호가 올바르지 않습니다.")
                else:
                    safe_name = make_safe_filename(manual_title)
                    resp, path = upload_text_to_github(target_folder, safe_name, manual_text)
                    if resp.status_code in [200, 201]:
                        clear_github_cache()
                        st.success(f"성공적으로 업로드되었습니다: {path}")
                    else:
                        st.error(f"저장 실패 (코드: {resp.status_code})")

    with tab2:
        uploaded_file = st.file_uploader("txt 파일 선택", type=["txt"])
        if uploaded_file:
            try:
                up_text = uploaded_file.getvalue().decode("utf-8")
            except:
                up_text = uploaded_file.getvalue().decode("cp949", errors="ignore")
                
            parsed, errors = parse_words_with_validation(up_text)
            if errors:
                st.error("파일 형식 오류 발견!")
                for err in errors[:5]: st.write(f"- {err}")
            else:
                st.success(f"정상 단어 {len(parsed)}개 확인 완료.")
                
            with st.form("upload_txt_form"):
                up_title = st.text_input("저장할 파일명", placeholder="기본적으로 원본 파일명을 사용합니다", value=uploaded_file.name)
                up_pw = st.text_input("업로드 비밀번호", type="password")
                if st.form_submit_button("파일 통째로 저장", use_container_width=True):
                    if errors or not parsed: st.warning("형식을 수정해주세요.")
                    elif up_pw != str(st.secrets.get("upload_password", "")).strip(): st.error("비밀번호 오류.")
                    else:
                        safe_name = make_safe_filename(up_title)
                        resp, path = upload_text_to_github(target_folder, safe_name, up_text)
                        if resp.status_code in [200, 201]:
                            clear_github_cache()
                            st.success(f"업로드 성공: {path}")
                        else:
                            st.error("업로드 실패")

# ---------------------------
# 10. 메인 실행
# ---------------------------
def main():
    init_session_state()
    apply_global_style()
    
    st.title("단어 암기 프로그램")
    
    page = st.radio("파트 이동", ["학습", "연습 (망각곡선 적용)", "시험", "단어장 추가"], horizontal=True, label_visibility="collapsed")
    
    if page == "학습":
        render_study_part()
    elif page == "연습 (망각곡선 적용)":
        render_practice_part()
    elif page == "시험":
        render_exam_part()
    elif page == "단어장 추가":
        render_wordbook_part()
        
    # 페이지 하단에서 자바스크립트(단축키) 주입
    inject_keyboard_shortcuts()

if __name__ == "__main__":
    main()