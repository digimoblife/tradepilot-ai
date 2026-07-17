# **TradePilot AI — Analysis Schema Specification**

**Document:** `ANALYSIS_SCHEMA_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Schema Standard:** JSON Schema Draft 2020-12  
**Primary References:** `AI_ANALYSIS_SPEC.md`, `THESIS_ENGINE_SPEC.md`, `CONTEXT_MEMORY_SPEC.md`, `PROBABILITY_CONFIDENCE_SPEC.md`, `AI_PROVIDER_SPEC.md`, `PROMPT_SPEC.md`  
**Purpose:** Define the technical JSON Schema architecture, shared definitions, analysis-specific contracts, validation rules, conditional requirements, schema versioning, provider transformations, and implementation requirements for every structured AI output.

---

## **1\. Document Purpose**

This document defines the authoritative technical contract for structured AI analysis output.

It specifies:

* JSON Schema standard;  
* schema directory structure;  
* naming conventions;  
* shared reusable definitions;  
* top-level analysis envelopes;  
* required fields for each analysis type;  
* controlled enum values;  
* null and unavailable-value rules;  
* conditional validation;  
* cross-field validation;  
* application-side validation beyond JSON Schema;  
* provider-specific schema transformation;  
* schema versioning;  
* compatibility;  
* testing;  
* generation of typed application models.

The actual schema files will be implemented separately, including:

initial\_analysis.schema.json  
watching\_update.schema.json  
open\_position\_update.schema.json  
partial\_exit\_review.schema.json  
closing\_analysis.schema.json  
trading\_journal.schema.json  
context\_summary.schema.json  
thesis\_review.schema.json

---

# **2\. Schema Design Principles**

## **2.1 Structured Output Is the Authoritative AI Contract**

AI provider output is accepted only when it can be normalized into a JSON object that conforms to the requested schema.

Free-form analysis is not an alternative authoritative format.

---

## **2.2 English Keys and Enums**

All:

* property names;  
* object names;  
* enum values;  
* schema identifiers;  
* definition names;

must use English.

Narrative values displayed to the user must use Bahasa Indonesia.

---

## **2.3 Strict Objects**

Unless explicitly stated otherwise, every object must use:

{  
  "additionalProperties": false  
}

This prevents providers from silently inventing unsupported fields.

---

## **2.4 Required Fields Must Be Explicit**

Every schema must declare required fields.

The application must not infer required fields only from prompt wording.

---

## **2.5 Unknown Is Not Zero**

Unavailable values must use:

null

when the schema allows null.

Do not use:

0

to represent unknown:

* price;  
* quantity;  
* probability;  
* confidence;  
* volume;  
* cost;  
* percentage.

---

## **2.6 Exact Facts and Narrative Are Separate**

Structured numerical facts should have typed numeric fields.

Their analytical explanation should use separate narrative fields.

Example:

{  
  "percentage": 62,  
  "reasoning": "Target masih mungkin dicapai, tetapi resistance terdekat belum ditembus."  
}

---

## **2.7 Schema Validation Is Necessary but Not Sufficient**

JSON Schema validates:

* structure;  
* types;  
* required properties;  
* enums;  
* basic ranges;  
* conditional presence.

Application validators must additionally validate:

* chronology;  
* arithmetic;  
* session ownership;  
* stale state;  
* thesis transition;  
* probability coherence;  
* source references;  
* language;  
* analytical logic.

---

# **3\. JSON Schema Standard**

All schemas must use:

JSON Schema Draft 2020-12

Required declaration:

{  
  "$schema": "https://json-schema.org/draft/2020-12/schema"  
}

Each root schema must define a stable `$id`.

Example:

{  
  "$id": "https://schemas.tradepilot.local/analysis/open-position-update/1.0.0"  
}

The URI acts as an identifier and does not require public internet hosting.

---

# **4\. Schema Versioning**

Schema versions use semantic versioning:

MAJOR.MINOR.PATCH

## **4.1 Major Version**

Increase when:

* a required field is removed or renamed;  
* enum meaning changes;  
* object meaning changes;  
* existing payloads become incompatible;  
* a property type changes incompatibly.

## **4.2 Minor Version**

Increase when:

* an optional field is added;  
* a new enum is added compatibly;  
* a new optional object is introduced;  
* validation is expanded without invalidating valid prior payloads.

## **4.3 Patch Version**

Increase when:

* descriptions are clarified;  
* examples are corrected;  
* non-semantic metadata changes;  
* provider transformation is fixed without changing the canonical contract.

---

# **5\. Schema Version Representation**

Every root output must include:

{  
  "schema\_version": "1.0.0"  
}

The value must equal the requested schema version.

The backend must reject mismatches.

---

# **6\. Schema Directory Structure**

Recommended structure:

schemas/  
├── analysis/  
│   ├── v1/  
│   │   ├── initial\_analysis.schema.json  
│   │   ├── watching\_update.schema.json  
│   │   ├── open\_position\_update.schema.json  
│   │   ├── partial\_exit\_review.schema.json  
│   │   ├── closing\_analysis.schema.json  
│   │   ├── trading\_journal.schema.json  
│   │   ├── context\_summary.schema.json  
│   │   └── thesis\_review.schema.json  
│   │  
│   └── common/  
│       └── v1/  
│           ├── identifiers.schema.json  
│           ├── market.schema.json  
│           ├── evidence.schema.json  
│           ├── levels.schema.json  
│           ├── thesis.schema.json  
│           ├── position.schema.json  
│           ├── probability.schema.json  
│           ├── confidence.schema.json  
│           ├── risk.schema.json  
│           ├── trading\_plan.schema.json  
│           ├── warnings.schema.json  
│           └── canonical\_proposal.schema.json  
│  
└── manifest.json

---

# **7\. Schema Manifest**

The schema registry must expose a manifest.

Example:

{  
  "registry\_version": "1.0.0",  
  "schemas": \[  
    {  
      "name": "open\_position\_update",  
      "analysis\_type": "OPEN\_POSITION\_UPDATE",  
      "version": "1.0.0",  
      "path": "analysis/v1/open\_position\_update.schema.json",  
      "status": "ACTIVE",  
      "compatible\_prompt\_versions": \[  
        "1.0.0"  
      \]  
    }  
  \]  
}

---

# **8\. Root Analysis Envelope**

All primary analysis schemas should share these root properties:

{  
  "schema\_version": "1.0.0",  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "language": "id-ID",  
  "analysis\_timestamp": "2026-07-17T05:30:00Z",  
  "ticker": "BBRI",  
  "data\_quality": {},  
  "executive\_summary": {},  
  "missing\_data": \[\],  
  "warnings": \[\],  
  "canonical\_state\_proposal": {}  
}

Root objects must use:

{  
  "type": "object",  
  "additionalProperties": false  
}

---

# **9\. Root Required Properties**

All analysis output types require:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
missing\_data  
warnings

`canonical_state_proposal` is required for:

INITIAL\_ANALYSIS  
WATCHING\_UPDATE  
OPEN\_POSITION\_UPDATE  
PARTIAL\_EXIT\_REVIEW  
THESIS\_REVIEW

It is optional or not applicable for:

CLOSING\_ANALYSIS  
TRADING\_JOURNAL  
CONTEXT\_SUMMARY

---

# **10\. Common Primitive Definitions**

## **10.1 UUID**

{  
  "$defs": {  
    "uuid": {  
      "type": "string",  
      "format": "uuid"  
    }  
  }  
}

---

## **10.2 Timestamp**

{  
  "$defs": {  
    "timestamp": {  
      "type": "string",  
      "format": "date-time"  
    }  
  }  
}

---

## **10.3 Trading Date**

{  
  "$defs": {  
    "tradingDate": {  
      "type": "string",  
      "format": "date"  
    }  
  }  
}

---

## **10.4 Non-Empty Narrative**

{  
  "$defs": {  
    "narrative": {  
      "type": "string",  
      "minLength": 1,  
      "maxLength": 5000  
    }  
  }  
}

Language validation remains application-side.

---

## **10.5 Percentage**

For analytical estimates:

{  
  "$defs": {  
    "percentage": {  
      "type": "number",  
      "minimum": 0,  
      "maximum": 100  
    }  
  }  
}

For unavailable estimates:

{  
  "$defs": {  
    "nullablePercentage": {  
      "type": \[  
        "number",  
        "null"  
      \],  
      "minimum": 0,  
      "maximum": 100  
    }  
  }  
}

---

## **10.6 Price**

{  
  "$defs": {  
    "price": {  
      "type": "number",  
      "exclusiveMinimum": 0  
    },  
    "nullablePrice": {  
      "type": \[  
        "number",  
        "null"  
      \],  
      "exclusiveMinimum": 0  
    }  
  }  
}

Because JSON Schema validators may apply numeric bounds inconsistently to null unions, generated schemas may instead use:

{  
  "anyOf": \[  
    {  
      "type": "number",  
      "exclusiveMinimum": 0  
    },  
    {  
      "type": "null"  
    }  
  \]  
}

---

## **10.7 Quantity**

{  
  "$defs": {  
    "nullableQuantity": {  
      "anyOf": \[  
        {  
          "type": "number",  
          "exclusiveMinimum": 0  
        },  
        {  
          "type": "null"  
        }  
      \]  
    }  
  }  
}

---

# **11\. Common Enum Definitions**

All controlled enums should be centralized.

---

## **11.1 Analysis Type**

{  
  "$defs": {  
    "analysisType": {  
      "type": "string",  
      "enum": \[  
        "INITIAL\_ANALYSIS",  
        "WATCHING\_UPDATE",  
        "OPEN\_POSITION\_UPDATE",  
        "PARTIAL\_EXIT\_REVIEW",  
        "CLOSING\_ANALYSIS",  
        "TRADING\_JOURNAL",  
        "CONTEXT\_SUMMARY",  
        "THESIS\_REVIEW"  
      \]  
    }  
  }  
}

---

## **11.2 Directional Bias**

BULLISH  
NEUTRAL  
BEARISH  
MIXED

---

## **11.3 Thesis Status**

STRENGTHENING  
INTACT  
INTACT\_BUT\_WEAKENING  
UNDER\_REVIEW  
INVALIDATED

---

## **11.4 Recommended Action**

WAIT\_FOR\_CONFIRMATION  
HOLD\_POSITION  
HOLD\_WITH\_CAUTION  
CONSIDER\_PARTIAL\_PROFIT  
REDUCE\_RISK  
REVIEW\_EXIT  
DO\_NOT\_ADD  
CANCEL\_SETUP  
NO\_MATERIAL\_CHANGE

---

## **11.5 Risk Level**

LOW  
MODERATE  
ELEVATED  
HIGH  
CRITICAL

---

## **11.6 Position Health**

HEALTHY  
HEALTHY\_BUT\_VOLATILE  
WEAKENING  
HIGH\_RISK  
EXIT\_CONDITION\_TRIGGERED  
NOT\_APPLICABLE

---

## **11.7 Uncertainty Level**

LOW  
MODERATE  
HIGH

---

## **11.8 Change Direction**

INCREASED  
DECREASED  
UNCHANGED  
NOT\_COMPARABLE

---

# **12\. Data Quality Definition**

Recommended schema:

{  
  "$defs": {  
    "dataQuality": {  
      "type": "object",  
      "additionalProperties": false,  
      "required": \[  
        "overall\_quality",  
        "evidence\_completeness\_score",  
        "image\_readability\_score",  
        "historical\_context\_quality",  
        "critical\_missing\_fields",  
        "limitations"  
      \],  
      "properties": {  
        "overall\_quality": {  
          "type": "string",  
          "enum": \[  
            "VERIFIED",  
            "HIGH\_CONFIDENCE",  
            "MODERATE\_CONFIDENCE",  
            "LOW\_CONFIDENCE",  
            "UNREADABLE",  
            "UNKNOWN"  
          \]  
        },  
        "evidence\_completeness\_score": {  
          "$ref": "\#/$defs/percentage"  
        },  
        "image\_readability\_score": {  
          "$ref": "\#/$defs/percentage"  
        },  
        "historical\_context\_quality": {  
          "type": "string",  
          "enum": \[  
            "HIGH\_CONFIDENCE",  
            "MODERATE\_CONFIDENCE",  
            "LOW\_CONFIDENCE",  
            "NOT\_APPLICABLE"  
          \]  
        },  
        "critical\_missing\_fields": {  
          "type": "array",  
          "items": {  
            "type": "string"  
          },  
          "uniqueItems": true  
        },  
        "limitations": {  
          "type": "array",  
          "items": {  
            "$ref": "\#/$defs/narrative"  
          }  
        }  
      }  
    }  
  }  
}

---

# **13\. Executive Summary Definition**

{  
  "$defs": {  
    "executiveSummary": {  
      "type": "object",  
      "additionalProperties": false,  
      "required": \[  
        "condition\_summary",  
        "directional\_bias",  
        "setup\_quality",  
        "primary\_opportunity",  
        "primary\_risk",  
        "recommended\_next\_action"  
      \],  
      "properties": {  
        "condition\_summary": {  
          "$ref": "\#/$defs/narrative"  
        },  
        "directional\_bias": {  
          "$ref": "\#/$defs/directionalBias"  
        },  
        "setup\_quality": {  
          "type": "string",  
          "enum": \[  
            "LOW",  
            "MODERATE",  
            "HIGH",  
            "NOT\_APPLICABLE"  
          \]  
        },  
        "primary\_opportunity": {  
          "$ref": "\#/$defs/narrative"  
        },  
        "primary\_risk": {  
          "$ref": "\#/$defs/narrative"  
        },  
        "recommended\_next\_action": {  
          "$ref": "\#/$defs/narrative"  
        }  
      }  
    }  
  }  
}

---

# **14\. Market Summary Definition**

Recommended object:

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
  "source\_summary": "Nilai berasal dari market snapshot yang disediakan sistem.",  
  "unavailable\_fields": \[  
    "volume",  
    "transaction\_value"  
  \]  
}

Required fields:

open  
high  
low  
last  
close  
previous\_close  
average  
absolute\_change  
percentage\_change  
volume  
transaction\_value  
best\_bid  
best\_offer  
source\_summary  
unavailable\_fields

Most numeric fields are nullable.

---

# **15\. Market Summary Schema Rules**

JSON Schema validates positive prices.

Application validation must verify:

high \>= low  
high \>= open when both exist  
high \>= last when both exist  
low \<= open when both exist  
low \<= last when both exist  
percentage\_change matches source values within tolerance  
spread \= best\_offer \- best\_bid when both exist

---

# **16\. Evidence Assessment Definition**

Required properties:

visible\_facts  
user\_provided\_facts  
system\_calculated\_facts  
interpretations  
assumptions  
uncertainties

Recommended shape:

{  
  "visible\_facts": \[\],  
  "user\_provided\_facts": \[\],  
  "system\_calculated\_facts": \[\],  
  "interpretations": \[\],  
  "assumptions": \[\],  
  "uncertainties": \[\]  
}

All are arrays of narrative strings.

The provider must not put interpretations inside `visible_facts`.

This separation requires application-side semantic validation.

---

# **17\. Price Level Definition**

A reusable `priceLevel` definition must support exact prices and zones.

{  
  "$defs": {  
    "priceLevel": {  
      "type": "object",  
      "additionalProperties": false,  
      "required": \[  
        "exact\_price",  
        "lower\_bound",  
        "upper\_bound",  
        "basis",  
        "source\_type",  
        "status",  
        "confidence\_score"  
      \],  
      "properties": {  
        "exact\_price": {  
          "$ref": "\#/$defs/nullablePrice"  
        },  
        "lower\_bound": {  
          "$ref": "\#/$defs/nullablePrice"  
        },  
        "upper\_bound": {  
          "$ref": "\#/$defs/nullablePrice"  
        },  
        "basis": {  
          "$ref": "\#/$defs/narrative"  
        },  
        "source\_type": {  
          "type": "string",  
          "enum": \[  
            "ORDERBOOK",  
            "CHART\_STRUCTURE",  
            "SWING\_HIGH",  
            "SWING\_LOW",  
            "HISTORICAL\_RANGE",  
            "AVERAGE\_PRICE",  
            "VOLUME\_ZONE",  
            "PSYCHOLOGICAL\_LEVEL",  
            "USER\_DEFINED",  
            "AI\_INFERRED"  
          \]  
        },  
        "status": {  
          "type": "string",  
          "enum": \[  
            "ACTIVE",  
            "BEING\_TESTED",  
            "BROKEN",  
            "CONFIRMED",  
            "NO\_LONGER\_RELEVANT",  
            "UNCONFIRMED"  
          \]  
        },  
        "confidence\_score": {  
          "$ref": "\#/$defs/percentage"  
        }  
      },  
      "oneOf": \[  
        {  
          "properties": {  
            "exact\_price": {  
              "type": "number",  
              "exclusiveMinimum": 0  
            },  
            "lower\_bound": {  
              "type": "null"  
            },  
            "upper\_bound": {  
              "type": "null"  
            }  
          }  
        },  
        {  
          "properties": {  
            "exact\_price": {  
              "type": "null"  
            },  
            "lower\_bound": {  
              "type": "number",  
              "exclusiveMinimum": 0  
            },  
            "upper\_bound": {  
              "type": "number",  
              "exclusiveMinimum": 0  
            }  
          }  
        }  
      \]  
    }  
  }  
}

Application validation must ensure:

lower\_bound \<= upper\_bound

---

# **18\. Level Assessment Definition**

Required keys:

immediate\_support  
major\_support  
thesis\_invalidation  
immediate\_resistance  
major\_resistance  
breakout\_confirmation

Each field may be:

* a valid `priceLevel`;  
* null when unavailable.

`thesis_invalidation` is required and non-null for all thesis-bearing analyses unless the thesis is under initial review because evidence is insufficient.

---

# **19\. Orderbook Analysis Definition**

Required properties:

applicable  
summary  
best\_bid  
best\_offer  
spread  
bid\_strength  
offer\_pressure  
bid\_concentration  
offer\_concentration  
buyer\_persistence  
seller\_aggression  
absorption\_assessment  
distribution\_assessment  
nearest\_orderbook\_support  
nearest\_orderbook\_resistance  
liquidity\_quality  
spoofing\_risk  
limitations

---

# **20\. Orderbook Applicability**

When `applicable = false`, require:

summary  
limitations

and require market-detail fields to be null or `UNKNOWN`.

Conditional validation should use `if`, `then`, and `else`.

Example:

{  
  "if": {  
    "properties": {  
      "applicable": {  
        "const": false  
      }  
    }  
  },  
  "then": {  
    "properties": {  
      "best\_bid": {  
        "type": "null"  
      },  
      "best\_offer": {  
        "type": "null"  
      },  
      "spread": {  
        "type": "null"  
      }  
    }  
  }  
}

---

# **21\. Chart Analysis Definitions**

The reusable `chartTimeframeAssessment` should contain:

available  
timeframe  
trend  
swing\_structure  
momentum  
volume\_behavior  
patterns  
support\_levels  
resistance\_levels  
breakout\_assessment  
breakdown\_assessment  
risk\_notes  
limitations

---

# **22\. Chart Trend Enums**

STRONGLY\_BULLISH  
BULLISH  
NEUTRAL  
BEARISH  
STRONGLY\_BEARISH  
MIXED  
UNKNOWN

---

# **23\. Swing Structure Enums**

HIGHER\_HIGH\_HIGHER\_LOW  
HIGHER\_LOW  
LOWER\_HIGH\_LOWER\_LOW  
LOWER\_HIGH  
RANGE  
BREAKOUT  
BREAKDOWN  
MIXED  
UNKNOWN

---

# **24\. Chart Pattern Definition**

{  
  "name": "Rebound structure",  
  "status": "POSSIBLE",  
  "explanation": "Harga membentuk higher low, tetapi breakout belum terkonfirmasi."  
}

Pattern status:

CONFIRMED  
POSSIBLE  
FAILED  
NOT\_CONFIRMED

The schema must require explanation.

---

# **25\. Change Summary Definition**

Required properties:

material\_change\_exists  
overall\_change\_summary  
items  
unchanged\_items

Each change item requires:

metric  
previous\_value  
current\_value  
change\_direction  
materiality  
explanation

Because previous and current values can be numbers, strings, objects, or null, their canonical schema may use:

{  
  "type": \[  
    "string",  
    "number",  
    "boolean",  
    "object",  
    "array",  
    "null"  
  \]  
}

Objects and arrays should remain shallow and controlled where possible.

---

# **26\. Change Materiality Enum**

NON\_MATERIAL  
MATERIAL  
CRITICAL  
NOT\_COMPARABLE

When:

{  
  "material\_change\_exists": false  
}

the `items` array must not contain `MATERIAL` or `CRITICAL` entries.

This requires application-side validation if provider schema compatibility limits conditional array checks.

---

# **27\. Thesis Assessment Definition**

Required properties:

previous\_status  
proposed\_status  
directional\_bias  
thesis\_statement  
change\_type  
change\_reason  
supporting\_evidence  
conflicting\_evidence  
key\_support  
key\_resistance  
invalidation\_level  
invalidation\_condition  
expected\_scenario  
canonicalization\_recommendation

`previous_status` may be null only for initial analysis.

---

# **28\. Thesis Change Type Enum**

CREATED  
STRENGTHENED  
UNCHANGED  
WEAKENED  
PLACED\_UNDER\_REVIEW  
INVALIDATED  
CORRECTED

---

# **29\. Thesis Canonicalization Recommendation**

ACCEPT  
KEEP\_PREVIOUS  
REVIEW\_REQUIRED

`REJECT` is an application validator outcome, not usually a model-requested canonicalization recommendation.

---

# **30\. Thesis Conditional Rules**

## **30.1 Initial Analysis**

Require:

previous\_status \= null  
change\_type \= CREATED  
proposed\_status \!= INVALIDATED

## **30.2 Unchanged Thesis**

When:

change\_type \= UNCHANGED

require:

previous\_status \= proposed\_status

## **30.3 Invalidated Thesis**

When:

proposed\_status \= INVALIDATED

require:

change\_type \= INVALIDATED  
invalidation\_level \!= null  
conflicting\_evidence has at least one item

The exact invalidation evidence should be required through an additional `invalidation_evidence` field in relevant schemas.

---

# **31\. Invalidation Evidence Definition**

Recommended object:

{  
  "condition": "Penutupan valid di bawah 3.020.",  
  "observed\_event": "Harga ditutup pada 3.000.",  
  "confirmation\_type": "CLOSING\_BREAK",  
  "evidence\_ids": \[  
    "uuid"  
  \],  
  "evidence\_quality": "VERIFIED",  
  "observed\_at": "timestamp"  
}

Required only when proposing `INVALIDATED`.

---

# **32\. Position Assessment Definition**

Required properties:

applicable  
position\_health  
average\_entry  
latest\_price  
return\_percentage  
distance\_to\_stop\_percentage  
distance\_to\_nearest\_target\_percentage  
thesis\_validity  
hold\_assessment  
averaging\_down\_assessment  
partial\_profit\_assessment  
exit\_assessment

---

# **33\. Position Applicability**

For:

INITIAL\_ANALYSIS  
WATCHING\_UPDATE

position assessment should either:

* be omitted; or  
* use `applicable = false`.

The preferred approach is omission when the root schema does not require the property.

For:

OPEN\_POSITION\_UPDATE  
PARTIAL\_EXIT\_REVIEW  
CLOSING\_ANALYSIS

the position-related object is required.

---

# **34\. Hold Assessment Definition**

{  
  "is\_rational": true,  
  "explanation": "Support utama belum rusak."  
}

`is_rational` may be null when the position has closed.

---

# **35\. Action Recommendation Assessment**

Reusable recommendation objects should use:

recommended  
explanation  
requires\_user\_confirmation

When `recommended = true` for an execution mutation, `requires_user_confirmation` must be true.

Application validation must enforce this across:

* additional entry;  
* stop change;  
* target change;  
* partial exit;  
* full exit.

---

# **36\. Stop-Loss Assessment Definition**

Required properties:

applicable  
active\_stop  
technical\_basis  
is\_still\_appropriate  
appropriateness\_explanation  
distance\_from\_latest\_price\_percentage  
risk\_status  
proposed\_change  
warnings

For initial and watching analysis, use a separate `stop_loss_plan` schema because there is no active user-confirmed stop.

---

# **37\. Stop-Loss Change Definition**

{  
  "recommended": false,  
  "proposed\_price": null,  
  "direction": "UNCHANGED",  
  "reason": "Belum terdapat evidence untuk mengubah stop.",  
  "risk\_impact": null,  
  "thesis\_impact": null,  
  "requires\_user\_confirmation": false  
}

Direction enum:

TIGHTEN  
WIDEN  
UNCHANGED  
REMOVE

Conditional requirements:

* if `recommended = true`, `proposed_price` must be non-null except for `REMOVE`;  
* if direction is `UNCHANGED`, recommended must normally be false;  
* if direction is `WIDEN`, reason, risk impact, and thesis impact are required;  
* `REMOVE` is invalid for active position analysis unless paired with an immediate replacement in another explicit field.

---

# **38\. Target Assessment Definition**

Required properties:

applicable  
overall\_realism  
summary  
targets

Each target assessment requires:

target\_id  
target\_type  
price  
status  
realism  
achievement\_probability  
nearest\_obstacles  
required\_conditions  
recommended\_change

---

# **39\. Target Realism Enum**

HIGHLY\_REALISTIC  
STILL\_REALISTIC  
REALISTIC\_WITH\_CONDITIONS  
LESS\_REALISTIC  
UNREALISTIC  
NOT\_APPLICABLE

---

# **40\. Target Change Definition**

action  
proposed\_price  
reason  
requires\_user\_confirmation

Action enum:

KEEP  
LOWER  
RAISE  
DEACTIVATE  
ADD\_TARGET

Conditional rules:

* `KEEP` requires `proposed_price = null`;  
* `LOWER`, `RAISE`, and `ADD_TARGET` require non-null proposed price;  
* non-`KEEP` action requires user confirmation;  
* every action requires reason.

---

# **41\. Confidence Assessment Definition**

Required properties:

score  
classification  
previous\_score  
score\_change  
drivers  
reducers  
evidence\_quality  
context\_quality\_score  
missing\_data  
explanation

Conditional rules:

score 0–39      → LOW  
score 40–69     → MODERATE  
score 70–100    → HIGH

JSON Schema may encode this through `allOf` with conditional rules.

Application validation must recompute:

score\_change \= score \- previous\_score

when previous score exists.

When no comparable prior analysis exists:

previous\_score \= null  
score\_change \= null

---

# **42\. Probability Assessment Definition**

Required properties:

probability\_type  
event\_definition  
percentage  
previous\_percentage  
change\_direction  
change\_amount  
reasoning  
supporting\_evidence  
opposing\_evidence  
uncertainty\_level  
estimate\_basis  
valid\_until

---

# **43\. Probability Event Definition**

Because different probability types require different parameters, use a typed union through `oneOf`.

Examples:

## **43.1 Target Achievement Event**

Required:

target\_id  
target\_type  
target\_price  
competing\_condition  
competing\_price  
forecast\_horizon  
confirmation\_type

## **43.2 Stop-Loss Touch Event**

Required:

stop\_price  
stop\_version  
forecast\_horizon  
confirmation\_type

## **43.3 Thesis Event**

Required:

thesis\_version  
invalidation\_condition  
forecast\_horizon  
confirmation\_type

## **43.4 Pullback Event**

Required:

definition  
reference\_price  
forecast\_horizon  
confirmation\_type

---

# **44\. Probability Type Enum**

BULLISH\_CONTINUATION  
TARGET\_ACHIEVEMENT  
PULLBACK  
STOP\_LOSS\_TOUCH  
THESIS\_REMAINS\_VALID  
THESIS\_INVALIDATION  
MAJOR\_SUPPORT\_BREAK

---

# **45\. Probability Estimate Basis Enum**

AI\_ASSISTED  
RULE\_BASED  
HYBRID\_AI\_RULE\_BASED  
CALIBRATED\_MODEL

MVP provider output should normally use:

HYBRID\_AI\_RULE\_BASED

The backend must reject `CALIBRATED_MODEL` unless calibration is enabled.

---

# **46\. Probability Comparison Conditional Rules**

When:

change\_direction \= NOT\_COMPARABLE

require:

previous\_percentage \= null  
change\_amount \= null

When comparison is available:

previous\_percentage \!= null  
change\_amount \!= null

The application must verify the arithmetic.

---

# **47\. Probability Array Rules**

Each analysis type has required probability types.

The schema can require minimum array length but cannot reliably guarantee the presence of each unique probability type across all provider implementations.

Application validation must enforce:

* required type set;  
* no duplicate type-event pairs;  
* target ordering;  
* thesis coherence;  
* compatible horizons;  
* current target and stop references.

---

# **48\. Risk Assessment Definition**

Required properties:

level  
primary\_risks  
stop\_proximity  
thesis\_risk  
evidence\_risk  
execution\_risk  
mitigation

Risk component enums:

LOW  
MODERATE  
ELEVATED  
HIGH  
CRITICAL  
NOT\_APPLICABLE

---

# **49\. Trading Plan Definition**

Required properties:

plan\_horizon  
bullish\_scenario  
neutral\_scenario  
bearish\_scenario  
prohibited\_actions  
next\_checkpoint  
recommended\_action

Each scenario requires:

trigger  
expected\_behavior  
user\_action  
target  
invalidation

`target` may be null for neutral or bearish scenarios.

---

# **50\. Recommended Action Definition**

Required properties:

action  
display\_label  
rationale  
conditions  
invalidation  
time\_horizon  
risk\_level  
requires\_user\_confirmation  
proposed\_mutation

`proposed_mutation` may be null or an object describing:

ENTRY  
ADDITIONAL\_ENTRY  
STOP\_CHANGE  
TARGET\_CHANGE  
PARTIAL\_EXIT  
FULL\_EXIT

When mutation exists:

requires\_user\_confirmation \= true

---

# **51\. Missing Data Definition**

Each missing-data item requires:

field  
importance  
reason  
impact  
recommended\_evidence

Importance enum:

LOW  
MODERATE  
HIGH  
CRITICAL

`recommended_evidence` may be null.

---

# **52\. Warning Definition**

Each warning requires:

code  
severity  
message  
related\_section

Severity:

INFORMATIONAL  
WARNING  
CRITICAL

`code` must follow:

^\[A-Z\]\[A-Z0-9\_\]+$

---

# **53\. Canonical State Proposal Definition**

Required properties:

proposed\_thesis\_status  
proposed\_directional\_bias  
proposed\_confidence\_score  
proposed\_target\_probability  
proposed\_risk\_level  
proposed\_position\_health  
proposed\_recommended\_action  
proposed\_key\_levels  
requires\_thesis\_version  
requires\_context\_summary\_refresh  
canonicalization\_recommendation

The object is only a proposal.

It must not contain:

* actual entry mutations;  
* actual stop activation;  
* actual target activation;  
* actual exits.

---

# **54\. Canonicalization Recommendation Enum**

ACCEPT  
KEEP\_PREVIOUS  
REVIEW\_REQUIRED

---

# **55\. Initial Analysis Root Schema**

Required root properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
market\_summary  
evidence\_assessment  
orderbook\_analysis  
chart\_analysis  
level\_assessment  
thesis\_assessment  
entry\_plan  
stop\_loss\_plan  
target\_plan  
confidence\_assessment  
probability\_assessments  
risk\_assessment  
trading\_plan  
recommended\_action  
missing\_data  
warnings  
canonical\_state\_proposal

The root must enforce:

{  
  "properties": {  
    "analysis\_type": {  
      "const": "INITIAL\_ANALYSIS"  
    }  
  }  
}

---

# **56\. Initial Analysis Entry Plan**

Required properties:

applicable  
ideal\_entry\_zone  
aggressive\_entry  
conservative\_entry  
breakout\_entry  
pullback\_entry  
chase\_limit  
avoid\_entry\_conditions

Individual entry alternatives may be null.

If `applicable = false`, require an explanation field such as:

unavailable\_reason

---

# **57\. Initial Stop-Loss Plan**

Required:

recommended\_stop  
technical\_basis  
estimated\_downside\_percentage  
invalidation\_reason  
warnings

`recommended_stop` may be null only if the setup is not actionable or under review.

---

# **58\. Initial Target Plan**

Required:

targets  
risk\_reward\_summary  
revision\_conditions

When entry plan is actionable, at least one target is required.

If no valid target exists:

* `targets` may be empty;  
* entry plan must not be actionable;  
* recommended action should be `WAIT_FOR_CONFIRMATION` or `CANCEL_SETUP`.

This relationship requires application-side validation.

---

# **59\. Watching Update Root Schema**

Required root properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
market\_summary  
evidence\_assessment  
orderbook\_analysis  
chart\_analysis  
change\_summary  
thesis\_assessment  
setup\_assessment  
level\_assessment  
entry\_plan  
stop\_loss\_plan  
target\_plan  
confidence\_assessment  
probability\_assessments  
risk\_assessment  
trading\_plan  
recommended\_action  
missing\_data  
warnings  
canonical\_state\_proposal

Root constant:

analysis\_type \= WATCHING\_UPDATE

---

# **60\. Setup Assessment Definition**

Required:

setup\_quality  
entry\_condition\_status  
planned\_entry\_still\_valid  
chase\_risk  
cancellation\_condition\_triggered  
explanation

Entry status enum:

CONFIRMED  
PARTIALLY\_CONFIRMED  
NOT\_YET\_CONFIRMED  
MISSED  
INVALIDATED

If:

cancellation\_condition\_triggered \= true

recommended action should normally be:

CANCEL\_SETUP

This is validated application-side.

---

# **61\. Open Position Update Root Schema**

Required root properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
market\_summary  
evidence\_assessment  
orderbook\_analysis  
chart\_analysis  
change\_summary  
thesis\_assessment  
position\_assessment  
level\_assessment  
stop\_loss\_assessment  
target\_assessment  
confidence\_assessment  
probability\_assessments  
risk\_assessment  
trading\_plan  
recommended\_action  
missing\_data  
warnings  
canonical\_state\_proposal

Root constant:

analysis\_type \= OPEN\_POSITION\_UPDATE

---

# **62\. Open Position Schema Guarantees**

The schema requires presence of:

* position assessment;  
* stop assessment;  
* target assessment;  
* change summary;  
* thesis assessment;  
* confidence;  
* required probability array;  
* trading plan;  
* recommended action.

The application additionally verifies:

* actual average entry matches position snapshot;  
* active stop matches request snapshot;  
* target IDs and prices match active targets;  
* position version is current;  
* no active mutation is represented as executed.

---

# **63\. Partial Exit Review Root Schema**

Required root properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
change\_summary  
thesis\_assessment  
partial\_exit\_review  
remaining\_position\_assessment  
stop\_loss\_assessment  
target\_assessment  
confidence\_assessment  
probability\_assessments  
risk\_assessment  
trading\_plan  
recommended\_action  
missing\_data  
warnings  
canonical\_state\_proposal

---

# **64\. Partial Exit Review Definition**

Required:

execution\_quality  
reason\_alignment  
realized\_risk\_reduction  
remaining\_position\_health  
remaining\_position\_plan  
stop\_adjustment\_recommendation  
target\_adjustment\_recommendation  
hindsight\_limitations

Execution quality enum:

EXCELLENT  
GOOD  
ACCEPTABLE  
POOR  
NOT\_EVALUABLE

Reason alignment enum:

ALIGNED\_WITH\_PLAN  
PARTIALLY\_ALIGNED  
NOT\_ALIGNED  
NO\_PRIOR\_PLAN  
NOT\_EVALUABLE

---

# **65\. Closing Analysis Root Schema**

Required properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
exit\_summary  
final\_thesis\_assessment  
exit\_quality  
plan\_compliance  
major\_timeline\_events  
preliminary\_lessons  
journal\_eligibility  
missing\_data  
warnings

No canonical active-state proposal is required.

The root must reject active trading-plan properties such as:

* entry plan;  
* active stop change;  
* active target change;  
* hold recommendation.

---

# **66\. Exit Summary Definition**

Required:

exit\_reason  
average\_entry  
average\_exit  
return\_percentage  
realized\_profit\_loss  
holding\_duration\_days  
summary

Quantity-dependent values may be null when quantity is unavailable.

Exit reason must match supported execution reasons.

---

# **67\. Final Thesis Assessment**

Required:

status\_at\_exit  
invalidation\_detected\_before\_exit  
invalidation\_timing\_quality  
explanation

Timing quality:

EARLY  
TIMELY  
LATE  
NOT\_DETECTED  
NOT\_APPLICABLE  
NOT\_EVALUABLE

---

# **68\. Exit Quality Definition**

Required:

classification  
explanation  
slippage\_from\_plan  
hindsight\_limitations

Classification:

EXCELLENT  
GOOD  
ACCEPTABLE  
EARLY  
LATE  
POOR  
NOT\_EVALUABLE

---

# **69\. Plan Compliance Definition**

Required:

classification  
compliant\_actions  
deviations  
unavoidable\_deviations  
explanation

Classification:

COMPLIANT  
MOSTLY\_COMPLIANT  
PARTIALLY\_COMPLIANT  
NON\_COMPLIANT  
NO\_PLAN  
NOT\_EVALUABLE

---

# **70\. Journal Eligibility Definition**

{  
  "eligible": true,  
  "blocking\_reasons": \[\],  
  "recommended\_next\_action": "Generate Trading Journal."  
}

When eligible is false, `blocking_reasons` must contain at least one item.

---

# **71\. Trading Journal Root Schema**

Required properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
trade\_summary  
initial\_thesis\_review  
entry\_review  
position\_management\_review  
stop\_loss\_review  
target\_management\_review  
partial\_exit\_review  
final\_exit\_review  
plan\_compliance  
ai\_analysis\_review  
user\_execution\_review  
probability\_review  
what\_worked  
what\_did\_not\_work  
lessons  
next\_trade\_checklist  
hindsight\_disclosure  
missing\_data  
warnings

Root constant:

analysis\_type \= TRADING\_JOURNAL

---

# **72\. Journal Review Section**

Reusable review section:

{  
  "classification": "GOOD",  
  "summary": "Entry dilakukan dekat area rencana.",  
  "strengths": \[\],  
  "weaknesses": \[\],  
  "evidence": \[\],  
  "hindsight\_limitations": \[\]  
}

Classification:

EXCELLENT  
GOOD  
ACCEPTABLE  
POOR  
NOT\_APPLICABLE  
NOT\_EVALUABLE

---

# **73\. AI Analysis Review**

Must evaluate AI separately from user execution.

Required:

accurate\_assessments  
late\_warnings  
incorrect\_assessments  
consistency\_issues  
probability\_issues  
overall\_classification  
explanation

The journal must not blame user execution for AI errors or vice versa.

---

# **74\. User Execution Review**

Required:

well\_executed\_actions  
execution\_deviations  
risk\_discipline  
emotional\_execution\_indicators  
overall\_classification  
explanation

Emotional indicators must be phrased cautiously and based only on available notes or explicit deviations.

---

# **75\. Journal Hindsight Disclosure**

Required object:

{  
  "hindsight\_was\_used": true,  
  "usage\_explanation": "Outcome data digunakan hanya untuk mengevaluasi hasil, bukan untuk menganggap keputusan awal seharusnya mengetahui masa depan.",  
  "facts\_unavailable\_at\_entry": \[\]  
}

---

# **76\. Context Summary Root Schema**

Required properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
session\_id  
source\_cutoff  
active\_thesis\_summary  
initial\_thesis\_summary  
position\_summary  
key\_level\_summary  
trade\_plan\_summary  
update\_history\_summary  
thesis\_change\_summary  
position\_event\_summary  
resolved\_questions  
unresolved\_questions  
current\_risks  
critical\_facts  
source\_analysis\_ids  
source\_event\_ids

Root constant:

analysis\_type \= CONTEXT\_SUMMARY

---

# **77\. Context Summary Critical Facts**

Each critical fact requires:

fact\_type  
value  
source\_type  
source\_id  
effective\_at  
must\_not\_override

The `value` field may use a controlled JSON value union.

Application validation compares these facts with canonical records.

---

# **78\. Thesis Review Root Schema**

Required properties:

schema\_version  
analysis\_type  
language  
analysis\_timestamp  
ticker  
data\_quality  
executive\_summary  
review\_result  
previous\_thesis\_status  
proposed\_thesis\_status  
resolved\_questions  
unresolved\_questions  
supporting\_evidence  
conflicting\_evidence  
required\_confirmation  
defensive\_action  
change\_reason  
position\_impact  
requires\_thesis\_version  
canonicalization\_recommendation  
missing\_data  
warnings  
canonical\_state\_proposal

---

# **79\. Thesis Review Result Enum**

RESTORE\_INTACT  
MARK\_WEAKENING  
KEEP\_UNDER\_REVIEW  
INVALIDATE  
REJECT\_NEW\_ANALYSIS

Conditional mapping:

| Review Result | Proposed Status |
| ----- | ----- |
| `RESTORE_INTACT` | `INTACT` |
| `MARK_WEAKENING` | `INTACT_BUT_WEAKENING` |
| `KEEP_UNDER_REVIEW` | `UNDER_REVIEW` |
| `INVALIDATE` | `INVALIDATED` |
| `REJECT_NEW_ANALYSIS` | Previous status retained |

Application validation enforces this mapping.

---

# **80\. Schema Composition**

Root schemas should reuse shared definitions through:

$ref  
allOf  
oneOf  
if / then / else

Avoid copying large shared definitions into every root schema.

Example:

{  
  "allOf": \[  
    {  
      "$ref": "../common/v1/base\_analysis.schema.json"  
    },  
    {  
      "type": "object",  
      "properties": {  
        "analysis\_type": {  
          "const": "OPEN\_POSITION\_UPDATE"  
        }  
      }  
    }  
  \]  
}

---

# **81\. Provider Schema Bundling**

Some providers may not resolve external `$ref` references.

The build pipeline must support schema bundling.

Bundled schema requirements:

* all references resolved;  
* one root document;  
* semantics unchanged;  
* stable bundle hash;  
* no network access required;  
* provider limit respected.

---

# **82\. Schema Build Pipeline**

Recommended pipeline:

Source JSON Schemas  
        ↓  
Static schema validation  
        ↓  
Reference resolution  
        ↓  
Canonical bundle generation  
        ↓  
Provider-specific transformation  
        ↓  
Compatibility tests  
        ↓  
Hash generation  
        ↓  
Application packaging

---

# **83\. Schema Registry Interface**

Conceptual interface:

class AnalysisSchemaRegistry:  
    def get\_schema(  
        self,  
        analysis\_type: AnalysisType,  
        schema\_version: str,  
    ) \-\> dict:  
        ...

    def get\_bundled\_schema(  
        self,  
        analysis\_type: AnalysisType,  
        schema\_version: str,  
        provider: ProviderName,  
    ) \-\> dict:  
        ...

    def validate\_payload(  
        self,  
        analysis\_type: AnalysisType,  
        schema\_version: str,  
        payload: dict,  
    ) \-\> SchemaValidationResult:  
        ...

---

# **84\. Schema Metadata**

Each compiled schema should expose:

{  
  "schema\_name": "open\_position\_update",  
  "schema\_version": "1.0.0",  
  "schema\_hash": "sha256",  
  "draft": "2020-12",  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "provider\_variant": "canonical",  
  "built\_at": "timestamp"  
}

---

# **85\. Canonical Schema Hash**

Calculate:

SHA-256(canonical normalized schema)

The hash should be recorded with the analysis request or prompt manifest.

This helps detect accidental runtime schema changes.

---

# **86\. Provider-Specific Transformation**

Provider transformations may:

* inline `$ref`;  
* remove unsupported annotation fields;  
* simplify regex;  
* convert nullable unions;  
* remove unsupported conditional constructs;  
* shorten descriptions.

They must not weaken the canonical application validator.

---

# **87\. Provider Transformation Restrictions**

A provider schema variant must not:

* remove required properties semantically;  
* broaden controlled enums;  
* permit unsupported top-level fields;  
* change numerical meaning;  
* remove analysis-type constants;  
* permit string values where canonical schema requires numbers.

If a provider cannot enforce a constraint, the application still must.

---

# **88\. Three Validation Layers**

## **88.1 Provider-Native Validation**

Best-effort prevention of malformed output.

## **88.2 Canonical JSON Schema Validation**

Authoritative structural validation after normalization.

## **88.3 Domain and Logical Validation**

Authoritative business validation.

All three are required when supported.

---

# **89\. Schema Validation Result**

Recommended structure:

{  
  "status": "INVALID",  
  "schema\_name": "open\_position\_update",  
  "schema\_version": "1.0.0",  
  "errors": \[  
    {  
      "path": "/probability\_assessments/2/percentage",  
      "keyword": "maximum",  
      "message": "Value must be less than or equal to 100.",  
      "expected": 100,  
      "actual": 120  
    }  
  \]  
}

---

# **90\. Validation Statuses**

VALID  
VALID\_WITH\_WARNINGS  
INVALID

Schema validation itself should normally return either:

VALID  
INVALID

Warnings usually arise from later logical validators.

---

# **91\. Validation Error Path**

Errors must use JSON Pointer paths.

Examples:

/executive\_summary/condition\_summary  
/probability\_assessments/2/percentage  
/target\_assessment/targets/0/recommended\_change

This allows precise correction prompts.

---

# **92\. Validation Error Normalization**

Recommended error codes:

SCHEMA\_REQUIRED\_FIELD\_MISSING  
SCHEMA\_UNEXPECTED\_PROPERTY  
SCHEMA\_INVALID\_TYPE  
SCHEMA\_INVALID\_ENUM  
SCHEMA\_VALUE\_BELOW\_MINIMUM  
SCHEMA\_VALUE\_ABOVE\_MAXIMUM  
SCHEMA\_STRING\_TOO\_SHORT  
SCHEMA\_STRING\_TOO\_LONG  
SCHEMA\_ARRAY\_TOO\_SHORT  
SCHEMA\_ARRAY\_DUPLICATE\_ITEM  
SCHEMA\_CONDITIONAL\_RULE\_FAILED  
SCHEMA\_REFERENCE\_RESOLUTION\_FAILED  
SCHEMA\_VERSION\_MISMATCH  
SCHEMA\_ANALYSIS\_TYPE\_MISMATCH

---

# **93\. Nullability Rules**

Use null when:

* value is unavailable;  
* value is not readable;  
* value is not applicable and the schema explicitly permits null;  
* comparison does not exist.

Use an empty array when:

* the category is applicable;  
* no items were found.

Examples:

{  
  "volume": null,  
  "supporting\_evidence": \[\],  
  "previous\_score": null  
}

---

# **94\. Omission Versus Null**

Use omission when:

* a section is not part of the analysis-type schema.

Use null when:

* a required field exists conceptually but no value is available.

Example:

`position_assessment` is omitted from initial analysis.

Inside market summary:

{  
  "volume": null  
}

---

# **95\. Empty Narrative Prohibition**

Required narrative values must not contain:

""  
" "  
"N/A"  
"Unknown"  
"-"

Unknown values should use null plus a missing-data explanation.

---

# **96\. Array Rules**

Use:

uniqueItems: true

for arrays such as:

* missing field names;  
* evidence IDs;  
* warning codes where duplicate warnings are invalid;  
* critical fact IDs.

Do not use `uniqueItems` on complex analytical arrays when objects may differ only slightly and provider support is inconsistent.

Application validation should deduplicate semantically.

---

# **97\. Maximum Array Sizes**

To control output size, recommended maximums:

schema\_limits:  
  visible\_facts: 20  
  interpretations: 20  
  assumptions: 10  
  uncertainties: 10  
  probability\_assessments: 12  
  warning\_items: 20  
  missing\_data\_items: 20  
  change\_items: 30  
  support\_levels\_per\_timeframe: 10  
  resistance\_levels\_per\_timeframe: 10  
  target\_assessments: 10  
  timeline\_events\_in\_closing\_analysis: 30  
  journal\_lessons: 20  
  next\_trade\_checklist: 20

These limits may be adjusted based on model output quality.

---

# **98\. Narrative Length Limits**

Recommended ranges:

| Field Type | Max Length |
| ----- | ----- |
| Short label | 120 |
| Short explanation | 500 |
| Standard narrative | 2,000 |
| Long review section | 5,000 |
| Journal summary | 8,000 |

The goal is to prevent uncontrolled verbose output while retaining useful reasoning.

---

# **99\. Numeric Precision**

The schema accepts JSON numbers.

Application normalization should:

* preserve source financial precision;  
* round AI display percentages appropriately;  
* reject unsupported extreme decimal precision where necessary;  
* avoid binary floating-point as authoritative persistence.

Provider output may be parsed into Python `Decimal`.

---

# **100\. Language Validation**

JSON Schema cannot reliably enforce Bahasa Indonesia.

Application language validation must inspect narrative fields identified through schema annotations.

Recommended annotation:

{  
  "type": "string",  
  "x-tradepilot-language": "id-ID"  
}

Custom annotations do not affect standard validation but help the application traverse narrative fields.

---

# **101\. Authority Annotation**

Schemas may use custom metadata:

{  
  "x-tradepilot-authority": "SYSTEM\_CALCULATED"  
}

Possible values:

USER\_CONFIRMED  
CANONICAL\_STATE  
SYSTEM\_CALCULATED  
AI\_INTERPRETED  
AI\_PROPOSED

This can guide normalization and frontend rendering.

---

# **102\. UI Annotation**

Optional custom annotations:

{  
  "x-tradepilot-ui": {  
    "component": "probability\_card",  
    "order": 12,  
    "collapsible": true  
  }  
}

The frontend should not rely entirely on schema annotations for layout, but they may support schema-driven rendering.

---

# **103\. Sensitive Field Annotation**

Schemas may mark restricted diagnostic fields:

{  
  "x-tradepilot-sensitive": true  
}

Primary analysis output should contain no credentials or secrets.

---

# **104\. Typed Model Generation**

Canonical schemas should generate or validate:

* Pydantic models for Python;  
* TypeScript types for frontend;  
* test fixtures;  
* API documentation components.

Recommended tools may include:

* Pydantic model generation;  
* `json-schema-to-typescript`;  
* OpenAPI schema reuse.

Tool selection will be finalized during implementation.

---

# **105\. Pydantic Model Requirements**

Generated or handwritten Pydantic models must:

* use strict types where practical;  
* reject unknown properties;  
* map enums explicitly;  
* use Decimal for financial values;  
* preserve null semantics;  
* validate analysis-type constants;  
* expose domain-validation hooks.

---

# **106\. TypeScript Model Requirements**

Frontend types must:

* use discriminated unions by `analysis_type`;  
* preserve nullable fields;  
* expose controlled enums;  
* prevent rendering incompatible sections;  
* distinguish active and historical probability status.

Example:

type AnalysisPayload \=  
  | InitialAnalysisPayload  
  | WatchingUpdatePayload  
  | OpenPositionUpdatePayload  
  | PartialExitReviewPayload  
  | ClosingAnalysisPayload  
  | TradingJournalPayload  
  | ContextSummaryPayload  
  | ThesisReviewPayload;

---

# **107\. Analysis Type Discriminator**

Every root schema must use:

analysis\_type

as a discriminator.

This allows:

* typed parsing;  
* correct UI rendering;  
* API validation;  
* prompt-schema matching.

---

# **108\. API Payload Wrapping**

The persisted analysis payload remains the schema-conforming object.

API responses may wrap it:

{  
  "analysis\_version\_id": "uuid",  
  "version\_number": 4,  
  "canonical\_status": "ACCEPTED",  
  "validation\_status": "VALID",  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "payload": {}  
}

The wrapper belongs to the API specification, not the AI output schema.

---

# **109\. Canonical Payload Normalization**

Before persistence, the backend may normalize:

* whitespace;  
* decimal representation;  
* timestamp formatting;  
* deterministic property ordering for hashing;  
* system-calculated values;  
* change amounts;  
* current source references.

The backend must not silently alter analytical meaning.

---

# **110\. System-Calculated Field Replacement**

Where a field is system-authoritative, the backend may replace the AI value.

Examples:

* return percentage;  
* distance to stop;  
* distance to target;  
* probability change amount;  
* confidence score change;  
* spread;  
* holding duration.

The raw candidate should remain available in restricted diagnostics when useful.

---

# **111\. Schema-Level Versus Domain-Level Checks**

## **111.1 Schema-Level**

Examples:

* probability is a number;  
* probability is between 0 and 100;  
* required field exists;  
* enum is valid;  
* additional property rejected.

## **111.2 Domain-Level**

Examples:

* target probability references an active target;  
* TP2 probability does not exceed TP1 without explanation;  
* invalidated thesis cannot recommend additional entry;  
* active stop matches current position;  
* final exit reason matches session lifecycle;  
* evidence belongs to the session.

---

# **112\. Validation Pipeline**

Receive normalized provider payload  
        ↓  
Verify root is JSON object  
        ↓  
Verify schema version  
        ↓  
Verify analysis-type discriminator  
        ↓  
Canonical JSON Schema validation  
        ↓  
Language validation  
        ↓  
Reference validation  
        ↓  
System arithmetic normalization  
        ↓  
Numerical coherence validation  
        ↓  
Thesis transition validation  
        ↓  
Probability coherence validation  
        ↓  
Position-state validation  
        ↓  
Stale-state validation  
        ↓  
Contradiction detection  
        ↓  
Canonicalization eligibility

---

# **113\. Repair Eligibility**

Schema errors eligible for correction prompt:

* missing required property;  
* unsupported additional property;  
* invalid enum;  
* wrong primitive type;  
* malformed nullable value;  
* missing nested object;  
* truncated array.

Schema errors generally not repairable without rerun:

* unrelated output;  
* missing most of the payload;  
* incorrect analysis type;  
* unsupported fabricated position state;  
* context mismatch;  
* stale evidence.

---

# **114\. Correction Prompt Error Payload**

Normalized validation errors sent to repair should include:

\[  
  {  
    "path": "/recommended\_action/action",  
    "code": "SCHEMA\_INVALID\_ENUM",  
    "message": "Expected one of the supported action enum values.",  
    "allowed\_values": \[  
      "HOLD\_POSITION",  
      "HOLD\_WITH\_CAUTION",  
      "REDUCE\_RISK"  
    \],  
    "actual\_value": "SELL"  
  }  
\]

Do not include secrets or unnecessary internal details.

---

# **115\. Schema Migration Policy**

When a new schema version becomes active:

* old Analysis Versions retain their original schema version;  
* the application must remain able to read supported historical versions;  
* new analysis requests use the active version;  
* optional migration to a normalized read model may be performed;  
* historical payloads must not be rewritten silently.

---

# **116\. Historical Schema Support**

Recommended policy:

Current major version: full support  
Previous major version: read support  
Older versions: archived compatibility adapter or explicit unsupported state

MVP begins with one major version.

---

# **117\. Payload Upgrade Adapter**

A read-time upgrade adapter may convert an older payload to a current frontend read model.

Example:

upgrade\_analysis\_payload(  
    payload=old\_payload,  
    from\_version="1.0.0",  
    to\_read\_model\_version="2.0.0",  
)

The original stored payload remains unchanged.

---

# **118\. Schema Deprecation**

A schema version may become:

DRAFT  
TESTING  
ACTIVE  
DEPRECATED  
RETIRED

`RETIRED` schemas remain available for historical reading when required.

---

# **119\. Schema Compatibility Tests**

Tests must verify:

* prompt version compatibility;  
* provider bundle compatibility;  
* Pydantic compatibility;  
* TypeScript generation;  
* API serialization;  
* historical fixture parsing.

---

# **120\. Provider Compatibility Tests**

For each active provider and schema:

1. bundle schema;  
2. transform provider variant;  
3. submit representative request;  
4. validate returned payload against canonical schema;  
5. compare semantic field coverage;  
6. record unsupported provider constraints.

---

# **121\. Golden Valid Fixtures**

At least one valid fixture is required for:

INITIAL\_ANALYSIS  
WATCHING\_UPDATE  
OPEN\_POSITION\_UPDATE  
PARTIAL\_EXIT\_REVIEW  
CLOSING\_ANALYSIS  
TRADING\_JOURNAL  
CONTEXT\_SUMMARY  
THESIS\_REVIEW

Additional open-position fixtures should cover:

* healthy position;  
* weakening thesis;  
* under-review thesis;  
* invalidated thesis;  
* multiple targets;  
* no quantity;  
* missing volume;  
* no material change.

---

# **122\. Invalid Fixtures**

Required invalid fixtures:

* missing required root field;  
* unexpected root property;  
* invalid analysis type;  
* invalid enum;  
* probability above 100;  
* negative price;  
* empty narrative;  
* exact price and zone both populated;  
* invalid target-change combination;  
* non-comparable probability with previous value;  
* closed analysis containing active hold plan;  
* initial analysis proposing invalidated thesis;  
* journal without hindsight disclosure.

---

# **123\. Boundary Tests**

Test:

confidence \= 0  
confidence \= 39  
confidence \= 40  
confidence \= 69  
confidence \= 70  
confidence \= 100

probability \= 0  
probability \= 5  
probability \= 95  
probability \= 100

Domain rules may warn about extreme values even when schema-valid.

---

# **124\. Null Tests**

Test nullable behavior for:

* OHLC;  
* volume;  
* transaction value;  
* previous probability;  
* position quantity;  
* realized P/L;  
* comparison analysis;  
* active stop in pre-entry analysis;  
* target proposal when no setup exists.

---

# **125\. Conditional Tests**

Test:

* invalidated thesis requires invalidation evidence;  
* stop change recommendation requires confirmation;  
* target change requires proposed price;  
* journal eligibility false requires blocking reasons;  
* context summary requires critical facts;  
* under-review thesis requires unresolved questions;  
* no material change prohibits critical change items.

---

# **126\. Schema Performance**

Schema validation should complete quickly enough not to dominate AI-processing latency.

Recommended targets:

Typical analysis validation: under 100 ms  
Large journal validation: under 500 ms

These are implementation targets, not strict domain requirements.

Compiled validators should be cached.

---

# **127\. Schema Security**

The schema registry must reject:

* arbitrary external `$ref` loading;  
* untrusted schema uploads;  
* remote reference resolution at runtime;  
* schema path traversal;  
* runtime changes without deployment or controlled configuration.

All production schemas must be packaged with the application.

---

# **128\. Schema Observability**

Metrics should include:

validation count  
validation success rate  
errors by schema version  
errors by field path  
errors by provider  
repair success rate  
average validation duration  
provider-specific schema failure rate  
unexpected-property frequency  
missing-required-field frequency

---

# **129\. Schema Debugging View**

Restricted diagnostics may display:

* schema name;  
* schema version;  
* schema hash;  
* provider variant;  
* validation errors;  
* candidate-response hash;  
* normalized payload;  
* repair attempts.

Do not expose private evidence or full provider context unnecessarily.

---

# **130\. Suggested Schema Registry Package**

app/  
├── ai/  
│   ├── schemas/  
│   │   ├── registry.py  
│   │   ├── loader.py  
│   │   ├── bundler.py  
│   │   ├── transformer.py  
│   │   ├── validator.py  
│   │   ├── errors.py  
│   │   ├── hashing.py  
│   │   │  
│   │   ├── canonical/  
│   │   │   ├── analysis/  
│   │   │   └── common/  
│   │   │  
│   │   └── tests/  
│   │       ├── valid/  
│   │       ├── invalid/  
│   │       └── provider\_variants/

---

# **131\. Example Root Schema Skeleton**

{  
  "$schema": "https://json-schema.org/draft/2020-12/schema",  
  "$id": "https://schemas.tradepilot.local/analysis/open-position-update/1.0.0",  
  "title": "TradePilot Open Position Update",  
  "type": "object",  
  "additionalProperties": false,  
  "required": \[  
    "schema\_version",  
    "analysis\_type",  
    "language",  
    "analysis\_timestamp",  
    "ticker",  
    "data\_quality",  
    "executive\_summary",  
    "market\_summary",  
    "evidence\_assessment",  
    "orderbook\_analysis",  
    "chart\_analysis",  
    "change\_summary",  
    "thesis\_assessment",  
    "position\_assessment",  
    "level\_assessment",  
    "stop\_loss\_assessment",  
    "target\_assessment",  
    "confidence\_assessment",  
    "probability\_assessments",  
    "risk\_assessment",  
    "trading\_plan",  
    "recommended\_action",  
    "missing\_data",  
    "warnings",  
    "canonical\_state\_proposal"  
  \],  
  "properties": {  
    "schema\_version": {  
      "const": "1.0.0"  
    },  
    "analysis\_type": {  
      "const": "OPEN\_POSITION\_UPDATE"  
    },  
    "language": {  
      "const": "id-ID"  
    },  
    "analysis\_timestamp": {  
      "$ref": "\#/$defs/timestamp"  
    },  
    "ticker": {  
      "type": "string",  
      "minLength": 1,  
      "maxLength": 32,  
      "pattern": "^\[A-Z0-9.\_-\]+$"  
    },  
    "data\_quality": {  
      "$ref": "\#/$defs/dataQuality"  
    },  
    "executive\_summary": {  
      "$ref": "\#/$defs/executiveSummary"  
    }  
  },  
  "$defs": {}  
}

In production, shared definitions should be referenced or bundled rather than manually duplicated.

---

# **132\. Example Probability Conditional Fragment**

{  
  "allOf": \[  
    {  
      "if": {  
        "properties": {  
          "change\_direction": {  
            "const": "NOT\_COMPARABLE"  
          }  
        }  
      },  
      "then": {  
        "properties": {  
          "previous\_percentage": {  
            "type": "null"  
          },  
          "change\_amount": {  
            "type": "null"  
          }  
        }  
      },  
      "else": {  
        "properties": {  
          "previous\_percentage": {  
            "type": "number",  
            "minimum": 0,  
            "maximum": 100  
          },  
          "change\_amount": {  
            "type": "number",  
            "minimum": \-100,  
            "maximum": 100  
          }  
        }  
      }  
    }  
  \]  
}

---

# **133\. Example Thesis Invalidation Conditional Fragment**

{  
  "allOf": \[  
    {  
      "if": {  
        "properties": {  
          "proposed\_status": {  
            "const": "INVALIDATED"  
          }  
        }  
      },  
      "then": {  
        "required": \[  
          "invalidation\_evidence"  
        \],  
        "properties": {  
          "change\_type": {  
            "const": "INVALIDATED"  
          },  
          "invalidation\_evidence": {  
            "$ref": "\#/$defs/invalidationEvidence"  
          }  
        }  
      }  
    }  
  \]  
}

---

# **134\. Example Target Change Conditional Fragment**

{  
  "allOf": \[  
    {  
      "if": {  
        "properties": {  
          "action": {  
            "const": "KEEP"  
          }  
        }  
      },  
      "then": {  
        "properties": {  
          "proposed\_price": {  
            "type": "null"  
          },  
          "requires\_user\_confirmation": {  
            "const": false  
          }  
        }  
      },  
      "else": {  
        "properties": {  
          "requires\_user\_confirmation": {  
            "const": true  
          }  
        }  
      }  
    }  
  \]  
}

A separate condition must require a price for `LOWER`, `RAISE`, and `ADD_TARGET`.

---

# **135\. Schema Error Handling**

When schema validation fails:

* analysis remains non-canonical;  
* current thesis remains unchanged;  
* current position remains unchanged;  
* validation errors are persisted;  
* repair may be attempted;  
* the user sees processing failure only if repair and fallback fail.

---

# **136\. Schema and Prompt Synchronization**

A prompt must not request fields absent from the schema.

A schema must not require fields omitted from the prompt’s task instructions.

Automated synchronization tests should compare:

* required root fields;  
* task prompt required sections;  
* frontend renderer support;  
* Pydantic models.

---

# **137\. Frontend Rendering Compatibility**

Before activating a schema version, verify the frontend can render:

* all required root sections;  
* all enum values;  
* all nullable states;  
* warning and missing-data items;  
* historical comparison;  
* proposed mutations;  
* schema validation warnings where displayed.

---

# **138\. API Compatibility**

The API must include the payload’s:

* schema name;  
* schema version;  
* analysis type.

Clients must not assume every historical analysis uses the latest schema.

---

# **139\. Schema Acceptance Criteria**

The analysis schema system is accepted when:

1. all analysis outputs use JSON Schema Draft 2020-12;  
2. every root schema has a stable ID and semantic version;  
3. every analysis type has its own root schema;  
4. shared definitions are reusable;  
5. root objects reject unsupported properties;  
6. required properties are explicit;  
7. analysis type acts as a discriminator;  
8. English keys and enum values are enforced;  
9. narrative language is validated separately;  
10. unknown values use null rather than zero;  
11. prices and percentages have valid ranges;  
12. exact price and price-zone forms are mutually exclusive;  
13. invalidated thesis requires invalidation evidence;  
14. execution recommendations require user confirmation;  
15. non-comparable probabilities cannot preserve previous values;  
16. initial analysis cannot create an invalidated first thesis;  
17. open-position output requires position, stop, and target assessment;  
18. closing analysis cannot contain active-trade instructions;  
19. Trading Journal requires hindsight disclosure;  
20. Context Summary preserves critical facts;  
21. provider schema variants remain semantically equivalent;  
22. canonical application validation always uses the full schema;  
23. schema validation errors use normalized JSON Pointer paths;  
24. valid and invalid golden fixtures exist;  
25. schemas can generate typed Python and TypeScript models;  
26. historical schema versions remain readable;  
27. schema hashes are recorded;  
28. schema and prompt compatibility is tested;  
29. untrusted remote schema references are prohibited;  
30. schema validation cannot directly mutate canonical state.

---

# **140\. Final Analysis Schema Statement**

TradePilot AI must treat structured analysis schemas as enforceable contracts, not as suggestions to the AI provider.

Every analysis type must have a precise, versioned, machine-validatable shape that defines:

* which sections must exist;  
* which values are permitted;  
* which fields may be unavailable;  
* which conditional relationships are required;  
* which properties are proposals rather than execution.

Provider output may vary in reasoning quality, but it must never vary in contractual meaning.

The schema layer ensures that AI analysis remains predictable, renderable, testable, auditable, and safe to integrate with the canonical Trade Session state.

