import streamlit as st
import requests
import random

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

# 깃허브의 텍스트 파일을 인터넷을 통해 읽어오는 함수입니다.
def load_words_from_github(url):
    try:
        # url에 접속해서 파일의 내용을 가져옵니다.
        response = requests.get(url)
        # 한글이 깨지는 것을 방지하기 위해 utf-8 방식으로 인코딩합니다.
        response.encoding = 'utf-8'
        # 줄바꿈 문자를 기준으로 한 줄씩 나눕니다.
        lines = response.text.split('\n')
        
        parsed_words = []
        for line in lines:
            # * 주의: 콜론(:)이 있는 줄만 정상적인 데이터로 인식하고 처리합니다.
            if ':' in line:
                # 콜론을 기준으로 왼쪽 내용과 오른쪽 내용으로 분리합니다.
                parts = line.split(':')
                # 양 끝의 공백을 제거하고 저장합니다.
                word = parts[0].strip()
                meaning = parts[1].strip()
                parsed_words.append({'word': word, 'meaning': meaning})
        return parsed_words
    except Exception as e:
        # 주소를 잘못 입력하거나 인터넷 연결이 안 될 때 에러를 보여줍니다.
        st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")
        return []

def main():
    # 프로그램을 시작할 때 가장 먼저 세션 상태를 준비합니다.
    init_session_state()
    
    st.title("단어 암기 프로그램")
    
    # 사이드바(화면 왼쪽)에 학습과 테스트를 선택할 수 있는 라디오 버튼을 만듭니다.
    st.sidebar.title("메뉴")
    page = st.sidebar.radio("파트를 선택하세요", ['학습', '테스트'])
    
    if page == '학습':
        st.header("학습 파트")
        
        # 사용자가 깃허브 파일의 주소를 직접 입력할 수 있는 텍스트 상자입니다.
        # 예: https://raw.githubusercontent.com/사용자이름/저장소/main/word.txt
        github_url = st.text_input("깃허브 txt 파일의 Raw URL을 입력하세요 (파일을 선택하는 공간입니다)")
        
        if st.button("파일 불러오기"):
            if github_url:
                st.session_state.words = load_words_from_github(github_url)
                # 파일을 새로 불러오면 학습 진행 상황을 처음으로 되돌립니다.
                st.session_state.study_index = 0
                st.session_state.is_studying = False
                st.success(f"{len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
        
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
                    
                    # HTML 코드를 이용해 폰트 크기를 키워서 단어와 의미를 출력합니다.
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
        
        github_url = st.text_input("파일을 선택하세요. (깃허브 Raw URL 입력)", key="test_url")
        
        if st.button("파일 불러오기", key="test_load"):
            if github_url:
                st.session_state.words = load_words_from_github(github_url)
                # * 중요: 테스트 파트에서는 임시 대기열(test_queue)에 단어를 복사해 두고, 
                # 넣고 빼는 작업을 반복하기 위해 list()로 복사본을 만듭니다.
                st.session_state.test_queue = list(st.session_state.words)
                st.session_state.is_testing = False
                st.success(f"{len(st.session_state.words)}개의 단어를 성공적으로 불러왔습니다!")
                
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
                    
                    # 3개의 버튼을 나란히 배치하기 위해 가상의 열을 만듭니다.
                    col1, col2, col3 = st.columns(3)
                    
                    # * 아래는 사용자의 이해도 응답에 따라 단어를 대기열의 특정 위치로 다시 집어넣는 핵심 이동 로직입니다.
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
                            st.rerun() # 화면 새로고침
                            
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
                            # 리스트 길이가 짧을 경우 위아래 순서가 꼬이는 것을 방지합니다.
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