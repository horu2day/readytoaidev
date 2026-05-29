# PLAN.md — readytoaidev 로드맵

> 에이전트들이 "무엇을 해야 하는가"를 읽는 파일. 진행 상태는 `PROGRESS.md`에 기록.
> 세션 시작 시 이 파일 + `PROGRESS.md`를 먼저 읽을 것 (CLAUDE.md §3).

## 목표 (Definition of Done)

비개발자용 AI 개발 강의 사이트(`vscode-lecture.html`)를 **접근성·반응형·콘텐츠 품질**
기준을 만족하고, 그 기준이 **자동 테스트로 검증**되는 상태로 만든다.

## 단계 (Phases)

### Phase 0 — 환경 셋업  ✅ 진행 중
- [x] 메모리에 프로젝트/테스트 계획 저장
- [x] CLAUDE.md, PLAN.md, PROGRESS.md, considerations.md 작성
- [x] `.claude/` 에이전트·커맨드·스킬·훅 골격 생성
- [ ] Node 프로젝트 초기화 (`package.json`, Playwright 설치)  — verify: `npx playwright --version`

### Phase 1 — 콘텐츠/마크업 정비
- [ ] HTML 구조 접근성 보강(`<main>`, heading 계층, lang)  — verify: html-validate 통과
- [ ] 색 대비·포커스 스타일 점검  — verify: axe 위반 0
- [ ] 콘텐츠 lint 통과(전문용어 정의, 문장 길이)  — verify: content-linter 통과
- 담당 에이전트: `content-writer`, `a11y-auditor`, `content-linter`

### Phase 2 — 테스트 자동화 구축 (에이전트를 하나씩)
각 레이어 = 하나의 테스트 스위트, 하나의 에이전트가 소유. PROGRESS.md에 결과 기록.
- [ ] 2.1 마크업 유효성 (html-validate)  — verify: `npm run test:html`
- [ ] 2.2 E2E + 반응형 (Playwright, 3 viewport)  — verify: `npm run test:e2e`
- [ ] 2.3 접근성 (@axe-core/playwright)  — verify: `npm run test:a11y`
- [ ] 2.4 시각 회귀 (Playwright snapshots)  — verify: `npm run test:visual`
- [ ] 2.5 성능/SEO (Lighthouse CI 예산)  — verify: `npm run test:perf`
- [ ] 2.6 죽은 링크 (linkinator)  — verify: `npm run test:links`
- [ ] 2.7 콘텐츠 품질 lint (커스텀)  — verify: `npm run lint:content`
- 담당 에이전트: `test-planner` → `e2e-tester` / `a11y-auditor` / `content-linter`

### Phase 3 — CI 통합
- [ ] GitHub Actions: PR마다 전체 스위트 실행  — verify: 워크플로 녹색
- [ ] 실패 시 PROGRESS.md 자동 갱신 훅

### Phase 4 — 확장 (백로그)
- [ ] 진도 체크리스트(localStorage), 퀴즈
- [ ] SEO/OG 태그, 목차
- [ ] 다국어(i18n)

## 작업 분배 원칙
- 한 번에 한 레이어/한 에이전트. 끝나면 PROGRESS.md 갱신 후 다음.
- 변경은 외과적으로(global CLAUDE.md §3). 요청 범위 밖 "개선" 금지.
- 막히면 PROGRESS.md의 Blocked에 적고 멈춤 → 사용자에게 질문.
