import streamlit as st
import json
import datetime
import joblib
import os
from json_repair import repair_json
import re
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from pages.tools import CareGraph, MemoryAgent, _4oMiniClient, UserProfile

# 비디오
st.video("https://youtube.com/shorts/uDWzTxF8qeY")

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

# --- Session initialization ---
if 'graph' not in st.session_state8:
    # Initialize or load CareGraph and profile
    if os.path.exists("../caregraph_full.pkl"):
        st.session_state8.graph = load_graph("../caregraph_full.pkl")
    else:
        st.session_state8.graph = CareGraph()
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="A123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state8.graph.add_profile(profile)

if 'llm' not in st.session_state8:
    st.session_state8.llm = _4oMiniClient()

if 'agent' not in st.session_state8:
    st.session_state8.agent = MemoryAgent(st.session_state8.llm, st.session_state8.graph)
    
# --- Page‐specific state (state2) initialization ---
if 'state2' not in st.session_state8:
    st.session_state8.state = "feedback_loop"
    st.session_state8.situation = (
        "패밀리 레스토랑에서 자폐 아동이 피로와 배고픔으로 인해 멜트다운을 일으키며 메뉴판을 빼앗으려다 통제가 되지 않자 공격적인 행동을 보입니다."
    )
    st.session_state8.strategy = {
        'cause': '소음 등 감각 과부하와 피로, 배고픔 등의 신체적 불편감이 누적되어, 아동이 자신을 표현하는 방법으로 소리 지르며 요구하는 행동으로 나타남.',
        'intervention': [
            {'strategy': '감각 조절 및 선호 전략 제공',
             'purpose': '아동이 과도한 자극을 받았을 때 선호하는 'Worm hug'를 통해 신체적 안정감을 취하도록 돕고, 감각 과부하를 완화하기 위함',
             'example': {'immediate': '당장 아동에게 'Worm hug'를 제공하여 신체 접촉을 통한 안정감을 빠르게 제공한다',
                         'standard': '일상적으로 감각 통합 치료 세션에서 'Worm hug'와 같은 선호 전략을 연습시킴으로써, 식당 등 외부자극이 강한 환경에서도 자체 조절능력을 기를 수 있도록 돕는다'}}
        ]
    }
    st.session_state8.history = []
    st.session_state8.loop_count = 0

# 관리자 정의 초기 안내

st.title("상황 3: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 가족들이 패밀리 레스토랑을 방문한 것으로 시작됩니다. 
사촌의 생일이라서 모인거라고 하는데 자폐 아동이 화를 내면서 떼를 쓰기 시작합니다.
영상에서는 패밀리 레스토랑에서의 피로감과 배고품으로 인하여 멜트 다운이 일어난 것 같다는 언급을 합니다.
자폐아동이 계속해서 엄머에게 떼를 쓰면서 엄마가 들고 있는 메뉴판을 뺏으려고 하고 
뜻대로 되지 않자 책상을 치거나 엄마한테 주먹질을 하는 모습을 보이고 있습니다.

**자폐인 A의 프로파일**  \n가상의 자폐인 A는 소리에 매우 민감하며 광반응에는 그렇게까지 민감하지 않고 의사소통 시에는 대화만 하는 것보다는 바디 랭귀지를 섞는 것을 더 선호하는 것으로 세팅했습니다. 스트레스를 받을 시에 손을 흔들거나 혹은 공격적인 성향을 보이는 것으로 설정했습니다.

**자폐인 A의 관찰 일지**  \n**상황_1** : 자폐 아동이 학원 교실에 도착. 평소 앉던 자리에 다른 학생이 먼저 앉아 있었음. 이에 자폐 아동이 화를 내며 떼를 쓰기 시작함  \n**중재_1** : 자폐 아동을 부드럽게 안아주며 그 자리에 앉아 있는 학생에게 양해를 구함

**상황_2** : 자폐 아동이 부모와 함께 장난감 가게에 방문. 원하는 장난감을 발견하였으나 부모가 예산상 구매를 거절함.  \n**중재_2** : 자폐 아동을 부드럽게 안아주며 진정 시킨 뒤에 평소에 좋아하던 곰인형을 안겨주며 관심을 다른 곳으로 유도하였음

**LLM의 답변에 대하여 판단 하실 때 위에서 제시 된 자폐인의 프로파일과 관찰일지를 참고해주시면 감사드리겠습니다.**

원본 링크 : https://www.youtube.com/shorts/vXB3Wbph2Sk
""")

# Expert ID input
if 'expert_id' not in st.session_state:
    st.session_state.expert_id = st.text_input("응답자 ID를 입력해주세요.")
    if not st.session_state.expert_id:
        st.stop()

# --- Feedback loop ---
if st.session_state8.state == "feedback_loop":
    strat = st.session_state8.strategy

    st.subheader("🤖 중재 전략 피드백")
    st.write(f"**문제 상황:** {st.session_state8.situation}")
    st.write(f"**원인:** {strat.get('cause')}")
    st.write("**중재 후보:**")
    for i, intr in enumerate(strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    if 'loop2_index' not in st.session_state2:
        st.session_state8.loop_index = 0
        st.session_state8.generated_situations = []
        st.session_state8.generated_strategies = [st.session_state8.strategy]  # 초기 전략 포함
        st.session_state8.user_comments = []
        st.session_state8.survey_saved = False
        
    if st.session_state8.loop_index < 3:
        idx = st.session_state8.loop_index
        current_strategy = st.session_state8.generated_strategies[idx]

        previous_situation = (
            st.session_state8.situation if idx == 0
            else st.session_state8.generated_situations[idx - 1]
        )
        
        intervention_txt = ""
        for item in current_strategy.get('intervention', []):
            intervention_txt += (
                f"- 전략: {item.get('strategy')}\n"
                f"  - 목적: {item.get('purpose')}\n"
                f"  - 즉시 적용: {item.get('example', {}).get('immediate')}\n"
                f"  - 표준 상황: {item.get('example', {}).get('standard')}\n\n"
            )
   
        prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
                     {previous_situation}
                     이에 대해 전문가가 제시한 중재 전략은 다음과 같습니다:
                     {intervention_txt}
                     이 전략이 충분하지 않거나 새로운 자극 요인에 의해 실패할 수 있는 **새로운 멜트다운 상황**을 생성해주세요.
                     감각 자극, 외부 요인, 아동의 정서 반응 등을 포함해 주세요. 상황 묘사에만 집중해주세요. 중재 방안이나 전문가는 등장해서는 안 됩니다.
                     """
        new_situation = st.session_state8.llm.call_as_llm(prompt)
        st.session_state8.generated_situations.append(new_situation)

        # 2. 상황 사용자에게 제시
        st.markdown(f"### 🔄 루프 {idx+1} — 생성된 새로운 상황")
        st.markdown(new_situation)

        # 3. 사용자 comment 입력
        comment = st.text_area("현재 주어진 상황을 자유롭게 요약하여 입력해주세요", key=f"comment_{idx}")
        if st.button("다음", key=f"next_{idx}"):
            if comment.strip() == "":
                st.warning("댓글을 작성해주세요.")
                st.stop()
            st.session_state8.user_comments.append(comment)
            
            # 4. MemoryAgent가 전략 생성
            agent = st.session_state8.agent
            caregraph = st.session_state8.graph
            user_id = "A123"
            situation = new_situation
            sid, similar_events = caregraph.find_similar_events(user_id, situation)
            user_profile = agent._profile_ctx(user_id)

            if sid is not None and similar_events:
                formatted_events = "\n".join([
                    f"{i+1}. 원인: {e['cause']}, 전략: {e['strategy']}, 목적: {e['purpose']}"
                    for i, e in enumerate(similar_events)
                ])
                response = agent.graph_ask(user_id, comment, formatted_events, user_profile)
            else:
                response = agent.alt_ask(user_id, comment, failed_event="N/A", user_profile=user_profile, situation=situation)
            
            parsed = agent._parse_json(response)
            if parsed is None or not isinstance(parsed, dict):
                st.error("⚠️ 중재 전략 생성 실패: JSON 파싱 오류")
                st.stop()
            try:
                action_input = parsed["action_input"]
                first_event = list(action_input.values())[0]
                cause = first_event.get("cause")
                interventions = first_event.get("intervention")
                structured = {"cause": cause, "intervention": interventions}
                st.session_state8.generated_strategies.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            st.session_state8.loop_index += 1
            st.rerun()
            
    elif st.session_state8.loop_index >= 3 and not st.session_state8.survey_saved:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_feedbackloop.csv")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
            for i in range(3):
                situation = st.session_state8.generated_situations[i].replace("\n", " ")
                comment = st.session_state2.user_comments[i].replace("\n", " ")
                strategy = json.dumps(st.session_state8.generated_strategies[i+1], ensure_ascii=False).replace("\n", " ")
                f.write(f"{now},{expert_id},{i+1},\"{situation}\",\"{comment}\",\"{strategy}\"\n")
        st.session_state8.survey_saved = True
        st.success("3회의 루프가 완료되었고 응답이 자동 저장되었습니다. 감사합니다.")

if session_state8.survey_saved:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/1_wo_system_1.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/3_servey_system_1.py")

if st.session_state.survey7_submitted:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/7_wo_system_3.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/9_servey_system_3.py")
