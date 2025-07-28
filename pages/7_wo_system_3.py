from pathlib import Path
import streamlit as st
import datetime
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from pages.tool import _4oMiniClient

st.title("상황 1: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 가족들이 패밀리 레스토랑을 방문한 것으로 시작됩니다. 
사촌의 생일이라서 모인거라고 하는데 자폐 아동이 화를 내면서 떼를 쓰기 시작합니다.
영상에서는 패밀리 레스토랑에서의 피로감과 배고품으로 인하여 멜트 다운이 일어난 것 같다는 언급을 합니다.
자폐아동이 계속해서 엄머에게 떼를 쓰면서 엄마가 들고 있는 메뉴판을 뺏으려고 하고 
뜻대로 되지 않자 책상을 치거나 엄마한테 주먹질을 하는 모습을 보이고 있습니다.

원본 링크 : https://www.youtube.com/shorts/vXB3Wbph2Sk
""")

if 'llm' not in st.session_state7:
    st.session_state7.llm = _4oMiniClient()

# ID가 없으면 작성하라고 유도
if "expert_id" not in st.session_state or not st.session_state.expert_id:
    st.warning("먼저 홈에서 응답자 ID를 입력해 주세요.")
    st.stop()

if 'survey_submitted' not in st.session_state7:
    st.session_state7.survey_submitted = False

# 비디오
st.video("https://youtube.com/shorts/uDWzTxF8qeY")

# 멜트다운 초기 상황에 대한 첫 중재 방안 입력
if "comments_history" not in st.session_stat7e:
    st.session_state7.comments_history = []

if "generated_situations" not in st.session_state7:
    st.session_state7.generated_situations = []

if "loop_index" not in st.session_state7:
    st.session_state7.loop_index = 0

# 초기 질문만 출력
if st.session_state7.loop_index == 0:
    comment = st.text_area("주어진 상황에 대하여 가장 적절한 것으로 보이는 중재 방안을 입력해주세요", key="initial_comment")
    if st.button("다음"):
        if comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state7.comments_history.append(comment)
        st.session_state7.loop_index += 1
        st.rerun()

# 반복 상황 생성 루프
elif 1 <= st.session_state7.loop_index <= 3:
    idx = st.session_state7.loop_index

    # 상황 생성
    if len(st.session_state7.generated_situations) < idx:
        user_comment = st.session_state7.comments_history[-1]
        previous_situation = st.session_state7.generated_situations[-1] if st.session_state7.generated_situations else "초기 멜트다운: 커튼 밖의 밝은 빛 자극으로 인하여 멜트 다운을 일으킴. 소리를 지르고 울면서 불안한 모습을 보이고 있음"
        prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
                     {previous_situation}
                     이에 대해 전문가가 제시한 중재 방안은 다음과 같습니다:
                     {user_comment}
                     이 중재 방안이 자폐인의 멜트다운을 충분히 완화하지 못했거나, 오히려 새로운 갈등 요소를 유발한 **새로운 상황**을 생성해주세요.
                     감각 자극, 외부 요인, 아동의 정서 반응 등을 포함하여 구체적으로 기술해주세요.
                  """
        new_situation = st.session_state7.llm.call_as_llm(prompt)
        st.session_state7.generated_situations.append(new_situation)

    # 새로운 상황 제시 및 중재 방안 입력
    st.markdown(f"### 새로 생성된 상황 {idx}")
    st.markdown(st.session_state7.generated_situations[idx - 1])

    new_comment = st.text_area("이 상황에 적절한 중재 방안을 입력해주세요", key=f"comment_{idx}")
    if st.button("다음", key=f"next_{idx}"):
        if new_comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state7.comments_history.append(new_comment)
        st.session_state7.loop_index += 1
        st.rerun()


elif st.session_state7.loop_index > 3:
    st.success("3회의 상황 생성 및 중재 응답이 완료되었습니다. 감사합니다.")

    if not st.session_state7.survey_submitted:
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
            for i, (situation, intervention) in enumerate(zip(st.session_state7.generated_situations, st.session_state7.comments_history[1:]), start=1):
                f.write(
                    f"{now},{expert_id},{i},"
                    f"\"{situation.strip()}\","
                    f"\"{intervention.strip()}\"\n"
                )

        st.session_state7.survey_submitted = True
        st.info("응답이 저장되었습니다. 감사합니다.")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("◀ 이전 페이지"):
                st.switch_page("pages/6_servey_system_2.py")       # pages/home.py (확장자 제외)
        with col2:
            if st.button("다음 페이지 ▶"):
                st.switch_page("pages/8_w_system_3.py")    # pages/survey2.py (확장자 제외)
    
