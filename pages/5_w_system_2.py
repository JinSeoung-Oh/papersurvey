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

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

if 'llm' not in st.session_state:
    st.session_state.llm5 = _4oMiniClient()

# --- Session initialization ---
if 'graph' not in st.session_state:
    # Initialize or load CareGraph and profile
    if PKL_FILE.exists():
        st.session_state.graph5 = load_graph(str(PKL_FILE))
    else:
        st.session_state.graph5 = CareGraph(st.session_state.llm5)
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="A123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state.graph5.add_profile(profile)

if 'agent' not in st.session_state:
    st.session_state.agent5 = MemoryAgent(st.session_state.llm5, st.session_state.graph5)
    
# --- Page‐specific state (state2) initialization ---
if 'state5' not in st.session_state:
    st.session_state.state5 = "feedback_loop"
    st.session_state.situation5 = (
        "학교에 등교 중이던 자폐아동이 길에 앉아 있는 토끼를 보고 겁에 질려 울며 멜트다운을 일으켰다."
    )
    st.session_state.strategy5 = {
        'cause': '자폐 아동이 가족과 함께 등교 중 경로에 예상치 못한 토끼를 발견하고, 가족의 긍정적 반응과 상반되는 본인의 감각 과부하 및 공포 경험으로 인해 감정 조절에 어려움을 겪으면서 폭발적 감정표현(울음 및 멜트다운 상태)에 이르게 됨',
        'intervention': [
            {'strategy': '환경 안정화',
             'purpose': '아동이 안전함을 인지하고 과도한 감각 자극을 줄여 정서적 안정을 찾도록 지원함',
             'example': {'immediate': '아동이 불안한 표정을 보일 경우 즉시 조용한 장소로 안내하고, 짧은 심호흡 및 신체 접촉(선호하는 블랭킷 제공)을 통해 안정감을 제공'',
                         'standard': '평소 교육 상황에서 감각 자극이 적은 공간을 마련하고, 시각적 자료 및 선호 도구(예: 블랭킷)를 준비하여 재현 가능한 환경 안정화 전략을 실시}}
        ]
    }
    st.session_state.history5 = []
    st.session_state.loop_count5 = 0

# 관리자 정의 초기 안내

st.title("상황 2: 등교길에서 발생한 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 자폐아동이 가족들과 함께 학교에 등교하고 있는 모습으로 시작됩니다.
길을 가던 도중에 지나가야 하는 길에 작은 토끼가 한 마리 앉아 있었습니다.
가족들은 귀여운 토끼의 모습에 감탄을 하였지만, 토끼를 본 자폐인은 이내 겁에 질린 듯한 모습을 보입니다.
이내 울면서 멜트 다운 상태가 되었습니다.

**자폐인 A의 프로파일**  \n가상의 자폐인 A는 소리에 매우 민감하며 광반응에는 그렇게까지 민감하지 않고 의사소통 시에는 대화만 하는 것보다는 바디 랭귀지를 섞는 것을 더 선호하는 것으로 세팅했습니다. 스트레스를 받을 시에 손을 흔들거나 혹은 공격적인 성향을 보이는 것으로 설정했습니다.

**자폐인 A의 관찰 일지**  \n**상황_1** : 자폐 아동이 부모와 함께 마트 입구로 향하던 중, 출입문 옆에서 대형 풍선 인형이 갑자기 움직이기 시작함.  \n**중재_1** : 깜짝 놀란 자폐인에게 평소 좋아하던 담요를 둘러주고 얼굴을 감싼 채 "괜찮아", "넌 안전해"라는 이야기를 해줌

**상황_2** : 자폐 아동이 공원 벤치에 앉아 가족과 함께 간식을 먹고 있던 중, 바로 앞에서 작은 새가 갑자기 날아오름.  \n**중재_2** : 자폐 아동을 감싸 안아주며 조용하게 "괜찮아", "안전해", "별거 아니야"라는 이야기를 해주었음 

**LLM의 답변에 대하여 판단 하실 때 위에서 제시 된 자폐인의 프로파일과 관찰일지를 참고해주시면 감사드리겠습니다.**

원본 링크 : https://www.youtube.com/watch?v=Cflrzyu_WZk
""")

# Expert ID input
if 'expert_id' not in st.session_state:
    st.session_state.expert_id = st.text_input("응답자 ID를 입력해주세요.")
    if not st.session_state.expert_id:
        st.stop()

# --- Feedback loop ---
if st.session_state.state5 == "feedback_loop":
    # 1) 초기화: loop_index, 전략 상태, 초기 상황 저장
    if 'loop_index5' not in st.session_state:
        st.session_state.loop_index5 = 0
        st.session_state.generated_situations5 = []
        st.session_state.generated_strategies5 = [st.session_state.strategy5]
        st.session_state.current_strategy5 = st.session_state.strategy5
        st.session_state.user_comments5 = []
        st.session_state.survey_saved5 = False
        # 초기 상황 복사
        st.session_state.initial_situation5 = st.session_state.situation5

    # 2) 초기(디폴트) 피드백 영역
    default_strat = st.session_state.strategy5
    st.subheader("🤖 초기 중재 전략 피드백")
    st.write(f"**문제 상황 (초기):** {st.session_state.initial_situation5}")
    st.write(f"**원인:** {default_strat.get('cause')}")
    st.write("**중재 후보 (초기):**")
    for i, intr in enumerate(default_strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 구분선
    st.markdown("---")

    # 3) 업데이트된 전략 피드백 영역
    updated_strat = st.session_state.current_strategy5
    st.subheader("🤖 업데이트된 중재 전략 피드백")
    st.write(f"**문제 상황 (업데이트):** {st.session_state.situation5}")
    st.write(f"**원인:** {updated_strat.get('cause')}")
    st.write("**중재 후보 (업데이트):**")
    for i, intr in enumerate(updated_strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 4) 루프 진행: 최대 3번
    if st.session_state.loop_index5 < 3:
        idx = st.session_state.loop_index5
        prev_situation = (
            st.session_state.initial_situation5 if idx == 0
            else st.session_state.generated_situations5[idx - 1]
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

        loop_key = f"new_situation_5_{idx}"
        # 최초 진입 또는 미생성 시 새로운 상황 생성
        if loop_key not in st.session_state:
            prompt = f"""다음은 자폐 아동의 멜트다운 상황입니다:
{prev_situation}
이에 대해 전문가가 제시한 중재 전략은 다음과 같습니다:
{intervention_txt}
이 중재 방안이 충분히 완화하지 못했거나 상황이 거부되었을 때 발생한 **새로운 상황**을 자연스럽게 생성해주세요.
감각 자극, 외부 요인, 아동의 정서 반응을 포함하여 구체적으로 기술하세요.
단 하나의 감각 자극만 포함되어야 합니다."""
            new_sit = st.session_state.llm5.call_as_llm(prompt)
            st.session_state[loop_key] = new_sit
            st.session_state.generated_situations5.append(new_sit)
            st.session_state.situation5 = new_sit

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
            st.session_state.user_comments5.append(comment)

            # 7. MemoryAgent 전략 생성
            agent = st.session_state.agent5
            caregraph = st.session_state.graph5
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
                st.session_state.current_strategy5 = structured
                st.session_state.generated_strategies5.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            # 10. 루프 인덱스 증가 및 rerun
            st.session_state.loop_index5 += 1
            st.rerun()
            
    elif st.session_state.loop_index5 >= 3 and not st.session_state.survey_saved5:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_feedbackloop.csv")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
            for i in range(3):
                situation = st.session_state.generated_situations5[i].replace("\n", " ")
                comment = st.session_state.user_comments5[i].replace("\n", " ")
                strategy = json.dumps(st.session_state.generated_strategies5[i+1], ensure_ascii=False).replace("\n", " ")
                f.write(f"{now},{expert_id},{i+1},\"{situation}\",\"{comment}\",\"{strategy}\"\n")
        st.session_state.survey_saved5 = True
        st.success("3회의 루프가 완료되었고 응답이 자동 저장되었습니다. 감사합니다.")

if st.session_state.survey_saved5:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/4_wo_system_2.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/6_servey_system_2.py")
