# **TradePilot AI PRD Amendment — BUY, WAIT, and SKIP Decisions**

**PRD Version:** 1.1
**Applies After:** Successful Initial Analysis
**Decision Authority:** User only

---

## **1\. Post-Initial Analysis Decisions**

After the Initial Analysis has been stored and displayed, the system must show three user decision buttons:

BUY
WAIT
SKIP

Gemini may recommend one of these actions in its analysis, but Gemini must not execute or persist the decision.

Only an explicit user action may change the session status.

---

## **2\. Decision Summary**

| Decision | Meaning | Position Created | Further Orderbook Updates | Session Closed |
| ----- | ----- | ----- | ----- | ----- |
| BUY | User decides to enter the trade | Yes | Yes | No |
| WAIT | User is not ready to enter and wants more evidence | No | Yes | No |
| SKIP | User decides not to enter the trade | No | No | Yes |

---

## **3\. BUY Decision**

The user selects BUY when they decide to enter the trade after reviewing the Initial Analysis.

### **3.1 BUY Form**

Required fields:

* entry price;
* quantity;
* entry date and time;
* stop loss;
* target price.

Optional field:

* user note.

### **3.2 BUY Behavior**

After the user confirms BUY:

1. The system stores the user decision as `BUY`.
2. The system creates one position record.
3. The entered position values become confirmed user-owned facts.
4. The session status becomes:

OPEN\_POSITION

5. The system displays the open-position monitoring form.
6. The user may upload further orderbook screenshots for Morning, Midday, or Afternoon.
7. BUY must not trigger a Gemini request by itself.

Gemini must not modify:

* entry price;
* quantity;
* entry timestamp;
* stop loss;
* target price;
* position status.

---

## **4\. WAIT Decision**

The user selects WAIT when the Initial Analysis is not yet sufficient for entering the trade, or when the user wants to observe additional orderbook evidence before deciding.

WAIT does not create a position.

### **4.1 WAIT Behavior**

After the user confirms WAIT:

1. The system stores the user decision as `WAIT`.
2. No position record is created.
3. No entry price, quantity, stop loss, or target price is required.
4. The session status becomes:

WAITING

5. The system displays a follow-up orderbook upload form.
6. The user may upload orderbook screenshots for:

MORNING
MIDDAY
AFTERNOON

7. WAIT must not trigger a Gemini request by itself.

### **4.2 WAIT Follow-Up Form**

Required fields:

* observation period;
* current price;
* orderbook screenshot;
* observation date and time.

Optional field:

* user note.

Supporting text for current price:

Masukkan harga terakhir yang terlihat pada orderbook.

### **4.3 WAIT Analysis Request**

When the user submits a WAIT follow-up update, the system must:

1. Store the current price.
2. Store the orderbook screenshot.
3. Store the observation period.
4. Store the observation date and time.
5. Create one follow-up analysis request.
6. Send one request to Gemini.
7. Include the latest orderbook screenshot.
8. Include the manually entered current price.
9. Include the Initial Analysis.
10. Include relevant previous WAIT analyses.
11. Store Gemini’s response.
12. Process and display the response in Indonesian.

The user-entered current price is authoritative.

Gemini must not replace it with a price inferred from the screenshot.

### **4.4 WAIT Analysis Output**

The WAIT analysis should answer whether the stock has become more attractive, less attractive, or remains inconclusive.

Required user-facing sections:

1. Ringkasan update
2. Harga saat ini
3. Analisis orderbook
4. Perubahan dibanding analisis sebelumnya
5. Kondisi entry saat ini
6. Risiko utama
7. Peluang kenaikan
8. Peluang penurunan
9. Apakah masih perlu menunggu
10. Trading plan berikutnya
11. Kesimpulan AI

After a successful WAIT update:

session.status remains WAITING

### **4.5 Decisions Available After WAIT Analysis**

After each WAIT analysis, the user must again be able to choose:

BUY
WAIT
SKIP

Behavior:

* BUY opens the BUY form and creates a position after confirmation.
* WAIT allows another orderbook update.
* SKIP closes the session without opening a position.

The user may submit multiple WAIT updates before making the final BUY or SKIP decision.

All WAIT analyses must remain visible chronologically.

---

## **5\. SKIP Decision**

The user selects SKIP when they decide not to enter the stock.

This may occur because:

* Gemini identifies excessive risk;
* the setup is not attractive;
* the risk-to-reward ratio is insufficient;
* orderbook conditions are weak;
* the market condition is unfavorable;
* the user personally decides not to continue.

### **5.1 SKIP Confirmation**

Before closing the session, the system should display a confirmation dialog.

Required input:

* skip reason.

Optional input:

* user note.

Suggested skip-reason options:

RISK\_TOO\_HIGH
SETUP\_NOT\_ATTRACTIVE
ORDERBOOK\_WEAK
MARKET\_CONDITION\_UNFAVORABLE
WAITING\_TOO\_LONG
USER\_DECISION
OTHER

The UI must display readable Indonesian labels for these values.

### **5.2 SKIP Behavior**

After the user confirms SKIP:

1. The system stores the decision as `SKIP`.
2. The system stores the skip reason.
3. No position record is created.
4. No closing trade price is required.
5. The session status becomes:

CLOSED\_SKIPPED

6. Further evidence uploads are disabled.
7. Further Gemini analysis requests are disabled.
8. The complete session history remains available.
9. The session must clearly show that no trade was opened.

SKIP must not trigger a Gemini request.

### **5.3 SKIP Is Different From CLOSE**

`SKIP` means:

The user never entered the trade.

`CLOSE` means:

The user entered the trade and later closed the open position.

These outcomes must remain distinguishable in stored data and in the user interface.

---

## **6\. Revised Session Statuses**

The approved session statuses are:

DRAFT
ANALYZING
ANALYZED
WAITING
OPEN\_POSITION
CLOSED
CLOSED\_SKIPPED

Optional technical status:

ANALYSIS\_FAILED

### **Status Definitions**

#### **DRAFT**

The session exists, but Initial Analysis has not completed.

#### **ANALYZING**

A Gemini analysis request is currently being processed.

#### **ANALYZED**

Initial Analysis completed successfully. The user has not selected BUY, WAIT, or SKIP.

#### **WAITING**

The user selected WAIT. No position exists. Follow-up orderbook analysis is allowed.

#### **OPEN\_POSITION**

The user selected BUY and confirmed position information.

#### **CLOSED**

The user previously opened a position and manually closed it.

#### **CLOSED\_SKIPPED**

The user selected SKIP without opening a position.

#### **ANALYSIS\_FAILED**

The latest Gemini request failed. The previous valid business status must remain recoverable.

No additional business status may be added without explicit product approval.

---

## **7\. Revised Analysis Types**

The approved analysis types are:

INITIAL\_ANALYSIS
WAIT\_UPDATE
POSITION\_UPDATE

Definitions:

### **INITIAL\_ANALYSIS**

Uses:

* orderbook screenshot;
* three-month chart screenshot;
* six-month chart screenshot.

### **WAIT\_UPDATE**

Used after the user selects WAIT.

Uses:

* latest orderbook screenshot;
* manually entered current price;
* Initial Analysis;
* relevant previous WAIT updates.

No position facts exist yet.

### **POSITION\_UPDATE**

Used after the user selects BUY.

Uses:

* latest orderbook screenshot;
* manually entered current price;
* confirmed position facts;
* Initial Analysis;
* relevant WAIT history, when available;
* relevant previous Position Updates.

Morning, Midday, and Afternoon remain observation-period metadata, not separate analysis types.

---

## **8\. Revised Decision Flow**

The complete decision flow is:

INITIAL ANALYSIS COMPLETED
        |
        \+── BUY
        |     |
        |     \+── Confirm position details
        |     \+── Status: OPEN\_POSITION
        |     \+── Upload repeated orderbook updates
        |     \+── User eventually clicks CLOSE
        |     \+── Status: CLOSED
        |
        \+── WAIT
        |     |
        |     \+── Status: WAITING
        |     \+── Upload repeated orderbook updates
        |     \+── Receive WAIT analyses
        |     \+── Choose BUY, WAIT, or SKIP again
        |
        \+── SKIP
              |
              \+── Store skip reason
              \+── No position created
              \+── Status: CLOSED\_SKIPPED

---

## **9\. Revised Session Page Requirements**

After Initial Analysis, the session detail page must display:

BUY
WAIT
SKIP

### **When Status Is `ANALYZED`**

Display:

* Initial Analysis;
* BUY button;
* WAIT button;
* SKIP button.

### **When Status Is `WAITING`**

Display:

* Initial Analysis;
* chronological WAIT analyses;
* WAIT follow-up upload form;
* BUY button;
* WAIT or Submit Another Update action;
* SKIP button.

Do not display position summary because no position exists.

### **When Status Is `OPEN_POSITION`**

Display:

* Initial Analysis;
* relevant WAIT history, when applicable;
* confirmed position summary;
* chronological Position Updates;
* Position Update form;
* CLOSE button.

Do not display BUY, WAIT, or SKIP after a position has been opened.

### **When Status Is `CLOSED_SKIPPED`**

Display:

* Initial Analysis;
* WAIT history, when applicable;
* SKIP decision;
* skip reason;
* session closure timestamp;
* clear indication that no trade was opened.

Disable new analysis submissions.

### **When Status Is `CLOSED`**

Display:

* Initial Analysis;
* WAIT history, when applicable;
* position details;
* all Position Updates;
* close information;
* realized result, when available.

Disable new analysis submissions.

---

## **10\. Revised Data Requirements**

### **10.1 User Decisions**

The system must store user decisions separately from Gemini recommendations.

Suggested logical entity:

session\_decisions

Suggested fields:

* `id`
* `session_id`
* `decision`
* `reason`
* `note`
* `created_at`

Allowed decisions:

BUY
WAIT
SKIP

A simple field on the session may be used if full decision history is not required, but repeated WAIT decisions should remain auditable.

### **10.2 Analysis Requests**

The analysis record must support:

INITIAL\_ANALYSIS
WAIT\_UPDATE
POSITION\_UPDATE

For WAIT updates:

* `position_id` must be null;
* `current_price` is required;
* `observation_period` is required.

For Position Updates:

* `position_id` is required;
* `current_price` is required;
* `observation_period` is required.

### **10.3 Skipped Sessions**

A skipped session must store:

* skip reason;
* optional note;
* skipped timestamp;
* final status `CLOSED_SKIPPED`.

It must not contain:

* entry price;
* quantity;
* stop loss;
* target price;
* close price;
* realized profit or loss.

---

## **11\. Revised Gemini Context Rules**

### **WAIT Update Context**

Gemini receives:

* ticker;
* company name;
* manually entered current price;
* latest orderbook screenshot;
* observation period;
* Initial Analysis;
* relevant previous WAIT analyses;
* optional user note.

Gemini does not receive fabricated position facts.

The WAIT prompt must focus on:

* whether entry conditions are improving;
* whether risk is increasing;
* whether the stock remains worth monitoring;
* whether BUY, WAIT, or SKIP is most reasonable.

Gemini’s recommendation remains non-authoritative.

### **Position Update Context**

Gemini receives:

* ticker;
* company name;
* manually entered current price;
* latest orderbook screenshot;
* observation period;
* confirmed entry price;
* quantity;
* stop loss;
* target price;
* Initial Analysis;
* relevant WAIT history;
* previous Position Updates.

The Position Update prompt must focus on the condition of the existing position.

---

## **12\. Revised Acceptance Criteria**

The product must support both possible pre-entry paths.

### **Path A — Direct BUY**

1. User creates a session.
2. User uploads the three required initial images.
3. Gemini Initial Analysis is stored and displayed.
4. BUY, WAIT, and SKIP buttons appear.
5. User clicks BUY.
6. User confirms position facts.
7. Session becomes `OPEN_POSITION`.
8. User submits repeated Position Updates.
9. User clicks CLOSE.
10. Session becomes `CLOSED`.

### **Path B — WAIT Then BUY**

1. User completes Initial Analysis.
2. User clicks WAIT.
3. Session becomes `WAITING`.
4. User enters current price and uploads an orderbook.
5. Gemini WAIT Update is stored and displayed.
6. BUY, WAIT, and SKIP remain available.
7. User clicks BUY.
8. User confirms position facts.
9. Session becomes `OPEN_POSITION`.
10. Previous WAIT history remains visible.
11. User submits Position Updates.
12. User eventually closes the trade.

### **Path C — WAIT Then SKIP**

1. User completes Initial Analysis.
2. User clicks WAIT.
3. User submits one or more WAIT updates.
4. All WAIT analyses remain visible.
5. User clicks SKIP.
6. User enters a skip reason.
7. No position is created.
8. Session becomes `CLOSED_SKIPPED`.
9. New uploads are disabled.
10. Complete history remains available.

### **Path D — Direct SKIP**

1. User completes Initial Analysis.
2. User clicks SKIP.
3. User enters a skip reason.
4. No position is created.
5. Session becomes `CLOSED_SKIPPED`.
6. Complete Initial Analysis history remains available.

---

## **13\. Updated Definition of Done**

The rebuild is complete when all of the following work:

* Initial Analysis;
* BUY after Initial Analysis;
* WAIT after Initial Analysis;
* repeated WAIT updates;
* BUY after one or more WAIT updates;
* SKIP directly after Initial Analysis;
* SKIP after one or more WAIT updates;
* repeated Position Updates after BUY;
* CLOSE after BUY;
* complete chronological history;
* no Gemini response changes user-owned decisions or execution facts;
* skipped sessions are distinguishable from closed trades;
* Gemini remains the only AI provider.
