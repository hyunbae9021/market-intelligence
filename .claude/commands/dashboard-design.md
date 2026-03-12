# HTML Dashboard Design Skill

이 문서는 HTML 대시보드 제작 시 반드시 따라야 할 디자인 가이드입니다.
모든 HTML 대시보드 요청에 이 규칙을 적용하세요.

---

## 1. 브랜드 컬러 팔레트 (두나무 로고 기반)

두나무 메인 컬러: `#1B3BFF` (두나무 블루)

```css
:root {
  /* Primary */
  --color-primary:        #1B3BFF;   /* 두나무 블루 — 주요 강조, 버튼, 링크 */
  --color-primary-dark:   #1230CC;   /* 호버/액티브 상태 */
  --color-primary-light:  #4D68FF;   /* 보조 강조 */
  --color-primary-bg:     #EEF1FF;   /* 카드 배경, 하이라이트 영역 */

  /* Neutral */
  --color-bg:             #F7F8FA;   /* 전체 페이지 배경 */
  --color-surface:        #FFFFFF;   /* 카드/패널 배경 */
  --color-border:         #E8EAED;   /* 구분선, 테두리 */

  /* Text */
  --color-text-primary:   #191F28;   /* 제목, 주요 텍스트 */
  --color-text-secondary: #4E5968;   /* 보조 텍스트, 라벨 */
  --color-text-tertiary:  #8B95A1;   /* 힌트, 비활성 */

  /* Semantic */
  --color-positive:       #0ABF76;   /* 상승, 긍정 */
  --color-negative:       #F04452;   /* 하락, 부정 */
  --color-warning:        #FF9500;   /* 주의 */
  --color-info:           #1B3BFF;   /* 정보 (primary와 동일) */
}
```

---

## 2. 폰트

**반드시 Pretendard 사용.** Google Fonts CDN 대신 Pretendard 공식 CDN을 사용합니다.

```html
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
```

```css
* {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
}
```

### 타이포그래피 스케일

| 용도 | 크기 | 굵기 |
|------|------|------|
| 페이지 제목 | 28px | 700 |
| 섹션 제목 | 22px | 700 |
| 카드 제목 | 18px | 600 |
| 주요 수치(KPI) | 32–40px | 700 |
| 본문 | 15px | 400 |
| 보조 라벨 | 13px | 400 |
| 최소 허용 크기 | **12px** | — |

> **규칙**: 본문 텍스트는 절대 12px 미만으로 설정하지 않습니다. 가독성 최우선.

---

## 3. 디자인 스타일 — 토스(Toss) 스타일

토스 디자인의 핵심 원칙을 따릅니다.

### 레이아웃
- **배경**: `#F7F8FA` (연한 회색)
- **카드**: `background: #FFFFFF`, `border-radius: 16px`, 섀도우 사용
- **카드 패딩**: `24px 28px`
- **그리드 간격(gap)**: `16–20px`
- **최대 페이지 너비**: `1280px`, 중앙 정렬

### 카드 섀도우
```css
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 0 1px rgba(0, 0, 0, 0.08);
```

호버 시:
```css
box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10), 0 0 1px rgba(0, 0, 0, 0.08);
transition: box-shadow 0.2s ease;
```

### 라운드 처리
| 요소 | border-radius |
|------|--------------|
| 카드/패널 | 16px |
| 버튼 (대) | 12px |
| 버튼 (소) / 뱃지 | 8px |
| 인풋 필드 | 10px |
| 태그/칩 | 100px (pill) |

### KPI 카드 구조 예시
```html
<div class="kpi-card">
  <span class="kpi-label">총 거래량</span>
  <div class="kpi-value">₩2.4조</div>
  <span class="kpi-change positive">▲ 12.3%</span>
</div>
```

### 색상 사용 원칙
- 페이지 배경은 항상 `#F7F8FA`
- 강조 포인트(버튼, 링크, 활성 상태)만 `--color-primary` 사용
- 배경 대비 충분한 텍스트 명도 확보 (WCAG AA 기준 이상)
- 상승/긍정: `#0ABF76`, 하락/부정: `#F04452`

### 구분선
```css
border-top: 1px solid #E8EAED;
```

---

## 4. 헤더 구조

```html
<header class="dashboard-header">
  <div class="header-left">
    <div class="logo">DUNAMU</div>
    <div class="header-title">대시보드 제목</div>
  </div>
  <div class="header-meta">
    <span class="date">기준일: 2026-03-10</span>
  </div>
</header>
```

---

## 5. 필수 워터마크 — 모든 대시보드에 반드시 포함

**모든 HTML 대시보드의 우측 하단**에 다음 워터마크를 고정 배치합니다.

```html
<div class="watermark">
  <span class="watermark-company">DUNAMU 경영혁신실</span>
  <span class="watermark-confidential">Confidential</span>
</div>
```

```css
.watermark {
  position: fixed;
  bottom: 20px;
  right: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  z-index: 100;
  pointer-events: none;
}

.watermark-company {
  font-size: 13px;
  font-weight: 600;
  color: #4E5968;
  letter-spacing: 0.02em;
}

.watermark-confidential {
  font-size: 12px;
  font-weight: 400;
  color: #8B95A1;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
```

> **규칙**: 이 워터마크는 생략하거나 위치를 변경하지 않습니다.

---

## 6. 전체 HTML 보일러플레이트

모든 대시보드는 아래 구조를 기반으로 시작합니다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>대시보드 제목</title>
  <link rel="stylesheet" as="style" crossorigin
    href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --color-primary:        #1B3BFF;
      --color-primary-dark:   #1230CC;
      --color-primary-light:  #4D68FF;
      --color-primary-bg:     #EEF1FF;
      --color-bg:             #F7F8FA;
      --color-surface:        #FFFFFF;
      --color-border:         #E8EAED;
      --color-text-primary:   #191F28;
      --color-text-secondary: #4E5968;
      --color-text-tertiary:  #8B95A1;
      --color-positive:       #0ABF76;
      --color-negative:       #F04452;
      --color-warning:        #FF9500;
    }

    body {
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--color-bg);
      color: var(--color-text-primary);
      font-size: 15px;
      line-height: 1.6;
    }

    .dashboard-wrapper {
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 24px 80px;
    }

    /* 카드 */
    .card {
      background: var(--color-surface);
      border-radius: 16px;
      padding: 24px 28px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 1px rgba(0,0,0,0.08);
    }
    .card:hover {
      box-shadow: 0 8px 24px rgba(0,0,0,0.10), 0 0 1px rgba(0,0,0,0.08);
      transition: box-shadow 0.2s ease;
    }

    /* 워터마크 */
    .watermark {
      position: fixed;
      bottom: 20px;
      right: 24px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 2px;
      z-index: 100;
      pointer-events: none;
    }
    .watermark-company {
      font-size: 13px;
      font-weight: 600;
      color: #4E5968;
      letter-spacing: 0.02em;
    }
    .watermark-confidential {
      font-size: 12px;
      font-weight: 400;
      color: #8B95A1;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
  </style>
</head>
<body>
  <div class="dashboard-wrapper">
    <!-- 콘텐츠 -->
  </div>

  <!-- 필수 워터마크: 절대 생략 불가 -->
  <div class="watermark">
    <span class="watermark-company">DUNAMU 경영혁신실</span>
    <span class="watermark-confidential">Confidential</span>
  </div>
</body>
</html>
```

---

## 7. 체크리스트 (완성 전 반드시 확인)

- [ ] Pretendard 폰트 CDN 연결 확인
- [ ] 모든 텍스트 12px 이상
- [ ] 본문 텍스트 15px 기준
- [ ] 두나무 블루(`#1B3BFF`) 메인 컬러 사용
- [ ] 카드 `border-radius: 16px` + 섀도우 적용
- [ ] 배경색 `#F7F8FA`
- [ ] 우측 하단 워터마크(DUNAMU 경영혁신실 / Confidential) 고정 배치
- [ ] 상승/하락 색상 `#0ABF76` / `#F04452` 사용
