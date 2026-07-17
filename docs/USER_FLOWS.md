# **TradePilot AI — User Flows**

**Document:** `USER_FLOWS.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`  
**Purpose:** Define end-to-end user journeys, system responses, validation rules, lifecycle transitions, and edge cases.

---

## **1\. Document Purpose**

This document defines the user flows required for the TradePilot AI MVP.

It covers:

* session creation;  
* initial evidence upload;  
* initial analysis;  
* setup monitoring;  
* opening a position;  
* position updates;  
* stop-loss changes;  
* target changes;  
* additional entries;  
* partial exits;  
* full closure;  
* AI Trading Journal generation;  
* analysis history;  
* failure recovery;  
* session cancellation;  
* session archiving.

All user-facing labels and messages described in this document are intended to be displayed in Bahasa Indonesia.

All internal identifiers, enums, API fields, and engineering references remain in English.

---

# **2\. User Roles**

## **2.1 Primary User**

The MVP supports one authenticated user.

The user can:

* create Trade Sessions;  
* upload evidence;  
* run analysis;  
* open positions;  
* modify position parameters;  
* record exits;  
* view session history;  
* generate journals;  
* archive sessions;  
* configure AI providers.

## **2.2 System Actor**

The system performs:

* validation;  
* file storage;  
* lifecycle transitions;  
* context construction;  
* AI job execution;  
* structured-output validation;  
* thesis-state updates;  
* analysis versioning;  
* audit logging;  
* journal generation.

## **2.3 AI Provider Actor**

The configured AI provider performs:

* image understanding;  
* chart interpretation;  
* orderbook interpretation;  
* longitudinal reasoning;  
* structured-response generation;  
* journal generation.

The AI provider must not directly mutate Trade Session state.

All mutations must be performed by application logic after validation.

---

# **3\. Global User Flow Principles**

## **3.1 One Session, One Trade Story**

Every flow operates inside one Trade Session.

The user must create a new session for a new trade lifecycle, even when using the same ticker.

## **3.2 User-Controlled Position Changes**

The system must never automatically:

* open a position;  
* add an entry;  
* change a stop loss;  
* change a target;  
* record an exit;  
* close a position.

AI recommendations remain advisory until confirmed by the user.

## **3.3 Analysis Is Versioned**

Every successful analysis creates a new immutable analysis version.

## **3.4 Analysis Is Longitudinal**

Every update after initial analysis must use the relevant Trade Session history.

## **3.5 User-Facing Output Is in Bahasa Indonesia**

All user-facing AI narrative, warnings, and error messages must be displayed in Bahasa Indonesia.

---

# **4\. Global Navigation Flow**

## **4.1 Entry Point**

After authentication, the user lands on the main dashboard.

Primary navigation items:

* Dashboard  
* Session Aktif  
* Posisi Terbuka  
* Session Selesai  
* Jurnal Trading  
* Pengaturan

## **4.2 Main Dashboard Actions**

The user can:

* create a new Trade Session;  
* open an active session;  
* continue an incomplete draft;  
* review a position requiring an update;  
* open a recently completed journal;  
* search sessions.

## **4.3 Session Context Preservation**

When the user navigates away from a Trade Session:

* unsaved forms must warn the user;  
* uploaded files already confirmed must remain stored;  
* completed analysis must remain accessible;  
* current lifecycle state must remain unchanged.

---

# **5\. Flow UF-001 — User Login**

## **5.1 Goal**

Allow the user to securely access TradePilot AI.

## **5.2 Preconditions**

* User account exists.  
* Application is reachable.  
* Authentication service is healthy.

## **5.3 Main Flow**

1. User opens the login page.  
2. User enters email or username.  
3. User enters password.  
4. User selects **Masuk**.  
5. System validates credentials.  
6. System creates an authenticated session.  
7. System redirects the user to the dashboard.

## **5.4 Success Result**

The user sees the dashboard and can access private trading data.

## **5.5 Failure Cases**

### **Invalid Credentials**

System displays:

Email/username atau kata sandi tidak sesuai.

### **Too Many Failed Attempts**

System displays:

Terlalu banyak percobaan masuk. Silakan coba kembali beberapa saat lagi.

### **Authentication Service Failure**

System displays:

Sistem autentikasi sedang mengalami gangguan. Silakan coba kembali.

## **5.6 Audit Events**

* `LOGIN_SUCCEEDED`  
* `LOGIN_FAILED`  
* `LOGIN_RATE_LIMITED`

---

# **6\. Flow UF-002 — Create a New Trade Session**

## **6.1 Goal**

Create a dedicated workspace for one ticker and one trade lifecycle.

## **6.2 Preconditions**

* User is authenticated.  
* User is on the dashboard or session list.

## **6.3 Main Flow**

1. User selects **Buat Trade Session Baru**.  
2. System opens the session creation form.  
3. User enters:  
   * ticker;  
   * company name, optional;  
   * market;  
   * session title, optional;  
   * initial notes, optional.  
4. User selects **Buat Session**.  
5. System validates the ticker and required fields.  
6. System creates a new Trade Session with status `DRAFT`.  
7. System creates a `SESSION_CREATED` timeline event.  
8. System redirects the user to the new Trade Session page.

## **6.4 Default Session Values**

* status: `DRAFT`  
* active thesis: null  
* active position: null  
* latest analysis: null  
* archive status: false  
* primary language: Indonesian

## **6.5 Validation Rules**

The session cannot be created when:

* ticker is empty;  
* ticker format is invalid;  
* market is missing;  
* ticker exceeds configured length.

The system may allow multiple sessions for the same ticker.

## **6.6 Success Result**

A dedicated Trade Session page exists.

## **6.7 Failure Cases**

### **Invalid Ticker Format**

Format ticker tidak valid. Periksa kembali ticker yang dimasukkan.

### **Server Failure**

Trade Session belum berhasil dibuat. Data Anda belum disimpan.

## **6.8 Audit Events**

* `SESSION_CREATED`

---

# **7\. Flow UF-003 — Continue an Incomplete Draft**

## **7.1 Goal**

Allow the user to complete a session whose initial evidence is incomplete.

## **7.2 Preconditions**

* Session status is `DRAFT`.

## **7.3 Main Flow**

1. User opens the draft session.  
2. System displays the initial evidence checklist.  
3. Missing required evidence is highlighted.  
4. User uploads missing evidence.  
5. System validates each upload.  
6. When all required evidence exists, system updates status to `READY_FOR_ANALYSIS`.  
7. System displays the **Jalankan Analisis Awal** action.

## **7.4 Required Evidence Checklist**

* Orderbook screenshot  
* Three-month chart  
* Six-month chart

## **7.5 Success Result**

The session becomes ready for initial analysis.

---

# **8\. Flow UF-004 — Upload Initial Evidence**

## **8.1 Goal**

Upload the minimum evidence required for initial analysis.

## **8.2 Preconditions**

* Session status is `DRAFT` or `READY_FOR_ANALYSIS`.  
* No initial analysis is currently processing.

## **8.3 Main Flow**

1. User selects an evidence slot.  
2. User chooses a file.  
3. System validates:  
   * MIME type;  
   * file extension;  
   * file size;  
   * image readability;  
   * duplicate hash when available.  
4. System uploads the file.  
5. System stores the original file.  
6. System creates preview and thumbnail variants.  
7. System creates an evidence record.  
8. System adds an `EVIDENCE_UPLOADED` timeline event.  
9. System updates the evidence checklist.  
10. When all required evidence exists, status becomes `READY_FOR_ANALYSIS`.

## **8.4 Optional User Input**

For each upload, user may provide:

* market timestamp;  
* caption;  
* source note;  
* image description.

## **8.5 Duplicate Handling**

When an identical file already exists in the same session, the system displays:

File yang sama sudah pernah diunggah ke session ini.

The user may:

* cancel;  
* keep as a separate timestamped update when explicitly allowed.

## **8.6 Failure Cases**

### **Unsupported File**

Jenis file tidak didukung. Unggah gambar dengan format yang diperbolehkan.

### **File Too Large**

Ukuran file melebihi batas yang diperbolehkan.

### **Upload Failure**

File belum berhasil diunggah. Silakan coba kembali.

### **Corrupted Image**

Gambar tidak dapat dibaca. Silakan unggah file lain.

---

# **9\. Flow UF-005 — Replace Incorrect Initial Evidence Before Analysis**

## **9.1 Goal**

Allow the user to correct initial evidence before the first analysis.

## **9.2 Preconditions**

* Initial analysis has not been completed.  
* Session status is `DRAFT` or `READY_FOR_ANALYSIS`.

## **9.3 Main Flow**

1. User opens the evidence item.  
2. User selects **Tandai Salah dan Ganti**.  
3. System asks for confirmation.  
4. User confirms.  
5. Existing evidence is marked `SUPERSEDED`.  
6. User uploads the replacement.  
7. Replacement is linked to the superseded evidence.  
8. Timeline records the correction.  
9. Session readiness is recalculated.

## **9.4 Rule**

The old evidence remains in audit history and is not used as active initial evidence.

---

# **10\. Flow UF-006 — Run Initial Analysis**

## **10.1 Goal**

Generate the first structured AI analysis for the Trade Session.

## **10.2 Preconditions**

* Session status is `READY_FOR_ANALYSIS`.  
* All required evidence exists.  
* No analysis job is currently active.  
* AI provider configuration is valid.

## **10.3 Main Flow**

1. User selects **Jalankan Analisis Awal**.  
2. System displays the evidence that will be used.  
3. User confirms the analysis request.  
4. System creates an idempotency key.  
5. System stores the current stable state.  
6. System changes temporary status to `ANALYZING`.  
7. System creates an analysis job with state `QUEUED`.  
8. System adds `ANALYSIS_QUEUED` to the timeline.  
9. Worker changes job state to `PROCESSING`.  
10. System constructs the initial analysis context.  
11. AI provider analyzes the images and context.  
12. AI returns structured output.  
13. System parses and validates the response.  
14. System validates Indonesian narrative fields.  
15. System validates required analysis sections.  
16. System creates:  
    * initial analysis version;  
    * canonical thesis;  
    * support and resistance state;  
    * confidence state;  
    * probability state;  
    * recommended trading plan.  
17. System changes status to `WATCHING`.  
18. System adds:  
    * `INITIAL_ANALYSIS_GENERATED`;  
    * `THESIS_CREATED`.  
19. System notifies the user that analysis is complete.  
20. User sees the structured analysis page.

## **10.4 Initial Analysis UI Sections**

* Ringkasan Eksekutif  
* Ringkasan Hari Ini  
* Analisis Orderbook  
* Analisis Chart 3 Bulan  
* Analisis Chart 6 Bulan  
* Support dan Resistance  
* Rencana Entry  
* Stop Loss  
* Target Profit  
* Confidence  
* Probability  
* Skenario Bullish  
* Skenario Netral  
* Skenario Bearish  
* Risiko dan Data yang Kurang  
* Tindakan Berikutnya

## **10.5 Success Result**

The session has:

* one valid initial analysis;  
* one canonical active thesis;  
* one current trading plan;  
* status `WATCHING`.

## **10.6 Failure Cases**

### **Provider Timeout**

1. Job becomes `FAILED`.  
2. Session returns to `READY_FOR_ANALYSIS`.  
3. Existing evidence remains unchanged.  
4. User sees:

Analisis belum selesai karena AI provider tidak merespons tepat waktu. Anda dapat mencoba kembali.

### **Invalid Structured Output**

1. System attempts configured repair or retry.  
2. If still invalid, job becomes `FAILED`.  
3. Invalid response does not become canonical.  
4. User sees:

Hasil analisis belum dapat digunakan karena format respons AI tidak valid.

### **Indonesian Output Validation Failure**

System may retry with a language-correction prompt.

If correction fails:

Hasil analisis belum dapat ditampilkan karena bahasa output tidak sesuai konfigurasi.

### **Missing Provider Configuration**

AI provider belum dikonfigurasi. Periksa Pengaturan AI sebelum menjalankan analisis.

---

# **11\. Flow UF-007 — View Initial Analysis**

## **11.1 Goal**

Review the initial setup and determine the next action.

## **11.2 Preconditions**

* Session status is `WATCHING`.  
* Initial analysis exists.

## **11.3 Main Flow**

1. User opens the Trade Session.  
2. System displays the latest analysis.  
3. System prominently displays:  
   * thesis status;  
   * confidence;  
   * target probability;  
   * recommended entry zone;  
   * stop loss;  
   * targets;  
   * next action.  
4. User reviews evidence and analysis.  
5. User may:  
   * upload an update;  
   * add a note;  
   * wait;  
   * mark the position as open;  
   * cancel the setup.

## **11.4 Evidence Traceability**

For each analysis section, the user should be able to inspect related evidence when available.

---

# **12\. Flow UF-008 — Add a Watching Update**

## **12.1 Goal**

Reassess a setup before entry using new evidence.

## **12.2 Preconditions**

* Session status is `WATCHING`.  
* Initial analysis exists.

## **12.3 Main Flow**

1. User selects **Tambah Update**.  
2. User selects update classification:  
   * Morning Update;  
   * Midday Update;  
   * Closing Update;  
   * Custom Update.  
3. User uploads at least one new evidence item.  
4. User may add:  
   * latest price;  
   * market values;  
   * notes;  
   * new chart.  
5. System validates and stores evidence.  
6. User selects **Analisis Update**.  
7. System queues a follow-up analysis job.  
8. Context builder includes:  
   * initial thesis;  
   * latest valid analysis;  
   * previous comparable evidence;  
   * current setup plan;  
   * current evidence.  
9. AI produces structured watching analysis.  
10. System validates the output.  
11. System compares the proposed thesis state with canonical state.  
12. System creates a new analysis version.  
13. System updates canonical state when valid.  
14. System restores status to `WATCHING`.  
15. User sees the updated analysis.

## **12.4 Required Output**

* Ringkasan Kondisi Terbaru  
* Analisis Orderbook Terbaru  
* Perubahan Sejak Update Sebelumnya  
* Kualitas Setup  
* Realisme Entry  
* Status Thesis  
* Confidence Terbaru  
* Probability Terbaru  
* Trading Plan Terbaru  
* Kondisi Entry atau Pembatalan

---

# **13\. Flow UF-009 — No Material Change in Watching Update**

## **13.1 Goal**

Avoid artificial changes when the setup is broadly unchanged.

## **13.2 Main Flow**

1. User uploads a new orderbook.  
2. AI compares it with previous context.  
3. AI determines no material change exists.  
4. Analysis explicitly states:  
   * condition remains broadly unchanged;  
   * thesis status remains unchanged;  
   * no target or stop revision is required;  
   * next checkpoint remains the same.  
5. System records a new analysis version without manufacturing thesis changes.

---

# **14\. Flow UF-010 — Cancel a Setup Before Entry**

## **14.1 Goal**

Close a setup that the user no longer wants to pursue.

## **14.2 Preconditions**

* Session status is `WATCHING` or `DRAFT`.  
* No historical position entry exists.

## **14.3 Main Flow**

1. User selects **Batalkan Setup**.  
2. System asks for a cancellation reason.  
3. User selects or enters:  
   * setup no longer valid;  
   * missed entry;  
   * risk became unacceptable;  
   * user changed plan;  
   * other.  
4. System requests confirmation.  
5. User confirms.  
6. System changes status to `CANCELLED`.  
7. System records `SETUP_CANCELLED`.  
8. Session remains available in history.  
9. Optional closing note may be added.

## **14.4 Restriction**

A session with an entry record cannot be cancelled.

---

# **15\. Flow UF-011 — Mark Position as Open**

## **15.1 Goal**

Convert a watched setup into an active position.

## **15.2 Preconditions**

* Session status is `WATCHING`.  
* Initial analysis exists.  
* Active thesis is not `INVALIDATED`.

## **15.3 Main Flow**

1. User selects **Tandai sebagai Posisi Terbuka**.  
2. System opens the position-entry form.  
3. User enters:  
   * actual entry price;  
   * entry timestamp;  
   * quantity, optional;  
   * stop loss;  
   * at least one target;  
   * entry notes, optional.  
4. System displays:  
   * planned entry;  
   * actual entry;  
   * difference from plan;  
   * current thesis;  
   * current invalidation level.  
5. User confirms.  
6. System validates required values.  
7. System creates:  
   * position record;  
   * first entry record;  
   * active stop;  
   * active target records;  
   * entry thesis snapshot.  
8. System changes status to `OPEN_POSITION`.  
9. System adds `POSITION_OPENED` to the timeline.  
10. System displays the open-position workspace.

## **15.4 Warning Cases**

### **Actual Entry Is Above Chase Limit**

System displays:

Harga entry berada di atas batas mengejar harga yang direkomendasikan. Pastikan Anda memahami perubahan risk-to-reward.

User may still confirm.

### **Entry Is Near Stop Loss**

Jarak antara harga entry dan stop loss sangat sempit atau tidak konsisten. Periksa kembali data posisi.

### **Thesis Is Under Review**

Thesis saat ini masih dalam status ditinjau. Membuka posisi pada kondisi ini memiliki ketidakpastian lebih tinggi.

## **15.5 Blocked Case**

If thesis status is `INVALIDATED`, system must block direct opening unless the user creates a new session.

---

# **16\. Flow UF-012 — Open Position Dashboard View**

## **16.1 Goal**

Provide immediate visibility into active position health.

## **16.2 Main View**

The page must prominently display:

* ticker;  
* session status;  
* position health;  
* thesis status;  
* average entry;  
* latest price, if available;  
* unrealized result;  
* active stop loss;  
* active targets;  
* distance to stop;  
* distance to target;  
* confidence;  
* key probabilities;  
* latest recommended action;  
* last update time.

## **16.3 Primary Actions**

* Tambah Update  
* Tambah Entry  
* Ubah Stop Loss  
* Ubah Target  
* Catat Partial Exit  
* Tutup Posisi  
* Tambah Catatan

---

# **17\. Flow UF-013 — Add Morning Open-Position Update**

## **17.1 Goal**

Assess the position near the start of the trading session.

## **17.2 Preconditions**

* Status is `OPEN_POSITION` or `PARTIALLY_CLOSED`.

## **17.3 Main Flow**

1. User selects **Tambah Update Pagi**.  
2. User uploads the latest orderbook screenshot.  
3. User may enter latest market values.  
4. User may add a note.  
5. System stores evidence with classification `MORNING`.  
6. User runs analysis.  
7. Context includes:  
   * initial thesis;  
   * current thesis;  
   * prior closing update when available;  
   * active position;  
   * current stop;  
   * active targets;  
   * latest orderbook.  
8. AI generates open-position analysis.  
9. System validates and stores the analysis.  
10. User sees a trading plan for the morning-to-midday period.

## **17.4 Required Focus**

* overnight continuity;  
* opening pressure;  
* initial bid support;  
* opening offer pressure;  
* gap behavior when data exists;  
* morning risk;  
* plan until midday.

---

# **18\. Flow UF-014 — Add Midday Open-Position Update**

## **18.1 Goal**

Compare midday conditions with the morning state.

## **18.2 Main Flow**

1. User selects **Tambah Update Siang**.  
2. User uploads the latest orderbook.  
3. System links the update to the current trading date.  
4. AI compares:  
   * morning evidence;  
   * morning analysis;  
   * initial thesis;  
   * current position.  
5. Analysis explains:  
   * whether bid support strengthened or weakened;  
   * whether offers were absorbed;  
   * whether target realism changed;  
   * whether the stop remains appropriate;  
   * plan until market close.

## **18.3 Required Output**

The analysis must explicitly answer:

* Apa yang berubah sejak pagi?  
* Apakah posisi masih sehat?  
* Apakah target masih realistis?  
* Apakah risiko menyentuh stop meningkat?  
* Apa rencana sampai penutupan?

---

# **19\. Flow UF-015 — Add Closing Open-Position Update**

## **19.1 Goal**

Evaluate the position after or near market close and prepare the next-day plan.

## **19.2 Main Flow**

1. User selects **Tambah Update Penutupan**.  
2. User uploads the closing orderbook.  
3. User may enter final OHLC and average values.  
4. AI compares:  
   * morning;  
   * midday;  
   * closing;  
   * previous trading day;  
   * active position.  
5. System stores the closing analysis.  
6. User sees:  
   * end-of-day assessment;  
   * daily thesis status;  
   * target realism;  
   * stop-risk assessment;  
   * next-trading-day plan.

## **19.3 Required Output**

* Ringkasan Hari Ini  
* Perubahan dari Pagi ke Penutupan  
* Kondisi Orderbook Penutupan  
* Kesehatan Posisi  
* Status Thesis  
* Realisme Target  
* Risiko Overnight  
* Trading Plan Besok

---

# **20\. Flow UF-016 — Add Custom Open-Position Update**

## **20.1 Goal**

Allow updates outside standard morning, midday, or closing classifications.

## **20.2 Main Flow**

1. User selects **Update Khusus**.  
2. User enters a label or reason.  
3. User uploads evidence.  
4. User adds notes when needed.  
5. System records a custom timestamp.  
6. AI uses the same longitudinal analysis rules.  
7. Output explains why this update matters.

---

# **21\. Flow UF-017 — Thesis Strengthens**

## **21.1 Goal**

Update canonical thesis state when new evidence materially confirms the setup.

## **21.2 Main Flow**

1. AI returns proposed thesis status `STRENGTHENING`.  
2. System verifies:  
   * supporting evidence exists;  
   * reason is present;  
   * no contradiction with critical state.  
3. System creates a thesis version.  
4. Canonical thesis status becomes `STRENGTHENING`.  
5. Timeline records `THESIS_STRENGTHENED`.  
6. Analysis explains:  
   * what strengthened;  
   * probability changes;  
   * whether target remains or changes;  
   * whether stop may be tightened.

## **21.3 User Control**

Any stop or target change remains a recommendation until confirmed by the user.

---

# **22\. Flow UF-018 — Thesis Weakens but Remains Valid**

## **22.1 Goal**

Warn the user without prematurely invalidating the trade.

## **22.2 Main Flow**

1. AI returns `INTACT_BUT_WEAKENING`.  
2. System validates the weakening reasons.  
3. Canonical state is updated.  
4. Timeline records `THESIS_WEAKENED`.  
5. UI displays a visible warning.  
6. Analysis explains:  
   * what weakened;  
   * what remains valid;  
   * what level must hold;  
   * what would restore strength;  
   * what would trigger review or invalidation.

---

# **23\. Flow UF-019 — Thesis Under Review**

## **23.1 Goal**

Handle material uncertainty while confirmation is pending.

## **23.2 Main Flow**

1. AI returns `UNDER_REVIEW`.  
2. System verifies that conflicting or incomplete evidence is documented.  
3. UI displays a high-attention status.  
4. Analysis prioritizes:  
   * unresolved technical condition;  
   * required confirmation;  
   * defensive action;  
   * next evidence needed.  
5. Timeline records `THESIS_UNDER_REVIEW`.  
6. The next analysis must explicitly resolve or continue the review state.

---

# **24\. Flow UF-020 — Thesis Invalidated**

## **24.1 Goal**

Warn the user when the original setup no longer holds.

## **24.2 Main Flow**

1. AI proposes status `INVALIDATED`.  
2. System validates:  
   * specific invalidation condition;  
   * supporting evidence;  
   * technical explanation;  
   * impact on current plan.  
3. System creates a thesis version.  
4. Canonical status becomes `INVALIDATED`.  
5. Timeline records `THESIS_INVALIDATED`.  
6. UI displays a critical warning.  
7. Analysis must:  
   * stop treating the previous base case as active;  
   * reassess exit risk;  
   * explain defensive action;  
   * avoid recommending a wider stop to preserve the position.

## **24.3 User Control**

The system does not automatically close the position.

The user must record the actual exit.

---

# **25\. Flow UF-021 — Contradictory AI Analysis**

## **25.1 Goal**

Prevent unsupported AI output from replacing canonical state.

## **25.2 Main Flow**

1. AI output materially contradicts canonical state.  
2. Contradiction validator checks whether a valid explanation exists.  
3. If explanation is sufficient:  
   * analysis may become canonical;  
   * change is versioned.  
4. If explanation is insufficient:  
   * result is stored as non-canonical or rejected;  
   * previous canonical state remains active;  
   * system retries when configured.  
5. User sees:

Hasil analisis terbaru belum dijadikan acuan utama karena terdapat perubahan yang belum memiliki alasan teknikal yang cukup.

---

# **26\. Flow UF-022 — Update Stop Loss**

## **26.1 Goal**

Allow the user to change the active stop loss while preserving history.

## **26.2 Preconditions**

* Status is `OPEN_POSITION` or `PARTIALLY_CLOSED`.

## **26.3 Main Flow**

1. User selects **Ubah Stop Loss**.  
2. System displays:  
   * current stop;  
   * current entry;  
   * estimated downside;  
   * current thesis invalidation level.  
3. User enters:  
   * new stop;  
   * reason.  
4. System calculates risk impact.  
5. If the stop is wider, system displays a warning.  
6. User confirms.  
7. System closes the previous active stop record.  
8. System creates a new active stop record.  
9. System adds `STOP_LOSS_CHANGED`.  
10. Canonical position state is updated.  
11. Future analyses use the new stop.

## **26.4 Wider Stop Warning**

Stop loss baru memperbesar risiko posisi. Pastikan perubahan ini memiliki alasan teknikal, bukan hanya untuk menghindari realisasi kerugian.

## **26.5 Validation**

The system should reject:

* zero or negative stop;  
* unchanged value without reason;  
* invalid numeric format.

---

# **27\. Flow UF-023 — Apply AI-Recommended Stop Change**

## **27.1 Goal**

Allow the user to apply a stop change proposed by the AI.

## **27.2 Main Flow**

1. AI analysis displays a proposed stop adjustment.  
2. User selects **Terapkan Rekomendasi Stop**.  
3. System opens the stop-change form prefilled with:  
   * proposed stop;  
   * AI reason;  
   * related analysis version.  
4. User reviews and confirms.  
5. System records the user-confirmed change.  
6. Timeline links the event to the AI recommendation.

## **27.3 Rule**

AI recommendation alone must not mutate the stop.

---

# **28\. Flow UF-024 — Update Target Profit**

## **28.1 Goal**

Allow the user to modify active target levels.

## **28.2 Main Flow**

1. User selects **Ubah Target**.  
2. System displays current targets.  
3. User may:  
   * modify a target;  
   * add a target;  
   * deactivate a target.  
4. User enters a reason.  
5. System displays risk-to-reward impact.  
6. User confirms.  
7. System versions the target records.  
8. Timeline records `TARGET_CHANGED`.  
9. Future analyses use the updated targets.

## **28.3 Warning**

When lowering a target while thesis is invalidated:

Thesis saat ini telah tidak valid. Menurunkan target tidak menggantikan kebutuhan untuk menilai risiko keluar dari posisi.

---

# **29\. Flow UF-025 — Add an Additional Entry**

## **29.1 Goal**

Record an additional position entry within the same thesis.

## **29.2 Preconditions**

* Status is `OPEN_POSITION` or `PARTIALLY_CLOSED`.  
* Position remains active.  
* Session thesis is not `INVALIDATED`.

## **29.3 Main Flow**

1. User selects **Tambah Entry**.  
2. System displays:  
   * current average entry;  
   * active quantity;  
   * active stop;  
   * active targets;  
   * current thesis status.  
3. User enters:  
   * additional entry price;  
   * timestamp;  
   * quantity, optional;  
   * reason.  
4. System determines:  
   * averaging up;  
   * averaging down;  
   * neutral addition.  
5. System calculates the new weighted average when quantity exists.  
6. If averaging down, system displays a stronger warning.  
7. User confirms.  
8. System creates an entry record.  
9. System updates position average.  
10. Timeline records `ADDITIONAL_ENTRY_RECORDED`.  
11. Future analyses use the new average entry.

## **29.4 Averaging Down Warning**

Entry tambahan ini menurunkan harga rata-rata posisi. Pastikan thesis masih valid dan total risiko terhadap stop loss tetap dapat diterima.

## **29.5 Blocked Case**

When thesis status is `INVALIDATED`, the system must block additional entry.

---

# **30\. Flow UF-026 — Record Partial Exit**

## **30.1 Goal**

Record a partial sale while keeping the remaining position active.

## **30.2 Preconditions**

* Position has active quantity.  
* Exit quantity is less than active quantity.

## **30.3 Main Flow**

1. User selects **Catat Partial Exit**.  
2. System displays current position.  
3. User enters:  
   * quantity sold;  
   * exit price;  
   * exit timestamp;  
   * reason;  
   * notes, optional.  
4. System validates quantity.  
5. System calculates:  
   * realized result;  
   * remaining quantity;  
   * remaining cost basis.  
6. User confirms.  
7. System creates an exit record.  
8. Status becomes `PARTIALLY_CLOSED`.  
9. Timeline records `PARTIAL_EXIT_RECORDED`.  
10. System displays the remaining position state.  
11. Future analysis evaluates only the remaining active position while considering the partial exit history.

## **30.4 Common Reasons**

* TP1 reached;  
* reduce risk;  
* resistance pressure;  
* thesis weakening;  
* manual discretion;  
* other.

---

# **31\. Flow UF-027 — Apply Partial Profit Recommendation**

## **31.1 Goal**

Allow the user to record a partial exit proposed by AI.

## **31.2 Main Flow**

1. AI recommends partial profit.  
2. User selects **Catat Partial Profit**.  
3. System opens the partial-exit form.  
4. Related AI reason is prefilled.  
5. User enters actual quantity, price, and time.  
6. User confirms.  
7. System records the actual partial exit.

## **31.3 Rule**

The system must distinguish between:

* recommended partial exit;  
* actual executed partial exit.

---

# **32\. Flow UF-028 — Close Position at Take Profit**

## **32.1 Goal**

Fully close a position because the target was achieved.

## **32.2 Preconditions**

* Active quantity exists.

## **32.3 Main Flow**

1. User selects **Tutup Posisi**.  
2. User selects reason **Take Profit**.  
3. User enters:  
   * final exit price;  
   * final exit timestamp;  
   * quantity;  
   * notes, optional.  
4. System validates that the quantity closes the remaining position.  
5. System calculates final result.  
6. User confirms.  
7. System creates the final exit record.  
8. Status becomes `CLOSED_TAKE_PROFIT`.  
9. Timeline records `POSITION_CLOSED_TAKE_PROFIT`.  
10. System queues closing analysis.  
11. Journal becomes eligible for generation.

---

# **33\. Flow UF-029 — Close Position at Stop Loss**

## **33.1 Goal**

Fully close a position because the stop loss was reached or executed.

## **33.2 Main Flow**

1. User selects **Tutup Posisi**.  
2. User selects reason **Stop Loss**.  
3. User enters actual exit details.  
4. System compares actual exit with active stop.  
5. System calculates slippage when quantity and values are available.  
6. User confirms.  
7. Status becomes `CLOSED_STOP_LOSS`.  
8. Timeline records `POSITION_CLOSED_STOP_LOSS`.  
9. System queues closing analysis.  
10. Journal becomes eligible.

## **33.3 Additional Journal Data**

The system should preserve:

* active stop at the time;  
* actual exit;  
* difference;  
* whether the user exited according to plan.

---

# **34\. Flow UF-030 — Close Position Manually**

## **34.1 Goal**

Fully close a position for a reason other than direct TP or SL execution.

## **34.2 Main Flow**

1. User selects **Tutup Posisi**.  
2. User selects **Manual Exit**.  
3. User chooses or enters:  
   * thesis invalidated;  
   * risk reduction;  
   * market condition changed;  
   * time-based exit;  
   * discretionary exit;  
   * other.  
4. User enters final exit details.  
5. System calculates final result.  
6. User confirms.  
7. Status becomes `CLOSED_MANUAL`.  
8. Timeline records `POSITION_CLOSED_MANUAL`.  
9. Closing analysis is queued.

---

# **35\. Flow UF-031 — Attempt to Close More Than Remaining Quantity**

## **35.1 Goal**

Protect position data integrity.

## **35.2 Flow**

1. User enters exit quantity greater than remaining quantity.  
2. System blocks submission.  
3. System displays:

Jumlah yang dijual melebihi sisa posisi aktif.

---

# **36\. Flow UF-032 — Generate Closing Analysis**

## **36.1 Goal**

Create an immediate post-exit evaluation before the full journal.

## **36.2 Preconditions**

* Position is fully closed.  
* A final exit record exists.

## **36.3 Main Flow**

1. System queues a closing analysis.  
2. Context includes:  
   * final position result;  
   * exit reason;  
   * active thesis before exit;  
   * latest analysis;  
   * important timeline events;  
   * entry and exit data.  
3. AI generates:  
   * exit summary;  
   * final thesis assessment;  
   * exit-quality assessment;  
   * plan-compliance assessment;  
   * preliminary lessons.  
4. System validates and stores the result.  
5. User sees the closing analysis.  
6. Journal generation begins automatically or becomes user-triggerable according to configuration.

---

# **37\. Flow UF-033 — Generate AI Trading Journal**

## **37.1 Goal**

Convert the complete session into a structured post-trade journal.

## **37.2 Preconditions**

* Session is fully closed.  
* Final position result exists.  
* No journal job is currently processing.

## **37.3 Main Flow**

1. User selects **Buat AI Trading Journal**, or automatic generation begins.  
2. System builds full-session context.  
3. Context includes:  
   * all initial evidence;  
   * all meaningful update evidence;  
   * all analysis versions;  
   * thesis history;  
   * entries;  
   * exits;  
   * stop changes;  
   * target changes;  
   * user notes;  
   * final result.  
4. AI generates structured journal output.  
5. System validates:  
   * Bahasa Indonesia narrative;  
   * hindsight separation;  
   * required journal sections;  
   * no rewritten history.  
6. System creates an immutable journal version.  
7. Timeline records `JOURNAL_GENERATED`.  
8. User sees the final AI Trading Journal.

## **37.4 Journal Sections**

* Ringkasan Trade  
* Review Thesis Awal  
* Perjalanan Thesis  
* Review Entry  
* Review Manajemen Posisi  
* Review Exit  
* Disiplin terhadap Trading Plan  
* Evaluasi Analisis AI  
* Hal yang Berjalan Baik  
* Hal yang Perlu Diperbaiki  
* Pelajaran Utama  
* Checklist untuk Trade Berikutnya  
* Refleksi User

---

# **38\. Flow UF-034 — Add User Reflection to Journal**

## **38.1 Goal**

Allow the user to add personal observations after closure.

## **38.2 Main Flow**

1. User opens the journal.  
2. User selects **Tambah Refleksi Pribadi**.  
3. User may enter:  
   * emotional state;  
   * reason for entry;  
   * reason for exit;  
   * mistake;  
   * lesson;  
   * rating;  
   * final note.  
4. User saves.  
5. System stores the reflection separately from AI-generated content.  
6. Timeline records `USER_REFLECTION_ADDED`.

## **38.3 Rule**

User reflection must not overwrite the AI journal.

---

# **39\. Flow UF-035 — View Analysis History**

## **39.1 Goal**

Review every analysis version in chronological order.

## **39.2 Main Flow**

1. User opens **Riwayat Analisis**.  
2. System displays:  
   * version number;  
   * timestamp;  
   * update classification;  
   * thesis status;  
   * confidence;  
   * target probability;  
   * recommended action.  
3. User selects a version.  
4. System displays:  
   * complete analysis;  
   * evidence used;  
   * provider;  
   * model;  
   * prompt version;  
   * schema version.

---

# **40\. Flow UF-036 — Compare Two Analysis Versions**

## **40.1 Goal**

Understand how the analysis evolved.

## **40.2 Main Flow**

1. User selects **Bandingkan Versi**.  
2. User chooses two analysis versions.  
3. System displays a structured comparison.  
4. Comparison includes:  
   * market summary;  
   * orderbook;  
   * support;  
   * resistance;  
   * thesis;  
   * confidence;  
   * probabilities;  
   * target realism;  
   * recommended action.  
5. User can open related evidence.

## **40.3 UI Requirement**

Differences must be shown as structured changes rather than raw text diff only.

---

# **41\. Flow UF-037 — View Evidence History**

## **41.1 Goal**

Inspect all uploaded evidence chronologically.

## **41.2 Main Flow**

1. User opens the evidence gallery.  
2. User filters by:  
   * type;  
   * date;  
   * update classification;  
   * active or superseded.  
3. User opens an evidence item.  
4. System displays:  
   * original image;  
   * timestamp;  
   * caption;  
   * extraction result;  
   * related analysis versions.

---

# **42\. Flow UF-038 — Mark Evidence as Incorrect**

## **42.1 Goal**

Prevent incorrect evidence from being used in future analysis.

## **42.2 Main Flow**

1. User opens evidence details.  
2. User selects **Tandai sebagai Salah**.  
3. User enters a reason.  
4. System asks whether the evidence should be excluded from future context.  
5. User confirms.  
6. Evidence is marked `INVALIDATED` or `EXCLUDED`.  
7. Timeline records `EVIDENCE_EXCLUDED`.  
8. Existing historical analyses remain unchanged.  
9. Future context builders exclude the evidence.

---

# **43\. Flow UF-039 — Retry Failed Analysis**

## **43.1 Goal**

Recover from provider, parsing, or validation failures.

## **43.2 Main Flow**

1. User sees a failed analysis job.  
2. User opens failure details.  
3. System displays a user-friendly explanation.  
4. User selects **Coba Lagi**.  
5. System creates a retry attempt linked to the original job.  
6. Same idempotency scope prevents duplicate canonical output.  
7. Job processes again.  
8. On success, one analysis version becomes canonical.  
9. Timeline records `ANALYSIS_RETRIED`.

---

# **44\. Flow UF-040 — Use AI Fallback Provider**

## **44.1 Goal**

Recover from primary-provider failure when fallback is configured.

## **44.2 Main Flow**

1. Primary provider fails.  
2. System determines whether failure is eligible for fallback.  
3. System records the primary failure.  
4. Fallback provider is invoked.  
5. Fallback response is normalized and validated.  
6. If valid:  
   * one canonical analysis is created;  
   * provider metadata identifies the fallback provider.  
7. If invalid:  
   * job fails;  
   * previous canonical analysis remains active.

---

# **45\. Flow UF-041 — Archive a Session**

## **45.1 Goal**

Remove a completed or inactive session from active views without deleting it.

## **45.2 Preconditions**

* Session is not currently analyzing.  
* Session may be closed, cancelled, or inactive.

## **45.3 Main Flow**

1. User selects **Arsipkan Session**.  
2. System explains that data will remain available.  
3. User confirms.  
4. Status becomes `ARCHIVED`, or archive flag is applied according to domain design.  
5. Timeline records `SESSION_ARCHIVED`.  
6. Session moves to archived views.

## **45.4 Rule**

Archiving must not change trade outcome or journal content.

---

# **46\. Flow UF-042 — Restore an Archived Session**

## **46.1 Goal**

Return an archived session to historical visibility.

## **46.2 Main Flow**

1. User opens archived sessions.  
2. User selects **Pulihkan dari Arsip**.  
3. System restores the previous terminal or stable state.  
4. Timeline records `SESSION_RESTORED`.

## **46.3 Restriction**

Restoring a closed session does not reopen the position.

---

# **47\. Flow UF-043 — Search and Filter Sessions**

## **47.1 Goal**

Quickly locate active or historical sessions.

## **47.2 Main Flow**

1. User enters search text or applies filters.  
2. System searches:  
   * ticker;  
   * company;  
   * title;  
   * notes;  
   * thesis;  
   * journal.  
3. System applies selected filters.  
4. Results update.  
5. User opens a session.

## **47.3 Supported Filters**

* lifecycle status;  
* ticker;  
* date range;  
* result;  
* thesis status;  
* active or closed;  
* profit or loss;  
* last update date;  
* archived state.

---

# **48\. Flow UF-044 — Configure AI Provider**

## **48.1 Goal**

Allow the user to choose Gemini or DeepSeek.

## **48.2 Preconditions**

* User is authenticated.  
* User can access settings.

## **48.3 Main Flow**

1. User opens **Pengaturan AI**.  
2. User selects a provider.  
3. User selects a model.  
4. User enters or updates API credentials.  
5. User configures optional fallback.  
6. System validates configuration server-side.  
7. System performs a safe connection test.  
8. System stores encrypted or protected configuration.  
9. User sees configuration status.

## **48.4 Security Rule**

The full API key must never be returned to the browser after storage.

---

# **49\. Flow UF-045 — View AI Usage and Cost**

## **49.1 Goal**

Provide visibility into AI consumption.

## **49.2 Main Flow**

1. User opens AI usage.  
2. System displays:  
   * request count;  
   * provider;  
   * model;  
   * token estimates;  
   * image usage;  
   * estimated cost;  
   * session cost;  
   * monthly cost.  
3. User may filter by session, date, provider, or model.

---

# **50\. Flow UF-046 — Session Requires Update**

## **50.1 Goal**

Help the user identify stale active sessions.

## **50.2 Main Flow**

1. System checks open or watching sessions.  
2. Session has not been updated within a configured period.  
3. Dashboard displays **Perlu Update**.  
4. User opens the session.  
5. User uploads new evidence or dismisses the reminder.

## **50.3 Rule**

A stale reminder must not trigger automatic AI analysis without new evidence.

---

# **51\. Flow UF-047 — Browser Refresh During Analysis**

## **51.1 Goal**

Preserve job visibility when the page reloads.

## **51.2 Main Flow**

1. Analysis job is running.  
2. User refreshes or leaves the page.  
3. Job continues in the background.  
4. User returns.  
5. System retrieves current job state.  
6. UI displays queued, processing, completed, or failed state.

---

# **52\. Flow UF-048 — Duplicate Analysis Submission**

## **52.1 Goal**

Prevent duplicate jobs caused by repeated clicks.

## **52.2 Main Flow**

1. User selects the analysis action multiple times.  
2. System detects an active job with the same idempotency scope.  
3. Additional submissions are not created.  
4. UI displays the existing job state.

---

# **53\. Flow UF-049 — Close Browser With Unsaved Position Form**

## **53.1 Goal**

Protect unsaved user-entered position data.

## **53.2 Main Flow**

1. User modifies a form.  
2. User attempts to navigate away.  
3. System warns:

Perubahan pada form belum disimpan.

4. User may:  
   * stay and save;  
   * leave and discard.

---

# **54\. Flow UF-050 — Correct Historical Position Data**

## **54.1 Goal**

Allow explicit corrections without rewriting audit history.

## **54.2 Preconditions**

* User identifies incorrect entry, exit, or quantity data.

## **54.3 Main Flow**

1. User selects **Koreksi Data Posisi**.  
2. System displays the original record.  
3. User enters:  
   * corrected value;  
   * correction reason.  
4. User confirms.  
5. System creates a correction record.  
6. Original record remains in audit history.  
7. Calculated position values are recomputed.  
8. Related journal may be marked outdated.  
9. User may regenerate affected analysis or journal.

## **54.4 Rule**

Historical corrections must never silently overwrite the original record.

---

# **55\. Flow UF-051 — Regenerate Journal After Data Correction**

## **55.1 Goal**

Update a journal after a valid historical correction.

## **55.2 Main Flow**

1. Position data correction is completed.  
2. Existing journal is marked `OUTDATED`.  
3. User selects **Buat Ulang Journal**.  
4. System generates a new journal version.  
5. Previous journal remains available.  
6. New version becomes canonical.

---

# **56\. User-Facing Status Mapping**

| Internal Status | Bahasa Indonesia Label |
| ----- | ----- |
| `DRAFT` | Draft |
| `READY_FOR_ANALYSIS` | Siap Dianalisis |
| `ANALYZING` | Sedang Dianalisis |
| `WATCHING` | Memantau Setup |
| `OPEN_POSITION` | Posisi Terbuka |
| `PARTIALLY_CLOSED` | Ditutup Sebagian |
| `CLOSED_TAKE_PROFIT` | Selesai — Take Profit |
| `CLOSED_STOP_LOSS` | Selesai — Stop Loss |
| `CLOSED_MANUAL` | Selesai — Exit Manual |
| `CANCELLED` | Setup Dibatalkan |
| `ARCHIVED` | Diarsipkan |

---

# **57\. Thesis Status Mapping**

| Internal Status | Bahasa Indonesia Label |
| ----- | ----- |
| `STRENGTHENING` | Thesis Menguat |
| `INTACT` | Thesis Masih Valid |
| `INTACT_BUT_WEAKENING` | Thesis Masih Valid, tetapi Melemah |
| `UNDER_REVIEW` | Thesis Sedang Ditinjau |
| `INVALIDATED` | Thesis Tidak Lagi Valid |

---

# **58\. Primary Happy Path**

The primary MVP happy path is:

1. User logs in.  
2. User creates a Trade Session.  
3. User uploads initial orderbook.  
4. User uploads three-month chart.  
5. User uploads six-month chart.  
6. Session becomes `READY_FOR_ANALYSIS`.  
7. User runs initial analysis.  
8. Session becomes `WATCHING`.  
9. User reviews entry, stop, target, confidence, and probability.  
10. User records actual entry.  
11. Session becomes `OPEN_POSITION`.  
12. User uploads morning orderbook.  
13. AI compares current and historical conditions.  
14. User uploads midday orderbook.  
15. AI explains what changed.  
16. User uploads closing orderbook.  
17. AI provides next-day plan.  
18. User records partial exit, optional.  
19. User records final exit.  
20. Session becomes closed.  
21. AI creates closing analysis.  
22. AI generates Trading Journal.  
23. User adds personal reflection.  
24. Session remains available as a complete historical trade story.

---

# **59\. Critical Edge Cases**

The implementation must explicitly test:

1. missing required initial evidence;  
2. duplicate evidence upload;  
3. unreadable screenshot;  
4. provider timeout;  
5. invalid structured output;  
6. English narrative returned instead of Indonesian;  
7. analysis job submitted twice;  
8. browser refresh during processing;  
9. thesis contradiction without explanation;  
10. stop widened without reason;  
11. target changed without reason;  
12. additional entry during invalidated thesis;  
13. partial exit greater than active quantity;  
14. attempt to cancel after entry;  
15. attempt to reopen a closed session;  
16. historical correction after journal generation;  
17. fallback provider returning a duplicate result;  
18. session restored from archive;  
19. stale session reminder without new evidence;  
20. context window compression removing critical thesis data.

---

# **60\. Flow Acceptance Criteria**

The user-flow implementation is accepted when:

1. every lifecycle state has a valid entry and exit flow;  
2. the user can complete the primary happy path;  
3. invalid lifecycle transitions are blocked;  
4. every position mutation requires explicit user action;  
5. every successful analysis creates a version;  
6. every update contains historical comparison;  
7. every thesis change is versioned;  
8. user-facing analysis is in Bahasa Indonesia;  
9. failed AI jobs do not damage session state;  
10. retries do not create duplicate canonical analyses;  
11. evidence remains traceable to analysis versions;  
12. closed sessions cannot become active positions again;  
13. journals use the full session history;  
14. historical corrections preserve audit history;  
15. all critical user actions create timeline events.

---

# **61\. Final User Flow Statement**

The TradePilot AI user experience must guide the user through one complete and traceable trade lifecycle.

At every stage, the user must understand:

* the current session state;  
* the current thesis;  
* what changed;  
* the current position risk;  
* what action is available;  
* which decisions remain under user control;  
* how the current analysis relates to the full trade history.

The user must never lose the story of the trade.

