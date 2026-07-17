# **TradePilot AI — UX/UI Specification**

**Document:** `UX_UI_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`  
**Purpose:** Define the user experience, information architecture, visual hierarchy, page structure, components, interaction behavior, responsive design, and user-facing language requirements.

---

## **1\. Document Purpose**

This document defines how TradePilot AI must be presented and operated through its web interface.

The UI must support the complete lifecycle of one trade:

Session creation → evidence upload → initial analysis → setup monitoring → open position → position updates → exit → AI Trading Journal.

The interface must make the full trade story easy to understand without requiring the user to reconstruct context from chat messages.

TradePilot AI must feel like a professional analytical workspace.

It must not feel like:

* a generic chatbot;  
* a social media feed;  
* a stock scanner;  
* a broker terminal;  
* a simple image-upload form;  
* a collection of disconnected AI responses.

---

# **2\. UX Vision**

The interface must help the user answer five questions immediately:

1. What is the current state of this trade?  
2. Is the trading thesis still valid?  
3. What has changed since the previous update?  
4. Is the current target still realistic?  
5. What should I do or monitor next?

The user should be able to understand the latest trade condition within a few seconds, while still being able to inspect detailed reasoning, evidence, and historical analysis.

The experience should balance:

* fast situational awareness;  
* detailed technical explanation;  
* historical traceability;  
* disciplined decision-making;  
* clear risk communication.

---

# **3\. Core UX Principles**

## **3.1 One Trade, One Workspace**

Each Trade Session must have a dedicated workspace.

The page must contain all relevant information for that trade only.

The user must not need to switch between multiple pages to understand:

* the thesis;  
* the active position;  
* latest analysis;  
* previous updates;  
* evidence;  
* stop loss;  
* targets;  
* timeline;  
* journal.

---

## **3.2 Structured Analysis, Not Chat Bubbles**

AI responses must be displayed as structured reports.

Preferred presentation patterns:

* cards;  
* grouped sections;  
* comparison tables;  
* timeline items;  
* metric blocks;  
* status badges;  
* evidence panels;  
* collapsible details;  
* version history.

A conversational input may be provided for notes or future assistant interaction, but the primary UI must not be organized as a chat conversation.

---

## **3.3 Latest State First**

The current state must be visible before historical detail.

The first viewport of the Trade Session page should prioritize:

* session status;  
* thesis status;  
* current position result;  
* stop loss;  
* target;  
* confidence;  
* probability;  
* latest recommended action;  
* last update time.

---

## **3.4 History Must Remain Accessible**

The latest analysis must not replace history.

The user must be able to inspect:

* previous analysis versions;  
* previous orderbook screenshots;  
* previous chart screenshots;  
* thesis changes;  
* stop-loss changes;  
* target changes;  
* entries;  
* exits;  
* AI recommendations;  
* user decisions.

---

## **3.5 Risk Must Be Visually Clear**

Risk-related information must never be hidden inside long paragraphs.

The UI must visually emphasize:

* thesis invalidation;  
* stop-loss proximity;  
* high uncertainty;  
* widened stop loss;  
* target deterioration;  
* unreadable evidence;  
* analysis failure;  
* inconsistent AI output.

---

## **3.6 User Control Must Be Explicit**

AI recommendations and actual user decisions must be visually separated.

The UI must distinguish:

* AI-recommended entry;  
* actual user entry;  
* AI-recommended stop;  
* active user-confirmed stop;  
* AI-recommended target;  
* active user-confirmed target;  
* AI-recommended partial exit;  
* recorded actual exit.

---

## **3.7 Progressive Disclosure**

The UI should show essential information immediately and deeper reasoning on demand.

Examples:

* summary visible by default;  
* technical details expandable;  
* evidence extraction expandable;  
* previous versions accessible through history;  
* full probability reasoning accessible from the score card.

---

# **4\. Language and Terminology Rules**

## **4.1 User-Facing Language**

The primary UI language is Bahasa Indonesia.

All user-facing:

* navigation;  
* labels;  
* buttons;  
* form instructions;  
* validation messages;  
* AI analysis narrative;  
* warnings;  
* journal content;

must use Bahasa Indonesia.

---

## **4.2 Internal Language**

Internal identifiers remain in English.

Examples:

OPEN\_POSITION  
THESIS\_INVALIDATED  
ANALYSIS\_FAILED  
TARGET\_PROBABILITY

The frontend must map internal values to Indonesian display labels.

---

## **4.3 Preferred User-Facing Terminology**

| Internal Concept | User-Facing Label |
| ----- | ----- |
| Trade Session | Trade Session |
| Trading Thesis | Thesis Trading |
| Initial Analysis | Analisis Awal |
| Open Position | Posisi Terbuka |
| Watching | Memantau Setup |
| Evidence | Evidence |
| Orderbook Screenshot | Screenshot Orderbook |
| Target Profit | Target Profit |
| Stop Loss | Stop Loss |
| Confidence | Confidence |
| Probability | Probability |
| Trading Plan | Trading Plan |
| Partial Exit | Partial Exit |
| Manual Exit | Exit Manual |
| AI Trading Journal | AI Trading Journal |

Common trading terms may remain in English when widely understood, but explanations must remain clear in Bahasa Indonesia.

---

# **5\. Information Architecture**

## **5.1 Primary Navigation**

The main application navigation must include:

1. Dashboard  
2. Session Aktif  
3. Posisi Terbuka  
4. Session Selesai  
5. Jurnal Trading  
6. Pengaturan

Optional secondary navigation:

* Session Draft  
* Arsip  
* Penggunaan AI  
* Sistem

---

## **5.2 Recommended URL Structure**

/login  
/dashboard  
/sessions  
/sessions/new  
/sessions/:sessionId  
/sessions/:sessionId/analysis/:analysisId  
/sessions/:sessionId/compare  
/sessions/:sessionId/evidence  
/sessions/:sessionId/journal  
/positions  
/journals  
/settings  
/settings/ai  
/settings/security  
/settings/system

The exact routing implementation may differ, but the URL must preserve clear session context.

---

## **5.3 Breadcrumbs**

Recommended breadcrumb pattern:

Dashboard / Session Aktif / BBRI / Analisis Terbaru

Breadcrumbs should appear on secondary or detailed views, not necessarily on the main dashboard.

---

# **6\. Global Application Shell**

## **6.1 Desktop Layout**

The desktop application shell should include:

* persistent left sidebar;  
* top application bar;  
* main content area;  
* optional contextual right panel.

Recommended proportions:

* left sidebar: 240–280 px;  
* main content: flexible;  
* right context panel: 300–360 px.

---

## **6.2 Left Sidebar**

The left sidebar should contain:

### **Brand Area**

* TradePilot AI logo;  
* product name;  
* optional environment badge.

### **Main Navigation**

* Dashboard  
* Session Aktif  
* Posisi Terbuka  
* Session Selesai  
* Jurnal Trading

### **Secondary Navigation**

* Arsip  
* Pengaturan

### **Quick Action**

A prominent:

**\+ Trade Session Baru**

### **Footer Area**

* user profile;  
* provider status;  
* system status indicator;  
* logout.

---

## **6.3 Top Application Bar**

The top bar may include:

* page title;  
* global search;  
* provider status;  
* background-job indicator;  
* notifications;  
* user menu.

The top bar should remain visually lightweight.

---

## **6.4 Main Content Area**

The main content area must support:

* full-width dashboard layouts;  
* multi-column Trade Session workspace;  
* table and card views;  
* responsive collapse.

---

## **6.5 Global Background Job Indicator**

When AI processing is active, the application should show:

* number of active jobs;  
* latest job status;  
* link to the related session.

Example:

1 analisis sedang diproses

The user should be able to navigate away without interrupting the job.

---

# **7\. Visual Design Direction**

## **7.1 General Style**

The interface should feel:

* professional;  
* calm;  
* analytical;  
* modern;  
* information-dense without being crowded;  
* suitable for long working sessions.

Avoid:

* excessive gradients;  
* decorative animation;  
* oversized marketing typography;  
* game-like visual effects;  
* highly saturated dashboards;  
* unnecessary financial-terminal complexity.

---

## **7.2 Recommended Visual Characteristics**

* neutral background;  
* clear card boundaries;  
* restrained use of accent color;  
* strong typography hierarchy;  
* consistent spacing;  
* compact but readable tables;  
* visually distinct risk states;  
* high-quality image previews.

---

## **7.3 Theme Support**

The MVP should preferably support:

* dark mode;  
* light mode.

If only one theme is implemented initially, dark mode may be prioritized because the application is an analytical workspace, but accessibility and readability must remain the deciding factors.

---

## **7.4 Status Color Semantics**

Color must reinforce meaning but must not be the only indicator.

Suggested semantic categories:

* positive or strengthening;  
* neutral or intact;  
* caution or weakening;  
* high risk or under review;  
* critical or invalidated;  
* informational;  
* processing;  
* failed.

Each state must also include text and iconography.

---

# **8\. Typography**

## **8.1 Hierarchy**

Recommended hierarchy:

* Page title  
* Session title  
* Section heading  
* Card heading  
* Metric value  
* Body analysis  
* Supporting metadata  
* Caption

---

## **8.2 Analysis Readability**

Long AI analysis content must use:

* comfortable line height;  
* limited line width;  
* paragraph spacing;  
* meaningful subheadings;  
* short bullet lists when appropriate;  
* bold emphasis only for important information.

Long paragraphs should be avoided when the content can be grouped into structured points.

---

## **8.3 Numeric Alignment**

Numeric values should use tabular figures when available.

This applies to:

* prices;  
* percentages;  
* probabilities;  
* quantities;  
* profit and loss;  
* dates and times.

---

# **9\. Dashboard Page**

## **9.1 Purpose**

The dashboard provides an overview of current trading activity and the fastest path to sessions requiring attention.

---

## **9.2 Dashboard Header**

Must include:

* page title: **Dashboard**  
* date or trading-day context;  
* **Trade Session Baru** primary action;  
* optional refresh action.

---

## **9.3 Primary Summary Cards**

Recommended cards:

### **Posisi Terbuka**

* count;  
* total unrealized result when calculable;  
* number requiring updates.

### **Setup Dipantau**

* count of `WATCHING` sessions;  
* count with no recent update.

### **Perlu Perhatian**

* thesis weakening;  
* thesis under review;  
* thesis invalidated;  
* failed analysis jobs.

### **Session Selesai**

* count for selected period;  
* wins and losses when calculable.

---

## **9.4 Active Session Priority List**

The dashboard should display active sessions sorted by urgency.

Priority order:

1. thesis invalidated;  
2. thesis under review;  
3. stop-loss proximity;  
4. analysis failed;  
5. update overdue;  
6. open position;  
7. watching setup.

Each row or card should include:

* ticker;  
* company name;  
* lifecycle status;  
* thesis status;  
* entry;  
* latest price;  
* current result;  
* stop;  
* target;  
* confidence;  
* latest action;  
* last update.

---

## **9.5 Recent Activity Timeline**

The dashboard may show recent events such as:

* analysis completed;  
* position opened;  
* thesis weakened;  
* stop changed;  
* partial exit;  
* position closed;  
* journal generated.

---

## **9.6 Empty Dashboard State**

When no sessions exist, display:

* brief product explanation;  
* required first steps;  
* primary CTA: **Buat Trade Session Pertama**.

Avoid generic empty tables.

---

# **10\. Session List Pages**

## **10.1 Session Aktif**

Includes:

* `DRAFT`;  
* `READY_FOR_ANALYSIS`;  
* `ANALYZING`;  
* `WATCHING`;  
* `OPEN_POSITION`;  
* `PARTIALLY_CLOSED`.

---

## **10.2 Posisi Terbuka**

Includes only:

* `OPEN_POSITION`;  
* `PARTIALLY_CLOSED`.

---

## **10.3 Session Selesai**

Includes:

* `CLOSED_TAKE_PROFIT`;  
* `CLOSED_STOP_LOSS`;  
* `CLOSED_MANUAL`;  
* `CANCELLED`.

---

## **10.4 List View Options**

The user should be able to switch between:

* table view;  
* card view.

Table view is preferred for information density.

---

## **10.5 Session Table Columns**

Recommended columns:

* Ticker  
* Nama Perusahaan  
* Status  
* Thesis  
* Entry  
* Harga Terakhir  
* P/L  
* Stop Loss  
* Target  
* Confidence  
* Update Terakhir  
* Tindakan

---

## **10.6 Filters**

Filters should include:

* lifecycle status;  
* thesis status;  
* result;  
* date;  
* ticker;  
* active or archived;  
* needs update;  
* analysis failure.

---

## **10.7 Search Behavior**

Search should match:

* ticker;  
* company;  
* session title;  
* notes;  
* thesis;  
* journal.

Search should use debouncing and display clear no-result states.

---

# **11\. New Trade Session Page**

## **11.1 Purpose**

Create the identity of one new trade story.

---

## **11.2 Form Fields**

Required:

* Ticker  
* Market

Optional:

* Nama Perusahaan  
* Judul Session  
* Catatan Awal

---

## **11.3 Form Behavior**

Ticker input should:

* automatically uppercase;  
* remove unnecessary whitespace;  
* validate supported characters;  
* show examples.

---

## **11.4 Context Explanation**

The page should explain:

Satu Trade Session digunakan untuk satu ticker dan satu lifecycle trading. Buat session baru apabila Anda ingin membuka thesis baru pada ticker yang sama.

---

## **11.5 Primary Actions**

* **Buat Session**  
* **Batal**

---

# **12\. Draft and Initial Evidence Page State**

## **12.1 Draft Workspace**

When status is `DRAFT`, the main area should show an initial evidence checklist.

---

## **12.2 Required Evidence Cards**

Three prominent cards:

### **Screenshot Orderbook**

Displays:

* upload state;  
* preview;  
* market timestamp;  
* replace action.

### **Chart 3 Bulan**

Displays:

* upload state;  
* preview;  
* replace action.

### **Chart 6 Bulan**

Displays:

* upload state;  
* preview;  
* replace action.

---

## **12.3 Evidence Checklist Status**

Each item must show:

* Belum diunggah  
* Sedang diunggah  
* Berhasil  
* Gagal  
* Tidak terbaca  
* Diganti

---

## **12.4 Initial Analysis CTA**

The **Jalankan Analisis Awal** button must remain disabled until all minimum evidence exists.

Disabled-state text or tooltip should explain the missing requirement.

---

## **12.5 Upload Interaction**

Recommended upload capabilities:

* drag and drop;  
* file browser;  
* paste from clipboard when supported;  
* upload progress;  
* preview before confirmation.

---

# **13\. Trade Session Page — Overall Structure**

## **13.1 Desktop Layout**

Recommended three-column layout:

### **Left Session Rail**

Contains:

* session navigation;  
* analysis versions;  
* timeline shortcuts;  
* evidence shortcuts.

### **Main Workspace**

Contains:

* current status banner;  
* latest analysis;  
* update comparison;  
* detailed technical sections;  
* trading plan;  
* timeline.

### **Right Context Panel**

Contains:

* active position;  
* thesis;  
* risk;  
* confidence;  
* probability;  
* key levels;  
* evidence thumbnails;  
* quick actions.

---

## **13.2 Alternative Two-Column Layout**

For narrower desktop screens:

* main workspace;  
* collapsible right context panel.

The left session rail may be replaced by tabs.

---

## **13.3 Session Header**

Must include:

* ticker;  
* company name;  
* session title;  
* lifecycle badge;  
* thesis-status badge;  
* created date;  
* last update;  
* overflow menu.

---

## **13.4 Session Header Actions**

Actions vary by state.

Possible actions:

* Tambah Evidence  
* Jalankan Analisis  
* Tambah Update  
* Tandai Posisi Terbuka  
* Tambah Entry  
* Ubah Stop Loss  
* Ubah Target  
* Partial Exit  
* Tutup Posisi  
* Batalkan Setup  
* Arsipkan

The primary action must be visually dominant.

---

# **14\. Session Summary Strip**

Directly below the header, show a compact summary strip.

Recommended metrics:

* Status Posisi  
* Harga Entry  
* Harga Terakhir  
* P/L  
* Stop Loss  
* Target Terdekat  
* Confidence  
* Probability Target  
* Update Terakhir

Unavailable values must display:

Belum tersedia

Do not use misleading zero values.

---

# **15\. Current Thesis Panel**

## **15.1 Purpose**

Provide the canonical technical explanation of the trade.

---

## **15.2 Required Content**

* current thesis;  
* thesis status;  
* supporting evidence;  
* key support;  
* key resistance;  
* invalidation condition;  
* last thesis change;  
* confidence.

---

## **15.3 Thesis Status Presentation**

Examples:

* Thesis Menguat  
* Thesis Masih Valid  
* Thesis Masih Valid, tetapi Melemah  
* Thesis Sedang Ditinjau  
* Thesis Tidak Lagi Valid

Status must include:

* badge;  
* text explanation;  
* last update timestamp.

---

## **15.4 Invalidation State**

When invalidated, display a prominent critical panel containing:

* invalidation reason;  
* evidence;  
* position impact;  
* required user attention.

The original thesis must remain viewable through history.

---

# **16\. Latest Analysis Workspace**

## **16.1 Default View**

The latest valid canonical analysis must be the default analysis displayed.

---

## **16.2 Analysis Header**

Must include:

* analysis type;  
* version;  
* timestamp;  
* update classification;  
* provider and model in details;  
* analysis status.

---

## **16.3 Core Analysis Sections**

Recommended order:

1. Ringkasan Eksekutif  
2. Tindakan yang Direkomendasikan  
3. Apa yang Berubah  
4. Ringkasan Pasar  
5. Analisis Orderbook  
6. Analisis Chart  
7. Support dan Resistance  
8. Penilaian Posisi  
9. Realisme Target  
10. Penilaian Stop Loss  
11. Confidence  
12. Probability  
13. Trading Plan  
14. Risiko dan Data yang Kurang

---

## **16.4 Section Behavior**

Each section may be:

* fully expanded by default for critical content;  
* collapsed for technical detail;  
* linkable through anchors;  
* printable or exportable later.

Recommended default expansion:

Expanded:

* Ringkasan Eksekutif  
* Tindakan yang Direkomendasikan  
* Apa yang Berubah  
* Penilaian Posisi  
* Trading Plan

Collapsed or compact:

* detailed extraction data;  
* provider metadata;  
* schema details;  
* full evidence references.

---

# **17\. Recommended Action Card**

## **17.1 Purpose**

Make the next action clear without reducing the analysis to a signal.

---

## **17.2 Content**

The card must include:

* recommended action label;  
* short rationale;  
* conditions;  
* invalidation;  
* time horizon;  
* risk level.

Possible labels:

* Tunggu Konfirmasi  
* Pertahankan Posisi  
* Pertahankan dengan Waspada  
* Pertimbangkan Partial Profit  
* Kurangi Risiko  
* Evaluasi Exit  
* Jangan Tambah Posisi  
* Setup Sebaiknya Dibatalkan

---

## **17.3 Restrictions**

The action card must never display only:

* BUY;  
* HOLD;  
* SELL.

The reasoning must remain visible.

---

# **18\. “What Changed” Comparison Panel**

## **18.1 Purpose**

Make longitudinal analysis immediately visible.

---

## **18.2 Required Comparison Categories**

* Harga  
* Average  
* Best Bid  
* Best Offer  
* Kekuatan Bid  
* Tekanan Offer  
* Support  
* Resistance  
* Momentum  
* Thesis  
* Confidence  
* Probability Target  
* Risiko  
* Rekomendasi

---

## **18.3 Display Pattern**

Recommended comparison table:

| Metric | Previous | Current | Change | Explanation |
| :---: | :---: | :---: | :---: | :---: |

For qualitative values:

| Area | Previous | Current | Interpretation |
| :---: | :---: | :---: | :---: |

---

## **18.4 No Material Change**

When no meaningful difference exists, display:

Tidak ada perubahan material sejak update sebelumnya. Thesis dan trading plan tetap sama.

Do not create artificial positive or negative change indicators.

---

# **19\. Orderbook Analysis UI**

## **19.1 Orderbook Evidence Viewer**

The UI should support side-by-side display of:

* previous orderbook;  
* current orderbook.

Optional future enhancements:

* zoom synchronization;  
* image annotations;  
* extracted-level overlays.

---

## **19.2 Orderbook Analysis Sections**

* Fakta yang Terlihat  
* Interpretasi  
* Perubahan dari Update Sebelumnya  
* Area Bid Penting  
* Area Offer Penting  
* Risiko Orderbook  
* Kesimpulan

---

## **19.3 Evidence Confidence**

Display extraction confidence when available.

Example:

Keterbacaan screenshot: Tinggi

When unreadable:

Beberapa angka pada orderbook tidak dapat dibaca dengan jelas.

---

# **20\. Chart Analysis UI**

## **20.1 Chart Tabs**

Recommended tabs:

* Chart 3 Bulan  
* Chart 6 Bulan  
* Chart Tambahan

---

## **20.2 Chart Analysis Content**

Each chart view should include:

* trend;  
* structure;  
* momentum;  
* volume;  
* support;  
* resistance;  
* pattern;  
* risk.

---

## **20.3 Image Viewer**

Chart viewer must support:

* zoom;  
* fullscreen;  
* download restriction according to security design;  
* evidence metadata;  
* related analysis version.

---

# **21\. Support and Resistance Panel**

## **21.1 Required Levels**

Display:

* Support Terdekat  
* Support Mayor  
* Level Invalidation  
* Resistance Terdekat  
* Resistance Mayor  
* Level Konfirmasi Breakout

---

## **21.2 Level Card Content**

Each level must show:

* price;  
* type;  
* basis;  
* status;  
* source;  
* last changed.

---

## **21.3 Level Status**

Possible statuses:

* Aktif  
* Sedang Diuji  
* Ditembus  
* Tidak Lagi Relevan  
* Belum Terkonfirmasi

---

# **22\. Position Panel**

## **22.1 Position Summary**

Must display:

* average entry;  
* total quantity when available;  
* remaining quantity;  
* latest price;  
* unrealized P/L;  
* realized P/L;  
* total P/L;  
* stop loss;  
* targets;  
* holding duration.

---

## **22.2 Position Health**

Recommended values:

* Sehat  
* Sehat, tetapi Volatil  
* Mulai Melemah  
* Risiko Tinggi  
* Kondisi Exit Terpicu

---

## **22.3 Planned Versus Actual Entry**

Display:

* AI planned entry;  
* actual user entry;  
* difference;  
* chase warning;  
* impact on risk-to-reward.

---

# **23\. Stop-Loss UI**

## **23.1 Active Stop Card**

Display:

* active stop;  
* distance from latest price;  
* distance from average entry;  
* technical basis;  
* last changed;  
* changed by.

---

## **23.2 Stop Change Flow**

When user selects **Ubah Stop Loss**, show:

* current stop;  
* proposed stop;  
* increased or reduced risk;  
* technical reason field;  
* thesis impact;  
* confirmation.

---

## **23.3 Wider Stop Warning**

Widening the stop must trigger a high-visibility warning.

The confirmation action should not be the default focused button.

---

# **24\. Target UI**

## **24.1 Target List**

Each target must display:

* target level;  
* target priority;  
* active or completed status;  
* distance;  
* probability;  
* technical basis;  
* quantity allocation when available.

---

## **24.2 Target Realism Card**

Must answer:

* Apakah target masih realistis?  
* Apakah probability meningkat atau menurun?  
* Apa hambatan terdekat?  
* Apakah target perlu dipertahankan?

---

## **24.3 Target Change Flow**

Display:

* old target;  
* new target;  
* reason;  
* risk-to-reward impact;  
* related AI recommendation when applicable.

---

# **25\. Confidence UI**

## **25.1 Confidence Card**

Display:

* score;  
* classification;  
* change from previous;  
* drivers;  
* reducers.

---

## **25.2 Confidence Labels**

* Rendah  
* Moderat  
* Tinggi

---

## **25.3 Explanation Access**

The user must be able to expand the score and see why it changed.

Do not display a score without context.

---

# **26\. Probability UI**

## **26.1 Required Probability Metrics**

* Peluang Mencapai Target  
* Peluang Pullback  
* Peluang Menyentuh Stop Loss  
* Peluang Thesis Tetap Valid  
* Peluang Thesis Tidak Valid  
* Peluang Bullish Berlanjut when applicable

---

## **26.2 Display Style**

Use:

* percentage;  
* previous value;  
* trend indicator;  
* explanation.

Avoid presenting probability as financial certainty.

---

## **26.3 Logical Warning**

When probabilities appear inconsistent, the UI may display:

Probability memiliki skenario yang saling tumpang tindih. Baca penjelasan untuk memahami konteksnya.

---

# **27\. Trading Plan UI**

## **27.1 Initial Analysis Plan**

Must display three scenario cards:

* Skenario Bullish  
* Skenario Netral  
* Skenario Bearish

Each card includes:

* trigger;  
* expected condition;  
* action;  
* target;  
* invalidation.

---

## **27.2 Open Position Plan**

Must be time-aware.

Examples:

* Trading Plan hingga Siang  
* Trading Plan hingga Penutupan  
* Trading Plan Besok

---

## **27.3 “Do Not” Section**

When relevant, show a visible section:

**Yang Sebaiknya Tidak Dilakukan**

Examples:

* Jangan mengejar harga di atas level tertentu.  
* Jangan average down selama thesis melemah.  
* Jangan memperlebar stop tanpa bukti teknikal baru.

---

# **28\. Evidence Gallery**

## **28.1 Gallery Structure**

Evidence may be grouped by:

* date;  
* update classification;  
* evidence type;  
* analysis version.

---

## **28.2 Evidence Card**

Each card must include:

* thumbnail;  
* type;  
* market timestamp;  
* upload timestamp;  
* processing state;  
* related analysis;  
* status.

---

## **28.3 Evidence Statuses**

* Aktif  
* Diganti  
* Dikecualikan  
* Tidak Terbaca  
* Duplikat  
* Gagal Diproses

---

## **28.4 Evidence Detail Drawer or Modal**

Must display:

* full image;  
* metadata;  
* caption;  
* extraction result;  
* extraction confidence;  
* linked analyses;  
* audit status.

---

# **29\. Timeline UI**

## **29.1 Purpose**

Show the complete story of the trade chronologically.

---

## **29.2 Timeline Event Categories**

* Session  
* Evidence  
* Analysis  
* Thesis  
* Position  
* Stop Loss  
* Target  
* Exit  
* Journal  
* System

---

## **29.3 Timeline Item Content**

Each item must show:

* date and time;  
* event title;  
* short description;  
* actor;  
* related object link;  
* change summary.

---

## **29.4 Timeline Grouping**

Group events by:

* trading date;  
* session phase.

Example:

17 July 2026  
Pagi  
Siang  
Penutupan

---

## **29.5 Timeline Filters**

Allow filtering by:

* analysis;  
* thesis;  
* evidence;  
* position;  
* system errors;  
* user actions.

---

# **30\. Analysis History UI**

## **30.1 Analysis Version List**

Display:

* version;  
* date and time;  
* type;  
* status;  
* thesis status;  
* confidence;  
* target probability;  
* provider;  
* canonical indicator.

---

## **30.2 Version Detail**

Must show:

* full analysis;  
* evidence used;  
* position snapshot;  
* prompt version;  
* provider;  
* model;  
* schema version;  
* context-summary version.

Technical metadata may be hidden behind an advanced section.

---

# **31\. Analysis Comparison UI**

## **31.1 Comparison Selection**

The user selects:

* previous version;  
* current version.

Default comparison:

* latest versus immediately previous.

---

## **31.2 Comparison Sections**

* Market Summary  
* Orderbook  
* Chart  
* Support  
* Resistance  
* Thesis  
* Position Health  
* Confidence  
* Probability  
* Trading Plan  
* Recommended Action

---

## **31.3 Visual Comparison**

Use structured side-by-side panels or tables.

Raw text diff may be available as an advanced view but must not be the only comparison format.

---

# **32\. Update Creation Flow UI**

## **32.1 Update Action**

Selecting **Tambah Update** opens a focused update workspace or modal.

---

## **32.2 Update Classification**

Required options:

* Update Pagi  
* Update Siang  
* Update Penutupan  
* Update Khusus

---

## **32.3 Required Input**

At least one new evidence item or market snapshot must be provided.

---

## **32.4 Optional Input**

* latest price;  
* OHLC;  
* average;  
* volume;  
* notes;  
* additional chart.

---

## **32.5 Submit State**

Primary action:

**Jalankan Analisis Update**

Before submission, show:

* evidence count;  
* update type;  
* market timestamp;  
* active position summary.

---

# **33\. Position Opening UI**

## **33.1 Position Entry Form**

Required fields:

* Harga Entry  
* Waktu Entry  
* Stop Loss  
* Target Profit

Optional:

* Quantity  
* Biaya Broker  
* Alokasi Modal  
* Catatan Entry

---

## **33.2 Context Panel**

Show:

* recommended entry;  
* chase limit;  
* thesis;  
* invalidation;  
* recommended stop;  
* recommended target;  
* current confidence.

---

## **33.3 Confirmation Summary**

Before final confirmation, display:

* actual entry;  
* distance to stop;  
* distance to target;  
* estimated risk-to-reward;  
* difference from AI plan;  
* warnings.

---

# **34\. Additional Entry UI**

## **34.1 Required Information**

* additional entry price;  
* time;  
* quantity;  
* reason.

---

## **34.2 Position Impact Preview**

Display before confirmation:

* old average;  
* new average;  
* old total quantity;  
* new total quantity;  
* new downside to stop;  
* whether averaging up or down.

---

## **34.3 Averaging Down Warning**

Must use a high-attention confirmation.

---

# **35\. Partial Exit UI**

## **35.1 Form Fields**

* Quantity Dijual  
* Harga Exit  
* Waktu Exit  
* Alasan  
* Catatan

---

## **35.2 Result Preview**

Before confirmation:

* realized P/L;  
* remaining quantity;  
* remaining cost basis;  
* active stop;  
* remaining targets.

---

## **35.3 Post-Exit Workspace**

After partial exit:

* status becomes **Ditutup Sebagian**;  
* realized and unrealized results are shown separately;  
* remaining-position plan remains active.

---

# **36\. Full Position Closure UI**

## **36.1 Exit Reason Selection**

Options:

* Take Profit  
* Stop Loss  
* Thesis Tidak Valid  
* Pengurangan Risiko  
* Exit Berdasarkan Waktu  
* Exit Manual  
* Lainnya

---

## **36.2 Closure Form**

Required:

* final exit price;  
* final exit time;  
* remaining quantity;  
* exit reason.

---

## **36.3 Final Confirmation**

Display:

* average entry;  
* average exit;  
* realized result;  
* return percentage;  
* holding duration;  
* plan compliance indicator.

---

## **36.4 Closed State**

After closure, active-management actions must disappear.

Available actions become:

* Lihat Closing Analysis  
* Buat Journal  
* Tambah Refleksi  
* Arsipkan  
* Buat Session Baru untuk Ticker Ini

---

# **37\. AI Trading Journal UI**

## **37.1 Journal Header**

Display:

* ticker;  
* outcome;  
* return;  
* duration;  
* entry and exit;  
* exit reason;  
* journal version.

---

## **37.2 Journal Sections**

* Ringkasan Trade  
* Thesis Awal  
* Perjalanan Thesis  
* Review Entry  
* Review Manajemen Posisi  
* Review Exit  
* Disiplin Trading Plan  
* Evaluasi AI  
* Hal yang Berjalan Baik  
* Hal yang Perlu Diperbaiki  
* Pelajaran Utama  
* Checklist Berikutnya  
* Refleksi Pribadi

---

## **37.3 AI and User Content Separation**

AI-generated journal content and user reflection must be visually distinct.

---

## **37.4 Journal Versioning**

If regenerated, show:

* latest canonical journal;  
* previous journal versions;  
* reason for regeneration.

---

# **38\. Settings UI**

## **38.1 Settings Sections**

* AI Provider  
* Tampilan  
* Keamanan  
* Penyimpanan  
* Notifikasi  
* Sistem  
* Penggunaan AI

---

## **38.2 AI Provider Settings**

Display:

* active provider;  
* active model;  
* vision support;  
* fallback provider;  
* connection status;  
* last successful request.

API key fields must be masked.

---

## **38.3 Connection Test**

Provide:

**Uji Koneksi**

Results:

* Berhasil  
* Gagal  
* Model tidak mendukung vision  
* API key tidak valid  
* Provider tidak merespons

---

## **38.4 AI Usage Page**

Display:

* requests;  
* tokens;  
* images;  
* provider;  
* estimated cost;  
* daily and monthly totals;  
* cost by Trade Session.

---

# **39\. Notifications UI**

## **39.1 Notification Types**

* analysis completed;  
* analysis failed;  
* thesis weakened;  
* thesis invalidated;  
* session requires update;  
* journal generated;  
* provider configuration issue.

---

## **39.2 Notification Priority**

* Critical  
* Warning  
* Informational  
* Success

---

## **39.3 Notification Behavior**

Notifications must:

* link to relevant session;  
* be dismissible;  
* retain unread state;  
* avoid duplicate messages for the same event.

---

# **40\. Empty States**

Every major page must have a purposeful empty state.

Examples:

### **No Open Positions**

Belum ada posisi terbuka.

CTA:

**Lihat Setup yang Dipantau**

### **No Journals**

Journal akan tersedia setelah posisi ditutup.

### **No Analysis History**

Analisis pertama belum dibuat.

### **No Evidence**

Unggah evidence untuk memulai analisis.

---

# **41\. Loading States**

## **41.1 Page Loading**

Use skeleton states for:

* dashboard cards;  
* session summary;  
* analysis sections;  
* evidence gallery;  
* timeline.

---

## **41.2 Analysis Processing State**

Display step-based progress where possible:

1. Menyiapkan evidence  
2. Menyusun histori session  
3. Mengirim ke AI provider  
4. Memvalidasi hasil  
5. Menyimpan analisis

Avoid fake exact percentage progress unless actual progress is available.

---

## **41.3 Upload Progress**

Each file must show:

* upload progress;  
* processing state;  
* completion;  
* failure retry.

---

# **42\. Error States**

## **42.1 General Error Requirements**

Every error must explain:

* what failed;  
* impact;  
* next action.

---

## **42.2 Analysis Failure Card**

Display:

* user-friendly error;  
* retry action;  
* provider;  
* timestamp;  
* technical detail in expandable section.

---

## **42.3 Invalid AI Output**

Display:

Hasil AI belum dapat digunakan karena tidak memenuhi format analisis yang diperlukan. Analisis sebelumnya tetap menjadi acuan.

---

## **42.4 Offline or Connectivity Error**

Display:

Koneksi ke server terputus. Perubahan yang belum tersimpan dapat hilang.

---

# **43\. Confirmation Dialogs**

Confirmation is required for:

* opening a position;  
* changing stop loss;  
* widening stop loss;  
* changing targets;  
* adding an entry;  
* recording partial exit;  
* closing position;  
* cancelling setup;  
* excluding evidence;  
* archiving session;  
* correcting historical data.

Destructive or high-risk actions must not use one-click execution.

---

# **44\. Unsaved Changes**

Forms must detect unsaved changes.

When user navigates away, display:

Perubahan belum disimpan. Apakah Anda yakin ingin meninggalkan halaman?

---

# **45\. Accessibility Requirements**

## **45.1 Keyboard Navigation**

All interactive controls must be keyboard accessible.

---

## **45.2 Focus States**

Visible focus indicators are required.

---

## **45.3 Color Independence**

Status must never be represented by color alone.

Use:

* text;  
* icon;  
* label;  
* color.

---

## **45.4 Screen Reader Support**

Important components must have:

* semantic headings;  
* accessible labels;  
* button names;  
* table headers;  
* image alternative text.

---

## **45.5 Contrast**

Text, badges, warnings, and buttons must meet acceptable contrast standards.

---

# **46\. Responsive Design**

## **46.1 Desktop Priority**

Desktop is the primary experience.

Recommended minimum desktop target:

* 1280 px width.

---

## **46.2 Tablet**

On tablet:

* sidebar may collapse;  
* right context panel becomes drawer;  
* analysis sections remain stacked;  
* tables may horizontally scroll.

---

## **46.3 Mobile**

On mobile:

* use bottom or compact navigation;  
* session header becomes stacked;  
* metrics become horizontally scrollable cards;  
* right context panel becomes tabs;  
* evidence viewer opens fullscreen;  
* comparison view becomes vertically stacked.

---

## **46.4 Mobile Priority Content**

The first mobile viewport should show:

* ticker;  
* status;  
* thesis;  
* P/L;  
* stop;  
* target;  
* latest action.

Detailed analysis follows below.

---

# **47\. Suggested Component Inventory**

## **47.1 Global Components**

* `AppSidebar`  
* `TopBar`  
* `GlobalSearch`  
* `NotificationCenter`  
* `BackgroundJobIndicator`  
* `UserMenu`

## **47.2 Session Components**

* `SessionHeader`  
* `SessionStatusBadge`  
* `SessionSummaryStrip`  
* `SessionActionBar`  
* `ThesisPanel`  
* `PositionSummaryCard`  
* `RiskWarningBanner`  
* `LatestAnalysisView`  
* `AnalysisSection`  
* `AnalysisVersionList`  
* `AnalysisComparison`  
* `EvidenceGallery`  
* `EvidenceViewer`  
* `Timeline`  
* `QuickNotes`

## **47.3 Trading Components**

* `EntryPlanCard`  
* `ActualEntryCard`  
* `StopLossCard`  
* `TargetList`  
* `TargetRealismCard`  
* `PositionHealthCard`  
* `ProfitLossCard`  
* `PartialExitForm`  
* `ClosePositionForm`

## **47.4 AI Components**

* `ConfidenceCard`  
* `ProbabilityCard`  
* `RecommendedActionCard`  
* `AnalysisJobStatus`  
* `ProviderBadge`  
* `MissingDataAlert`  
* `ContradictionWarning`

---

# **48\. UX State Matrix**

| Session State | Primary Message | Primary Action |
| ----- | ----- | ----- |
| `DRAFT` | Evidence awal belum lengkap | Lengkapi Evidence |
| `READY_FOR_ANALYSIS` | Session siap dianalisis | Jalankan Analisis Awal |
| `ANALYZING` | Analisis sedang diproses | Lihat Status |
| `WATCHING` | Setup sedang dipantau | Tambah Update / Buka Posisi |
| `OPEN_POSITION` | Posisi sedang aktif | Tambah Update |
| `PARTIALLY_CLOSED` | Sebagian posisi telah ditutup | Pantau Sisa Posisi |
| `CLOSED_TAKE_PROFIT` | Posisi selesai dengan take profit | Lihat Journal |
| `CLOSED_STOP_LOSS` | Posisi selesai dengan stop loss | Lihat Journal |
| `CLOSED_MANUAL` | Posisi telah ditutup manual | Lihat Journal |
| `CANCELLED` | Setup dibatalkan | Buat Session Baru |
| `ARCHIVED` | Session berada di arsip | Pulihkan |

---

# **49\. Recommended Action Mapping**

| Internal Action | Bahasa Indonesia Label |
| ----- | ----- |
| `WAIT_FOR_CONFIRMATION` | Tunggu Konfirmasi |
| `HOLD_POSITION` | Pertahankan Posisi |
| `HOLD_WITH_CAUTION` | Pertahankan dengan Waspada |
| `CONSIDER_PARTIAL_PROFIT` | Pertimbangkan Partial Profit |
| `REDUCE_RISK` | Kurangi Risiko |
| `REVIEW_EXIT` | Evaluasi Exit |
| `DO_NOT_ADD` | Jangan Tambah Posisi |
| `CANCEL_SETUP` | Batalkan Setup |
| `NO_MATERIAL_CHANGE` | Tidak Ada Perubahan Material |

---

# **50\. Risk Level Mapping**

| Internal Value | Bahasa Indonesia Label |
| ----- | ----- |
| `LOW` | Rendah |
| `MODERATE` | Moderat |
| `ELEVATED` | Meningkat |
| `HIGH` | Tinggi |
| `CRITICAL` | Kritis |

---

# **51\. Interaction Performance Requirements**

The interface should:

* respond to local interactions within 100–200 ms where possible;  
* show feedback immediately after user action;  
* avoid blocking the page during AI work;  
* preserve scroll position when updating analysis state;  
* lazy-load large evidence images;  
* paginate long timelines;  
* virtualize large session lists when needed.

---

# **52\. Audit Visibility**

Important user-confirmed changes should show:

* who made the change;  
* when;  
* previous value;  
* new value;  
* reason.

Audit detail may appear in:

* timeline;  
* change history;  
* object details.

---

# **53\. Privacy and Security UX**

## **53.1 Protected Evidence**

Evidence images must not expose public URLs.

---

## **53.2 Sensitive Settings**

API keys must:

* be masked;  
* not be readable after save;  
* support replace and revoke flows.

---

## **53.3 Session Timeout**

When authentication expires, the UI should preserve safe local form state where possible and redirect to login.

---

# **54\. MVP Screen Inventory**

The MVP must include at least:

1. Login  
2. Dashboard  
3. Session List  
4. Create Trade Session  
5. Draft Evidence Workspace  
6. Trade Session — Watching  
7. Trade Session — Open Position  
8. Add Update  
9. Open Position Form  
10. Additional Entry Form  
11. Stop-Loss Update Form  
12. Target Update Form  
13. Partial Exit Form  
14. Close Position Form  
15. Evidence Gallery  
16. Evidence Detail  
17. Analysis History  
18. Analysis Comparison  
19. Timeline  
20. Closing Analysis  
21. AI Trading Journal  
22. Journal Reflection  
23. Archived Sessions  
24. AI Provider Settings  
25. AI Usage  
26. Notifications  
27. Error and Retry States

---

# **55\. MVP UX Acceptance Criteria**

The UX/UI implementation is accepted when:

1. the user can identify the current trade state immediately;  
2. the latest thesis is prominently visible;  
3. the latest recommended action is visible without opening history;  
4. stop loss and target are clearly separated from AI recommendations;  
5. every session has one dedicated workspace;  
6. analysis is displayed as structured content, not chat bubbles;  
7. every update includes a visible historical comparison;  
8. the user can open previous analyses and evidence;  
9. risk warnings are visually distinct;  
10. user-facing text is in Bahasa Indonesia;  
11. internal enum values are not shown as raw primary labels;  
12. the user can complete the full trade lifecycle from the UI;  
13. failed analyses can be retried without losing context;  
14. AI jobs remain visible after navigation or refresh;  
15. closed sessions display journal-focused actions;  
16. mobile layout preserves critical position information;  
17. destructive and risk-increasing actions require confirmation;  
18. unavailable values are displayed as unavailable, not zero;  
19. the UI clearly distinguishes AI recommendations from user-confirmed actions;  
20. the user can reconstruct the full trade story through timeline, evidence, and version history.

---

# **56\. Final UX Statement**

TradePilot AI must provide a workspace where the user can understand the current condition of a trade, inspect the evidence behind the analysis, compare changes over time, and manage the position without losing the original trading story.

The interface must make the complete trade lifecycle visible, structured, and auditable.

The user should never need to search through disconnected chat messages to understand:

* why the trade was considered valid;  
* what changed;  
* whether the thesis remains valid;  
* whether the target is still realistic;  
* what action should be taken next;  
* what was learned after the position was closed.

