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

PKL_FILE = PROJECT_ROOT / "caregraph_full.pkl"
sys.modules["__main__"].CareGraph = CareGraph

outformat = {
  "action_input": {
    "Aggressive behavior": {
      "cause": "Brief cause description",
      "intervention": [
        "Intervention 1",
        "Intervention 2",
        "..."
      ]
    },
    "Self‑harm behavior": {
      "cause": "Brief cause description",
      "intervention": [
        "Intervention 1",
        "Intervention 2",
        "..."
      ]
    },
    "Tantrum behavior": {
      "cause": "Brief cause description",
      "intervention": [
        "Intervention 1",
        "Intervention 2",
        "..."
      ]
    },
    "Ambiguous physical interaction": {
      "cause": "Brief cause description",
      "intervention": [
        "Intervention 1",
        "Intervention 2",
        "..."
      ]
    }
  }
}

st.video("https://youtu.be/GjddtdjWaj8")

for key in [k for k in st.session_state.keys() if k != "expert_id"]:
    del st.session_state[key]

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

if 'llm' not in st.session_state:
    st.session_state.llm = _4oMiniClient()

# --- Session initialization ---
if 'graph' not in st.session_state:
    # Initialize or load CareGraph and profile
    if PKL_FILE.exists():
        st.session_state.graph = load_graph(str(PKL_FILE))
    else:
        st.session_state.graph = CareGraph(st.session_state.llm)
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="A123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state.graph.add_profile(profile)

if 'agent' not in st.session_state:
    st.session_state.agent = MemoryAgent(st.session_state.llm, st.session_state.graph)
    
# --- Page‐specific state (state2) initialization ---
if 'state2' not in st.session_state:
    st.session_state.state = "feedback_loop"
    st.session_state.situation = (
        "패밀리 레스토랑에서 자폐 아동이 피로와 배고픔으로 인해 멜트다운을 일으키며 메뉴판을 빼앗으려다 통제가 되지 않자 공격적인 행동을 보입니다."
    )
    st.session_state.strategy = {
        'cause': '소음 등 감각 과부하와 피로, 배고픔 등의 신체적 불편감이 누적되어, 아동이 자신을 표현하는 방법으로 소리 지르며 요구하는 행동으로 나타남.',
        'intervention': [
            {'strategy': '감각 조절 및 선호 전략 제공',
             'purpose': '아동이 과도한 자극을 받았을 때 선호하는 Worm hug를 통해 신체적 안정감을 취하도록 돕고, 감각 과부하를 완화하기 위함',
             'example': {'immediate': '당장 아동에게 Worm hug를 제공하여 신체 접촉을 통한 안정감을 빠르게 제공한다',
                         'standard': '일상적으로 감각 통합 치료 세션에서 Worm hug와 같은 선호 전략을 연습시킴으로써, 식당 등 외부자극이 강한 환경에서도 자체 조절능력을 기를 수 있도록 돕는다'}}
        ]
    }
    st.session_state.history = []
    st.session_state.loop_count = 0

# 관리자 정의 초기 안내

st.title("상황 3: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 가족들이 패밀리 레스토랑을 방문한 것으로 시작됩니다. 
사촌의 생일이라서 모인거라고 하는데 자폐 아동이 화를 내면서 떼를 쓰기 시작합니다.
영상에서는 패밀리 레스토랑에서의 피로감과 배고품으로 인하여 멜트 다운이 일어난 것 같다는 언급을 합니다.
자폐아동이 계속해서 엄머에게 떼를 쓰면서 엄마가 들고 있는 메뉴판을 뺏으려고 하고 
뜻대로 되지 않자 책상을 치거나 엄마한테 주먹질을 하는 모습을 보이고 있습니다.

**자폐인 A의 프로파일**  \n가상의 자폐인 A는 소리와 광반응에 매우 민감하며 의사소통 시에는 바디랭귀지는 선호하지 않고 소리를 통한 대화는 어느정도는 선호하는 것으로 세팅했습니다. 스트레스를 받을 시에 공격적인 성향을 보이는 것으로 설정했습니다. 선호하는 감각은 따뜻한 포옹입니다.

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
if st.session_state.state == "feedback_loop":
    # 1) 초기화: loop_index, 전략 상태, 초기 상황 저장
    if 'loop_index' not in st.session_state:
        st.session_state.loop_index = 0
        st.session_state.generated_situations = []
        st.session_state.generated_strategies = [st.session_state.strategy]
        st.session_state.current_strategy = st.session_state.strategy
        st.session_state.user_comments = []
        st.session_state.survey_saved = False
        # 초기 상황 복사
        st.session_state.initial_situation = st.session_state.situation

    # 2) 초기(디폴트) 피드백 영역
    default_strat = st.session_state.strategy
    st.subheader("🤖 초기 중재 전략 피드백")
    st.write(f"**문제 상황 (초기):** {st.session_state.initial_situation}")
    st.write(f"**원인:** {default_strat.get('cause')}")
    st.write("**중재 후보 (초기):**")
    for i, intr in enumerate(default_strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 구분선
    st.markdown("---")

    # 3) 업데이트된 전략 피드백 영역
    updated_strat = st.session_state.current_strategy
    st.subheader("🤖 업데이트된 중재 전략 피드백")
    st.write(f"**문제 상황 (업데이트):** {st.session_state.situation}")
    st.write(f"**원인:** {updated_strat.get('cause')}")
    st.write("**중재 후보 (업데이트):**")
    for i, intr in enumerate(updated_strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 4) 루프 진행: 최대 3번
    if st.session_state.loop_index < 3:
        idx = st.session_state.loop_index
        prev_situation = (
            st.session_state.initial_situation if idx == 0
            else st.session_state.generated_situations[idx - 1]
        )

        # 전략 요약 텍스트 생성
        intervention_txt = ""
        for item in updated_strat.get('intervention', []):
            intervention_txt += (
                f"- 전략: {item.get('strategy')}\n"
                f"  - 목적: {item.get('purpose')}\n"
                f"  - 즉시 적용: {item.get('example', {}).get('immediate')}\n"
                f"  - 표준 상황: {item.get('example', {}).get('standard')}\n\n"
            )

        loop_key = f"new_situation_{idx}"
        # 최초 진입 또는 미생성 시 새로운 상황 생성
        if loop_key not in st.session_state:
            prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
{prev_situation}
이에 대해 전문가가 제시한 중재 전략은 다음과 같습니다:
{intervention_txt}
이 중재 방안이 충분히 완화하지 못했거나 상황이 거부되었을 때 발생한 **새로운 상황**을 자연스럽게 생성해주세요.
감각 자극, 외부 요인, 아동의 정서 반응을 포함하여 구체적으로 기술하세요.
단 하나의 감각 자극만 포함되어야 합니다."""
            new_sit = st.session_state.llm.call_as_llm(prompt)
            st.session_state[loop_key] = new_sit
            st.session_state.generated_situations.append(new_sit)
            st.session_state.situation = new_sit

        # 5. 새 상황 표시
        st.markdown(f"### 🔄 루프 {idx+1} — 생성된 새로운 상황")
        st.markdown(st.session_state[loop_key])

        # 6. 사용자 코멘트 입력 폼
        with st.form(key=f"loop_form_{idx}"):
            comment = st.text_area(
                "현재 주어진 상황을 자유롭게 요약하여 입력해주세요",
                key=f"comment_{idx}"
            )
            submitted = st.form_submit_button("다음")

        if submitted:
            if not comment.strip():
                st.warning("댓글을 작성해주세요.")
                st.stop()
            st.session_state.user_comments.append(comment)

            # 7. MemoryAgent 전략 생성
            agent = st.session_state.agent
            caregraph = st.session_state.graph
            user_id = "A123"
            situation = st.session_state[loop_key]
            sid, similar_events = caregraph.find_similar_events(user_id, situation)
            user_profile = agent._profile_ctx(user_id)

            if sid is not None and similar_events:
                formatted_events = "\n".join([
                    f"{i+1}. 원인: {e['cause']}, 전략: {e['strategy']}, 목적: {e['purpose']}"
                    for i, e in enumerate(similar_events)
                ])
                response = agent.graph_ask(user_id, comment, formatted_events, user_profile)
            else:
                failed_events = updated_strat.get('intervention', [])
                response = agent.alt_ask(
                    user_id,
                    comment,
                    failed_event=failed_events,
                    user_profile=user_profile,
                    situation=situation
                )

            # 8. JSON repair & 파싱
            repaired = repair_json(response)
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError as e:
                st.error(f"⚠️ JSON 파싱 오류: {e}")
                st.stop()

            # 9. 전략 업데이트
            try:
                action_input = parsed["action_input"]
                first_event = list(action_input.values())[0]
                cause = first_event.get("cause")
                interventions = first_event.get("intervention")
                structured = {"cause": cause, "intervention": interventions}
                st.session_state.current_strategy = structured
                st.session_state.generated_strategies.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            # 10. 루프 인덱스 증가 및 rerun
            st.session_state.loop_index += 1
            st.rerun()

if session_state.survey_saved:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/1_wo_system_1.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/3_servey_system_1.py")

if st.session_state.survey_saved:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/7_wo_system_3.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/9_servey_system_3.py")
