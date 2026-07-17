# **TradePilot AI — AI Analysis Specification**

**Document:** `AI_ANALYSIS_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`, `DOMAIN_MODEL.md`, `SESSION_LIFECYCLE.md`, `DATABASE_SCHEMA.md`  
**Purpose:** Define AI analysis types, input context, output contracts, structured schemas, validation rules, longitudinal comparison requirements, canonicalization behavior, and user-facing analysis standards.

---

## **1\. Document Purpose**

This document defines how TradePilot AI generates, validates, stores, and presents AI trading analysis.

It specifies:

* supported analysis types;  
* input requirements;  
* context-construction requirements;  
* mandatory output sections;  
* structured-output contracts;  
* narrative-language rules;  
* numerical rules;  
* longitudinal comparison behavior;  
* thesis-change behavior;  
* confidence and probability requirements;  
* recommended-action rules;  
* missing-data handling;  
* contradiction handling;  
* canonicalization eligibility;  
* failure and retry behavior.

This specification applies to all AI providers.

Provider-specific request formats are defined separately in:

* `AI_PROVIDER_SPEC.md`

Prompt wording and templates are defined separately in:

* `PROMPT_SPEC.md`

Thesis-transition logic is defined separately in:

* `THESIS_ENGINE_SPEC.md`

Confidence and probability calculations are defined separately in:

* `PROBABILITY_CONFIDENCE_SPEC.md`

---

# **2\. AI Analysis Objectives**

TradePilot AI analysis must help the user understand:

1. the current technical condition;  
2. what is visible in the latest evidence;  
3. what changed since the previous update;  
4. whether the active thesis remains valid;  
5. whether the position remains healthy;  
6. whether the target remains realistic;  
7. whether the stop loss remains technically appropriate;  
8. which risks are increasing or decreasing;  
9. what action or observation is appropriate next;  
10. which evidence would invalidate the current plan.

The analysis must not merely return a directional label.

---

# **3\. Core AI Analysis Principles**

## **3.1 Structured Output Is Mandatory**

Every AI analysis must return a structured object matching the active schema version.

Free-form Markdown alone is not a valid result.

The structured response must use:

* English keys;  
* English enum values;  
* Bahasa Indonesia narrative values.

Example:

{  
  "thesis\_status": "INTACT\_BUT\_WEAKENING",  
  "recommended\_action": "HOLD\_WITH\_CAUTION",  
  "executive\_summary": {  
    "condition\_summary": "Posisi masih berada di atas support utama, tetapi tekanan offer meningkat dibandingkan update pagi."  
  }  
}

---

## **3.2 User-Facing Narrative Must Use Bahasa Indonesia**

All narrative fields displayed to the user must be written in clear Bahasa Indonesia.

Allowed exceptions:

* ticker symbols;  
* common trading terms;  
* technical names;  
* internal enum values not directly displayed.

The AI must avoid unnecessarily mixing English and Indonesian.

---

## **3.3 Analysis Must Use Session History**

Except for the first initial analysis, every analysis must use relevant prior context.

The AI must not analyze only the newest screenshot.

Required historical context may include:

* initial thesis;  
* current thesis;  
* previous analysis;  
* previous comparable evidence;  
* current position;  
* active stop loss;  
* active targets;  
* prior confidence;  
* prior probabilities;  
* prior trading plan;  
* meaningful timeline events.

---

## **3.4 Facts Must Be Separated from Interpretation**

The analysis must distinguish between:

* visible evidence;  
* extracted numerical facts;  
* user-provided facts;  
* technical interpretation;  
* analytical inference;  
* uncertainty;  
* unavailable information.

The AI must not present inference as directly observed fact.

---

## **3.5 No Fabricated Values**

The AI must never invent:

* price;  
* Open, High, Low, or Close;  
* average price;  
* bid or offer quantity;  
* volume;  
* support;  
* resistance;  
* entry price;  
* stop loss;  
* target;  
* timestamps;  
* percentage values derived from unavailable inputs.

Unknown or unreadable values must be represented as null and explained.

---

## **3.6 Recommendations Must Be Conditional**

Recommendations must specify:

* recommended action;  
* reason;  
* conditions;  
* risks;  
* invalidation;  
* time horizon.

Standalone BUY, HOLD, or SELL outputs are prohibited.

---

## **3.7 Probability Is Not Certainty**

Probability values are analytical estimates.

The AI must not describe them as guaranteed, statistically calibrated, or certain unless future evaluation demonstrates calibration.

---

## **3.8 AI Cannot Execute Position Changes**

The AI may propose:

* entry;  
* stop change;  
* target change;  
* additional entry;  
* partial exit;  
* full exit.

The application must not apply the proposal until the user explicitly confirms it.

---

# **4\. Supported Analysis Types**

The system must support:

INITIAL\_ANALYSIS  
WATCHING\_UPDATE  
OPEN\_POSITION\_UPDATE  
PARTIAL\_EXIT\_REVIEW  
CLOSING\_ANALYSIS  
TRADING\_JOURNAL  
CONTEXT\_SUMMARY  
THESIS\_REVIEW

Each type has a distinct purpose and output contract.

---

# **5\. Shared Analysis Input Envelope**

Every analysis request must be represented internally by a normalized input envelope.

Recommended conceptual structure:

{  
  "request": {  
    "analysis\_request\_id": "uuid",  
    "analysis\_type": "OPEN\_POSITION\_UPDATE",  
    "requested\_at": "2026-07-17T04:30:00Z",  
    "output\_language": "id-ID",  
    "schema\_version": "1.0",  
    "prompt\_version": "1.0"  
  },  
  "session": {},  
  "current\_update": {},  
  "position": {},  
  "thesis": {},  
  "history": {},  
  "evidence": \[\],  
  "instructions": {}  
}

The exact provider payload may differ, but all providers must receive equivalent semantic context.

---

# **6\. Shared Session Input**

The session context should include:

{  
  "session\_id": "uuid",  
  "ticker": "BBRI",  
  "company\_name": "Bank Rakyat Indonesia",  
  "market": "IDX",  
  "currency": "IDR",  
  "lifecycle\_status": "OPEN\_POSITION",  
  "stable\_status": "OPEN\_POSITION",  
  "created\_at": "timestamp",  
  "last\_analysis\_at": "timestamp",  
  "trading\_timezone": "Asia/Jakarta"  
}

---

# **7\. Shared Current Update Input**

The current update should include:

{  
  "update\_id": "uuid",  
  "classification": "MIDDAY",  
  "custom\_label": null,  
  "trading\_date": "2026-07-17",  
  "market\_timestamp": "timestamp",  
  "user\_note": "Bid mulai menipis setelah sesi pertama.",  
  "market\_snapshot": {},  
  "evidence\_ids": \[\]  
}

---

# **8\. Shared Position Input**

When a position exists, the input must include:

{  
  "position\_id": "uuid",  
  "position\_status": "OPEN",  
  "average\_entry": 3090,  
  "total\_quantity": 10000,  
  "remaining\_quantity": 10000,  
  "latest\_price": 3120,  
  "realized\_profit\_loss": 0,  
  "unrealized\_profit\_loss": 300000,  
  "return\_percentage": 0.9709,  
  "active\_stop\_loss": {  
    "price": 2840,  
    "technical\_basis": "Di bawah support mayor."  
  },  
  "active\_targets": \[  
    {  
      "type": "TP1",  
      "price": 3250,  
      "priority": 1  
    }  
  \],  
  "entries": \[\],  
  "exits": \[\],  
  "position\_version": 4  
}

Unknown quantity-dependent values remain null.

---

# **9\. Shared Thesis Input**

The active thesis context must include:

{  
  "thesis\_id": "uuid",  
  "version\_number": 3,  
  "thesis\_status": "INTACT",  
  "directional\_bias": "BULLISH",  
  "thesis\_statement": "Harga masih membentuk struktur rebound dengan support utama tetap terjaga.",  
  "technical\_rationale": "Bid bertahan dan chart masih menunjukkan higher low.",  
  "key\_support": {},  
  "key\_resistance": {},  
  "invalidation\_level": {},  
  "invalidation\_condition": "Penutupan valid di bawah support mayor.",  
  "confidence\_score": 72  
}

---

# **10\. Shared Historical Context**

The historical context should contain:

{  
  "initial\_analysis\_summary": {},  
  "latest\_analysis\_summary": {},  
  "previous\_comparable\_update": {},  
  "significant\_analysis\_versions": \[\],  
  "thesis\_history": \[\],  
  "key\_timeline\_events": \[\],  
  "previous\_confidence": {},  
  "previous\_probabilities": \[\],  
  "previous\_trading\_plan": {},  
  "canonical\_context\_summary": {}  
}

Older repetitive history may be summarized.

Critical historical facts must remain explicit.

---

# **11\. Shared Evidence Input**

Each evidence item provided to the model should include metadata such as:

{  
  "evidence\_id": "uuid",  
  "evidence\_type": "ORDERBOOK\_SCREENSHOT",  
  "evidence\_role": "PRIMARY\_CURRENT",  
  "market\_timestamp": "timestamp",  
  "caption": null,  
  "extraction\_status": "COMPLETED",  
  "extraction\_confidence": 88,  
  "extracted\_data": {},  
  "included\_as\_image": true,  
  "limitations": \[\]  
}

The AI must know which evidence is:

* current;  
* previous;  
* historical reference;  
* initial reference;  
* contradictory;  
* user-provided note.

---

# **12\. Shared Output Envelope**

Every analysis type must return a common top-level envelope.

{  
  "schema\_version": "1.0",  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "language": "id-ID",  
  "analysis\_timestamp": "timestamp",  
  "ticker": "BBRI",  
  "data\_quality": {},  
  "executive\_summary": {},  
  "market\_summary": {},  
  "evidence\_assessment": {},  
  "orderbook\_analysis": {},  
  "chart\_analysis": {},  
  "change\_summary": {},  
  "thesis\_assessment": {},  
  "position\_assessment": {},  
  "level\_assessment": {},  
  "entry\_plan": {},  
  "stop\_loss\_assessment": {},  
  "target\_assessment": {},  
  "confidence\_assessment": {},  
  "probability\_assessments": \[\],  
  "risk\_assessment": {},  
  "trading\_plan": {},  
  "recommended\_action": {},  
  "missing\_data": \[\],  
  "warnings": \[\],  
  "canonical\_state\_proposal": {}  
}

Fields not applicable to one analysis type may be null or omitted according to the JSON schema.

---

# **13\. Common Data Quality Contract**

The output must include a data-quality assessment.

{  
  "overall\_quality": "HIGH\_CONFIDENCE",  
  "evidence\_completeness\_score": 85,  
  "image\_readability\_score": 90,  
  "historical\_context\_quality": "HIGH\_CONFIDENCE",  
  "critical\_missing\_fields": \[\],  
  "limitations": \[  
    "Volume transaksi tidak terlihat pada screenshot orderbook."  
  \]  
}

## **13.1 Rules**

* scores must be between 0 and 100;  
* missing evidence must reduce confidence where material;  
* unreadable values must not appear as exact extracted facts;  
* the AI must identify evidence limitations explicitly.

---

# **14\. Common Executive Summary Contract**

{  
  "condition\_summary": "Posisi masih sehat, tetapi tekanan offer meningkat dibandingkan update pagi.",  
  "directional\_bias": "BULLISH",  
  "setup\_quality": "MODERATE",  
  "primary\_opportunity": "Support intraday masih dipertahankan buyer.",  
  "primary\_risk": "Offer tebal berada dekat resistance terdekat.",  
  "recommended\_next\_action": "Pertahankan posisi dengan disiplin pada stop loss."  
}

The summary must be concise enough for quick reading but technically supported by later sections.

---

# **15\. Common Market Summary Contract**

{  
  "open": 3100,  
  "high": 3150,  
  "low": 3070,  
  "last": 3120,  
  "close": null,  
  "previous\_close": 3090,  
  "average": 3110,  
  "absolute\_change": 30,  
  "percentage\_change": 0.9709,  
  "volume": null,  
  "transaction\_value": null,  
  "best\_bid": 3110,  
  "best\_offer": 3120,  
  "source\_summary": "Nilai berasal dari data yang diberikan user dan screenshot orderbook.",  
  "unavailable\_fields": \[  
    "volume",  
    "transaction\_value"  
  \]  
}

## **15.1 Numerical Rule**

The AI should preferably reproduce validated values supplied by the application rather than recalculate them independently.

System-calculated values override AI calculations.

---

# **16\. Common Evidence Assessment Contract**

{  
  "visible\_facts": \[  
    "Best bid terlihat pada 3.110.",  
    "Best offer terlihat pada 3.120."  
  \],  
  "user\_provided\_facts": \[  
    "Entry user berada di 3.090."  
  \],  
  "interpretations": \[  
    "Bid masih bertahan dekat harga rata-rata."  
  \],  
  "assumptions": \[\],  
  "uncertainties": \[  
    "Ketahanan antrean bid belum dapat dipastikan hanya dari satu snapshot."  
  \]  
}

The output must not combine all four categories into one undifferentiated narrative.

---

# **17\. Common Orderbook Analysis Contract**

{  
  "summary": "Orderbook masih menunjukkan buyer bertahan, tetapi offer terdekat mulai menebal.",  
  "best\_bid": 3110,  
  "best\_offer": 3120,  
  "spread": 10,  
  "bid\_strength": "MODERATE",  
  "offer\_pressure": "ELEVATED",  
  "bid\_concentration": \[\],  
  "offer\_concentration": \[\],  
  "buyer\_persistence": "UNCERTAIN",  
  "seller\_aggression": "MODERATE",  
  "absorption\_assessment": {  
    "status": "POSSIBLE",  
    "explanation": "Offer pada 3.120 beberapa kali terlihat berkurang, tetapi histori antrean belum cukup."  
  },  
  "distribution\_assessment": {  
    "status": "NOT\_CONFIRMED",  
    "explanation": "Belum terdapat bukti cukup untuk menyimpulkan distribusi."  
  },  
  "nearest\_orderbook\_support": {  
    "price": 3100,  
    "basis": "Konsentrasi bid terdekat."  
  },  
  "nearest\_orderbook\_resistance": {  
    "price": 3130,  
    "basis": "Konsentrasi offer terdekat."  
  },  
  "liquidity\_quality": "MODERATE",  
  "spoofing\_risk": "MODERATE",  
  "limitations": \[  
    "Orderbook merupakan snapshot dan antrean dapat berubah."  
  \]  
}

---

# **18\. Orderbook Controlled Values**

Suggested controlled values:

## **18.1 Strength and Pressure**

VERY\_WEAK  
WEAK  
MODERATE  
STRONG  
VERY\_STRONG  
UNKNOWN

## **18.2 Absorption Status**

CONFIRMED  
POSSIBLE  
NOT\_CONFIRMED  
NOT\_APPLICABLE

## **18.3 Buyer Persistence**

INCREASING  
STABLE  
DECREASING  
UNCERTAIN  
NOT\_COMPARABLE

## **18.4 Liquidity Quality**

LOW  
MODERATE  
HIGH  
UNKNOWN

Final values must be defined in the JSON schema and shared types.

---

# **19\. Common Chart Analysis Contract**

Chart analysis may contain separate objects for each timeframe.

{  
  "three\_month": {  
    "available": true,  
    "trend": "BULLISH",  
    "swing\_structure": "HIGHER\_LOW",  
    "momentum": "IMPROVING",  
    "volume\_behavior": "UNAVAILABLE",  
    "patterns": \[  
      {  
        "name": "Rebound structure",  
        "status": "POSSIBLE",  
        "explanation": "Harga membentuk higher low, tetapi breakout belum terkonfirmasi."  
      }  
    \],  
    "support\_levels": \[\],  
    "resistance\_levels": \[\],  
    "breakout\_assessment": {},  
    "breakdown\_assessment": {},  
    "risk\_notes": \[\]  
  },  
  "six\_month": {  
    "available": true,  
    "trend": "NEUTRAL",  
    "swing\_structure": "RANGE",  
    "momentum": "STABLE",  
    "volume\_behavior": "UNAVAILABLE",  
    "patterns": \[\],  
    "support\_levels": \[\],  
    "resistance\_levels": \[\],  
    "breakout\_assessment": {},  
    "breakdown\_assessment": {},  
    "risk\_notes": \[\]  
  }  
}

The AI must not identify a chart pattern as confirmed when the visible evidence is ambiguous.

---

# **20\. Common Level Assessment Contract**

{  
  "immediate\_support": {  
    "exact\_price": 3100,  
    "lower\_bound": null,  
    "upper\_bound": null,  
    "basis": "Area bid dan reaksi harga intraday.",  
    "source\_type": "ORDERBOOK",  
    "status": "ACTIVE",  
    "confidence\_score": 72  
  },  
  "major\_support": {  
    "exact\_price": null,  
    "lower\_bound": 3020,  
    "upper\_bound": 3050,  
    "basis": "Area swing low pada chart tiga bulan.",  
    "source\_type": "CHART\_STRUCTURE",  
    "status": "ACTIVE",  
    "confidence\_score": 78  
  },  
  "thesis\_invalidation": {  
    "exact\_price": 3020,  
    "basis": "Penutupan valid di bawah area ini merusak higher low.",  
    "source\_type": "CHART\_STRUCTURE",  
    "status": "ACTIVE",  
    "confidence\_score": 80  
  },  
  "immediate\_resistance": {},  
  "major\_resistance": {},  
  "breakout\_confirmation": {}  
}

## **20.1 Exact Price Versus Zone**

Use an exact price only when evidence supports exact precision.

Use a zone when:

* chart structure is broad;  
* multiple reactions occur across nearby levels;  
* screenshot precision is limited.

---

# **21\. Common Change Summary Contract**

Every follow-up analysis must include:

{  
  "material\_change\_exists": true,  
  "overall\_change\_summary": "Tekanan offer meningkat, sedangkan support utama belum berubah.",  
  "items": \[  
    {  
      "metric": "BID\_STRENGTH",  
      "previous\_value": "STRONG",  
      "current\_value": "MODERATE",  
      "change\_direction": "DECREASED",  
      "materiality": "MATERIAL",  
      "explanation": "Antrean bid terdekat lebih tipis dibandingkan update pagi."  
    }  
  \],  
  "unchanged\_items": \[  
    {  
      "metric": "MAJOR\_SUPPORT",  
      "value": 3020,  
      "explanation": "Belum terdapat evidence baru yang mengubah support mayor."  
    }  
  \]  
}

---

# **22\. Change Summary Metrics**

Supported comparison metrics should include:

LAST\_PRICE  
AVERAGE\_PRICE  
BEST\_BID  
BEST\_OFFER  
BID\_STRENGTH  
OFFER\_PRESSURE  
BUYER\_PERSISTENCE  
SELLER\_AGGRESSION  
IMMEDIATE\_SUPPORT  
MAJOR\_SUPPORT  
IMMEDIATE\_RESISTANCE  
MAJOR\_RESISTANCE  
MOMENTUM  
THESIS\_STATUS  
CONFIDENCE  
TARGET\_PROBABILITY  
PULLBACK\_PROBABILITY  
STOP\_LOSS\_TOUCH\_PROBABILITY  
RISK\_LEVEL  
POSITION\_HEALTH  
RECOMMENDED\_ACTION

---

# **23\. Change Materiality**

Allowed values:

NON\_MATERIAL  
MATERIAL  
CRITICAL  
NOT\_COMPARABLE

The AI must not classify every small difference as material.

---

# **24\. Common Thesis Assessment Contract**

{  
  "previous\_status": "INTACT",  
  "proposed\_status": "INTACT\_BUT\_WEAKENING",  
  "directional\_bias": "BULLISH",  
  "thesis\_statement": "Thesis rebound masih valid selama support mayor bertahan.",  
  "change\_type": "WEAKENED",  
  "change\_reason": "Bid intraday melemah dan offer meningkat, tetapi invalidation belum terjadi.",  
  "supporting\_evidence": \[  
    "Harga masih berada di atas support mayor."  
  \],  
  "conflicting\_evidence": \[  
    "Tekanan offer meningkat dibandingkan update sebelumnya."  
  \],  
  "key\_support": {},  
  "key\_resistance": {},  
  "invalidation\_level": {},  
  "invalidation\_condition": "Penutupan valid di bawah support mayor.",  
  "expected\_scenario": "Konsolidasi sebelum mencoba resistance.",  
  "canonicalization\_recommendation": "ACCEPT"  
}

---

# **25\. Thesis Canonicalization Recommendations**

The AI may propose:

ACCEPT  
KEEP\_PREVIOUS  
REVIEW\_REQUIRED

The application remains authoritative.

The AI cannot force canonicalization.

---

# **26\. Common Position Assessment Contract**

{  
  "applicable": true,  
  "position\_health": "HEALTHY\_BUT\_VOLATILE",  
  "average\_entry": 3090,  
  "latest\_price": 3120,  
  "return\_percentage": 0.9709,  
  "distance\_to\_stop\_percentage": 8.9744,  
  "distance\_to\_nearest\_target\_percentage": 4.1667,  
  "thesis\_validity": "INTACT\_BUT\_WEAKENING",  
  "hold\_assessment": {  
    "is\_rational": true,  
    "explanation": "Support mayor belum rusak dan harga masih berada di atas entry."  
  },  
  "averaging\_down\_assessment": {  
    "recommended": false,  
    "explanation": "Thesis sedang melemah sehingga penambahan posisi belum layak."  
  },  
  "partial\_profit\_assessment": {  
    "recommended": false,  
    "explanation": "Harga belum mencapai resistance utama."  
  },  
  "exit\_assessment": {  
    "exit\_condition\_triggered": false,  
    "explanation": "Belum ada invalidation yang terkonfirmasi."  
  }  
}

All application-calculable distances should preferably be calculated by the backend.

---

# **27\. Common Stop-Loss Assessment Contract**

{  
  "active\_stop": 2840,  
  "technical\_basis": "Di bawah support mayor.",  
  "is\_still\_appropriate": true,  
  "appropriateness\_explanation": "Support yang menjadi basis stop belum berubah.",  
  "distance\_from\_latest\_price\_percentage": 8.9744,  
  "risk\_status": "MODERATE",  
  "proposed\_change": {  
    "recommended": false,  
    "proposed\_price": null,  
    "direction": "UNCHANGED",  
    "reason": "Belum terdapat evidence untuk memindahkan stop.",  
    "risk\_impact": null,  
    "thesis\_impact": null  
  },  
  "warnings": \[\]  
}

## **27.1 Stop Change Directions**

TIGHTEN  
WIDEN  
UNCHANGED  
REMOVE

`REMOVE` must be invalid for an open position unless immediately replaced.

---

# **28\. Common Target Assessment Contract**

{  
  "overall\_realism": "STILL\_REALISTIC",  
  "summary": "Target masih realistis, tetapi membutuhkan penyerapan offer pada resistance terdekat.",  
  "targets": \[  
    {  
      "target\_type": "TP1",  
      "price": 3250,  
      "status": "ACTIVE",  
      "realism": "MODERATE",  
      "achievement\_probability": 62,  
      "nearest\_obstacles": \[  
        3130,  
        3200  
      \],  
      "required\_conditions": \[  
        "Harga bertahan di atas 3.100.",  
        "Offer 3.130 berhasil diserap."  
      \],  
      "recommended\_change": {  
        "action": "KEEP",  
        "proposed\_price": null,  
        "reason": "Belum ada perubahan struktur yang memerlukan revisi."  
      }  
    }  
  \]  
}

---

# **29\. Target Realism Values**

HIGHLY\_REALISTIC  
STILL\_REALISTIC  
REALISTIC\_WITH\_CONDITIONS  
LESS\_REALISTIC  
UNREALISTIC  
NOT\_APPLICABLE

Target-change actions:

KEEP  
LOWER  
RAISE  
DEACTIVATE  
ADD\_TARGET

Every non-`KEEP` recommendation requires a detailed reason.

---

# **30\. Common Confidence Assessment Contract**

{  
  "score": 68,  
  "classification": "MODERATE",  
  "previous\_score": 74,  
  "score\_change": \-6,  
  "drivers": \[  
    "Support mayor masih terlihat jelas."  
  \],  
  "reducers": \[  
    "Orderbook terbaru menunjukkan tekanan offer meningkat."  
  \],  
  "evidence\_quality": "MODERATE\_CONFIDENCE",  
  "missing\_data": \[  
    "Volume transaksi tidak tersedia."  
  \],  
  "explanation": "Confidence menurun karena orderbook melemah, tetapi struktur chart belum rusak."  
}

---

# **31\. Confidence Classification Rules**

LOW       0–39  
MODERATE  40–69  
HIGH      70–100

The classification must match the score.

The AI must not confuse confidence with bullish probability.

---

# **32\. Common Probability Assessment Contract**

\[  
  {  
    "probability\_type": "TARGET\_ACHIEVEMENT",  
    "percentage": 62,  
    "previous\_percentage": 68,  
    "change\_direction": "DECREASED",  
    "reasoning": "Offer terdekat meningkat dan momentum intraday melemah.",  
    "supporting\_evidence": \[  
      "Target masih berada di dalam range chart tiga bulan."  
    \],  
    "uncertainty\_level": "MODERATE"  
  },  
  {  
    "probability\_type": "PULLBACK",  
    "percentage": 48,  
    "previous\_percentage": 38,  
    "change\_direction": "INCREASED",  
    "reasoning": "Bid terdekat lebih tipis dibandingkan update pagi.",  
    "supporting\_evidence": \[\],  
    "uncertainty\_level": "MODERATE"  
  }  
\]

---

# **33\. Required Probability Types by Analysis**

## **33.1 Initial Analysis**

Required:

* `BULLISH_CONTINUATION`  
* `TARGET_ACHIEVEMENT`  
* `PULLBACK`  
* `MAJOR_SUPPORT_BREAK`  
* `THESIS_INVALIDATION`

## **33.2 Watching Update**

Required:

* `BULLISH_CONTINUATION`  
* `TARGET_ACHIEVEMENT`  
* `PULLBACK`  
* `THESIS_REMAINS_VALID`  
* `THESIS_INVALIDATION`

## **33.3 Open Position Update**

Required:

* `TARGET_ACHIEVEMENT`  
* `PULLBACK`  
* `STOP_LOSS_TOUCH`  
* `THESIS_REMAINS_VALID`  
* `THESIS_INVALIDATION`

## **33.4 Closing Analysis**

Probability output is optional and generally not required.

---

# **34\. Common Risk Assessment Contract**

{  
  "level": "ELEVATED",  
  "primary\_risks": \[  
    "Offer menebal dekat resistance.",  
    "Bid terdekat lebih tipis dibandingkan pagi."  
  \],  
  "stop\_proximity": "MODERATE",  
  "thesis\_risk": "ELEVATED",  
  "evidence\_risk": "MODERATE",  
  "execution\_risk": "LOW",  
  "mitigation": \[  
    "Jangan menambah posisi sebelum offer berhasil diserap.",  
    "Pertahankan stop loss yang telah ditetapkan."  
  \]  
}

---

# **35\. Common Trading Plan Contract**

{  
  "plan\_horizon": "UNTIL\_MARKET\_CLOSE",  
  "bullish\_scenario": {  
    "trigger": "Harga bertahan di atas 3.110 dan menembus 3.130.",  
    "expected\_behavior": "Momentum berpotensi berlanjut menuju resistance berikutnya.",  
    "user\_action": "Pertahankan posisi.",  
    "target": "Target aktif tetap digunakan.",  
    "invalidation": "Harga kembali di bawah 3.100 dengan bid melemah."  
  },  
  "neutral\_scenario": {  
    "trigger": "Harga bergerak di antara 3.100–3.130.",  
    "expected\_behavior": "Konsolidasi intraday.",  
    "user\_action": "Tunggu tanpa menambah posisi.",  
    "invalidation": "Range pecah dengan tekanan jual kuat."  
  },  
  "bearish\_scenario": {  
    "trigger": "Harga kehilangan 3.100 dan bid tidak bertahan.",  
    "expected\_behavior": "Risiko pullback menuju support berikutnya meningkat.",  
    "user\_action": "Evaluasi risiko dan disiplin pada stop loss.",  
    "invalidation": "Harga kembali di atas 3.110 dengan bid menguat."  
  },  
  "prohibited\_actions": \[  
    "Jangan average down selama thesis melemah.",  
    "Jangan memperlebar stop hanya untuk menghindari kerugian."  
  \],  
  "next\_checkpoint": "Update penutupan",  
  "recommended\_action": "HOLD\_WITH\_CAUTION"  
}

---

# **36\. Plan Horizon Values**

UNTIL\_MIDDAY  
UNTIL\_MARKET\_CLOSE  
NEXT\_TRADING\_SESSION  
NEXT\_TRADING\_DAY  
UNTIL\_NEXT\_EVIDENCE  
CUSTOM  
NOT\_APPLICABLE

---

# **37\. Common Recommended Action Contract**

{  
  "action": "HOLD\_WITH\_CAUTION",  
  "display\_label": "Pertahankan dengan Waspada",  
  "rationale": "Thesis masih valid, tetapi orderbook melemah dibandingkan update sebelumnya.",  
  "conditions": \[  
    "Support 3.100 tetap bertahan."  
  \],  
  "invalidation": \[  
    "Harga turun di bawah support dengan bid yang tidak pulih."  
  \],  
  "time\_horizon": "UNTIL\_MARKET\_CLOSE",  
  "risk\_level": "ELEVATED",  
  "requires\_user\_confirmation": false  
}

`requires_user_confirmation` must be true for recommended position mutations such as:

* stop change;  
* target change;  
* additional entry;  
* partial exit;  
* final exit.

---

# **38\. Missing Data Contract**

\[  
  {  
    "field": "transaction\_value",  
    "importance": "LOW",  
    "reason": "Nilai transaksi tidak terlihat.",  
    "impact": "Tidak memengaruhi support utama, tetapi mengurangi kualitas evaluasi likuiditas.",  
    "recommended\_evidence": "Screenshot yang menampilkan nilai transaksi."  
  }  
\]

Importance values:

LOW  
MODERATE  
HIGH  
CRITICAL

---

# **39\. Warning Contract**

\[  
  {  
    "code": "ORDERBOOK\_SNAPSHOT\_LIMITATION",  
    "severity": "WARNING",  
    "message": "Antrean orderbook dapat berubah dan tidak boleh dianggap sebagai kepastian.",  
    "related\_section": "orderbook\_analysis"  
  }  
\]

Warning severity:

INFORMATIONAL  
WARNING  
CRITICAL

---

# **40\. Canonical State Proposal Contract**

The AI must provide a normalized proposal for application validation.

{  
  "proposed\_thesis\_status": "INTACT\_BUT\_WEAKENING",  
  "proposed\_directional\_bias": "BULLISH",  
  "proposed\_confidence\_score": 68,  
  "proposed\_target\_probability": 62,  
  "proposed\_risk\_level": "ELEVATED",  
  "proposed\_position\_health": "HEALTHY\_BUT\_VOLATILE",  
  "proposed\_recommended\_action": "HOLD\_WITH\_CAUTION",  
  "proposed\_key\_levels": \[\],  
  "requires\_thesis\_version": true,  
  "requires\_context\_summary\_refresh": true,  
  "canonicalization\_recommendation": "ACCEPT"  
}

This proposal must not contain actual user-execution mutations.

---

# **41\. Initial Analysis Specification**

## **41.1 Purpose**

Generate the first complete assessment of a Trade Session.

## **41.2 Preconditions**

* ticker exists;  
* orderbook screenshot exists;  
* three-month chart exists;  
* six-month chart exists;  
* evidence is available;  
* no canonical initial analysis exists.

## **41.3 Required Inputs**

* session identity;  
* initial evidence;  
* user notes;  
* market snapshot when available;  
* no active position.

## **41.4 Required Output Sections**

1. Executive Summary  
2. Today’s Market Summary  
3. Evidence Quality  
4. Orderbook Analysis  
5. Three-Month Chart Analysis  
6. Six-Month Chart Analysis  
7. Support and Resistance  
8. Initial Trading Thesis  
9. Entry Plan  
10. Stop-Loss Plan  
11. Target Plan  
12. Confidence Assessment  
13. Probability Assessments  
14. Risk Assessment  
15. Bullish Scenario  
16. Neutral Scenario  
17. Bearish Scenario  
18. Recommended Next Action  
19. Missing Data  
20. Warnings

---

# **42\. Initial Entry Plan Contract**

{  
  "applicable": true,  
  "ideal\_entry\_zone": {  
    "lower\_bound": 3050,  
    "upper\_bound": 3100,  
    "basis": "Area pullback dekat support."  
  },  
  "aggressive\_entry": {  
    "price": 3100,  
    "condition": "Bid tetap bertahan."  
  },  
  "conservative\_entry": {  
    "price": 3130,  
    "condition": "Breakout resistance terkonfirmasi."  
  },  
  "breakout\_entry": {},  
  "pullback\_entry": {},  
  "chase\_limit": {  
    "price": 3160,  
    "reason": "Di atas level ini risk-to-reward memburuk."  
  },  
  "avoid\_entry\_conditions": \[  
    "Support utama ditembus.",  
    "Offer meningkat tanpa penyerapan."  
  \]  
}

The AI may state that no valid entry is currently available.

---

# **43\. Initial Stop-Loss Plan Contract**

{  
  "recommended\_stop": 3020,  
  "technical\_basis": "Di bawah support mayor dan invalidation structure.",  
  "estimated\_downside\_percentage": 2.5806,  
  "invalidation\_reason": "Penurunan di bawah level ini merusak struktur higher low.",  
  "warnings": \[  
    "Stop loss harus disesuaikan dengan harga entry aktual."  
  \]  
}

The backend should recalculate downside from the actual entry before position opening.

---

# **44\. Initial Target Plan Contract**

{  
  "targets": \[  
    {  
      "target\_type": "TP1",  
      "price": 3250,  
      "technical\_basis": "Resistance terdekat pada chart tiga bulan.",  
      "achievement\_probability": 64,  
      "partial\_profit\_consideration": "Dapat dipertimbangkan jika offer resistance sangat tebal."  
    },  
    {  
      "target\_type": "TP2",  
      "price": 3380,  
      "technical\_basis": "Resistance mayor enam bulan.",  
      "achievement\_probability": 42,  
      "partial\_profit\_consideration": null  
    }  
  \],  
  "risk\_reward\_summary": "TP1 memberikan rasio risiko-imbalan yang masih layak.",  
  "revision\_conditions": \[  
    "Breakout resistance gagal.",  
    "Support mayor melemah."  
  \]  
}

---

# **45\. Watching Update Specification**

## **45.1 Purpose**

Reassess an analyzed setup before the user enters.

## **45.2 Required Historical Context**

* initial analysis;  
* current thesis;  
* latest watching analysis;  
* previous comparable evidence;  
* planned entry;  
* planned stop;  
* planned targets.

## **45.3 Required Output Focus**

* setup quality;  
* entry realism;  
* whether entry conditions have been met;  
* chase risk;  
* cancellation conditions;  
* thesis status;  
* what changed;  
* updated trading plan.

## **45.4 Required Additional Contract**

{  
  "setup\_assessment": {  
    "setup\_quality": "MODERATE",  
    "entry\_condition\_status": "NOT\_YET\_CONFIRMED",  
    "planned\_entry\_still\_valid": true,  
    "chase\_risk": "HIGH",  
    "cancellation\_condition\_triggered": false,  
    "explanation": "Harga naik mendekati chase limit tanpa peningkatan bid yang cukup."  
  }  
}

Entry-condition statuses:

CONFIRMED  
PARTIALLY\_CONFIRMED  
NOT\_YET\_CONFIRMED  
MISSED  
INVALIDATED

---

# **46\. Open Position Update Specification**

## **46.1 Purpose**

Provide detailed analysis for an actual open or partially closed position.

## **46.2 Required Historical Context**

* initial thesis;  
* entry thesis snapshot;  
* actual entries;  
* average entry;  
* active stop;  
* active targets;  
* exits;  
* previous open-position analysis;  
* previous comparable evidence;  
* current evidence.

## **46.3 Required Output Sections**

1. Executive Summary  
2. Latest Market Summary  
3. What the Orderbook Shows  
4. What Changed Since Previous Update  
5. Current Position Assessment  
6. Thesis Status  
7. Target Realism  
8. Stop-Loss Assessment  
9. Confidence  
10. Probabilities  
11. Risk  
12. Time-Aware Trading Plan  
13. Recommended Action  
14. Missing Data and Warnings

---

# **47\. Open Position Summary Requirements**

The output must explicitly answer:

* Is the position still healthy?  
* Is the thesis still valid?  
* Is the target still realistic?  
* Is the stop still appropriate?  
* Has the probability of reaching target increased or decreased?  
* Has the probability of pullback increased or decreased?  
* Has the probability of stop-loss touch increased or decreased?  
* Should the user hold, reduce risk, consider partial profit, or review exit?  
* What should the user monitor next?

No open-position analysis is valid if these questions are omitted.

---

# **48\. Time-Aware Analysis Requirements**

## **48.1 Morning Update**

Focus on:

* opening behavior;  
* gap when data exists;  
* bid defense;  
* offer pressure;  
* continuity from prior close;  
* plan until midday.

## **48.2 Midday Update**

Focus on:

* change from morning;  
* whether bids strengthened or weakened;  
* whether offers were absorbed;  
* target realism;  
* plan until close.

## **48.3 Closing Update**

Focus on:

* full-day OHLC;  
* average price;  
* closing orderbook;  
* daily thesis status;  
* overnight risk;  
* plan for the next trading day.

## **48.4 Custom Update**

Focus on the stated reason and compare with the most relevant previous checkpoint.

---

# **49\. Partial Exit Review Specification**

## **49.1 Purpose**

Evaluate the remaining position after an actual partial exit.

## **49.2 Required Inputs**

* original position;  
* actual partial exit;  
* realized P/L;  
* remaining quantity;  
* remaining cost basis;  
* active stop;  
* remaining targets;  
* active thesis;  
* related AI recommendation, when any.

## **49.3 Required Output**

{  
  "partial\_exit\_review": {  
    "execution\_quality": "GOOD",  
    "reason\_alignment": "ALIGNED\_WITH\_PLAN",  
    "realized\_risk\_reduction": "MODERATE",  
    "remaining\_position\_health": "HEALTHY",  
    "remaining\_position\_plan": "Pertahankan sisa posisi menuju TP2 dengan stop yang diperketat.",  
    "stop\_adjustment\_recommendation": {},  
    "target\_adjustment\_recommendation": {}  
  }  
}

The AI must distinguish:

* AI recommendation;  
* actual user execution;  
* remaining position plan.

---

# **50\. Closing Analysis Specification**

## **50.1 Purpose**

Produce an immediate evaluation after the position is fully closed.

## **50.2 Required Inputs**

* all entries;  
* all exits;  
* final result;  
* final exit reason;  
* active thesis before exit;  
* current thesis;  
* latest analysis;  
* stop and target at exit;  
* major timeline events.

## **50.3 Required Output Sections**

1. Exit Summary  
2. Final Result  
3. Final Thesis Assessment  
4. Exit Quality  
5. Plan Compliance  
6. Major Timeline Events  
7. Preliminary Lessons  
8. Journal Eligibility

---

# **51\. Closing Analysis Contract**

{  
  "exit\_summary": {  
    "exit\_reason": "STOP\_LOSS",  
    "average\_entry": 3090,  
    "average\_exit": 2820,  
    "return\_percentage": \-8.7379,  
    "holding\_duration\_days": 4,  
    "summary": "Posisi ditutup setelah stop loss terlewati."  
  },  
  "final\_thesis\_assessment": {  
    "status\_at\_exit": "INVALIDATED",  
    "invalidation\_detected\_before\_exit": true,  
    "invalidation\_timing\_quality": "TIMELY",  
    "explanation": "Support mayor telah ditembus sebelum exit final."  
  },  
  "exit\_quality": {  
    "classification": "LATE",  
    "explanation": "Exit dilakukan di bawah stop aktif sehingga terdapat slippage terhadap rencana."  
  },  
  "plan\_compliance": {  
    "classification": "PARTIALLY\_COMPLIANT",  
    "deviations": \[  
      "Exit dilakukan setelah harga melewati stop."  
    \]  
  },  
  "preliminary\_lessons": \[\]  
}

---

# **52\. Trading Journal Analysis Specification**

The `TRADING_JOURNAL` output is detailed in the journal domain, but must use the same structured validation principles.

The journal must not:

* rewrite history;  
* use hindsight as if it were available earlier;  
* merge AI recommendations with user actions;  
* omit losing trades;  
* hide deviations from plan.

Journal-specific schema will be expanded in `AI_EVALUATION_PLAN.md` or a dedicated future journal specification if needed.

---

# **53\. Context Summary Specification**

## **53.1 Purpose**

Compress long session history while preserving critical context.

## **53.2 Required Output**

{  
  "active\_thesis\_summary": {},  
  "position\_summary": {},  
  "key\_level\_summary": {},  
  "update\_history\_summary": \[\],  
  "thesis\_change\_summary": \[\],  
  "current\_risks": \[\],  
  "unresolved\_questions": \[\],  
  "latest\_plan\_summary": {},  
  "critical\_facts\_that\_must\_not\_be\_removed": \[\],  
  "source\_cutoff": "timestamp"  
}

## **53.3 Required Preservation**

The summary must preserve:

* original thesis;  
* current thesis;  
* entry;  
* stop;  
* targets;  
* invalidation;  
* major thesis changes;  
* partial exits;  
* unresolved critical risks.

---

# **54\. Thesis Review Specification**

## **54.1 Purpose**

Resolve uncertainty when thesis status is `UNDER_REVIEW` or contradiction detection requires focused review.

## **54.2 Required Output**

{  
  "review\_result": "KEEP\_UNDER\_REVIEW",  
  "proposed\_thesis\_status": "UNDER\_REVIEW",  
  "resolved\_questions": \[\],  
  "unresolved\_questions": \[\],  
  "required\_confirmation": \[\],  
  "defensive\_action": "Jangan tambah posisi sampai support terkonfirmasi.",  
  "change\_reason": "Evidence masih saling bertentangan."  
}

Review results:

RESTORE\_INTACT  
MARK\_WEAKENING  
KEEP\_UNDER\_REVIEW  
INVALIDATE  
REJECT\_NEW\_ANALYSIS

---

# **55\. No-Material-Change Behavior**

When no material change exists:

* `material_change_exists` must be false;  
* thesis status should normally remain unchanged;  
* support and resistance should remain unchanged;  
* probabilities may remain unchanged;  
* recommended action may be `NO_MATERIAL_CHANGE` or preserve the existing action;  
* the AI must not manufacture differences.

Example:

{  
  "change\_summary": {  
    "material\_change\_exists": false,  
    "overall\_change\_summary": "Tidak terdapat perubahan material sejak update sebelumnya."  
  },  
  "thesis\_assessment": {  
    "previous\_status": "INTACT",  
    "proposed\_status": "INTACT",  
    "change\_type": "UNCHANGED",  
    "change\_reason": "Evidence terbaru masih konsisten dengan kondisi sebelumnya."  
  }  
}

---

# **56\. Thesis Change Requirements**

A proposed thesis change is invalid unless it includes:

* previous status;  
* proposed status;  
* change type;  
* change reason;  
* supporting evidence;  
* conflicting evidence;  
* impact on key levels;  
* confidence impact;  
* probability impact;  
* trading-plan impact.

Thesis invalidation additionally requires:

* specific invalidation condition;  
* evidence that the condition occurred;  
* impact on current position;  
* defensive recommendation.

---

# **57\. Analysis Type Applicability Matrix**

| Output Section | Initial | Watching | Open Position | Partial Exit | Closing |
| ----- | ----- | ----- | ----- | ----- | ----- |
| Executive Summary | Required | Required | Required | Required | Required |
| Market Summary | Required when available | Required | Required | Optional | Final summary |
| Orderbook Analysis | Required | Required | Required | Optional | Optional |
| Chart Analysis | Required | When updated | When updated | Optional | Historical |
| Change Summary | Not applicable | Required | Required | Required | Required |
| Thesis Assessment | Required | Required | Required | Required | Final |
| Position Assessment | Not applicable | Not applicable | Required | Required | Final |
| Entry Plan | Required | Required | Not applicable | Not applicable | Not applicable |
| Stop Assessment | Proposed | Proposed | Required | Required | Historical |
| Target Assessment | Proposed | Proposed | Required | Required | Historical |
| Confidence | Required | Required | Required | Required | Optional |
| Probabilities | Required | Required | Required | Optional | Optional |
| Trading Plan | Required | Required | Required | Required | Not active |
| Recommended Action | Required | Required | Required | Required | Review only |
| Closing Review | No | No | No | No | Required |

---

# **58\. Numerical Validation Rules**

The validator must enforce:

* confidence between 0 and 100;  
* probability between 0 and 100;  
* prices greater than zero;  
* zones with lower bound less than or equal to upper bound;  
* quantities non-negative;  
* target and stop references consistent with input;  
* previous values matching supplied history where required;  
* calculated values within a configured tolerance.

System-calculated values should replace AI-calculated values in the persisted canonical payload where applicable.

---

# **59\. Language Validation Rules**

Narrative fields must be validated for Bahasa Indonesia.

Validation should detect:

* output predominantly in English;  
* empty narrative fields;  
* raw enum values used as the only explanation;  
* malformed text;  
* provider refusal text;  
* unrelated content.

Permitted English terms may include:

* orderbook;  
* bullish;  
* bearish;  
* breakout;  
* pullback;  
* support;  
* resistance;  
* stop loss;  
* target profit;  
* confidence;  
* probability;  
* partial profit;  
* average down.

The surrounding explanation must remain in Bahasa Indonesia.

---

# **60\. Required-Field Validation**

An analysis is invalid when required fields for its type are missing.

Examples:

## **60.1 Initial Analysis Invalid When Missing**

* thesis;  
* support;  
* resistance;  
* entry plan;  
* stop plan;  
* targets;  
* confidence;  
* probabilities;  
* scenarios.

## **60.2 Open Position Analysis Invalid When Missing**

* actual position assessment;  
* target realism;  
* stop assessment;  
* thesis status;  
* what changed;  
* required probabilities;  
* trading plan;  
* recommended action.

---

# **61\. Logical Validation Rules**

The validator must detect cases such as:

* thesis invalidated but action says add position;  
* target unrealistic but target probability is extremely high without explanation;  
* confidence high while all evidence is unreadable;  
* position closed but active holding recommendation exists;  
* stop change recommended without reason;  
* target change recommended without reason;  
* no material change but thesis status reverses;  
* additional entry recommended while thesis is invalidated;  
* exact values supplied without evidence or input support.

---

# **62\. Contradiction Detection Inputs**

The contradiction detector must compare:

* current analysis;  
* latest accepted analysis;  
* active thesis;  
* active levels;  
* active stop;  
* active targets;  
* previous confidence;  
* previous probabilities;  
* previous recommended action;  
* position version.

---

# **63\. Contradiction Outcomes**

PASS  
PASS\_WITH\_EXPLANATION  
REVIEW\_REQUIRED  
REJECT

## **63.1 PASS**

No material contradiction.

## **63.2 PASS\_WITH\_EXPLANATION**

A change exists and is adequately explained.

## **63.3 REVIEW\_REQUIRED**

The change may be valid, but evidence or reasoning is insufficient for automatic canonicalization.

## **63.4 REJECT**

The output is logically incompatible or unsafe to use as canonical state.

---

# **64\. Canonicalization Eligibility**

An analysis may become accepted when:

* schema validation passes;  
* required fields are present;  
* narrative language passes;  
* numerical validation passes;  
* logical validation passes;  
* contradiction status is `PASS` or `PASS_WITH_EXPLANATION`;  
* analysis is not stale relative to critical session or position state;  
* evidence references are valid;  
* job has not been cancelled.

---

# **65\. Stale Analysis Handling**

An analysis may become stale when:

* position version changed during processing;  
* stop loss changed;  
* target changed;  
* entry or exit was recorded;  
* evidence was excluded;  
* session was closed;  
* analysis request was cancelled.

Stale output may be:

* stored as `NON_CANONICAL`;  
* shown as outdated historical analysis;  
* rejected;  
* regenerated.

It must not overwrite current canonical state.

---

# **66\. AI Response Repair Pipeline**

Recommended sequence:

1. parse provider structured response;  
2. attempt deterministic JSON cleanup;  
3. validate schema;  
4. request provider correction using the same source result;  
5. retry provider call when eligible;  
6. use fallback provider when configured;  
7. fail the job.

Repair must not change business facts silently.

---

# **67\. Failure Codes**

Recommended analysis failure codes:

AI\_PROVIDER\_TIMEOUT  
AI\_PROVIDER\_AUTHENTICATION\_FAILED  
AI\_PROVIDER\_RATE\_LIMITED  
AI\_PROVIDER\_UNAVAILABLE  
AI\_PROVIDER\_UNSUPPORTED\_CAPABILITY  
AI\_RESPONSE\_EMPTY  
AI\_RESPONSE\_NOT\_JSON  
AI\_RESPONSE\_SCHEMA\_INVALID  
AI\_RESPONSE\_LANGUAGE\_INVALID  
AI\_RESPONSE\_LOGIC\_INVALID  
AI\_RESPONSE\_CONTRADICTORY  
AI\_RESPONSE\_STALE  
EVIDENCE\_UNAVAILABLE  
EVIDENCE\_UNREADABLE  
CONTEXT\_BUILD\_FAILED  
CONTEXT\_TOO\_LARGE  
CANONICALIZATION\_FAILED  
JOB\_CANCELLED

---

# **68\. Retry Rules**

Retry is generally allowed for:

* timeout;  
* rate limit;  
* temporary provider error;  
* invalid JSON;  
* schema-invalid response;  
* language-invalid response.

Retry should generally not occur automatically for:

* invalid lifecycle;  
* missing required evidence;  
* cancelled job;  
* stale position state;  
* unsupported provider capability;  
* thesis conflict requiring user review.

---

# **69\. Provider Fallback Rules**

Fallback may occur when:

* primary provider times out;  
* primary provider is temporarily unavailable;  
* primary provider returns unrepairable structured output;  
* provider lacks a required capability at runtime.

Fallback must not bypass:

* schema validation;  
* language validation;  
* contradiction detection;  
* stale-state validation.

---

# **70\. Analysis Persistence Requirements**

Every stored analysis version must include:

* session ID;  
* analysis request ID;  
* analysis type;  
* version number;  
* provider;  
* model;  
* prompt version;  
* schema version;  
* position snapshot;  
* session version snapshot;  
* evidence IDs;  
* structured payload;  
* validation status;  
* contradiction status;  
* language;  
* timestamps.

---

# **71\. Analysis Version Immutability**

After storage, the core analysis payload must not be edited.

Corrections require:

* new analysis request;  
* new analysis version;  
* correction reason;  
* reference to the corrected version;  
* optional canonical-pointer update.

---

# **72\. UI Rendering Rules**

The frontend must render structured fields into:

* summary cards;  
* comparison tables;  
* thesis panel;  
* position panel;  
* target realism card;  
* stop-loss card;  
* confidence card;  
* probability cards;  
* trading-plan scenarios;  
* warning banners.

The frontend must not depend on parsing Markdown headings from one large text field.

---

# **73\. Raw AI Output Handling**

Raw provider responses may be stored temporarily or in restricted diagnostic storage.

Raw output must not be displayed as the primary user analysis.

The user sees only:

* validated normalized output;  
* validation warnings where appropriate;  
* accepted historical versions.

---

# **74\. Model Prompt Safety Boundaries**

The prompt must instruct the AI:

* not to guarantee returns;  
* not to fabricate values;  
* not to execute trades;  
* not to ignore stop-loss discipline;  
* not to treat orderbook queues as certainty;  
* not to revise thesis without evidence;  
* not to use unsupported exact precision;  
* to state limitations.

These rules must also be enforced after generation.

---

# **75\. Analysis Quality Scoring**

The system may calculate an internal quality score based on:

* schema completeness;  
* evidence traceability;  
* language compliance;  
* required-section completeness;  
* contradiction result;  
* numerical support;  
* reasoning quality;  
* missing-data disclosure.

A quality score must not be confused with trading confidence.

---

# **76\. AI Analysis Evaluation Hooks**

Every analysis should preserve data needed for later evaluation:

* predicted probabilities;  
* active thesis;  
* recommended action;  
* current price;  
* target;  
* stop;  
* eventual outcome;  
* timestamps;  
* evidence quality;  
* provider and model.

This enables future evaluation of:

* probability calibration;  
* thesis consistency;  
* warning timeliness;  
* target realism;  
* stop-risk detection;  
* provider comparison.

---

# **77\. Example Open Position Output**

{  
  "schema\_version": "1.0",  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "language": "id-ID",  
  "ticker": "BBRI",  
  "executive\_summary": {  
    "condition\_summary": "Posisi masih berada dalam kondisi cukup sehat, tetapi tekanan offer meningkat dibandingkan update pagi.",  
    "directional\_bias": "BULLISH",  
    "setup\_quality": "MODERATE",  
    "primary\_opportunity": "Support 3.100 masih dipertahankan.",  
    "primary\_risk": "Offer 3.130 menjadi hambatan terdekat.",  
    "recommended\_next\_action": "Pertahankan posisi dengan waspada hingga penutupan."  
  },  
  "market\_summary": {  
    "open": 3100,  
    "high": 3150,  
    "low": 3070,  
    "last": 3120,  
    "close": null,  
    "average": 3110,  
    "best\_bid": 3110,  
    "best\_offer": 3120,  
    "unavailable\_fields": \[  
      "volume",  
      "transaction\_value"  
    \]  
  },  
  "change\_summary": {  
    "material\_change\_exists": true,  
    "overall\_change\_summary": "Bid melemah dan offer meningkat, tetapi support mayor belum rusak.",  
    "items": \[  
      {  
        "metric": "BID\_STRENGTH",  
        "previous\_value": "STRONG",  
        "current\_value": "MODERATE",  
        "change\_direction": "DECREASED",  
        "materiality": "MATERIAL",  
        "explanation": "Antrean bid terdekat lebih tipis dibandingkan pagi."  
      }  
    \],  
    "unchanged\_items": \[  
      {  
        "metric": "MAJOR\_SUPPORT",  
        "value": 3020,  
        "explanation": "Belum ada evidence yang mengubah support mayor."  
      }  
    \]  
  },  
  "thesis\_assessment": {  
    "previous\_status": "INTACT",  
    "proposed\_status": "INTACT\_BUT\_WEAKENING",  
    "directional\_bias": "BULLISH",  
    "thesis\_statement": "Thesis rebound masih valid selama support mayor bertahan.",  
    "change\_type": "WEAKENED",  
    "change\_reason": "Tekanan offer meningkat, tetapi invalidation belum terjadi.",  
    "supporting\_evidence": \[  
      "Harga masih berada di atas support mayor."  
    \],  
    "conflicting\_evidence": \[  
      "Bid intraday melemah."  
    \],  
    "invalidation\_condition": "Penutupan valid di bawah 3.020.",  
    "canonicalization\_recommendation": "ACCEPT"  
  },  
  "position\_assessment": {  
    "applicable": true,  
    "position\_health": "HEALTHY\_BUT\_VOLATILE",  
    "average\_entry": 3090,  
    "latest\_price": 3120,  
    "return\_percentage": 0.9709,  
    "thesis\_validity": "INTACT\_BUT\_WEAKENING",  
    "hold\_assessment": {  
      "is\_rational": true,  
      "explanation": "Support utama belum rusak."  
    },  
    "averaging\_down\_assessment": {  
      "recommended": false,  
      "explanation": "Jangan menambah posisi selama thesis melemah."  
    },  
    "exit\_assessment": {  
      "exit\_condition\_triggered": false,  
      "explanation": "Belum ada invalidation terkonfirmasi."  
    }  
  },  
  "stop\_loss\_assessment": {  
    "active\_stop": 2840,  
    "is\_still\_appropriate": true,  
    "appropriateness\_explanation": "Basis support mayor belum berubah.",  
    "proposed\_change": {  
      "recommended": false,  
      "proposed\_price": null,  
      "direction": "UNCHANGED",  
      "reason": "Belum ada alasan teknikal untuk mengubah stop."  
    }  
  },  
  "target\_assessment": {  
    "overall\_realism": "REALISTIC\_WITH\_CONDITIONS",  
    "summary": "Target masih realistis jika resistance 3.130 berhasil diserap.",  
    "targets": \[  
      {  
        "target\_type": "TP1",  
        "price": 3250,  
        "realism": "MODERATE",  
        "achievement\_probability": 62,  
        "nearest\_obstacles": \[  
          3130,  
          3200  
        \],  
        "required\_conditions": \[  
          "Support 3.100 tetap bertahan.",  
          "Offer 3.130 berhasil diserap."  
        \],  
        "recommended\_change": {  
          "action": "KEEP",  
          "proposed\_price": null,  
          "reason": "Struktur utama belum berubah."  
        }  
      }  
    \]  
  },  
  "confidence\_assessment": {  
    "score": 68,  
    "classification": "MODERATE",  
    "previous\_score": 74,  
    "score\_change": \-6,  
    "drivers": \[  
      "Support mayor masih terjaga."  
    \],  
    "reducers": \[  
      "Orderbook melemah."  
    \],  
    "evidence\_quality": "MODERATE\_CONFIDENCE",  
    "missing\_data": \[  
      "Volume transaksi."  
    \],  
    "explanation": "Confidence turun karena orderbook melemah."  
  },  
  "probability\_assessments": \[  
    {  
      "probability\_type": "TARGET\_ACHIEVEMENT",  
      "percentage": 62,  
      "previous\_percentage": 68,  
      "change\_direction": "DECREASED",  
      "reasoning": "Offer meningkat dekat resistance.",  
      "supporting\_evidence": \[\],  
      "uncertainty\_level": "MODERATE"  
    },  
    {  
      "probability\_type": "PULLBACK",  
      "percentage": 48,  
      "previous\_percentage": 38,  
      "change\_direction": "INCREASED",  
      "reasoning": "Bid intraday menipis.",  
      "supporting\_evidence": \[\],  
      "uncertainty\_level": "MODERATE"  
    },  
    {  
      "probability\_type": "STOP\_LOSS\_TOUCH",  
      "percentage": 22,  
      "previous\_percentage": 18,  
      "change\_direction": "INCREASED",  
      "reasoning": "Risiko meningkat, tetapi jarak ke stop masih cukup jauh.",  
      "supporting\_evidence": \[\],  
      "uncertainty\_level": "HIGH"  
    },  
    {  
      "probability\_type": "THESIS\_REMAINS\_VALID",  
      "percentage": 70,  
      "previous\_percentage": 76,  
      "change\_direction": "DECREASED",  
      "reasoning": "Support mayor masih bertahan.",  
      "supporting\_evidence": \[\],  
      "uncertainty\_level": "MODERATE"  
    },  
    {  
      "probability\_type": "THESIS\_INVALIDATION",  
      "percentage": 30,  
      "previous\_percentage": 24,  
      "change\_direction": "INCREASED",  
      "reasoning": "Tekanan jual meningkat tetapi invalidation belum terjadi.",  
      "supporting\_evidence": \[\],  
      "uncertainty\_level": "MODERATE"  
    }  
  \],  
  "risk\_assessment": {  
    "level": "ELEVATED",  
    "primary\_risks": \[  
      "Offer meningkat.",  
      "Bid menipis."  
    \],  
    "mitigation": \[  
      "Jangan tambah posisi.",  
      "Disiplin pada stop loss."  
    \]  
  },  
  "trading\_plan": {  
    "plan\_horizon": "UNTIL\_MARKET\_CLOSE",  
    "bullish\_scenario": {  
      "trigger": "Harga menembus 3.130.",  
      "expected\_behavior": "Momentum menuju resistance berikutnya.",  
      "user\_action": "Pertahankan posisi.",  
      "invalidation": "Harga kembali di bawah 3.100."  
    },  
    "neutral\_scenario": {  
      "trigger": "Harga bergerak di 3.100–3.130.",  
      "expected\_behavior": "Konsolidasi.",  
      "user\_action": "Tunggu tanpa menambah posisi.",  
      "invalidation": "Range pecah ke bawah."  
    },  
    "bearish\_scenario": {  
      "trigger": "Harga kehilangan 3.100.",  
      "expected\_behavior": "Risiko pullback meningkat.",  
      "user\_action": "Evaluasi risiko dan disiplin pada stop.",  
      "invalidation": "Harga kembali di atas 3.110."  
    },  
    "prohibited\_actions": \[  
      "Jangan average down.",  
      "Jangan memperlebar stop."  
    \],  
    "next\_checkpoint": "Update penutupan",  
    "recommended\_action": "HOLD\_WITH\_CAUTION"  
  },  
  "recommended\_action": {  
    "action": "HOLD\_WITH\_CAUTION",  
    "display\_label": "Pertahankan dengan Waspada",  
    "rationale": "Thesis masih valid tetapi orderbook melemah.",  
    "conditions": \[  
      "Support 3.100 bertahan."  
    \],  
    "invalidation": \[  
      "Support ditembus dengan tekanan jual."  
    \],  
    "time\_horizon": "UNTIL\_MARKET\_CLOSE",  
    "risk\_level": "ELEVATED",  
    "requires\_user\_confirmation": false  
  },  
  "missing\_data": \[  
    {  
      "field": "volume",  
      "importance": "MODERATE",  
      "reason": "Tidak tersedia.",  
      "impact": "Mengurangi kualitas konfirmasi momentum.",  
      "recommended\_evidence": "Chart yang menampilkan volume."  
    }  
  \],  
  "warnings": \[  
    {  
      "code": "ORDERBOOK\_SNAPSHOT\_LIMITATION",  
      "severity": "WARNING",  
      "message": "Orderbook hanya merupakan snapshot dan dapat berubah.",  
      "related\_section": "orderbook\_analysis"  
    }  
  \],  
  "canonical\_state\_proposal": {  
    "proposed\_thesis\_status": "INTACT\_BUT\_WEAKENING",  
    "proposed\_directional\_bias": "BULLISH",  
    "proposed\_confidence\_score": 68,  
    "proposed\_target\_probability": 62,  
    "proposed\_risk\_level": "ELEVATED",  
    "proposed\_position\_health": "HEALTHY\_BUT\_VOLATILE",  
    "proposed\_recommended\_action": "HOLD\_WITH\_CAUTION",  
    "requires\_thesis\_version": true,  
    "requires\_context\_summary\_refresh": true,  
    "canonicalization\_recommendation": "ACCEPT"  
  }  
}

---

# **78\. Analysis Acceptance Criteria**

An AI analysis is accepted when:

1. the response matches the active JSON schema;  
2. the analysis type matches the request;  
3. English keys and enum values are used;  
4. narrative fields are in Bahasa Indonesia;  
5. required sections exist;  
6. exact values are supported by input or reliable extraction;  
7. confidence and probabilities are valid;  
8. recommendations contain reasons and conditions;  
9. follow-up analysis contains historical comparison;  
10. thesis changes contain evidence and explanation;  
11. open-position analysis uses actual entry, stop, and targets;  
12. target realism is assessed;  
13. stop-loss appropriateness is assessed;  
14. missing data is disclosed;  
15. logical validation passes;  
16. contradiction detection passes;  
17. the result is not stale;  
18. evidence references are valid;  
19. the request was not cancelled;  
20. canonicalization succeeds transactionally.

---

# **79\. Prohibited Analysis Behavior**

The AI analysis system must not:

1. analyze the newest screenshot in isolation;  
2. output only BUY, HOLD, or SELL;  
3. guarantee profit;  
4. invent unreadable values;  
5. silently change thesis;  
6. silently change stop loss;  
7. silently change targets;  
8. recommend additional entry after thesis invalidation;  
9. recommend widening stop only to avoid realizing a loss;  
10. treat large orderbook queues as guaranteed intent;  
11. hide missing data;  
12. present probability as certainty;  
13. overwrite previous analysis;  
14. ignore actual user position;  
15. use outdated stop or target values;  
16. recommend active position management after closure;  
17. rewrite history in closing analysis or journal;  
18. use English as the normal user-facing narrative;  
19. become canonical before validation;  
20. execute position mutations.

---

# **80\. Final AI Analysis Statement**

TradePilot AI analysis must function as a structured, longitudinal, evidence-based trading assessment.

Every analysis must explain:

* what is currently visible;  
* what has changed;  
* why the change matters;  
* whether the thesis remains valid;  
* whether the target remains realistic;  
* whether the stop remains appropriate;  
* what risks are increasing;  
* what action or observation is appropriate next.

The AI must preserve continuity across the full Trade Session and must never reduce the trade story to a single screenshot or unsupported directional opinion.

