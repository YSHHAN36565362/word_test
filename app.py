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

def load_words_from_file(file_name):
    try:
        # **** 연속 수정 안내: 이제 file_name에는 'word_list/단어장.txt' 처럼 폴더 경로까지 포함되어 전달됩니다.
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        parsed_words = []
        i = 0
        
        # **** 연속 수정 안내: 전체 줄을 하나씩 확인하면서 내려가기 위해 while 반복문을 사용합니다.
        while i < len(lines):
            # 양 끝 공백이나 줄바꿈을 제거합니다.
            line = lines[i].strip()
            
            # 빈 줄이면 단어나 뜻이 아니므로 그냥 다음 줄로 넘어갑니다.
            if not line:
                i += 1
                continue
            
            # 이전처럼 전각 콜론을 반각 콜론으로 바꿔주는 기능은 그대로 유지합니다.
            line = line.replace('：', ':')
            
            # 만약 해당 줄에 콜론(:)이 있다면 기존 방식대로 처리합니다.
            if ':' in line:
                # 콜론을 기준으로 한 번만 나눕니다.
                parts = line.split(':', 1)
                word = parts[0].strip()
                meaning = parts[1].strip()
                
                if word and meaning:
                    parsed_words.append({'word': word, 'meaning': meaning})
                
                # 처리가 끝났으므로 다음 줄(1칸 아래)로 이동합니다.
                i += 1
                
            # **** 연속 수정 안내: 콜론이 없다면, 첫 줄을 단어, 그 다음 줄을 의미로 인식하는 새로운 규칙입니다.
            else:
                word = line
                meaning = ""
                
                # 파일의 마지막 줄이 아니라면, 바로 밑에 있는 줄을 의미로 가져옵니다.
                if i + 1 < len(lines):
                    meaning = lines[i+1].strip()
                
                if word and meaning:
                    parsed_words.append({'word': word, 'meaning': meaning})
                
                # 단어(1줄)와 의미(1줄) 총 2줄을 읽었으므로, 다음 읽을 위치를 2칸 뒤로 옮깁니다.
                # 만약 그 다음 줄이 한 줄 공란이라면, 위쪽의 '빈 줄이면 넘어갑니다' 코드에서 알아서 걸러집니다.
                i += 2
                
        return parsed_words
    except Exception as e:
        st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")
        return []

def main():
    init_session_state()
    
    st.title("단어 암기 프로그램")
    
    # 왼쪽에 파트 선택을 만들어주고 사용자가 파트를 선택하면 해당 파트로 이동합니다.
    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '테스트'])
    
    # **** 연속 수정 안내: 단어장 파일들이 들어있는 폴더 이름을 지정합니다.
    target_folder = 'word_list'
    
    # **** 연속 수정 안내: 만약 word_list 폴더가 아직 없다면 프로그램이 에러를 내지 않도록 빈 폴더를 알아서 만들어줍니다.
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        
    # **** 연속 수정 안내: 모든 파일이 아닌 target_folder(word_list 폴더) 안에서 .txt로 끝나는 파일들만 가져옵니다.
    txt_files = [f for f in os.listdir(target_folder) if f.endswith('.txt')]
    
    if page == '학습':
        st.header("학습 파트")
        
        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            # 학습 파트는 파일을 선택할 수 있게 합니다.
            selected_file = st.selectbox("학습할 텍스트 파일을 선택하세요", txt_files, key="study_file_select")
            
            if st.button("파일 선택하기"):
                # **** 연속 수정 안내: 파일을 읽을 때 폴더 이름(word_list)과 파일 이름(정보처리기사.txt)을 합쳐서 정확한 경로를 찾아줍니다.
                file_path = os.path.join(target_folder, selected_file)
                st.session_state.words = load_words_from_file(file_path)
                st.session_state.study_index = 0
                st.session_state.is_studying = False
                st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
        
        # 파일에서 단어를 하나라도 불러왔을 때만 아래 버튼과 기능들이 화면에 나타납니다.
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
                    
                    # 한 줄씩 기준 좌우 내용을 모두 출력합니다.
                    st.markdown(f"<div style='font-size: 24px;'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 24px;'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)
                    
                    if st.button("다음"):
                        st.session_state.study_index += 1
                        st.rerun()
                else:
                    # 모두 출력하면 해당 문구를 출력합니다.
                    st.success("모두 학습했습니다.")
                    
    elif page == '테스트':
        st.header("테스트 파트")
        
        if len(txt_files) == 0:
            st.warning(f"'{target_folder}' 폴더에 txt 파일이 없습니다. 깃허브의 {target_folder} 폴더에 txt 파일을 먼저 올려주세요.")
        else:
            selected_file_test = st.selectbox("파일을 선택하세요.", txt_files, key="test_file_select")
            
            if st.button("파일 선택하기", key="test_load"):
                # **** 연속 수정 안내: 테스트 파트에서도 동일하게 폴더 경로를 합쳐서 파일을 읽습니다.
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
                if len(st.session_state.test_queue) > 0:
                    st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                    st.session_state.test_display_side = random.choice([0, 1])
                else:
                    st.session_state.current_test_word = None
                    
            if st.session_state.is_testing:
                st.write("---")
                if st.session_state.current_test_word is not None:
                    # 왼쪽이나 오른쪽 내용을 랜덤으로 고릅니다.
                    if st.session_state.test_display_side == 0:
                        display_text = st.session_state.current_test_word['word']
                    else:
                        display_text = st.session_state.current_test_word['meaning']
                    
                    # 단어를 보기 편하게 크게 출력합니다.
                    st.markdown(f"<div style='font-size: 40px; text-align: center; padding: 20px;'>{display_text}</div>", unsafe_allow_html=True)
                    
                    # 하단에 3개의 평가 버튼을 나란히 배치합니다.
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("아는 단어"):
                            n = len(st.session_state.test_queue)
                            # 아래에서 5번째 ~ 10번째 줄로 보냅니다.
                            pos = n - random.randint(5, 10)
                            pos = max(0, pos)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                            
                    with col2:
                        if st.button("모르는 단어"):
                            n = len(st.session_state.test_queue)
                            # 위에서 5번째 ~ 10번째 줄 사이로 보냅니다.
                            pos = random.randint(5, 10)
                            pos = min(n, pos)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                            
                    with col3:
                        if st.button("헷갈리는 단어"):
                            n = len(st.session_state.test_queue)
                            # 위에서 10번째 줄에서 아래에서 10번째 줄 사이로 보냅니다.
                            lower = min(n, 10)
                            upper = max(0, n - 10)
                            if lower > upper:
                                lower, upper = upper, lower
                            pos = random.randint(lower, upper)
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun()
                else:
                    st.success("모든 테스트를 완료했습니다.")

# 파이썬 프로그램의 시작점입니다.
if __name__ == '__main__':
    main()