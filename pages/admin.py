# 관리자.py
import os
import streamlit as st
import pandas as pd

# ——— 관리자 인증 ———
st.title("관리자 모드: 응답 파일 확인 및 다운로드")

admin_pw = st.text_input("관리자 비밀번호", type="password")
if admin_pw != st.secrets["ADMIN_PASSWORD"]:
    st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# ——— 파일 시스템 확인 ———
st.subheader("📂 responses 폴더 구조")
if not os.path.exists("responses"):
    st.warning("응답 폴더가 없습니다. 아직 저장된 응답이 없습니다.")
    st.stop()

# 트리 구조 출력
for root, dirs, files in os.walk("responses"):
    indent = root.count(os.sep)
    st.write(" " * (indent*2) + os.path.basename(root) + "/")
    for f in files:
        st.write(" " * ((indent+1)*2) + f)

# ——— 파일 선택 & 다운로드 ———
st.subheader("📥 CSV 다운로드")
user_ids = [d for d in os.listdir("responses") if os.path.isdir(os.path.join("responses", d))]
choice = st.selectbox("사용자 ID 선택", user_ids)

# 해당 디렉터리에서 CSV 파일 목록
csv_dir = os.path.join("responses", choice)
csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
file_choice = st.selectbox("다운로드할 파일 선택", csv_files)

file_path = os.path.join(csv_dir, file_choice)
df = pd.read_csv(file_path, header=None)
st.write(f"### `{choice}/{file_choice}` 미리보기")
st.dataframe(df, use_container_width=True)

with open(file_path, "rb") as f:
    st.download_button(
        "CSV 파일 다운로드",
        data=f,
        file_name=file_choice,
        mime="text/csv"
    )
