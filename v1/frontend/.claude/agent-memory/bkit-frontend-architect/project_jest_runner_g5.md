---
name: jest-test-runner-setup G'-5 completion
description: Phase 7 G'-5 done; Jest 29 + ts-jest + jsdom installed; 8 analytics tests pass; dual tsconfig pattern for test type-safety
type: project
---

Jest test runner setup for G'-5 is complete (2026-05-04).

**Why:** A-1 analytics tests (`capture.test.ts`, `featureFlags.test.ts`) existed since Phase 6 with no runner. G'-5 closes that carry-over.

**How to apply:** When writing new tests, follow the dual-tsconfig pattern: main `tsconfig.json` excludes `src/__tests__`; `tsconfig.test.json` covers test files with `strict: false` (needed because A-1 tests assign to `process.env.NODE_ENV`). Jest config is at `jest.config.ts` using `setupFilesAfterEnv`.

**Key decisions:**
- Jest 29 (not 30) — ts-jest 29 compatibility
- `tsconfig.test.json` with `strict: false` — A-1 test files assign `process.env.NODE_ENV` which strict mode rejects; cannot modify A-1 tests
- `ts-node` required as devDependency for `jest.config.ts` (TypeScript config file)
- PostHog mock in `jest.setup.ts` covers both `capture.ts` and `featureFlags.ts`
- 8 tests pass (spec said 5 — actual count is 8; spec was conservative)

**New files (6):**
- `jest.config.ts` — preset ts-jest, jsdom, setupFilesAfterEnv, @/ alias
- `jest.setup.ts` — @testing-library/jest-dom + posthog-js mock
- `tsconfig.test.json` — extends main tsconfig, strict:false, commonjs module
- `__mocks__/styleMock.js` — CSS mock
- `__mocks__/fileMock.js` — static asset mock

**Modified files (2):**
- `package.json` — added jest/ts-jest/jest-environment-jsdom/@types/jest/@testing-library/* + ts-node + 4 test scripts
- `tsconfig.json` — `src/__tests__` stays excluded (test coverage via tsconfig.test.json)

**Test results:** 8/8 pass. Both `tsc --noEmit` and `tsc -p tsconfig.test.json --noEmit` = 0 errors.
