"""카카오 로컬 API로 가게를 검색하고, 우리 취향 점수를 매겨 정렬해요."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import requests

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
MAX_PAGES = 3          # 한 페이지 15개, 최대 45개까지
TIMEOUT_SECONDS = 8


class KakaoError(Exception):
    """사용자에게 그대로 보여줄 수 있는 한국어 오류."""


@dataclass
class Place:
    id: str
    name: str
    category: str          # 예: "음식점 > 한식 > 육류,고기"
    address: str
    road_address: str
    phone: str
    x: float
    y: float
    distance_m: int | None
    kakao_url: str
    score: float = 0.0
    matched: tuple[str, ...] = ()

    @property
    def short_category(self) -> str:
        parts = [p.strip() for p in self.category.split(">")]
        return " · ".join(parts[1:]) if len(parts) > 1 else self.category

    @property
    def naver_url(self) -> str:
        return "https://map.naver.com/p/search/" + quote(f"{self.name} {self.road_address or self.address}")

    @property
    def kakao_directions_url(self) -> str:
        return f"https://map.kakao.com/link/to/{quote(self.name)},{self.y},{self.x}"


def parse_place(doc: dict) -> Place:
    dist = doc.get("distance")
    return Place(
        id=str(doc.get("id", "")),
        name=doc.get("place_name", ""),
        category=doc.get("category_name", ""),
        address=doc.get("address_name", ""),
        road_address=doc.get("road_address_name", ""),
        phone=doc.get("phone", ""),
        x=float(doc.get("x") or 0),
        y=float(doc.get("y") or 0),
        distance_m=int(dist) if dist not in (None, "") else None,
        kakao_url=(doc.get("place_url") or "").replace("http://", "https://"),
    )


def search(
    api_key: str,
    query: str,
    *,
    x: float | None = None,
    y: float | None = None,
    radius: int | None = None,
    category: str | None = None,
    sort: str = "accuracy",
    max_pages: int = MAX_PAGES,
    session: requests.Session | None = None,
) -> list[Place]:
    """키워드로 가게를 검색해요. x/y/radius를 주면 그 주변만 찾아요."""
    if not api_key:
        raise KakaoError("카카오 REST API 키가 없어요. 설정(Secrets)에 KAKAO_REST_API_KEY를 넣어주세요.")
    http = session or requests
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params: dict = {"query": query, "size": 15, "sort": sort}
    if x is not None and y is not None:
        params.update(x=x, y=y)
        if radius:
            params["radius"] = max(0, min(int(radius), 20000))
    if category:
        params["category_group_code"] = category

    places: list[Place] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        params["page"] = page
        try:
            resp = http.get(KEYWORD_URL, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as e:
            raise KakaoError("카카오 서버에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.") from e
        if resp.status_code == 401:
            raise KakaoError("카카오 API 키가 올바르지 않아요. REST API 키를 다시 확인해 주세요.")
        if resp.status_code == 403:
            raise KakaoError(
                "카카오 API 사용 권한이 없어요. 카카오 개발자 사이트의 내 앱 설정에서 "
                "'카카오맵' 사용 설정을 켰는지 확인해 주세요."
            )
        if resp.status_code == 429:
            raise KakaoError("오늘 검색 한도를 넘었어요. 내일 다시 시도해 주세요.")
        if resp.status_code != 200:
            raise KakaoError(f"카카오 검색 중 오류가 났어요 (코드 {resp.status_code}).")
        data = resp.json()
        for doc in data.get("documents", []):
            p = parse_place(doc)
            if p.id and p.id not in seen:
                seen.add(p.id)
                places.append(p)
        if data.get("meta", {}).get("is_end", True):
            break
    return places


def geocode(api_key: str, text: str, session: requests.Session | None = None) -> tuple[float, float, str] | None:
    """'대구 ○○' 처럼 동네 이름을 좌표로 바꿔요. (위도, 경도, 찾은 장소 이름)"""
    query = text if text.startswith("대구") else f"대구 {text}"
    found = search(api_key, query, max_pages=1, session=session)
    if not found:
        return None
    top = found[0]
    return top.y, top.x, top.name


def score_places(places: list[Place], likes: dict[str, int], exclude: list[str]) -> list[Place]:
    """제외할 가게를 빼고, 취향 단어가 들어 있으면 점수를 더해요.

    점수 = 취향 점수 합 + (카카오 정확도 순위 보너스) - (거리 페널티)
    """
    kept: list[Place] = []
    n = len(places)
    for rank, p in enumerate(places):
        if any(word and word in p.name for word in exclude):
            continue
        text = f"{p.name} {p.category}"
        matched = tuple(w for w in likes if w in text)
        base = sum(likes[w] for w in matched)
        rank_bonus = 2.0 * (n - rank) / n if n else 0     # 카카오가 앞에 보여준 곳일수록 +
        dist_penalty = (p.distance_m or 0) / 1000        # 1km마다 -1
        p.score = round(base + rank_bonus - dist_penalty, 2)
        p.matched = matched
        kept.append(p)
    return kept


def sort_places(places: list[Place], how: str) -> list[Place]:
    if how == "distance":
        return sorted(places, key=lambda p: (p.distance_m is None, p.distance_m or 0))
    if how == "taste":
        return sorted(places, key=lambda p: -p.score)
    return list(places)  # accuracy: 카카오가 준 순서 그대로
