# 🍽️ 데이트 맛집 찾기

동네와 먹고 싶은 음식을 고르면 **카카오맵에서 실시간으로** 가게를 찾아주는 웹앱이에요.
대구 중구 · 수성구 · 동대구 위주로 동네가 준비돼 있고, 우리 커플 취향(고기, 야장, 떡볶이, 신상 카페 등)에 맞는 곳이 위로 올라와요.

- 동네: 교동, 동성로, 삼덕동, 대봉동, 동인동, 경대병원역, 반월당, 범어역, 들안길, 수성못, 시지, 동대구역 · 신세계 + 직접 입력
- 음식: 소고기, 삼겹살, 족발, 회, 떡볶이, 마라탕, 중식, 치킨, 야장 · 술집, 초밥, 파스타, 카페, 베이커리, 브런치 + 직접 입력
- 정렬: 우리 취향순 / 가까운순 / 카카오 추천순
- ☕ 카페 → 저녁 코스: 근처 카페를 같이 찾아줘요
- 🎲 못 고르겠을 때 하나 골라주기
- 가게마다 카카오맵(리뷰·사진), 네이버지도, 길찾기 링크

---

## 1단계. 카카오 API 키 받기 (무료, 5분)

1. <https://developers.kakao.com> 에 카카오 계정으로 로그인
2. 위쪽 메뉴 **내 애플리케이션 → 애플리케이션 추가하기**
   - 앱 이름: `데이트맛집` (아무거나), 회사명: `개인`
3. 만든 앱을 누르고 **앱 키** 화면에서 **REST API 키**를 복사
   - 화면 구성은 가끔 바뀌어요. "REST API 키"라는 이름을 찾으면 돼요.
4. 왼쪽 메뉴 **카카오맵**(제품 설정)에 들어가서 **사용 설정을 ON**
   - 2024년 12월 이후에 만든 앱은 이걸 켜야 검색이 돼요. 안 켜면 앱에서 "사용 권한이 없어요" 오류가 나요.

> 🔒 키는 비밀번호처럼 다뤄 주세요. 채팅이나 GitHub에 그대로 올리지 말고, 아래 방법대로 **Secrets**에만 넣어요.

## 2단계-A. 폰에서 쓰기: Streamlit Cloud에 무료 배포 (추천)

1. 이 폴더를 내 GitHub 저장소에 올려요 (비공개 저장소도 괜찮아요).
2. <https://share.streamlit.io> 에 GitHub 계정으로 로그인
3. **Create app → Deploy a public app from GitHub** 선택
   - Repository: 방금 올린 저장소 / Branch: `main` / Main file path: `app.py`
4. **Advanced settings → Secrets** 칸에 아래 한 줄을 붙여넣기
   ```toml
   KAKAO_REST_API_KEY = "복사한_REST_API_키"
   ```
5. **Deploy** → 1~2분 뒤 `https://○○○.streamlit.app` 주소가 생겨요.
6. 폰에서 그 주소를 열고 **홈 화면에 추가**하면 앱처럼 쓸 수 있어요.

## 2단계-B. 내 컴퓨터에서 실행하기

Python 3.10 이상이 필요해요.

**Mac**
```bash
cd date-food-finder
```
```bash
python3 -m venv .venv && source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```
`.streamlit/secrets.toml`을 열어 키를 넣은 다음:
```bash
streamlit run app.py
```

**Windows (PowerShell)**
```bash
cd date-food-finder
```
```bash
python -m venv .venv; .venv\Scripts\Activate.ps1
```
```bash
pip install -r requirements.txt
```
```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```
메모장으로 `.streamlit\secrets.toml`을 열어 키를 넣은 다음:
```bash
streamlit run app.py
```

브라우저가 `http://localhost:8501`로 열려요. 키가 없으면 **예시 화면**으로 떠요.

---

## 취향 바꾸기

`presets.py` 한 파일만 고치면 돼요.

| 바꾸고 싶은 것 | 고칠 곳 |
|---|---|
| 동네 추가 (좌표) | `NEIGHBORHOODS` |
| 음식 버튼 추가 | `FOOD_TYPES` |
| 좋아하는 단어와 점수 | `LIKES` (점수가 클수록 위로) |
| 추천에서 뺄 가게 | `EXCLUDE` |

예를 들어 곱창을 좋아하게 됐다면 `LIKES`에 `"곱창": 3,`을 추가하면 돼요.

## 파일 구조

```
app.py          화면 (Streamlit)
kakao.py        카카오 로컬 API 검색 + 취향 점수 + 정렬
presets.py      동네 좌표, 음식 종류, 우리 취향
tests/          카카오 API를 부르지 않는 자동 테스트 (pytest)
```

테스트 실행: `pip install -r requirements-dev.txt` 후 `pytest`

## 알아두면 좋은 점

- 카카오 로컬 API는 무료이고 하루 사용량 한도가 넉넉해요. 둘이 쓰기엔 충분해요.
- 별점은 API로 제공되지 않아요. 가게마다 있는 **카카오맵 · 리뷰** 버튼으로 확인해요.
- 같은 검색은 10분 동안 저장해 두었다가 다시 보여줘서 빠르고 사용량도 아껴요.
