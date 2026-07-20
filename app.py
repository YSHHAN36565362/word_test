import streamlit as st
import random
import requests
import base64
import re
import calendar
from datetime import datetime, date, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

# (중략: init_session_state, parse_word_text, parse_words_with_validation 등은 기존과 동일)
# ... [이전 코드의 파싱 및 유틸리티 함수들을 그대로 유지하세요] ...

# ---------------------------
# 수정된 UI 부분: 폴더 선택 및 설정 이동
# ---------------------------

def render_sidebar_controls(prefix):
    """설정 및 폴더 선택을 사이드바에 배치"""
    with st.sidebar:
        st.write("---")
        st.subheader("⚙️ 설정 및 폴더 선택")
        
        # 1. 폴더 목록 자동 감지
        status, data = github_get_contents_cached("word_list")
        if status == 200:
            categories = [item['name'] for item in data if item['type'] == 'dir']
            main_category = st.selectbox("대분류 선택", categories, key=f"{prefix}_main_category")
            
            # 하위 폴더 스캔
            sub_status, sub_data = github_get_contents_cached(f"word_list/{main_category}")
            if sub_status == 200:
                sub_folders = [f"word_list/{main_category}/{item['name']}" for item in sub_data if item['type'] == 'dir']
                if sub_folders:
                    selected_folders = st.multiselect("학습 폴더 선택", sub_folders, default=sub_folders, key=f"{prefix}_folders")
                else:
                    selected_folders = [f"word_list/{main_category}"]
            else:
                selected_folders = [f"word_list/{main_category}"]
        
        st.write("---")
        render_under_card_view_controls(prefix)
    
    return selected_folders

# ---------------------------
# 연습 파트 레이아웃 개선
# ---------------------------
def render_practice_part():
    st.header("연습 파트")
    
    # 설정은 사이드바로 이동
    selected_folders = render_sidebar_controls("practice")
    
    # ... (파일 선택 로직은 기존처럼 selected_folders를 기반으로 수행) ...
    
    if st.session_state.is_practicing and st.session_state.current_practice_word:
        # 1. 고정 영역: 정답/힌트/평가 버튼
        c1, c2 = st.columns(2)
        has_hint = bool(st.session_state.current_practice_word.get("hint", "").strip())
        
        with c1:
            if st.button("정답 확인", use_container_width=True): st.session_state.show_answer = True
        with c2:
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint): st.session_state.practice_show_hint = True
        
        # 숫자 평가 버튼 (정답 확인 필수)
        s1, s2, s3, s4 = st.columns(4)
        if s1.button("100%", disabled=not st.session_state.show_answer, use_container_width=True): handle_practice_score(100); st.rerun()
        if s2.button("60%", disabled=not st.session_state.show_answer, use_container_width=True): handle_practice_score(60); st.rerun()
        # ... (나머지 버튼)

        st.write("---")
        
        # 2. 카드 영역 (고정)
        # (CSS 스타일을 적용하여 높이를 고정하면 더 좋습니다)
        st.markdown(f"<div class='practice-question'>문제: {question_text}</div>", unsafe_allow_html=True)
        if st.session_state.practice_show_hint: st.info(...)
        if st.session_state.show_answer: st.markdown(...)

# ---------------------------
# Main (스타일 및 실행)
# ---------------------------
def main():
    init_session_state()
    apply_global_style()
    # ... (나머지 로직)