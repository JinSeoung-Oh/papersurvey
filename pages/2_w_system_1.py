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
        "자기 방에서 A는 밝은 바깥을 보던 중 갑작스럽게 정서적 멜트다운에 빠져 울고 소리를 지르며, “Lucifer가 나를 훔쳐간다”, “비가 와야 한다”는 강박적이고 혼란스러운 발화를 반복하는 등 불안과 감정 폭발을 보입니다."
    )
    st.session_state.strategy = {
        'cause': '강한 시각 자극과 환경의 혼란으로 인해 A는 감각 과부하를 경험하면서 내면의 불안이 공격적인 반응으로 표출될 수 있음',
        'intervention': [
            {'strategy': '환경 빛 차단',
             'purpose': '강한 밝은 빛에 의한 감각 과부하를 줄여 A가 불안을 느끼지 않도록 돕기 위함',
             'example': {'immediate': '위급 상황에서 즉시 블랭킷으로 창문 쪽 빛을 차단하며 A에게 부드럽게 다가가 진정 유도',
                         'standard': '교실이나 생활공간에 조절 가능한 커튼, 블라인드 설치 및 정기적인 빛 조절 점검을 통해 안정된 시각 환경 제공'}}
        ]
    }
    st.session_state.history = []
    st.session_state.loop_count = 0

# 관리자 정의 초기 안내

st.title("상황 1: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 Ian은 창문 가까이에서 커튼을 젖히고 바깥을 바라보고 있는데, 바깥은 매우 밝습니다.
바깥을 바라보던 그는 잠시 후 눈에 띄게 불안한 상태에 빠지며, 울음을 터뜨리고 큰 소리로 외치며 강한 정서적 동요를 보입니다.
그는 “Lucifer가 나를 훔쳐가려 한다”, “비가 와야 한다”고 반복적으로 말하는데, 특히 비가 오지 않으면 캠핑을 가지 못한다고 생각하고 있으며
동시에 비가 와야 더러운 공기를 씻어낼 수 있다는 믿음을 갖고 있는 것으로 보입니다. 
A는 울면서 소리를 지르고, 언어적 혼란, 강박적인 반복 발화, 감정 폭발 등의 모습을 보이고 있습니다.
영상에 의하면 A는 감각적 자극 완하를 위하여 담요를 머리 끝까지 쓰는 것을 선호하는 것으로 보입니다.

**자폐인 A의 프로파일**  \n가상의 자폐인 A는 광반응에 매우 민감하고 소리에도 어느 정도 민감하며 의사소통 시에는 소리를 통한 대화를 더 선호하는 것으로 세팅했습니다. 스트레스를 받을 시에 공격적인 성향을 보이며 담요 속에서 안정감을 빠르게 가집니다.

**자폐인 A의 관찰 일지**  \n**상황_1** : A는 아침 식사 중 창문 옆 식탁에 앉아 있음. 커튼이 안 쳐져 있어 아침 햇빛이 강하게 비추고 있고 A가 이에 짜증을 내며 아침을 먹는 것을 거부하고 있음  \n**중재_1** : 즉각적으로 커튼을 치고 A에게 다가가 낮고 부드러운 목소리로 진정을 유도하였음

**상황_2** : 가족과 함께 야외 공원 피크닉을 왔음. 나무 그늘이 아래에 있었으나 부분적으로 햇빛이 들어오고 있었고 A가 나무를 올려다보다가 짜증을 갑자기 짜증을 내기 시작하였음  \n**중재_2** : 선글라스를 껴주면서 가만히 안아주며 부드러운 목소리로 진정을 유도하였음

**LLM의 답변에 대하여 판단 하실 때 위에서 제시 된 자폐인의 프로파일과 관찰일지를 참고해주시면 감사드리겠습니다.**

원본 링크 : https://www.youtube.com/watch?v=C0rdZOhet24
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

    # 4) 루프 진행: 최대 3번
    if st.session_state.loop_index < 3:
        idx = st.session_state.loop_index
        prev_situation = (
            st.session_state.initial_situation if idx == 0
            else st.session_state.generated_situations[idx - 1]
        )
      
        # 3) 업데이트된 전략 피드백 영역
        updated_strat = st.session_state.current_strategy
        st.subheader("🤖 업데이트된 중재 전략 피드백")
        st.write(f"**문제 상황 (업데이트):** {prev_situation}")
        st.write(f"**원인:** {updated_strat.get('cause')}")
        st.write("**중재 후보 (업데이트):**")
        for i, intr in enumerate(updated_strat.get('intervention', []), 1):
          st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
          st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
          st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

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
이 중재 방안이 충분히 완화하지 못했거나 중재 방안이 자폐인에 의해 거부되었을 때 발생한 **새로운 상황**을 자연스럽게 생성해주세요.
감각 자극, 외부 요인, 아동의 정서 반응을 포함하여 구체적으로 기술하세요. 상황 묘사에만 집중하세요. 당신의 답변에 중재방안이나 전문가의 의견이 들어가서는 안 됩니다.
새로운 문제 상황을 만들기 위하여 억지스러운 상황은 만들지 마시고 너무 상황을 극단적으로 묘사하지 마세요. 현실에서 발생할 수 있는 자연스러운 상황 이어야만하며 {prev_situation}과 자여스럽게 이어지는 상황이어야만 합니다.
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
            
    elif st.session_state.loop_index >= 3 and not st.session_state.survey_saved:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_feedbackloop.csv")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
            for i in range(3):
                situation = st.session_state.generated_situations[i].replace("\n", " ")
                comment = st.session_state.user_comments[i].replace("\n", " ")
                strategy = json.dumps(st.session_state.generated_strategies[i+1], ensure_ascii=False).replace("\n", " ")
                f.write(f"{now},{expert_id},{i+1},\"{situation}\",\"{comment}\",\"{strategy}\"\n")
        st.session_state.survey_saved = True
        st.success("3회의 루프가 완료되었고 응답이 자동 저장되었습니다. 감사합니다.")

if st.session_state.survey_saved:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/1_wo_system_1.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/3_servey_system_1.py")
