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
import random

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
        {
          "strategy": "Intervention 1 title",
          "purpose": "Educational purpose of intervention 1",
          "example": {
            "immediate": "Immediate action for intervention 1",
            "standard": "Standard classroom method for intervention 1"
          }
        },
        {
          "strategy": "Intervention 2 title",
          "purpose": "Educational purpose of intervention 2",
          "example": {
            "immediate": "Immediate action for intervention 2",
            "standard": "Standard classroom method for intervention 2"
          }
        }
      ]
    },
    "Self-harm behavior": {
      "cause": "Brief cause description",
      "intervention": [
        {
          "strategy": "Intervention 1 title",
          "purpose": "Educational purpose of intervention 1",
          "example": {
            "immediate": "Immediate action for intervention 1",
            "standard": "Standard classroom method for intervention 1"
          }
        },
        {
          "strategy": "Intervention 2 title",
          "purpose": "Educational purpose of intervention 2",
          "example": {
            "immediate": "Immediate action for intervention 2",
            "standard": "Standard classroom method for intervention 2"
          }
        }
      ]
    },
    "Tantrum behavior": {
      "cause": "Brief cause description",
      "intervention": [
        {
          "strategy": "Intervention 1 title",
          "purpose": "Educational purpose of intervention 1",
          "example": {
            "immediate": "Immediate action for intervention 1",
            "standard": "Standard classroom method for intervention 1"
          }
        },
        {
          "strategy": "Intervention 2 title",
          "purpose": "Educational purpose of intervention 2",
          "example": {
            "immediate": "Immediate action for intervention 2",
            "standard": "Standard classroom method for intervention 2"
          }
        }
      ]
    },
    "Ambiguous physical interaction": {
      "cause": "Brief cause description",
      "intervention": [
        {
          "strategy": "Intervention 1 title",
          "purpose": "Educational purpose of intervention 1",
          "example": {
            "immediate": "Immediate action for intervention 1",
            "standard": "Standard classroom method for intervention 1"
          }
        },
        {
          "strategy": "Intervention 2 title",
          "purpose": "Educational purpose of intervention 2",
          "example": {
            "immediate": "Immediate action for intervention 2",
            "standard": "Standard classroom method for intervention 2"
          }
        }
      ]
    }
  }
}

st.video("https://youtu.be/AaWWfjb8DjM")

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

def strategy_to_text(strat_dict: dict) -> str:
    """전략 dict를 프롬프트 삽입용 간결 텍스트로 변환"""
    if not strat_dict:
        return ""
    parts = []
    for it in strat_dict.get("intervention", []) or []:
        parts.append(
            f"- 전략: {it.get('strategy','')}\n"
            f"  - 목적: {it.get('purpose','')}\n"
            f"  - 즉시 적용: {it.get('example',{}).get('immediate','')}\n"
            f"  - 표준 상황: {it.get('example',{}).get('standard','')}\n"
        )
    return "\n".join(parts).strip()

def build_prompt_with_past_history5(
    previous_situation: str,
    expert_action: str,          # 직전 상황에 대한 전문가 중재
    user_profile: dict,
    history_pairs5: list,         # [(old_situation, its_expert_action), ...]
    cause_mode: str              # "sensory" | "nonsensory"
) -> str:
    # 과거 히스토리(전전, 전전전…)
    if history_pairs5:
        hist_lines = []
        for i, (s, a) in enumerate(history_pairs5, 1):
            hist_lines.append(f"- [과거#{i}] 상황: {s}")
            hist_lines.append(f"              해당 상황에 대한 전문가 중재: {a}")
        history_block = "\n".join(hist_lines)
    else:
        history_block = "(과거 히스토리 없음)"
    
    # 감각/비감각 모드 규칙 개선
    if cause_mode == "sensory":
        cause_rule = (
            "도전 행동의 원인은 감각적(sensory) 요인 **정확히 1종**만 선택하세요. "
            "감각적 요인에는 **시각(빛/밝기), 청각(소리/소음), 후각(냄새), 촉각(질감/온도/압력), 미각(맛), 전정감각(균형), 고유수용감각(몸의 위치감각)** 등이 포함됩니다. "
            "새로운 감각 자극을 도입할 때는 **현재 물리적 환경에서 실제 발생 가능한 것**만 선택하고, "
            "그 자극의 발생 과정이나 출처를 상황 내에서 자연스럽게 설명하세요. "
            "(예: '이때 ~소리가 들리기 시작했다', '~냄새가 퍼져왔다', '~질감이 느껴졌다' 등)"
            "- 다음 단어가 등장하면 원인은 무조건 감각(촉각)입니다: 무게, 압박, 답답, 조임, 촉감, 질감, 온기, 냉기."
        )
        transition_guide = (
            "중재로 차단/제거된 감각 자극은 재등장하지 않습니다. "
            "새로운 감각 자극이 필요한 경우, 현재 환경(실내/실외, 시간, 날씨, 주변 상황)에서 "
            "**논리적으로 발생 가능한 것**만 도입하세요. 환경과 맞지 않는 자극은 절대 사용하지 마세요."
        )
    else:
        cause_rule = (
            "도전 행동의 원인은 **비감각(nonsensory) 요인** 중 정확히 1개를 선택하세요: "
            "[중재 방법 자체에 대한 거부반응 | 신체적 피로/에너지 부족 | 인지적 혼란/이해 부족 | 루틴 변화에 대한 저항]. "
            "-**절대 금지**: 온도, 빛, 소음, 냄새, 촉감, 맛 등 물리적 감각을 원인으로 언급하거나 암시하지 마세요. "
            "-**'감정 조절 실패'는 결과이지 원인이 아닙니다** - 감각적 자극 때문에 감정조절이 어려워진다면 그것은 감각 모드입니다. "
            "- 다음 단어가 텍스트에 포함되면 비감각 원인을 선택할 수 없습니다(감각으로 간주): 무게, 압박, 답답, 조임, 촉감, 질감, 온기, 냉기. "
            "-비감각 원인이란: 감각과 무관하게 발생하는 내적/인지적/사회적/생리적 요인을 의미합니다. "
            "-새롭게 생성된 상황은 이러한 비감각적 요인이 충분히 추측 가능한 형태로 서술되어야합니다. 이유 조차 짐작 할 수 없으면 안 됩니다."
            "(예: '예상치 못한 상황 변화로 인해 혼란스러워 보였다'라면서 어떤 상황이 변화하였는지 서술하지 않는 형태는 생성하지 마세요.)"
        )
        transition_guide = (
            "비감각적 원인의 구체적 예시: "
            "- 중재 방법 거부: '담요를 쓰기 싫어하며 벗어던짐', '헤드폰을 거부하며 밀어냄' "
            "- 신체적 피로: '오랜 시간 울고 소리친 후 체력이 고갈되어', '기력 부족으로 인해' "
            "- 인지적 혼란: '상황을 이해하지 못해 더욱 혼란스러워하며', '예상과 다른 결과에 당황하며' "
            "- 루틴 변화 저항: **히스토리에서 명시된 일상 패턴이 있을 때만 사용 가능**. 주어진 컨텍스트에 루틴 정보가 없다면 이 원인은 사용 금지 "
            "**중요**: 환경적 요소(온도, 빛, 소음 등)는 배경 설명으로만 언급하고, 절대 행동의 직접적 원인으로 지목하지 마세요. "
            "**정보 날조 금지**: '평소에', '늘 하던', '예전처럼' 등 히스토리에 없는 과거 정보를 임의로 만들어내지 마세요."
        )
    
    return f"""
[과거 히스토리 (참고용)]
{history_block}

[직전 컨텍스트 (출발점)]
- 직전 상황: {previous_situation}
- 적용된 전문가 중재: {expert_action}
- 사용자 프로필: {user_profile}

[상황 생성 가이드라인]

**1. 시간적 연속성과 자연스러운 전환**
- 직전 중재 적용 직후부터 자연스럽게 이어지는 상황을 생성하세요
- **갑작스러운 상황 변화를 피하고, 이전 상황과 새로운 상황 사이의 논리적 연결고리를 제시하세요**
- 시간 경과를 명시하고 (예: "잠시 후", "10분 후", "한동안 지나자"), 변화의 원인이나 과정을 포함하세요
- 중재의 효과가 제한적이거나, 새로운 요인이 등장하거나, 시간이 지나면서 상황이 변화할 수 있습니다

**2. 논리적 일관성과 환경 맥락 (핵심!)**
- 중재로 제거/차단된 요소는 다시 등장하지 않습니다
- **물리적으로 불가능한 상황은 생성하지 마세요** 
  (예: 담요를 머리끝까지 썼는데 바깥을 바라본다, 실내인데 비가 직접 떨어진다)
- **현재 환경 맥락을 정확히 파악하고 그에 맞는 상황만 생성**하세요
  (실내/실외, 시간대, 날씨, 주변 사람, 사용 중인 도구 등)
- 과거 히스토리와 모순되지 않는 범위에서 새로운 전개를 만드세요

**3. 원인 설정 규칙 (매우 중요!)**
{cause_rule}

**4. 상황 전개 가능성 (중요 참고자료)**
{transition_guide}

**5. 서술 방식과 전개 구조**
- 순수한 관찰자 시점으로 작성 (전문가/중재/평가 언급 금지)
- 130~220자의 한 단락
- **자연스러운 전개 구조**: (중재 효과/시간 경과) → (전환 과정/변화 징조) → (새로운 상황 발생) → (개인 반응) → (구체적 도전 행동)
- **뜬금없는 전개 방지**: 안정 상태에서 갑자기 새로운 문제로 점프하지 말고, 점진적이고 논리적인 변화 과정을 포함하세요

**6. 도전 행동 필수 포함 (핵심!)**
- **반드시 도전 행동(challenging behavior)이 발생하는 상황을 생성해야 합니다**
- 도전 행동 예시: 눈에 띄는 불안이나 초조, 울음, 소리지르기, 자해, 공격성, 파괴적 행동, 반복 행동, 위험한 행동 등
- **단순히 불편함을 느끼고 합리적으로 해결하는 상황이 아님**
- 자폐 특성으로 인한 부적응적 반응이 나타나야 함
- 일반인의 건전한 문제 해결 과정이 아닌, 자폐인의 도전적 대응 방식이어야 함

**8. 정보 창조 금지 (중요!)**
- **히스토리에 없는 정보를 임의로 창조하지 마세요**
- "평소에", "늘 하던", "예전에" 등 과거 패턴을 가정하는 표현 금지
- 주어진 컨텍스트에서만 추론 가능한 내용만 사용
- **억지로 특정 원인에 맞추려고 없는 설정을 만들어내지 마세요**

**9. 최종 검토 사항**
- 생성된 상황이 감각적 원인인지 비감각적 원인인지 명확히 구분되는가?
- 원인 설정 규칙에 정확히 맞게 생성되었는가?
- 상황 전개 가능성을 참고하여 다시 한번 검토
- 철저하게 관찰자 시점으로 서술되었는가? (내면/생각 묘사 금지)
- 자폐인이라는 맥락에 맞는 상황인가?
- 도전 행동이 명확히 포함되어 있는가?

[출력 요구사항]
위 조건을 모두 만족하는 **자폐인의 새로운 도전 행동 상황 서술 1개**를 생성하세요.
""".strip()
    

if 'llm5' not in st.session_state:
    st.session_state.llm5 = _4oMiniClient()

# --- Session initialization ---
if 'graph5' not in st.session_state:
    # Initialize or load CareGraph and profile
    if PKL_FILE.exists():
        st.session_state.graph5 = load_graph(str(PKL_FILE))
    else:
        st.session_state.graph5 = CareGraph(st.session_state.llm5)
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="B123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state.graph5.add_profile(profile)

if 'agent5' not in st.session_state:
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
             'example': {'immediate': '아동이 불안한 표정을 보일 경우 즉시 조용한 장소로 안내하고, 짧은 심호흡 및 신체 접촉(선호하는 블랭킷 제공)을 통해 안정감을 제공',
                         'standard': '평소 교육 상황에서 감각 자극이 적은 공간을 마련하고, 시각적 자료 및 선호 도구(예: 블랭킷)를 준비하여 재현 가능한 환경 안정화 전략을 실시'}}
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

# (llm5 설정 아래쯤)
PAGE_ID = Path(__file__).stem
page_seed_key = f"seed_{PAGE_ID}"
page_rng_key  = f"rng_{PAGE_ID}"
if page_seed_key not in st.session_state:
    st.session_state[page_seed_key] = int.from_bytes(os.urandom(8), "big")
    st.session_state[page_rng_key]  = random.Random(st.session_state[page_seed_key])

if "initial_situation5" not in st.session_state:
    st.session_state.initial_situation5 = st.session_state.situation5
if "static_default5" not in st.session_state:
    st.session_state.static_default5 = st.session_state.initial_situation5

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

    # 2) 초기(디폴트) 피드백 영역
    default_strat = st.session_state.strategy5
    st.subheader("🤖 초기 중재 전략 피드백")
    st.write(f"**문제 상황 (초기):** {st.session_state.initial_situation5}")
    st.write(f"**원인:** {default_strat.get('cause')}")
    st.write("**중재 후보 (초기):**")
    for i, intr in enumerate(default_strat.get('intervention', []), 1):
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 구분선
    st.markdown("---")

    # 4) 루프 진행: 최대 3번
    if st.session_state.loop_index5 < 3:
        idx = st.session_state.loop_index5
        prev_situation = (
            st.session_state.static_default5 if idx == 0
            else st.session_state.generated_situations5[idx - 1]
        )
      
        # 3) 업데이트된 전략 피드백 영역
        updated_strat = st.session_state.current_strategy5
        st.subheader("🤖 업데이트된 중재 전략 피드백")
        st.write(f"**문제 상황 (업데이트):** {prev_situation}")
        st.write(f"**원인:** {updated_strat.get('cause')}")
        st.write("**중재 후보 (업데이트):**")
        for i, intr in enumerate(updated_strat.get('intervention', []), 1):
          st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
          st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")
          
        # 직전 상황에 대한 중재 텍스트(프롬프트용)
        intervention_txt = strategy_to_text(updated_strat)
      
        loop_key = f"new_situation_5_{idx}"
        user_profile = {'sensory_profile': {'sound': 'medium', 'light': 'high'}, 'comm_prefs': {'visual': 'medium', 'verbal': 'high'}, 'stress_signals': ['aggressive behavior'],'preference': ['Block the light with a blanket']}
        # 최초 진입 또는 미생성 시 새로운 상황 생성
        if loop_key not in st.session_state:
            # ---- History 구성: [디폴트 페어] + [전전~ 과거 생성 페어], 오래된→덜 오래된 (직전 제외) ----
            history_pairs5 = []

            # (a) 디폴트 페어(항상 포함)
            default_pair = (
                st.session_state.static_default5,
                strategy_to_text(st.session_state.generated_strategies5[0])  # 0번은 초기전략
            )
            history_pairs5.append(default_pair)
            # (b) 과거 생성 페어: i = 0 .. S-2 (직전 i=S-1 은 제외)
            S = len(st.session_state.generated_situations5)
            for i in range(max(0, S - 1)):
                s = st.session_state.generated_situations5[i]
                if (i + 1) < len(st.session_state.generated_strategies5):
                    a_text = strategy_to_text(st.session_state.generated_strategies5[i + 1])
                    history_pairs5.append((s, a_text))
                  
            # (c) 너무 길면 오래된 것부터 최대 N개만 유지(디폴트 포함)
            MAX_PAST = 4  # 디폴트 + 과거 3개 예시
            history_pairs5 = history_pairs5[:MAX_PAST]

            cause_mode = st.session_state[page_rng_key].choice(["sensory", "nonsensory"])

            # ---- 프롬프트 빌드(History + 직전 컨텍스트) & 호출 ----
            prompt = build_prompt_with_past_history5(
                previous_situation=prev_situation,
                expert_action=intervention_txt,
                user_profile=user_profile,
                history_pairs5=history_pairs5,
                cause_mode = cause_mode
            )
            new_sit = st.session_state.llm5.call_as_llm(prompt)

            st.session_state[loop_key] = new_sit
            st.session_state.generated_situations5.append(new_sit)
            # 주의: 화면 고정 디폴트는 static_default2로만 표시. 아래는 '현재 컨텍스트' 용도.
            st.session_state.situation5 = new_sit
      
        # 5. 새 상황 표시
        st.markdown(f"### 🔄 루프 {idx+1} — 생성된 새로운 상황")
        st.markdown(st.session_state[loop_key])

        # 6. 사용자 코멘트 입력 폼
        with st.form(key=f"loop_form_{idx}"):
            # 강조된 안내문
            st.markdown(
                "<span style='color:red; font-weight:bold;'>현재 주어진 상황을 자유롭게 요약하여 입력해주세요</span>",
                unsafe_allow_html=True
            )
            comment = st.text_area("", key=f"comment_{idx}", height=150)
            submitted = st.form_submit_button("다음")

        if submitted:
            if not comment.strip():
                st.warning("댓글을 작성해주세요.")
                st.stop()
            st.session_state.user_comments5.append(comment)

            # 7. MemoryAgent 전략 생성
            agent = st.session_state.agent5
            caregraph = st.session_state.graph5
            user_id = "B123"
            situation = st.session_state[loop_key]
            sid, similar_events = caregraph.find_similar_events(user_id, situation)

            if sid is not None and similar_events:
                formatted_events = "\n".join([
                    f"{i+1}. 원인: {e['cause']}, 전략: {e['strategy']}, 목적: {e['purpose']}"
                    for i, e in enumerate(similar_events)
                ])
                response = agent.graph_ask(user_id, comment, formatted_events, user_profile, outformat)
            else:
                failed_events = updated_strat.get('intervention', [])
                response = agent.alt_ask(
                    user_id,
                    comment,
                    failed_event=failed_events,
                    user_profile=user_profile,
                    situation=situation,
                    outformat = outformat
                )

            # 8. JSON repair & 파싱
            repaired = repair_json(response)
            st.write(repaired)
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
                st.write(interventions)
                structured = {"cause": cause, "intervention": interventions}
                st.session_state.current_strategy5 = structured
                st.session_state.generated_strategies5.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            # 10. 루프 인덱스 증가 및 rerun
            st.session_state.loop_index5 += 1
            st.rerun()
            
    elif st.session_state.loop_index5 >= 3:
      st.subheader("✅ 최종 루프(3/3) 결과")
      last_sit = st.session_state.generated_situations5[-1] if st.session_state.generated_situations5 else ""
      last_strat = st.session_state.generated_strategies5[-1] if st.session_state.generated_strategies5 else {}

      st.markdown("### 🔎 최종 생성 상황")
      st.markdown(last_sit or "_생성된 상황이 없습니다._")

      st.markdown("### 🧩 최종 전략 요약")
      st.write(f"**원인:** {last_strat.get('cause', '')}")
      for i, intr in enumerate(last_strat.get('intervention') or [], 1):
          st.write(f"- 전략 {i}: {intr.get('strategy','')}")
          ex = intr.get('example') or {}
          st.write(f"  - 목적: {intr.get('purpose','')}")
          st.write(f"  - 즉시 적용: {ex.get('immediate','')}")
          st.write(f"  - 표준 상황: {ex.get('standard','')}")

      # 자동 저장: 표시 직후 1회만 실행
      if not st.session_state.survey_saved5:
          now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          expert_id = st.session_state.expert_id
          user_dir = f"responses/{expert_id}"
          os.makedirs(user_dir, exist_ok=True)
          filepath = os.path.join(user_dir, "survey2_feedbackloop.csv")

          n = min(3, len(st.session_state.generated_situations5), len(st.session_state.user_comments5))
          with open(filepath, "w", encoding="utf-8") as f:
              f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
              for i in range(n):
                  situation = (st.session_state.generated_situations5[i] or "").replace("\n", " ")
                  comment = (st.session_state.user_comments5[i] or "").replace("\n", " ")
                  strat_idx = min(i + 1, len(st.session_state.generated_strategies5) - 1)  # 0은 초기전략
                  strategy = json.dumps(st.session_state.generated_strategies5[strat_idx], ensure_ascii=False).replace("\n", " ")
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
