# TradePilot AI — Project Audit

> Dibuat: 2026-09-10. Dokumen ini adalah ringkasan konteks untuk AI assistant lain agar bisa
> melanjutkan pengembangan tanpa membaca ulang seluruh codebase. Verifikasi ulang detail kritikal
> sebelum bertindak, terutama status migrasi/legacy yang disebut di bagian 8.

## 1. Struktur & Stack

```
tradepilot-ai/
├── backend/            FastAPI app (Python 3.12+ target, venv shows 3.14 runtime)
│   ├── app/            source (lihat peta modul di bawah)
│   ├── migrations/     Alembic, 27 revision files
│   └── tests/          169 file test (pytest)
├── worker/             Python background worker (queue consumer)
│   ├── app/            source
│   └── tests/          7 file test
├── frontend/           Next.js 16 + React 19 + TypeScript
│   └── src/            app/ (routes), features/, components/, lib/
├── infra/              docker/, deploy/, deployment/, nginx/
├── schemas/            JSON Schema untuk validasi output AI (fixtures, production, rebuild)
├── prompts/            prompt AI versioned (production/, rebuild/)
├── docs/               dokumentasi sangat lengkap (archive/, rebuild/, evidence-expansion/, v2/, ui-ux/, dll)
├── scripts/            backup/restore DB, e2e smoke test, fixture validator
├── storage/            evidence & file storage lokal
└── docker-compose.production.yml, Makefile
```

**Arsitektur**: Monorepo single-project, fullstack — 3 service terpisah (backend API, worker,
frontend), dikoordinasikan lewat PostgreSQL sebagai database + durable queue. Bukan
microservices penuh, lebih ke "modular monolith backend + dedicated worker".

**Stack & versi (dari config, bukan hanya README):**
- Backend: FastAPI ≥0.115, Python (`requires-python>=3.12`, venv aktif memakai 3.14),
  SQLAlchemy 2 (async, `asyncpg`), Alembic, `psycopg[binary]`, Pillow, bcrypt, `google-genai`,
  `openai`, `jsonschema`. Package manager: pip/hatchling (`pyproject.toml`), venv per-service (`.venv`).
- Worker: paket Python terpisah (`tradepilot-worker`), dependensi minim (SQLAlchemy, asyncpg,
  psycopg, pydantic-settings) — **tapi runtime-nya meng-import modul `app.*` milik backend**
  (lihat temuan §3).
- Frontend: Next.js 16.2.10, React 19.2.4, TypeScript 5, Tailwind CSS v4 (via
  `@tailwindcss/postcss`), Vitest 4 + Testing Library untuk test, ESLint 9. Package manager: npm
  (`package-lock.json`).
- Database: PostgreSQL, diakses async (`asyncpg`) dari app dan sync (`psycopg`) untuk Alembic.
- README menyebut target "Python 3.14" untuk backend — pyproject hanya mensyaratkan `>=3.12`;
  venv terpasang memang 3.14.

## 2. Entry Points & Flow

- Backend entry: [backend/app/main.py](backend/app/main.py) → `create_application()` di
  [backend/app/application.py](backend/app/application.py). Di sinilah semua middleware &
  router didaftarkan (lihat daftar lengkap router di §8).
- Worker entry: [worker/app/main.py](worker/app/main.py) → loop di
  [worker/app/runtime.py](worker/app/runtime.py), mengonsumsi tabel antrian
  `analysis_requests_v2` via `FOR UPDATE SKIP LOCKED`.
- Frontend entry: Next.js App Router di `frontend/src/app/` (routes: `login`, `sessions`,
  `sessions/[sessionId]/...` — analysis, close, history, initial-evidence, position-update,
  wait-update — `trade-workspace`, `evaluations`).

**Alur data (V2, arsitektur aktif menurut README):**
```
Frontend upload evidence → API route (trade_workspace/api) → service layer
  (trade_workspace/services/*) → insert row PENDING ke analysis_requests_v2
  → Worker klaim row (advisory lock, SKIP LOCKED) → panggil Gemini
  (trade_workspace/ai/gemini_adapter.py) → validasi output via JSON Schema
  (trade_workspace/ai/response_validator.py) → update state sesi (trade_session)
  → Frontend polling 5 detik membaca status.
```
Pola: layered/service-oriented (routes → schemas → services → models/repositories), bukan
MVC klasik. Backend memakai dependency injection FastAPI standar
([backend/app/api/dependencies.py](backend/app/api/dependencies.py)).

**Catatan penting**: Ada **dua generasi kode berdampingan** di `backend/app`:
- Legacy V1: `app/models/*`, `app/api/routes/{analyses,evidence,trade_actions,trade_sessions,...}.py`,
  `app/services/*`, `app/lifecycle/*`.
- Rebuild V2 (arsitektur resmi/aktif menurut README): `app/trade_workspace/*`.

Keduanya di-mount bersamaan di `application.py`. Legacy belum dihapus — lihat §8 untuk status
resmi rencana penghapusannya.

## 3. Dependensi

**Backend (utama):** fastapi, uvicorn, pydantic/pydantic-settings, sqlalchemy, asyncpg, psycopg,
alembic, Pillow, bcrypt, python-multipart, google-genai, openai, jsonschema, referencing.
Dev: pytest, pytest-asyncio, httpx, ruff, mypy.

**Worker (utama):** pydantic-settings, sqlalchemy, asyncpg, psycopg. Dev: pytest, ruff, mypy.

**Frontend (utama):** next, react, react-dom. Dev: tailwindcss v4, vitest, testing-library,
ajv/ajv-draft-04/ajv-formats (validasi schema di sisi client?), eslint.

**Temuan dependensi:**
- ⚠️ **Worker mengimpor kode backend lintas-paket tanpa deklarasi dependensi.** Menjalankan
  `worker/.venv/bin/pytest` gagal 3 test dengan `ModuleNotFoundError: No module named 'jsonschema'`
  karena `worker/tests/test_runtime.py` memuat `backend/app/validation/json_schema.py` yang
  butuh `jsonschema`, padahal `jsonschema` tidak ada di `worker/pyproject.toml`. Ini
  menunjukkan coupling implisit worker↔backend yang tidak eksplisit di dependency graph.
- Versi frontend relatif baru; `npm outdated` hanya menunjukkan selisih minor/patch
  (React 19.2.4→19.3.0, Next 16.2.10→16.3.4, TypeScript 5.9→7.0 major baru, vitest 4→5 major
  baru). Tidak ada indikasi kerentanan kritis dari daftar ini, tapi belum dijalankan
  `npm audit` / pengecekan CVE terhadap registry publik (tidak ada akses internet saat audit).
- Tidak ditemukan dependency yang jelas-jelas unused lewat inspeksi cepat; tidak dilakukan
  analisis unused-import menyeluruh (butuh tooling seperti `depcheck`/`vulture` untuk kepastian).

## 4. Konfigurasi & Environment

- Root [.env.example](.env.example): konfigurasi utama — `APP_ENV`, kredensial Postgres,
  `DATABASE_URL` (asyncpg) & `DATABASE_SYNC_URL` (psycopg untuk Alembic), pool settings,
  `API_HOST/PORT`, `LOG_LEVEL`, `WORKER_NAME`, `WORKER_POLL_INTERVAL_SECONDS`, `WEB_PORT`,
  `NEXT_PUBLIC_API_BASE_URL`, `EVIDENCE_STORAGE_BACKEND`/`EVIDENCE_STORAGE_PATH`,
  `GEMINI_API_KEY`/`GEMINI_MODEL`/`PROVIDER_ORDER`, `DEEPSEEK_API_KEY`.
- [backend/.env.example](backend/.env.example): subset lain — `ZAPI_API_KEY`/`ZAPI_BASE_URL`
  (integrasi market data pihak ketiga: Pluang/IDX/Stockbit via ZAPI), plus AI provider keys.
- File `.env` asli ada di root dan di `backend/` (tidak dibaca isinya — hanya nama key
  diverifikasi cocok dengan `.env.example`, tidak ada key mencurigakan di luar contoh).
- Docker: [docker-compose.production.yml](docker-compose.production.yml) mendefinisikan service
  `postgres`, `backend`, `worker`, `frontend`, `gateway`, plus volume `pgdata`/`evidence_data`.
  Compose dev lain ada di `infra/docker/compose.yml` (dipakai `Makefile` target `docker-*`).

**Menjalankan lokal:**
```bash
# Backend + worker test (butuh Postgres lokal)
DATABASE_SYNC_URL="postgresql+psycopg://user@localhost:5432/tradepilot_test" \
  backend/.venv/bin/pytest backend/tests/trade_workspace/

# Backend serve
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Migrasi
cd backend && alembic upgrade head   # atau `make migrate` dari root

# Frontend
cd frontend && npm install && npm run dev      # port 3001
cd frontend && npm run build && npm start
cd frontend && npm test                         # vitest run
cd frontend && npm run typecheck               # tsc --noEmit

# Docker
make docker-up / docker-down / docker-reset / docker-logs
```

## 5. Database & Data Model

**Skema aktif (V2, sesuai README):**
- `trade_sessions_v2` — sesi trading (satu posisi/keputusan dari awal sampai selesai)
- `analysis_requests_v2` — antrian durable untuk request analisis AI (state PENDING→PROCESSING)
- `evidence_uploads_v2` — evidence (orderbook, chart) yang diunggah
- `session_decisions_v2` — record keputusan BUY/WAIT/SKIP
- `positions_v2` — posisi terbuka
- `trade_closures_v2` — hasil penutupan posisi (realized PnL)

Model ORM V2 ada di [backend/app/trade_workspace/models/](backend/app/trade_workspace/models).

**Skema legacy (V1, masih ada, status penghapusan pending — lihat §8):**
`trade_sessions`, `evidence`, `evidence_batches`, `analysis`, `analysis_job`,
`context_summary`, `evaluation_record`, `provider_request`/`provider_response`,
`session_event`, `trade_action`, `trade_state`, `user`, `validation_attempt` — model di
[backend/app/models/](backend/app/models).

**Migrasi**: Alembic, 27 file revisi di `backend/migrations/versions/`. Ada file duplikat
mencurigakan: `8e4d747e19db_context_and_events.py` **dan**
`8e4d747e19db_context_and_events.py.bak` (revision ID sama, file `.bak` kemungkinan sisa
percobaan — sebaiknya dibersihkan/diverifikasi tidak dobel-apply).

## 6. Testing & CI/CD

- **Tidak ditemukan pipeline CI/CD** — tidak ada folder `.github/workflows`, tidak ada
  `.gitlab-ci.yml`, tidak ada config CI lain di root. Semua verifikasi saat ini manual
  (`make`, `pytest`, `npm test`).
- **Backend**: pytest, 169 file test, marker `database` untuk test yang butuh Postgres asli.
  Hasil audit menjalankan `pytest -m "not database"`:
  - 21 error koleksi di `tests/database/*` dan `tests/models/*` — **ImportError**:
    `tests/models/test_user.py` memanggil `create_async_engine_from_config` dari
    `app.database.session`, padahal fungsi itu **tidak ada lagi** di modul tersebut (isi modul
    sekarang hanya `_get_engine`, `get_engine`, `get_db_session`). Test-test ini basi/stale,
    kemungkinan besar sisa V1 yang belum diupdate mengikuti refactor `app/database`.
  - Setelah exclude direktori itu: **29 failed, 1366 passed, 3 skipped, 25 error** (dari total
    ~2424 test collected). File gagal: `tests/ai/test_prompt_registry.py`,
    `tests/ai/test_provider_contract_suite.py`, `tests/test_health.py`,
    `tests/test_schema_manifest.py`, `tests/test_schemas.py`. **Belum di-debug detail
    root cause** — perlu investigasi lanjutan sebelum mengklaim "testsuite hijau".
- **Worker**: 7 file test, `worker/.venv/bin/pytest` → **3 failed, 57 passed** karena
  `ModuleNotFoundError: jsonschema` (lihat §3, coupling worker→backend).
- **Frontend**: Vitest, 71 file test. `npm run typecheck` **bersih** (tsc --noEmit tanpa
  error). `npx vitest run` → **3 file failed (14 test), 68 file passed (1013 test)**:
  - [frontend/src/features/trade-workspace/api-url.test.ts](frontend/src/features/trade-workspace/api-url.test.ts) —
    bug nyata: URL request menjadi `.../api/api/v2/trade-sessions/...` (double `/api` prefix)
    dan body `"{}"` yang seharusnya `undefined` pada request tanpa body. Ini kemungkinan bug
    regresi di helper pembangun URL API trade-workspace, bukan sekadar test basi — perlu
    diperbaiki di kode aplikasi.
  - [frontend/src/__tests__/route-session-recovery.test.tsx](frontend/src/__tests__/route-session-recovery.test.tsx) dan
    [frontend/src/__tests__/cutover.test.tsx](frontend/src/__tests__/cutover.test.tsx) — 12 test gagal terkait
    pemulihan state route/sesi; belum didiagnosis root cause-nya secara mendalam.
- Ada juga `scripts/e2e_p9_smoke.py` (smoke test manual, bukan bagian pipeline otomatis) dan
  `scripts/validate_fixtures.py`.

## 7. Kualitas Kode

- **Konvensi**: Ruff untuk lint (target py312, line-length 99, `select = ["E","F","I","N","W"]`),
  format quote-style double. Mypy **strict mode** untuk backend & worker
  (`disallow_untyped_defs`, dll), dengan override longgar khusus untuk `tests.*` dan
  `app.schemas.manifest`. Frontend pakai ESLint 9 (`eslint-config-next`) + TypeScript strict
  (implisit dari `tsc --noEmit` bersih).
- **Tidak ada marker TODO/FIXME/HACK/XXX** di source `backend/app`, `worker/app`,
  `frontend/src` — disiplin kebersihan kode baik, tapi utang teknis didokumentasikan secara
  eksplisit di `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md` (lihat §8) alih-alih inline comment.
- **Tidak ditemukan hardcoded secret** pada pola pencarian umum (`api_key=`, `password=`,
  `secret=` diikuti literal panjang) di source backend/worker.
- Backend punya middleware keamanan eksplisit di
  [backend/app/api/security.py](backend/app/api/security.py): `SecurityHeadersMiddleware`,
  `CSRFProtectionMiddleware`, `RateLimitMiddleware`, plus `TrustedHostMiddleware`,
  `HTTPSRedirectMiddleware` (production only), CORS — pendekatan defense-in-depth cukup baik,
  tapi implementasi detail (allowlist origin, rate limit threshold) belum direview mendalam.
- **Technical debt terbesar yang teridentifikasi**: koeksistensi kode V1 (legacy) dan V2
  (rebuild) di backend yang sama. Ini meningkatkan permukaan bug (contoh nyata: test legacy
  yang basi karena API lama sudah berubah, lihat §6) dan risiko kebingungan untuk kontributor
  baru soal endpoint mana yang aktif dipakai.
- File migrasi duplikat `.bak` (§5) sebaiknya dibersihkan.

## 8. Status Fitur

Berdasarkan `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md` (dokumen governance resmi proyek) dan
riwayat commit terbaru:

- **Selesai (aktif dipakai)**: Arsitektur V2 rebuild penuh — durable queue
  (`analysis_requests_v2` + advisory lock), lifecycle DRAFT→ANALYZING→ANALYZED→
  BUY/WAIT/SKIP→OPEN_POSITION/WAITING/CLOSED_SKIPPED→CLOSE→CLOSED, integrasi Gemini,
  evidence upload, integrasi live market data (ZAPI: Stockbit intraday price feed — commit
  `e5465e9`), UI trade-workspace modern, archive/restore sesi closed/skipped, animasi loading
  UI (`4ec023a`), thesis generator AI dengan gaya bahasa kasual (`70fe572`).
- **Sedang dikerjakan / diputuskan ditunda**: Task ledger menyatakan
  *"Phase 11 remains deferred by product-owner decision"* dan pointer eksekusi saat ini adalah
  **Phase 12 — internal cleanup** untuk menghapus kode legacy V1, dipecah jadi
  P12-A (inventory legacy — selesai) → P12-B (verifikasi dependency/runtime — selesai) →
  P12-C (klasifikasi coupling V2 — selesai, belum ada penghapusan kode) →
  **P12-D — Incremental Safe Removal (task aktif saat ini, per dokumen)** → P12-E → P12-F.
- **Direncanakan tapi eksplisit "NOT IMPLEMENTED"** di ledger: sub-task P12.5a–P12.5g
  (hapus rute Partial Exit, requirement Closing Analysis lama, provider routing tak terpakai,
  transport registry lama, canonical normalizer tak terpakai, lifecycle transition lama,
  evaluation flow usang) dan P12.6 (Final Production-Like Acceptance).
- ⚠️ Perlu verifikasi ulang: dokumen ledger bisa jadi tidak 100% sinkron dengan commit terbaru
  di luar rebuild (mis. commit UI/AI terbaru `41e8794`, `4ec023a` tampak di luar penomoran
  P-task) — anggap ledger sebagai sumber kebenaran untuk *rebuild plan*, bukan seluruh
  aktivitas repo.
- Dokumentasi tambahan di `docs/evidence-expansion/` menunjukkan fitur "System-Acquired
  Evidence" (integrasi otomatis data foreign flow/broker flow via ZAPI Pluang/IDX/Stockbit)
  sudah diimplementasikan (commit `0c1f133`, `5eaf80b`, dst).

## 9. Dokumentasi

- README root **sangat lengkap dan up to date** — mencakup stack, repo map, diagram lifecycle
  V2, technical highlights, cara testing, dan language policy (UI harus Bahasa Indonesia,
  dokumentasi teknis harus Bahasa Inggris).
- `docs/` sangat kaya: `archive/` (spec V1 lama — PRD, arsitektur, domain model, dll, untuk
  referensi historis), `rebuild/` (task ledger otoritatif, task plan detail, verification
  docs), `evidence-expansion/`, `system-acquired-evidence/`, `ui-ux/`, `v2/`, `redesign/`,
  `visual-design/`, `zapi-api/`.
- **Gap dokumentasi**: tidak ada `CONTRIBUTING.md`, tidak ada dokumentasi API (OpenAPI/Swagger
  disebutkan tidak eksplisit — FastAPI otomatis expose `/docs` tapi tidak didokumentasikan
  cara aksesnya di README). Tidak ada `CHANGELOG.md` di root (histori fitur harus digali dari
  git log/task ledger). README `backend/` dan `frontend/` ada tapi lebih pendek/generik
  dibanding README root.

## 10. Rekomendasi Prioritas

1. **[Bug — Prioritas Tinggi]** Perbaiki bug double `/api/api/...` prefix pada URL request di
   fitur trade-workspace (test:
   [frontend/src/features/trade-workspace/api-url.test.ts](frontend/src/features/trade-workspace/api-url.test.ts)).
   Ini kemungkinan bug produksi nyata pada composisi base URL API, bukan sekadar test usang —
   verifikasi dulu di kode aplikasi terkait (kemungkinan file `api-url.ts` di fitur yang sama).
2. **[Bug/Debt — Tinggi]** Investigasi 12 test gagal di
   [route-session-recovery.test.tsx](frontend/src/__tests__/route-session-recovery.test.tsx) dan
   [cutover.test.tsx](frontend/src/__tests__/cutover.test.tsx) — berkaitan dengan pemulihan
   state sesi setelah refresh/route remount, area sensitif untuk UX produksi.
3. **[Debt — Tinggi]** Bereskan 21 error koleksi test backend V1 di `tests/database/*` dan
   `tests/models/*` (referensi `create_async_engine_from_config` yang sudah tidak ada) — baik
   dengan mengupdate test mengikuti API `app.database.session` saat ini, atau menghapusnya
   sekaligus sebagai bagian Phase 12 legacy removal (lebih konsisten dengan rencana resmi).
4. **[Debt — Tinggi]** Lanjutkan **Phase 12-D (Incremental Safe Removal)** sesuai
   `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md` — ini adalah task resmi aktif proyek saat ini.
   Menghapus kode V1 legacy akan otomatis membereskan sebagian besar item #3 di atas dan
   mengurangi permukaan bug.
5. **[Debt — Sedang]** Deklarasikan dependensi `jsonschema` (dan cek modul backend lain yang
   di-import worker) secara eksplisit di `worker/pyproject.toml`, atau — lebih baik — hilangkan
   coupling lintas-paket worker→backend dengan mengekstrak kode bersama (validasi schema) ke
   package/util terpisah yang dipakai keduanya.
6. **[Debt — Sedang]** Investigasi 29 test gagal + 25 error di
   `tests/ai/test_prompt_registry.py`, `tests/ai/test_provider_contract_suite.py`,
   `tests/test_health.py`, `tests/test_schema_manifest.py`, `tests/test_schemas.py` (di luar
   direktori legacy yang sudah diketahui basi).
7. **[Kebersihan — Rendah]** Hapus file migrasi duplikat
   `backend/migrations/versions/8e4d747e19db_context_and_events.py.bak`, dan pastikan tidak ada
   dua revision Alembic dengan ID sama yang bisa membingungkan riwayat migrasi.
8. **[Infra — Sedang]** Tambahkan pipeline CI/CD minimal (lint + typecheck + test) — saat ini
   semua verifikasi manual, sehingga regresi seperti bug di item #1 bisa lolos ke `main` tanpa
   terdeteksi otomatis.
9. **[Dokumentasi — Rendah]** Tambahkan `CONTRIBUTING.md` singkat dan catatan akses
   `/docs` (Swagger UI) FastAPI di README, plus `CHANGELOG.md` agar histori fitur tidak hanya
   hidup di git log/task ledger.
10. **[Nice-to-have]** Perbarui minor/patch dependency frontend yang sedikit tertinggal
    (`@testing-library/*`, `@types/*`, `eslint`) saat siklus maintenance berikutnya; evaluasi
    upgrade major TypeScript 5→7 dan Vitest 4→5 secara terpisah dan hati-hati (breaking changes).

---

## Ringkasan Eksekutif

TradePilot AI adalah workspace analisis trading berbasis AI (Next.js 16 + FastAPI + worker
Python + PostgreSQL), sedang dalam **rebuild arsitektur V2** yang sudah aktif diproduksi
(lifecycle sesi DRAFT→...→CLOSED, queue durable, integrasi Gemini & ZAPI market data). Kode V1
lama masih hidup berdampingan dengan V2 dan **secara resmi sedang dalam proses penghapusan
bertahap (Phase 12)** menurut dokumen governance proyek sendiri. Kualitas kode dasar cukup baik
(strict mypy, ruff, tanpa TODO liar, tanpa secret hardcoded, security middleware lengkap), tapi
audit menemukan **bug nyata** (double `/api` prefix di trade-workspace API client) dan
**test suite yang tidak sepenuhnya hijau**: 14 test frontend gagal, 29 gagal + 25 error di
backend (sebagian besar dari test V1 basi), 3 gagal di worker karena dependensi hilang. Tidak
ada CI/CD otomatis. Dokumentasi historis dan rencana kerja sangat lengkap dan menjadi sumber
kebenaran yang baik untuk melanjutkan pekerjaan. Prioritas utama: selesaikan Phase 12 cleanup,
perbaiki bug URL trade-workspace, dan tambahkan CI dasar.
