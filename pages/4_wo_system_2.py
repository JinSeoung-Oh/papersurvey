from pathlib import Path
import streamlit as st
import datetime
import os
import sys
import random

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

# -------------------------------
# LLM & 세션 상태 초기화 (페이지 전용 키)
# -------------------------------
if 'llm4' not in st.session_state:
    st.session_state.llm4 = _4oMiniClient()

# 전문가 ID 확인 (공통)
if "expert_id" not in st.session_state or not st.session_state.expert_id:
    st.warning("먼저 홈에서 응답자 ID를 입력해 주세요.")
    st.stop()

PAGE_ID = Path(__file__).stem

# 페이지 진입 시 1회만 무작위 시드 생성(세션 동안 고정) → rerun 안정, expert_id와 무관
page_seed_key = f"seed_{PAGE_ID}"
page_rng_key  = f"rng_{PAGE_ID}"
if page_seed_key not in st.session_state:
    st.session_state[page_seed_key] = int.from_bytes(os.urandom(8), "big")
    st.session_state[page_rng_key]  = random.Random(st.session_state[page_seed_key])

if 'survey_submitted4' not in st.session_state:
    st.session_state.survey_submitted4 = False

st.video("https://youtu.be/AaWWfjb8DjM")

if "comments_history4" not in st.session_state:
    st.session_state.comments_history4 = []  # 전문가 중재 입력 이력(페이지2)

if "generated_situations4" not in st.session_state:
    st.session_state.generated_situations4 = []  # LLM 생성 상황 이력(페이지2)

if "loop_index4" not in st.session_state:
    st.session_state.loop_index4 = 0  # 0: 초기 중재 입력, 1~3: 생성 루프

# 사용자 프로필(예시)
USER_PROFILE_4 = {
    'sensory_profile': {'sound': 'medium', 'light': 'high'},
    'comm_prefs': {'visual': 'medium', 'verbal': 'high'},
    'stress_signals': ['aggressive behavior'],
    'preference': ['Block the light with a blanket']
}

# -------------------------------
# 프롬프트 빌더 (히스토리/직전 분리, 모드 고정)
#  - history_pairs4: 오래된 → 덜 오래된, "직전 페어 제외"
#  - previous_situation / expert_action: 직전 상황과 그에 대한 중재
# -------------------------------
def build_prompt_with_past_history4(
    previous_situation: str,
    expert_action: str,          # 직전 상황에 대한 전문가 중재
    user_profile: dict,
    history_pairs4: list,         # [(old_situation, its_expert_action), ...]
    cause_mode: str              # "sensory" | "nonsensory"
) -> str:
    # 과거 히스토리(전전, 전전전…)
    if history_pairs4:
        hist_lines = []
        for i, (s, a) in enumerate(history_pairs4, 1):
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

# -------------------------------
# 초기 질문(중재 입력)
# -------------------------------
if st.session_state.loop_index4 == 0:
    with st.form("initial_form"):
        # 강조된 안내문 (빨간색 + 굵게)
        st.markdown(
            "<span style='color:red; font-weight:bold;'>주어진 상황에 대하여 가장 적절한 것으로 보이는 중재 방안을 입력해주세요</span>",
            unsafe_allow_html=True
        )
        comment = st.text_area("", key="initial_comment", height=150)
        go = st.form_submit_button("다음")
    if go:
        if comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state.comments_history4.append(comment)  # 초기 중재 저장
        st.session_state.loop_index4 = 1
        st.rerun()

# -------------------------------
# 반복 상황 생성 루프 (1~3회)
# -------------------------------
elif 1 <= st.session_state.loop_index4 <= 3:
    idx = st.session_state.loop_index4

    # 상황 생성(아직 안 했으면)
    if len(st.session_state.generated_situations4) < idx:
        previous_situation = (
            st.session_state.generated_situations4[-1]
            if st.session_state.generated_situations4
            else "초기 멜트다운: 등교길에 우연히 만난 토끼에 매우 놀란 모습을 보임. 울면서 불안한 모습을 보이고 있음"
        )
        # “직전 상황에 대한” 전문가 중재(가장 최근 입력)
        expert_action_txt = st.session_state.comments_history4[-1]

        # ---- 과거 히스토리(전전~) 구성: 오래된 → 덜 오래된, 직전 페어 제외 ----
        history_pairs4 = []
        S = len(st.session_state.generated_situations4)
        # 상황 i에 대한 중재는 comments_history4[i+1]
        # 과거 범위: i = 0 .. S-2
        for i in range(max(0, S - 1)):
            s = st.session_state.generated_situations4[i]
            if i + 1 < len(st.session_state.comments_history4):
                a = st.session_state.comments_history4[i + 1]
                history_pairs4.append((s, a))
        # 너무 길면 오래된 것부터 최대 N개만 유지
        MAX_PAST = 3
        history_pairs4 = history_pairs4[:MAX_PAST]

        # ---- 감각/비감각 모드 선택(난수 또는 번갈아) ----
        cause_mode = st.session_state[page_rng_key].choice(["sensory", "nonsensory"])
        # 번갈아 사용하고 싶다면:
        # cause_mode = "sensory" if (idx % 2 == 1) else "nonsensory"

        prompt = build_prompt_with_past_history4(
            previous_situation=previous_situation,
            expert_action=expert_action_txt,
            user_profile=USER_PROFILE_4,
            history_pairs4=history_pairs4,
            cause_mode=cause_mode,
        )

        new_situation = st.session_state.llm4.call_as_llm(prompt)
        st.session_state.generated_situations4.append(new_situation)

    # 새 상황 표시 + 다음 중재 입력
    st.markdown(f"### 새로 생성된 상황 {idx}")
    st.markdown(st.session_state.generated_situations4[idx - 1])

    with st.form(f"form_comment4_{idx}"):
        new_comment = st.text_area("이 상황에 적절한 중재 방안을 입력해주세요", key=f"comment4_{idx}")
        go_next = st.form_submit_button("다음")
    if go_next:
        if new_comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state.comments_history4.append(new_comment)  # 이번 상황에 대한 중재
        st.session_state.loop_index4 += 1
        st.rerun()

# -------------------------------
# 완료 및 저장
# -------------------------------
elif st.session_state.loop_index4 > 3:
    st.success("3회의 상황 생성 및 중재 응답이 완료되었습니다. 감사합니다.")

    if not st.session_state.survey_submitted4:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey2_loop.csv")

        # 파일이 없다면 헤더 추가
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("timestamp,expert_id,loop_index,situation,intervention\n")

        # 상황 + '그 상황에 대한' 중재 저장
        # 규칙: situation_i ↔ comments_history4[i+1]
        with open(filepath, "a", encoding="utf-8") as f:
            for i, situation in enumerate(st.session_state.generated_situations4):
                if (i + 1) < len(st.session_state.comments_history4):
                    intervention = st.session_state.comments_history4[i + 1]
                    f.write(
                        f"{now},{expert_id},{i+1},"
                        f"\"{situation.strip()}\","
                        f"\"{intervention.strip()}\"\n"
                    )

        st.session_state.survey_submitted4 = True
        st.info("응답이 저장되었습니다. 감사합니다.")

    # 다음 페이지 이동 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/3_servey_system_1.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/5_w_system_2.py")
