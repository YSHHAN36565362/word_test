import streamlit as st
import streamlit.components.v1 as components
import random
import requests
import base64
import re
import calendar
from datetime import datetime, date
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
# 초보자를 위한 주석: 프로그램이 기억하고 있어야 할 변수(데이터)들의 기본값을 설정하는 곳입니다.
def init_session_state():
    defaults = {
        "words": [],
        "loaded_words_snapshot": [],
        
        # * 변경점: 현재 학습하기 위해 불러온 파일들의 이름을 저장하는 공간을 만들었습니다. (요청사항 4번)
        "current_loaded_files": [],

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
        
        # ** 변경점: 추가 기능 - 시험 파트에서 틀린 단어들을 모아둘 오답 노트 리스트입니다.
        "exam_wrong_list": [],

        "font_scale": 1.0,
        "theme_mode": "다크 모드",
        
        "script_lines": [],
        "script_index": 0,
        "is_scripting": False,
        "cal_selected_dates": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ---------------------------
# 2. 글로벌 CSS 스타일 및 키보드 단축키 스크립트
# ---------------------------
# 초보자를 위한 주석: 화면의 디자인(색상, 글씨 크기, 모바일 화면 맞춤 등)을 담당하는 함수입니다.
def apply_global_style():
    scale = st.session_state.font_scale
    base = int(16 * scale)
    large = int(24 * scale)
    huge = int(40 * scale)
    
    is_dark = (st.session_state.theme_mode == "다크 모드")
    
    card_bg = "#262730" if is_dark else "#f8f9fa"
    text_color = "#ffffff" if is_dark else "#000000"
    word_color = "#4db8ff" if is_dark else "#1f77b4"
    hint_bg = "#3a3b40" if is_dark else "#e9ecef"   
    hint_text = "#eeeeee" if is_dark else "#333333"  
    ans_color = "#45c95c" if is_dark else "#2ca02c"
    shadow_color = "rgba(0,0,0,0.5)" if is_dark else "rgba(0,0,0,0.1)"
    
    st.markdown(f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{ font-size: {base}px !important; }}
        p, li, div, span {{ font-size: {base}px; }}
        
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
        .script-text {{ font-size: {large}px !important; font-weight: bold; color: {word_color}; text-align: left; padding: 15px; line-height: 1.8; }}
        
        .test-question {{ font-size: {huge}px !important; color: {text_color}; text-align: center; padding: 30px 10px; font-weight: bold; }}
        .test-answer {{ font-size: {large}px !important; text-align: center; color: {ans_color}; font-weight: bold; margin-bottom: 20px; }}
        
        div[data-testid="stButton"] > button {{ font-size: {base}px !important; font-weight: 600 !important; }}
        
        /* * 변경점: (요청사항 1, 2번) 모바일 환경에서 박스 최적화 및 긴 파일명 줄바꿈 허용 CSS 추가 */
        @media (max-width: 640px) {{
            /* 가로로 강제 정렬하여 화면을 벗어나게 만들던 속성을 제거하고, 화면 크기에 맞게 자동으로 위아래로 떨어지게(wrap) 수정했습니다. */
            div[data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
            }}
        }}

        /* 2. 최종 파일 선택 박스에서 파일명이 너무 길면 ...으로 잘리는 것을 방지하고, 텍스트가 박스 안에서 여러 줄로 다 보이도록 합니다. */
        div[data-baseweb="select"] span {{
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            line-height: 1.4 !important;
        }}
        /* 선택된 파일 태그(회색 배경) 내부 글자도 길면 아래로 자연스럽게 늘어나게 합니다. */
        span[data-baseweb="tag"] {{
            height: auto !important;
            max-width: 100% !important;
        }}
        </style>
    """, unsafe_allow_html=True)

def inject_keyboard_shortcuts():
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
        "message": f"Add file: {repo_path}",
        "content": content_b64,
        "branch": branch
    }
    
    response = requests.put(url, headers=get_github_headers(), json=payload, timeout=30)
    return response, repo_path

def clear_github_cache():
    st.cache_data.clear()

# ---------------------------
# 4. 단어 파싱 / 지문 파싱 유틸
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

def parse_script_text(text):
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    return [line.strip() for line in lines if line.strip()]

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
# 5. UI - 사이드바 및 공통 함수
# ---------------------------
def render_sidebar(prefix):
    with st.sidebar:
        st.subheader("⚙️ 화면 설정")
        new_theme = st.selectbox("테마 선택", ["기본 모드", "다크 모드"], index=1 if st.session_state.theme_mode == "다크 모드" else 0, key=f"{prefix}_theme_select")
        if new_theme != st.session_state.theme_mode:
            st.session_state.theme_mode = new_theme
            st.rerun()
            
        col1, col2, col3 = st.columns(3)
        if col1.button("A+", use_container_width=True): change_font_scale(0.1); st.rerun()
        if col2.button("A-", use_container_width=True): change_font_scale(-0.1); st.rerun()
        if col3.button("초기화", use_container_width=True): st.session_state.font_scale = 1.0; st.rerun()
        
        st.write("---")
        st.subheader("📁 학습 자료 선택")
        
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
                
        available_dates = {}
        for f in all_files:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", f["label"])
            if match:
                try:
                    dt = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                    available_dates.setdefault(dt, []).append(f)
                except ValueError:
                    pass

        st.write("---")
        st.write("🗓️ **달력에서 특정 날짜 파일 찾기**")
        
        today_date = datetime.now(ZoneInfo("Asia/Seoul")).date()
        cal_y_key = f"{prefix}_cal_y"
        cal_m_key = f"{prefix}_cal_m"
        if cal_y_key not in st.session_state: st.session_state[cal_y_key] = today_date.year
        if cal_m_key not in st.session_state: st.session_state[cal_m_key] = today_date.month
        
        c_y, c_m = st.columns(2)
        with c_y: st.session_state[cal_y_key] = st.selectbox("연도", range(2023, 2031), index=range(2023, 2031).index(st.session_state[cal_y_key]), key=f"{prefix}_y_box")
        with c_m: st.session_state[cal_m_key] = st.selectbox("월", range(1, 13), index=range(1, 13).index(st.session_state[cal_m_key]), key=f"{prefix}_m_box")
        
        y = st.session_state[cal_y_key]
        m = st.session_state[cal_m_key]
        
        cal = calendar.monthcalendar(y, m)
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        
        w_cols = st.columns(7)
        for i, wd in enumerate(weekdays): w_cols[i].markdown(f"**{wd}**")
        
        for week in cal:
            d_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    d_cols[i].write("")
                else:
                    dt = date(y, m, day)
                    if dt in available_dates:
                        chk_key = f"{prefix}_cal_chk_{dt}"
                        checked = st.session_state.cal_selected_dates.get(chk_key, False)
                        new_checked = d_cols[i].checkbox(str(day), value=checked, key=chk_key)
                        st.session_state.cal_selected_dates[chk_key] = new_checked
                    else:
                        d_cols[i].markdown(f"<span style='color:gray;'>{day}</span>", unsafe_allow_html=True)
                        
        if st.button("달력 선택 모두 해제", use_container_width=True, key=f"{prefix}_clear_cal"):
            st.session_state.cal_selected_dates.clear()
            st.rerun()

        selected_cal_files = []
        for dt, files in available_dates.items():
            if st.session_state.cal_selected_dates.get(f"{prefix}_cal_chk_{dt}", False):
                selected_cal_files.extend(files)
                
        if show_today_only or selected_cal_files:
            filtered = []
            if show_today_only:
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
        selected_labels = st.multiselect("3. 최종 파일 확인 및 선택", file_labels, default=file_labels, key=f"{prefix}_file_select")
        
        return [f for f in all_files if f["label"] in selected_labels]

def load_data(selected_files, is_script=False):
    if not selected_files:
        st.warning("사이드바에서 파일을 선택해주세요.")
        return False
        
    merged = []
    # * 변경점: 데이터를 성공적으로 불러오면 현재 파일 이름들을 세션에 저장해둡니다. (요청사항 4번 처리용)
    st.session_state.current_loaded_files = [f["label"] for f in selected_files]

    for f in selected_files:
        text = get_file_content(f["path"])
        if is_script:
            merged.extend(parse_script_text(text))
        else:
            merged.extend(parse_word_text(text))
        
    if is_script:
        st.session_state.script_lines = merged
    else:
        random.shuffle(merged)
        st.session_state.words = merged
    return True

# * 변경점: 현재 실행 중인 파일을 예쁘게 출력해주는 공통 함수를 만들었습니다. (요청사항 4번 반영)
def display_current_loaded_files_info():
    files = st.session_state.get("current_loaded_files", [])
    if files:
        if len(files) == 1:
            st.info(f"📂 **현재 학습 중인 파일:** {files[0]}")
        else:
            st.info(f"📂 **현재 학습 중인 파일:** {files[0]} 외 {len(files) - 1}건")

# ---------------------------
# 6. UI - 학습 파트
# ---------------------------
def render_study_part():
    st.header("📖 학습 파트")
    st.caption("💡 단축키: [스페이스바] 다음 단어 / [H] 힌트 보기")
    selected_files = render_sidebar("study")
    
    # * 변경점: 학습 파트 상단에 현재 파일 정보를 출력합니다.
    display_current_loaded_files_info()

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
                st.markdown(f"<div class='hint-text'><strong>💡 힌트:</strong><br>{word_data['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                
            st.caption(f"진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}")
        else:
            st.success("모든 단어 학습을 완료했습니다!")

# ---------------------------
# 7. UI - 연습 파트
# ---------------------------
def render_practice_part():
    st.header("📝 연습 파트 (망각 곡선 적용)")
    st.caption("단축키: [스페이스바] 정답 / [H] 힌트 / [Z] 100 / [X] 60 / [C] 40 / [V] 0")
    selected_files = render_sidebar("practice")
    
    # * 변경점: 연습 파트 상단에 현재 파일 정보를 출력합니다.
    display_current_loaded_files_info()

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
            if st.button("정답 확인", use_container_width=True):
                st.session_state.practice_show_answer = True; st.rerun()
        with btn2:
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint):
                st.session_state.practice_show_hint = True; st.rerun()
                
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
        
        # * 변경점: 정답 확인 시 힌트도 자동으로 함께 표시되도록 수정했습니다. (요청사항 5번)
        if st.session_state.practice_show_hint or (is_ans_shown and has_hint):
            st.markdown(f"<div class='hint-text'><strong>💡 힌트:</strong><br>{cw['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)

    elif st.session_state.is_practicing:
        st.success("완벽합니다! 대기열의 모든 연습을 완료했습니다.")

# ---------------------------
# 8. UI - 시험 파트
# ---------------------------
def render_exam_part():
    st.header("🎯 시험 파트")
    st.caption("단축키: [스페이스바] 정답 확인 / [Z] O 맞음 / [X] X 틀림")
    selected_files = render_sidebar("exam")
    
    # * 변경점: 시험 파트 상단에 현재 파일 정보를 출력합니다.
    display_current_loaded_files_info()

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
            # ** 변경점: 시험을 새로 시작할 때 오답 노트를 초기화합니다.
            st.session_state.exam_wrong_list = []
            
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
            if correct: 
                st.session_state.exam_correct_count += 1
            else: 
                st.session_state.exam_wrong_count += 1
                # ** 변경점: 틀린 문제일 경우 오답 노트 리스트에 추가합니다.
                st.session_state.exam_wrong_list.append(cw)
            
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
        has_hint = bool(cw.get("hint", "").strip())

        st.markdown(f"<div class='study-card'><div class='test-question'>Q: {q_text}</div></div>", unsafe_allow_html=True)
        
        if is_ans_shown:
            st.markdown(f"<div class='test-answer'>정답: {a_text}</div>", unsafe_allow_html=True)
            # * 변경점: 시험 파트에서도 정답 확인 시 힌트가 있으면 함께 띄워줍니다. (요청사항 5번)
            if has_hint:
                st.markdown(f"<div class='hint-text'><strong>💡 힌트:</strong><br>{cw['hint'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    elif st.session_state.is_examining:
        st.success(f"시험 종료! 최종 성적: {st.session_state.exam_correct_count} / {st.session_state.exam_total_count}")
        # ** 변경점: (보너스 기능) 시험이 끝나면 오답 노트를 화면에 보여주어 스스로 복습할 수 있게 합니다.
        if st.session_state.get("exam_wrong_list"):
            st.error("📝 오답 노트 (아래 단어들을 다시 한번 외워보세요!)")
            for wrong_word in st.session_state.exam_wrong_list:
                st.write(f"- **{wrong_word['word']}** : {wrong_word['meaning']}")

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
            manual_title = st.text_input("파일 제목", value=get_default_title_prefix(), placeholder="예: 2026-07-20_N2")
            manual_text = st.text_area("단어/뜻/힌트 순서", height=250)
            manual_pw = st.text_input("업로드 비밀번호", type="password")
            if st.form_submit_button("저장", use_container_width=True):
                if manual_pw != str(st.secrets.get("upload_password", "")).strip():
                    st.error("비밀번호 오류.")
                else:
                    safe_name = make_safe_filename(manual_title)
                    resp, path = upload_text_to_github(target_folder, safe_name, manual_text)
                    if resp.status_code in [200, 201]:
                        clear_github_cache(); st.success(f"업로드 완료: {path}")

    with tab2:
        uploaded_file = st.file_uploader("txt 파일 선택", type=["txt"])
        if uploaded_file:
            up_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            with st.form("upload_txt_form"):
                up_title = st.text_input("파일명", value=uploaded_file.name)
                up_pw = st.text_input("비밀번호", type="password")
                if st.form_submit_button("저장", use_container_width=True):
                    if up_pw != str(st.secrets.get("upload_password", "")).strip(): st.error("비밀번호 오류.")
                    else:
                        safe_name = make_safe_filename(up_title)
                        resp, path = upload_text_to_github(target_folder, safe_name, up_text)
                        if resp.status_code in [200, 201]:
                            clear_github_cache(); st.success(f"업로드 완료: {path}")

# ---------------------------
# 10. UI - 지문 한 줄 외우기 파트
# ---------------------------
def render_script_part():
    st.header("🗣️ 지문 한 줄 외우기")
    st.caption("대화 및 지문을 순서대로 연상하며 외웁니다. (단축키: [스페이스바] 다음 문장)")
    selected_files = render_sidebar("script")
    
    # * 변경점: 지문 외우기 파트 상단에 현재 파일 정보를 출력합니다.
    display_current_loaded_files_info()

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
            
            st.caption(f"진행 상황: {st.session_state.script_index + 1} / {len(st.session_state.script_lines)}")
        else:
            st.success("🎉 모든 대본/지문 학습을 완료했습니다!")
            if st.button("⏪ 다시 처음부터", use_container_width=True):
                st.session_state.script_index = 0
                st.rerun()

# ---------------------------
# 11. 메인 실행
# ---------------------------
def main():
    init_session_state()
    apply_global_style()
    
    st.title("단어 암기 프로그램")
    
    page = st.radio("파트 이동", ["학습", "연습", "시험", "단어장 추가", "지문 외우기"], horizontal=True, label_visibility="collapsed")
    
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
