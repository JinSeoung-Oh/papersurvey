from pathlib import Path
import streamlit as st
import datetime
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from pages.tools import _4oMiniClient

st.title("상황 1: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 Ian은 창문 가까이에서 커튼을 젖히고 바깥을 바라보고 있는데, 바깥은 매우 밝습니다.
바깥을 바라보던 그는 잠시 후 눈에 띄게 불안한 상태에 빠지며, 울음을 터뜨리고 큰 소리로 외치며 강한 정서적 동요를 보입니다.
그는 “Lucifer가 나를 훔쳐가려 한다”, “비가 와야 한다”고 반복적으로 말하는데, 특히 비가 오지 않으면 캠핑을 가지 못한다고 생각하고 있으며
동시에 비가 와야 더러운 공기를 씻어낼 수 있다는 믿음을 갖고 있는 것으로 보입니다. 
Ian은 울면서 소리를 지르고, 언어적 혼란, 강박적인 반복 발화, 감정 폭발 등의 모습을 보이고 있습니다.
영상에 의하면 Ian은 감각적 자극 완하를 위하여 담요를 머리 끝까지 쓰는 것을 선호하는 것으로 보입니다.

원본 링크 : https://www.youtube.com/watch?v=C0rdZOhet24
""")

if 'llm' not in st.session_state:
    st.session_state.llm = _4oMiniClient()

# ID가 없으면 작성하라고 유도
if "expert_id" not in st.session_state or not st.session_state.expert_id:
    st.warning("먼저 홈에서 응답자 ID를 입력해 주세요.")
    st.stop()

if 'survey1_submitted' not in st.session_state:
    st.session_state.survey1_submitted = False

# 비디오
st.video("https://youtu.be/GjddtdjWaj8")

# 멜트다운 초기 상황에 대한 첫 중재 방안 입력
if "comments_history" not in st.session_state:
    st.session_state.comments_history = []

if "generated_situations" not in st.session_state:
    st.session_state.generated_situations = []

if "loop_index" not in st.session_state:
    st.session_state.loop_index = 0

# 초기 질문만 출력
if st.session_state.loop_index == 0:
    comment = st.text_area("주어진 상황에 대하여 가장 적절한 것으로 보이는 중재 방안을 입력해주세요", key="initial_comment")
    if st.button("다음"):
        if comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state.comments_history.append(comment)
        st.session_state.loop_index += 1
        st.rerun()

# 반복 상황 생성 루프
elif 1 <= st.session_state.loop_index <= 3:
    idx = st.session_state.loop_index

    # 상황 생성
    if len(st.session_state.generated_situations) < idx:
        user_comment = st.session_state.comments_history[-1]
        previous_situation = st.session_state.generated_situations[-1] if st.session_state.generated_situations else "초기 멜트다운: 커튼 밖의 밝은 빛 자극으로 인하여 멜트 다운을 일으킴. 소리를 지르고 울면서 불안한 모습을 보이고 있음"
        user_profile = {'sensory_profile': {'sound': 'medium', 'light': 'high'}, 'comm_prefs': {'visual': 'medium', 'verbal': 'high'}, 'stress_signals': ['aggressive behavior'],'preference': ['Block the light with a blanket']}
        prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
                     {previous_situation}
                     이에 대해 전문가가 제시한 중재 방안은 다음과 같습니다:
                     {user_comment}
                     이 중재 방안이 자폐인의 멜트다운을 충분히 완화하지 못했거나, 자폐인의 멜트 다운이 너무 심해서 중재를 거부한다거나 혹은 오히려 새로운 갈등 요소를 유발한 **새로운 상황**을 생성해주세요.
                     다만 억지로 상황을 만들지 마시고 자연스럽게 이어지도록 상황을 만들어주세요. {user_profile}을 참고하여 자연스럽게 만들어주시되 만약 {user_profile}에 맞지 않은 상황을 제시하실 때에는 납득 가능한 수준으로 서술해주세요.
                     **억지로 상황을 만들어 복잡하게 하지 마세요**
                     감각 자극, 외부 요인, 아동의 정서 반응 등을 포함하여 관찰자 시점으로 기술해주세요. 특히 상황 묘사에 집중해주세요. 중재 방안이나 전문가는 등장해서는 안 됩니다.
                     단 하나의 감각 자극에 의한 상황을 제시해주세요. 새롭게 만들어진 상황에는 감각 자극은 단 한 종류만 등장해야만 합니다.
                     당신이 생성해야 하는 상황은 전문가가 제시한 중재 방안을 시도한 뒤의 상황임을 명심하십시오.
                     현재 전문가가 자폐인에게 취한 중재 방안으로 인한 자폐인의 상태를 반드시 고려하여 논리적으로 말이 되는 상황이어야만 합니다. 
                     예를 들어 전문가가 빛을 차단하기 위하여 자폐인에게 담요를 덮어씌여주었으면 자폐인은 그 상태에서는 빛을 볼 수 없습니다.  
                  """
        new_situation = st.session_state.llm.call_as_llm(prompt)
        st.session_state.generated_situations.append(new_situation)

    # 새로운 상황 제시 및 중재 방안 입력
    st.markdown(f"### 새로 생성된 상황 {idx}")
    st.markdown(st.session_state.generated_situations[idx - 1])

    new_comment = st.text_area("이 상황에 적절한 중재 방안을 입력해주세요", key=f"comment_{idx}")
    if st.button("다음", key=f"next_{idx}"):
        if new_comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state.comments_history.append(new_comment)
        st.session_state.loop_index += 1
        st.rerun()


elif st.session_state.loop_index > 3:
    st.success("3회의 상황 생성 및 중재 응답이 완료되었습니다. 감사합니다.")

    if not st.session_state.survey1_submitted:
        # 자동 저장
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_loop.csv")

        # 파일이 없다면 헤더 추가
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("timestamp,expert_id,loop_index,situation,intervention\n")

        # 상황 + 중재 방안 저장
        with open(filepath, "a", encoding="utf-8") as f:
            for i, (situation, intervention) in enumerate(zip(st.session_state.generated_situations, st.session_state.comments_history[1:]), start=1):
                f.write(
                    f"{now},{expert_id},{i},"
                    f"\"{situation.strip()}\","
                    f"\"{intervention.strip()}\"\n"
                )

        st.session_state.survey1_submitted = True
        st.info("응답이 저장되었습니다. 감사합니다.")

    # 다음 페이지 이동 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/0_ProfessionalExperience.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/2_w_system_1.py")
