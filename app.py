import streamlit as st
import random
import os


def init_session_state():
    if 'words' not in st.session_state:
        st.session_state.words = []

    if 'study_index' not in st.session_state:
        st.session_state.study_index = 0
    if 'is_studying' not in st.session_state:
        st.session_state.is_studying = False

    # ***** 연속 수정 안내: 기존 테스트 상태를 연습 상태로 이름 변경했습니다.
    if 'practice_queue' not in st.session_state:
        st.session_state.practice_queue = []
    if 'current_practice_word' not in st.session_state:
        st.session_state.current_practice_word = None
    if 'is_practicing' not in st.session_state:
        st.session_state.is_practicing = False
    if 'practice_display_side' not in st.session_state:
        st.session_state.practice_display_side = 0

    # ***** 연속 수정 안내: 연습/시험에서 정답 표시 여부를 각각 따로 관리합니다.
    if 'show_answer' not in st.session_state:
        st.session_state.show_answer = False
    if 'exam_show_answer' not in st.session_state:
        st.session_state.exam_show_answer = False

    # ***** 연속 수정 안내: 시험 파트에 필요한 상태값들을 새로 추가했습니다.
    if 'exam_queue' not in st.session_state:
        st.session_state.exam_queue = []
    if 'exam_source_words' not in st.session_state:
        st.session_state.exam_source_words = []
    if 'current_exam_word' not in st.session_state:
        st.session_state.current_exam_word = None
    if 'is_examining' not in st.session_state:
        st.session_state.is_examining = False
    if 'exam_mode' not in st.session_state:
        st.session_state.exam_mode = None  # 'meaning_only', 'word_only', 'random'
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


# ***** 연속 수정 안내: 시험 시작 전 상태를 한 번에 정리하는 함수입니다.
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


# ***** 연속 수정 안내: 시험에서 다음 문제를 꺼내는 함수입니다.
def load_next_exam_question():
    if len(st.session_state.exam_queue) > 0:
        st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
        st.session_state.exam_current_number += 1
        st.session_state.exam_show_answer = False

        if st.session_state.exam_mode == 'meaning_only':
            st.session_state.exam_display_side = 0  # 뜻만 출력(문제=뜻, 정답=단어)
        elif st.session_state.exam_mode == 'word_only':
            st.session_state.exam_display_side = 1  # 단어만 출력(문제=단어, 정답=뜻)
        else:
            st.session_state.exam_display_side = random.choice([0, 1])
    else:
        st.session_state.current_exam_word = None
        st.session_state.is_examining = False


# ***** 연속 수정 안내: 시험 시작 함수입니다.
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


def main():
    init_session_state()

    st.title("단어 암기 프로그램")

    st.sidebar.title("메뉴")
    # ***** 연속 수정 안내: 테스트를 연습으로 바꾸고, 시험 파트를 새로 추가했습니다.
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '연습', '시험'])

    target_folder = 'word_list'

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    txt_files = [f for f in os.listdir(target_folder) if f.endswith('.txt')]

    if page == '학습':
        st.header("학습 파트")

        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            selected_file = st.selectbox("학습할 텍스트 파일을 선택하세요", txt_files, key="study_file_select")

            # ***** 연속 수정 안내: 학습 파트의 3버튼을 가로 배치했습니다.
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("파일 선택하기", use_container_width=True):
                    file_path = os.path.join(target_folder, selected_file)
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

                # ***** 연속 수정 안내: '다음' 버튼을 단어와 의미 출력 내용 위로 끌어올렸습니다.
                if st.button("다음"):
                    st.session_state.study_index += 1
                    st.rerun()

                st.markdown(f"<div style='font-size: 24px;'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 24px;'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)

            else:
                st.success("모두 학습했습니다.")

    elif page == '연습':
        st.header("연습 파트")

        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            selected_file_practice = st.selectbox("파일을 선택하세요.", txt_files, key="practice_file_select")

            # ***** 연속 수정 안내: 연습 파트의 3버튼을 가로 배치했습니다.
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("파일 선택하기", key="practice_load", use_container_width=True):
                    file_path = os.path.join(target_folder, selected_file_practice)
                    st.session_state.words = load_words_from_file(file_path)
                    st.session_state.practice_queue = list(st.session_state.words)
                    st.session_state.is_practicing = False
                    st.session_state.current_practice_word = None
                    st.session_state.show_answer = False
                    st.success(f"'{selected_file_practice}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")

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
                # ***** 연속 수정 안내: 버튼이 글자 길이에 따라 움직이지 않도록 단어 출력보다 위로 배치했습니다.
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    if st.button("정답", use_container_width=True):
                        st.session_state.show_answer = True
                        st.rerun()

                with col2:
                    if st.button("아는 단어", disabled=not st.session_state.show_answer, use_container_width=True):
                        n = len(st.session_state.practice_queue)
                        pos = n - random.randint(5, 10)
                        pos = max(0, pos)
                        st.session_state.practice_queue.insert(pos, st.session_state.current_practice_word)

                        st.session_state.show_answer = False
                        if len(st.session_state.practice_queue) > 0:
                            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                            st.session_state.practice_display_side = random.choice([0, 1])
                        else:
                            st.session_state.current_practice_word = None
                        st.rerun()

                with col3:
                    if st.button("모르는 단어", disabled=not st.session_state.show_answer, use_container_width=True):
                        n = len(st.session_state.practice_queue)
                        pos = random.randint(5, 10)
                        pos = min(n, pos)
                        st.session_state.practice_queue.insert(pos, st.session_state.current_practice_word)

                        st.session_state.show_answer = False
                        if len(st.session_state.practice_queue) > 0:
                            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                            st.session_state.practice_display_side = random.choice([0, 1])
                        else:
                            st.session_state.current_practice_word = None
                        st.rerun()

                with col4:
                    if st.button("헷갈리는 단어", disabled=not st.session_state.show_answer, use_container_width=True):
                        n = len(st.session_state.practice_queue)
                        lower = min(n, 10)
                        upper = max(0, n - 10)
                        if lower > upper:
                            lower, upper = upper, lower
                        pos = random.randint(lower, upper)
                        st.session_state.practice_queue.insert(pos, st.session_state.current_practice_word)

                        st.session_state.show_answer = False
                        if len(st.session_state.practice_queue) > 0:
                            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                            st.session_state.practice_display_side = random.choice([0, 1])
                        else:
                            st.session_state.current_practice_word = None
                        st.rerun()

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

    elif page == '시험':
        st.header("시험 파트")

        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            selected_file_exam = st.selectbox("시험할 파일을 선택하세요", txt_files, key="exam_file_select")

            # ***** 연속 수정 안내: 시험 파트 상단 3버튼 + 시험 개수 입력칸을 가로로 배치했습니다.
            top_col1, top_col2, top_col3, top_col4 = st.columns([1.2, 1.2, 1.2, 1.4], vertical_alignment="bottom")

            with top_col1:
                if st.button("파일 선택하기", key="exam_load", use_container_width=True):
                    file_path = os.path.join(target_folder, selected_file_exam)
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

            # ***** 연속 수정 안내: 시험 방식 선택 버튼 3개를 가로로 만들었습니다.
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

            # ***** 연속 수정 안내: 정답/O/X/현황을 한 줄 인터페이스로 배치했습니다.
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

            # ***** 연속 수정 안내: 사용자가 선택한 시험 방식에 맞는 문제/정답을 표시합니다.
            if st.session_state.exam_display_side == 0:
                # 문제는 단어, 정답은 뜻
                question_text = st.session_state.current_exam_word['word']
                answer_text = st.session_state.current_exam_word['meaning']
            else:
                # 문제는 뜻, 정답은 단어
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

        elif page == '시험' and not st.session_state.is_examining:
            # ***** 연속 수정 안내: 시험이 끝난 뒤 결과를 보여줍니다.
            if st.session_state.exam_current_number > 0:
                total_answered = st.session_state.exam_correct_count + st.session_state.exam_wrong_count
                if total_answered == st.session_state.exam_total_count:
                    st.success(
                        f"시험이 완료되었습니다. 맞음 {st.session_state.exam_correct_count}개, 틀림 {st.session_state.exam_wrong_count}개입니다."
                    )


if __name__ == '__main__':
    main()