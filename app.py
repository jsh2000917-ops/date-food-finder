"""데이트 맛집 찾기 — 동네와 음식 종류를 고르면 카카오맵에서 실시간으로 가게를 찾아줘요.

실행:  streamlit run app.py
"""

from __future__ import annotations

import html
import os
import random

import streamlit as st

import kakao
from presets import CAFE, EXCLUDE, FOOD_TYPES, LIKES, NEIGHBORHOODS, RADIUS_CHOICES

st.set_page_config(page_title="데이트 맛집 찾기", page_icon="🍽️", layout="centered")

st.markdown(
    """
    <style>
      .block-container { max-width: 720px; padding-top: 2rem; }
      .place-name { font-size: 1.15rem; font-weight: 700; margin: 0; }
      .place-meta { color: #8a8494; font-size: 0.88rem; margin: 0.1rem 0 0.4rem; }
      .chip { display: inline-block; background: rgba(217,71,108,.12); color: #d9476c;
              border-radius: 999px; padding: 1px 10px; font-size: 0.78rem; margin-right: 4px; }
      .links { display: flex; gap: 6px; flex-wrap: wrap; }
      .links a { flex: 1 1 0; min-width: 90px; text-align: center; text-decoration: none !important;
                 border: 1px solid rgba(128,128,128,.35); border-radius: 10px; padding: 6px 8px;
                 font-size: .85rem; color: inherit !important; white-space: nowrap; }
      .links a:hover { border-color: #d9476c; color: #d9476c !important; }
      .demo { background: rgba(255,165,0,.15); border-radius: 8px; padding: 2px 8px; font-size: .8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_api_key() -> str:
    try:
        key = st.secrets.get("KAKAO_REST_API_KEY", "")
    except Exception:  # secrets.toml이 아예 없을 때
        key = ""
    return (key or os.environ.get("KAKAO_REST_API_KEY", "")).strip()


@st.cache_data(ttl=600, show_spinner=False)
def cached_search(_api_key: str, query: str, x: float, y: float, radius: int, category: str | None):
    return kakao.search(_api_key, query, x=x, y=y, radius=radius, category=category)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_geocode(_api_key: str, text: str):
    return kakao.geocode(_api_key, text)


def demo_places(food_label: str) -> list[kakao.Place]:
    """API 키가 없을 때 화면 모양을 보여주는 예시 데이터 (실제 가게 아님)."""
    word = FOOD_TYPES.get(food_label, (food_label, None))[0]
    rows = [
        (f"예시) {word} 맛집 A", f"예시 > {word}", 180),
        (f"예시) {word} 전문점 B", f"예시 > {word}", 420),
        (f"예시) 동네 {word}집 C", f"예시 > {word}", 760),
    ]
    return [
        kakao.Place(id=str(i), name=n, category=c, address="대구 (예시 주소)", road_address="",
                    phone="", x=128.6, y=35.87, distance_m=d, kakao_url="https://map.kakao.com")
        for i, (n, c, d) in enumerate(rows)
    ]


def render_place(p: kakao.Place, key_prefix: str, highlight: bool = False) -> None:
    with st.container(border=True):
        title = ("🎯 " if highlight else "") + html.escape(p.name)
        st.markdown(f'<p class="place-name">{title}</p>', unsafe_allow_html=True)
        meta = [p.short_category]
        if p.distance_m is not None:
            meta.append(f"{p.distance_m:,}m")
        st.markdown(f'<p class="place-meta">{html.escape(" · ".join(meta))}</p>', unsafe_allow_html=True)
        if p.matched:
            chips = "".join(f'<span class="chip">{w}</span>' for w in p.matched[:4])
            st.markdown(f"취향 저격 {chips}", unsafe_allow_html=True)
        st.caption(f"📍 {p.road_address or p.address}" + (f"  ·  ☎ {p.phone}" if p.phone else ""))
        links = [("카카오맵 · 리뷰", p.kakao_url), ("네이버지도", p.naver_url), ("길찾기", p.kakao_directions_url)]
        st.markdown(
            '<div class="links">' + "".join(
                f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{t}</a>' for t, u in links
            ) + "</div>",
            unsafe_allow_html=True,
        )


# ---------------- 화면 ----------------
st.title("🍽️ 데이트 맛집 찾기")
st.caption("동네랑 먹고 싶은 걸 고르면 카카오맵에서 지금 바로 찾아줘요. 고기·야장·신상 카페를 좋아하는 우리 취향대로 정렬돼요.")

api_key = get_api_key()
demo = not api_key
if demo:
    st.info(
        "아직 카카오 API 키가 없어서 **예시 화면**을 보여주고 있어요. "
        "README의 'API 키 넣기'를 따라 키를 넣으면 실제 가게가 검색돼요.",
        icon="🔑",
    )

# 1) 동네
areas = [f"{gu} · {name}" for gu, d in NEIGHBORHOODS.items() for name in d] + ["✏️ 직접 입력"]
area_choice = st.selectbox("어느 동네?", areas, index=0, key="area")
custom_area = ""
if area_choice == "✏️ 직접 입력":
    custom_area = st.text_input("동네나 역 이름", placeholder="예) 김광석길, 대구역, 앞산카페거리", key="custom_area")

# 2) 음식
food_label = st.pills("뭐 먹을까?", list(FOOD_TYPES), default="🥩 소고기 · 갈비살", key="food")
custom_food = st.text_input("직접 입력 (선택)", placeholder="예) 곱창, 오마카세, 디저트", key="custom_food")

c1, c2 = st.columns(2)
radius_label = c1.segmented_control("얼마나 멀리?", list(RADIUS_CHOICES), default="걸어서 15분 (1km)", key="radius")
sort_label = c2.segmented_control("정렬", ["우리 취향순", "가까운순", "카카오 추천순"], default="우리 취향순", key="sort")
with_cafe = st.toggle("☕ 근처 카페도 같이 찾기 (카페 → 저녁 코스)", value=False, key="with_cafe")

go = st.button("찾아보기", type="primary", use_container_width=True)

if go:
    st.session_state["last_query"] = dict(
        area=area_choice, custom_area=custom_area.strip(), food=food_label,
        custom_food=custom_food.strip(), radius=radius_label, sort=sort_label, with_cafe=with_cafe,
    )
    st.session_state.pop("pick", None)

q = st.session_state.get("last_query")
if not q:
    st.stop()

# 검색 조건 정리
if q["custom_food"]:
    query, category = q["custom_food"], None
elif q["food"]:
    query, category = FOOD_TYPES[q["food"]]
else:
    st.warning("먹고 싶은 걸 하나 골라주세요.")
    st.stop()
radius = RADIUS_CHOICES.get(q["radius"] or "", 1000)
sort_key = {"우리 취향순": "taste", "가까운순": "distance"}.get(q["sort"] or "", "accuracy")

try:
    if q["area"] == "✏️ 직접 입력":
        if not q["custom_area"]:
            st.warning("동네나 역 이름을 적어주세요.")
            st.stop()
        if demo:
            y, x, area_name = 35.87, 128.6, q["custom_area"]
        else:
            loc = cached_geocode(api_key, q["custom_area"])
            if not loc:
                st.warning(f"'{q['custom_area']}' 위치를 찾지 못했어요. 다른 이름으로 적어볼래요?")
                st.stop()
            y, x, area_name = loc
    else:
        gu, name = q["area"].split(" · ", 1)
        y, x = NEIGHBORHOODS[gu][name]
        area_name = name

    with st.spinner(f"{area_name} 근처 '{query}' 찾는 중…"):
        found = demo_places(query if q["custom_food"] else q["food"]) if demo else cached_search(api_key, query, x, y, radius, category)
        places = kakao.sort_places(kakao.score_places(found, LIKES, EXCLUDE), sort_key)
        cafes: list[kakao.Place] = []
        if q["with_cafe"] and category != CAFE:
            raw_cafes = demo_places("☕ 카페") if demo else cached_search(api_key, "카페", x, y, radius, CAFE)
            cafes = kakao.sort_places(kakao.score_places(raw_cafes, LIKES, EXCLUDE), sort_key)[:5]
except kakao.KakaoError as e:
    st.error(str(e), icon="⚠️")
    st.stop()

st.divider()
head = f"**{area_name}** 근처 **{query}** {len(places)}곳"
if demo:
    head += ' <span class="demo">예시 데이터</span>'
st.markdown(head, unsafe_allow_html=True)

if not places:
    st.info("조건에 맞는 가게가 없어요. 반경을 넓히거나 다른 음식을 골라보세요.")
    st.stop()

if st.button("🎲 못 고르겠어! 하나 골라줘", use_container_width=True):
    top = sorted(places, key=lambda p: -p.score)[:10]
    st.session_state["pick"] = random.choice(top).id

pick_id = st.session_state.get("pick")
if pick_id:
    picked = next((p for p in places if p.id == pick_id), None)
    if picked:
        st.success("오늘은 여기 어때요?", icon="🎯")
        render_place(picked, "pick", highlight=True)
        st.markdown("&nbsp;")

if cafes:
    st.markdown("#### ☕ 먼저 들를 카페")
    for p in cafes:
        render_place(p, "cafe")
    st.markdown(f"#### 🍽️ 그다음 {query}")

for p in places[:20]:
    render_place(p, "main")

if len(places) > 20:
    st.caption(f"상위 20곳만 보여줬어요 (전체 {len(places)}곳).")
st.caption("가게 정보 제공: 카카오 로컬 API · 별점과 리뷰는 카카오맵 링크에서 확인하세요.")
