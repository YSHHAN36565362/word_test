import streamlit as st
import random
import os

# 초보자를 위한 주석: 스트림릿은 버튼을 누를 때마다 화면이 새로고침되면서 코드가 처음부터 다시 실행됩니다.
# 따라서 중간에 학습하던 단어의 위치나 섞어둔 목록을 잃어버리지 않도록 세션 상태(session_state)에 저장해두는 함수입니다.
def init_session_state():
    if 'words' not in st.session_state:
        st.session_state.words = []
    
    if 'study_index' not in st.session_state:
        st.session_state.study_index = 0
    if 'is_studying' not in st.session_state:
        st.session_state.is_studying = False
    
    if 'test_queue' not in st.session_state:
        st.session_state.test_queue = []
    if 'current_test_word' not in st.session_state:
        st.session_state.current_test_word = None
    if 'is_testing' not in st.session_state:
        st.session_state.is_testing = False
    if 'test_display_side' not in st.session_state:
        st.session_state.test_display_side = 0
    
    # ***** 연속 수정 안내: 테스트 시 정답을 확인했는지 기억하는 상태 값을 새로 추가했습니다.
    if 'show_answer' not in st.session_state:
        st.session_state.show_answer = False

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
                    meaning = lines[i+1].strip()
                
                if word and meaning:
                    parsed_words.append({'word': word, 'meaning': meaning})
                
                i += 2
                
        return parsed_words
    except Exception as e:
        st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")
        return []

def main():
    init_session_state()
    
    st.title("단어 암기 프로그램")
    
    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '테스트'])
    
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
            
            if st.button("파일 선택하기"):
                file_path = os.path.join(target_folder, selected_file)
                st.session_state.words = load_words_from_file(file_path)
                st.session_state.study_index = 0
                st.session_state.is_studying = False
                st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
        
        if len(st.session_state.words) > 0:
            if st.button("랜덤으로 섞기"):
                random.shuffle(st.session_state.words)
                st.session_state.study_index = 0
                st.success("단어 목록이 랜덤으로 섞였습니다!")
                
            if st.button("학습하기"):
                st.session_state.is_studying = True
                st.session_state.study_index = 0
                
            if st.session_state.is_studying:
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
                    
    elif page == '테스트':
        st.header("테스트 파트")
        
        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            selected_file_test = st.selectbox("파일을 선택하세요.", txt_files, key="test_file_select")
            
            if st.button("파일 선택하기", key="test_load"):
                file_path = os.path.join(target_folder, selected_file_test)
                st.session_state.words = load_words_from_file(file_path)
                st.session_state.test_queue = list(st.session_state.words)
                st.session_state.is_testing = False
                st.success(f"'{selected_file_test}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
                
        if len(st.session_state.words) > 0:
            if st.button("단어 랜덤으로 섞기"):
                random.shuffle(st.session_state.test_queue)
                st.session_state.is_testing = False
                st.success("테스트 단어가 랜덤으로 섞였습니다!")
                
            if st.button("테스트하기"):
                st.session_state.is_testing = True
                st.session_state.show_answer = False # ***** 연속 수정 안내: 테스트 시작 시 정답을 가림 상태로 초기화합니다.
                if len(st.session_state.test_queue) > 0:
                    st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                    st.session_state.test_display_side = random.choice([0, 1])
                else:
                    st.session_state.current_test_word = None
                    
            if st.session_state.is_testing:
                st.write("---")
                if st.session_state.current_test_word is not None:
                    
                    # ***** 연속 수정 안내: 버튼이 글자 길이에 따라 움직이지 않도록 단어 출력보다 위로 배치했습니다.
                    # 정답 버튼이 추가되어 4개의 공간(col1~col4)으로 나눴습니다.
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        # ***** 연속 수정 안내: 정답 확인 버튼을 아는 단어 버튼의 제일 왼쪽에 추가했습니다.
                        if st.button("정답"):
                            st.session_state.show_answer = True
                            st.rerun()
                    
                    with col2:
                        # ***** 연속 수정 안내: disabled 옵션을 사용하여, 정답 버튼을 누르기 전에는 이 버튼들을 비활성화 상태로 만듭니다.
                        if st.button("아는 단어", disabled=not st.session_state.show_answer):
                            n = len(st.session_state.test_queue)
                            pos = n - random.randint(5, 10)
                            pos = max(0, pos)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            st.session_state.show_answer = False # ***** 연속 수정 안내: 다음 단어로 넘어가므로 다시 정답을 가립니다.
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                            
                    with col3:
                        if st.button("모르는 단어", disabled=not st.session_state.show_answer):
                            n = len(st.session_state.test_queue)
                            pos = random.randint(5, 10)
                            pos = min(n, pos)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            st.session_state.show_answer = False
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                            
                    with col4:
                        if st.button("헷갈리는 단어", disabled=not st.session_state.show_answer):
                            n = len(st.session_state.test_queue)
                            lower = min(n, 10)
                            upper = max(0, n - 10)
                            if lower > upper:
                                lower, upper = upper, lower
                            pos = random.randint(lower, upper)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            st.session_state.show_answer = False
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                    
                    st.write("---")
                    
                    # ***** 연속 수정 안내: 버튼 아래에 문제로 낼 텍스트와 정답 텍스트를 준비합니다.
                    if st.session_state.test_display_side == 0:
                        question_text = st.session_state.current_test_word['word']
                        answer_text = st.session_state.current_test_word['meaning']
                    else:
                        question_text = st.session_state.current_test_word['meaning']
                        answer_text = st.session_state.current_test_word['word']
                    
                    # 문제를 화면 중앙에 크게 출력합니다.
                    st.markdown(f"<div style='font-size: 40px; text-align: center; padding: 20px;'>문제: {question_text}</div>", unsafe_allow_html=True)
                    
                    # ***** 연속 수정 안내: 정답 버튼을 눌렀다면, 문제 아래에 정답 내용도 함께 크게 보여줍니다.
                    if st.session_state.show_answer:
                        st.markdown(f"<div style='font-size: 30px; text-align: center; color: gray; padding: 10px;'>정답: {answer_text}</div>", unsafe_allow_html=True)
                        
                else:
                    st.success("모든 테스트를 완료했습니다.")

# 파이썬 프로그램의 시작점입니다.
if __name__ == '__main__':
    main()