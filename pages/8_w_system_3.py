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

st.video("https://youtube.com/shorts/uDWzTxF8qeY")

# --- Helper functions ---
def load_graph(path: str) -> CareGraph:
    graph = joblib.load(path)
    graph.llm = _4oMiniClient()
    return graph

if 'llm8' not in st.session_state:
    st.session_state.llm8 = _4oMiniClient()

# --- Session initialization ---
if 'graph8' not in st.session_state:
    # Initialize or load CareGraph and profile
    if PKL_FILE.exists():
        st.session_state.graph8 = load_graph(str(PKL_FILE))
    else:
        st.session_state.graph8 = CareGraph(st.session_state.llm8)
        # 관리자 정의 초기 사용자 프로필
        profile = UserProfile(
            user_id="C123",
            sensory_profile={'sound':'medium','light':'very high'},
            communication_preferences={"visual": "midium", "verbal": "hight"},
            stress_signals=['aggressive behavior'],
            preference = ['Blocking light through a blanket']
            )
        st.session_state.graph8.add_profile(profile)
      
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

def build_prompt_with_past_history8(
    previous_situation: str,
    expert_action: str,          # 직전 상황에 대한 전문가 중재
    user_profile: dict,
    history_pairs8: list,         # [(old_situation, its_expert_action), ...]
    cause_mode: str              # "sensory" | "nonsensory"
) -> str:
    # 과거 히스토리(전전, 전전전…)
    if history_pairs8:
        hist_lines = []
        for i, (s, a) in enumerate(history_pairs8, 1):
            hist_lines.append(f"- [과거#{i}] 상황: {s}")
            hist_lines.append(f"              해당 상황에 대한 전문가 중재: {a}")
        history_block = "\n".join(hist_lines)
    else:
        history_block = "(과거 히스토리 없음)"

    # 감각/비감각 모드 규칙
    if cause_mode == "sensory":
        cause_rule = (
            "도전 행동의 원인은 감각적(sensory) 요인 **정확히 1종**만 선택하세요."
            " (다중 감각 병기 금지)"
        )
    else:
        # ★ 강화된 비감각 규칙: '원인 프레이밍'을 비감각 6종 중 하나로 고정 + 감각 인과 서술 금지
        cause_rule = (
            "도전 행동의 **원인 프레이밍을 비감각(nonsensory) 요인 6종 중 정확히 1개로 고정**하세요 "
            "[communication | routine/transition | physiological/fatigue | "
            "emotional dysregulation | social misunderstanding | learned behavior]. "
            "원인 문장에는 **감각을 인과로 두는 표현을 절대 사용하지 마세요** "
            "(밝음/소음/냄새/촉감/온도/진동 등 물리적 자극을 원인으로 지목하거나, "
            "‘감각/자극/과부하’ 같은 단어로 원인을 정의하는 서술 금지). "
            "불가피하게 환경 맥락이 필요한 경우에도 **감각을 원인으로 명시하지 말고**, "
            "의사소통 오해, 절차/전환 혼란, 피로 누적, 감정 조절 실패, 사회적 오해, 학습된 반응 중 하나로 "
            "행동 발생의 논리적 연결을 구성하세요. **선택한 1개 범주가 문맥상 분명히 드러나게** 하되, "
            "범주 이름 자체를 노출할 필요는 없습니다."
        )

    return f"""
[과거 히스토리(오래된 → 덜 오래된)]
{history_block}

[직전 컨텍스트(가장 최근)]
- 직전 상황(관찰자 시점): {previous_situation}
- 해당 상황에 대한 전문가 중재(정확히 인용): {expert_action}
- 사용자 프로필: {user_profile}

[사용 규칙]
- '과거 히스토리'는 중복·반복을 피하기 위한 참고 자료입니다. 패턴을 복제하지 말고 **겹치지 않는 새로운 전개**를 선택하세요.
- '직전 컨텍스트'는 이번 생성의 **직접 출발점**입니다. 반드시 직전 중재 이후로 자연스럽게 이어지게 하세요.
- **비감각 모드에서는 외부 물리적 자극을 원인으로 설정하거나 감각 용어로 원인을 정의하는 서술을 금지**합니다.

[일관성 힌트]
- 직전 중재로 **제거/차단된 자극은 재등장 금지**(예: 커튼으로 빛 차단 → '빛' 서술 금지).
- 감각 원인을 고를 경우 **감각 1종만** 사용.
- '과거 히스토리'에서 얻을 수 있는 정보가 아닌 정보는 사용금지

[생성 규칙]
1) 새 상황은 '직전 컨텍스트' 이후 자연스럽게 이어집니다(완화 실패/거부/부작용 가능).
2) {cause_rule}
3) 관찰자 시점, 전문가/중재/조언/평가 직접 언급 금지.
4) 130~220자, 한 단락.
5) 흐름: (중재 이후) → 인지/환경 변화 → 정서 변화 → 행동(관찰).
6) '과거 히스토리'와 '직전 컨텍스트'에서 얻을 수 있는 정보를 최대한으로 활용하여 '직전 컨텍스트'에서 바로 연속된 상황으로 생성

[출력]
- 위 조건을 만족하는 **상황 서술 문단 1개**만 출력.
""".strip()
  
if 'agent8' not in st.session_state:
    st.session_state.agent8 = MemoryAgent(st.session_state.llm8, st.session_state.graph8)

# 페이지별 고유 ID(파일명 기준)
PAGE_ID = Path(__file__).stem

# 페이지 진입 시 1회만 무작위 시드 생성(세션 동안 고정) → rerun 안정, expert_id와 무관
page_seed_key = f"seed_{PAGE_ID}"
page_rng_key  = f"rng_{PAGE_ID}"
if page_seed_key not in st.session_state:
    st.session_state[page_seed_key] = int.from_bytes(os.urandom(8), "big")
    st.session_state[page_rng_key]  = random.Random(st.session_state[page_seed_key])
    
# --- Page‐specific state (state2) initialization ---
if 'state8' not in st.session_state:
    st.session_state.state8 = "feedback_loop"
    st.session_state.situation8 = (
        "패밀리 레스토랑에서 자폐 아동이 피로와 배고픔으로 인해 멜트다운을 일으키며 메뉴판을 빼앗으려다 통제가 되지 않자 공격적인 행동을 보입니다."
    )
    st.session_state.strategy8 = {
        'cause': '소음 등 감각 과부하와 피로, 배고픔 등의 신체적 불편감이 누적되어, 아동이 자신을 표현하는 방법으로 소리 지르며 요구하는 행동으로 나타남.',
        'intervention': [
            {'strategy': '감각 조절 및 선호 전략 제공',
             'purpose': '아동이 과도한 자극을 받았을 때 선호하는 Worm hug를 통해 신체적 안정감을 취하도록 돕고, 감각 과부하를 완화하기 위함',
             'example': {'immediate': '당장 아동에게 Worm hug를 제공하여 신체 접촉을 통한 안정감을 빠르게 제공한다',
                         'standard': '일상적으로 감각 통합 치료 세션에서 Worm hug와 같은 선호 전략을 연습시킴으로써, 식당 등 외부자극이 강한 환경에서도 자체 조절능력을 기를 수 있도록 돕는다'}}
        ]
    }
    st.session_state.history8 = []
    st.session_state.loop_count8 = 0

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

# ===== 디폴트(화면 고정) 보존: 최초 1회만 설정 =====
if "initial_situation8" not in st.session_state:
    st.session_state.initial_situation8 = st.session_state.situation8
if "static_default28" not in st.session_state:
    st.session_state.static_default8 = st.session_state.initial_situation8  # 화면 고정 디폴트(절대 불변)

# --- Feedback loop ---
if st.session_state.state8 == "feedback_loop":
    # 1) 초기화: loop_index, 전략 상태, 초기 상황 저장
    if 'loop_index8' not in st.session_state:
        st.session_state.loop_index8 = 0
        st.session_state.generated_situations8 = []
        st.session_state.generated_strategies8 = [st.session_state.strategy8]
        st.session_state.current_strategy8 = st.session_state.strategy8
        st.session_state.user_comments8 = []
        st.session_state.survey_saved8 = False

    # 2) 초기(디폴트) 피드백 영역
    default_strat = st.session_state.strategy8
    st.subheader("🤖 초기 중재 전략 피드백")
    st.write(f"**문제 상황 (초기):** {st.session_state.initial_situation8}")
    st.write(f"**원인:** {default_strat.get('cause')}")
    st.write("**중재 후보 (초기):**")
    for i, intr in enumerate(default_strat.get('intervention', []), 1):
        st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
        st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

    # 구분선
    st.markdown("---")

    # 4) 루프 진행: 최대 3번
    if st.session_state.loop_index8 < 3:
        idx = st.session_state.loop_index8
        prev_situation = (
            st.session_state.static_default8 if idx == 0
            else st.session_state.generated_situations8[idx - 1]
        )
      
        # 3) 업데이트된 전략 피드백 영역
        updated_strat = st.session_state.current_strategy8
        st.subheader("🤖 업데이트된 중재 전략 피드백")
        st.write(f"**문제 상황 (업데이트):** {prev_situation}")
        st.write(f"**원인:** {updated_strat.get('cause')}")
        st.write("**중재 후보 (업데이트):**")
        for i, intr in enumerate(updated_strat.get('intervention', []), 1):
          st.write(f"   - 즉시 적용: {intr.get('example', {}).get('immediate')}")
          st.write(f"   - 표준 상황: {intr.get('example', {}).get('standard')}")

        # 직전 상황에 대한 중재 텍스트(프롬프트용)
        intervention_txt = strategy_to_text(updated_strat)

        loop_key = f"new_situation_8_{idx}"
        user_profile = {'sensory_profile': {'sound': 'high', 'light': 'high'},'comm_prefs': {'visual': 'low', 'verbal': 'medium'},'stress_signals': ['aggressive behavior'],'preference': ['Worm hug']}
      
        # 최초 진입 또는 미생성 시 새로운 상황 생성
        if loop_key not in st.session_state:
            # ---- History 구성: [디폴트 페어] + [전전~ 과거 생성 페어], 오래된→덜 오래된 (직전 제외) ----
            history_pairs8 = []

            # (a) 디폴트 페어(항상 포함)
            default_pair = (
                st.session_state.static_default8,
                strategy_to_text(st.session_state.generated_strategies8[0])  # 0번은 초기전략
            )

            history_pairs8.append(default_pair)
          
            # (b) 과거 생성 페어: i = 0 .. S-2 (직전 i=S-1 은 제외)
            S = len(st.session_state.generated_situations8)
            for i in range(max(0, S - 1)):
                s = st.session_state.generated_situations8[i]
                if (i + 1) < len(st.session_state.generated_strategies8):
                    a_text = strategy_to_text(st.session_state.generated_strategies8[i + 1])
                    history_pairs8.append((s, a_text))
                  
            # (c) 너무 길면 오래된 것부터 최대 N개만 유지(디폴트 포함)
            MAX_PAST = 4  # 디폴트 + 과거 3개 예시
            history_pairs8 = history_pairs2[:MAX_PAST]
          
            cause_mode = st.session_state[page_rng_key].choice(["sensory", "nonsensory"])
          
            # ---- 프롬프트 빌드(History + 직전 컨텍스트) & 호출 ----
            prompt = build_prompt_with_past_history8(
                previous_situation=prev_situation,
                expert_action=intervention_txt,
                user_profile=user_profile,
                history_pairs2=history_pairs8,
                cause_mode = cause_mode
            )
            new_sit = st.session_state.llm8.call_as_llm(prompt)
          
            st.session_state[loop_key] = new_sit
            st.session_state.generated_situations8.append(new_sit)
            # 주의: 화면 고정 디폴트는 static_default2로만 표시. 아래는 '현재 컨텍스트' 용도.
            st.session_state.situation8 = new_sit

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
            st.session_state.user_comments8.append(comment)

            # 7. MemoryAgent 전략 생성
            agent = st.session_state.agent8
            caregraph = st.session_state.graph8
            user_id = "C123"
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
                st.session_state.current_strategy8 = structured
                st.session_state.generated_strategies8.append(structured)
            except Exception as e:
                st.error(f"⚠️ 중재 전략 구조 파싱 오류: {e}")
                st.stop()

            # 10. 루프 인덱스 증가 및 rerun
            st.session_state.loop_index8 += 1
            st.rerun()
            
    elif st.session_state.loop_index8 >= 3:
      st.subheader("✅ 최종 루프(3/3) 결과")
      last_sit = st.session_state.generated_situations8[-1] if st.session_state.generated_situations8 else ""
      last_strat = st.session_state.generated_strategies8[-1] if st.session_state.generated_strategies8 else {}

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
      if not st.session_state.survey_saved8:
          now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          expert_id = st.session_state.expert_id
          user_dir = f"responses/{expert_id}"
          os.makedirs(user_dir, exist_ok=True)
          filepath = os.path.join(user_dir, "survey1_feedbackloop.csv")

          n = min(3, len(st.session_state.generated_situations8), len(st.session_state.user_comments8))
          with open(filepath, "w", encoding="utf-8") as f:
              f.write("timestamp,expert_id,loop,situation,comment,strategy\n")
              for i in range(n):
                  situation = (st.session_state.generated_situations8[i] or "").replace("\n", " ")
                  comment = (st.session_state.user_comments8[i] or "").replace("\n", " ")
                  strat_idx = min(i + 1, len(st.session_state.generated_strategies8) - 1)  # 0은 초기전략
                  strategy = json.dumps(st.session_state.generated_strategies8[strat_idx], ensure_ascii=False).replace("\n", " ")
                  f.write(f"{now},{expert_id},{i+1},\"{situation}\",\"{comment}\",\"{strategy}\"\n")

          st.session_state.survey_saved8 = True
          st.success("3회의 루프가 완료되었고 응답이 자동 저장되었습니다. 감사합니다.")
          
if st.session_state.survey_saved8:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/7_wo_system_3.py")       # pages/home.py (확장자 제외)
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/9_servey_system_3.py")
