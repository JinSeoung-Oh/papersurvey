from pathlib import Path
import streamlit as st
import datetime
import os
import sys
import random

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from pages.tools import _4oMiniClient

st.title("상황 1: 일상생활에서의 자폐인 Meltdown")
st.markdown(""" 영상에서의 멜트 다운 상황 : 영상이 시작되면 Ian은 창문 가까이에서 커튼을 젖히고 바깥을 바라보고 있는데, 바깥은 매우 밝습니다.
바깥을 바라보던 그는 잠시 후 눈에 띄게 불안한 상태에 빠지며, 울음을 터뜨리고 큰 소리로 외치며 강한 정서적 동요를 보입니다.
그는 “Lucifer가 나를 훔쳐가려 한다”, “비가 와야 한다”고 반복적으로 말하는데, 특히 비가 오지 않으면 캠핑을 가지 못한다고 생각하고 있으며
동시에 비가 와야 더러운 공기를 씻어낼 수 있다는 믿음을 갖고 있는 것으로 보입니다. 
Ian은 울면서 소리를 지르고, 언어적 혼란, 강박적인 반복 발화, 감정 폭발 등의 모습을 보이고 있습니다.
영상에 의하면 Ian은 감각적 자극 완하를 위하여 담요를 머리 끝까지 쓰는 것을 선호하는 것으로 보입니다.

원본 링크 : https://www.youtube.com/watch?v=C0rdZOhet24
""")

# -------------------------------
# LLM & 세션 상태 초기화
# -------------------------------
if 'llm' not in st.session_state:
    st.session_state.llm = _4oMiniClient()

# 전문가 ID 확인
if "expert_id" not in st.session_state or not st.session_state.expert_id:
    st.warning("먼저 홈에서 응답자 ID를 입력해 주세요.")
    st.stop()

# 페이지별 고유 ID(파일명 기준)
PAGE_ID = Path(__file__).stem

# 페이지 진입 시 1회만 무작위 시드 생성(세션 동안 고정) → rerun 안정, expert_id와 무관
page_seed_key = f"seed_{PAGE_ID}"
page_rng_key  = f"rng_{PAGE_ID}"
if page_seed_key not in st.session_state:
    st.session_state[page_seed_key] = int.from_bytes(os.urandom(8), "big")
    st.session_state[page_rng_key]  = random.Random(st.session_state[page_seed_key])

if 'survey1_submitted' not in st.session_state:
    st.session_state.survey1_submitted = False

st.video("https://youtu.be/GjddtdjWaj8")

if "comments_history" not in st.session_state:
    st.session_state.comments_history = []  # 전문가 중재 입력 이력

if "generated_situations" not in st.session_state:
    st.session_state.generated_situations = []  # LLM이 생성한 상황 이력

if "loop_index" not in st.session_state:
    st.session_state.loop_index = 0  # 0: 초기 중재 입력, 1~3: 상황 생성 루프

# 사용자 프로필(예시)
USER_PROFILE = {
    'sensory_profile': {'sound': 'medium', 'light': 'high'},
    'comm_prefs': {'visual': 'medium', 'verbal': 'high'},
    'stress_signals': ['aggressive behavior'],
    'preference': ['Block the light with a blanket']
}

# -------------------------------
# 프롬프트 빌더
#  - history_pairs: 오래된 → 덜 오래된 (직전 페어 제외)
#  - previous_situation / expert_action: 직전 상황 및 그에 대한 중재
# -------------------------------
def build_prompt_with_past_history(
    previous_situation: str,
    expert_action: str,          # 직전 상황에 대한 전문가 중재
    user_profile: dict,
    history_pairs: list,         # [(old_situation, its_expert_action), ...]
    cause_mode: str              # "sensory" | "nonsensory"
) -> str:
    # 과거 히스토리(전전, 전전전…)
    if history_pairs:
        hist_lines = []
        for i, (s, a) in enumerate(history_pairs, 1):
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
    
# -------------------------------
if st.session_state.loop_index == 0:
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
        st.session_state.comments_history.append(comment)  # 초기 중재 저장
        st.session_state.loop_index = 1
        st.rerun()

# -------------------------------
# 반복 상황 생성 루프 (1~3회)
# -------------------------------
elif 1 <= st.session_state.loop_index <= 3:
    idx = st.session_state.loop_index

    # 상황 생성(아직 안 했으면)
    if len(st.session_state.generated_situations) < idx:
        # 직전 상황: 없으면 초기 설명 사용
        previous_situation = (
            st.session_state.generated_situations[-1]
            if st.session_state.generated_situations
            else "초기 멜트다운: 커튼 밖의 밝은 빛 자극으로 인하여 멜트 다운을 일으킴. 소리를 지르고 울면서 불안한 모습을 보이고 있음"
        )
        # 직전 상황에 대한 전문가 중재(방금/가장 최근에 입력된 것)
        expert_action_txt = st.session_state.comments_history[-1]

        # ---- 과거 히스토리(직전 페어 제외) 구성: 오래된 → 덜 오래된 ----
        # 상황 i(0-base)에 대한 '그 상황에 대한 중재'는 comments_history[i+1]
        # 과거 페어 범위: i = 0 .. S-2
        history_pairs = []
        S = len(st.session_state.generated_situations)
        for i in range(max(0, S - 1)):
            s = st.session_state.generated_situations[i]
            if i + 1 < len(st.session_state.comments_history):
                a = st.session_state.comments_history[i + 1]
                history_pairs.append((s, a))
        # 너무 길면 오래된 것부터 N개만 유지
        MAX_PAST = 3
        history_pairs = history_pairs[:MAX_PAST]

        # ---- 감각/비감각 모드 선택(난수 또는 번갈아) ----
        cause_mode = st.session_state[page_rng_key].choice(["sensory", "nonsensory"])
        st.write(f"디버깅: 현재 모드{cause_mode}")
        # 번갈아 쓰고 싶으면 대신 아래 사용:
        # cause_mode = "sensory" if (idx % 2 == 1) else "nonsensory"

        prompt = build_prompt_with_past_history(
            previous_situation=previous_situation,
            expert_action=expert_action_txt,
            user_profile=USER_PROFILE,
            history_pairs=history_pairs,
            cause_mode=cause_mode,
        )
        st.write(f"프롬프트 디버깅: {prompt}")

        new_situation = st.session_state.llm.call_as_llm(prompt)
        st.session_state.generated_situations.append(new_situation)

    # 새 상황 표시 + 다음 중재 입력
    st.markdown(f"### 새로 생성된 상황 {idx}")
    st.markdown(st.session_state.generated_situations[idx - 1])

    with st.form(f"form_comment_{idx}"):
        new_comment = st.text_area("이 상황에 적절한 중재 방안을 입력해주세요", key=f"comment_{idx}")
        go_next = st.form_submit_button("다음")
    if go_next:
        if new_comment.strip() == "":
            st.warning("중재 방안을 입력해주세요.")
            st.stop()
        st.session_state.comments_history.append(new_comment)  # 이번 상황에 대한 중재
        st.session_state.loop_index += 1
        st.rerun()

# -------------------------------
# 완료 및 저장
# -------------------------------
elif st.session_state.loop_index > 3:
    st.success("3회의 상황 생성 및 중재 응답이 완료되었습니다. 감사합니다.")

    if not st.session_state.survey1_submitted:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expert_id = st.session_state.expert_id
        user_dir = f"responses/{expert_id}"
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, "survey1_loop.csv")

        # 파일이 없다면 헤더 추가
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("timestamp,expert_id,loop_index,situation,intervention\n")

        # 상황 + '그 상황에 대한' 중재 방안 저장
        # 저장 규칙: situation_i ↔ comments_history[i+1] (i=0부터)
        with open(filepath, "a", encoding="utf-8") as f:
            for i, situation in enumerate(st.session_state.generated_situations):
                # 해당 상황에 대한 중재가 존재하면 저장
                if (i + 1) < len(st.session_state.comments_history):
                    intervention = st.session_state.comments_history[i + 1]
                    f.write(
                        f"{now},{expert_id},{i+1},"
                        f"\"{situation.strip()}\","
                        f"\"{intervention.strip()}\"\n"
                    )

        st.session_state.survey1_submitted = True
        st.info("응답이 저장되었습니다. 감사합니다.")
        
    # 다음 페이지 이동 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/0_ProfessionalExperience.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/2_w_system_1.py")
