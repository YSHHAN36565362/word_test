import streamlit as st
import streamlit.components.v1 as components
import random
import requests
import base64
import re
import hmac
import json
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="단어 암기 프로그램",
    page_icon=None,
    layout="centered"
)

KOREA_TZ = ZoneInfo("Asia/Seoul")
PROGRESS_FOLDER = "progress_logs"
WRONGNOTE_FOLDER = "wrong_notes"  # [신규] 시험 오답만 모아두는 GitHub 폴더
STATS_FOLDER = "study_stats"      # [신규] 일자별 학습 통계 로그 폴더
RADICAL_LIBRARY_FILE = "resources/radicals.json"  # [신규] 한자 구성요소(부수) 공용 사전


# ---------------------------
# 1. Session State 초기화
# ---------------------------
def init_session_state() -> None:
    defaults = {
        "words": [],
        "current_files_label": [],
        "favorite_words": [],  # [신규] 즐겨찾기(별표) 표시한 단어 (word 문자열 집합)

        "study_index": 0,
        "is_studying": False,
        "study_show_hint": False,

        "practice_queue": [],
        "practice_total_count": 0,
        "practice_done_count": 0,
        "current_practice_word": None,
        "is_practicing": False,
        "practice_display_side": 0,
        "practice_mode": "random",
        "practice_show_answer": False,
        "practice_show_hint": False,
        "practice_result_saved": False,  # [신규] 연습 종료 시 통계 저장을 1회만 수행하기 위한 플래그

        "exam_queue": [],
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
        "exam_wrong_words": [],  # [신규] 이번 시험 회차에서 "틀림"으로 채점된 단어 목록
        "exam_result_saved": False,  # [신규] 시험 종료 시 오답노트/통계 저장을 1회만 수행하기 위한 플래그

        "font_scale": 1.0,
        "theme_mode": "다크 모드",

        "script_lines": [],
        "script_index": 0,
        "is_scripting": False,

        "sidebar_main_cat": None,
        "sidebar_sub_cats": [],

        "active_part": None,
        "current_page_select": "학습",

        "user_id": "",

        # [신규] 상단 라디오 대신 쓸 페이지 네비게이션에서, "통계" 탭 캐시
        "stats_summary_cache": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_focus_active() -> bool:
    """학습/연습/시험/지문 중 하나라도 진행 중이면 True. 이 경우 상단 UI를 최소화한다."""
    return (
        st.session_state.is_studying
        or st.session_state.is_practicing
        or st.session_state.is_examining
        or st.session_state.is_scripting
    )


def exit_focus_mode() -> None:
    """진행 중인 세션을 종료하고 전체 UI(제목, 파트 이동, 파일 선택 등)를 다시 보여준다."""
    st.session_state.is_studying = False
    st.session_state.is_practicing = False
    st.session_state.is_examining = False
    st.session_state.is_scripting = False
    st.session_state.active_part = None


def render_exit_button(label: str = "학습 종료하기") -> None:
    """화면 맨 아래에 작게 배치되는 종료 버튼. 누르면 전체 UI로 돌아간다."""
    st.write("")
    left, mid, right = st.columns([3, 2, 3])
    with mid:
        if st.button(label, use_container_width=True, key=f"exit_focus_{label}"):
            exit_focus_mode()
            st.rerun()


# ---------------------------
# 2. 글로벌 CSS 스타일
# ---------------------------
def apply_global_style() -> None:
    scale = st.session_state.font_scale
    base = int(16 * scale)

    is_dark = (st.session_state.theme_mode == "다크 모드")
    focus_on = is_focus_active()

    card_bg = "#22222b" if is_dark else "#ffffff"
    border_color = "#38383f" if is_dark else "#e4e4e8"
    text_color = "#f0f0f3" if is_dark else "#1c1c1f"
    word_color = "#8aa6ff" if is_dark else "#4a5fd6"
    hint_bg = "#2a2a33" if is_dark else "#f2f2f6"
    hint_text = "#d8d8de" if is_dark else "#42424a"
    ans_color = "#5fbf7a" if is_dark else "#1f8a44"
    muted_color = "#98989f" if is_dark else "#6b6b72"
    accent_bg = "#1f2233" if is_dark else "#eef0fa"
    accent_text = "#9db2ff" if is_dark else "#3d4ea8"
    sticky_bg = "#1a1a20" if is_dark else "#fafafc"

    focus_header_css = """
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0.4rem !important; }
    """ if focus_on else ""

    st.markdown(f"""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');

        html, body, [data-testid="stAppViewContainer"] {{
            font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}

        html {{ font-size: clamp(14px, 1vw + 10px, {base}px); }}

        .block-container {{
            padding-top: 1rem;
            padding-bottom: 1.6rem;
            max-width: 720px;
        }}

        {focus_header_css}

        h1, h2, h3 {{ font-weight: 700 !important; letter-spacing: -0.01em; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to   {{ opacity: 1; }}
        }}

        /* ---------- 진행 중 화면 상단 고정 조작바 (정답 확인 / 힌트 보기) ---------- */
        .sticky-action-bar {{
            position: sticky;
            top: 0;
            z-index: 999;
            background: {sticky_bg};
            padding: 8px 0 8px 0;
            margin-bottom: 6px;
            border-bottom: 1px solid {border_color};
        }}
        .sticky-action-bar .stButton > button {{
            padding-top: 0.55rem !important;
            padding-bottom: 0.55rem !important;
        }}

        .study-card {{
            background: {card_bg};
            border: 1px solid {border_color};
            border-radius: 14px;
            padding: clamp(16px, 3vw, 28px) clamp(14px, 3vw, 24px);
            margin: 10px 0;
            animation: fadeIn 0.25s ease both;
        }}
        .word-text {{
            font-size: clamp(1.3rem, 2.4vw, 1.7rem) !important;
            font-weight: 700; margin-bottom: 8px; text-align: center;
            color: {word_color};
        }}
        .meaning-text {{ font-size: clamp(1.1rem, 2vw, 1.4rem) !important; color: {text_color}; margin-bottom: 4px; text-align: center; }}
        .hint-box {{
            font-size: clamp(0.92rem, 1.6vw, 1.05rem) !important; color: {hint_text}; background-color: {hint_bg};
            padding: 10px 14px; border-radius: 10px; margin-top: 10px; line-height: 1.6;
        }}
        .qa-compact {{ padding: clamp(14px, 3vw, 22px) clamp(14px, 3vw, 20px) !important; margin: 6px 0 !important; }}
        .qa-compact .test-question {{ padding: 2px 4px 2px 4px !important; }}
        .qa-compact .test-answer {{ margin: 2px 0 4px 0 !important; }}
        .qa-compact .hint-box {{ margin-top: 6px !important; }}
        .hint-box b {{ color: {muted_color}; font-weight: 600; }}
        .script-text {{ font-size: clamp(1.1rem, 2vw, 1.35rem) !important; font-weight: 600; color: {word_color}; text-align: left; line-height: 1.85; }}

        .test-question {{
            font-size: clamp(1.5rem, 4vw, 2.2rem) !important; color: {text_color}; text-align: center; padding: 10px 8px 4px 8px;
            font-weight: 700; word-break: break-word;
        }}
        .test-answer {{
            font-size: clamp(1.05rem, 1.9vw, 1.3rem) !important; text-align: center; color: {ans_color}; font-weight: 700; margin: 2px 0 10px 0;
        }}

        .progress-caption {{ text-align: center; color: {muted_color}; margin-top: 4px; font-size: 0.85rem; }}

        .active-files-box {{
            background: {accent_bg};
            color: {accent_text};
            border-radius: 10px;
            padding: 8px 12px;
            margin: 6px 0 2px 0;
            font-size: 0.8rem;
            line-height: 1.5;
            word-break: break-all;
        }}

        div[data-testid="stButton"] > button {{
            font-weight: 600 !important; border-radius: 10px !important;
            transition: background-color 0.12s ease !important;
        }}

        div[data-testid="stProgress"] div[role="progressbar"] > div {{
            transition: width 0.4s ease !important;
        }}

        div[data-testid="stCheckbox"] {{ display: flex; justify-content: flex-start; }}
        .file-check-row div[data-testid="stCheckbox"] label p {{
            white-space: nowrap !important;
            overflow-x: auto !important;
        }}

        div[data-testid="stAlert"] {{ border-radius: 10px !important; }}

        div[data-testid="stRadio"] > div {{
            background: {hint_bg};
            border-radius: 12px;
            padding: 4px;
            gap: 2px !important;
        }}
        div[data-testid="stRadio"] label {{
            border-radius: 9px !important;
            padding: 7px 10px !important;
            font-weight: 600 !important;
        }}
        div[data-testid="stRadio"] label:has(input:checked) {{
            background: {word_color} !important;
        }}
        div[data-testid="stRadio"] label:has(input:checked) p {{
            color: #ffffff !important;
        }}
        div[data-testid="stRadio"] input {{ display: none !important; }}

        .cat-group-title {{
            font-weight: 700; font-size: 0.95rem; margin: 10px 0 4px 0; color: {word_color};
        }}

        @media (max-width: 1024px) {{
            .block-container {{ padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
            .mobile-stack div[data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
                gap: 6px !important;
            }}
            .mobile-stack div[data-testid="column"] {{
                width: 100% !important;
                min-width: 100% !important;
                padding: 0 !important;
            }}
        }}

        @media (min-width: 1400px) {{
            .block-container {{ max-width: 820px; }}
        }}
        </style>
    """, unsafe_allow_html=True)


def mobile_stack_container(key: str):
    box = st.container(key=key)
    return box


def sticky_action_bar(key: str):
    """정답 확인/다음 버튼과 힌트 버튼을 화면 맨 위에 고정해서 스크롤해도 항상 보이게 한다."""
    st.markdown('<div class="sticky-action-bar">', unsafe_allow_html=True)
    box = st.container(key=key)
    st.markdown('</div>', unsafe_allow_html=True)
    return box


# ---------------------------
# 2-1. [신규] 떠다니는 애플펜슬 메모장 (드래그 이동 / 크기 조절 / 닫기)
# ---------------------------
def inject_floating_memo_window() -> None:
    """
    화면 우측 하단의 동그란 "메모" 버튼을 누르면 열리는, 자유롭게 옮기고 크기를 바꿀 수 있는
    필기 창을 페이지에 주입한다.

    기존 방식(좌/우 고정 도크)은 components.html이 만드는 작은 iframe 안에서 position:fixed를
    걸었기 때문에, 그 iframe 박스 자체가 좁으면 카드 위로 겹쳐 보이는 문제가 있었다.
    이 함수는 그 iframe 안이 아니라 실제 최상위 페이지(window.parent.document)에 직접
    버튼/창 DOM을 붙이므로, 화면 어디로든 자유롭게 드래그하고 원하는 크기로 늘릴 수 있다.
    (이 파일의 inject_keyboard_shortcuts / inject_session_keepalive 와 같은 방식.)

    Streamlit이 재실행(rerun)될 때마다 이 함수가 다시 호출되므로, 이미 만들어둔 DOM을
    중복 생성하지 않도록 window.parent.document에 플래그를 남겨 한 번만 붙인다.
    창의 위치/크기/열림상태와 필기 내용은 브라우저 localStorage에 저장되어 유지된다.
    """
    components.html("""
        <script>
        (function () {
            var doc = window.parent.document;
            if (doc.hasOwnProperty('_memoWindowAttached')) { return; }
            doc._memoWindowAttached = true;

            var win_ = window.parent;
            var STORAGE_STATE = "pencil_memo_window_state_v1";
            var STORAGE_STROKES = "pencil_memo_strokes_v1";

            var style = doc.createElement("style");
            style.textContent =
                '#memo-toggle-btn{position:fixed;bottom:22px;right:22px;z-index:99998;' +
                'width:52px;height:52px;border-radius:50%;background:#4a5fd6;color:#fff;' +
                'border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,0.35);}' +
                '#memo-window,#memo-window *{box-sizing:border-box;}' +
                '#memo-window{position:fixed;z-index:99999;background:#22222b;border:1px solid #444;' +
                'border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.5);display:flex;' +
                'flex-direction:column;overflow:hidden;min-width:240px;min-height:220px;}' +
                '#memo-titlebar{background:#2a2a33;color:#eee;padding:8px 10px;display:flex;' +
                'align-items:center;justify-content:space-between;cursor:move;user-select:none;' +
                'font-size:13px;font-weight:700;touch-action:none;}' +
                '#memo-titlebar button{background:transparent;border:none;color:#ccc;' +
                'font-size:16px;cursor:pointer;padding:0 4px;}' +
                '#memo-toolbar{display:flex;align-items:center;gap:6px;padding:6px 8px;' +
                'background:#22222b;border-bottom:1px solid #38383f;flex-wrap:wrap;}' +
                '#memo-toolbar button{font-size:11px;padding:5px 8px;border-radius:6px;' +
                'border:1px solid #444;background:#2a2a33;color:#eee;cursor:pointer;}' +
                '#memo-toolbar input[type=color]{width:24px;height:24px;padding:0;border:none;background:none;}' +
                '#memo-toolbar input[type=range]{width:60px;}' +
                '#memo-toolbar label{font-size:10px;color:#aaa;display:flex;align-items:center;' +
                'gap:2px;white-space:nowrap;}' +
                '#memo-canvas{display:block;flex:1;touch-action:none;cursor:crosshair;' +
                'background:#1a1a20;width:100%;border:none;margin:0;padding:0;}' +
                '#memo-resize-handle{position:absolute;right:0;bottom:0;width:18px;height:18px;' +
                'cursor:nwse-resize;touch-action:none;background:linear-gradient(135deg,' +
                'transparent 0 50%,#666 50% 60%,transparent 60% 70%,#666 70% 80%,transparent 80% 100%);}';
            doc.head.appendChild(style);

            var toggleBtn = doc.createElement("button");
            toggleBtn.id = "memo-toggle-btn";
            toggleBtn.title = "메모장 열기/닫기";
            toggleBtn.textContent = "메모";
            doc.body.appendChild(toggleBtn);

            var win = doc.createElement("div");
            win.id = "memo-window";
            win.innerHTML =
                '<div id="memo-titlebar"><span>메모장</span>' +
                '<button id="memo-close-btn" title="닫기">닫기</button></div>' +
                '<div id="memo-toolbar">' +
                '<button id="memo-undo-btn">되돌리기</button>' +
                '<button id="memo-clear-btn">지우기</button>' +
                '<button id="memo-save-btn">저장</button>' +
                '<input type="color" id="memo-color-input" value="#8aa6ff">' +
                '<input type="range" id="memo-width-input" min="1" max="12" value="2">' +
                '<label><input type="checkbox" id="memo-pen-only-input">펜만</label>' +
                '</div>' +
                '<canvas id="memo-canvas"></canvas>' +
                '<div id="memo-resize-handle"></div>';
            doc.body.appendChild(win);

            function loadState() {
                try {
                    var raw = win_.localStorage.getItem(STORAGE_STATE);
                    return raw ? JSON.parse(raw) : null;
                } catch (e) { return null; }
            }
            function saveState() {
                try {
                    var rect = win.getBoundingClientRect();
                    win_.localStorage.setItem(STORAGE_STATE, JSON.stringify({
                        open: win.style.display !== "none",
                        left: rect.left, top: rect.top, width: rect.width, height: rect.height
                    }));
                } catch (e) {}
            }

            var savedState = loadState();
            var vw = win_.innerWidth, vh = win_.innerHeight;
            var initLeft = savedState ? savedState.left : Math.max(10, vw - 340);
            var initTop = savedState ? savedState.top : 80;
            var initWidth = savedState ? savedState.width : 300;
            var initHeight = savedState ? savedState.height : 360;
            initLeft = Math.min(Math.max(0, initLeft), Math.max(0, vw - 100));
            initTop = Math.min(Math.max(0, initTop), Math.max(0, vh - 100));

            win.style.left = initLeft + "px";
            win.style.top = initTop + "px";
            win.style.width = initWidth + "px";
            win.style.height = initHeight + "px";
            win.style.display = (savedState && savedState.open) ? "flex" : "none";

            toggleBtn.addEventListener("click", function () {
                win.style.display = (win.style.display === "none") ? "flex" : "none";
                saveState();
            });
            doc.getElementById("memo-close-btn").addEventListener("click", function () {
                win.style.display = "none";
                saveState();
            });

            var titlebar = doc.getElementById("memo-titlebar");
            var dragging = false, dragOffsetX = 0, dragOffsetY = 0;
            titlebar.addEventListener("pointerdown", function (e) {
                if (e.target.closest("button")) { return; }
                dragging = true;
                var rect = win.getBoundingClientRect();
                dragOffsetX = e.clientX - rect.left;
                dragOffsetY = e.clientY - rect.top;
                try { titlebar.setPointerCapture(e.pointerId); } catch (err) {}
                e.preventDefault();
            });
            doc.addEventListener("pointermove", function (e) {
                if (!dragging) { return; }
                var newLeft = e.clientX - dragOffsetX;
                var newTop = e.clientY - dragOffsetY;
                newLeft = Math.min(Math.max(0, newLeft), win_.innerWidth - 60);
                newTop = Math.min(Math.max(0, newTop), win_.innerHeight - 40);
                win.style.left = newLeft + "px";
                win.style.top = newTop + "px";
            });
            function stopDrag() { if (dragging) { dragging = false; saveState(); } }
            doc.addEventListener("pointerup", stopDrag);
            doc.addEventListener("pointercancel", stopDrag);

            var resizeHandle = doc.getElementById("memo-resize-handle");
            var resizing = false;
            resizeHandle.addEventListener("pointerdown", function (e) {
                resizing = true;
                try { resizeHandle.setPointerCapture(e.pointerId); } catch (err) {}
                e.stopPropagation();
                e.preventDefault();
            });
            doc.addEventListener("pointermove", function (e) {
                if (!resizing) { return; }
                var rect = win.getBoundingClientRect();
                var newWidth = Math.max(240, e.clientX - rect.left);
                var newHeight = Math.max(220, e.clientY - rect.top);
                win.style.width = newWidth + "px";
                win.style.height = newHeight + "px";
                resizeCanvas();
            });
            function stopResize() { if (resizing) { resizing = false; saveState(); } }
            doc.addEventListener("pointerup", stopResize);
            doc.addEventListener("pointercancel", stopResize);

            var canvas = doc.getElementById("memo-canvas");
            var ctx = canvas.getContext("2d");
            var strokes = [];
            var currentStroke = null;
            var penOnly = false;

            function loadStrokes() {
                try {
                    var raw = win_.localStorage.getItem(STORAGE_STROKES);
                    strokes = raw ? JSON.parse(raw) : [];
                } catch (e) { strokes = []; }
            }
            function saveStrokes() {
                try { win_.localStorage.setItem(STORAGE_STROKES, JSON.stringify(strokes)); } catch (e) {}
            }
            function redraw() {
                var rect = canvas.getBoundingClientRect();
                ctx.clearRect(0, 0, rect.width, rect.height);
                for (var i = 0; i < strokes.length; i++) { drawStroke(strokes[i]); }
            }
            function drawStroke(s) {
                if (!s.points || s.points.length < 2) { return; }
                ctx.beginPath();
                ctx.strokeStyle = s.color;
                ctx.lineWidth = s.width;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.moveTo(s.points[0].x, s.points[0].y);
                for (var i = 1; i < s.points.length; i++) { ctx.lineTo(s.points[i].x, s.points[i].y); }
                ctx.stroke();
            }
            function resizeCanvas() {
                var rect = canvas.getBoundingClientRect();
                var dpr = win_.devicePixelRatio || 1;
                canvas.width = Math.max(1, Math.round(rect.width * dpr));
                canvas.height = Math.max(1, Math.round(rect.height * dpr));
                ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
                redraw();
            }
            function getPos(e) {
                // e.target이 캔버스 자신일 때는(포인터 캡처가 성공했거나, 캔버스 위에 있을 때)
                // 브라우저가 직접 계산해주는 offsetX/offsetY를 쓴다. 이 값은 테두리, 박스 모델,
                // 배율(dpr) 등을 브라우저가 알아서 반영해서 주기 때문에 우리가 직접 계산하는 것보다 정확하다.
                if (e.target === canvas) {
                    return { x: e.offsetX, y: e.offsetY };
                }
                // 드물게 캡처가 실패해 포인터가 캔버스 밖으로 나간 경우에만 수동 계산으로 대체한다.
                var rect = canvas.getBoundingClientRect();
                return {
                    x: e.clientX - rect.left - canvas.clientLeft,
                    y: e.clientY - rect.top - canvas.clientTop
                };
            }

            canvas.addEventListener("pointerdown", function (e) {
                if (penOnly && e.pointerType === "touch") { return; }
                try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
                var color = doc.getElementById("memo-color-input").value;
                var width = parseFloat(doc.getElementById("memo-width-input").value);
                currentStroke = { color: color, width: width, points: [getPos(e)] };
                e.preventDefault();
            });
            doc.addEventListener("pointermove", function (e) {
                if (!currentStroke) { return; }
                currentStroke.points.push(getPos(e));
                var n = currentStroke.points.length;
                if (n >= 2) {
                    ctx.beginPath();
                    ctx.strokeStyle = currentStroke.color;
                    ctx.lineWidth = currentStroke.width;
                    ctx.lineCap = "round";
                    ctx.lineJoin = "round";
                    ctx.moveTo(currentStroke.points[n - 2].x, currentStroke.points[n - 2].y);
                    ctx.lineTo(currentStroke.points[n - 1].x, currentStroke.points[n - 1].y);
                    ctx.stroke();
                }
                e.preventDefault();
            });
            function endStroke() {
                if (!currentStroke) { return; }
                if (currentStroke.points.length >= 2) { strokes.push(currentStroke); saveStrokes(); }
                currentStroke = null;
            }
            doc.addEventListener("pointerup", endStroke);
            doc.addEventListener("pointercancel", endStroke);

            doc.getElementById("memo-undo-btn").addEventListener("click", function () {
                strokes.pop(); saveStrokes(); redraw();
            });
            doc.getElementById("memo-clear-btn").addEventListener("click", function () {
                strokes = []; saveStrokes(); redraw();
            });
            doc.getElementById("memo-pen-only-input").addEventListener("change", function (e) {
                penOnly = e.target.checked;
            });
            doc.getElementById("memo-save-btn").addEventListener("click", function () {
                var exportCanvas = doc.createElement("canvas");
                exportCanvas.width = canvas.width;
                exportCanvas.height = canvas.height;
                var exportCtx = exportCanvas.getContext("2d");
                exportCtx.fillStyle = "#1a1a20";
                exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
                exportCtx.drawImage(canvas, 0, 0);
                var link = doc.createElement("a");
                link.download = "memo.png";
                link.href = exportCanvas.toDataURL("image/png");
                link.click();
            });

            loadStrokes();
            // setTimeout으로 "이쯤이면 크기가 잡혔겠지"하고 추측하는 대신,
            // 창 크기가 실제로 바뀌는 바로 그 순간(열릴 때 포함) 브라우저가 즉시 알려주는
            // ResizeObserver를 쓴다. 창을 열자마자 바로 그리기 시작해도, 캔버스 해상도가
            // 아직 안 맞은 상태에서 그려진 획이 리사이즈 타이밍에 사라지는 문제가 없어진다.
            if (typeof win_.ResizeObserver !== "undefined") {
                var canvasResizeObserver = new win_.ResizeObserver(function () { resizeCanvas(); });
                canvasResizeObserver.observe(win);
            } else {
                win_.addEventListener("resize", resizeCanvas);
                resizeCanvas();
            }
        })();
        </script>
    """, height=0, width=0)


def inject_session_keepalive() -> None:
    """
    브라우저가 서버에게 '나 아직 여기 있어요' 라는 신호를 주기적으로 보내는 기능입니다.
    이 신호가 끊기면, 사용자가 화면만 보고 아무 버튼도 누르지 않을 때
    서버가 '이 사람은 나갔다'고 오해해서 세션(학습 진행 상태)을 정리해버릴 수 있습니다.
    아래 코드는 90초(1.5분)마다 신호를 보내서, 30분 동안 최소 20번 이상 신호가 가도록 만들었습니다.
    """
    components.html("""
        <script>
        // 부모 창(실제 브라우저 탭)의 window 객체를 가져옵니다.
        const win = window.parent;

        // 이미 신호 타이머가 설정돼 있다면 중복으로 또 만들지 않도록 막습니다.
        // (화면이 다시 그려질 때마다 이 스크립트가 여러 번 실행될 수 있기 때문입니다.)
        if (!win.hasOwnProperty('_keepalive_attached')) {
            win._keepalive_attached = true;

            // 서버에게 아주 작은 요청을 보내서 '접속 중'임을 알리는 함수입니다.
            function sendPing() {
                try {
                    // no-store: 이 요청 결과를 브라우저가 저장(캐시)하지 않게 합니다.
                    // no-cors: 응답 내용은 필요 없고, 요청을 보냈다는 사실 자체가 중요합니다.
                    fetch(win.location.href, { method: 'GET', cache: 'no-store', mode: 'no-cors' });
                } catch (e) {
                    // 네트워크가 잠깐 끊기는 등의 이유로 실패해도 앱이 멈추지 않도록 무시합니다.
                }
            }

            // 90초(1.5분)마다 sendPing 함수를 반복 실행합니다.
            win._keepalive_timer = setInterval(sendPing, 90 * 1000);

            // 사용자가 다른 탭을 보다가 이 탭으로 다시 돌아왔을 때 즉시 신호를 한 번 더 보냅니다.
            // 브라우저는 화면에 보이지 않는 탭의 타이머를 느리게 돌리는 경우가 있기 때문입니다.
            win.document.addEventListener('visibilitychange', function () {
                if (win.document.visibilityState === 'visible') {
                    sendPing();
                }
            });

            // 스크립트가 처음 실행될 때도 신호를 한 번 바로 보내둡니다.
            sendPing();
        }
        </script>
    """, height=0, width=0)


def inject_keyboard_shortcuts() -> None:
    """스페이스바/H/Z/X/C/V 단축키를 입력창 밖에서만 동작하도록 주입한다."""
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
                else if (key === 'z') { clickBtn(['완벽함', '맞음']); }
                else if (key === 'x') { clickBtn(['조금 앎', '틀림']); }
                else if (key === 'c') { clickBtn(['헷갈림']); }
                else if (key === 'v') { clickBtn(['모름']); }
            });
        }
        </script>
    """, height=0, width=0)


def change_font_scale(amount: float) -> None:
    st.session_state.font_scale = max(0.8, min(2.0, st.session_state.font_scale + amount))


# ---------------------------
# 3. GitHub API 및 캐싱
# ---------------------------
def get_github_headers() -> dict:
    token = str(st.secrets["github_token"]).strip()
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def get_repo_info() -> tuple:
    owner = str(st.secrets["github_owner"]).strip()
    repo = str(st.secrets["github_repo"]).strip()
    branch = str(st.secrets["github_branch"]).strip()
    return owner, repo, branch


def github_status_message(status: int) -> str:
    messages = {
        401: "GitHub 인증에 실패했습니다. github_token 설정을 확인해주세요.",
        403: "GitHub API 요청 한도를 초과했거나 접근 권한이 없습니다. 잠시 후 다시 시도해주세요.",
        404: "요청한 경로를 GitHub 저장소에서 찾을 수 없습니다.",
    }
    return messages.get(status, f"GitHub API 오류가 발생했습니다 (status: {status}).")


@st.cache_data(ttl=1800, show_spinner=False)
def github_get_contents(path: str):
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path.strip(), safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return 0, {}
    return response.status_code, response.json() if response.status_code == 200 else {}

def get_dynamic_categories() -> tuple:
    status, data = github_get_contents("word_list")
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "dir"]), None
    return [], github_status_message(status)


def get_subfolders(main_category: str) -> list:
    status, data = github_get_contents(f"word_list/{main_category}")
    if status == 200 and isinstance(data, list):
        folders = [item["name"] for item in data if item["type"] == "dir"]
        return sorted(folders) if folders else []
    return []


def get_txt_files(folder_path: str) -> list:
    status, data = github_get_contents(folder_path)
    if status == 200 and isinstance(data, list):
        return sorted([item["name"] for item in data if item["type"] == "file" and item["name"].lower().endswith(".txt")])
    return []


def get_file_content(repo_file_path: str) -> str:
    status, data = github_get_contents(repo_file_path)
    if status == 200:
        return base64.b64decode(data.get("content", "")).decode("utf-8")
    return ""


def get_remote_file_sha(repo_path: str):
    """
    GitHub에 같은 경로의 파일이 이미 있는지 확인하고, 있다면 그 파일의 sha 값을 가져온다.
    GitHub Contents API는 '기존 파일을 덮어쓰기' 할 때 반드시 최신 sha를 함께 보내야 하며,
    그렇지 않으면 422 "sha" wasn't supplied 오류가 발생한다.
    30분짜리 캐시(github_get_contents)를 타면 방금 지운/새로 만든 파일의 sha가 낡을 수 있으므로
    이 함수는 캐시를 거치지 않고 항상 최신 상태를 직접 조회한다.
    """
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path.strip(), safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return None
    if response.status_code == 200:
        return response.json().get("sha")
    return None


def upload_text_to_github(folder_path: str, file_name: str, text_content: str):
    owner, repo, branch = get_repo_info()
    repo_path = f"{str(folder_path).strip()}/{str(file_name).strip()}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}"

    content_b64 = base64.b64encode(text_content.encode("utf-8")).decode("utf-8")

    def build_payload(sha):
        payload = {
            "message": f"{'Update' if sha else 'Add'} file: {repo_path}",
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        return payload

    existing_sha = get_remote_file_sha(repo_path)
    response = requests.put(url, headers=get_github_headers(), json=build_payload(existing_sha), timeout=30)

    # sha 조회 시점과 업로드 시점 사이의 타이밍 문제 등으로 "sha wasn't supplied" 오류가 나면,
    # 최신 sha를 한 번 더 가져와서 즉시 재시도한다. (방금 막 생성된 파일 등 엣지 케이스 대응)
    if response.status_code == 422 and "sha" in response.text.lower():
        retry_sha = get_remote_file_sha(repo_path)
        if retry_sha and retry_sha != existing_sha:
            response = requests.put(url, headers=get_github_headers(), json=build_payload(retry_sha), timeout=30)

    return response, repo_path


def delete_file_from_github(repo_path: str) -> bool:
    """주어진 경로의 파일을 GitHub에서 삭제한다. 파일이 없으면 아무 것도 하지 않는다."""
    sha = get_remote_file_sha(repo_path)
    if not sha:
        return False
    owner, repo, branch = get_repo_info()
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}"
    payload = {"message": f"Remove file: {repo_path}", "sha": sha, "branch": branch}
    try:
        response = requests.delete(url, headers=get_github_headers(), json=payload, timeout=15)
    except requests.RequestException:
        return False
    return response.status_code == 200


def clear_github_cache() -> None:
    st.cache_data.clear()


# ---------------------------
# 3-1. 사용자별 학습 진행 저장/불러오기 (GitHub 로그)
# ---------------------------
# 사용자가 "내 번호"를 입력하면, 그 번호를 파일명 삼아 진행 상황을 GitHub 저장소의
# progress_logs/{번호}/{파트}.json 경로에 저장한다. 사용자마다 별도 파일을 쓰기 때문에
# 20명이 동시에 접속해도 서로의 진행 상황을 덮어쓸 위험이 없다.
# (PROGRESS_FOLDER 상수는 파일 상단으로 이동하여 다른 폴더 상수들과 함께 관리한다.)


def sanitize_user_id(raw_id: str) -> str:
    """사용자가 입력한 번호에서 파일 경로에 쓸 수 없는 문자를 제거해 안전한 식별자로 만든다."""
    cleaned = re.sub(r"[^0-9A-Za-z_\-]", "", str(raw_id).strip())
    return cleaned[:40]


def progress_file_path(user_id: str, part: str) -> str:
    return f"{PROGRESS_FOLDER}/{user_id}/{part}.json"


def save_user_progress(user_id: str, part: str, data: dict) -> bool:
    """
    현재 학습/연습/시험/지문 진행 상태를 GitHub에 JSON으로 저장한다.
    저장에 실패하더라도(네트워크 오류 등) 학습 자체가 멈추지 않도록 예외를 삼키고 False를 반환한다.
    """
    if not user_id:
        return False
    try:
        payload = dict(data)
        payload["_saved_at"] = datetime.now(KOREA_TZ).isoformat()
        text_content = json.dumps(payload, ensure_ascii=False, indent=2)
        resp, _ = upload_text_to_github(f"{PROGRESS_FOLDER}/{user_id}", f"{part}.json", text_content)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def load_user_progress(user_id: str, part: str):
    """저장된 진행 상태를 불러온다. 항상 최신 값을 읽기 위해 캐시를 타지 않는다."""
    if not user_id:
        return None
    owner, repo, branch = get_repo_info()
    repo_path = progress_file_path(user_id, part)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        raw = base64.b64decode(response.json().get("content", "")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


def save_practice_progress() -> None:
    """[코드 개선] practice 파트에서 반복되던 저장 payload 조립 로직을 한 곳으로 모음."""
    if not st.session_state.user_id:
        return
    save_user_progress(st.session_state.user_id, "practice", {
        "files_label": st.session_state.current_files_label,
        "mode": st.session_state.practice_mode,
        "queue": st.session_state.practice_queue,
        "current_word": st.session_state.current_practice_word,
        "display_side": st.session_state.practice_display_side,
        "total_count": st.session_state.practice_total_count,
        "done_count": st.session_state.practice_done_count,
    })


def save_exam_progress() -> None:
    """[코드 개선] exam 파트에서 반복되던 저장 payload 조립 로직을 한 곳으로 모음."""
    if not st.session_state.user_id:
        return
    save_user_progress(st.session_state.user_id, "exam", {
        "files_label": st.session_state.current_files_label,
        "mode": st.session_state.exam_mode,
        "queue": st.session_state.exam_queue,
        "current_word": st.session_state.current_exam_word,
        "display_side": st.session_state.exam_display_side,
        "total_count": st.session_state.exam_total_count,
        "current_number": st.session_state.exam_current_number,
        "correct_count": st.session_state.exam_correct_count,
        "wrong_count": st.session_state.exam_wrong_count,
    })


def delete_user_progress(user_id: str, part: str) -> None:
    """해당 파트를 끝까지 완료했을 때, 다음에 또 '이어서 하기'가 뜨지 않도록 저장 기록을 지운다."""
    if not user_id:
        return
    try:
        delete_file_from_github(progress_file_path(user_id, part))
    except Exception:
        pass


# ---------------------------
# 3-2. [신규] 오답 노트 & 학습 통계 (GitHub 로그)
# ---------------------------
# 시험 파트에서 "틀림"으로 채점된 단어를 모아 wrong_notes/{내번호}.json 에 누적 저장한다.
# 오답 노트는 화면에서 "오답만 다시 풀기"로 바로 연습에 투입할 수 있다.
def wrongnote_path(user_id: str) -> str:
    return f"{WRONGNOTE_FOLDER}/{user_id}.json"


def load_wrong_notes(user_id: str) -> list:
    if not user_id:
        return []
    owner, repo, branch = get_repo_info()
    repo_path = wrongnote_path(user_id)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    try:
        raw = base64.b64decode(response.json().get("content", "")).decode("utf-8")
        data = json.loads(raw)
        return data.get("words", [])
    except Exception:
        return []


def save_wrong_notes(user_id: str, words: list) -> bool:
    """오답 단어 리스트를 (word, meaning, hint) 기준으로 중복 제거해 통째로 덮어쓴다."""
    if not user_id:
        return False
    seen, deduped = set(), []
    for w in words:
        key = (w.get("word", ""), w.get("meaning", ""), w.get("hint", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(w)
    try:
        payload = {"words": deduped, "_updated_at": datetime.now(KOREA_TZ).isoformat()}
        text_content = json.dumps(payload, ensure_ascii=False, indent=2)
        resp, _ = upload_text_to_github(WRONGNOTE_FOLDER, f"{user_id}.json", text_content)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def add_words_to_wrong_notes(user_id: str, new_wrong_words: list) -> None:
    """시험이 끝났을 때, 이번 회차의 오답들을 기존 오답 노트에 합쳐 저장한다."""
    if not user_id or not new_wrong_words:
        return
    existing = load_wrong_notes(user_id)
    save_wrong_notes(user_id, existing + new_wrong_words)


def remove_word_from_wrong_notes(user_id: str, word_data: dict) -> None:
    """오답 노트 화면에서 개별 단어를 '이제 외웠음' 처리로 제거할 때 사용."""
    if not user_id:
        return
    existing = load_wrong_notes(user_id)
    key = (word_data.get("word", ""), word_data.get("meaning", ""), word_data.get("hint", ""))
    filtered = [w for w in existing if (w.get("word", ""), w.get("meaning", ""), w.get("hint", "")) != key]
    save_wrong_notes(user_id, filtered)


# 학습 통계: 시험/연습을 마칠 때마다 그날 날짜로 한 줄씩 누적 기록한다.
# study_stats/{내번호}.json = [{"date": "2026-08-17", "part": "exam", "total": 10, "correct": 8}, ...]
def stats_path(user_id: str) -> str:
    return f"{STATS_FOLDER}/{user_id}.json"


def load_study_stats(user_id: str) -> list:
    if not user_id:
        return []
    owner, repo, branch = get_repo_info()
    repo_path = stats_path(user_id)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(repo_path, safe='/')}?ref={quote(branch)}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=15)
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    try:
        raw = base64.b64decode(response.json().get("content", "")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return []


def append_study_stat(user_id: str, part: str, total: int, correct: int) -> None:
    """시험/연습 종료 시점에 오늘 기록 한 줄을 추가한다. 실패해도 학습 흐름은 막지 않는다."""
    if not user_id:
        return
    try:
        records = load_study_stats(user_id)
        records.append({
            "date": datetime.now(KOREA_TZ).strftime("%Y-%m-%d"),
            "part": part,
            "total": total,
            "correct": correct,
        })
        # 기록이 지나치게 길어지지 않도록 최근 200건만 보관
        records = records[-200:]
        text_content = json.dumps(records, ensure_ascii=False, indent=2)
        upload_text_to_github(STATS_FOLDER, f"{user_id}.json", text_content)
    except Exception:
        pass


# ---------------------------
# 3-3. [신규] 한자 구성요소(부수) 공용 사전
# ---------------------------
# 단어마다 한자 풀이를 매번 새로 적으면, 같은 한자(예: 水, 日)가 여러 단어에 반복해서
# 나올 때마다 설명이 중복된다. 이 사전은 "한 글자당 설명 1개"만 GitHub에 저장해두고,
# 단어에 그 글자가 나올 때마다 자동으로 찾아서 보여주는 방식이다. 즉 단어 힌트에는
# 그 단어만의 뜻/쓰임을 적고, 한자 풀이는 이 공용 사전에서 자동으로 가져와 붙인다.
RADICAL_SEED_DATA = {
    "一": {"reading": "한 일", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 丁, 七, 丘, 不, 丈, 上."},
    "丨": {"reading": "뚫을 곤", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 中, 串."},
    "丶": {"reading": "점 주", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 丹, 丸, 主."},
    "丿": {"reading": "삐침 별", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 乃, 乖, 乘, 乎, 之."},
    "乙": {"reading": "새 을", "desc": "부수 위치: 발,제부수(乙)/방(乚). 이 부수가 쓰인 대표 한자: 乞, 乾, 九, 亂, 乳, 也."},
    "亅": {"reading": "갈고리 궐", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 了, 事, 予."},
    "二": {"reading": "두 이", "desc": "부수 위치: 머리,몸,변,발. 이 부수가 쓰인 대표 한자: 于, 互, 五, 云, 井."},
    "亠": {"reading": "돼지해머리 두", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 京, 亥, 亡, 交, 亨."},
    "人": {"reading": "사람 인", "desc": "부수 위치: 머리,변(亻). 이 부수가 쓰인 대표 한자: 仁, 今, 來, 價, 像."},
    "儿": {"reading": "어진사람 인", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 光, 兀, 兒, 克, 兄."},
    "入": {"reading": "들 입", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 內, 全, 兩."},
    "八": {"reading": "여덟 팔", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 其, 共, 公, 具, 兼."},
    "冂": {"reading": "멀 경", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 再, 冒, 円, 冊."},
    "冖": {"reading": "덮을 멱", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 冠, 冥."},
    "冫": {"reading": "얼음 빙", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 冷, 凍, 冬, 凜."},
    "几": {"reading": "안석 궤", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 凱, 凡."},
    "凵": {"reading": "입벌릴 감", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 凶, 凸, 凹, 出, 函."},
    "刀": {"reading": "칼 도", "desc": "부수 위치: 방(刂),발. 이 부수가 쓰인 대표 한자: 初, 券, 分, 切, 刃, 利."},
    "力": {"reading": "힘 력", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 勇, 勢, 動, 勸, 勵."},
    "勹": {"reading": "쌀 포", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 包, 匐, 勿."},
    "匕": {"reading": "비수 비", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 北, 化, 匙."},
    "匚": {"reading": "상자 방", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 匣, 匡, 匪."},
    "匸": {"reading": "감출 혜", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 區, 匿, 医."},
    "十": {"reading": "열 십", "desc": "부수 위치: 제부수,머리,변,발. 이 부수가 쓰인 대표 한자: 半, 南, 卍, 卑, 協."},
    "卜": {"reading": "점 복", "desc": "부수 위치: 제부수,머리,방. 이 부수가 쓰인 대표 한자: 占, 卡, 卨."},
    "卩": {"reading": "병부 절", "desc": "부수 위치: 방,발(㔾). 이 부수가 쓰인 대표 한자: 卽, 卵, 卿, 危, 卷."},
    "厂": {"reading": "기슭 엄", "desc": "부수 위치: 엄. 이 부수가 쓰인 대표 한자: 厄, 厭, 原."},
    "厶": {"reading": "사사 사", "desc": "부수 위치: 제부수,머리,발. 이 부수가 쓰인 대표 한자: 去, 參."},
    "又": {"reading": "또 우", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 友, 及, 反, 叛, 取."},
    "口": {"reading": "입 구", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 口, 叩, 哭, 告, 品."},
    "囗": {"reading": "나라 국", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 回, 固, 國, 四, 圖."},
    "土": {"reading": "흙 토", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 土, 地, 均, 基, 坤."},
    "士": {"reading": "선비 사", "desc": "부수 위치: 제부수,변,방,머리. 이 부수가 쓰인 대표 한자: 士, 壬, 壻, 壯, 壽."},
    "夂": {"reading": "뒤쳐져올 치", "desc": "부수 위치: 머리,발,받침. 이 부수가 쓰인 대표 한자: 夂, 备, 変, 处."},
    "夊": {"reading": "천천히걸을 쇠", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 夊, 夏, 复."},
    "夕": {"reading": "저녁 석", "desc": "부수 위치: 제부수,변,방,발. 이 부수가 쓰인 대표 한자: 夕, 多, 外, 夜, 夢."},
    "大": {"reading": "큰 대", "desc": "부수 위치: 제부수,머리,발. 이 부수가 쓰인 대표 한자: 大, 失, 央, 奇, 奉, 契."},
    "女": {"reading": "계집 녀", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 女, 娘, 委, 威, 嫌."},
    "子": {"reading": "아들 자", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 子, 孑, 孓, 孔, 孟, 季."},
    "宀": {"reading": "집 면", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 宀, 守, 宗, 家, 客."},
    "寸": {"reading": "마디 촌", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 寸, 封, 專, 對, 導."},
    "小": {"reading": "작을 소", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 小, 少, 当, 尔."},
    "尢": {"reading": "절름발이 왕", "desc": "부수 위치: 제부수,방,받침. 이 부수가 쓰인 대표 한자: 尢, 尤, 就, 尨."},
    "尸": {"reading": "주검 시", "desc": "부수 위치: 제부수,엄. 이 부수가 쓰인 대표 한자: 尸, 尺, 局, 尹, 屋, 屬."},
    "屮": {"reading": "왼손 좌", "desc": "부수 위치: 제부수,머리,발. 이 부수가 쓰인 대표 한자: 屮, 屰, 㞢, 屯, 㞷."},
    "山": {"reading": "메 산", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 山, 岬, 峰, 岸, 島, 巖."},
    "巛": {"reading": "내 천", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 巛, 巜, 巢, 巡, 巠."},
    "工": {"reading": "장인 공", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 工, 巨, 巧, 左, 差."},
    "己": {"reading": "몸 기", "desc": "부수 위치: 제부수,머리,발. 이 부수가 쓰인 대표 한자: 己, 已, 巳, 巴, 巽, 巷."},
    "巾": {"reading": "수건 건", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 巾, 帽, 常, 席, 帆."},
    "干": {"reading": "방패 간", "desc": "부수 위치: 제부수,발. 이 부수가 쓰인 대표 한자: 干, 年, 幷, 平, 幸, 幹."},
    "幺": {"reading": "작을 요", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 幺, 幾, 幽, 幼, 幻."},
    "广": {"reading": "집 엄", "desc": "부수 위치: 엄. 이 부수가 쓰인 대표 한자: 广, 康, 庫, 廣, 廳."},
    "廴": {"reading": "길게걸을 인", "desc": "부수 위치: 받침. 이 부수가 쓰인 대표 한자: 廴, 建, 廻, 延."},
    "廾": {"reading": "받들 공", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 廾, 弁, 弄, 弊."},
    "弋": {"reading": "주살 익", "desc": "부수 위치: 방,엄. 이 부수가 쓰인 대표 한자: 弋, 弌, 弍, 弎, 式, 弑."},
    "弓": {"reading": "활 궁", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 弓, 强, 弱, 弔, 張."},
    "彐": {"reading": "돼지머리 계", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 彖, 彝, 录, 归."},
    "彡": {"reading": "터럭 삼", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 彡, 彬, 彰, 影, 彩."},
    "彳": {"reading": "조금걸을 척", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 彳, 往, 徐, 得, 德."},
    "心": {"reading": "마음 심", "desc": "부수 위치: 변(忄),발(⺗). 이 부수가 쓰인 대표 한자: 心, 志, 感, 恭, 情, 慶, 愛."},
    "戈": {"reading": "창 과", "desc": "부수 위치: 방,엄. 이 부수가 쓰인 대표 한자: 戈, 戊, 成, 戟, 戰."},
    "戶": {"reading": "집 호", "desc": "부수 위치: 변,엄. 이 부수가 쓰인 대표 한자: 戶, 所, 扇, 房."},
    "手": {"reading": "손 수", "desc": "부수 위치: 제부수,변(扌),발. 이 부수가 쓰인 대표 한자: 手, 才, 打, 拜, 擧, 擊."},
    "支": {"reading": "지탱할 지", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 支, 攲."},
    "攴": {"reading": "칠 복", "desc": "부수 위치: 방(攵),발. 이 부수가 쓰인 대표 한자: 攴, 敲, 故, 敎, 敬."},
    "文": {"reading": "글월 문", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 文, 斑, 斕, 斉, 斐."},
    "斗": {"reading": "말 두", "desc": "부수 위치: 방,머리,발. 이 부수가 쓰인 대표 한자: 斗, 料, 㪳, 斝."},
    "斤": {"reading": "근 근", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 斤, 斧, 新, 斷."},
    "方": {"reading": "모 방", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 方, 旅, 旁, 族, 旗."},
    "无": {"reading": "없을 무", "desc": "부수 위치: 제부수,방. 이 부수가 쓰인 대표 한자: 无, 旡, 旣."},
    "日": {"reading": "날 일", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 日, 明, 景, 旬, 晝."},
    "曰": {"reading": "가로 왈", "desc": "부수 위치: 제부수,머리,발. 이 부수가 쓰인 대표 한자: 曰, 曲, 曷, 更, 書."},
    "月": {"reading": "달 월", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 月, 有, 㬼, 朞."},
    "木": {"reading": "나무 목", "desc": "부수 위치: 제부수,변,머리,발. 이 부수가 쓰인 대표 한자: 木, 東, 樹, 果, 權."},
    "欠": {"reading": "하품 흠", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 欠, 歌, 次."},
    "止": {"reading": "그칠 지", "desc": "부수 위치: 제부수,변,머리,발. 이 부수가 쓰인 대표 한자: 止, 正, 此, 歲, 歷."},
    "歹": {"reading": "살바른뼈 알", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 歹, 死, 殃, 殉."},
    "殳": {"reading": "몽둥이 수", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 殳, 殺, 段, 毆, 毅."},
    "毋": {"reading": "말 무", "desc": "부수 위치: 제부수,발. 이 부수가 쓰인 대표 한자: 毋, 毌, 母."},
    "比": {"reading": "견줄 비", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 比, 毕, 毘."},
    "毛": {"reading": "터럭 모", "desc": "부수 위치: 방,발,받침. 이 부수가 쓰인 대표 한자: 毛, 氈, 毫, 毯."},
    "氏": {"reading": "각시 씨", "desc": "부수 위치: 제부수,머리. 이 부수가 쓰인 대표 한자: 氏, 民, 氐."},
    "气": {"reading": "기운 기", "desc": "부수 위치: 엄. 이 부수가 쓰인 대표 한자: 氣, 氛, 氢, 氦."},
    "水": {"reading": "물 수", "desc": "부수 위치: 제부수,변,머리,발. 이 부수가 쓰인 대표 한자: 水, 永, 氷, 海, 洋, 沓."},
    "火": {"reading": "불 화", "desc": "부수 위치: 변,발(灬). 이 부수가 쓰인 대표 한자: 火, 然, 炎, 熱, 無, 烏."},
    "爪": {"reading": "손톱 조", "desc": "부수 위치: 머리(爫),받침. 이 부수가 쓰인 대표 한자: 爪, 爲, 爬."},
    "父": {"reading": "아버지 부", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 父, 爸, 爺."},
    "爻": {"reading": "사귈 효", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 爻, 爽, 爾."},
    "爿": {"reading": "나뭇조각 장", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 爿, 壯, 牀, 牆."},
    "片": {"reading": "조각 편", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 片, 版, 牌."},
    "牙": {"reading": "어금니 아", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 牙, 㸦, 㸧, 牚."},
    "牛": {"reading": "소 우", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 牛, 牟, 物, 牢."},
    "犬": {"reading": "개 견", "desc": "부수 위치: 변(犭),방,발. 이 부수가 쓰인 대표 한자: 犬, 狀, 狗, 獒, 獄, 獻."},
    "玄": {"reading": "검을 현", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 玄, 玆, 率."},
    "玉": {"reading": "구슬 옥", "desc": "부수 위치: 제부수,변(王),발. 이 부수가 쓰인 대표 한자: 玉, 王, 璧, 理."},
    "瓜": {"reading": "오이 과", "desc": "부수 위치: 방,몸. 이 부수가 쓰인 대표 한자: 瓜, 瓣, 瓢."},
    "瓦": {"reading": "기와 와", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 瓦, 甁, 甕."},
    "甘": {"reading": "달 감", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 甘, 甛, 甚, 甞."},
    "生": {"reading": "날 생", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 生, 産, 甥."},
    "用": {"reading": "쓸 용", "desc": "부수 위치: 제부수,발. 이 부수가 쓰인 대표 한자: 用, 甫, 甩, 甭."},
    "田": {"reading": "밭 전", "desc": "부수 위치: 제부수,변,머리,발. 이 부수가 쓰인 대표 한자: 田, 申, 男, 畓, 略."},
    "疋": {"reading": "짝 필", "desc": "부수 위치: 변,방. 이 부수가 쓰인 대표 한자: 疋, 疑, 疎."},
    "疒": {"reading": "병들어기댈 녁", "desc": "부수 위치: 엄. 이 부수가 쓰인 대표 한자: 疾病, 痛症, 癌, 療."},
    "癶": {"reading": "등질 발", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 發, 癸, 登."},
    "白": {"reading": "흰 백", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 白, 的, 皇, 百."},
    "皮": {"reading": "가죽 피", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 皮, 皺, 皰."},
    "皿": {"reading": "그릇 명", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 皿, 盛, 監, 盡, 盧."},
    "目": {"reading": "눈 목", "desc": "부수 위치: 머리,변,발. 이 부수가 쓰인 대표 한자: 目, 相, 眼, 看, 督."},
    "矛": {"reading": "창 모", "desc": "부수 위치: 변,머리. 이 부수가 쓰인 대표 한자: 矛, 矜, 矞."},
    "矢": {"reading": "화살 시", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 矢, 短, 矣, 矮."},
    "石": {"reading": "돌 석", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 石, 硬, 碧, 磬."},
    "示": {"reading": "보일 시", "desc": "부수 위치: 변(⺬),발. 이 부수가 쓰인 대표 한자: 示, 神, 祈禱, 禁, 福."},
    "禸": {"reading": "발자국 유", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 禸, 禽, 离, 禹."},
    "禾": {"reading": "벼 화", "desc": "부수 위치: 변,머리,몸,발. 이 부수가 쓰인 대표 한자: 禾, 秋, 秀, 秉, 積."},
    "穴": {"reading": "구멍 혈", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 穴, 空, 窓, 突."},
    "立": {"reading": "설 립", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 立, 端, 竟, 競."},
    "竹": {"reading": "대 죽", "desc": "부수 위치: 머리(⺮). 이 부수가 쓰인 대표 한자: 竹, 簡, 籐, 筆, 算."},
    "米": {"reading": "쌀 미", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 米, 糟, 糠, 糞, 粱, 糖."},
    "糸": {"reading": "가는실 멱", "desc": "부수 위치: 변(糹),발. 이 부수가 쓰인 대표 한자: 糸, 系, 繁, 緊, 繼."},
    "缶": {"reading": "장군 부", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 缶, 缺, 罄."},
    "网": {"reading": "그물 망", "desc": "부수 위치: 머리(罒). 이 부수가 쓰인 대표 한자: 网, 罕, 䍙, 羅, 罷."},
    "羊": {"reading": "양 양", "desc": "부수 위치: 머리(⺷),변(⺶),발. 이 부수가 쓰인 대표 한자: 羊, 美, 羚, 羔, 義."},
    "羽": {"reading": "깃 우", "desc": "부수 위치: 변,방,머리,발. 이 부수가 쓰인 대표 한자: 羽, 翼, 翁, 翅, 翰."},
    "老": {"reading": "늙을 로", "desc": "부수 위치: 머리(耂). 이 부수가 쓰인 대표 한자: 老, 考, 耈."},
    "而": {"reading": "말이을 이", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 而, 耐, 耑, 耍."},
    "耒": {"reading": "가래 뢰", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 耒, 耕, 耗."},
    "耳": {"reading": "귀 이", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 耳, 聽, 聲, 聞, 職."},
    "聿": {"reading": "붓 율", "desc": "부수 위치: 머리,방,발. 이 부수가 쓰인 대표 한자: 聿, 肅, 肆."},
    "肉": {"reading": "고기 육", "desc": "부수 위치: 변,발,방. 이 부수가 쓰인 대표 한자: 肉, 腐, 脚, 肩, 胡, 肘."},
    "臣": {"reading": "신하 신", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 臣, 臨, 臥."},
    "自": {"reading": "스스로 자", "desc": "부수 위치: 머리,변. 이 부수가 쓰인 대표 한자: 自, 臭."},
    "至": {"reading": "이를 지", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 至, 致, 臺."},
    "臼": {"reading": "절구 구", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 臼, 舅, 舊, 興."},
    "舌": {"reading": "혀 설", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 舌, 舒, 舍."},
    "舛": {"reading": "어그러질 천", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 舛, 舞."},
    "舟": {"reading": "배 주", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 舟, 船, 般, 艇."},
    "艮": {"reading": "괘이름 간", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 艮, 良, 艱."},
    "色": {"reading": "빛 색", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 色, 艷."},
    "艸": {"reading": "풀 초", "desc": "부수 위치: 제부수,머리(艹). 이 부수가 쓰인 대표 한자: 艸, 葡萄, 蔡, 蘇."},
    "虍": {"reading": "호피무늬 호", "desc": "부수 위치: 엄,방(虎). 이 부수가 쓰인 대표 한자: 虎, 虜, 虐, 號."},
    "虫": {"reading": "벌레 훼", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 虫, 蟲, 蝕, 螳螂, 蜜蜂, 蟹."},
    "血": {"reading": "피 혈", "desc": "부수 위치: 변,머리,발. 이 부수가 쓰인 대표 한자: 血, 衆, 衄."},
    "行": {"reading": "다닐 행", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 行, 街, 衛, 術."},
    "衣": {"reading": "옷 의", "desc": "부수 위치: 변(衤),발,몸. 이 부수가 쓰인 대표 한자: 衣, 袋, 裏, 裙, 複."},
    "襾": {"reading": "덮을 아", "desc": "부수 위치: 제부수,머리. 이 부수가 쓰인 대표 한자: 西, 要, 覆."},
    "見": {"reading": "볼 견", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 見, 視, 親, 覺."},
    "角": {"reading": "뿔 각", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 角, 解, 觜, 觸."},
    "言": {"reading": "말씀 언", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 言, 許, 語, 論, 譽."},
    "谷": {"reading": "골 곡", "desc": "부수 위치: 변,방. 이 부수가 쓰인 대표 한자: 谷, 谿."},
    "豆": {"reading": "콩 두", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 豆, 豌, 豈."},
    "豕": {"reading": "돼지 시", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 豕, 豚, 象, 豬."},
    "豸": {"reading": "벌레 치", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 豸, 貌, 豹."},
    "貝": {"reading": "조개 패", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 貝, 財, 賣買, 貨, 貪."},
    "赤": {"reading": "붉을 적", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 赤, 赦, 赫."},
    "走": {"reading": "달릴 주", "desc": "부수 위치: 받침. 이 부수가 쓰인 대표 한자: 走, 起, 趙, 越."},
    "足": {"reading": "발 족", "desc": "부수 위치: 발,변(𧾷). 이 부수가 쓰인 대표 한자: 足, 路, 蹇, 跳."},
    "身": {"reading": "몸 신", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 身, 軀."},
    "車": {"reading": "수레 거", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 車, 軍, 輪, 輕."},
    "辛": {"reading": "매울 신", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 辛, 辭, 辨."},
    "辰": {"reading": "별 진", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 辰, 辱, 農."},
    "辵": {"reading": "쉬엄쉬엄갈 착", "desc": "부수 위치: 제부수,받침(⻍). 이 부수가 쓰인 대표 한자: 辵, 近, 造, 道, 選, 邊."},
    "邑": {"reading": "고을 읍", "desc": "부수 위치: 제부수,방(⻏). 이 부수가 쓰인 대표 한자: 邑, 郡, 部, 鄕, 鄭."},
    "酉": {"reading": "닭 유", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 酉, 酒, 醉, 醫."},
    "釆": {"reading": "분별할 변", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 釆, 采, 釋."},
    "里": {"reading": "마을 리", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 里, 野, 量, 重."},
    "金": {"reading": "쇠 금", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 金, 銀, 銅, 釜, 鑿."},
    "長": {"reading": "길 장", "desc": "부수 위치: 제부수,변(镸). 이 부수가 쓰인 대표 한자: 長, 镹."},
    "門": {"reading": "문 문", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 門, 問, 聞, 閻, 關."},
    "阜": {"reading": "언덕 부(좌부변)", "desc": "부수 위치: 제부수,변(阝),몸,발. 이 부수가 쓰인 대표 한자: 阜, 防, 院, 隊, 陳, 隣."},
    "隶": {"reading": "미칠 이", "desc": "부수 위치: 제부수,방. 이 부수가 쓰인 대표 한자: 隶, 隷."},
    "隹": {"reading": "새 추", "desc": "부수 위치: 방,머리,발. 이 부수가 쓰인 대표 한자: 隹, 雄, 集, 雙, 離."},
    "雨": {"reading": "비 우", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 雨, 雪, 電, 露, 霜, 霧."},
    "靑": {"reading": "푸를 청", "desc": "부수 위치: 제부수,변,방. 이 부수가 쓰인 대표 한자: 靑, 靜, 靖."},
    "非": {"reading": "아닐 비", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 非, 靠, 靟."},
    "面": {"reading": "낯 면", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 面, 靤, 靨."},
    "革": {"reading": "가죽 혁", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 革, 靷, 靴, 鞠, 鞏."},
    "韋": {"reading": "가죽 위", "desc": "부수 위치: 변,방. 이 부수가 쓰인 대표 한자: 韋, 韓, 韜."},
    "韭": {"reading": "부추 구", "desc": "부수 위치: 제부수,발. 이 부수가 쓰인 대표 한자: 韭, 韮."},
    "音": {"reading": "소리 음", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 音, 韻, 響."},
    "頁": {"reading": "머리 혈", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 頁, 頃, 領, 順, 頭, 顯."},
    "風": {"reading": "바람 풍", "desc": "부수 위치: 변,방. 이 부수가 쓰인 대표 한자: 風, 颱, 飄."},
    "飛": {"reading": "날 비", "desc": "부수 위치: 방. 이 부수가 쓰인 대표 한자: 飛, 飜."},
    "食": {"reading": "밥 식", "desc": "부수 위치: 변(𩙿),발. 이 부수가 쓰인 대표 한자: 食, 飯, 飽."},
    "首": {"reading": "머리 수", "desc": "부수 위치: 제부수,변,방,발. 이 부수가 쓰인 대표 한자: 首, 馗, 馘."},
    "香": {"reading": "향기 향", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 香, 馝, 馨, 馥."},
    "馬": {"reading": "말 마", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 馬, 駐, 騎, 駕, 驚, 驛."},
    "骨": {"reading": "뼈 골", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 骨, 體, 髓."},
    "高": {"reading": "높을 고", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 高, 髙, 髚, 髝."},
    "髟": {"reading": "늘어질 표", "desc": "부수 위치: 머리. 이 부수가 쓰인 대표 한자: 髮, 鬚."},
    "鬥": {"reading": "싸울 투", "desc": "부수 위치: 몸. 이 부수가 쓰인 대표 한자: 鬥, 鬪."},
    "鬯": {"reading": "울창주 창", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 鬯, 鬱."},
    "鬲": {"reading": "막을 격", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 鬲, 䰚, 鬷."},
    "鬼": {"reading": "귀신 귀", "desc": "부수 위치: 받침,방,발. 이 부수가 쓰인 대표 한자: 鬼, 魂, 魅, 魔, 魏."},
    "魚": {"reading": "물고기 어", "desc": "부수 위치: 변,발. 이 부수가 쓰인 대표 한자: 魚, 魯, 鮮, 鯉."},
    "鳥": {"reading": "새 조", "desc": "부수 위치: 변,방,발. 이 부수가 쓰인 대표 한자: 鳥, 鴻, 鵬, 鶴, 鷹, 鸞."},
    "鹵": {"reading": "소금 로", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 鹵, 鹽, 鹹."},
    "鹿": {"reading": "사슴 록", "desc": "부수 위치: 제부수,엄,변,발. 이 부수가 쓰인 대표 한자: 鹿, 麗, 麒麟, 麏."},
    "麥": {"reading": "보리 맥", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 麥, 麪."},
    "麻": {"reading": "삼 마", "desc": "부수 위치: 제부수,엄. 이 부수가 쓰인 대표 한자: 麻, 麾."},
    "黃": {"reading": "누를 황", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 黃, 黇."},
    "黍": {"reading": "기장 서", "desc": "부수 위치: 제부수. 이 부수가 쓰인 대표 한자: 黍, 黎."},
    "黑": {"reading": "검을 흑", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 黑, 默, 點, 黨."},
    "黹": {"reading": "바느질할 치", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 黹, 黼, 黻."},
    "黽": {"reading": "맹꽁이 맹", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 黽, 鼈."},
    "鼎": {"reading": "솥 정", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 鼎, 鼒."},
    "鼓": {"reading": "북 고", "desc": "부수 위치: 머리,발. 이 부수가 쓰인 대표 한자: 鼓, 鼔, 鼖."},
    "鼠": {"reading": "쥐 서", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 鼠, 鼱, 鼴."},
    "鼻": {"reading": "코 비", "desc": "부수 위치: 제부수,변. 이 부수가 쓰인 대표 한자: 鼻, 鼾."},
    "齊": {"reading": "가지런할 제", "desc": "부수 위치: 제부수,몸. 이 부수가 쓰인 대표 한자: 齊, 齋."},
    "齒": {"reading": "이 치", "desc": "부수 위치: 제부수,변,발. 이 부수가 쓰인 대표 한자: 齒, 齡, 齧."},
    "龍": {"reading": "용 룡", "desc": "부수 위치: 발. 이 부수가 쓰인 대표 한자: 龍, 龕, 𪚥, 龏."},
    "龜": {"reading": "거북 귀", "desc": "부수 위치: 방,발. 이 부수가 쓰인 대표 한자: 龜."},
    "龠": {"reading": "피리 약", "desc": "부수 위치: 변. 이 부수가 쓰인 대표 한자: 龠, 龡, 龥, 䶳."},
}


def load_radical_library() -> dict:
    """
    공용 한자 사전을 GitHub에서 불러온다. 아직 파일이 없으면 빈 사전을 돌려준다.
    (다른 GitHub 조회처럼 30분 캐시를 그대로 활용한다.)
    """
    status, data = github_get_contents(RADICAL_LIBRARY_FILE)
    if status != 200:
        return {}
    try:
        raw = base64.b64decode(data.get("content", "")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def save_radical_library(library: dict) -> bool:
    try:
        text_content = json.dumps(library, ensure_ascii=False, indent=2, sort_keys=True)
        folder, filename = RADICAL_LIBRARY_FILE.rsplit("/", 1)
        resp, _ = upload_text_to_github(folder, filename, text_content)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def get_char_breakdown(word: str) -> list:
    """
    단어에 들어있는 한자(CJK 통합 한자) 중, 공용 사전에 등록된 글자만 뽑아서
    [(글자, {"reading":.., "desc":..}), ...] 형태로 돌려준다. 사전에 없는 글자는 그냥 건너뛴다.
    """
    library = load_radical_library()
    if not library:
        return []
    seen = set()
    result = []
    for ch in word:
        if ch in seen:
            continue
        if "\u4e00" <= ch <= "\u9fff" and ch in library:
            seen.add(ch)
            result.append((ch, library[ch]))
    return result


def render_char_breakdown(word: str) -> None:
    """단어 카드 아래에, 공용 사전에 등록된 한자가 있을 때만 접이식으로 보여준다."""
    breakdown = get_char_breakdown(word)
    if not breakdown:
        return
    with st.expander("한자 풀이"):
        for ch, info in breakdown:
            reading = info.get("reading", "")
            desc = info.get("desc", "")
            st.markdown(f"**{ch}**" + (f" ({reading})" if reading else "") + (f" — {desc}" if desc else ""))


def render_radical_library_part() -> None:
    """한자 공용 사전을 보고, 새 글자를 추가/수정/삭제하는 관리 화면."""
    st.header("한자 풀이 사전")
    st.caption(
        "여기 등록한 한자는, 그 글자가 들어있는 모든 단어의 학습/연습/시험 화면에 "
        "'한자 풀이'로 자동으로 표시됩니다. 단어마다 같은 한자를 반복해서 설명할 필요가 없습니다."
    )

    library = load_radical_library()
    correct_pw = str(st.secrets.get("upload_password", "")).strip()

    st.write(f"현재 등록된 글자 수: {len(library)}개")

    st.subheader("1. 214개 한 번에 불러오기")
    with st.expander("강희자전 부수 214개 한 번에 불러오기 (이미 있는 글자는 건드리지 않음)", expanded=True):
        st.caption(
            "나무위키 부수 문서를 참고해 정리한 강희자전 214개 부수 전체를 한 번에 채워 넣습니다. "
            "**아래 비밀번호 칸만 채우면 되고, 한자를 따로 입력하실 필요는 없습니다.**"
        )
        seed_pw = st.text_input("업로드 비밀번호", type="password", key="seed_radical_pw")
        if st.button("기본 세트 추가하기 (비밀번호만 입력)", use_container_width=True, key="load_seed_radical_btn"):
            if not hmac.compare_digest(seed_pw, correct_pw):
                st.error("비밀번호가 올바르지 않습니다.")
            else:
                merged = dict(RADICAL_SEED_DATA)
                merged.update(library)  # 기존에 사용자가 수정한 내용을 우선시함
                if save_radical_library(merged):
                    clear_github_cache()
                    st.toast("기본 세트를 추가했습니다.")
                    st.rerun()
                else:
                    st.error("저장에 실패했습니다.")

    st.write("---")
    st.subheader("2. 글자 하나씩 직접 추가 / 수정 (선택사항)")
    st.caption("위 1번과 별개 기능입니다. 214개 세트에 없는 한자를 직접 추가하고 싶을 때만 사용하세요.")
    with st.form("radical_add_form"):
        char_input = st.text_input("한자 (한 글자)", max_chars=1)
        reading_input = st.text_input("훈음 (예: 물 수)")
        desc_input = st.text_area("설명", height=80)
        pw_input = st.text_input("업로드 비밀번호", type="password")
        submitted = st.form_submit_button("저장", use_container_width=True)

    if submitted:
        if not hmac.compare_digest(pw_input, correct_pw):
            st.error("비밀번호가 올바르지 않습니다.")
        elif not char_input.strip():
            st.warning("한자를 입력해주세요.")
        else:
            library[char_input.strip()] = {"reading": reading_input.strip(), "desc": desc_input.strip()}
            if save_radical_library(library):
                clear_github_cache()
                st.toast(f"'{char_input.strip()}' 저장했습니다.")
                st.rerun()
            else:
                st.error("저장에 실패했습니다.")

    st.write("---")
    st.subheader(f"등록된 글자 목록 ({len(library)}개)")
    if not library:
        st.info("아직 등록된 글자가 없습니다.")
        return

    del_pw = st.text_input("삭제할 때 사용할 비밀번호", type="password", key="radical_delete_pw")
    for ch in sorted(library.keys()):
        info = library[ch]
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{ch}** ({info.get('reading', '')}) — {info.get('desc', '')}")
            with c2:
                if st.button("삭제", key=f"radical_del_{ch}", use_container_width=True):
                    if not hmac.compare_digest(del_pw, correct_pw):
                        st.error("비밀번호가 올바르지 않습니다.")
                    else:
                        library.pop(ch, None)
                        if save_radical_library(library):
                            clear_github_cache()
                            st.toast(f"'{ch}' 삭제했습니다.")
                            st.rerun()
                        else:
                            st.error("삭제에 실패했습니다.")


def render_user_id_gate() -> None:
    """
    사용자 고유 번호를 입력받는다. 번호를 입력하면 이후 학습/연습/시험/지문 진행 상황이
    자동으로 GitHub에 저장되어, 다음날 같은 번호로 접속했을 때 이어서 할 수 있다.
    번호를 입력하지 않아도 앱은 그대로 동작하며, 그 경우 진행 상황만 저장되지 않는다.
    """
    query_uid = st.query_params.get("uid", "")
    if not st.session_state.user_id and query_uid:
        st.session_state.user_id = sanitize_user_id(query_uid)

    with st.expander("내 번호 (진행 상황 저장)", expanded=not st.session_state.user_id):
        st.caption("번호를 입력하면 학습/연습/시험/지문 진행 상황이 자동 저장되어, 다음에 이어서 할 수 있습니다. 번호 없이 진행시, 저장없이 진행 가능")
        input_id = st.text_input("내 번호 (숫자 등 자유롭게, 010721,0107211 등 겹치지 않는 숫자나 생년월일 추천)", value=st.session_state.user_id, key="user_id_input")
        clean_id = sanitize_user_id(input_id)
        if clean_id != st.session_state.user_id:
            st.session_state.user_id = clean_id
            if clean_id:
                st.query_params["uid"] = clean_id
            st.rerun()
        if st.session_state.user_id:
            st.success(f"현재 번호: {st.session_state.user_id} (이 번호로 진행 상황이 저장됩니다)")


# ---------------------------
# 4. 단어 파싱 / 지문 파싱 유틸
# ---------------------------
def parse_word_text(text: str) -> list:
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
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
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if word and meaning:
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) >= 2:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if word and meaning:
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    seen, result = set(), []
    for w in parsed_words:
        key = (w["word"], w["meaning"], w["hint"])
        if key not in seen:
            seen.add(key)
            result.append(w)
    return result


def parse_script_text(text: str) -> list:
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    return [line.strip() for line in lines if line.strip()]


def parse_words_with_validation(text: str) -> tuple:
    normalized = text.replace("\r\n", "\n").replace("：", ":")
    lines = normalized.split("\n")
    parsed_words, errors = [], []
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
            word, meaning = parts[0].strip(), parts[1].strip()
            hint = "\n".join(block[1:]) if len(block) > 1 else ""
            if not word:
                errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
            elif not meaning:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없습니다.")
            else:
                parsed_words.append({"word": word, "meaning": meaning, "hint": hint})
        else:
            if len(block) == 1:
                errors.append(f"{block_start + 1}번 줄: 뜻이 없는 단어입니다.")
            else:
                word, meaning = block[0], block[1]
                hint = "\n".join(block[2:])
                if not word:
                    errors.append(f"{block_start + 1}번 줄: 단어가 없습니다.")
                elif not meaning:
                    errors.append(f"{block_start + 2}번 줄: 뜻이 없습니다.")
                else:
                    parsed_words.append({"word": word, "meaning": meaning, "hint": hint})

    return parsed_words, errors


def make_safe_filename(name: str) -> str:
    invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    safe_name = str(name).strip()
    for ch in invalid_chars:
        safe_name = safe_name.replace(ch, "_")
    if not safe_name:
        safe_name = "untitled"
    if not safe_name.lower().endswith(".txt"):
        safe_name += ".txt"
    return safe_name


def get_default_title_prefix() -> str:
    korea_now = datetime.now(KOREA_TZ)
    return korea_now.strftime("%Y-%m-%d_")


def build_word_pool(selected_files: list) -> list:
    seen = set()
    pool = []
    for f in selected_files:
        text = get_file_content(f["path"])
        for w in parse_word_text(text):
            key = (w["word"], w["meaning"], w["hint"])
            if key not in seen:
                seen.add(key)
                pool.append(w)
    return pool


def get_session_rng() -> random.Random:
    """사용자(세션)별로 독립된 난수 생성기를 반환한다."""
    if "session_rng" not in st.session_state:
        st.session_state.session_rng = random.Random()
    return st.session_state.session_rng


def get_display_side(mode: str) -> int:
    rng = get_session_rng()
    if mode == "random":
        return rng.choice([0, 1])
    return 0 if mode == "meaning_only" else 1


def requeue_position(queue_len: int, level: int) -> int:
    if queue_len <= 1:
        return 0
    ranges = {60: (0.5, 0.8), 40: (0.2, 0.4), 0: (0.05, 0.15)}
    lo, hi = ranges[level]
    lo_idx = max(0, int(queue_len * lo))
    hi_idx = max(lo_idx, int(queue_len * hi))
    return get_session_rng().randint(lo_idx, hi_idx)


def render_active_files_banner() -> None:
    labels = st.session_state.get("current_files_label", [])
    if not labels:
        return
    items = "".join([f"- {lbl}<br>" for lbl in labels])
    st.markdown(
        f"<div class='active-files-box'><b>현재 학습 파일 ({len(labels)}개)</b><br>{items}</div>",
        unsafe_allow_html=True
    )


# ---------------------------
# 5. UI - 사이드바 (카테고리 기반 파일 선택, 설정 화면에서만 표시)
# ---------------------------
def render_sidebar() -> list:
    with st.sidebar:
        with st.expander("화면 설정(글자가 안보일 경우, 다크모드 Or 기본 모드 선택)", expanded=False):
            new_theme = st.selectbox(
                "테마 선택", ["기본 모드", "다크 모드"],
                index=1 if st.session_state.theme_mode == "다크 모드" else 0,
                key="global_theme_select"
            )
            if new_theme != st.session_state.theme_mode:
                st.session_state.theme_mode = new_theme
                st.rerun()

            col1, col2, col3 = st.columns(3)
            if col1.button("크게", use_container_width=True):
                change_font_scale(0.1); st.rerun()
            if col2.button("작게", use_container_width=True):
                change_font_scale(-0.1); st.rerun()
            if col3.button("초기화", use_container_width=True):
                st.session_state.font_scale = 1.0; st.rerun()

        render_user_id_gate()

        st.write("---")
        st.subheader("학습 자료 선택")

        categories, cat_error = get_dynamic_categories()
        if cat_error:
            st.error(cat_error)
            return []
        if not categories:
            st.error("word_list 폴더를 찾을 수 없습니다.")
            return []

        if st.session_state.sidebar_main_cat not in categories:
            st.session_state.sidebar_main_cat = categories[0]

        main_cat = st.selectbox("1. 대분류 선택", categories, key="sidebar_main_cat")
        sub_folders = get_subfolders(main_cat)

        if sub_folders:
            st.session_state.sidebar_sub_cats = [
                s for s in st.session_state.sidebar_sub_cats if s in sub_folders
            ] or sub_folders
            selected_subs = st.multiselect("2. 세부 카테고리 선택 (예: N2, N3)", sub_folders, key="sidebar_sub_cats")
        else:
            selected_subs = []

        groups = {}
        if sub_folders:
            for sub in selected_subs:
                path = f"word_list/{main_cat}/{sub}"
                files = [{"path": f"{path}/{f}", "label": f"[{sub}] {f}"} for f in get_txt_files(path)]
                groups[sub] = files
        else:
            path = f"word_list/{main_cat}"
            files = [{"path": f"{path}/{f}", "label": f} for f in get_txt_files(path)]
            groups[main_cat] = files

        all_files = [f for files in groups.values() for f in files]
        if not all_files:
            st.warning("선택한 카테고리에 파일이 없습니다.")
            return []

        st.write("**3. 파일 선택**")

        all_widget_keys = [f"filechk_{f['label']}_widget" for f in all_files]
        for wk in all_widget_keys:
            if wk not in st.session_state:
                st.session_state[wk] = False

        overall_col1, overall_col2 = st.columns(2)
        with overall_col1:
            if st.button("전체 선택", use_container_width=True, key="select_all_files_btn"):
                for wk in all_widget_keys:
                    st.session_state[wk] = True
                st.rerun()
        with overall_col2:
            if st.button("전체 해제", use_container_width=True, key="deselect_all_files_btn"):
                for wk in all_widget_keys:
                    st.session_state[wk] = False
                st.rerun()

        for group_name, files in groups.items():
            if not files:
                continue
            st.markdown(f"<div class='cat-group-title'>{group_name}</div>", unsafe_allow_html=True)

            group_widget_keys = [f"filechk_{f['label']}_widget" for f in files]
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                if st.button(f"{group_name} 전체 선택", use_container_width=True, key=f"grp_sel_{group_name}"):
                    for wk in group_widget_keys:
                        st.session_state[wk] = True
                    st.rerun()
            with g_col2:
                if st.button(f"{group_name} 전체 해제", use_container_width=True, key=f"grp_desel_{group_name}"):
                    for wk in group_widget_keys:
                        st.session_state[wk] = False
                    st.rerun()

            st.markdown('<div class="file-check-row">', unsafe_allow_html=True)
            for f in files:
                wk = f"filechk_{f['label']}_widget"
                st.checkbox(f["label"], key=wk)
            st.markdown('</div>', unsafe_allow_html=True)

        selected_labels = [
            f["label"] for f in all_files
            if st.session_state.get(f"filechk_{f['label']}_widget", False)
        ]

        # [신규] 몇 개 파일을 골랐는지 즉시 보여줘서, 스크롤을 다시 올리지 않아도 알 수 있게 함
        if selected_labels:
            st.success(f"{len(selected_labels)}개 파일 선택됨")
        else:
            st.caption("선택된 파일이 없습니다.")

        return [f for f in all_files if f["label"] in selected_labels]


def load_data(selected_files: list, is_script: bool = False) -> bool:
    if not selected_files:
        st.warning("사이드바에서 파일을 선택해주세요.")
        return False

    st.session_state.current_files_label = [f["label"] for f in selected_files]

    if is_script:
        merged = []
        for f in selected_files:
            text = get_file_content(f["path"])
            merged.extend(parse_script_text(text))
        st.session_state.script_lines = merged
    else:
        pool = build_word_pool(selected_files)
        get_session_rng().shuffle(pool)
        st.session_state.words = pool

    return True


# ---------------------------
# 6. 학습 파트
# ---------------------------
def render_study_setup() -> None:
    st.header("학습 파트")
    st.caption("단축키 : (대문자는 capslock시 편함) 스페이스바 = 다음 단어, H = 힌트 보기")
    selected_files = render_sidebar()

    if st.session_state.user_id:
        saved = load_user_progress(st.session_state.user_id, "study")
        if saved and saved.get("words"):
            st.info(
                f"저장된 진행이 있습니다: {saved.get('study_index', 0) + 1} / {len(saved['words'])}번째 단어"
                f" (파일: {', '.join(saved.get('files_label', [])) or '알 수 없음'})"
            )
            if st.button("이어서 학습하기", use_container_width=True, key="resume_study_btn"):
                st.session_state.words = saved["words"]
                st.session_state.current_files_label = saved.get("files_label", [])
                st.session_state.study_index = saved.get("study_index", 0)
                st.session_state.study_show_hint = False
                st.session_state.is_studying = True
                st.session_state.active_part = "study"
                st.rerun()

    if st.button("학습 시작", use_container_width=True):
        if load_data(selected_files):
            st.session_state.is_studying = True
            st.session_state.active_part = "study"
            st.session_state.study_index = 0
            st.session_state.study_show_hint = False
            if st.session_state.user_id:
                save_user_progress(st.session_state.user_id, "study", {
                    "words": st.session_state.words,
                    "files_label": st.session_state.current_files_label,
                    "study_index": 0,
                })
            st.rerun()


def render_study_active() -> None:
    """진행 중에는 조작 버튼을 화면 맨 위 고정바에 배치하고, 그 아래에 카드를 보여준다."""
    if st.session_state.study_index < len(st.session_state.words):
        word_data = st.session_state.words[st.session_state.study_index]
        has_hint = bool(word_data["hint"].strip())

        is_favorite = word_data["word"] in st.session_state.favorite_words

        with sticky_action_bar("study_sticky_bar"):
            b1, b2, b3 = st.columns([2, 2, 2])
            with b1:
                if st.button("다음 단어", use_container_width=True, key="study_next_btn"):
                    st.session_state.study_index += 1
                    st.session_state.study_show_hint = False
                    if st.session_state.user_id:
                        save_user_progress(st.session_state.user_id, "study", {
                            "words": st.session_state.words,
                            "files_label": st.session_state.current_files_label,
                            "study_index": st.session_state.study_index,
                        })
                    st.rerun()
            with b2:
                if st.button("힌트 보기", use_container_width=True, disabled=not has_hint, key="study_hint_btn"):
                    st.session_state.study_show_hint = True
                    st.rerun()
            with b3:
                # [신규] 즐겨찾기 토글 - 헷갈리는 단어를 표시해두고 나중에 모아 볼 수 있음
                star_label = "즐겨찾기 해제" if is_favorite else "즐겨찾기"
                if st.button(star_label, use_container_width=True, key="study_favorite_btn"):
                    if is_favorite:
                        st.session_state.favorite_words.remove(word_data["word"])
                    else:
                        st.session_state.favorite_words.append(word_data["word"])
                    st.rerun()

        fav_badge = " (즐겨찾기)" if is_favorite else ""
        st.markdown(f"""
            <div class="study-card qa-compact">
                <div class="word-text">{word_data['word']}{fav_badge}</div>
                <div class="meaning-text">{word_data['meaning']}</div>
            </div>
        """, unsafe_allow_html=True)

        if st.session_state.study_show_hint and has_hint:
            st.markdown(
                f"<div class='hint-box'><b>힌트</b><br>{word_data['hint'].replace(chr(10), '<br>')}</div>",
                unsafe_allow_html=True
            )
        render_char_breakdown(word_data["word"])

        progress = (st.session_state.study_index) / max(1, len(st.session_state.words))
        st.progress(min(1.0, progress))
        st.markdown(
            f"<div class='progress-caption'>진행 상황: {st.session_state.study_index + 1} / {len(st.session_state.words)}</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("모든 단어 학습을 완료했습니다.")
        if st.session_state.favorite_words:
            st.info(f"이번 세션에서 즐겨찾기한 단어 {len(st.session_state.favorite_words)}개가 있습니다. (연습/시험에서 다시 만날 수 있어요)")
        if st.session_state.user_id:
            delete_user_progress(st.session_state.user_id, "study")
        if st.button("다시 처음부터", use_container_width=True):
            st.session_state.study_index = 0
            st.session_state.study_show_hint = False
            st.rerun()

    render_exit_button("학습 종료하기")


# ---------------------------
# 7. 연습 파트
# ---------------------------
def render_practice_setup() -> None:
    st.header("연습 파트 (망각 곡선 적용)")
    st.caption("단축키 : (대문자는 capslock시 편함) 스페이스바 = 정답(힌트도 함께 표시), H = 힌트, Z=100 X=60 C=40 V=0")
    selected_files = render_sidebar()

    if st.session_state.user_id:
        saved = load_user_progress(st.session_state.user_id, "practice")
        if saved and (saved.get("queue") or saved.get("current_word")):
            st.info(
                f"저장된 연습 진행이 있습니다: {saved.get('done_count', 0)} / {saved.get('total_count', 0)} 완료"
                f" (파일: {', '.join(saved.get('files_label', [])) or '알 수 없음'})"
            )
            if st.button("이어서 연습하기", use_container_width=True, key="resume_practice_btn"):
                st.session_state.current_files_label = saved.get("files_label", [])
                st.session_state.practice_mode = saved.get("mode", "random")
                st.session_state.practice_queue = saved.get("queue", [])
                st.session_state.current_practice_word = saved.get("current_word")
                st.session_state.practice_display_side = saved.get("display_side", 0)
                st.session_state.practice_total_count = saved.get("total_count", 0)
                st.session_state.practice_done_count = saved.get("done_count", 0)
                st.session_state.practice_show_answer = False
                st.session_state.practice_show_hint = False
                st.session_state.practice_result_saved = False
                st.session_state.is_practicing = True
                st.session_state.active_part = "practice"
                st.rerun()

    with mobile_stack_container("practice_mode_btns"):
        c1, c2, c3 = st.columns(3)
        mode = None
        if c1.button("이름만 연습", use_container_width=True): mode = "word_only"
        if c2.button("뜻만 연습", use_container_width=True): mode = "meaning_only"
        if c3.button("랜덤 연습", use_container_width=True): mode = "random"

    if mode and load_data(selected_files):
        st.session_state.practice_queue = list(st.session_state.words)
        st.session_state.practice_total_count = len(st.session_state.practice_queue)
        st.session_state.practice_done_count = 0
        st.session_state.is_practicing = True
        st.session_state.active_part = "practice"
        st.session_state.practice_mode = mode
        st.session_state.practice_show_answer = False
        st.session_state.practice_show_hint = False
        st.session_state.practice_result_saved = False

        if st.session_state.practice_queue:
            st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
            st.session_state.practice_display_side = get_display_side(mode)

        save_practice_progress()
        st.rerun()


def render_practice_active() -> None:
    if st.session_state.current_practice_word:
        cw = st.session_state.current_practice_word
        has_hint = bool(cw["hint"].strip())
        is_ans_shown = st.session_state.practice_show_answer

        with sticky_action_bar("practice_sticky_bar"):
            if st.button("정답 확인", use_container_width=True, key="practice_check_btn"):
                st.session_state.practice_show_answer = True
                st.session_state.practice_show_hint = has_hint
                st.rerun()
            if st.button("힌트 보기", use_container_width=True, disabled=not has_hint, key="practice_hint_btn"):
                st.session_state.practice_show_hint = True; st.rerun()

            def apply_score(level: int) -> None:
                if level != 100:
                    pos = requeue_position(len(st.session_state.practice_queue), level)
                    st.session_state.practice_queue.insert(pos, cw)
                else:
                    # 완벽함으로 채점된 단어만 큐에서 완전히 빠져나가므로,
                    # 진행률(완료 개수)은 이 경우에만 올려야 실제 진행 상황과 맞는다.
                    st.session_state.practice_done_count += 1

                st.session_state.practice_show_answer = False
                st.session_state.practice_show_hint = False
                if st.session_state.practice_queue:
                    st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                    st.session_state.practice_display_side = get_display_side(st.session_state.practice_mode)
                else:
                    st.session_state.current_practice_word = None

                save_practice_progress()

            s1, s2, s3, s4 = st.columns(4)
            with s1:
                if st.button("완벽함 (100)", disabled=not is_ans_shown, use_container_width=True, key="practice_100"): apply_score(100); st.rerun()
            with s2:
                if st.button("조금 앎 (60)", disabled=not is_ans_shown, use_container_width=True, key="practice_60"): apply_score(60); st.rerun()
            with s3:
                if st.button("헷갈림 (40)", disabled=not is_ans_shown, use_container_width=True, key="practice_40"): apply_score(40); st.rerun()
            with s4:
                if st.button("모름 (0)", disabled=not is_ans_shown, use_container_width=True, key="practice_0"): apply_score(0); st.rerun()

        q_text = cw["word"] if st.session_state.practice_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.practice_display_side == 0 else cw["word"]

        card_html = f"<div class='study-card qa-compact'><div class='test-question'>{q_text}</div>"
        if is_ans_shown:
            card_html += f"<div class='test-answer'>정답: {a_text}</div>"
        if st.session_state.practice_show_hint and has_hint:
            card_html += f"<div class='hint-box'><b>힌트</b><br>{cw['hint'].replace(chr(10), '<br>')}</div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)
        if is_ans_shown:
            render_char_breakdown(cw["word"])

        total = max(1, st.session_state.practice_total_count)
        st.progress(min(1.0, st.session_state.practice_done_count / total))
        st.markdown(
            f"<div class='progress-caption'>완료 {st.session_state.practice_done_count}개, 남은 큐 {len(st.session_state.practice_queue)}개</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("대기열의 모든 연습을 완료했습니다.")
        if st.session_state.user_id:
            if not st.session_state.get("practice_result_saved", False):
                st.session_state.practice_result_saved = True
                append_study_stat(
                    st.session_state.user_id, "practice",
                    st.session_state.practice_total_count, st.session_state.practice_total_count
                )
            delete_user_progress(st.session_state.user_id, "practice")

    render_exit_button("연습 종료하기")


# ---------------------------
# 8. 시험 파트
# ---------------------------
def render_exam_setup() -> None:
    st.header("시험 파트")
    st.caption("단축키 : (대문자는 capslock시 편함) 스페이스바 = 정답 확인(힌트도 함께 표시), Z = 맞음, X = 틀림")
    selected_files = render_sidebar()

    if st.session_state.user_id:
        saved = load_user_progress(st.session_state.user_id, "exam")
        if saved and (saved.get("queue") or saved.get("current_word")):
            st.info(
                f"저장된 시험 진행이 있습니다: {saved.get('current_number', 0)} / {saved.get('total_count', 0)}"
                f" (맞음 {saved.get('correct_count', 0)}, 틀림 {saved.get('wrong_count', 0)})"
            )
            if st.button("이어서 시험보기", use_container_width=True, key="resume_exam_btn"):
                st.session_state.current_files_label = saved.get("files_label", [])
                st.session_state.exam_mode = saved.get("mode", "random")
                st.session_state.exam_queue = saved.get("queue", [])
                st.session_state.current_exam_word = saved.get("current_word")
                st.session_state.exam_display_side = saved.get("display_side", 0)
                st.session_state.exam_total_count = saved.get("total_count", 0)
                st.session_state.exam_current_number = saved.get("current_number", 0)
                st.session_state.exam_correct_count = saved.get("correct_count", 0)
                st.session_state.exam_wrong_count = saved.get("wrong_count", 0)
                st.session_state.exam_show_answer = False
                st.session_state.exam_wrong_words = []
                st.session_state.exam_result_saved = False
                st.session_state.is_examining = True
                st.session_state.active_part = "exam"
                st.rerun()

    total_words = 0
    if selected_files:
        total_words = len(build_word_pool(selected_files))

    if total_words > 0:
        st.write("---")
        st.subheader("출제 개수 설정")

        current_val = min(st.session_state.exam_total_count_input, total_words)
        st.session_state.exam_total_count_input = current_val

        with mobile_stack_container("exam_count_btns"):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1], vertical_alignment="bottom")
            with col1:
                st.number_input(f"총 출제 개수 (최대 {total_words}개)", min_value=1, max_value=total_words, key="exam_total_count_input")
            with col2:
                if st.button("최대", use_container_width=True):
                    st.session_state.exam_total_count_input = total_words; st.rerun()
            with col3:
                if st.button("+5", use_container_width=True):
                    st.session_state.exam_total_count_input = min(total_words, current_val + 5); st.rerun()
            with col4:
                if st.button("-5", use_container_width=True):
                    st.session_state.exam_total_count_input = max(1, current_val - 5); st.rerun()

        st.write("---")

        with mobile_stack_container("exam_mode_btns"):
            m1, m2, m3 = st.columns(3)
            mode = None
            if m1.button("이름만 시험", use_container_width=True): mode = "word_only"
            if m2.button("뜻만 시험", use_container_width=True): mode = "meaning_only"
            if m3.button("랜덤 시험", use_container_width=True): mode = "random"

        if mode and load_data(selected_files):
            st.session_state.is_examining = True
            st.session_state.active_part = "exam"
            st.session_state.exam_mode = mode
            st.session_state.exam_current_number = 0
            st.session_state.exam_correct_count = 0
            st.session_state.exam_wrong_count = 0
            st.session_state.exam_show_answer = False
            st.session_state.exam_wrong_words = []  # [신규] 새 시험 시작 시 오답 목록 초기화
            st.session_state.exam_result_saved = False

            exam_words = list(st.session_state.words)
            actual_count = min(st.session_state.exam_total_count_input, len(exam_words))
            st.session_state.exam_total_count = actual_count
            st.session_state.exam_queue = exam_words[:actual_count]

            if st.session_state.exam_queue:
                st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                st.session_state.exam_current_number += 1
                st.session_state.exam_display_side = get_display_side(mode)

            save_exam_progress()
            st.rerun()


def render_exam_active() -> None:
    if st.session_state.current_exam_word:
        cw = st.session_state.current_exam_word
        has_hint = bool(cw.get("hint", "").strip())
        is_ans_shown = st.session_state.exam_show_answer

        with sticky_action_bar("exam_sticky_bar"):
            if st.button("정답 확인", use_container_width=True, key="exam_check_btn"):
                st.session_state.exam_show_answer = True; st.rerun()

            def next_exam(correct: bool = True) -> None:
                if correct:
                    st.session_state.exam_correct_count += 1
                else:
                    st.session_state.exam_wrong_count += 1
                    # [신규] 틀린 단어를 이번 회차 오답 목록에 쌓아둔다 (시험 종료 시 오답 노트로 커밋)
                    st.session_state.exam_wrong_words.append(cw)

                st.session_state.exam_show_answer = False
                if st.session_state.exam_queue:
                    st.session_state.current_exam_word = st.session_state.exam_queue.pop(0)
                    st.session_state.exam_current_number += 1
                    st.session_state.exam_display_side = get_display_side(st.session_state.exam_mode)
                else:
                    st.session_state.current_exam_word = None

                save_exam_progress()

            c2, c3 = st.columns(2)
            with c2:
                if st.button("맞음", disabled=not is_ans_shown, use_container_width=True, key="exam_correct_btn"): next_exam(True); st.rerun()
            with c3:
                if st.button("틀림", disabled=not is_ans_shown, use_container_width=True, key="exam_wrong_btn"): next_exam(False); st.rerun()

            st.info(f"진행: {st.session_state.exam_current_number}/{st.session_state.exam_total_count}  맞음 {st.session_state.exam_correct_count}  틀림 {st.session_state.exam_wrong_count}")

        q_text = cw["word"] if st.session_state.exam_display_side == 0 else cw["meaning"]
        a_text = cw["meaning"] if st.session_state.exam_display_side == 0 else cw["word"]

        card_html = f"<div class='study-card qa-compact'><div class='test-question'>{q_text}</div>"
        if is_ans_shown:
            card_html += f"<div class='test-answer'>정답: {a_text}</div>"
            if has_hint:
                card_html += f"<div class='hint-box'><b>힌트</b><br>{cw['hint'].replace(chr(10), '<br>')}</div>"
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)
        if is_ans_shown:
            render_char_breakdown(cw["word"])

        total = max(1, st.session_state.exam_total_count)
        st.progress(min(1.0, (st.session_state.exam_current_number - 1) / total))
    else:
        total = max(1, st.session_state.exam_total_count)
        accuracy = round(st.session_state.exam_correct_count / total * 100, 1)

        # [신규] 정답률에 따라 다른 톤으로 결과를 보여줘서 한눈에 체감되도록 함 (UX 개선)
        if accuracy >= 90:
            st.success(f"시험 종료. {st.session_state.exam_correct_count} / {st.session_state.exam_total_count} (정답률 {accuracy}%) — 훌륭합니다.")
        elif accuracy >= 70:
            st.info(f"시험 종료. {st.session_state.exam_correct_count} / {st.session_state.exam_total_count} (정답률 {accuracy}%) — 조금만 더!")
        else:
            st.warning(f"시험 종료. {st.session_state.exam_correct_count} / {st.session_state.exam_total_count} (정답률 {accuracy}%) — 오답 노트로 복습해봐요.")

        # [신규] 이번 시험이 처음 종료되는 시점에만(중복 저장 방지) 오답 노트 + 통계에 반영
        if not st.session_state.get("exam_result_saved", False):
            st.session_state.exam_result_saved = True
            if st.session_state.user_id:
                if st.session_state.exam_wrong_words:
                    add_words_to_wrong_notes(st.session_state.user_id, st.session_state.exam_wrong_words)
                append_study_stat(
                    st.session_state.user_id, "exam",
                    st.session_state.exam_total_count, st.session_state.exam_correct_count
                )
                delete_user_progress(st.session_state.user_id, "exam")

        if st.session_state.exam_wrong_words:
            st.caption(f"이번 시험에서 틀린 단어 {len(st.session_state.exam_wrong_words)}개가 오답 노트에 저장되었습니다.")
            wc1, wc2 = st.columns(2)
            with wc1:
                if st.button("틀린 단어만 다시 풀기", use_container_width=True, key="retry_wrong_exam_btn"):
                    st.session_state.exam_queue = list(st.session_state.exam_wrong_words[1:])
                    st.session_state.current_exam_word = st.session_state.exam_wrong_words[0]
                    st.session_state.exam_total_count = len(st.session_state.exam_wrong_words)
                    st.session_state.exam_current_number = 1
                    st.session_state.exam_correct_count = 0
                    st.session_state.exam_wrong_count = 0
                    st.session_state.exam_wrong_words = []
                    st.session_state.exam_show_answer = False
                    st.session_state.exam_display_side = get_display_side(st.session_state.exam_mode)
                    st.session_state.exam_result_saved = False
                    st.rerun()
            with wc2:
                if st.button("오답 노트 전체 보기", use_container_width=True, key="goto_wrongnote_btn"):
                    exit_focus_mode()
                    st.session_state.current_page_select = "오답 노트"
                    st.rerun()

    render_exit_button("시험 종료하기")


# ---------------------------
# 9. UI - 단어장 추가 파트
# ---------------------------
def render_wordbook_part() -> None:
    st.header("단어장 관리 (GitHub 연동)")
    st.caption("새로운 단어장 파일(.txt)을 GitHub 저장소에 업로드합니다.")

    _, top_right = st.columns([5, 1])
    with top_right:
        if st.button("새로고침", use_container_width=True):
            clear_github_cache()
            st.rerun()

    categories, cat_error = get_dynamic_categories()
    if cat_error:
        st.error(cat_error)
        return
    if not categories:
        st.error("저장할 폴더 트리를 불러오지 못했습니다.")
        return

    c1, c2 = st.columns(2)
    with c1:
        main_cat = st.selectbox("1. 대분류 선택", categories, key="wb_main_cat")
    with c2:
        sub_folders = get_subfolders(main_cat)
        sub_cat = st.selectbox("2. 하위 폴더 선택", sub_folders, key="wb_sub_cat") if sub_folders else None

    target_folder = f"word_list/{main_cat}/{sub_cat}" if sub_cat else f"word_list/{main_cat}"

    st.caption(f"현재 폴더: {target_folder}")
    with st.expander("현재 폴더에 있는 파일 목록 보기"):
        existing = get_txt_files(target_folder)
        if existing:
            for f in existing:
                st.write(f"- {f}")
        else:
            st.info("비어 있습니다.")

    correct_pw = str(st.secrets.get("upload_password", "")).strip()

    st.write("---")
    tab1, tab2 = st.tabs(["직접 입력해서 저장", "txt 파일 업로드"])

    with tab1:
        with st.form("manual_wordbook_form"):
            manual_title = st.text_input("파일 제목", value=get_default_title_prefix(), placeholder="예: 2026-07-20_N2")
            manual_text = st.text_area("단어 : 뜻, 다음 줄에 힌트 (또는 단어 / 뜻 / 힌트를 각 줄에)", height=250)
            manual_pw = st.text_input("업로드 비밀번호", type="password")
            submitted = st.form_submit_button("저장", use_container_width=True)

        if submitted:
            parsed, errors = parse_words_with_validation(manual_text)
            if not hmac.compare_digest(manual_pw, correct_pw):
                st.error("비밀번호가 올바르지 않습니다.")
            elif errors:
                st.error("아래 형식 오류를 수정한 뒤 다시 저장해주세요.")
                for e in errors:
                    st.write(f"- {e}")
            elif not parsed:
                st.warning("저장할 단어가 없습니다.")
            else:
                safe_name = make_safe_filename(manual_title)
                resp, path = upload_text_to_github(target_folder, safe_name, manual_text)
                if resp.status_code in (200, 201):
                    clear_github_cache()
                    st.toast(f"업로드 완료: {path}")
                    st.success(f"업로드 완료: {path} ({len(parsed)}개 단어)")
                    st.rerun()
                else:
                    st.toast("업로드 실패")
                    st.error(f"업로드 실패 (status {resp.status_code}, 경로: {path}): {resp.text[:200]}")

    with tab2:
        uploaded_file = st.file_uploader("txt 파일 선택", type=["txt"])
        if uploaded_file:
            up_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            with st.form("upload_txt_form"):
                up_title = st.text_input("파일명", value=uploaded_file.name)
                up_pw = st.text_input("비밀번호", type="password")
                up_submitted = st.form_submit_button("저장", use_container_width=True)

            if up_submitted:
                parsed, errors = parse_words_with_validation(up_text)
                if not hmac.compare_digest(up_pw, correct_pw):
                    st.error("비밀번호가 올바르지 않습니다.")
                elif errors:
                    st.error("아래 형식 오류가 있어 업로드를 중단했습니다.")
                    for e in errors:
                        st.write(f"- {e}")
                elif not parsed:
                    st.warning("저장할 단어가 없습니다.")
                else:
                    safe_name = make_safe_filename(up_title)
                    resp, path = upload_text_to_github(target_folder, safe_name, up_text)
                    if resp.status_code in (200, 201):
                        clear_github_cache()
                        st.toast(f"업로드 완료: {path}")
                        st.success(f"업로드 완료: {path} ({len(parsed)}개 단어)")
                        st.rerun()
                    else:
                        st.toast("업로드 실패")
                        st.error(f"업로드 실패 (status {resp.status_code}, 경로: {path}): {resp.text[:200]}")


# ---------------------------
# 10. 지문 한 줄 외우기 파트
# ---------------------------
def render_script_setup() -> None:
    st.header("지문 한 줄 외우기")
    st.caption("대화 및 지문을 순서대로 연상하며 외웁니다. 단축키 : (대문자는 capslock시 편함) 스페이스바 = 다음 문장")
    selected_files = render_sidebar()

    if st.session_state.user_id:
        saved = load_user_progress(st.session_state.user_id, "script")
        if saved and saved.get("lines"):
            st.info(
                f"저장된 진행이 있습니다: {saved.get('script_index', 0) + 1} / {len(saved['lines'])}번째 문장"
                f" (파일: {', '.join(saved.get('files_label', [])) or '알 수 없음'})"
            )
            if st.button("이어서 외우기", use_container_width=True, key="resume_script_btn"):
                st.session_state.script_lines = saved["lines"]
                st.session_state.current_files_label = saved.get("files_label", [])
                st.session_state.script_index = saved.get("script_index", 0)
                st.session_state.is_scripting = True
                st.session_state.active_part = "script"
                st.rerun()

    if st.button("대본 학습 시작", use_container_width=True):
        if load_data(selected_files, is_script=True):
            st.session_state.is_scripting = True
            st.session_state.active_part = "script"
            st.session_state.script_index = 0
            if st.session_state.user_id:
                save_user_progress(st.session_state.user_id, "script", {
                    "lines": st.session_state.script_lines,
                    "files_label": st.session_state.current_files_label,
                    "script_index": 0,
                })
            st.rerun()


def render_script_active() -> None:
    if st.session_state.script_index < len(st.session_state.script_lines):
        line_text = st.session_state.script_lines[st.session_state.script_index]

        with sticky_action_bar("script_sticky_bar"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("이전 문장", disabled=(st.session_state.script_index == 0), use_container_width=True, key="script_prev_btn"):
                    st.session_state.script_index -= 1
                    if st.session_state.user_id:
                        save_user_progress(st.session_state.user_id, "script", {
                            "lines": st.session_state.script_lines,
                            "files_label": st.session_state.current_files_label,
                            "script_index": st.session_state.script_index,
                        })
                    st.rerun()
            with c2:
                if st.button("다음 문장", use_container_width=True, key="script_next_btn"):
                    st.session_state.script_index += 1
                    if st.session_state.user_id:
                        save_user_progress(st.session_state.user_id, "script", {
                            "lines": st.session_state.script_lines,
                            "files_label": st.session_state.current_files_label,
                            "script_index": st.session_state.script_index,
                        })
                    st.rerun()

        st.markdown(f"""
            <div class="study-card qa-compact">
                <div class="script-text">{line_text}</div>
            </div>
        """, unsafe_allow_html=True)

        progress = st.session_state.script_index / max(1, len(st.session_state.script_lines))
        st.progress(min(1.0, progress))
        st.markdown(
            f"<div class='progress-caption'>진행 상황: {st.session_state.script_index + 1} / {len(st.session_state.script_lines)}</div>",
            unsafe_allow_html=True
        )
    else:
        st.success("모든 대본/지문 학습을 완료했습니다.")
        if st.session_state.user_id:
            delete_user_progress(st.session_state.user_id, "script")
        if st.button("다시 처음부터", use_container_width=True):
            st.session_state.script_index = 0
            st.rerun()

    render_exit_button("지문 학습 종료하기")


# ---------------------------
# 11. [신규] 오답 노트 파트
# ---------------------------
def render_wrongnote_part() -> None:
    st.header("오답 노트")
    st.caption("시험에서 틀린 단어가 자동으로 여기 쌓입니다. '이제 외웠어요'를 누르면 목록에서 제거됩니다.")

    if not st.session_state.user_id:
        st.info("오답 노트는 '내 번호'를 입력해야 사용할 수 있습니다. 사이드바에서 번호를 먼저 등록해주세요.")
        render_sidebar()
        return

    words = load_wrong_notes(st.session_state.user_id)

    if not words:
        st.success("오답 노트가 비어 있습니다. 시험을 보면 틀린 단어가 자동으로 여기 쌓입니다.")
        return

    st.write(f"**총 {len(words)}개**의 단어가 오답 노트에 있습니다.")

    top1, top2 = st.columns(2)
    with top1:
        if st.button("오답 노트로 연습 시작", use_container_width=True, key="wrongnote_practice_btn"):
            st.session_state.words = list(words)
            st.session_state.current_files_label = ["오답 노트"]
            st.session_state.practice_queue = list(words)
            st.session_state.practice_total_count = len(words)
            st.session_state.practice_done_count = 0
            st.session_state.practice_mode = "random"
            st.session_state.practice_show_answer = False
            st.session_state.practice_show_hint = False
            st.session_state.practice_result_saved = False
            if st.session_state.practice_queue:
                st.session_state.current_practice_word = st.session_state.practice_queue.pop(0)
                st.session_state.practice_display_side = get_display_side("random")
            st.session_state.is_practicing = True
            st.session_state.active_part = "practice"
            st.rerun()
    with top2:
        if st.button("오답 노트 전체 비우기", use_container_width=True, key="wrongnote_clear_btn"):
            save_wrong_notes(st.session_state.user_id, [])
            st.toast("오답 노트를 비웠습니다.")
            st.rerun()

    st.write("---")
    for idx, w in enumerate(words):
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{w.get('word', '')}** — {w.get('meaning', '')}")
                if w.get("hint", "").strip():
                    with st.expander("힌트 보기"):
                        st.write(w["hint"])
            with c2:
                if st.button("암기완료", key=f"wrongnote_done_{idx}", use_container_width=True):
                    remove_word_from_wrong_notes(st.session_state.user_id, w)
                    st.toast("오답 노트에서 제거했습니다.")
                    st.rerun()


# ---------------------------
# 12. [신규] 학습 통계 대시보드 파트
# ---------------------------
def render_stats_part() -> None:
    st.header("학습 통계")
    st.caption("연습·시험을 마칠 때마다 자동으로 기록됩니다.")

    if not st.session_state.user_id:
        st.info("학습 통계는 '내 번호'를 입력해야 사용할 수 있습니다. 사이드바에서 번호를 먼저 등록해주세요.")
        render_sidebar()
        return

    records = load_study_stats(st.session_state.user_id)
    if not records:
        st.info("아직 기록된 학습 데이터가 없습니다. 연습이나 시험을 완료하면 이곳에 통계가 쌓입니다.")
        return

    total_sessions = len(records)
    exam_records = [r for r in records if r.get("part") == "exam"]
    total_correct = sum(r.get("correct", 0) for r in exam_records)
    total_questions = sum(r.get("total", 0) for r in exam_records)
    overall_accuracy = round(total_correct / total_questions * 100, 1) if total_questions else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("총 학습 세션", f"{total_sessions}회")
    m2.metric("누적 시험 문항", f"{total_questions}개")
    m3.metric("전체 시험 정답률", f"{overall_accuracy}%")

    st.write("---")
    st.subheader("일자별 기록 (최근 30건)")

    # 날짜별로 묶어서 최근 순으로 보여준다. (외부 라이브러리 없이 표 형태로 표시)
    daily = {}
    for r in records:
        d = r.get("date", "알 수 없음")
        daily.setdefault(d, {"exam_total": 0, "exam_correct": 0, "practice_count": 0})
        if r.get("part") == "exam":
            daily[d]["exam_total"] += r.get("total", 0)
            daily[d]["exam_correct"] += r.get("correct", 0)
        else:
            daily[d]["practice_count"] += 1

    sorted_dates = sorted(daily.keys(), reverse=True)[:30]
    for d in sorted_dates:
        info = daily[d]
        acc_txt = ""
        if info["exam_total"] > 0:
            acc = round(info["exam_correct"] / info["exam_total"] * 100, 1)
            acc_txt = f" · 시험 정답률 {acc}% ({info['exam_correct']}/{info['exam_total']})"
        practice_txt = f" · 연습 {info['practice_count']}회" if info["practice_count"] else ""
        st.markdown(f"- **{d}**{acc_txt}{practice_txt}")

    # 최근 정답률 추이를 st.line_chart로 간단히 시각화 (UX 개선: 숫자보다 그래프가 한눈에 들어옴)
    if len(exam_records) >= 2:
        st.write("---")
        st.subheader("시험 정답률 추이")
        chart_data = []
        for r in exam_records[-20:]:
            t = r.get("total", 0)
            acc = round(r.get("correct", 0) / t * 100, 1) if t else 0
            chart_data.append(acc)
        st.line_chart(chart_data)


# ---------------------------
# 13. 메인 실행
# ---------------------------
def render_full_header() -> None:
    st.markdown("""
        <div style="text-align:center; margin-bottom: 4px;">
            <span style="font-size: 1.6rem; font-weight: 800;">단어 암기 프로그램</span>
        </div>
        <div style="text-align:center; color:#8a8a92; font-size:0.85rem; margin-bottom:12px;">
            매일 조금씩, 확실하게 외우기(왼쪽 위의 버튼을 눌러 공부 과목을 선택하세요.)
        </div>
    """, unsafe_allow_html=True)


def main() -> None:
    init_session_state()
    apply_global_style()

    if is_focus_active():
        active_part = st.session_state.active_part
        if active_part == "study":
            render_study_active()
        elif active_part == "practice":
            render_practice_active()
        elif active_part == "exam":
            render_exam_active()
        elif active_part == "script":
            render_script_active()
        else:
            exit_focus_mode()
            st.rerun()
    else:
        render_full_header()

        page = st.radio(
            "파트 이동",
            ["학습", "연습", "시험", "오답 노트", "학습 통계", "단어장 추가", "지문 외우기", "한자 풀이 사전"],
            horizontal=True,
            label_visibility="collapsed",
            key="current_page_select"
        )

        if page == "학습":
            render_study_setup()
        elif page == "연습":
            render_practice_setup()
        elif page == "시험":
            render_exam_setup()
        elif page == "오답 노트":
            render_wrongnote_part()
        elif page == "학습 통계":
            render_stats_part()
        elif page == "단어장 추가":
            render_wordbook_part()
        elif page == "지문 외우기":
            render_script_setup()
        elif page == "한자 풀이 사전":
            render_radical_library_part()

    inject_keyboard_shortcuts()
    inject_session_keepalive()
    inject_floating_memo_window()


if __name__ == "__main__":
    main()