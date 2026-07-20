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

        "selected_labels_study": [],
        "selected_labels_practice": [],
        "selected_labels_exam": [],

        "calendar_year_study": now.year,
        "calendar_month_study": now.month,
        "calendar_selected_dates_study": [],

        "calendar_year_practice": now.year,
        "calendar_month_practice": now.month,
        "calendar_selected_dates_practice": [],

        "calendar_year_exam": now.year,
        "calendar_month_exam": now.month,
        "calendar_selected_dates_exam": [],

        "study_japanese_mode": "단일 등급",
        "practice_japanese_mode": "단일 등급",
        "exam_japanese_mode": "단일 등급",

        "study_japanese_level_single": "N2",
        "practice_japanese_level_single": "N2",
        "exam_japanese_level_single": "N2",

        "study_japanese_level_multi": ["N2", "N3", "N4~N5"],
        "practice_japanese_level_multi": ["N2", "N3", "N4~N5"],
        "exam_japanese_level_multi": ["N2", "N3", "N4~N5"],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def keep_session_keys():
    protected_keys = [
        "words",
        "loaded_words_snapshot",
        "study_index",
        "is_studying",
        "study_show_hint",
        "practice_queue",
        "practice_queue_snapshot",
        "current_practice_word",
        "is_practicing",
        "practice_display_side",
        "practice_mode",
        "show_answer",
        "practice_show_hint",
        "exam_show_answer",
        "exam_queue",
        "exam_source_words",
        "current_exam_word",
        "is_examining",
        "exam_mode",
        "exam_total_count",
        "exam_current_number",
        "exam_correct_count",
        "exam_wrong_count",
        "exam_display_side",
        "exam_total_count_input",
        "font_scale",
        "button_scale",
        "big_button_mode",
        "selected_labels_study",
        "selected_labels_practice",
        "selected_labels_exam",
        "calendar_year_study",
        "calendar_month_study",
        "calendar_selected_dates_study",
        "calendar_year_practice",
        "calendar_month_practice",
        "calendar_selected_dates_practice",
        "calendar_year_exam",
        "calendar_month_exam",
        "calendar_selected_dates_exam",
        "study_japanese_mode",
        "practice_japanese_mode",
        "exam_japanese_mode",
        "study_japanese_level_single",
        "practice_japanese_level_single",
        "exam_japanese_level_single",
        "study_japanese_level_multi",
        "practice_japanese_level_multi",
        "exam_japanese_level_multi",
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
        html, body, [data-testid="stAppViewContainer"] {{
            font-size: {base_font}px !important;
        }}
        p, li, label, div, span {{
            font-size: {base_font}px;
        }}
        .study-word {{
            font-size: {large_font}px !important;
            line-height: 1.5;
            word-break: keep-all;
            margin-bottom: 0.5rem;
        }}
        .practice-question {{
            font-size: {question_font}px !important;
            text-align: center;
            padding: 20px;
            line-height: 1.5;
            word-break: keep-all;
        }}
        .practice-answer {{
            font-size: {answer_font}px !important;
            text-align: center;
            color: gray;
            padding: 10px;
            line-height: 1.5;
            word-break: keep-all;
        }}
        .exam-question {{
            font-size: {exam_question_font}px !important;
            text-align: center;
            padding: 28px;
            line-height: 1.5;
            word-break: keep-all;
        }}
        .exam-answer {{
            font-size: {answer_font}px !important;
            text-align: center;
            color: gray;
            padding: 12px;
            line-height: 1.5;
            word-break: keep-all;
        }}
        .under-card-controls {{
            margin-top: 0.8rem;
            margin-bottom: 1.2rem;
        }}
        .under-card-help {{
            font-size: {small_font}px !important;
            color: #666;
        }}
        div[data-testid="stButton"] > button,
        .stFormSubmitButton > button {{
            min-height: {button_height}px !important;
            font-size: {button_font}px !important;
            font-weight: 700 !important;
            border-radius: 12px !important;
            padding-top: 0.6rem !important;
            padding-bottom: 0.6rem !important;
        }}
        div[data-baseweb="select"] * {{
            font-size: {input_font}px !important;
        }}
        input, textarea, [data-testid="stNumberInput"] input {{
            font-size: {input_font}px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_under_card_view_controls(unique_prefix):
    st.markdown("<div class='under-card-controls'>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1.3, 2.4])
    with c1:
        if st.button("+", key=f"{unique_prefix}_font_plus_btn", use_container_width=True):
            increase_font_scale()
            st.rerun()
    with c2:
        if st.button("-", key=f"{unique_prefix}_font_minus_btn", use_container_width=True):
            decrease_font_scale()
            st.rerun()
    with c3:
        if st.button("기본", key=f"{unique_prefix}_font_reset_btn", use_container_width=True):
            reset_font_scale()
            st.rerun()
    with c4:
        if st.button("큰 버튼 모드", key=f"{unique_prefix}_big_button_toggle_btn", use_container_width=True):
            toggle_big_button_mode()
            st.rerun()

    mode_text = "켜짐" if st.session_state.big_button_mode else "꺼짐"
    st.markdown(
        f"<div class='under-card-help'>글자 {int(st.session_state.font_scale * 100)}% / 버튼 {int(st.session_state.button_scale * 100)}% / 큰 버튼 {mode_text}</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Parsing
# ---------------------------
def parse_word_text(text):
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
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) >= 2:
                word = block[0]
                meaning = block[1]
                hint = "\n".join(block[2:])
                if word and meaning:
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    return parsed_words


def parse_words_with_validation(text):
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
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
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
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

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
    return korea_now.strftime("%Y-%m-%d_")


def extract_iso_date_from_filename(filename):
    name = filename.rsplit("/", 1)[-1]
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def is_dated_file(filename):
    return extract_iso_date_from_filename(filename) is not None


def split_required_and_dated_files(files):
    required_files = []
    dated_files = []

    for f in files:
        if is_dated_file(f):
            dated_files.append(f)
        else:
            required_files.append(f)

    required_files.sort()
    dated_files.sort()
    return required_files, dated_files


def deduplicate_words(words):
    seen = set()
    result = []

    for item in words:
        key = (
            item.get("word", "").strip(),
            item.get("meaning", "").strip(),
            item.get("hint", "").strip()
        )
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def monday_of_week(target_date):
    return target_date - timedelta(days=target_date.weekday())


def sunday_of_week(target_date):
    return monday_of_week(target_date) + timedelta(days=6)


def get_this_week_range():
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    return monday_of_week(today), sunday_of_week(today)


def get_last_week_range():
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    this_monday = monday_of_week(today)
    last_sunday = this_monday - timedelta(days=1)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday, last_sunday


def get_this_month_range():
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    start = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end = date(today.year, today.month, last_day)
    return start, end


def filter_dated_files_by_range(dated_files, start_date, end_date):
    result = []
    for f in dated_files:
        dt = extract_iso_date_from_filename(f)
        if dt and start_date <= dt <= end_date:
            result.append(f)
    return sorted(result)


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
    owner, repo, branch = get_repo_info()
    encoded_path = encode_github_path(path)
    encoded_branch = quote(branch, safe="")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded_path}?ref={encoded_branch}"
    response = requests.get(url, headers=get_github_headers(), timeout=30)
    return response.status_code, response.json() if response.content else {}


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
# Folder / file UI
# ---------------------------
def get_main_category_options():
    return ["IT", "Japanese"]


def get_japanese_level_options():
    return ["N2", "N3", "N4~N5"]


def render_folder_picker(prefix):
    st.write("### 학습할 폴더 선택" if prefix == "study" else "### 폴더 선택")

    main_category = st.selectbox(
        "대분류 선택",
        get_main_category_options(),
        key=f"{prefix}_main_category_widget"
    )

    folder_list = []
    if main_category == "IT":
        folder_list = ["word_list/IT"]
    else:
        mode = st.radio(
            "일본어 폴더 선택 방식",
            ["단일 등급", "통합 선택"],
            key=f"{prefix}_japanese_mode",
            horizontal=True
        )

        if mode == "단일 등급":
            selected_level = st.selectbox(
                "일본어 등급 선택",
                get_japanese_level_options(),
                key=f"{prefix}_japanese_level_single"
            )
            folder_list = [f"word_list/Japanese/{selected_level}"]
        else:
            selected_levels = st.multiselect(
                "여러 등급 폴더 선택",
                options=get_japanese_level_options(),
                default=st.session_state[f"{prefix}_japanese_level_multi"],
                key=f"{prefix}_japanese_level_multi"
            )
            folder_list = [f"word_list/Japanese/{lv}" for lv in selected_levels]

    if folder_list:
        st.caption("선택된 폴더")
        for fp in folder_list:
            st.write(f"- {fp}")

    return folder_list, main_category


def get_merged_items(folder_list):
    merged_items = []
    errors = []

    for folder_path in folder_list:
        files, err = get_github_txt_files(folder_path)
        if err:
            errors.append(err)
        else:
            for f in files:
                merged_items.append({
                    "folder": folder_path,
                    "file": f,
                    "label": f"[{folder_path.split('/')[-1]}] {f}"
                })

    return merged_items, errors


def get_selected_labels(prefix):
    return set(st.session_state.get(f"selected_labels_{prefix}", []))


def set_selected_labels(prefix, labels):
    st.session_state[f"selected_labels_{prefix}"] = sorted(set(labels))


def clear_all_selection(prefix):
    set_selected_labels(prefix, [])
    st.session_state[f"calendar_selected_dates_{prefix}"] = []


def select_all_from_labels(prefix, labels):
    current = get_selected_labels(prefix)
    current.update(labels)
    set_selected_labels(prefix, current)


def remove_labels(prefix, labels):
    current = get_selected_labels(prefix)
    for label in labels:
        current.discard(label)
    set_selected_labels(prefix, current)


def apply_quick_date_selection(prefix, dated_labels, label_to_item, range_type):
    dated_real_files = [label_to_item[label]["file"] for label in dated_labels]

    if range_type == "this_week":
        start_d, end_d = get_this_week_range()
    elif range_type == "last_week":
        start_d, end_d = get_last_week_range()
    else:
        start_d, end_d = get_this_month_range()

    files = filter_dated_files_by_range(dated_real_files, start_d, end_d)
    selected_set = set(files)
    applied_labels = [label for label in dated_labels if label_to_item[label]["file"] in selected_set]

    current = get_selected_labels(prefix)
    for label in dated_labels:
        current.discard(label)
    current.update(applied_labels)
    set_selected_labels(prefix, current)

    st.session_state[f"calendar_selected_dates_{prefix}"] = sorted(
        {extract_iso_date_from_filename(f) for f in files if extract_iso_date_from_filename(f)}
    )


def get_calendar_selected_files(dated_real_files, prefix):
    year_key = f"calendar_year_{prefix}"
    month_key = f"calendar_month_{prefix}"
    selected_dates_key = f"calendar_selected_dates_{prefix}"

    file_date_map = {}
    all_dates = []

    for f in dated_real_files:
        dt = extract_iso_date_from_filename(f)
        if dt:
            file_date_map.setdefault(dt, []).append(f)
            all_dates.append(dt)

    if not all_dates:
        st.info("날짜 파일이 없어 캘린더를 표시하지 않습니다.")
        return []

    available_years = sorted({d.year for d in all_dates})
    if st.session_state[year_key] not in available_years:
        st.session_state[year_key] = available_years[0]

    months_for_year = sorted({d.month for d in all_dates if d.year == st.session_state[year_key]})
    if months_for_year and st.session_state[month_key] not in months_for_year:
        st.session_state[month_key] = months_for_year[0]

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("연도", available_years, key=year_key)
    with c2:
        months_for_year = sorted({d.month for d in all_dates if d.year == st.session_state[year_key]})
        st.selectbox("월", months_for_year, key=month_key)

    year = st.session_state[year_key]
    month = st.session_state[month_key]

    st.write("#### 날짜 선택")

    month_dates = sorted([d for d in all_dates if d.year == year and d.month == month])

    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    head_cols = st.columns(7)
    for idx, wd in enumerate(weekday_names):
        with head_cols[idx]:
            st.markdown(f"**{wd}**")

    cal = calendar.monthcalendar(year, month)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.write("")
                else:
                    current_date = date(year, month, day)
                    has_file = current_date in file_date_map
                    checked = current_date in st.session_state[selected_dates_key]

                    if has_file:
                        new_value = st.checkbox(
                            f"{day}",
                            value=checked,
                            key=f"{prefix}_calendar_day_{year}_{month}_{day}"
                        )
                        if new_value and current_date not in st.session_state[selected_dates_key]:
                            st.session_state[selected_dates_key].append(current_date)
                        elif (not new_value) and current_date in st.session_state[selected_dates_key]:
                            st.session_state[selected_dates_key].remove(current_date)
                    else:
                        st.markdown(f"<span style='color:#bbb'>{day}</span>", unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("이 달 전체 선택", key=f"{prefix}_select_month_btn", use_container_width=True):
            st.session_state[selected_dates_key] = month_dates
            st.rerun()
    with b2:
        if st.button("날짜 선택 해제", key=f"{prefix}_clear_month_btn", use_container_width=True):
            st.session_state[selected_dates_key] = []
            st.rerun()

    selected_files = []
    for dt in st.session_state[selected_dates_key]:
        selected_files.extend(file_date_map.get(dt, []))

    return sorted(set(selected_files))


def render_checkbox_file_group(title, labels, prefix, group_name):
    st.write(f"### {title}")

    if not labels:
        st.info("선택 가능한 파일이 없습니다.")
        return

    current_selected = get_selected_labels(prefix)

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"{title} 전체 선택", key=f"{prefix}_{group_name}_all_btn", use_container_width=True):
            select_all_from_labels(prefix, labels)
            st.rerun()
    with c2:
        if st.button(f"{title} 선택 해제", key=f"{prefix}_{group_name}_clear_btn", use_container_width=True):
            remove_labels(prefix, labels)
            st.rerun()

    for label in labels:
        checked = label in current_selected
        new_checked = st.checkbox(
            label,
            value=checked,
            key=f"{prefix}_{group_name}_chk_{label}"
        )

        if new_checked != checked:
            updated = get_selected_labels(prefix)
            if new_checked:
                updated.add(label)
            else:
                updated.discard(label)
            set_selected_labels(prefix, updated)
            st.rerun()


def render_file_selector_section(folder_list, prefix, main_category):
    merged_items, errors = get_merged_items(folder_list)

    if errors:
        for err in errors:
            st.error(err)

    if not merged_items:
        st.warning("선택한 폴더에 txt 파일이 없습니다.")
        return []

    label_to_item = {item["label"]: item for item in merged_items}
    raw_files = [item["file"] for item in merged_items]
    required_files, dated_files = split_required_and_dated_files(raw_files)

    required_labels = [item["label"] for item in merged_items if item["file"] in required_files]
    dated_labels = [item["label"] for item in merged_items if item["file"] in dated_files]
    dated_real_files = [label_to_item[label]["file"] for label in dated_labels]

    if main_category == "Japanese":
        render_checkbox_file_group("핵심 단어", required_labels, prefix, "required")
        render_checkbox_file_group("날짜 파일", dated_labels, prefix, "dated")

        with st.expander("빠른 날짜 선택 / 캘린더"):
            q1, q2, q3, q4 = st.columns(4)

            with q1:
                if st.button("이번 주", key=f"{prefix}_quick_this_week", use_container_width=True):
                    apply_quick_date_selection(prefix, dated_labels, label_to_item, "this_week")
                    st.rerun()
            with q2:
                if st.button("지난 주", key=f"{prefix}_quick_last_week", use_container_width=True):
                    apply_quick_date_selection(prefix, dated_labels, label_to_item, "last_week")
                    st.rerun()
            with q3:
                if st.button("이번 달", key=f"{prefix}_quick_this_month", use_container_width=True):
                    apply_quick_date_selection(prefix, dated_labels, label_to_item, "this_month")
                    st.rerun()
            with q4:
                if st.button("빠른 선택 해제", key=f"{prefix}_quick_clear", use_container_width=True):
                    remove_labels(prefix, dated_labels)
                    st.session_state[f"calendar_selected_dates_{prefix}"] = []
                    st.rerun()

            calendar_selected_files = get_calendar_selected_files(dated_real_files, prefix)

            if st.button("캘린더 선택 반영", key=f"{prefix}_calendar_apply_btn", use_container_width=True):
                selected_set = set(calendar_selected_files)
                applied_labels = [label for label in dated_labels if label_to_item[label]["file"] in selected_set]

                current = get_selected_labels(prefix)
                for label in dated_labels:
                    current.discard(label)
                current.update(applied_labels)
                set_selected_labels(prefix, current)
                st.rerun()
    else:
        render_checkbox_file_group("파일", [item["label"] for item in merged_items], prefix, "allfiles")

    selected_now_labels = get_selected_labels(prefix)
    selected_items = [label_to_item[label] for label in selected_now_labels if label in label_to_item]

    if selected_items:
        st.caption(f"현재 선택된 파일 수: {len(selected_items)}개")
    else:
        st.caption("현재 선택된 파일이 없습니다.")

    return selected_items


# ---------------------------
# Load / merge words
# ---------------------------
def load_words_from_multiple_github_files(selected_items):
    merged_words = []

    for item in selected_items:
        repo_file_path = f"{item['folder']}/{item['file']}"
        text = get_github_file_text(repo_file_path)
        parsed = parse_word_text(text)
        merged_words.extend(parsed)

    merged_words = deduplicate_words(merged_words)
    random.shuffle(merged_words)
    return merged_words


def save_loaded_words(words):
    st.session_state.words = list(words)
    st.session_state.loaded_words_snapshot = list(words)


# ---------------------------
# Study / Practice / Exam logic
# ---------------------------
def load_first_practice_word():
    if len(st.session_state.practice_queue) > 0:
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
        st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)
        set_next_practice_display_side()
    else:
        st.session_state.current_practice_word = None
        st.session_state.practice_queue_snapshot = []


def start_practice(mode):
    if len(st.session_state.words) == 0:
        st.warning("먼저 파일을 선택해 주세요.")
        return

    st.session_state.practice_mode = mode

    if len(st.session_state.practice_queue) == 0 and st.session_state.current_practice_word is None:
        st.session_state.practice_queue = list(st.session_state.words)
        st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)

    st.session_state.is_practicing = True
    st.session_state.show_answer = False
    st.session_state.practice_show_hint = False
    load_first_practice_word()


def reset_exam_state():
    st.session_state.is_examining = False
    st.session_state.exam_mode = None
    st.session_state.exam_queue = []
    st.session_state.current_exam_word = None
    st.session_state.exam_current_number = 0
    st.session_state.exam_correct_count = 0
    st.session_state.exam_wrong_count = 0
    st.session_state.exam_show_answer = False
    st.session_state.exam_display_side = 0


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
    st.session_state.show_answer = False
    st.session_state.practice_show_hint = False

    if len(st.session_state.practice_queue) > 0:
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
        st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)
        set_next_practice_display_side()
    else:
        st.session_state.current_practice_word = None
        st.session_state.practice_queue_snapshot = []


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

    st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)
    move_to_next_practice_word()


def load_and_start_study(selected_items):
    if not selected_items:
        st.warning("먼저 파일을 하나 이상 선택해 주세요.")
        return False

    loaded = load_words_from_multiple_github_files(selected_items)
    save_loaded_words(loaded)
    st.session_state.study_index = 0
    st.session_state.is_studying = True
    st.session_state.study_show_hint = False
    return True


def load_and_start_practice(selected_items, mode):
    if not selected_items:
        st.warning("먼저 파일을 하나 이상 선택해 주세요.")
        return False

    loaded = load_words_from_multiple_github_files(selected_items)
    save_loaded_words(loaded)
    st.session_state.practice_queue = list(st.session_state.words)
    st.session_state.practice_queue_snapshot = list(st.session_state.practice_queue)
    st.session_state.is_practicing = False
    st.session_state.current_practice_word = None
    st.session_state.show_answer = False
    st.session_state.practice_show_hint = False
    start_practice(mode)
    return True


def load_and_start_exam(selected_items, mode):
    if not selected_items:
        st.warning("먼저 파일을 하나 이상 선택해 주세요.")
        return False

    loaded_words = load_words_from_multiple_github_files(selected_items)
    save_loaded_words(loaded_words)
    st.session_state.exam_source_words = list(loaded_words)
    reset_exam_state()
    st.session_state.exam_total_count_input = min(
        max(1, len(st.session_state.exam_source_words)),
        st.session_state.exam_total_count_input
    )
    start_exam(mode)
    return True


# ---------------------------
# UI Parts
# ---------------------------
def render_study_part():
    st.header("학습 파트")

    top_controls = st.container()
    card_container = st.container()
    under_card_container = st.container()
    selector_container = st.container()

    with top_controls:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("다음", key="study_next_btn_top", use_container_width=True):
                if st.session_state.is_studying and st.session_state.study_index < len(st.session_state.words):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False
                    st.rerun()
        with c2:
            current_hint_exists = False
            if st.session_state.is_studying and st.session_state.study_index < len(st.session_state.words):
                current_hint_exists = bool(st.session_state.words[st.session_state.study_index].get("hint", "").strip())

            if st.button("힌트 보기", key="study_hint_btn_top", use_container_width=True, disabled=not current_hint_exists):
                st.session_state.study_show_hint = True
                st.rerun()

    with card_container:
        if len(st.session_state.words) > 0 and st.session_state.is_studying and st.session_state.study_index < len(st.session_state.words):
            current_word = st.session_state.words[st.session_state.study_index]
            st.markdown(f"<div class='study-word'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='study-word'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)

            if st.session_state.study_show_hint and current_word.get("hint", "").strip():
                st.info(f"힌트:\n{current_word['hint']}")
        elif st.session_state.is_studying and st.session_state.study_index >= len(st.session_state.words):
            st.success("모두 학습했습니다.")
        else:
            st.info("아래에서 파일을 선택하고 학습하기를 누르세요.")

    with under_card_container:
        render_under_card_view_controls("study")

    with selector_container:
        folder_list, main_category = render_folder_picker("study")
        selected_items = []
        if folder_list:
            selected_items = render_file_selector_section(folder_list, "study", main_category)

        if st.button("학습하기", key="study_start_only_btn", use_container_width=True):
            ok = load_and_start_study(selected_items)
            if ok:
                st.rerun()


def render_practice_part():
    st.header("연습 파트")

    card_container = st.container()
    under_card_container = st.container()
    selector_container = st.container()

    with card_container:
        if st.session_state.is_practicing and st.session_state.current_practice_word is not None:
            has_hint = bool(st.session_state.current_practice_word.get("hint", "").strip())

            if st.session_state.practice_display_side == 0:
                question_text = st.session_state.current_practice_word["word"]
                answer_text = st.session_state.current_practice_word["meaning"]
            else:
                question_text = st.session_state.current_practice_word["meaning"]
                answer_text = st.session_state.current_practice_word["word"]

            c1, c2 = st.columns(2)
            with c1:
                if st.button("정답", key="practice_show_answer_btn", use_container_width=True):
                    st.session_state.show_answer = True
                    if has_hint:
                        st.session_state.practice_show_hint = True
                    st.rerun()

            with c2:
                if st.button("힌트 보기", key="practice_hint_btn", use_container_width=True, disabled=not has_hint):
                    st.session_state.practice_show_hint = True
                    st.rerun()

            st.markdown(f"<div class='practice-question'>문제: {question_text}</div>", unsafe_allow_html=True)

            if st.session_state.practice_show_hint and has_hint:
                st.info(f"힌트:\n{st.session_state.current_practice_word['hint']}")

            if st.session_state.show_answer:
                st.markdown(f"<div class='practice-answer'>정답: {answer_text}</div>", unsafe_allow_html=True)

            score1, score2, score3, score4 = st.columns(4)
            with score1:
                if st.button("100%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(100)
                    st.rerun()
            with score2:
                if st.button("60%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(60)
                    st.rerun()
            with score3:
                if st.button("40%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(40)
                    st.rerun()
            with score4:
                if st.button("0%", disabled=not st.session_state.show_answer, use_container_width=True):
                    handle_practice_score(0)
                    st.rerun()

        elif st.session_state.is_practicing and st.session_state.current_practice_word is None:
            st.success("모든 연습을 완료했습니다.")
        else:
            st.info("아래에서 파일을 선택하고 연습 시작 버튼을 누르세요.")

    with under_card_container:
        render_under_card_view_controls("practice")

    with selector_container:
        folder_list, main_category = render_folder_picker("practice")
        selected_items = []
        if folder_list:
            selected_items = render_file_selector_section(folder_list, "practice", main_category)

        m1, m2, m3 = st.columns(3)
        with m1:
            if st.button("단어 이름만 연습하기", key="practice_word_only_btn", use_container_width=True):
                ok = load_and_start_practice(selected_items, "word_only")
                if ok:
                    st.rerun()
        with m2:
            if st.button("단어 뜻만 연습하기", key="practice_meaning_only_btn", use_container_width=True):
                ok = load_and_start_practice(selected_items, "meaning_only")
                if ok:
                    st.rerun()
        with m3:
            if st.button("랜덤으로 연습하기", key="practice_random_btn", use_container_width=True):
                ok = load_and_start_practice(selected_items, "random")
                if ok:
                    st.rerun()


def render_exam_part():
    st.header("시험 파트")

    card_container = st.container()
    under_card_container = st.container()
    selector_container = st.container()

    with card_container:
        if st.session_state.current_exam_word is not None:
            if st.session_state.exam_display_side == 0:
                question_text = st.session_state.current_exam_word["word"]
                answer_text = st.session_state.current_exam_word["meaning"]
            else:
                question_text = st.session_state.current_exam_word["meaning"]
                answer_text = st.session_state.current_exam_word["word"]

            st.markdown(f"<div class='exam-question'>문제: {question_text}</div>", unsafe_allow_html=True)

            if st.session_state.exam_show_answer:
                st.markdown(f"<div class='exam-answer'>정답: {answer_text}</div>", unsafe_allow_html=True)

            a1, a2, a3, a4 = st.columns([1, 1, 1, 2])

            with a1:
                if st.button("정답", key="exam_show_answer_btn", use_container_width=True):
                    st.session_state.exam_show_answer = True
                    st.rerun()

            with a2:
                if st.button("O", key="exam_o_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                    st.session_state.exam_correct_count += 1
                    load_next_exam_question()
                    st.rerun()

            with a3:
                if st.button("X", key="exam_x_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                    st.session_state.exam_wrong_count += 1
                    load_next_exam_question()
                    st.rerun()

            with a4:
                total = st.session_state.exam_total_count
                current = st.session_state.exam_current_number
                remain = total - (st.session_state.exam_correct_count + st.session_state.exam_wrong_count)
                st.info(
                    f"진행중: {current}/{total}  |  남음: {remain}  |  맞음: {st.session_state.exam_correct_count}  |  틀림: {st.session_state.exam_wrong_count}"
                )
        elif not st.session_state.is_examining and st.session_state.exam_current_number > 0:
            total_answered = st.session_state.exam_correct_count + st.session_state.exam_wrong_count
            if total_answered == st.session_state.exam_total_count:
                st.success(
                    f"시험이 완료되었습니다. 맞음 {st.session_state.exam_correct_count}개, 틀림 {st.session_state.exam_wrong_count}개입니다."
                )
        else:
            st.info("아래에서 파일을 선택하고 시험 시작 버튼을 누르세요.")

    with under_card_container:
        render_under_card_view_controls("exam")

    with selector_container:
        folder_list, main_category = render_folder_picker("exam")
        selected_items = []
        if folder_list:
            selected_items = render_file_selector_section(folder_list, "exam", main_category)

        max_count = max(1, len(st.session_state.exam_source_words)) if len(st.session_state.exam_source_words) > 0 else 1
        if st.session_state.exam_total_count_input > max_count:
            st.session_state.exam_total_count_input = max_count

        top1, top2 = st.columns([2.2, 1])
        with top1:
            st.number_input(
                "시험 개수 선택하기",
                min_value=1,
                max_value=max_count,
                step=1,
                key="exam_total_count_input"
            )
        with top2:
            st.write("")
            if st.button("max", key="exam_count_max_btn", use_container_width=True):
                st.session_state.exam_total_count_input = max_count
                st.rerun()

        st.session_state.exam_total_count = st.session_state.exam_total_count_input

        m1, m2, m3 = st.columns(3)
        with m1:
            if st.button("단어 이름만 시험 보기", key="exam_word_only_btn", use_container_width=True):
                ok = load_and_start_exam(selected_items, "word_only")
                if ok:
                    st.rerun()
        with m2:
            if st.button("단어 뜻만 시험 보기", key="exam_meaning_only_btn", use_container_width=True):
                ok = load_and_start_exam(selected_items, "meaning_only")
                if ok:
                    st.rerun()
        with m3:
            if st.button("랜덤으로 시험 보기", key="exam_random_btn", use_container_width=True):
                ok = load_and_start_exam(selected_items, "random")
                if ok:
                    st.rerun()


def render_wordbook_part():
    st.header("단어장 파트")
    st.caption("사용자는 직접 txt 파일을 업로드하거나 내용을 입력해 새 단어장을 만들 수 있습니다. 날짜 파일은 YYYY-MM-DD 형식을 권장합니다.")

    _, top_right = st.columns([5, 1])
    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
            st.success("GitHub 목록 캐시를 새로고침했습니다.")

    folders_to_offer = [
        "word_list/IT",
        "word_list/Japanese/N2",
        "word_list/Japanese/N3",
        "word_list/Japanese/N4~N5"
    ]

    selected_folder = st.selectbox("저장할 폴더를 선택하세요", folders_to_offer, key="wordbook_folder_select")
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
                    upload_title = st.text_input("저장할 파일명을 입력하세요", placeholder="예: 2026-07-20_일본어수업정리")
                    upload_password_input = st.text_input("업로드 비밀번호", type="password")
                    upload_submitted = st.form_submit_button("GitHub에 저장하기", use_container_width=True)

                    if upload_submitted:
                        if not upload_title.strip():
                            st.warning("저장할 파일명을 입력해 주세요.")
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
                "저장할 파일명을 입력하세요",
                value=default_title_prefix,
                placeholder="예: 2026-07-20_일본어오답"
            )
            manual_text = st.text_area(
                "단어장을 입력하세요",
                height=300,
                placeholder="예시 1)\napple\n사과\n힌트 여러 줄 가능\n\nbanana\n바나나\n힌트\n\n예시 2)\napple: 사과\n힌트 여러 줄 가능\nbanana: 바나나\n힌트"
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
                st.warning("저장할 파일명을 입력해 주세요.")
            elif manual_title.strip() == default_title_prefix.strip():
                st.warning("파일명 뒤의 자유 내용을 입력해 주세요.")
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


def main():
    init_session_state()
    keep_session_keys()
    restore_if_words_disappeared()
    apply_global_style()

    st.title("단어 암기 프로그램")

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