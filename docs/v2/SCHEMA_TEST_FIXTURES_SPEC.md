# **SCHEMA\_TEST\_FIXTURES\_SPEC.md**

## **TradePilot AI Schema Test Fixtures Specification**

**Document Version:** 1.0  
**Status:** Draft for Implementation  
**Applies To:** Production schema package v1.0.0  
**Primary Runtime:** Python backend  
**Test Framework:** Pytest  
**Schema Standard:** JSON Schema Draft 2020-12

---

## **1\. Purpose**

This document defines the test-fixture strategy for TradePilot AI production schemas and domain validators.

The fixture suite must prove that:

* every production schema accepts valid payloads;  
* every important invalid condition is rejected;  
* domain validation rules produce stable error codes;  
* canonical Trade State conflicts are detected;  
* lifecycle restrictions are enforced;  
* deterministic calculations are validated;  
* provider repair flows can be tested consistently;  
* historical schema versions remain testable;  
* Gemini and DeepSeek produce compatible structured outputs.

Fixtures are not only sample data.

They are executable contracts between:

* product specifications;  
* JSON Schemas;  
* domain validators;  
* AI provider adapters;  
* backend services;  
* lifecycle rules;  
* context-memory generation.

---

## **2\. Goals**

The fixture system must support:

1. JSON Schema validation tests.  
2. Domain validation tests.  
3. Canonical-state consistency tests.  
4. Lifecycle transition tests.  
5. Context Summary tests.  
6. AI output repair tests.  
7. Provider fallback tests.  
8. Regression tests.  
9. Schema migration tests.  
10. End-to-end Trade Session scenarios.

---

## **3\. Non-Goals**

The fixture suite does not replace:

* live provider integration tests;  
* browser UI tests;  
* database performance tests;  
* load tests;  
* visual regression tests;  
* market-data provider accuracy tests;  
* investment-strategy backtesting.

Fixtures validate contracts and system behavior, not trading profitability.

---

## **4\. Fixture Categories**

Fixtures are divided into six primary categories.

### **4.1 Valid schema fixtures**

Payloads that must pass JSON Schema validation.

### **4.2 Invalid schema fixtures**

Payloads that must fail JSON Schema validation.

### **4.3 Valid domain fixtures**

Structurally valid payloads that must also pass domain validation.

### **4.4 Invalid domain fixtures**

Structurally valid payloads that violate business rules.

### **4.5 Integration scenario fixtures**

Multiple connected payloads representing a complete Trade Session lifecycle.

### **4.6 Provider contract fixtures**

Recorded or synthetic AI responses used to test parsing, repair, retry, and fallback behavior.

---

## **5\. Recommended Directory Structure**

backend/  
└── tests/  
    ├── fixtures/  
    │   ├── manifests/  
    │   │   ├── valid/  
    │   │   └── invalid/  
    │   │  
    │   ├── schemas/  
    │   │   ├── valid/  
    │   │   │   ├── market\_snapshot/  
    │   │   │   ├── trade\_state/  
    │   │   │   ├── evidence/  
    │   │   │   ├── initial\_analysis/  
    │   │   │   ├── watching\_update/  
    │   │   │   ├── open\_position\_update/  
    │   │   │   ├── partial\_exit\_review/  
    │   │   │   ├── closing\_analysis/  
    │   │   │   └── context\_summary/  
    │   │   │  
    │   │   └── invalid/  
    │   │       ├── market\_snapshot/  
    │   │       ├── trade\_state/  
    │   │       ├── evidence/  
    │   │       ├── initial\_analysis/  
    │   │       ├── watching\_update/  
    │   │       ├── open\_position\_update/  
    │   │       ├── partial\_exit\_review/  
    │   │       ├── closing\_analysis/  
    │   │       └── context\_summary/  
    │   │  
    │   ├── domain/  
    │   │   ├── valid/  
    │   │   └── invalid/  
    │   │  
    │   ├── scenarios/  
    │   │   ├── profitable\_full\_exit/  
    │   │   ├── stop\_loss\_exit/  
    │   │   ├── manual\_exit/  
    │   │   ├── partial\_exit\_then\_close/  
    │   │   ├── watched\_setup\_cancelled/  
    │   │   └── invalid\_state\_conflict/  
    │   │  
    │   ├── providers/  
    │   │   ├── gemini/  
    │   │   ├── deepseek/  
    │   │   ├── repair/  
    │   │   └── fallback/  
    │   │  
    │   ├── context/  
    │   │   ├── valid/  
    │   │   └── invalid/  
    │   │  
    │   └── migrations/  
    │       ├── source/  
    │       ├── expected/  
    │       └── invalid/  
    │  
    ├── factories/  
    │   ├── market\_snapshot\_factory.py  
    │   ├── trade\_state\_factory.py  
    │   ├── evidence\_factory.py  
    │   ├── analysis\_factory.py  
    │   ├── context\_summary\_factory.py  
    │   └── scenario\_factory.py  
    │  
    ├── test\_schema\_registry.py  
    ├── test\_schema\_valid\_fixtures.py  
    ├── test\_schema\_invalid\_fixtures.py  
    ├── test\_domain\_valid\_fixtures.py  
    ├── test\_domain\_invalid\_fixtures.py  
    ├── test\_trade\_session\_scenarios.py  
    ├── test\_provider\_contracts.py  
    ├── test\_context\_summary.py  
    └── test\_schema\_migrations.py

---

## **6\. Fixture File Naming Convention**

Use lowercase snake case.

Valid fixtures:

\<scenario\>.valid.json

Examples:

open\_position\_basic.valid.json  
open\_position\_missing\_chart.valid.json  
partial\_exit\_profit.valid.json  
closing\_manual\_exit.valid.json

Invalid fixtures:

\<rule\_name\>.invalid.json

Examples:

high\_below\_low.invalid.json  
entry\_price\_mismatch.invalid.json  
remaining\_quantity\_exceeds\_original.invalid.json  
target\_probability\_above\_100.invalid.json

Expected-result files:

\<fixture\_name\>.expected.json

Example:

entry\_price\_mismatch.invalid.json  
entry\_price\_mismatch.expected.json

---

## **7\. Fixture Metadata Sidecar**

Invalid fixtures should have a sidecar expected-result file.

Example:

{  
  "expected\_valid": false,  
  "validation\_stage": "DOMAIN",  
  "expected\_issues": \[  
    {  
      "code": "POSITION\_ENTRY\_PRICE\_MISMATCH",  
      "path": "/position\_assessment/entry\_price",  
      "severity": "ERROR"  
    }  
  \]  
}

Required fields:

* `expected_valid`;  
* `validation_stage`;  
* `expected_issues`.

Supported stages:

MANIFEST  
PARSE  
SCHEMA  
DOMAIN  
STATE\_CONSISTENCY  
LIFECYCLE  
NARRATIVE  
PROVIDER  
MIGRATION

---

## **8\. Fixture Immutability**

Committed fixtures must be treated as immutable test contracts.

When behavior changes:

* do not silently modify the fixture;  
* document the reason;  
* update schema or domain-rule version;  
* update expected result;  
* add a regression note;  
* consider retaining the old fixture for historical-version testing.

---

## **9\. Stable Identifiers**

Fixtures should use deterministic UUIDs.

Recommended namespace:

00000000-0000-4000-8000-XXXXXXXXXXXX

Example allocation:

Session IDs:  
00000000-0000-4000-8000-000000000001

Analysis IDs:  
00000000-0000-4000-8000-000000001001

Evidence IDs:  
00000000-0000-4000-8000-000000002001

Action IDs:  
00000000-0000-4000-8000-000000003001

Context IDs:  
00000000-0000-4000-8000-000000004001

This makes test failures easier to read and compare.

---

## **10\. Stable Timestamps**

Use fixed timestamps in Asia/Jakarta unless testing timezone behavior.

Recommended base timeline:

Session created:  
2026-07-15T09:00:00+07:00

Initial evidence:  
2026-07-15T09:10:00+07:00

Initial analysis:  
2026-07-15T09:20:00+07:00

Watching update:  
2026-07-15T10:00:00+07:00

Position opened:  
2026-07-15T10:12:00+07:00

Open Position update:  
2026-07-16T10:00:00+07:00

Partial exit:  
2026-07-17T14:05:00+07:00

Final exit:  
2026-07-17T15:12:00+07:00

Closing analysis:  
2026-07-17T15:25:00+07:00

Tests must not depend on the current real-world date.

---

## **11\. Base Trading Example**

The primary fixture family should use one consistent long-position example.

Ticker: BBRI  
Currency: IDR  
Entry price: 2800  
Original quantity: 100  
Initial stop loss: 2700  
Updated stop loss: 2840  
Initial target: 2920  
Partial exit: 50 units at 2920  
Final exit: 50 units at 2900  
Weighted average exit: 2910  
Gross P/L: 11000  
Gross return: 3.93%

A secondary fixture family should use a US stock to ensure currency and decimal-price support.

Example:

Ticker: SOFI  
Currency: USD  
Entry price: 14.50  
Quantity: 20  
Stop loss: 13.90  
Target: 15.80

---

# **Part I — Manifest Fixtures**

## **12\. Valid Manifest Fixtures**

Minimum valid manifest fixtures:

manifest.production.v1.valid.json  
manifest.all\_schemas\_active.valid.json  
manifest\_local\_reference\_resolution.valid.json

They must prove:

* manifest status is active;  
* all required schema files are registered;  
* schema IDs are unique;  
* schema names are unique;  
* dependencies resolve;  
* analysis types map to active schemas;  
* no remote network fetch is required.

---

## **13\. Invalid Manifest Fixtures**

Required invalid manifest fixtures:

manifest\_duplicate\_schema\_name.invalid.json  
manifest\_duplicate\_schema\_id.invalid.json  
manifest\_missing\_common\_schema.invalid.json  
manifest\_unknown\_dependency.invalid.json  
manifest\_inactive\_analysis\_schema.invalid.json  
manifest\_unknown\_analysis\_type.invalid.json  
manifest\_version\_mismatch.invalid.json  
manifest\_schema\_file\_missing.invalid.json  
manifest\_schema\_id\_mismatch.invalid.json  
manifest\_circular\_dependency.invalid.json

Expected error codes:

MANIFEST\_DUPLICATE\_SCHEMA\_NAME  
MANIFEST\_DUPLICATE\_SCHEMA\_ID  
MANIFEST\_REQUIRED\_SCHEMA\_MISSING  
MANIFEST\_DEPENDENCY\_NOT\_FOUND  
MANIFEST\_ANALYSIS\_SCHEMA\_INACTIVE  
MANIFEST\_ANALYSIS\_TYPE\_UNKNOWN  
MANIFEST\_VERSION\_MISMATCH  
MANIFEST\_SCHEMA\_FILE\_NOT\_FOUND  
MANIFEST\_SCHEMA\_ID\_MISMATCH  
MANIFEST\_CIRCULAR\_DEPENDENCY

---

# **Part II — Valid Schema Fixtures**

## **14\. Market Snapshot Valid Fixtures**

Required:

intraday\_complete.valid.json  
market\_close\_complete.valid.json  
minimal\_with\_last.valid.json  
minimal\_with\_close.valid.json  
unavailable\_data.valid.json  
zero\_spread.valid.json  
decimal\_us\_price.valid.json

Coverage:

* complete OHLC;  
* missing optional fields;  
* intraday `last`;  
* final `close`;  
* null handling;  
* zero spread;  
* IDR integer prices;  
* USD decimal prices.

---

## **15\. Trade State Valid Fixtures**

Required:

draft\_without\_position.valid.json  
watching\_without\_position.valid.json  
open\_position.valid.json  
open\_position\_with\_updated\_stop.valid.json  
partially\_closed.valid.json  
closed\_take\_profit.valid.json  
closed\_stop\_loss.valid.json  
closed\_manual.valid.json  
archived\_closed\_session.valid.json

Coverage:

* lifecycle states;  
* canonical action history;  
* open quantity;  
* partial quantity;  
* closed quantity;  
* active level removal after close.

---

## **16\. Evidence Valid Fixtures**

Required:

orderbook\_screenshot.valid.json  
chart\_3\_month.valid.json  
chart\_6\_month.valid.json  
market\_screenshot.valid.json  
user\_note.valid.json  
position\_open\_confirmation.valid.json  
partial\_exit\_confirmation.valid.json  
full\_exit\_confirmation.valid.json  
unreadable\_screenshot.valid.json  
stale\_historical\_chart.valid.json

Coverage:

* evidence type;  
* upload timestamp;  
* market timestamp;  
* extracted facts;  
* confirmation payload;  
* unreadable evidence;  
* historical evidence.

---

## **17\. Initial Analysis Valid Fixtures**

Required:

complete\_setup.valid.json  
entry\_exact\_price.valid.json  
entry\_price\_zone.valid.json  
breakout\_confirmation.valid.json  
pullback\_confirmation.valid.json  
wait\_for\_confirmation.valid.json  
no\_entry.valid.json  
missing\_orderbook\_with\_warning.valid.json  
missing\_one\_chart\_with\_warning.valid.json  
invalid\_setup\_no\_entry.valid.json

Coverage:

* all entry modes;  
* complete and incomplete evidence;  
* valid setup;  
* invalid setup;  
* no-position state;  
* proposed stop and target.

---

## **18\. Watching Update Valid Fixtures**

Required:

setup\_improving.valid.json  
setup\_unchanged.valid.json  
setup\_weakening.valid.json  
entry\_confirmation\_met.valid.json  
price\_extended\_do\_not\_chase.valid.json  
revised\_entry\_exact.valid.json  
revised\_entry\_zone.valid.json  
setup\_invalidated.valid.json  
historical\_chart\_context.valid.json

Coverage:

* previous-analysis comparison;  
* setup evolution;  
* entry confirmation;  
* chase-risk handling;  
* revised proposal;  
* invalidation.

---

## **19\. Open Position Update Valid Fixtures**

Required:

morning\_hold.valid.json  
midday\_hold.valid.json  
afternoon\_hold\_with\_caution.valid.json  
target\_still\_realistic.valid.json  
target\_unlikely.valid.json  
stop\_approached.valid.json  
stop\_triggered\_review\_exit.valid.json  
proposed\_stop\_change.valid.json  
proposed\_target\_change.valid.json  
thesis\_strengthening.valid.json  
thesis\_weakening.valid.json  
thesis\_invalidated.valid.json  
missing\_chart\_uses\_history.valid.json

Coverage:

* daily summary;  
* orderbook;  
* active position facts;  
* thesis condition;  
* target realism;  
* stop handling;  
* proposed state changes;  
* user confirmation requirement.

---

## **20\. Partial Exit Review Valid Fixtures**

Required:

partial\_take\_profit.valid.json  
partial\_risk\_reduction.valid.json  
remaining\_position\_hold.valid.json  
remaining\_target\_revised.valid.json  
protective\_stop\_proposed.valid.json  
second\_partial\_exit\_possible.valid.json  
remaining\_thesis\_invalidated.valid.json  
multiple\_partial\_exits.valid.json

Coverage:

* confirmed partial exit;  
* realized result;  
* remaining position;  
* target revision;  
* stop revision;  
* cumulative exit calculations.

---

## **21\. Closing Analysis Valid Fixtures**

Required:

take\_profit\_close.valid.json  
stop\_loss\_close.valid.json  
manual\_profit\_close.valid.json  
manual\_loss\_close.valid.json  
partial\_then\_final\_close.valid.json  
break\_even\_close.valid.json  
closing\_without\_fee\_data.valid.json  
closing\_with\_fee\_and\_tax.valid.json  
good\_process\_losing\_trade.valid.json  
poor\_process\_profitable\_trade.valid.json

Coverage:

* closing reasons;  
* result classes;  
* weighted exits;  
* gross and net result;  
* process evaluation independent of profit.

---

## **22\. Context Summary Valid Fixtures**

Required:

draft\_context.valid.json  
watching\_context.valid.json  
open\_position\_context.valid.json  
partial\_position\_context.valid.json  
closed\_context.valid.json  
context\_with\_pending\_stop.valid.json  
context\_with\_pending\_target.valid.json  
context\_with\_historical\_chart.valid.json  
compressed\_history.valid.json

Coverage:

* all lifecycle states;  
* canonical facts;  
* active and proposed levels;  
* important history;  
* unresolved proposals;  
* closing context.

---

# **Part III — Invalid JSON Schema Fixtures**

## **23\. Shared Invalid Schema Rules**

Every root schema must have fixtures for:

missing\_required\_property.invalid.json  
unknown\_property.invalid.json  
wrong\_property\_type.invalid.json  
invalid\_enum.invalid.json  
invalid\_uuid.invalid.json  
invalid\_timestamp.invalid.json  
negative\_price.invalid.json  
probability\_above\_100.invalid.json  
probability\_below\_0.invalid.json  
empty\_required\_narrative.invalid.json

Expected stage:

SCHEMA

---

## **24\. Market Snapshot Invalid Schema Fixtures**

missing\_trading\_date.invalid.json  
invalid\_update\_period.invalid.json  
negative\_volume.invalid.json  
negative\_transaction\_value.invalid.json  
string\_price.invalid.json  
unavailable\_without\_nulls.invalid.json

These primarily test JSON Schema constraints.

OHLC relationship violations belong to domain fixtures because their individual field types remain valid.

---

## **25\. Trade State Invalid Schema Fixtures**

missing\_session\_status.invalid.json  
invalid\_position\_status.invalid.json  
closed\_remaining\_quantity\_string.invalid.json  
confirmed\_action\_missing\_id.invalid.json  
invalid\_action\_type.invalid.json  
unknown\_position\_property.invalid.json

---

## **26\. Analysis Invalid Schema Fixtures**

Each analysis schema must test:

* incorrect `metadata.analysis_type`;  
* incorrect schema name;  
* incorrect schema version;  
* incorrect language;  
* missing AI assessment;  
* invalid recommended action;  
* invalid confidence range;  
* invalid target realism;  
* conditional rule violation;  
* unknown top-level section.

Example:

wrong\_analysis\_type.invalid.json  
wrong\_schema\_name.invalid.json  
missing\_trading\_plan.invalid.json  
exit\_action\_without\_confirmation\_flag.invalid.json  
revised\_stop\_true\_without\_price.invalid.json

---

# **Part IV — Invalid Domain Fixtures**

## **27\. Market Domain Fixtures**

Required:

high\_below\_low.invalid.json  
high\_below\_last.invalid.json  
low\_above\_open.invalid.json  
average\_outside\_range.invalid.json  
offer\_below\_bid.invalid.json  
spread\_mismatch.invalid.json  
spread\_percentage\_mismatch.invalid.json  
change\_mismatch.invalid.json  
change\_percentage\_mismatch.invalid.json  
timestamp\_date\_mismatch.invalid.json  
update\_period\_mismatch.invalid.json

Each fixture must pass JSON Schema validation first.

Expected codes must match `DOMAIN_VALIDATION_RULES.md`.

---

## **28\. Position State Domain Fixtures**

Required:

open\_remaining\_not\_equal\_original.invalid.json  
partial\_remaining\_not\_reduced.invalid.json  
partial\_missing\_average\_exit.invalid.json  
closed\_with\_remaining\_quantity.invalid.json  
closed\_with\_active\_stop.invalid.json  
closed\_with\_active\_target.invalid.json  
quantity\_conservation\_failed.invalid.json  
confirmed\_actions\_contradict\_state.invalid.json

---

## **29\. Canonical Conflict Fixtures**

Required:

analysis\_ticker\_mismatch.invalid.json  
entry\_price\_mismatch.invalid.json  
remaining\_quantity\_mismatch.invalid.json  
active\_stop\_mismatch.invalid.json  
active\_target\_mismatch.invalid.json  
session\_id\_mismatch.invalid.json  
proposed\_stop\_presented\_as\_active.invalid.json  
proposed\_target\_presented\_as\_active.invalid.json

Expected stage:

STATE\_CONSISTENCY

---

## **30\. Entry Domain Fixtures**

Required:

entry\_zone\_low\_above\_high.invalid.json  
maximum\_entry\_below\_exact\_entry.invalid.json  
maximum\_entry\_below\_zone.invalid.json  
confirmation\_required\_without\_condition.invalid.json  
no\_entry\_with\_entry\_price.invalid.json  
extended\_price\_low\_chase\_risk.invalid.json  
missing\_cancel\_condition.invalid.json

---

## **31\. Stop-Loss Domain Fixtures**

Required:

initial\_stop\_above\_entry.invalid.json  
initial\_stop\_equal\_entry.invalid.json  
active\_stop\_above\_current.invalid.json  
stop\_trigger\_flag\_false\_below\_stop.invalid.json  
risk\_percentage\_mismatch.invalid.json  
initial\_risk\_above\_limit.invalid.json  
protective\_stop\_above\_current.invalid.json  
stop\_above\_target.invalid.json

---

## **32\. Target Domain Fixtures**

Required:

initial\_target\_below\_entry.invalid.json  
initial\_target\_equal\_entry.invalid.json  
reward\_percentage\_mismatch.invalid.json  
risk\_reward\_ratio\_mismatch.invalid.json  
risk\_reward\_zero\_denominator.invalid.json  
target\_reached\_without\_price\_evidence.invalid.json  
target\_probability\_without\_target.invalid.json

---

## **33\. Probability Domain Fixtures**

Required warning fixtures:

target\_probability\_far\_above\_bullish.invalid.json  
strongly\_bullish\_with\_low\_probability.invalid.json  
high\_confidence\_without\_orderbook.invalid.json  
high\_confidence\_with\_insufficient\_context.invalid.json

Some may produce warnings rather than blocking errors.

Expected sidecar must specify severity.

---

## **34\. Partial Exit Domain Fixtures**

Required:

partial\_exit\_zero\_quantity.invalid.json  
partial\_exit\_exceeds\_remaining.invalid.json  
partial\_exit\_closes\_full\_position.invalid.json  
partial\_exit\_quantity\_mismatch.invalid.json  
partial\_realized\_pl\_mismatch.invalid.json  
partial\_return\_mismatch.invalid.json  
capital\_recovered\_mismatch.invalid.json  
average\_exit\_mismatch.invalid.json  
remaining\_unrealized\_pl\_mismatch.invalid.json  
partial\_total\_pl\_mismatch.invalid.json  
partial\_total\_return\_mismatch.invalid.json

---

## **35\. Closing Domain Fixtures**

Required:

final\_exit\_quantity\_mismatch.invalid.json  
final\_quantity\_conservation\_failed.invalid.json  
weighted\_average\_exit\_mismatch.invalid.json  
gross\_pl\_mismatch.invalid.json  
gross\_return\_mismatch.invalid.json  
net\_pl\_mismatch.invalid.json  
net\_return\_mismatch.invalid.json  
net\_result\_with\_missing\_fees.invalid.json  
outcome\_classification\_mismatch.invalid.json  
closing\_reason\_status\_mismatch.invalid.json  
timeline\_out\_of\_order.invalid.json  
duplicate\_timeline\_event.invalid.json  
closing\_before\_final\_exit.invalid.json

---

## **36\. Context Domain Fixtures**

Required:

context\_entry\_mismatch.invalid.json  
context\_quantity\_mismatch.invalid.json  
context\_active\_stop\_mismatch.invalid.json  
context\_active\_target\_mismatch.invalid.json  
context\_event\_after\_cutoff.invalid.json  
context\_generated\_before\_cutoff.invalid.json  
context\_stale\_before\_analysis.invalid.json  
pending\_stop\_lost.invalid.json  
proposal\_promoted\_without\_confirmation.invalid.json  
closed\_context\_missing\_result.invalid.json  
open\_context\_has\_closing\_result.invalid.json

---

## **37\. Lifecycle Fixtures**

Required:

draft\_to\_open\_position.invalid.json  
watching\_to\_partial.invalid.json  
closed\_to\_open.invalid.json  
archived\_to\_open.invalid.json  
open\_without\_user\_confirmation.invalid.json  
partial\_without\_confirmation.invalid.json  
close\_without\_confirmation.invalid.json  
ai\_direct\_state\_transition.invalid.json

Expected stage:

LIFECYCLE

---

# **Part V — Fixture Factories**

## **38\. Why Factories Are Needed**

Static JSON fixtures are useful for readability and regression.

Factories are needed to:

* reduce duplication;  
* create controlled variations;  
* test numeric boundaries;  
* generate many valid states;  
* generate combinations for property-based testing.

Factories must produce deterministic defaults.

---

## **39\. Market Snapshot Factory**

Recommended interface:

def make\_market\_snapshot(  
    \*,  
    open\_price: str \= "2840",  
    high: str \= "2910",  
    low: str \= "2820",  
    last: str | None \= "2890",  
    close: str | None \= None,  
    previous\_close: str \= "2830",  
    average: str \= "2867",  
    best\_bid: str \= "2880",  
    best\_offer: str \= "2890",  
    update\_period: str \= "MIDDAY",  
    data\_available: bool \= True,  
) \-\> dict:  
    ...

The factory should calculate:

* change;  
* change percentage;  
* spread;  
* spread percentage.

---

## **40\. Trade State Factory**

Recommended interface:

def make\_trade\_state(  
    \*,  
    session\_status: str \= "OPEN\_POSITION",  
    position\_status: str \= "OPEN",  
    entry\_price: str | None \= "2800",  
    original\_quantity: str | None \= "100",  
    remaining\_quantity: str | None \= "100",  
    active\_stop\_loss: str | None \= "2840",  
    active\_target: str | None \= "2920",  
) \-\> dict:  
    ...

Factory variants:

make\_watching\_trade\_state()  
make\_open\_trade\_state()  
make\_partial\_trade\_state()  
make\_closed\_trade\_state()

---

## **41\. Analysis Factory**

Recommended interface:

def make\_analysis\_payload(  
    \*,  
    analysis\_type: str,  
    trade\_state: dict,  
    market\_snapshot: dict | None \= None,  
    overrides: dict | None \= None,  
) \-\> dict:  
    ...

The factory should:

* inject metadata;  
* select correct schema name;  
* use fixed timestamps;  
* copy canonical facts;  
* calculate deterministic fields;  
* produce minimally valid narratives.

---

## **42\. Deep Merge Utility**

Overrides should use a deep merge function.

Example:

payload \= make\_open\_position\_update()

payload \= deep\_merge(  
    payload,  
    {  
        "position\_assessment": {  
            "entry\_price": 2820  
        }  
    }  
)

This allows one-field invalid fixtures without duplicating the entire payload.

---

## **43\. Context Factory**

Recommended variants:

make\_watching\_context()  
make\_open\_position\_context()  
make\_partial\_position\_context()  
make\_closed\_context()

The context factory must derive canonical facts from Trade State rather than duplicate manually supplied values where possible.

---

# **Part VI — Scenario Fixtures**

## **44\. Scenario Package Structure**

Each scenario directory should contain:

scenario.json  
trade\_state/  
evidence/  
analyses/  
actions/  
context/  
expected/

Example:

scenarios/partial\_exit\_then\_close/  
├── scenario.json  
├── trade\_state/  
│   ├── 01\_watching.json  
│   ├── 02\_open.json  
│   ├── 03\_partial.json  
│   └── 04\_closed.json  
├── evidence/  
├── analyses/  
│   ├── 01\_initial\_analysis.json  
│   ├── 02\_watching\_update.json  
│   ├── 03\_open\_position\_update.json  
│   ├── 04\_partial\_exit\_review.json  
│   └── 05\_closing\_analysis.json  
├── actions/  
│   ├── 01\_position\_opened.json  
│   ├── 02\_partial\_exit.json  
│   └── 03\_full\_exit.json  
├── context/  
│   ├── 01\_after\_initial.json  
│   ├── 02\_after\_entry.json  
│   ├── 03\_after\_partial.json  
│   └── 04\_after\_close.json  
└── expected/  
    └── final\_result.json

---

## **45\. Scenario Manifest**

Example:

{  
  "scenario\_name": "partial\_exit\_then\_close",  
  "description": "A profitable long trade with one partial exit and one final exit.",  
  "initial\_session\_status": "READY\_FOR\_ANALYSIS",  
  "final\_session\_status": "CLOSED\_MANUAL",  
  "expected\_analysis\_count": 5,  
  "expected\_action\_count": 3,  
  "expected\_gross\_profit\_loss": 11000,  
  "expected\_gross\_return\_percentage": 3.93,  
  "expected\_trade\_grade": "A"  
}

---

## **46\. Required End-to-End Scenarios**

### **46.1 Profitable full take-profit**

Lifecycle:

READY\_FOR\_ANALYSIS  
\-\> WATCHING  
\-\> OPEN\_POSITION  
\-\> CLOSED\_TAKE\_PROFIT

### **46.2 Stop-loss exit**

Lifecycle:

READY\_FOR\_ANALYSIS  
\-\> WATCHING  
\-\> OPEN\_POSITION  
\-\> CLOSED\_STOP\_LOSS

### **46.3 Manual profitable exit**

Lifecycle:

READY\_FOR\_ANALYSIS  
\-\> WATCHING  
\-\> OPEN\_POSITION  
\-\> CLOSED\_MANUAL

### **46.4 Partial exit followed by final exit**

Lifecycle:

READY\_FOR\_ANALYSIS  
\-\> WATCHING  
\-\> OPEN\_POSITION  
\-\> PARTIALLY\_CLOSED  
\-\> CLOSED\_MANUAL

### **46.5 Watched setup cancelled before entry**

Lifecycle:

READY\_FOR\_ANALYSIS  
\-\> WATCHING  
\-\> CANCELLED

No live position should exist.

### **46.6 Thesis invalidated while position open**

The AI recommends exit, but canonical state remains open until user confirmation.

### **46.7 Provider output conflicts with Trade State**

The analysis must fail validation and enter repair flow.

### **46.8 Stale context rebuilt before analysis**

The initial context fails freshness validation, gets rebuilt, and then analysis succeeds.

---

# **Part VII — Provider Contract Fixtures**

## **47\. Provider Fixture Structure**

Each provider response fixture should include:

{  
  "provider": "GEMINI",  
  "model": "fixture-model",  
  "request\_analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "response\_mode": "STRUCTURED\_JSON",  
  "raw\_response": {},  
  "expected\_parse\_result": "SUCCESS",  
  "expected\_validation\_result": "VALID"  
}

Raw provider responses may be stored separately when large.

---

## **48\. Gemini Contract Fixtures**

Required:

gemini\_valid\_structured\_json.json  
gemini\_json\_in\_markdown\_fence.json  
gemini\_leading\_commentary.json  
gemini\_missing\_required\_field.json  
gemini\_invalid\_enum.json  
gemini\_extra\_property.json  
gemini\_truncated\_json.json  
gemini\_state\_conflict.json  
gemini\_refusal.json  
gemini\_empty\_response.json

---

## **49\. DeepSeek Contract Fixtures**

Required:

deepseek\_valid\_structured\_json.json  
deepseek\_json\_in\_markdown\_fence.json  
deepseek\_leading\_commentary.json  
deepseek\_missing\_required\_field.json  
deepseek\_invalid\_enum.json  
deepseek\_extra\_property.json  
deepseek\_truncated\_json.json  
deepseek\_state\_conflict.json  
deepseek\_refusal.json  
deepseek\_empty\_response.json

Both providers must be tested against identical expected schemas.

---

## **50\. JSON Extraction Fixtures**

Required raw strings:

plain\_object.txt  
markdown\_json\_fence.txt  
leading\_text\_then\_json.txt  
json\_then\_trailing\_text.txt  
multiple\_json\_objects.txt  
malformed\_json.txt  
json\_array\_instead\_of\_object.txt  
duplicate\_critical\_keys.txt  
nan\_value.txt  
infinity\_value.txt

Expected extraction behavior must be explicit.

---

## **51\. Repair Fixtures**

Required scenarios:

repair\_missing\_required\_field/  
repair\_invalid\_enum/  
repair\_state\_conflict/  
repair\_invalid\_probability/  
repair\_unknown\_property/  
repair\_malformed\_json/  
repair\_failure\_same\_error/  
repair\_introduces\_new\_error/

Each repair scenario should contain:

original\_response.json  
validation\_errors.json  
repair\_prompt.txt  
repaired\_response.json  
expected\_result.json

---

## **52\. Repair Success Requirements**

A successful repaired payload must:

* validate against the expected schema;  
* preserve canonical facts;  
* remove all blocking validation issues;  
* not introduce unknown properties;  
* not change analysis type;  
* not change schema version;  
* return JSON only.

---

## **53\. Repair Failure Requirements**

The repair attempt must fail when it:

* repeats the same blocking error;  
* changes canonical entry;  
* changes quantity;  
* changes session ticker;  
* invents a confirmed execution;  
* produces another schema type;  
* returns malformed JSON.

---

## **54\. Fallback Fixtures**

Required:

primary\_valid\_no\_fallback/  
primary\_invalid\_repair\_valid/  
primary\_invalid\_repair\_invalid\_fallback\_valid/  
all\_attempts\_invalid/  
primary\_transport\_error\_fallback\_valid/  
primary\_refusal\_fallback\_valid/

Assertions should include:

* provider-call count;  
* provider order;  
* repair-attempt count;  
* final accepted provider;  
* validation result;  
* persisted raw responses.

---

# **Part VIII — Context Summary Fixtures**

## **55\. Context Build Input Bundle**

A Context Summary test should provide:

trade\_state.json  
latest\_analysis.json  
accepted\_analyses.json  
evidence\_index.json  
confirmed\_actions.json  
pending\_proposals.json  
expected\_context.json

The test should build context from source data and compare it with expected output.

---

## **56\. Context Rebuild Tests**

Required:

rebuild\_after\_initial\_analysis  
rebuild\_after\_watching\_update  
rebuild\_after\_position\_opened  
rebuild\_after\_stop\_changed  
rebuild\_after\_target\_changed  
rebuild\_after\_open\_position\_update  
rebuild\_after\_partial\_exit  
rebuild\_after\_full\_exit  
rebuild\_after\_evidence\_replacement

---

## **57\. Context Preservation Tests**

The builder must preserve:

* original thesis;  
* latest thesis;  
* confirmed entry;  
* active stop;  
* active target;  
* all confirmed exits;  
* pending proposal;  
* latest accepted analysis;  
* latest evidence timestamp;  
* material history.

Required regression fixtures:

original\_thesis\_not\_lost  
confirmed\_stop\_not\_replaced\_by\_proposal  
partial\_exit\_not\_lost  
pending\_target\_preserved  
historical\_chart\_timestamp\_preserved

---

# **Part IX — Boundary Tests**

## **58\. Probability Boundaries**

Test values:

0  
1  
99  
100  
\-1  
101

Expected:

* 0–100 valid;  
* \-1 and 101 invalid.

---

## **59\. Risk Boundaries**

Maximum risk configured at 5%.

Test:

4.99%  
5.00%  
5.01%

Expected:

* 4.99 valid;  
* 5.00 valid;  
* 5.01 invalid.

---

## **60\. Break-Even Classification Boundaries**

Test:

\-0.26%  
\-0.25%  
0.00%  
0.25%  
0.26%

Expected classification:

\-0.26 \-\> SMALL\_LOSS  
\-0.25 \-\> BREAK\_EVEN  
0.00 \-\> BREAK\_EVEN  
0.25 \-\> BREAK\_EVEN  
0.26 \-\> SMALL\_PROFIT

---

## **61\. Evidence Staleness Boundaries**

Orderbook thresholds:

15 minutes  
60 minutes

Test:

14m59s  
15m00s  
15m01s  
59m59s  
60m00s  
60m01s

Expected behavior must follow configured inclusive/exclusive rules.

Recommended:

age \<= 15m:  
    fresh

15m \< age \<= 60m:  
    warning

age \> 60m:  
    error

---

## **62\. Quantity Boundaries**

Test:

remaining \= original  
remaining \= 1  
remaining \= 0  
remaining \> original  
remaining \< 0

Interpretation depends on position status.

---

## **63\. Timestamp Clock Skew**

Allowed future skew:

60 seconds

Test:

now \+ 59 seconds  
now \+ 60 seconds  
now \+ 61 seconds

---

# **Part X — Property-Based Tests**

## **64\. Property-Based Testing**

Recommended library:

Hypothesis

Property-based tests should supplement, not replace, static fixtures.

---

## **65\. Market OHLC Properties**

Generate valid values satisfying:

low \<= open \<= high  
low \<= last \<= high

Expected:

* validator passes.

Mutate one relationship per test.

Expected:

* validator produces the correct error.

---

## **66\. Position Quantity Properties**

Generate:

original\_quantity \> 0  
0 \<= remaining\_quantity \<= original\_quantity

For partial states:

0 \< remaining\_quantity \< original\_quantity

For closed states:

remaining\_quantity \= 0

---

## **67\. Exit Calculation Properties**

Generate one entry and multiple exits satisfying quantity conservation.

Assert:

* weighted average exit;  
* realized P/L;  
* gross return;  
* final remaining quantity.

---

## **68\. Decimal Precision Properties**

Generate decimal USD prices with two to four decimal places.

Assert:

* Decimal-based calculations remain stable;  
* results do not exhibit binary floating-point artifacts;  
* configured rounding is applied.

---

# **Part XI — Pytest Implementation**

## **69\. Valid Schema Test Pattern**

import json  
from pathlib import Path

import pytest

VALID\_FIXTURES \= list(  
    Path("tests/fixtures/schemas/valid").rglob("\*.valid.json")  
)

@pytest.mark.parametrize("fixture\_path", VALID\_FIXTURES)  
def test\_valid\_schema\_fixture(  
    fixture\_path: Path,  
    schema\_registry,  
):  
    payload \= json.loads(fixture\_path.read\_text())

    schema\_name \= fixture\_path.parent.name  
    validator \= schema\_registry.get(  
        name=schema\_name,  
        version="1.0.0",  
    ).compiled\_validator

    errors \= list(validator.iter\_errors(payload))

    assert errors \== \[\]

The actual schema name should preferably come from fixture metadata or a fixture index rather than relying only on directory names.

---

## **70\. Invalid Schema Test Pattern**

@pytest.mark.parametrize(  
    "fixture\_path",  
    list(Path("tests/fixtures/schemas/invalid").rglob("\*.invalid.json")),  
)  
def test\_invalid\_schema\_fixture(  
    fixture\_path: Path,  
    schema\_registry,  
):  
    payload \= load\_json(fixture\_path)  
    expected \= load\_expected\_sidecar(fixture\_path)

    validator \= resolve\_validator(  
        fixture\_path=fixture\_path,  
        registry=schema\_registry,  
    )

    issues \= normalize\_schema\_errors(  
        validator.iter\_errors(payload)  
    )

    assert issues  
    assert\_expected\_issues(  
        actual=issues,  
        expected=expected\["expected\_issues"\],  
    )

---

## **71\. Domain Fixture Test Pattern**

@pytest.mark.parametrize(  
    "fixture\_path",  
    list(Path("tests/fixtures/domain/invalid").rglob("\*.invalid.json")),  
)  
def test\_invalid\_domain\_fixture(  
    fixture\_path: Path,  
    validation\_service,  
):  
    bundle \= load\_domain\_fixture\_bundle(fixture\_path)  
    expected \= load\_expected\_sidecar(fixture\_path)

    result \= validation\_service.validate(  
        payload=bundle.payload,  
        expected\_analysis\_type=bundle.analysis\_type,  
        trade\_state=bundle.trade\_state,  
        session\_status\_before\_job=bundle.session\_status,  
        context\_summary=bundle.context\_summary,  
    )

    assert result.valid is False  
    assert\_expected\_issues(  
        actual=result.issues,  
        expected=expected\["expected\_issues"\],  
    )

---

## **72\. Assertion Matching Rules**

By default, tests should assert:

* validation code;  
* JSON Pointer path;  
* severity.

Tests should not normally assert the full human-readable message because wording may improve without changing behavior.

Optional strict message tests may exist for public API errors.

---

## **73\. Multiple-Issue Fixtures**

Some fixtures intentionally produce multiple errors.

Their sidecar must declare:

{  
  "issue\_match\_mode": "EXACT\_SET",  
  "expected\_issues": \[\]  
}

Supported modes:

EXACT\_SET  
CONTAINS  
FIRST\_ERROR

Default:

CONTAINS

This avoids fragile tests where one invalid value triggers several related diagnostics.

---

## **74\. Ordering of Issues**

Validation issue ordering must be deterministic.

Recommended sort order:

1. severity;  
2. JSON Pointer path;  
3. error code.

Tests should normalize order before comparison.

---

# **Part XII — Golden Fixtures**

## **75\. Golden Payloads**

The following should be designated golden fixtures:

initial\_analysis.complete\_setup.valid.json  
watching\_update.entry\_confirmation\_met.valid.json  
open\_position\_update.midday\_hold.valid.json  
partial\_exit\_review.partial\_take\_profit.valid.json  
closing\_analysis.partial\_then\_final\_close.valid.json  
context\_summary.open\_position\_context.valid.json

Golden fixtures represent the preferred production payload shape.

They may be used for:

* API examples;  
* developer documentation;  
* frontend mock data;  
* provider prompt examples;  
* end-to-end tests.

---

## **76\. Golden Fixture Change Control**

Changing a golden fixture requires review of:

* JSON Schema;  
* domain rules;  
* frontend rendering;  
* AI prompt;  
* database storage;  
* context builder;  
* API contract.

Golden fixtures should not be modified casually.

---

# **Part XIII — Frontend Fixture Usage**

## **77\. Frontend Mock Data**

Validated golden fixtures may be copied or imported into frontend test data.

Recommended location:

frontend/  
└── src/  
    └── test/  
        └── fixtures/  
            ├── initial-analysis.json  
            ├── watching-update.json  
            ├── open-position-update.json  
            ├── partial-exit-review.json  
            └── closing-analysis.json

The backend fixture remains the source of truth.

---

## **78\. UI Rendering Tests**

Frontend tests should verify that each golden payload renders:

* section titles;  
* price values;  
* probabilities;  
* thesis state;  
* active action;  
* warning blocks;  
* pending confirmation;  
* material changes;  
* empty optional sections.

Frontend tests must not reinterpret canonical values.

---

# **Part XIV — Migration Fixtures**

## **79\. Migration Fixture Package**

Each migration case should contain:

source\_payload.json  
source\_schema.json  
migration\_config.json  
expected\_payload.json  
expected\_validation.json

---

## **80\. Migration Test Requirements**

A migration test must:

1. validate source against old schema;  
2. execute migration;  
3. validate output against new schema;  
4. run domain validation;  
5. verify canonical facts remain unchanged;  
6. verify historical source remains available.

---

## **81\. Invalid Migration Fixtures**

Required examples:

migration\_drops\_entry\_price.invalid.json  
migration\_changes\_quantity.invalid.json  
migration\_unknown\_enum.invalid.json  
migration\_missing\_required\_field.invalid.json  
migration\_result\_domain\_invalid.invalid.json

---

# **Part XV — Coverage Requirements**

## **82\. Minimum Schema Coverage**

Every:

* required property;  
* enum value;  
* conditional branch;  
* nullable branch;  
* root schema;  
* major `$ref`;

must be exercised by at least one fixture.

---

## **83\. Minimum Domain-Rule Coverage**

Every blocking error code in `DOMAIN_VALIDATION_RULES.md` must have at least one failing test.

Every warning code should have at least one test where practical.

---

## **84\. Lifecycle Coverage**

Every allowed transition and every explicitly forbidden transition must be tested.

---

## **85\. Provider Coverage**

Both Gemini and DeepSeek adapters must pass the same contract-test suite.

Provider-specific parsing tests may be added, but schema expectations must remain identical.

---

## **86\. Calculation Coverage**

Required calculation tests:

* nominal change;  
* change percentage;  
* spread;  
* spread percentage;  
* unrealized P/L;  
* unrealized return;  
* distance to stop;  
* distance to target;  
* risk percentage;  
* reward percentage;  
* risk-reward ratio;  
* realized partial P/L;  
* weighted average exit;  
* total partial-state P/L;  
* gross closing P/L;  
* gross return;  
* net P/L;  
* net return.

---

# **Part XVI — Fixture Validation Command**

## **87\. Local Command**

Recommended:

python \-m app.schema\_validation.validate\_fixtures

Optional filtering:

python \-m app.schema\_validation.validate\_fixtures \\  
  \--schema open\_position\_update

python \-m app.schema\_validation.validate\_fixtures \\  
  \--category domain

python \-m app.schema\_validation.validate\_fixtures \\  
  \--scenario partial\_exit\_then\_close

---

## **88\. Expected Output**

TradePilot AI Fixture Validation

Manifest fixtures:  
  Passed: 10  
  Failed: 0

Valid schema fixtures:  
  Passed: 72  
  Failed: 0

Invalid schema fixtures:  
  Passed: 81  
  Failed: 0

Valid domain fixtures:  
  Passed: 31  
  Failed: 0

Invalid domain fixtures:  
  Passed: 96  
  Failed: 0

Provider contracts:  
  Passed: 28  
  Failed: 0

Integration scenarios:  
  Passed: 8  
  Failed: 0

Result: PASS

---

## **89\. CI Command**

Recommended:

pytest \\  
  tests/test\_schema\_registry.py \\  
  tests/test\_schema\_valid\_fixtures.py \\  
  tests/test\_schema\_invalid\_fixtures.py \\  
  tests/test\_domain\_valid\_fixtures.py \\  
  tests/test\_domain\_invalid\_fixtures.py \\  
  tests/test\_trade\_session\_scenarios.py \\  
  tests/test\_provider\_contracts.py \\  
  tests/test\_context\_summary.py

CI must return non-zero when:

* a valid fixture fails;  
* an invalid fixture unexpectedly passes;  
* expected error code changes;  
* a schema reference cannot resolve;  
* a golden fixture changes without approval;  
* a provider contract fails.

---

# **Part XVII — Initial Fixture Implementation Priority**

## **90\. Phase 1 Fixtures**

Create first:

1. Valid manifest.  
2. Valid Market Snapshot.  
3. Valid Trade State for watching, open, partial, and closed states.  
4. Valid Open Position Update.  
5. Invalid canonical entry mismatch.  
6. Invalid remaining quantity mismatch.  
7. Invalid active stop mismatch.  
8. Invalid target mismatch.  
9. Valid partial exit.  
10. Valid closing result.

These fixtures unblock the first validator implementation.

---

## **91\. Phase 2 Fixtures**

Add:

* Initial Analysis;  
* Watching Update;  
* Context Summary;  
* all market calculation failures;  
* all entry, stop, and target rules;  
* lifecycle transitions.

---

## **92\. Phase 3 Fixtures**

Add:

* provider repair;  
* provider fallback;  
* complete end-to-end scenarios;  
* migrations;  
* property-based tests;  
* frontend golden fixture consumption.

---

# **Part XVIII — Acceptance Criteria**

## **93\. Fixture Specification Completion**

The fixture implementation is complete when:

1. Every production schema has valid fixtures.  
2. Every production schema has invalid fixtures.  
3. All blocking domain error codes have tests.  
4. Canonical Trade State conflicts are covered.  
5. Every lifecycle transition is covered.  
6. Partial and full exit calculations are covered.  
7. Context Summary rebuild and staleness are covered.  
8. Gemini and DeepSeek share one contract-test suite.  
9. Repair and fallback flows are tested.  
10. Golden fixtures are available for frontend development.  
11. Fixtures use fixed IDs and timestamps.  
12. All calculations use Decimal-compatible source values.  
13. CI validates the entire fixture package.  
14. No fixture test depends on live APIs or the current date.  
15. Expected failures assert stable code and JSON Pointer path.

---

## **94\. Recommended Next Artifact**

The next required implementation document is:

IMPLEMENTATION\_PLAN.md

It should convert all existing product and engineering specifications into an ordered delivery plan covering:

* repository scaffolding;  
* backend foundation;  
* database migrations;  
* schema registry;  
* domain validators;  
* AI provider adapters;  
* analysis worker;  
* context-memory builder;  
* Trade Session API;  
* frontend session pages;  
* user confirmation workflows;  
* fixture and integration testing;  
* deployment to VPS.

