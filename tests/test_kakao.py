"""카카오 API를 실제로 부르지 않고(가짜 응답으로) 검색·점수·정렬 로직을 확인해요."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kakao  # noqa: E402
from presets import EXCLUDE, LIKES  # noqa: E402


def doc(i, name, category="음식점 > 한식 > 육류,고기", distance="300"):
    return {
        "id": str(i), "place_name": name, "category_name": category,
        "address_name": "대구 중구 교동 1", "road_address_name": "대구 중구 교동길 1",
        "phone": "053-000-0000", "x": "128.5967", "y": "35.8722",
        "place_url": f"http://place.map.kakao.com/{i}", "distance": distance,
    }


class FakeResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or {}

    def json(self):
        return self._data


class FakeSession:
    """페이지별 응답을 순서대로 돌려주고, 요청 내용을 기록해요."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "params": dict(params)})
        return self.responses.pop(0)


def page(docs, is_end):
    return FakeResp(200, {"documents": docs, "meta": {"is_end": is_end}})


def test_search_sends_key_and_location_and_paginates():
    s = FakeSession([page([doc(1, "갈비집")], False), page([doc(2, "고기집"), doc(1, "갈비집")], True)])
    places = kakao.search("KEY", "소고기", x=128.59, y=35.87, radius=1000, category="FD6", session=s)

    assert [p.name for p in places] == ["갈비집", "고기집"]  # 중복 제거
    assert len(s.calls) == 2  # is_end에서 멈춤
    first = s.calls[0]
    assert first["headers"]["Authorization"] == "KakaoAK KEY"
    assert first["params"]["x"] == 128.59 and first["params"]["radius"] == 1000
    assert first["params"]["category_group_code"] == "FD6"
    assert s.calls[1]["params"]["page"] == 2
    assert places[0].kakao_url.startswith("https://")


def test_search_clamps_radius():
    s = FakeSession([page([], True)])
    kakao.search("KEY", "회", x=1, y=2, radius=99999, session=s)
    assert s.calls[0]["params"]["radius"] == 20000


@pytest.mark.parametrize("status,needle", [(401, "키가 올바르지"), (403, "카카오맵"), (429, "한도"), (500, "500")])
def test_search_errors_are_friendly(status, needle):
    with pytest.raises(kakao.KakaoError, match=needle):
        kakao.search("KEY", "회", session=FakeSession([FakeResp(status)]))


def test_search_without_key():
    with pytest.raises(kakao.KakaoError, match="키가 없어요"):
        kakao.search("", "회")


def test_score_excludes_and_prefers_our_taste():
    places = [kakao.parse_place(d) for d in [
        doc(1, "평범한 한식당", "음식점 > 한식", "100"),
        doc(2, "바밤", "음식점 > 술집", "50"),
        doc(3, "소고기 갈비살 전문", "음식점 > 한식 > 육류,고기", "400"),
    ]]
    scored = kakao.score_places(places, LIKES, EXCLUDE)
    names = [p.name for p in scored]
    assert "바밤" not in names
    best = kakao.sort_places(scored, "taste")[0]
    assert best.name == "소고기 갈비살 전문"
    assert "소고기" in best.matched and "갈비살" in best.matched


def test_sort_by_distance_puts_unknown_last():
    a, b, c = (kakao.parse_place(doc(i, n, distance=d)) for i, n, d in [(1, "먼곳", "900"), (2, "모름", ""), (3, "가까운곳", "50")])
    assert [p.name for p in kakao.sort_places([a, b, c], "distance")] == ["가까운곳", "먼곳", "모름"]


def test_geocode_adds_daegu_prefix():
    s = FakeSession([page([doc(9, "김광석다시그리기길")], True)])
    y, x, name = kakao.geocode("KEY", "김광석길", session=s)
    assert s.calls[0]["params"]["query"] == "대구 김광석길"
    assert (y, x, name) == (35.8722, 128.5967, "김광석다시그리기길")


def test_links():
    p = kakao.parse_place(doc(1, "갈비 집"))
    assert p.naver_url.startswith("https://map.naver.com/p/search/")
    assert p.kakao_directions_url == "https://map.kakao.com/link/to/%EA%B0%88%EB%B9%84%20%EC%A7%91,35.8722,128.5967"
    assert p.short_category == "한식 · 육류,고기"
