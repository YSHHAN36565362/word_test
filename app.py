import streamlit as st
import random
import os  # * 변경됨: 컴퓨터(또는 깃허브 서버)의 폴더와 파일 목록을 확인하기 위해 os 모듈을 추가로 가져옵니다.

# 초보자를 위한 주석: 스트림릿은 버튼을 누를 때마다 화면이 새로고침되면서 코드가 처음부터 다시 실행됩니다.
# 따라서 중간에 학습하던 단어의 위치나 섞어둔 목록을 잃어버리지 않도록 세션 상태(session_state)에 저장해두는 함수입니다.
def init_session_state():
    # 원본 단어 목록을 저장하는 공간
    if 'words' not in st.session_state:
        st.session_state.words = []
    
    # 학습 파트에서 현재 몇 번째 단어를 보고 있는지 기억하는 숫자
    if 'study_index' not in st.session_state:
        st.session_state.study_index = 0
    # 학습이 진행 중인지 확인하는 상태 값
    if 'is_studying' not in st.session_state:
        st.session_state.is_studying = False
    
    # 테스트 파트에서 섞은 후 임시로 사용하는 단어 대기열 목록
    if 'test_queue' not in st.session_state:
        st.session_state.test_queue = []
    # 테스트 화면에 띄울 현재 단어
    if 'current_test_word' not in st.session_state:
        st.session_state.current_test_word = None
    # 테스트가 진행 중인지 확인하는 상태 값
    if 'is_testing' not in st.session_state:
        st.session_state.is_testing = False
    # 테스트 시 왼쪽(단어)을 보여줄지 오른쪽(의미)을 보여줄지 결정하는 숫자 (0이면 왼쪽, 1이면 오른쪽)
    if 'test_display_side' not in st.session_state:
        st.session_state.test_display_side = 0

# * 변경됨: 깃허브 URL 대신, 현재 프로그램이 실행 중인 폴더 안의 txt 파일을 직접 읽어오는 함수로 바뀌었습니다.
def load_words_from_file(file_name):
    try:
        # * 변경됨: 파이썬의 기본 기능인 open을 사용해 선택한 텍스트 파일을 엽니다. 한글 깨짐 방지를 위해 utf-8을 사용합니다.
        with open(file_name, 'r', encoding='utf-8') as file:
            # 파일의 모든 내용을 한 줄씩 읽어서 리스트 형태로 저장합니다.
            lines = file.readlines()
        
        parsed_words = []
        for line in lines:
            # 콜론(:)이 있는 줄만 정상적인 데이터로 인식하고 처리합니다.
            if ':' in line:
                # 콜론을 기준으로 왼쪽 내용과 오른쪽 내용으로 분리합니다.
                parts = line.split(':')
                # 양 끝의 띄어쓰기나 줄바꿈(공백)을 제거하고 깔끔하게 저장합니다.
                word = parts[0].strip()
                meaning = parts[1].strip()
                parsed_words.append({'word': word, 'meaning': meaning})
        return parsed_words
    except Exception as e:
        # 파일을 읽는 중 문제가 생기면 화면에 에러를 보여줍니다.
        st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")
        return []

def main():
    # 프로그램을 시작할 때 가장 먼저 세션 상태를 준비합니다.
    init_session_state()
    
    st.title("단어 암기 프로그램")
    
    # 사이드바(화면 왼쪽)에 학습과 테스트를 선택할 수 있는 라디오 버튼을 만듭니다.
    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '테스트'])
    
    # * 변경됨: 현재 프로그램이 실행되는 폴더(깃허브 저장소)에서 확장자가 .txt인 파일들의 이름만 모아서 리스트로 만듭니다.
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    if page == '학습':
        st.header("학습 파트")
        
        # * 변경됨: 폴더에 txt 파일이 하나도 없다면 안내 문구를 띄워줍니다.
        if len(txt_files) == 0:
            st.warning("현재 폴더에 txt 파일이 없습니다. 깃허브에 txt 파일을 먼저 올려주세요.")
        else:
            # * 변경됨: 사용자가 직접 URL을 입력하는 대신, 찾은 txt 파일 목록 중 하나를 선택할 수 있는 드롭다운(선택 상자)을 만듭니다.
            selected_file = st.selectbox("학습할 텍스트 파일을 선택하세요", txt_files, key="study_file_select")
            
            # * 변경됨: 버튼 이름이 URL 불러오기에서 파일 선택하기로 바뀌었습니다.
            if st.button("파일 선택하기"):
                # 선택한 파일 이름으로 위에서 만든 파일 읽기 함수를 실행합니다.
                st.session_state.words = load_words_from_file(selected_file)
                # 파일을 새로 불러오면 학습 진행 상황을 처음으로 되돌립니다.
                st.session_state.study_index = 0
                st.session_state.is_studying = False
                st.success(f"'{selected_file}'에서 {len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
        
        # 파일에서 단어를 하나라도 불러왔을 때만 아래 기능들을 보여줍니다.
        if len(st.session_state.words) > 0:
            if st.button("랜덤으로 섞기"):
                # random.shuffle을 이용해 단어 리스트의 순서를 무작위로 섞습니다.
                random.shuffle(st.session_state.words)
                st.session_state.study_index = 0
                st.success("단어 목록이 랜덤으로 섞였습니다!")
                
            if st.button("학습하기"):
                # 학습하기 버튼을 누르면 화면에 단어를 출력하기 시작합니다.
                st.session_state.is_studying = True
                st.session_state.study_index = 0
                
            if st.session_state.is_studying:
                st.write("---")
                # 현재 몇 번째 단어인지 확인하여, 전체 개수보다 작을 때만 단어를 보여줍니다.
                if st.session_state.study_index < len(st.session_state.words):
                    current_word = st.session_state.words[st.session_state.study_index]
                    
                    # HTML 코드를 이용해 글자 크기를 키워서 단어와 의미를 출력합니다.
                    st.markdown(f"<div style='font-size: 24px;'>단어: {current_word['word']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 24px;'>의미: {current_word['meaning']}</div>", unsafe_allow_html=True)
                    
                    # 다음 버튼을 누르면 인덱스(순서)를 1 증가시키고 화면을 새로고침합니다.
                    if st.button("다음"):
                        st.session_state.study_index += 1
                        st.rerun()
                else:
                    # 모든 단어를 다 본 경우 아래 문구를 출력합니다.
                    st.success("모두 학습했습니다.")
                    
    elif page == '테스트':
        st.header("테스트 파트")
        
        # * 변경됨: 테스트 파트에서도 동일하게 txt 파일이 있는지 확인합니다.
        if len(txt_files) == 0:
            st.warning("현재 폴더에 txt 파일이 없습니다. 깃허브에 txt 파일을 먼저 올려주세요.")
        else:
            # * 변경됨: 테스트 파트용 파일 선택 상자를 만듭니다.
            selected_file_test = st.selectbox("테스트할 텍스트 파일을 선택하세요", txt_files, key="test_file_select")
            
            # * 변경됨: 버튼 이름 변경
            if st.button("파일 선택하기", key="test_load"):
                st.session_state.words = load_words_from_file(selected_file_test)
                # 테스트 파트에서는 임시 대기열(test_queue)에 단어를 복사해 두고 넣고 빼는 작업을 반복하기 위해 list()로 복사본을 만듭니다.
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
                # 대기열에 단어가 남아있다면 맨 위의 단어를 뽑아서(pop) 현재 단어로 설정합니다.
                if len(st.session_state.test_queue) > 0:
                    st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                    # 0과 1 중 무작위로 골라 왼쪽과 오른쪽 중 무엇을 보여줄지 결정합니다.
                    st.session_state.test_display_side = random.choice([0, 1])
                else:
                    st.session_state.current_test_word = None
                    
            if st.session_state.is_testing:
                st.write("---")
                if st.session_state.current_test_word is not None:
                    # 0이면 단어, 1이면 의미 텍스트를 선택합니다.
                    if st.session_state.test_display_side == 0:
                        display_text = st.session_state.current_test_word['word']
                    else:
                        display_text = st.session_state.current_test_word['meaning']
                    
                    # 사용자가 보기 편하게 텍스트를 크게 중앙에 배치합니다.
                    st.markdown(f"<div style='font-size: 40px; text-align: center; padding: 20px;'>{display_text}</div>", unsafe_allow_html=True)
                    
                    # 3개의 버튼을 나란히 배치하기 위해 가상의 열을 3개 만듭니다.
                    col1, col2, col3 = st.columns(3)
                    
                    # 아래는 사용자의 이해도 응답에 따라 단어를 대기열의 특정 위치로 다시 집어넣는 핵심 이동 로직입니다.
                    with col1:
                        if st.button("아는 단어"):
                            n = len(st.session_state.test_queue)
                            # 아래에서 5번째 ~ 10번째 줄 사이의 위치를 계산합니다.
                            pos = n - random.randint(5, 10)
                            pos = max(0, pos) # 만약 단어가 몇 개 안 남아서 위치가 음수가 되면 최상단(0)으로 고정합니다.
                            st.session_state.test_queue.insert(pos, st.session_state.current_test_word)
                            
                            # 다음 단어를 뽑습니다.
                            if len(st.session_state.test_queue) > 0:
                                st.session_state.current_test_word = st.session_state.test_queue.pop(0)
                                st.session_state.test_display_side = random.choice([0, 1])
                            else:
                                st.session_state.current_test_word = None
                            st.rerun() # 화면을 새로고침하여 다음 단어를 보여줍니다.
                            
                    with col2:
                        if st.button("모르는 단어"):
                            n = len(st.session_state.test_queue)
                            # 위에서 5번째 ~ 10번째 줄 사이로 이동시킵니다.
                            pos = random.randint(5, 10)
                            pos = min(n, pos) # 대기열 길이보다 큰 위치로 벗어나지 않게 막아줍니다.
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
                            # 위에서 10번째 줄과 아래에서 10번째 줄 사이의 구간을 계산합니다.
                            lower = min(n, 10)
                            upper = max(0, n - 10)
                            # 리스트 길이가 너무 짧아서 위아래 순서가 꼬이는 것을 방지합니다.
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