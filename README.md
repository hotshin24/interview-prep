# 면접 답변집

웹 퍼블리셔 면접 대비 개인 학습 문서를 단일 HTML로 정리한 것입니다.

**배포:** https://hotshin24.github.io/interview-prep/

## 기능

- 14개 챕터 · 287문항, 좌측 고정 목차 + 문항 검색 + 스크롤 위치 추적
- iOS 디자인 언어 기반 다크 UI (라이트 전환 · 인쇄 시 자동 라이트)
- 브라우저 음성 합성(Web Speech API) 읽어주기 — 연속 재생 · 속도 조절 · 목소리 선택
- 외부 리소스 의존 없는 단일 파일 (오프라인 동작)

## 구조

```
신호진_면접_답변집.md   원고 (수정은 여기서)
index.html              생성물 — 직접 고치지 말 것
tools/build.py          변환 스크립트
tools/template.html     레이아웃 · 스타일 · 스크립트 템플릿
```

## 수정 방법

원고나 템플릿을 고친 뒤 다시 생성합니다.

```bash
python3 tools/build.py
```

`index.html`이 갱신되며, 커밋·푸시하면 1~2분 내 GitHub Pages에 반영됩니다.

개인 학습·연습 용도의 문서입니다.
