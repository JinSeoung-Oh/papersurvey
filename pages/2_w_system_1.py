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
st.video("https://youtu.be/GjddtdjWaj8")

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

# --- Session initialization ---
if 'graph' not in st.session_state2:
    # Initialize or load CareGraph and profile
    if os.path.exists("../caregraph_full.pkl"):
        st.session_state2.graph = load_graph("../caregraph_full.pkl")
    else:
        st.session_state2.graph = CareGraph()
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="A123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state2.graph.add_profile(profile)

if 'llm' not in st.session_state2:
    st.session_state2.llm = _4oMiniClient()

if 'agent' not in st.session_state2:
    st.session_state2.agent = MemoryAgent(st.session_state2.llm, st.session_state2.graph)
    
# --- Page‐specific state (state2) initialization ---
if 'state2' not in st.session_state2:
    st.session_state2.state = "feedback_loop"
    st.session_state2.situation = (
        "수업 종료 후, 쉬는 시간이 되었을 때 다른 반 친구들이 과학실을 가기 위해서 이동 중이었습니다. 이때 다른 반 친구들 매우 소란스럽게 떠들며 지나갔고 일부는 서로 소리를 지르며 복도를 뛰어다녔습니다. 이때 가만히 반 친구들 대화를 하던 자폐인이 갑자기 귀를 막으며 소리를 지르기 시작했습니다."
    )
    st.session_state2.strategy = {
        'cause': '수업 종료 후 복도를 이동하는 다른 반 친구들의 과도한 소음(큰 목소리와 발소리)으로 인해, 소리에 매우 민감한 자폐인 A가 청각적 감각 과부하를 경험하여 귀를 막고 소리를 지르는 불안 반응을 보임.',
        'intervention': [
            {'strategy': '물리적 청각 차단 (고밀도 폼 귀마개)',
             'purpose': '복도에서 튀어나오는 큰 소음으로 인한 자폐인의 감각 과부하를 즉시 차단',
             'example': {'immediate': '돌봄교사가 A의 손목을 부드럽게 잡고 미리 합의된 ‘귀옆 두 번 톡톡’ 제스처를 보낸 뒤, 책상 서랍에서 꺼낸 고밀도 폼 귀마개를 A가 손쉽게 양쪽 귀에 삽입하도록 유도',
                         'standard': '매일 등교 직후 1분 동안 A가 스스로 귀마개 파우치에서 꺼내 양쪽 귀에 삽입해 보는 연습을 실시해, “귀마개＝안전” 패턴을 강화'}}
        ]
    }
    st.session_state2.history = []
    st.session_state2.loop_count = 0

# 관리자 정의 초기 안내

st.title("상황 1: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 Ian은 창문 가까이에서 커튼을 젖히고 바깥을 바라보고 있는데, 바깥은 매우 밝습니다.
바깥을 바라보던 그는 잠시 후 눈에 띄게 불안한 상태에 빠지며, 울음을 터뜨리고 큰 소리로 외치며 강한 정서적 동요를 보입니다.
그는 “Lucifer가 나를 훔쳐가려 한다”, “비가 와야 한다”고 반복적으로 말하는데, 특히 비가 오지 않으면 캠핑을 가지 못한다고 생각하고 있으며
동시에 비가 와야 더러운 공기를 씻어낼 수 있다는 믿음을 갖고 있는 것으로 보입니다. 
Ian은 울면서 소리를 지르고, 언어적 혼란, 강박적인 반복 발화, 감정 폭발 등의 모습을 보이고 있습니다.
영상에 의하면 Ian은 감각적 자극 완하를 위하여 담요를 머리 끝까지 쓰는 것을 선호하는 것으로 보입니다.

**자폐인 A의 프로파일**  \n가상의 자폐인 A는 소리에 매우 민감하며 광반응에는 그렇게까지 민감하지 않고 의사소통 시에는 대화만 하는 것보다는 바디 랭귀지를 섞는 것을 더 선호하는 것으로 세팅했습니다. 스트레스를 받을 시에 손을 흔들거나 혹은 공격적인 성향을 보이는 것으로 설정했습니다.

**자폐인 A의 관찰 일지**  \n**상황_1** : 붐비고 시끄러운 슈퍼마켓 환경, 즉 많은 사람들과 소음, 낯선 자극들로 인한 감각 과부하가 원인으로 작용하여 자폐인이 불편함을 느끼고, 부모에게 향하는 항의 및 신체적 저항 행동(짜증 행동)을 나타냄  \n**중재_1** : 부모가 가능한 한 조용하고 밝기가 낮은 구역으로 즉시 이동시켜 감각 자극을 줄임

**상황_2** : 계곡에서 가족들과 즐거운 시간을 보내고 있었으나 갑자기 낯선 가족들이 자폐인의 가족이 있는 곳으로 오면서 자폐인이 분노와 공포 반응을 보였음  \n**중재_2** : 부모나 돌봄자가 부드럽게 다가가서 가볍게 어깨를 감싸거나 손을 잡으며 '괜찮아, 안전해'라는 짧은 시각적 메시지를 전달함

**LLM의 답변에 대하여 판단 하실 때 위에서 제시 된 자폐인의 프로파일과 관찰일지를 참고해주시면 감사드리겠습니다.**

원본 링크 : https://www.youtube.com/watch?v=C0rdZOhet24
""")

# Expert ID input
if 'expert_id' not in st.session_state:
    st.session_state.expert_id = st.text_input("응답자 ID를 입력해주세요.")
    if not st.session_state.expert_id:
        st.stop()

# --- Feedback loop ---
if st.session_state2.state == "feedback_loop":
    strat = st.session_state2.strategy

    st.subheader("🤖 중재 전략 피드백")
    st.write(f"**문제 상황:** {st.session_state2.situation}")
    st.write(f"**원인:** {strat.get('cause')}")
    st.write("**중재 후보:**")
    for i, intr in enumerate(strat.get('intervention', []), 1):
        st.write(f"{i}. {intr.get('strategy')} - {intr.get('purpose')}")
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    if 'loop2_index' not in st.session_state2:
        st.session_state2.loop_index = 0
        st.session_state2.generated_situations = []
        st.session_state2.generated_strategies = [st.session_state2.strategy]  # 초기 전략 포함
        st.session_state2.user_comments = []
        st.session_state2.survey_saved = False
        
    if st.session_state2.loop_index < 3:
        idx = st.session_state2.loop_index
        current_strategy = st.session_state2.generated_strategies[idx]

        previous_situation = (
            st.session_state2.situation if idx == 0
            else st.session_state2.generated_situations[idx - 1]
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
                     감각 자극, 외부 요인, 아동의 정서 반응 등을 포함해 주세요.
                     """
        new_situation = st.session_state2.llm.call_as_llm(prompt)
        st.session_state2.generated_situations.append(new_situation)

        # 2. 상황 사용자에게 제시
        st.markdown(f"### 🔄 루프 {idx+1} — 생성된 새로운 상황")
        st.markdown(new_situation)

        # 3. 사용자 comment 입력
        comment = st.text_area("현재 주어진 상황을 자유롭게 요약하여 입력해주세요", key=f"comment_{idx}")
        if st.button("다음", key=f"next_{idx}"):
            if comment.strip() == "":
                st.warning("댓글을 작성해주세요.")
                st.stop()
            st.session_state2.user_comments.append(comment)
            
            # 4. MemoryAgent가 전략 생성
            agent = st.session_state2.agent
            caregraph = st.session_state2.graph
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
                st.session_state2.generated_strategies.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            st.session_state2.loop_index += 1
            st.rerun()
            
    elif st.session_state2.loop_index >= 3 and not st.session_state2.survey_saved:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_feedbackloop.csv")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
            for i in range(3):
                situation = st.session_state2.generated_situations[i].replace("\n", " ")
                comment = st.session_state2.user_comments[i].replace("\n", " ")
                strategy = json.dumps(st.session_state2.generated_strategies[i+1], ensure_ascii=False).replace("\n", " ")
                f.write(f"{now},{expert_id},{i+1},\"{situation}\",\"{comment}\",\"{strategy}\"\n")
        st.session_state2.survey_saved = True
        st.success("3회의 루프가 완료되었고 응답이 자동 저장되었습니다. 감사합니다.")

if session_state2.survey_saved:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/1_wo_system_1.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/3_servey_system_1.py")
