import streamlit as st
import json
import datetime
import joblib
import os
from json_repair import repair_json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Expert ID 입력 (한 번만 입력받음)
if 'expert_id' not in st.session_state:
    st.session_state.expert_id = st.text_input("응답자 ID를 입력해주세요.")
    if not st.session_state.expert_id:
        st.stop()

# 설문 제출 여부 상태 초기화
if 'survey_submitted3' not in st.session_state:
    st.session_state.survey_submitted3 = False

# --- 공통 0~5 리커트 라디오 ---
LIKERT6 = [
    ("0", "0"),
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
    ("5", "5"),
]
def likert6_radio(key: str, label: str, help_text: str = "0=전혀 아니다, 5=매우 그렇다"):
    st.caption(help_text)
    choice = st.radio(label, [t[1] for t in LIKERT6], key=key, horizontal=True)
    return int(next(v for v, t in LIKERT6 if t == choice))

# 바로 설문 시작
st.subheader("📋 설문조사: 시스템 사용 vs 비사용 비교 평가")
st.markdown("시스템을 사용한 경험과 사용하지 않은 경우를 비교하여 다음 문항에 응답해 주세요. (0=전혀 아니다, 5=매우 그렇다)")

# 비교 기반 설문 항목 (0~5 라디오)
q1  = likert6_radio("q1",  "1. 시스템 없이 직접 구성했을 때보다, 시스템 사용 시 개별 특성이 더 잘 반영된 전략을 도출할 수 있었다.")
q2  = likert6_radio("q2",  "2. 메모리(과거 상황) 기록을 참고하지 않았을 때보다, 이를 활용한 시스템의 전략 제안이 더 효과적이었다.")
q3  = likert6_radio("q3",  "3. 시스템 없이 반복 수정했을 때보다, 시스템을 통한 피드백 반영 과정이 전략 개선에 더 도움이 되었다.")
q4  = likert6_radio("q4",  "4. 시스템 없이 직접 구성·수정하는 흐름에 비해, 시스템의 (전략 제시 → 피드백 → 반복) 흐름이 더 직관적이었다.")
q5  = likert6_radio("q5",  "5. 시스템 없이 구성한 전략보다, 시스템을 활용한 전략이 문제 해결에 더 기여했다.")
q6  = likert6_radio("q6",  "6. 시스템 없이 구성한 전략보다, 시스템 생성 전략이 교실/상담/가정에 적용하기 더 적합했다.")
q7  = likert6_radio("q7",  "7. 시스템을 사용한 경우가, 시스템 없이 전략을 직접 수립했을 때보다 전반적으로 더 효과적이었다.")
q8  = likert6_radio("q8",  "8. 시스템을 사용한 경우가, 전략 구성 과정에서 더 수월했다.")

# q9: 양극값 대신 명확한 비교 효용 문장으로 변경 (여전히 0~5 리커트 유지)
q9  = likert6_radio("q9",  "9. 시스템 없이 구성했을 때보다, 시스템 사용 시 전반적으로 더 우수한 전략을 얻었다.")

q10 = likert6_radio("q10", "10. 시스템 없이 구성했을 때보다, 시스템 사용 후 전략 결정을 내리는 데 더 자신감이 생겼다.")
q11 = likert6_radio("q11", "11. 시스템 없이 구성했을 때보다, 시스템 사용 시 중재 과정을 더 잘 통제하고 있다고 느꼈다.")
q12 = st.text_area("12. 두 방식(직접 전략 구성 vs. 시스템 활용)을 비교하며 느낀 점이나 개선 제안이 있다면 자유롭게 적어주세요", key="q12")

# 제출 버튼
if st.button("설문 제출"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expert_id = st.session_state.expert_id
    user_dir = PROJECT_ROOT / "responses" / expert_id
    user_dir.mkdir(parents=True, exist_ok=True)
    filepath = user_dir / "caregraph_evaluation_comparative.csv"

    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(
                "timestamp,expert_id,"
                "profile_reflection,"
                "memory_helpfulness,"
                "feedback_improvement,"
                "workflow_intuitiveness,"
                "problem_contribution,"
                "real_world_applicability,"
                "overall_effectiveness,"
                "ease_of_use,"
                "preferred_method,"
                "confidence_gain,"
                "sense_of_control,"
                "additional_comments\n"
            )

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(
            f"{now},{expert_id},"
            f"{q1},{q2},{q3},{q4},{q5},{q6},{q7},{q8},{q9},{q10},{q11},\"{q12}\"\n"
        )

    st.session_state.survey_submitted3 = True
    st.success("응답이 저장되었습니다. 감사합니다!")

# 제출 후 페이지 이동 버튼
if st.session_state.survey_submitted3:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/2_w_system_1.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/4_wo_system_2.py")

