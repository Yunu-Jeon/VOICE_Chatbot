import streamlit as st
import streamlit.components.v1 as components
from audio_recorder_streamlit import audio_recorder
from openai import OpenAI
import base64
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
client = OpenAI()

# 1. 페이지 설정 및 깔끔한 CSS
st.set_page_config(page_title="미룬이인 당신, 구출해드립니다🔥", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 6rem; }
    
    .step-badge {
        display: inline-block; padding: 5px 12px; background-color: #f1f5f9; color: #64748b; 
        border-radius: 12px; font-size: 0.9rem; font-weight: bold; margin-right: 8px;
    }
    .step-badge.active { background-color: #4f46e5; color: white; }
    
    .mic-top-label {
        text-align: center;
        font-size: 1.2rem;
        font-weight: 900;
        color: #4f46e5;
        margin-top: 15px;
        margin-bottom: 10px;
        letter-spacing: -0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 1분 이상 반응이 없으면 알림을 보냄.
idle_timer_js = """
<script>
    setTimeout(function() {
        alert("딴짓 하지 말고 하던 일 빨리 끝내볼까요? 👀");
    }, 60000); 
</script>
"""
components.html(idle_timer_js, height=0, width=0)

# 3. 처음 메시지 상태
if "step" not in st.session_state:
    st.session_state.step = 0  
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 해야 하는 일이 있는데 하기 싫으시죠? 당신이 할 일을 5단계로 쪼개서 차근차근 할 수 있게 정리해드릴게요😊"}
    ]
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "latest_audio_html" not in st.session_state:
    st.session_state.latest_audio_html = ""
if "awaiting_bot" not in st.session_state:
    st.session_state.awaiting_bot = False

# 4. 함수 구현
# 4-1. STT
def perform_stt(audio_bytes):
    with open("temp_input.wav", "wb") as f:
        f.write(audio_bytes)
    with open("temp_input.wav", "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
    return transcription.text

# 4-2. TTS
def generate_tts_html(text):
    with client.audio.speech.with_streaming_response.create(
        model='gpt-4o-mini-tts', # 에러 발생 시 'tts-1'로 변경하세요!
        voice='nova',
        input=text
    ) as response:
        response.stream_to_file("response.mp3")
        
    with open("response.mp3", "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"""<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>"""

# 4-3. 다섯 단계로 쪼개기
def generate_5_steps(user_task):
    prompt = f"""
    사용자가 미루고 있는 일: "{user_task}"
    이 일을 시작하고 끝내기 위한 현실적이고 구체적인 5단계 행동 지침을 작성하세요.
    - '숨쉬기', '컴퓨터 켜기' 같은 너무 사소한 행동이나, 반대로 '책 한 권 다 읽기' 같은 한 번에 실행하기 어려운 일은 제외하세요.
    - 당장 실천할 수 있으면서도 확실한 진척이 느껴지는 적절한 난이도로 구성하세요.
    - 반드시 1. 2. 3. 4. 5. 번호만 달아서 딱 5줄로 출력하세요. 부연 설명 절대 금지.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "user", "content": prompt}], 
        temperature=0.6,
        max_tokens=150
    )
    raw_text = response.choices[0].message.content
    return [line for line in raw_text.split('\n') if line.strip()][:5]

# cf) 오디오 자동 재생
if st.session_state.latest_audio_html:
    st.markdown(st.session_state.latest_audio_html, unsafe_allow_html=True)
    st.session_state.latest_audio_html = "" 

# 5. 화면 상단
col_title, col_mic_area = st.columns([4, 1.5])

with col_title:
    st.title("🚀 미룬이 구출 로드맵")
    st.progress(st.session_state.step / 5.0)
    st.write("")

with col_mic_area:
    st.markdown("<div class='mic-top-label'>🎙️ 음성으로 말하기</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns([1, 1, 1])
    with m2:
        audio_bytes = audio_recorder(text="", recording_color="#ef4444", neutral_color="#4f46e5", icon_size="3x")

# 6. 메인 레이아웃
current = st.session_state.step
col_list, col_chat = st.columns([1.2, 1], gap="large")

# [좌측]
with col_list:
    st.markdown("### 📢 프로젝트 소개")
    st.info("마감이 얼마 남지 않았는데, 양은 많고, 시작하기 어려운 일이 있으신가요? 제가 다섯 단계로 쪼개서 어떻게든 일을 끝낼 수 있게 도와드리겠습니다👊🏻")
    
    st.write("") 
    
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f"✅ 진행률: {current * 20}%")
    with c2:
        # 수동 초기화 버튼 추가
        if st.button("🔄 로드맵 초기화"):
            st.session_state.tasks = []
            st.session_state.step = 0
            st.session_state.messages = [{"role": "assistant", "content": "로드맵을 싹 비웠어요. 어떤 일을 새로 시작해 볼까요?"}]
            st.rerun()

    with st.container(border=True):
        if not st.session_state.tasks:
            st.info("오른쪽 채팅창에 미루고 있는 일을 입력해주세요. (예: 발표 자료 만들기)")
        else:
            for i, task in enumerate(st.session_state.tasks):
                if i < current:
                    st.markdown(f"~~<span class='step-badge'>Step {i+1}</span> {task}~~", unsafe_allow_html=True)
                elif i == current:
                    st.markdown(f"<span class='step-badge active'>Step {i+1}</span> **{task}** 🔥", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='step-badge'>Step {i+1}</span> <span style='color:#cbd5e1;'>{task}</span>", unsafe_allow_html=True)

# [우측]
with col_chat:
    st.markdown("💬 미룬이 전담 코치")
    
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for message in st.session_state.messages:
            avatar_icon = "🧸" if message["role"] == "assistant" else "👤"
            with st.chat_message(message["role"], avatar=avatar_icon):
                st.write(message["content"])
        
        if st.session_state.awaiting_bot:
            user_text = st.session_state.messages[-1]["content"]
            with st.chat_message("assistant", avatar="🧸"):
                with st.spinner("생각 중... 🤔"):
                    if not st.session_state.tasks:
                        st.session_state.tasks = generate_5_steps(user_text)
                        st.session_state.step = 0
                        bot_response = "좋아! 진도가 확 나갈 수 있게 5단계로 짜봤어요. 왼쪽 로드맵 보이시나요? 일단 1단계부터 부숴보아요👊🏻 다 하면 '다 했어'라고 말해주세요!"
                    else:
                        # 정정 키워드를 감시하고 그에 따라서 고쳐주는 코드
                        if any(word in user_text for word in ["아니", "잘못", "다시", "수정", "바꿀", "정정", "취소", "틀렸"]):
                            st.session_state.tasks = generate_5_steps(user_text)
                            st.session_state.step = 0
                            bot_response = "앗, 제가 잘못 알아들었네요! 죄송해요 😅 말해준 내용으로 로드맵을 다시 제대로 짜봤어요. 이번엔 어떠신가요? 1단계부터 바로 해볼까요?"
                        
                        elif any(word in user_text for word in ["완료", "다 했", "했어", "끝"]):
                            st.session_state.step += 1
                            if st.session_state.step < 5:
                                next_task = st.session_state.tasks[st.session_state.step]
                                bot_response = f"역시 해낼 줄 알았어요! 👏 쉬지 말고 바로 다음 단계인 **{next_task}** 로 나아가볼까요?"
                            else:
                                bot_response = "우와아!! 5단계를 다 끝내다니 진짜 대박이에요!! 🎉 고생 엄청 많았어요. 당신은 정말 최고예요! 앞으로도 잘 할 수 있을 거예요🩷"
                                st.balloons()
                        else:
                            current_task = st.session_state.tasks[st.session_state.step]
                            bot_response = f"귀찮은 거 완전 인정이에요! 😅 그런데 **{current_task}** 이것만 해봐요. 당신은 할 수 있어요. 제가 늘 곁에 있을게요 ✍️"

                    st.session_state.latest_audio_html = generate_tts_html(bot_response)

                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                st.session_state.awaiting_bot = False
                st.rerun() 
                
    with st.form("chat_form", clear_on_submit=True, border=False):
        inner_txt, inner_btn = st.columns([5, 1])
        with inner_txt:
            text_input = st.text_input("메시지 입력...", label_visibility="collapsed", placeholder="타자로 입력해도 돼요!")
        with inner_btn:
            submit_btn = st.form_submit_button("전송 🚀")

# 7. 입력 처리 로직
user_input = None

if audio_bytes and audio_bytes != st.session_state.last_audio:
    st.session_state.last_audio = audio_bytes
    with st.spinner("목소리를 받아적고 있어요..."): 
        user_input = perform_stt(audio_bytes) 
elif submit_btn and text_input:
    user_input = text_input

if user_input and not st.session_state.awaiting_bot:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.awaiting_bot = True
    st.rerun()
