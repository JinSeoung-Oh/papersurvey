from pathlib import Path
import streamlit as st
import datetime
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from pages.tools import _4oMiniClient

st.title("상황 2: 등교길에서 발생한 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 자폐아동이 가족들과 함께 학교에 등교하고 있는 모습으로 시작됩니다.
길을 가던 도중에 지나가야 하는 길에 작은 토끼가 한 마리 앉아 있었습니다.
가족들은 귀여운 토끼의 모습에 감탄을 하였지만, 토끼를 본 자폐인은 이내 겁에 질린 듯한 모습을 보입니다.
이내 울면서 멜트 다운 상태가 되었습니다.

원본 링크 : https://www.youtube.com/watch?v=Cflrzyu_WZk
""")

for key in [k for k in st.session_state.keys() if k != "expert_id"]:
    del st.session_state[key]

if 'llm' not in st.session_state:
    st.session_state.llm = _4oMiniClient()

# ID가 없으면 작성하라고 유도
if "expert_id" not in st.session_state or not st.session_state.expert_id:
    st.warning("먼저 홈에서 응답자 ID를 입력해 주세요.")
    st.stop()

if 'survey_submitted' not in st.session_state:
    st.session_state.survey_submitted = False

# 비디오
st.video("https://youtu.be/AaWWfjb8DjM")

# 멜트다운 초기 상황에 대한 첫 중재 방안 입력
if "comments_history" not in st.session_state4:
    st.session_state.comments_history = []

if "generated_situations" not in st.session_state4:
    st.session_state.generated_situations = []

if "loop_index" not in st.session_state4:
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
        previous_situation = st.session_state.generated_situations[-1] if st.session_state.generated_situations else "초기 멜트다운: 등교길에 우연히 만난 토끼에 매우 놀란 모습을 보임. 울면서 불안한 모습을 보이고 있음"
        prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
                     {previous_situation}
                     이에 대해 전문가가 제시한 중재 방안은 다음과 같습니다:
                     {user_comment}
                     이 중재 방안이 자폐인의 멜트다운을 충분히 완화하지 못했거나, 자폐인의 멜트 다운이 너무 심해서 중재를 거부한다거나 혹은 오히려 새로운 갈등 요소를 유발한 **새로운 상황**을 생성해주세요.
                     감각 자극, 외부 요인, 아동의 정서 반응 등을 포함하여 구체적으로 기술해주세요. 상황 묘사에만 집중해주세요. 중재 방안이나 전문가는 등장해서는 안 됩니다.
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

    if not st.session_state.survey_submitted:
        # 자동 저장
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey2_loop.csv")

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

        st.session_state.survey_submitted = True
        st.info("응답이 저장되었습니다. 감사합니다.")

    # 다음 페이지 이동 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/3_servey_system_1.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/5_w_system_2.py")
