import streamlit as st
import json
import datetime
import joblib
import os
from json_repair import repair_json
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Expert ID 입력 (한 번만 입력받음)
if 'expert_id' not in st.session_state:
    st.session_state.expert_id = st.text_input("응답자 ID를 입력해주세요.")
    if not st.session_state.expert_id:
        st.stop()

if 'initialized2' not in st.session_state:
    for k in list(st.session_state.keys()):
        if k != "expert_id":
            del st.session_state[k]
    st.session_state.initialized2 = True

# 설문 제출 여부 상태 초기화
if 'survey_submitted' not in st.session_state:
    st.session_state.survey_submitted = False

# 바로 설문 시작
st.subheader("📋 설문조사: 시스템 사용 vs 비사용 비교 평가")
st.markdown("시스템을 사용한 경험과 사용하지 않은 경우를 비교하여 다음 문항에 응답해 주세요.")

# 비교 기반 설문 항목
q1 = st.slider("1. 자폐인의 개별 특성(감각/소통/스트레스 신호 등)이 반영된 전략을 시스템 없이 직접 구성했을 때보다, 시스템을 사용할 때 더 잘 도출할 수 있었다고 느끼셨습니까?", 0, 5, key="q1")
q2 = st.slider("2. 과거 상황(메모리) 기록을 참고하지 않고 전략을 구성했을 때보다, 시스템이 이를 활용한 전략 제안이 더 효과적이었다고 느끼셨습니까?", 0, 5, key="q2")
q3 = st.slider("3. 시스템 없이 반복적으로 전략을 수정했을 때보다, 시스템을 통해 피드백을 반영해가는 과정이 전략 개선에 더 도움이 되었다고 느끼셨습니까?", 0, 5, key="q3")
q4 = st.slider("4. 시스템 없이 전략을 직접 구성하고 수정하는 흐름에 비해, 시스템의 (전략 제시 → 피드백 → 반복) 흐름이 더 직관적이었다고 느끼셨습니까?", 0, 5, key="q4")
q5 = st.slider("5. 시스템 없이 문제 상황에 대해 전략을 구성했을 때보다, 시스템을 활용한 전략이 문제 해결에 더 기여했다고 느끼셨습니까?", 0, 5, key="q5")
q6 = st.slider("6. 시스템 없이 구성한 전략보다, 시스템을 통해 생성된 전략이 실제 교실/상담/가정 환경에 적용하기에 더 적합하다고 느끼셨습니까?", 0, 5, key="q6")
q7 = st.slider("7. 시스템을 사용한 경우가 시스템 없이 전략을 직접 수립했을 때보다 더 효과적이었다고 느끼셨습니까?", 0, 5, key="q7")
q8 = st.slider("8. 시스템을 사용한 경우가 전략 구성 과정에서 더 수월했다고 느끼셨습니까?", 0, 5, key="q8")
q9 = st.slider("9. 두 방식 중 어느 쪽이 더 바람직하다고 느끼셨습니까? (0=직접 작성이 더 나음, 5=시스템 사용이 더 나음)", 0, 5, key="q9")
q10 = st.slider("10. 시스템을 사용한 뒤 자폐인 중재 전략을 결정할 때 더 자신감이 생겼다고 느끼셨습니까?", 0, 5, key="q10")
q11 = st.slider("11. 시스템과 함께 전략을 구성할 때 내가 중재 과정을 더 잘 통제하고 있다고 느끼셨습니까?", 0, 5, key="q11")
q12 = st.text_area("12. 두 방식(직접 전략 구성 vs. 시스템 활용 전략 구성)을 비교하며 느낀 점이나 개선 제안이 있다면 자유롭게 적어주세요", key="q12")

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

    st.session_state.survey_submitted = True
    st.success("응답이 저장되었습니다. 감사합니다!")

# 제출 후 페이지 이동 버튼
if st.session_state.survey_submitted:
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("◀ 이전 페이지"):
            st.switch_page("pages/2_w_system_1.py")
    with col2:
        if st.button("다음 페이지 ▶"):
            st.switch_page("pages/4_wo_system_2.py")

