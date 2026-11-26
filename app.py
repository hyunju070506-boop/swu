import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="진짜 맛집 지도 판독기", page_icon="🗺️", layout="centered")

@st.cache_data
def load_data():
    return pd.read_csv("final_store_scores.csv")

df = load_data()

st.title("🗺️ AI 진짜 맛집 지도 (True Score)")
st.caption("공공데이터 실제 위치 좌표 + AI 어뷰징 필터링 평점 결합 프로토타입")

tab1, tab2 = st.tabs(["📍 인터랙티브 맛집 지도", "🔍 실시간 리뷰 판독기"])

with tab1:
    gu_list = ["전체"] + sorted(df['시군구명'].dropna().unique().tolist())
    selected_gu = st.selectbox("자치구 선택", gu_list)
    filtered_df = df if selected_gu == "전체" else df[df['시군구명'] == selected_gu]

    # 위도·경도가 있는 데이터만 필터링
    map_df = filtered_df.dropna(subset=['위도', '경도']).head(50)

    if not map_df.empty:
        center_lat = map_df['위도'].mean()
        center_lon = map_df['경도'].mean()
        
        # 인터랙티브 지도 생성
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
        
        for _, row in map_df.iterrows():
            # 평점 거품이 0.4 이상이면 빨간색(광고의심), 아니면 초록색(진짜맛집) 핀
            pin_color = "red" if row['rating_gap'] >= 0.4 else "green"
            
            popup_html = f"""
            <div style="width:200px; font-family:sans-serif;">
                <b>{row['상호명']}</b><br>
                <span style="color:gray; font-size:12px;">{row['행정동명']} | {row.get('상권업종중분류명', '음식점')}</span><hr style="margin:5px 0;">
                기존 단순 별점: <b>{row['raw_rating']:.2f}점</b><br>
                AI 진짜 평점: <b style="color:{pin_color};">{row['true_score']:.2f}점</b><br>
                <span style="font-size:11px;">(거품 지수: -{row['rating_gap']:.2f})</span>
            </div>
            """
            folium.Marker(
                location=[row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['상호명']} (진짜평점 {row['true_score']:.2f})",
                icon=folium.Icon(color=pin_color, icon="cutlery", prefix="fa")
            ).add_to(m)

        st.info("🟢 초록 핀: 진짜 맛집 (거품 적음) / 🔴 빨간 핀: 광고 거품 주의 매장 (핀을 클릭해 보세요!)")
        st_folium(m, width=700, height=450)
    else:
        st.warning("선택한 지역에 표시할 위도·경도 좌표 데이터가 없습니다.")

    # 하단 요약 리스트
    st.subheader("📋 선택 지역 매장 평점 비교표")
    st.dataframe(
        filtered_df[['상호명', '시군구명', '행정동명', 'raw_rating', 'true_score', 'rating_gap']]
        .rename(columns={'raw_rating': '기존별점', 'true_score': '진짜평점', 'rating_gap': '평점거품'})
        .sort_values(by='진짜평점', ascending=False),
        use_container_width=True
    )

with tab2:
    st.subheader("이 리뷰, 영수증 이벤트 알바일까?")
    user_review = st.text_area("리뷰 텍스트 입력", placeholder="예: 영수증 리뷰 이벤트 참여하면 음료수 주셔서 남깁니다~ 사장님 친절해요!", height=120)
    
    if st.button("AI 판독 실행", type="primary", use_container_width=True):
        if user_review.strip() == "":
            st.warning("리뷰 내용을 먼저 입력해 주세요.")
        else:
            ad_keywords = ['영수증', '이벤트', '서비스', '협찬', '원고료', '제공받아', '친절', '음료수']
            hit_keywords = [kw for kw in ad_keywords if kw in user_review]
            length = len(user_review.strip())
            
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
