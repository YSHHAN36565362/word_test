import streamlit as st
import random
import os
import requests
import base64
from datetime import datetime
from urllib.parse import quote


def init_session_state():
    if 'words' not in st.session_state:
        st.session_state.words = []

    if 'study_index' not in st.session_state:
        st.session_state.study_index = 0
    if 'is_studying' not in st.session_state:
        st.session_state.is_studying = False

    if 'practice_queue' not in st.session_state:
        st.session_state.practice_queue = []
    if 'current_practice_word' not in st.session_state:
        st.session_state.current_practice_word = None
    if 'is_practicing' not in st.session_state:
        st.session_state.is_practicing = False
    if 'practice_display_side' not in st.session_state:
        st.session_state.practice_display_side = 0

    if 'show_answer' not in st.session_state:
        st.session_state.show_answer = False
    if 'exam_show_answer' not in st.session_state:
        st.session_state.exam_show_answer = False

    if 'exam_queue' not in st.session_state:
        st.session_state.exam_queue = []
    if 'exam_source_words' not in st.session_state:
        st.session_state.exam_source_words = []
    if 'current_exam_word' not in st.session_state:
        st.session_state.current_exam_word = None
    if 'is_examining' not in st.session_state:
        st.session_state.is_examining = False
    if 'exam_mode' not in st.session_state:
        st.session_state.exam_mode = None
    if 'exam_total_count' not in st.session_state:
        st.session_state.exam_total_count = 10
    if 'exam_current_number' not in st.session_state:
        st.session_state.exam_current_number = 0
    if 'exam_correct_count' not in st.session_state:
        st.session_state.exam_correct_count = 0
    if 'exam_wrong_count' not in st.session_state:
        st.session_state.exam_wrong_count = 0
    if 'exam_display_side' not in st.session_state:
        st.session_state.exam_display_side = 0


def load_words_from_file(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        parsed_words = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            line = line.replace('：', ':')

            if ':' in line:
                parts = line.split(':', 1)
                word = parts[0].strip()
                meaning = parts[1].strip()

                if word and meaning:
                    parsed_words.append({'word': word, 'meaning': meaning})

                i += 1

            else:
                word = line
                meaning = ""

                if i + 1 < len(lines):
                    meaning = lines[i + 1].strip()

                if word and meaning:
                    parsed_words.append({'word': word, 'meaning': meaning})

                i += 2

        return parsed_words

    except Exception as e:
        st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")
        return []


def parse_words_with_validation(text):
    normalized_text = text.replace('\r\n', '\n').replace('：', ':')
    lines = normalized_text.split('\n')

    parsed_words = []
    errors = []
    i = 0

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        if not line:
            i += 1
            continue

        if ':' in line:
            parts = line.split(':', 1)
            word = parts[0].strip()
            meaning = parts[1].strip()

            if not word and not meaning:
                errors.append(f"{i + 1}번 줄: 단어와 뜻이 모두 비어 있습니다.")
            elif not word:
                errors.append(f"{i + 1}번 줄: 단어가 비어 있습니다.")
            elif not meaning:
                errors.append(f"{i + 1}번 줄: 뜻이 비어 있습니다.")
            else:
                parsed_words.append({'word': word, 'meaning': meaning})

            i += 1

        else:
            word = line
            next_index = i + 1

            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1

            if next_index >= len(lines):
                errors.append(f"{i + 1}번 줄: 뜻이 없는 단어입니다.")
                i += 1
                continue

            meaning = lines[next_index].strip()

            if not word:
                errors.append(f"{i + 1}번 줄: 단어가 비어 있습니다.")
            elif not meaning:
                errors.append(f"{next_index + 1}번 줄: 뜻이 비어 있습니다.")
            else:
                parsed_words.append({'word': word, 'meaning': meaning})

            i = next_index + 1

    return parsed_words, errors


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

        if st.session_state.exam_mode == 'meaning_only':
            st.session_state.exam_display_side = 0
        elif st.session_state.exam_mode == 'word_only':
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
    st.rerun()


def move_to_next_practice_word():
    st.session_state.show_answer = False

    if len(st.session_state.practice_queue) > 0:
        st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
        st.session_state.practice_display_side = random.choice([0, 1])
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
    st.rerun()


def get_github_headers():
    return {
        "Authorization": f"Bearer {st.secrets['github_token']}",
        "Accept": "application/vnd.github+json"
    }


def get_repo_info():
    owner = st.secrets["github_owner"]
    repo = st.secrets["github_repo"]
    branch = st.secrets["github_branch"]
    return owner, repo, branch


def encode_github_path(path):
    return quote(path, safe='/')


def github_get_contents(path):
    owner, repo, branch = get_repo_info()
    encoded_path = encode_github_path(path)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{encoded_path}?ref={branch}"
    response = requests.get(url, headers=get_github_headers(), timeout=30)
    return response


def get_github_folders(base_path="word_list"):
    try:
        response = github_get_contents(base_path)

        if response.status_code != 200:
            return [], f"GitHub 폴더 목록을 불러오지 못했습니다. 상태 코드: {response.status_code}"

        data = response.json()
        folders = []

        for item in data:
            if item.get("type") == "dir":
                folders.append(item.get("path"))

        folders.sort()
        return folders, None

    except Exception as e:
        return [], f"GitHub 폴더 목록 조회 중 오류가 발생했습니다: {e}"


def get_github_txt_files(folder_path):
    try:
        response = github_get_contents(folder_path)

        if response.status_code != 200:
            return [], f"선택한 폴더의 파일 목록을 불러오지 못했습니다. 상태 코드: {response.status_code}"

        data = response.json()
        txt_files = []

        for item in data:
            if item.get("type") == "file" and item.get("name", "").lower().endswith(".txt"):
                txt_files.append(item.get("name"))

        txt_files.sort()
        return txt_files, None

    except Exception as e:
        return [], f"파일 목록 조회 중 오류가 발생했습니다: {e}"


def get_local_wordbook_structure(base_folder='word_list'):
    folder_map = {}

    if not os.path.exists(base_folder):
        os.makedirs(base_folder)

    for root, dirs, files in os.walk(base_folder):
        txt_files = sorted([f for f in files if f.lower().endswith('.txt')])

        if txt_files:
            rel_folder = os.path.relpath(root, base_folder)
            if rel_folder == ".":
                rel_folder = "(루트)"
            folder_map[rel_folder] = txt_files

    return folder_map


def make_safe_filename_part(name):
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_name = name.strip()

    for ch in invalid_chars:
        safe_name = safe_name.replace(ch, '_')

    safe_name = safe_name.replace('\n', ' ').replace('\r', ' ')
    safe_name = " ".join(safe_name.split())

    if not safe_name:
        safe_name = "untitled"

    return safe_name


def make_timestamped_filename(user_title):
    safe_title = make_safe_filename_part(user_title)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{timestamp}_{safe_title}.txt"


def upload_text_to_github(folder_path, file_name, text_content):
    owner, repo, branch = get_repo_info()
    repo_path = f"{folder_path}/{file_name}"
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


def render_study_part(target_folder):
    st.header("학습 파트")

    folder_map = get_local_wordbook_structure(target_folder)

    if not folder_map:
        st.warning(f"'{target_folder}' 폴더 및 하위 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더 안에 txt 파일을 먼저 올려주세요.")
        return

    selected_folder = st.selectbox("학습할 폴더를 선택하세요", list(folder_map.keys()), key="study_folder_select")
    selected_file = st.selectbox("학습할 텍스트 파일을 선택하세요", folder_map[selected_folder], key="study_file_select")

    actual_folder = target_folder if selected_folder == "(루트)" else os.path.join(target_folder, selected_folder)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("파일 선택하기", use_container_width=True):
            file_path = os.path.join(actual_folder, selected_file)
            st.session_state.words = load_words_from_file(file_path)
            st.session_state.study_index = 0
            st.session_state.is_studying = False
            st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")

    with col2:
        if st.button("랜덤으로 섞기", use_container_width=True):
            if len(st.session_state.words) > 0:
                random.shuffle(st.session_state.words)
                st.session_state.study_index = 0
                st.success("단어 목록이 랜덤으로 섞였습니다!")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with col3:
        if st.button("학습하기", use_container_width=True):
            if len(st.session_state.words) > 0:
                st.session_state.is_studying = True
                st.session_state.study_index = 0
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    if len(st.session_state.words) > 0 and st.session_state.is_studying:
        st.write("---")
        if st.session_state.study_index < len(st.session_state.words):
            current_word = st.session_state.words[st.session_state.study_index]

            if st.button("다음"):
                st.session_state.study_index += 1
                st.rerun()

            st.markdown(f"<div style='font-size: 24px;'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 24px;'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)
        else:
            st.success("모두 학습했습니다.")


def render_practice_part(target_folder):
    st.header("연습 파트")

    folder_map = get_local_wordbook_structure(target_folder)

    if not folder_map:
        st.warning(f"'{target_folder}' 폴더 및 하위 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더 안에 txt 파일을 먼저 올려주세요.")
        return

    selected_folder = st.selectbox("연습할 폴더를 선택하세요", list(folder_map.keys()), key="practice_folder_select")
    selected_file = st.selectbox("파일을 선택하세요.", folder_map[selected_folder], key="practice_file_select")

    actual_folder = target_folder if selected_folder == "(루트)" else os.path.join(target_folder, selected_folder)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("파일 선택하기", key="practice_load", use_container_width=True):
            file_path = os.path.join(actual_folder, selected_file)
            st.session_state.words = load_words_from_file(file_path)
            st.session_state.practice_queue = list(st.session_state.words)
            st.session_state.is_practicing = False
            st.session_state.current_practice_word = None
            st.session_state.show_answer = False
            st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")

    with col2:
        if st.button("단어 랜덤으로 섞기", use_container_width=True):
            if len(st.session_state.practice_queue) > 0:
                random.shuffle(st.session_state.practice_queue)
                st.session_state.is_practicing = False
                st.session_state.current_practice_word = None
                st.session_state.show_answer = False
                st.success("연습 단어가 랜덤으로 섞였습니다!")
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    with col3:
        if st.button("연습하기", use_container_width=True):
            if len(st.session_state.words) > 0:
                st.session_state.practice_queue = list(st.session_state.words) if len(st.session_state.practice_queue) == 0 else st.session_state.practice_queue
                st.session_state.is_practicing = True
                st.session_state.show_answer = False
                if len(st.session_state.practice_queue) > 0:
                    st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                    st.session_state.practice_display_side = random.choice([0, 1])
                else:
                    st.session_state.current_practice_word = None
            else:
                st.warning("먼저 파일을 선택해 주세요.")

    if st.session_state.is_practicing:
        st.write("---")
        if st.session_state.current_practice_word is not None:
            score_col1, score_col2, score_col3, score_col4, score_col5 = st.columns(5)

            with score_col1:
                if st.button("정답", use_container_width=True):
                    st.session_state.show_answer = True
                    st.rerun()

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

            if st.session_state.practice_display_side == 0:
                question_text = st.session_state.current_practice_word['word']
                answer_text = st.session_state.current_practice_word['meaning']
            else:
                question_text = st.session_state.current_practice_word['meaning']
                answer_text = st.session_state.current_practice_word['word']

            st.markdown(
                f"<div style='font-size: 40px; text-align: center; padding: 20px;'>문제: {question_text}</div>",
                unsafe_allow_html=True
            )

            if st.session_state.show_answer:
                st.markdown(
                    f"<div style='font-size: 30px; text-align: center; color: gray; padding: 10px;'>정답: {answer_text}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.success("모든 연습을 완료했습니다.")


def render_exam_part(target_folder):
    st.header("시험 파트")

    folder_map = get_local_wordbook_structure(target_folder)

    if not folder_map:
        st.warning(f"'{target_folder}' 폴더 및 하위 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더 안에 txt 파일을 먼저 올려주세요.")
        return

    selected_folder = st.selectbox("시험할 폴더를 선택하세요", list(folder_map.keys()), key="exam_folder_select")
    selected_file_exam = st.selectbox("시험할 파일을 선택하세요", folder_map[selected_folder], key="exam_file_select")

    actual_folder = target_folder if selected_folder == "(루트)" else os.path.join(target_folder, selected_folder)

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.2, 1.2, 1.2, 1.4], vertical_alignment="bottom")

    with top_col1:
        if st.button("파일 선택하기", key="exam_load", use_container_width=True):
            file_path = os.path.join(actual_folder, selected_file_exam)
            loaded_words = load_words_from_file(file_path)
            st.session_state.words = loaded_words
            st.session_state.exam_source_words = list(loaded_words)
            reset_exam_state()
            st.success(f"'{selected_file_exam}'에서 {len(loaded_words)}개의 단어를 성공적으로 불러왔습니다!")

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
        st.session_state.exam_total_count = st.number_input(
            "시험 개수 선택하기",
            min_value=1,
            max_value=max_count,
            value=min(st.session_state.exam_total_count, max_count),
            step=1,
            key="exam_total_count_input"
        )

    st.write("")

    mode_col1, mode_col2, mode_col3 = st.columns(3)

    with mode_col1:
        if st.button("단어 이름만 시험 보기", use_container_width=True):
            start_exam('word_only')

    with mode_col2:
        if st.button("단어 뜻만 시험 보기", use_container_width=True):
            start_exam('meaning_only')

    with mode_col3:
        if st.button("랜덤으로 시험 보기", use_container_width=True):
            start_exam('random')

    if st.session_state.current_exam_word is not None:
        st.write("---")

        action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1, 2])

        with action_col1:
            if st.button("정답", key="exam_show_answer_btn", use_container_width=True):
                st.session_state.exam_show_answer = True
                st.rerun()

        with action_col2:
            if st.button("O", key="exam_o_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                st.session_state.exam_correct_count += 1
                load_next_exam_question()
                st.rerun()

        with action_col3:
            if st.button("X", key="exam_x_btn", disabled=not st.session_state.exam_show_answer, use_container_width=True):
                st.session_state.exam_wrong_count += 1
                load_next_exam_question()
                st.rerun()

        with action_col4:
            total = st.session_state.exam_total_count
            current = st.session_state.exam_current_number
            remain = total - (st.session_state.exam_correct_count + st.session_state.exam_wrong_count)
            st.info(
                f"진행중: {current}/{total}  |  남음: {remain}  |  맞음: {st.session_state.exam_correct_count}  |  틀림: {st.session_state.exam_wrong_count}"
            )

        st.write("---")

        if st.session_state.exam_display_side == 0:
            question_text = st.session_state.current_exam_word['word']
            answer_text = st.session_state.current_exam_word['meaning']
        else:
            question_text = st.session_state.current_exam_word['meaning']
            answer_text = st.session_state.current_exam_word['word']

        st.markdown(
            f"<div style='font-size: 42px; text-align: center; padding: 28px;'>문제: {question_text}</div>",
            unsafe_allow_html=True
        )

        if st.session_state.exam_show_answer:
            st.markdown(
                f"<div style='font-size: 30px; text-align: center; color: gray; padding: 12px;'>정답: {answer_text}</div>",
                unsafe_allow_html=True
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
                        elif upload_password_input != st.secrets["upload_password"]:
                            st.error("업로드 비밀번호가 올바르지 않습니다.")
                        else:
                            final_file_name = make_timestamped_filename(upload_title)
                            response, repo_path = upload_text_to_github(selected_folder, final_file_name, uploaded_text)

                            if response.status_code in [200, 201]:
                                st.success(f"GitHub에 저장되었습니다: {repo_path}")
                            else:
                                st.error(f"GitHub 저장 실패: {response.status_code}")
                                try:
                                    st.code(response.json())
                                except Exception:
                                    st.text(response.text)

    with manual_tab:
        st.subheader("직접 입력해서 저장")

        with st.form("manual_wordbook_form"):
            manual_title = st.text_input("저장할 제목을 입력하세요", placeholder="예: 오늘 외운 단어")
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
            elif not manual_text.strip():
                st.warning("단어장 내용을 입력해 주세요.")
            elif len(parsed_words) == 0:
                st.warning("저장할 정상 단어가 없습니다.")
            elif errors:
                st.warning("형식 오류를 먼저 수정한 뒤 다시 저장해 주세요.")
            elif manual_password_input != st.secrets["upload_password"]:
                st.error("업로드 비밀번호가 올바르지 않습니다.")
            else:
                final_file_name = make_timestamped_filename(manual_title)
                response, repo_path = upload_text_to_github(selected_folder, final_file_name, manual_text)

                if response.status_code in [200, 201]:
                    st.success(f"GitHub에 저장되었습니다: {repo_path}")
                else:
                    st.error(f"GitHub 저장 실패: {response.status_code}")
                    try:
                        st.code(response.json())
                    except Exception:
                        st.text(response.text)


def main():
    init_session_state()

    st.title("단어 암기 프로그램")

    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '연습', '시험', '단어장'])

    target_folder = 'word_list'

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    if page == '학습':
        render_study_part(target_folder)
    elif page == '연습':
        render_practice_part(target_folder)
    elif page == '시험':
        render_exam_part(target_folder)
    elif page == '단어장':
        render_wordbook_part()


if __name__ == '__main__':
    main()