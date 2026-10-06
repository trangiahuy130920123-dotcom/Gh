import os
import re
import html
import json
import streamlit as st

# Cần file requirements.txt (cùng thư mục) chứa: streamlit và openai>=1.60
try:
    from openai import OpenAI
except ImportError:
    st.error(
        "Thiếu thư viện `openai`. Hãy thêm file `requirements.txt` "
        "(gồm 2 dòng: `streamlit` và `openai>=1.60`) vào GitHub rồi Reboot app."
    )
    st.stop()

# ============================================================
# NOVA AI — REAL AI + PRESENTATION
# One-file Streamlit app
#
# Cài:
#   pip install streamlit openai
#
# Chạy:
#   streamlit run nova_ai.py
#
# API key:
#   Cách 1: nhập ở thanh bên
#   Cách 2: đặt biến môi trường OPENAI_API_KEY
# ============================================================

st.set_page_config(
    page_title="Nova AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>
/* Không ẩn <header>: nó chứa nút mở thanh bên (nhập API key). */
#MainMenu, footer {visibility:hidden;}
header[data-testid="stHeader"] {background:transparent;}

.stApp {
    background:#f7f7f8;
}

.block-container {
    max-width:1100px;
    padding:28px 24px 110px;
}

.topbar {
    display:flex;
    align-items:center;
    margin-bottom:38px;
}

.brand {
    display:flex;
    align-items:center;
    gap:12px;
}

.logo {
    width:42px;
    height:42px;
    border-radius:13px;
    display:flex;
    align-items:center;
    justify-content:center;
    background:#111;
    color:white;
    font-size:21px;
    font-weight:700;
}

.brand-name {
    font-size:20px;
    font-weight:700;
    color:#111;
}

.badge {
    font-size:12px;
    padding:5px 9px;
    border-radius:999px;
    background:#ececf0;
    color:#666;
}

.hero {
    text-align:center;
    margin:70px auto 35px;
}

.hero h1 {
    font-size:46px;
    line-height:1.05;
    letter-spacing:-1.8px;
    color:#111;
    margin-bottom:13px;
}

.hero p {
    color:#777;
    font-size:17px;
}

.feature {
    border:1px solid #e5e5e8;
    border-radius:18px;
    padding:18px;
    background:white;
    min-height:120px;
}

.card-title {
    font-weight:700;
    color:#222;
    font-size:15px;
    margin-bottom:8px;
}

.card-desc {
    color:#777;
    font-size:13px;
    line-height:1.5;
}

/* Tin nhắn chat (st.chat_message) */
[data-testid="stChatMessage"] {
    background:white;
    border:1px solid #e5e5e8;
    border-radius:18px;
    padding:14px 18px;
    max-width:780px;
    margin:10px auto;
    overflow-wrap:anywhere;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    color:#222;
}

.slide-card {
    background:white;
    border:1px solid #e2e2e6;
    border-radius:20px;
    padding:28px;
    margin:16px auto;
    max-width:800px;
    box-shadow:0 8px 28px rgba(0,0,0,.04);
}

.slide-number {
    color:#888;
    font-size:12px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:1px;
    margin-bottom:8px;
}

.slide-title {
    color:#111;
    font-size:25px;
    font-weight:750;
    margin-bottom:12px;
}

.slide-body {
    color:#444;
    font-size:15px;
    line-height:1.65;
}

@media (max-width:700px) {
    .block-container {
        padding:18px 14px 100px;
    }

    .hero {
        margin-top:45px;
    }

    .hero h1 {
        font-size:34px;
    }

    .hero p {
        font-size:15px;
    }

    .slide-card {
        padding:20px;
    }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "started" not in st.session_state:
    st.session_state.started = False

if "presentation" not in st.session_state:
    st.session_state.presentation = None

# ============================================================
# OPENAI
# ============================================================

with st.sidebar:
    st.markdown("## ✦ Nova AI")
    st.caption("Kết nối AI thật bằng OpenAI API")

    # Thứ tự ưu tiên: biến môi trường -> st.secrets (Streamlit Cloud) -> nhập tay
    env_key = os.getenv("OPENAI_API_KEY", "")
    if not env_key:
        try:
            env_key = st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            env_key = ""

    api_key = st.text_input(
        "OpenAI API Key",
        value=env_key,
        type="password",
        placeholder="sk-...",
        help="Key chỉ được dùng trong phiên Streamlit hiện tại.",
    )

    model = st.selectbox(
        "Model",
        [
            "gpt-6-luna",
            "gpt-6-sol",
        ],
        index=0,
    )

    custom_model = st.text_input(
        "Hoặc nhập tên model khác",
        placeholder="vd: gpt-5",
        help="Nếu điền, sẽ dùng model này thay cho danh sách trên.",
    )
    if custom_model.strip():
        model = custom_model.strip()

    st.divider()
    st.caption("Ví dụ:")
    st.caption("• Logistics là gì?")
    st.caption("• Giải thích AI cho học sinh lớp 10")
    st.caption("• Tạo bài thuyết trình 8 slide về Logistics")

def get_client():
    if not api_key or not api_key.strip():
        return None
    return OpenAI(api_key=api_key.strip())

def is_presentation_request(text):
    """
    Chỉ bật chế độ presentation khi người dùng thực sự yêu cầu.
    Các câu hỏi thông thường sẽ đi vào chat bình thường.
    """
    t = text.lower().strip()

    explicit_phrases = [
        "tạo bài thuyết trình",
        "tạo bài trình bày",
        "làm bài thuyết trình",
        "làm bài trình bày",
        "tạo slide",
        "tạo slides",
        "làm slide",
        "làm slides",
        "tạo powerpoint",
        "tạo powerpoint",
        "làm powerpoint",
        "presentation",
        "presentation về",
        "slides về",
        "slide về",
        "bài thuyết trình",
    ]

    return any(p in t for p in explicit_phrases)

def ask_ai(user_prompt):
    client = get_client()

    if client is None:
        return (
            "⚠️ Chưa có OpenAI API Key.\n\n"
            "Mở thanh bên trái → nhập API Key → gửi lại câu hỏi."
        )

    history = []
    for role, content in st.session_state.messages[-12:]:
        if role == "user":
            history.append({"role": "user", "content": content})
        elif role == "assistant":
            history.append({"role": "assistant", "content": content})

    # Tránh gửi lại câu user hiện tại 2 lần.
    if history and history[-1]["role"] == "user" and history[-1]["content"] == user_prompt:
        history = history[:-1]

    system = """
Bạn là Nova AI, một trợ lý AI thân thiện, thông minh và hữu ích.

Quy tắc quan trọng:
1. Nếu người dùng chỉ hỏi một câu hỏi bình thường, hãy TRẢ LỜI CÂU HỎI.
2. Không tự biến câu trả lời thành bài thuyết trình.
3. Chỉ khi người dùng rõ ràng yêu cầu tạo bài thuyết trình/slide/PowerPoint,
   ứng dụng mới chuyển sang chế độ presentation.
4. Trả lời bằng tiếng Việt nếu người dùng dùng tiếng Việt.
5. Không nói rằng bạn là Gamma. Bạn chỉ cung cấp tính năng tạo nội dung
   trình bày theo phong cách hiện đại, tương tự một công cụ presentation AI.
6. Nếu câu hỏi không cần dài, trả lời ngắn gọn và dễ hiểu.
"""

    messages = [{"role": "developer", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    try:
        response = client.responses.create(
            model=model,
            input=messages,
        )
        return response.output_text.strip()
    except Exception as e:
        return (
            "❌ Không gọi được AI.\n\n"
            f"Chi tiết lỗi: `{type(e).__name__}: {e}`"
        )

def create_presentation(user_prompt):
    client = get_client()

    if client is None:
        return None, (
            "⚠️ Chưa có OpenAI API Key.\n\n"
            "Mở thanh bên trái → nhập API Key → gửi lại yêu cầu."
        )

    presentation_instruction = f"""
Người dùng yêu cầu tạo một bài thuyết trình.

Yêu cầu gốc:
{user_prompt}

Hãy tạo nội dung bài thuyết trình hiện đại, rõ ràng, dễ trình bày.
Nếu người dùng không ghi số slide thì tự chọn khoảng 7-10 slide.

Chỉ trả về JSON hợp lệ, không markdown, theo đúng cấu trúc:
{{
  "title": "Tên bài",
  "subtitle": "Mô tả ngắn",
  "slides": [
    {{
      "title": "Tiêu đề slide",
      "bullets": ["Ý 1", "Ý 2", "Ý 3"]
    }}
  ]
}}

Không thêm text ngoài JSON.
"""

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Bạn là công cụ tạo presentation AI. "
                        "JSON phải hợp lệ và nội dung phải bằng tiếng Việt."
                    ),
                },
                {"role": "user", "content": presentation_instruction},
            ],
        )

        raw = response.output_text.strip()

        # Loại bỏ markdown fence nếu model vô tình thêm vào.
        raw = re.sub(r"^```json\s*", "", raw, flags=re.I)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
            raise ValueError("AI trả về cấu trúc slide không hợp lệ.")

        return data, None

    except Exception as e:
        return None, (
            "❌ Không tạo được bài thuyết trình.\n\n"
            f"Chi tiết lỗi: `{type(e).__name__}: {e}`"
        )

def render_ai_message(message):
    # Markdown renderer của Streamlit đẹp hơn HTML thủ công và an toàn hơn.
    st.markdown(message)

# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="topbar">
    <div class="brand">
        <div class="logo">✦</div>
        <div class="brand-name">Nova AI</div>
        <div class="badge">AI + Presentation</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# HOME
# ============================================================

if not st.session_state.started:
    st.markdown("""
    <div class="hero">
        <h1>What can I help you create?</h1>
        <p>
            Hỏi AI bất cứ điều gì — hoặc yêu cầu tạo bài trình bày khi bạn cần.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# CHAT HISTORY
# ============================================================

for role, message in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(message)  # không bật unsafe_allow_html nên an toàn

# ============================================================
# PRESENTATION RESULT
# ============================================================

if st.session_state.presentation:
    data = st.session_state.presentation

    st.markdown(
        f"""
        <div class="slide-card">
            <div class="slide-number">Presentation</div>
            <div class="slide-title">{html.escape(str(data.get("title", "Bài thuyết trình")))}</div>
            <div class="slide-body">{html.escape(str(data.get("subtitle", "")))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, slide in enumerate(data.get("slides", []), start=1):
        title = html.escape(str(slide.get("title", f"Slide {i}")))
        bullets = slide.get("bullets", [])

        bullet_html = "".join(
            f"<li>{html.escape(str(item))}</li>"
            for item in bullets
        )

        st.markdown(
            f"""
            <div class="slide-card">
                <div class="slide-number">Slide {i}</div>
                <div class="slide-title">{title}</div>
                <div class="slide-body">
                    <ul>{bullet_html}</ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# INPUT
# ============================================================

prompt = st.chat_input(
    "Hỏi một câu hỏi hoặc yêu cầu tạo bài trình bày..."
)

if prompt:
    st.session_state.started = True
    st.session_state.messages.append(("user", prompt))

    with st.chat_message("user"):
        st.markdown(prompt)

    # Chỉ kích hoạt presentation khi người dùng yêu cầu rõ ràng.
    if is_presentation_request(prompt):
        with st.spinner("✦ Nova AI đang tạo bài thuyết trình..."):
            presentation, error = create_presentation(prompt)

        if error:
            st.session_state.messages.append(("assistant", error))
        else:
            st.session_state.presentation = presentation
            st.session_state.messages.append(
                (
                    "assistant",
                    "Đã tạo xong bài thuyết trình. Mình hiển thị các slide bên dưới."
                )
            )
    else:
        with st.spinner("✦ Nova AI đang suy nghĩ..."):
            answer = ask_ai(prompt)

        st.session_state.messages.append(("assistant", answer))

    st.rerun()

# ============================================================
# FEATURES
# ============================================================

if not st.session_state.messages:
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature">
            <div class="card-title">💬 Hỏi đáp</div>
            <div class="card-desc">
                Hỏi câu hỏi bình thường và nhận câu trả lời từ AI thật.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature">
            <div class="card-title">📊 Tạo trình bày</div>
            <div class="card-desc">
                Chỉ tạo slide khi bạn thực sự yêu cầu bài thuyết trình.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature">
            <div class="card-title">✨ Một AI duy nhất</div>
            <div class="card-desc">
                Một giao diện cho hỏi đáp và tạo nội dung trình bày.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# RESET
# ============================================================

if st.session_state.messages:
    if st.button("🗑️ Xóa cuộc trò chuyện"):
        st.session_state.messages = []
        st.session_state.started = False
        st.session_state.presentation = None
        st.rerun()
