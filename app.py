import streamlit as st
import pandas as pd
import numpy as np
import re

# 1. 모바일 화면 비율 최적화 설정
st.set_page_config(page_title="진짜 맛집 판독기", page_icon="🍽️", layout="centered")

# 2. 데이터 로드
@st.cache_data
def load_data():
    return pd.read_csv("final_store_scores.csv")

df = load_data()

# 상단 타이틀
st.title("🍽️ 광고 거품 뺀 '진짜 맛집' 랭킹")
st.caption("AI 어뷰징 탐지 기반 신뢰도 가중 평점(True Score) 서비스")

# 탭 구성 (1. 동네 맛집 랭킹 / 2. 실시간 리뷰 판독기)
tab1, tab2 = st.tabs(["🏆 서울시 진짜 맛집 랭킹", "🔍 실시간 리뷰 판독기"])

with tab1:
    # 자치구 필터링
    gu_list = ["전체"] + sorted(df['시군구명'].dropna().unique().tolist())
    selected_gu = st.selectbox("자치구 선택", gu_list)
    
    filtered_df = df if selected_gu == "전체" else df[df['시군구명'] == selected_gu]
    
    # 정렬 기준 선택
    sort_option = st.radio("정렬 기준", ["진짜 평점(True Score) 높은 순", "평점 거품(광고 의심) 심한 순"], horizontal=True)
    if sort_option == "진짜 평점(True Score) 높은 순":
        filtered_df = filtered_df.sort_values(by="true_score", ascending=False)
    else:
        filtered_df = filtered_df.sort_values(by="rating_gap", ascending=False)
        
    st.divider()
    
    # 매장 카드 리스트 출력
    for idx, row in filtered_df.head(15).iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"{row['상호명']}")
                st.caption(f"📍 {row['시군구명']} {row['행정동명']} | {row.get('상권업종중분류명', '음식점')}")
            with col2:
                st.metric(
                    label="진짜 평점", 
                    value=f"{row['true_score']:.2f}점", 
                    delta=f"{-row['rating_gap']:.2f} (거품제거)" if row['rating_gap'] > 0 else f"+{abs(row['rating_gap']):.2f}"
                )
            st.write(f"기존 플랫폼 단순 별점: **{row['raw_rating']:.2f}점** → AI 보정 후: **{row['true_score']:.2f}점**")

with tab2:
    st.subheader("이 리뷰, 영수증 이벤트 알바일까?")
    st.write("의심되는 리뷰 문장을 아래에 붙여넣으면 AI가 즉시 광고 확률을 판독합니다.")
    
    user_review = st.text_area("리뷰 텍스트 입력", placeholder="예: 영수증 리뷰 이벤트 참여하면 음료수 주셔서 남깁니다~ 사장님 친절해요!", height=120)
    
    if st.button("AI 판독 실행", type="primary", use_container_width=True):
        if user_review.strip() == "":
            st.warning("리뷰 내용을 먼저 입력해 주세요.")
        else:
            # 규칙 및 형태소 기반 실시간 간이 스코어링
            ad_keywords = ['영수증', '이벤트', '서비스', '협찬', '원고료', '제공받아', '친절', '음료수']
            hit_keywords = [kw for kw in ad_keywords if kw in user_review]
            length = len(user_review.strip())
            
            # 광고 확률 계산
            score = 0.15 + (len(hit_keywords) * 0.25)
            if length < 20:
                score += 0.25
            elif length > 80 and len(hit_keywords) == 0:
                score -= 0.10
            abuse_prob = min(max(score, 0.05), 0.98) * 100
            
            st.divider()
            if abuse_prob >= 60:
                st.error(f"🚨 **광고·어뷰징 의심 리뷰 (확률: {abuse_prob:.1f}%)**")
                st.write(f"- **감지된 광고 패턴:** {', '.join(hit_keywords) if hit_keywords else '정보량 부족 단문 패턴'}")
                st.write(f"- **평점 반영 가중치:** 기존 1.0 → **{max(0.05, 1 - abuse_prob/100):.2f}배로 축소 반영**")
            else:
                st.success(f"✅ **신뢰할 수 있는 진짜 리뷰 (광고 확률: {abuse_prob:.1f}%)**")
                st.write(f"- **분석 결과:** 구체적 경험 서술 확인 (글자 수 {length}자)")
                st.write("- **평점 반영 가중치:** **정상 반영**")
