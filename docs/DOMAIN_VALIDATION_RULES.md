# **DOMAIN\_VALIDATION\_RULES.md**

## **TradePilot AI Domain Validation Rules**

**Document Version:** 1.0  
**Status:** Draft for Implementation  
**Applies To:** Production schema package v1.0.0  
**Primary Runtime:** Python backend  
**Trading Direction:** Long positions only in version 1  
**Primary Market Context:** Indonesian and United States equities

---

## **1\. Purpose**

This document defines the business validation rules that cannot be enforced reliably through JSON Schema alone.

Domain validation ensures that:

* market values are mathematically consistent;  
* trade calculations are correct;  
* AI output matches canonical Trade State;  
* entry, stop-loss, and target relationships are logical;  
* partial exits and final exits reconcile with confirmed quantities;  
* lifecycle states remain valid;  
* analysis timestamps and historical context remain chronological;  
* AI proposals are never interpreted as confirmed actions;  
* deterministic financial values come from backend calculations.

JSON Schema validates structure.

Domain validators validate meaning.

---

## **2\. Scope**

The rules apply to:

* `market_snapshot.schema.json`;  
* `trade_state.schema.json`;  
* `initial_analysis.schema.json`;  
* `watching_update.schema.json`;  
* `open_position_update.schema.json`;  
* `partial_exit_review.schema.json`;  
* `closing_analysis.schema.json`;  
* `context_summary.schema.json`.

The following are not included in version 1:

* short selling;  
* leveraged positions;  
* options;  
* futures;  
* foreign-exchange positions;  
* multiple entry lots with independent cost bases;  
* corporate-action adjustments;  
* automatic broker execution;  
* portfolio-level capital allocation.

Version 1 assumes one long position per Trade Session.

---

## **3\. Validation Severity**

Every domain issue must have one of the following severities.

### **3.1 Error**

An error blocks payload acceptance.

Examples:

* canonical entry price mismatch;  
* remaining quantity exceeds original quantity;  
* target below entry;  
* impossible OHLC values;  
* partial exit quantity mismatch;  
* final position still has remaining quantity.

### **3.2 Warning**

A warning does not block acceptance unless strict configuration promotes it to an error.

Examples:

* chart context is old;  
* orderbook screenshot is stale;  
* target is technically valid but risk-reward is weak;  
* market snapshot is incomplete;  
* confidence is high despite limited evidence.

### **3.3 Informational**

An informational issue is used for diagnostics and observability.

Examples:

* deterministic AI value was replaced by backend value;  
* percentage was normalized within rounding tolerance;  
* unavailable optional data was retained as `null`.

---

## **4\. Validation Issue Contract**

Recommended domain issue format:

{  
  "code": "POSITION\_ENTRY\_PRICE\_MISMATCH",  
  "category": "STATE\_CONFLICT",  
  "severity": "ERROR",  
  "path": "/position\_assessment/entry\_price",  
  "message": "Entry price does not match canonical Trade State.",  
  "expected": 2800,  
  "actual": 2820,  
  "context": {  
    "session\_id": "d95b3775-aa8c-49fb-b5a8-19c475b5bcc1"  
  }  
}

Required fields:

* `code`;  
* `category`;  
* `severity`;  
* `path`;  
* `message`.

Optional fields:

* `expected`;  
* `actual`;  
* `context`.

---

## **5\. Error Categories**

Supported categories:

MARKET\_DATA  
CALCULATION  
PRICE\_RELATIONSHIP  
POSITION\_STATE  
STATE\_CONFLICT  
USER\_CONFIRMATION  
LIFECYCLE  
TIMESTAMP  
EVIDENCE  
THESIS  
PROBABILITY  
CONTEXT  
CLOSING  
DATA\_QUALITY

---

## **6\. Numeric Precision**

Financial calculations must use decimal arithmetic.

Python implementations must use:

from decimal import Decimal

Binary floating-point values must not be used as the authoritative calculation source.

Recommended conversion:

def to\_decimal(value: int | float | str) \-\> Decimal:  
    return Decimal(str(value))

---

## **7\. Rounding Rules**

### **7.1 Monetary values**

P/L values should be rounded according to the currency configuration.

Default rules:

IDR: 0 decimal places  
USD: 2 decimal places

### **7.2 Percentages**

Percentages should be rounded to two decimal places for persistence and display comparison.

### **7.3 Risk-reward ratio**

Risk-reward ratios should be rounded to two decimal places.

### **7.4 Probability**

Probabilities are whole integers from 0 through 100\.

### **7.5 Quantity**

Quantity may be fractional in the generic schema to support markets that allow fractional shares.

For IDX implementation, a market-specific validator may require whole-share or lot-compatible quantities.

---

## **8\. Validation Tolerances**

Recommended default tolerances:

PRICE\_ABSOLUTE\_TOLERANCE \= Decimal("0.01")  
PERCENTAGE\_ABSOLUTE\_TOLERANCE \= Decimal("0.02")  
RATIO\_ABSOLUTE\_TOLERANCE \= Decimal("0.02")  
MONEY\_ABSOLUTE\_TOLERANCE\_IDR \= Decimal("1")  
MONEY\_ABSOLUTE\_TOLERANCE\_USD \= Decimal("0.01")  
PROBABILITY\_TOLERANCE \= 0  
TIMESTAMP\_CLOCK\_SKEW\_SECONDS \= 60

Market-specific price tick size may override `PRICE_ABSOLUTE_TOLERANCE`.

---

## **9\. Comparison Function**

Recommended helper:

from decimal import Decimal

def approximately\_equal(  
    actual: Decimal,  
    expected: Decimal,  
    tolerance: Decimal,  
) \-\> bool:  
    return abs(actual \- expected) \<= tolerance

Relative tolerance may be added for large transaction values, but price, percentage, and quantity rules should primarily use explicit absolute tolerances.

---

# **Part I — Market Snapshot Rules**

## **10\. Market Snapshot Availability**

When `data_available = false`:

* market numeric fields must be `null`;  
* source must be `UNAVAILABLE`;  
* limitations must contain at least one item;  
* analysis must not infer current market values;  
* price-dependent deterministic calculations must remain unavailable.

Error codes:

MARKET\_DATA\_UNAVAILABLE\_HAS\_VALUES  
MARKET\_DATA\_UNAVAILABLE\_INVALID\_SOURCE  
MARKET\_DATA\_UNAVAILABLE\_WITHOUT\_LIMITATION

---

## **11\. Minimum Available Price**

When `data_available = true`, at least one of these must exist:

* `last`;  
* `close`.

For an intraday update, `last` is preferred.

For a final market-close update, `close` is preferred.

Error code:

MARKET\_PRICE\_MISSING

Warning codes:

INTRADAY\_LAST\_PRICE\_MISSING  
MARKET\_CLOSE\_CLOSE\_PRICE\_MISSING

---

## **12\. OHLC Relationship Rules**

When values are available:

high \>= low  
high \>= open  
high \>= last  
high \>= close  
low \<= open  
low \<= last  
low \<= close

The validator only compares pairs where both values are non-null.

Error codes:

MARKET\_HIGH\_BELOW\_LOW  
MARKET\_HIGH\_BELOW\_OPEN  
MARKET\_HIGH\_BELOW\_LAST  
MARKET\_HIGH\_BELOW\_CLOSE  
MARKET\_LOW\_ABOVE\_OPEN  
MARKET\_LOW\_ABOVE\_LAST  
MARKET\_LOW\_ABOVE\_CLOSE

---

## **13\. Positive Price Rules**

All available market prices must be greater than zero:

* open;  
* high;  
* low;  
* last;  
* close;  
* previous close;  
* average;  
* best bid;  
* best offer.

Error code:

MARKET\_PRICE\_NOT\_POSITIVE

JSON Schema already rejects most invalid values, but domain validation must retain this safeguard.

---

## **14\. Average Price Plausibility**

When high, low, and average are available:

low \<= average \<= high

A small tick-size tolerance may be applied.

Error code:

MARKET\_AVERAGE\_OUTSIDE\_DAILY\_RANGE

When only average and last are available, no hard range validation is performed.

---

## **15\. Bid and Offer Rules**

When both are available:

best\_offer \>= best\_bid

Expected spread:

spread \= best\_offer \- best\_bid

Expected spread percentage:

spread\_percentage \=  
(spread / best\_offer) × 100

`best_offer` is used as the denominator because it represents the immediate purchase price.

Error codes:

MARKET\_OFFER\_BELOW\_BID  
MARKET\_SPREAD\_MISMATCH  
MARKET\_SPREAD\_PERCENTAGE\_MISMATCH

If bid equals offer, spread may be zero.

---

## **16\. Market Change Rules**

Reference market price:

reference\_price \=  
close, when close is available;  
otherwise last.

Expected nominal change:

change \= reference\_price \- previous\_close

Expected change percentage:

change\_percentage \=  
((reference\_price \- previous\_close) / previous\_close) × 100

Error codes:

MARKET\_CHANGE\_MISMATCH  
MARKET\_CHANGE\_PERCENTAGE\_MISMATCH  
MARKET\_PREVIOUS\_CLOSE\_INVALID

If previous close is unavailable, change fields may remain `null`.

---

## **17\. Volume and Transaction Value**

Available values must be nonnegative.

When volume is zero:

* transaction value should normally be zero or null;  
* price fields may still exist for pre-market or suspended states;  
* the market limitation should explain the condition when relevant.

Error codes:

MARKET\_VOLUME\_NEGATIVE  
MARKET\_TRANSACTION\_VALUE\_NEGATIVE  
MARKET\_ZERO\_VOLUME\_WITH\_POSITIVE\_TRANSACTION\_VALUE

The last condition may be configured as a warning for external data-source anomalies.

---

## **18\. Trading Date and Timestamp**

The calendar date represented by `market_timestamp` in the market timezone should match `trading_date`.

Error code:

MARKET\_TIMESTAMP\_DATE\_MISMATCH

Allowed exception:

* post-market processing shortly after midnight;  
* explicitly configured overnight market sessions.

The market calendar module should determine the correct trading session where available.

---

## **19\. Update Period Consistency**

The top-level analysis `update_period` must match:

market\_snapshot.update\_period

Error code:

ANALYSIS\_MARKET\_UPDATE\_PERIOD\_MISMATCH

The actual time window should also be checked where market calendars are configured.

Potential warning:

UPDATE\_PERIOD\_TIME\_WINDOW\_UNUSUAL

---

# **Part II — Position and Trade State Rules**

## **20\. Canonical Source Hierarchy**

When sources conflict, use this precedence:

1. user-confirmed action records;  
2. canonical `trade_state`;  
3. backend-calculated values;  
4. accepted analysis payload;  
5. context summary;  
6. new AI provider output.

The lower source must never overwrite a higher source automatically.

Error code:

CANONICAL\_SOURCE\_CONFLICT

---

## **21\. Position Existence Rules**

When `position_exists = false`:

position\_status \= NOT\_OPENED  
entry\_price \= null  
entry\_timestamp \= null  
original\_quantity \= null  
remaining\_quantity \= null  
average\_exit\_price \= null

There must be no realized or unrealized P/L.

Error code:

NON\_POSITION\_HAS\_POSITION\_VALUES

---

## **22\. Open Position Rules**

When `position_status = OPEN`:

position\_exists \= true  
entry\_price \> 0  
original\_quantity \> 0  
remaining\_quantity \> 0  
remaining\_quantity \= original\_quantity  
average\_exit\_price \= null

The equality between original and remaining quantity applies when no partial exit has occurred.

Error codes:

OPEN\_POSITION\_INVALID\_ENTRY  
OPEN\_POSITION\_INVALID\_ORIGINAL\_QUANTITY  
OPEN\_POSITION\_INVALID\_REMAINING\_QUANTITY  
OPEN\_POSITION\_HAS\_AVERAGE\_EXIT  
OPEN\_POSITION\_QUANTITY\_MISMATCH

---

## **23\. Partially Closed Position Rules**

When `position_status = PARTIALLY_CLOSED`:

position\_exists \= true  
original\_quantity \> 0  
remaining\_quantity \> 0  
remaining\_quantity \< original\_quantity  
average\_exit\_price \> 0  
realized\_profit\_loss \!= null

Error codes:

PARTIAL\_POSITION\_INVALID\_QUANTITY  
PARTIAL\_POSITION\_REMAINING\_NOT\_REDUCED  
PARTIAL\_POSITION\_AVERAGE\_EXIT\_MISSING  
PARTIAL\_POSITION\_REALIZED\_RESULT\_MISSING

---

## **24\. Closed Position Rules**

When `position_status = CLOSED`:

position\_exists \= true  
remaining\_quantity \= 0  
average\_exit\_price \> 0  
active\_stop\_loss \= null  
active\_target \= null  
unrealized\_profit\_loss \= null  
unrealized\_return\_percentage \= null

Error codes:

CLOSED\_POSITION\_HAS\_REMAINING\_QUANTITY  
CLOSED\_POSITION\_AVERAGE\_EXIT\_MISSING  
CLOSED\_POSITION\_HAS\_ACTIVE\_STOP  
CLOSED\_POSITION\_HAS\_ACTIVE\_TARGET  
CLOSED\_POSITION\_HAS\_UNREALIZED\_RESULT

---

## **25\. Quantity Conservation**

At all times:

0 \<= remaining\_quantity \<= original\_quantity

Across confirmed exits:

original\_quantity \=  
sum(all exited quantities) \+ remaining\_quantity

Error codes:

POSITION\_REMAINING\_EXCEEDS\_ORIGINAL  
POSITION\_QUANTITY\_CONSERVATION\_FAILED

---

## **26\. Entry Price Consistency**

The following values must equal canonical entry price:

* `position_assessment.entry_price`;  
* `remaining_position_assessment.entry_price`;  
* `trade_result.entry_price`;  
* `context_summary.current_position.entry_price`.

Error code:

POSITION\_ENTRY\_PRICE\_MISMATCH

The AI may discuss an alternative entry only inside a clearly marked proposed-entry field before a position exists.

---

## **27\. Remaining Quantity Consistency**

The following must equal canonical remaining quantity:

* Open Position update;  
* Partial Exit review;  
* Context Summary;  
* final exit confirmation input before close.

Error code:

POSITION\_REMAINING\_QUANTITY\_MISMATCH

---

## **28\. Active Stop Consistency**

An active stop shown in analysis must equal canonical Trade State.

A different AI-generated value must appear only as:

proposed\_stop\_loss

Error codes:

ACTIVE\_STOP\_LOSS\_MISMATCH  
PROPOSED\_STOP\_PRESENTED\_AS\_ACTIVE

---

## **29\. Active Target Consistency**

An active target shown in analysis must equal canonical Trade State.

A different value must appear only as a proposal.

Error codes:

ACTIVE\_TARGET\_MISMATCH  
PROPOSED\_TARGET\_PRESENTED\_AS\_ACTIVE

---

# **Part III — Position Calculations**

## **30\. Unrealized Profit and Loss**

For a long position:

unrealized\_profit\_loss \=  
(current\_price \- entry\_price) × remaining\_quantity

This formula excludes fees and taxes unless a future schema explicitly includes them.

Error code:

UNREALIZED\_PROFIT\_LOSS\_MISMATCH

---

## **31\. Unrealized Return Percentage**

For a long position:

unrealized\_return\_percentage \=  
((current\_price \- entry\_price) / entry\_price) × 100

This percentage is price return, independent of quantity.

Error code:

UNREALIZED\_RETURN\_PERCENTAGE\_MISMATCH

---

## **32\. Distance to Stop**

Standard display calculation:

distance\_to\_stop\_percentage \=  
((current\_price \- stop\_loss) / current\_price) × 100

Interpretation:

* positive: price is above stop;  
* zero: price equals stop;  
* negative: price has fallen below stop.

Error code:

DISTANCE\_TO\_STOP\_MISMATCH

---

## **33\. Distance to Target**

Standard display calculation:

distance\_to\_target\_percentage \=  
((target\_price \- current\_price) / current\_price) × 100

Interpretation:

* positive: target is above current price;  
* zero: target equals current price;  
* negative: current price is above target.

Error code:

DISTANCE\_TO\_TARGET\_MISMATCH

A negative value is allowed when price has passed the target but execution has not been confirmed.

---

## **34\. Holding Duration**

Calendar duration:

holding\_duration\_calendar\_days \=  
calendar date difference between entry and exit/current timestamp

Trading duration:

holding\_duration\_trading\_days \=  
number of relevant market trading dates touched by the position

The backend market-calendar service is authoritative.

Error codes:

HOLDING\_DURATION\_MISMATCH  
HOLDING\_DURATION\_NEGATIVE

---

# **Part IV — Entry Plan Rules**

## **35\. Exact Entry**

When entry type is `EXACT_PRICE`:

entry\_price \!= null  
entry\_zone\_low \= null  
entry\_zone\_high \= null

Error code:

EXACT\_ENTRY\_STRUCTURE\_INVALID

---

## **36\. Entry Zone**

When entry type is `PRICE_ZONE`:

entry\_price \= null  
entry\_zone\_low \> 0  
entry\_zone\_high \> 0  
entry\_zone\_low \<= entry\_zone\_high

Error codes:

ENTRY\_ZONE\_STRUCTURE\_INVALID  
ENTRY\_ZONE\_LOW\_ABOVE\_HIGH

---

## **37\. Wait and No-Entry Plans**

When entry type is `WAIT` or `NO_ENTRY`:

entry\_price \= null  
entry\_zone\_low \= null  
entry\_zone\_high \= null

Error code:

NON\_ENTRY\_PLAN\_HAS\_ENTRY\_PRICE

A reference level may still exist under `price_levels`, but it must not be presented as an actionable current entry.

---

## **38\. Entry Confirmation**

When `confirmation_required = true`:

confirmation\_condition must not be null or empty

Error code:

ENTRY\_CONFIRMATION\_CONDITION\_MISSING

Entry confirmation from AI does not equal user execution confirmation.

---

## **39\. Maximum Acceptable Entry**

For an exact entry:

maximum\_acceptable\_entry \>= entry\_price

For an entry zone:

maximum\_acceptable\_entry \>= entry\_zone\_high

Error code:

MAXIMUM\_ENTRY\_BELOW\_PROPOSED\_ENTRY

---

## **40\. Chase Risk**

For a not-yet-opened long position:

distance\_above\_maximum\_entry \=  
((current\_price \- maximum\_acceptable\_entry)  
 / maximum\_acceptable\_entry) × 100

Default interpretation:

current\_price \<= maximum\_acceptable\_entry:  
    price\_already\_extended \= false

current\_price \> maximum\_acceptable\_entry:  
    price\_already\_extended \= true  
    chase\_risk must be HIGH or VERY\_HIGH

Error codes:

PRICE\_EXTENSION\_FLAG\_MISMATCH  
CHASE\_RISK\_INCONSISTENT

Market-specific configuration may add a tolerance of one price tick.

---

## **41\. Entry Cancellation Condition**

Every initial or watching entry plan must include a cancellation condition.

Error code:

ENTRY\_CANCEL\_CONDITION\_MISSING

The condition should describe either:

* a price invalidation;  
* an orderbook deterioration;  
* a chart breakdown;  
* expiration of the setup;  
* a material risk change.

Narrative quality is evaluated lightly and should not require a specific writing style.

---

# **Part V — Stop-Loss Rules**

## **42\. Initial Stop-Loss Position**

For a long setup before entry:

stop\_loss\_price \< reference\_entry\_price

Error code:

INITIAL\_STOP\_NOT\_BELOW\_ENTRY

Exception:

* no stop is proposed because entry is not recommended.

---

## **43\. Active Stop-Loss Position**

For an active long position:

active\_stop\_loss \< current\_price

unless the stop has been triggered.

Error code:

ACTIVE\_STOP\_NOT\_BELOW\_CURRENT\_PRICE

When current price is equal to or below active stop, the analysis must identify:

triggered \= true

subject to the trigger policy in the next section.

---

## **44\. Stop Trigger Policy**

Default version 1 trigger rule:

stop\_triggered \=  
current\_reference\_price \<= active\_stop\_loss

The current reference price is:

last during market hours;  
close after market close.

A screenshot showing an intraday low below stop does not prove execution unless the product rule explicitly uses low-price touch as the trigger.

Recommended configuration:

stop\_trigger\_mode: CURRENT\_PRICE\_OR\_USER\_CONFIRMATION

Alternative future modes:

INTRADAY\_TOUCH  
CLOSE\_BELOW  
USER\_CONFIRMATION\_ONLY

Error codes:

STOP\_TRIGGER\_FLAG\_MISMATCH  
STOP\_TRIGGER\_POLICY\_UNSUPPORTED

---

## **45\. Initial Risk Percentage**

For a long entry:

initial\_risk\_percentage \=  
((entry\_price \- stop\_loss\_price) / entry\_price) × 100

Error code:

INITIAL\_RISK\_PERCENTAGE\_MISMATCH

---

## **46\. Maximum Risk Rule**

Default user risk guideline:

maximum price risk per trade \= 5%

When:

initial\_risk\_percentage \> 5%

the system should produce:

INITIAL\_RISK\_EXCEEDS\_LIMIT

Default severity:

ERROR

This may be made configurable per user or trading profile later.

---

## **47\. Protective Stop After Profit**

After price has moved above entry, a proposed protective stop may be:

* below entry;  
* equal to entry;  
* above entry.

The proposed stop must still normally remain below current price.

Valid examples:

entry \= 2800  
current price \= 2920  
proposed stop \= 2800

entry \= 2800  
current price \= 2920  
proposed stop \= 2880

Invalid:

proposed stop \= 2950

unless stop-triggered handling is explicitly intended.

Error code:

PROTECTIVE\_STOP\_NOT\_BELOW\_CURRENT\_PRICE

---

## **48\. Stop and Target Crossing**

For an active long position:

active\_stop\_loss \< active\_target

Error code:

STOP\_NOT\_BELOW\_TARGET

For a proposed stop and proposed target, the same rule applies.

---

# **Part VI — Target and Reward Rules**

## **49\. Initial Target Position**

For a long setup:

target\_price \> reference\_entry\_price

Error code:

INITIAL\_TARGET\_NOT\_ABOVE\_ENTRY

---

## **50\. Reward Percentage**

reward\_percentage \=  
((target\_price \- entry\_price) / entry\_price) × 100

Error code:

REWARD\_PERCENTAGE\_MISMATCH

---

## **51\. Risk-Reward Ratio**

risk\_per\_share \= entry\_price \- stop\_loss\_price  
reward\_per\_share \= target\_price \- entry\_price  
risk\_reward\_ratio \= reward\_per\_share / risk\_per\_share

Required conditions:

risk\_per\_share \> 0  
reward\_per\_share \> 0

Error codes:

RISK\_REWARD\_INVALID\_RISK  
RISK\_REWARD\_INVALID\_REWARD  
RISK\_REWARD\_RATIO\_MISMATCH

---

## **52\. Weak Risk-Reward Warning**

Recommended default:

risk\_reward\_ratio \< 1.0

produces:

RISK\_REWARD\_BELOW\_ONE

Default severity:

WARNING

It does not automatically invalidate a trade because probability and execution context may differ.

---

## **53\. Target Reached Status**

A target may be described as reached when at least one of the following is true:

* current price is equal to or above target;  
* market high is equal to or above target;  
* a user-confirmed exit occurred at or above target.

However:

* market high reaching the target does not prove the user sold;  
* canonical position must remain unchanged until user confirmation.

Error code:

TARGET\_REACHED\_WITHOUT\_PRICE\_EVIDENCE

Warning code:

TARGET\_REACHED\_BUT\_EXIT\_NOT\_CONFIRMED

---

## **54\. Target Probability Reference**

Every target probability must correspond to a known target.

Priority:

1. active target;  
2. proposed target explicitly identified in the same section;  
3. original target in pre-entry analysis.

Error code:

TARGET\_PROBABILITY\_WITHOUT\_TARGET

A probability must not silently switch from active target to proposed target.

---

# **Part VII — Probability and Confidence Rules**

## **55\. Probability Range**

All probabilities must be integers from 0 through 100\.

Schema validation enforces this, while domain validation checks semantic consistency.

---

## **56\. Probabilities Do Not Need to Sum to 100**

These values describe different events:

* bullish probability;  
* target probability;  
* downside probability;  
* entry probability;  
* full-exit probability.

They must not be treated as mutually exclusive outcomes.

No sum-to-100 rule applies.

---

## **57\. Basic Probability Consistency**

Recommended warning rules:

target\_probability \> bullish\_probability \+ 20

may indicate inconsistency.

bias \= STRONGLY\_BULLISH  
bullish\_probability \< 55

may indicate inconsistency.

bias \= STRONGLY\_BEARISH  
downside\_probability \< 55

may indicate inconsistency.

Warning codes:

TARGET\_PROBABILITY\_EXCEEDS\_BULLISH\_CONTEXT  
BIAS\_PROBABILITY\_INCONSISTENT

These are warnings because model interpretations may differ.

---

## **58\. Confidence and Evidence Quality**

Confidence should be limited when critical evidence is missing.

Recommended caps:

No orderbook and no current chart:  
    maximum recommended confidence \= 55

Orderbook unavailable:  
    maximum recommended confidence \= 70

Both charts unavailable:  
    maximum recommended confidence \= 65

Context quality insufficient:  
    analysis must not be accepted

Warnings:

CONFIDENCE\_HIGH\_WITH\_LIMITED\_EVIDENCE  
CONFIDENCE\_HIGH\_WITH\_STALE\_CONTEXT

The backend may either:

* reject values above configured caps; or  
* preserve the value and add a warning.

Default version 1 behavior: warning.

---

# **Part VIII — Thesis Rules**

## **59\. Thesis Status Consistency**

When thesis status is `INVALIDATED`:

remains\_valid \= false  
invalidation\_triggered \= true

Error code:

INVALIDATED\_THESIS\_FLAG\_MISMATCH

---

## **60\. Valid Thesis Status**

When `remains_valid = true`, allowed statuses are:

STRENGTHENING  
INTACT  
INTACT\_BUT\_WEAKENING  
UNDER\_REVIEW

Error code:

VALID\_THESIS\_STATUS\_MISMATCH

---

## **61\. Completed Thesis**

`COMPLETED` is normally allowed when:

* target scenario has materially completed; or  
* the position is closed and final thesis review confirms completion.

It should not normally be used for a routine open-position update before the thesis objective has occurred.

Warning code:

THESIS\_COMPLETED\_PREMATURELY

---

## **62\. Thesis Invalidation Price**

When invalidation price is available, it should be consistent with:

* the thesis narrative;  
* active stop or a nearby structural level;  
* current long-position logic.

The invalidation level may differ from active stop, but the difference should be explained.

Warning code:

THESIS\_INVALIDATION\_DIFFERS\_FROM\_STOP

No automatic equality rule applies.

---

# **Part IX — Analysis-Type Rules**

## **63\. Initial Analysis**

Required canonical conditions:

position\_exists \= false  
session status is READY\_FOR\_ANALYSIS or ANALYZING

It must not contain:

* realized P/L;  
* active position quantity;  
* confirmed entry;  
* confirmed active stop;  
* confirmed active target.

Error codes:

INITIAL\_ANALYSIS\_POSITION\_ALREADY\_EXISTS  
INITIAL\_ANALYSIS\_HAS\_CONFIRMED\_TRADE\_VALUES

---

## **64\. Watching Update**

Required canonical conditions:

position\_exists \= false  
session status \= WATCHING

Entry, stop, and target remain proposals.

Error codes:

WATCHING\_UPDATE\_POSITION\_EXISTS  
WATCHING\_UPDATE\_HAS\_ACTIVE\_POSITION\_METRICS

---

## **65\. Open Position Update**

Required canonical conditions:

position\_status \= OPEN  
session status \= OPEN\_POSITION  
remaining\_quantity \> 0

Error codes:

OPEN\_UPDATE\_WITHOUT\_OPEN\_POSITION  
OPEN\_UPDATE\_SESSION\_STATUS\_MISMATCH

---

## **66\. Partial Exit Review**

Required canonical conditions:

position\_status \= PARTIALLY\_CLOSED  
session status \= PARTIALLY\_CLOSED  
remaining\_quantity \> 0  
at least one confirmed partial exit exists

Error codes:

PARTIAL\_REVIEW\_WITHOUT\_PARTIAL\_POSITION  
PARTIAL\_REVIEW\_CONFIRMATION\_MISSING

---

## **67\. Closing Analysis**

Required canonical conditions:

position\_status \= CLOSED  
remaining\_quantity \= 0  
session status is a supported closed status  
full exit confirmation exists

Error codes:

CLOSING\_ANALYSIS\_POSITION\_NOT\_CLOSED  
CLOSING\_ANALYSIS\_REMAINING\_QUANTITY\_NONZERO  
CLOSING\_ANALYSIS\_CONFIRMATION\_MISSING

---

# **Part X — Partial Exit Rules**

## **68\. Partial Exit Quantity**

Before partial exit:

previous\_remaining\_quantity \> 0

After partial exit:

exited\_quantity \> 0  
new\_remaining\_quantity \> 0  
exited\_quantity \< previous\_remaining\_quantity

Conservation rule:

exited\_quantity \+ new\_remaining\_quantity  
\= previous\_remaining\_quantity

Error codes:

PARTIAL\_EXIT\_QUANTITY\_INVALID  
PARTIAL\_EXIT\_CLOSES\_FULL\_POSITION  
PARTIAL\_EXIT\_QUANTITY\_MISMATCH

If remaining quantity becomes zero, the action is a full exit, not a partial exit.

---

## **69\. Partial Exit Realized P/L**

For a single entry price:

realized\_profit\_loss\_for\_exit \=  
(exit\_price \- entry\_price) × exited\_quantity

Cumulative realized P/L:

cumulative\_realized\_profit\_loss \=  
sum((exit\_price\_i \- entry\_price) × exited\_quantity\_i)

Error code:

PARTIAL\_EXIT\_REALIZED\_PROFIT\_LOSS\_MISMATCH

---

## **70\. Partial Exit Return Percentage**

Price return for the exit:

realized\_return\_percentage \=  
((exit\_price \- entry\_price) / entry\_price) × 100

This is not weighted by exited quantity.

Error code:

PARTIAL\_EXIT\_RETURN\_PERCENTAGE\_MISMATCH

---

## **71\. Capital Recovered Percentage**

Default gross capital-recovered formula:

capital\_recovered\_percentage \=  
((exit\_price × exited\_quantity)  
 / (entry\_price × original\_quantity)) × 100

Error code:

CAPITAL\_RECOVERED\_PERCENTAGE\_MISMATCH

This metric represents recovered gross sale value relative to original gross capital.

It is not the same as percentage of quantity sold.

---

## **72\. Average Exit Price**

Across partial exits:

average\_exit\_price \=  
sum(exit\_price\_i × exited\_quantity\_i)  
/  
sum(exited\_quantity\_i)

Error code:

AVERAGE\_EXIT\_PRICE\_MISMATCH

Fees and taxes do not change average execution price.

---

## **73\. Remaining Unrealized P/L**

remaining\_unrealized\_profit\_loss \=  
(current\_price \- entry\_price) × remaining\_quantity

Error code:

REMAINING\_UNREALIZED\_PROFIT\_LOSS\_MISMATCH

---

## **74\. Total Trade P/L During Partial State**

total\_trade\_profit\_loss \=  
cumulative\_realized\_profit\_loss  
\+ remaining\_unrealized\_profit\_loss

Error code:

PARTIAL\_STATE\_TOTAL\_PROFIT\_LOSS\_MISMATCH

---

## **75\. Total Trade Return During Partial State**

Default denominator:

original\_cost \=  
entry\_price × original\_quantity

Formula:

total\_trade\_return\_percentage \=  
(total\_trade\_profit\_loss / original\_cost) × 100

Error code:

PARTIAL\_STATE\_TOTAL\_RETURN\_MISMATCH

---

# **Part XI — Full Exit and Closing Rules**

## **76\. Final Exit Quantity**

final\_exit\_quantity \=  
remaining\_quantity immediately before final exit

Error code:

FINAL\_EXIT\_QUANTITY\_MISMATCH

---

## **77\. Final Weighted Average Exit**

Across all partial and final exits:

average\_exit\_price \=  
sum(exit\_price\_i × exited\_quantity\_i)  
/  
original\_quantity

This requires:

sum(exited\_quantity\_i) \= original\_quantity

Error codes:

FINAL\_AVERAGE\_EXIT\_MISMATCH  
FINAL\_EXIT\_QUANTITY\_CONSERVATION\_FAILED

---

## **78\. Gross Profit and Loss**

gross\_profit\_loss \=  
(average\_exit\_price \- entry\_price) × original\_quantity

Equivalent event-based formula:

gross\_profit\_loss \=  
sum((exit\_price\_i \- entry\_price) × exited\_quantity\_i)

Both calculations must match.

Error code:

FINAL\_GROSS\_PROFIT\_LOSS\_MISMATCH

---

## **79\. Gross Return Percentage**

gross\_return\_percentage \=  
((average\_exit\_price \- entry\_price) / entry\_price) × 100

Error code:

FINAL\_GROSS\_RETURN\_MISMATCH

---

## **80\. Net Profit and Loss**

When fees and taxes are both known:

net\_profit\_loss \=  
gross\_profit\_loss \- fees \- taxes

Error code:

FINAL\_NET\_PROFIT\_LOSS\_MISMATCH

When either fees or taxes are unknown:

net\_profit\_loss \= null  
net\_return\_percentage \= null

unless the application explicitly declares that missing components are zero.

Error code:

NET\_RESULT\_PRESENT\_WITH\_INCOMPLETE\_COSTS

---

## **81\. Net Return Percentage**

When net P/L is available:

original\_cost \=  
entry\_price × original\_quantity

net\_return\_percentage \=  
(net\_profit\_loss / original\_cost) × 100

Error code:

FINAL\_NET\_RETURN\_MISMATCH

---

## **82\. Outcome Classification**

Default configurable thresholds:

large\_profit\_min\_percentage: 10.0  
profit\_min\_percentage: 2.0  
small\_profit\_min\_percentage: 0.25  
break\_even\_min\_percentage: \-0.25  
break\_even\_max\_percentage: 0.25  
small\_loss\_min\_percentage: \-2.0  
large\_loss\_max\_percentage: \-5.0

Recommended classification:

return \>= 10.0:  
    LARGE\_PROFIT

2.0 \<= return \< 10.0:  
    PROFIT

0.25 \< return \< 2.0:  
    SMALL\_PROFIT

\-0.25 \<= return \<= 0.25:  
    BREAK\_EVEN

\-2.0 \< return \< \-0.25:  
    SMALL\_LOSS

\-5.0 \< return \<= \-2.0:  
    LOSS

return \<= \-5.0:  
    LARGE\_LOSS

Error code:

TRADE\_OUTCOME\_CLASSIFICATION\_MISMATCH

Use gross return when net return is unavailable.

Use net return when fully calculated and configured as the reporting standard.

---

## **83\. Closing Reason and Session Status**

Required mapping:

TAKE\_PROFIT \-\> CLOSED\_TAKE\_PROFIT  
STOP\_LOSS \-\> CLOSED\_STOP\_LOSS  
MANUAL\_EXIT \-\> CLOSED\_MANUAL  
THESIS\_INVALIDATED \-\> CLOSED\_MANUAL  
RISK\_REDUCTION \-\> CLOSED\_MANUAL

`SESSION_CANCELLED` applies only where no live position remained.

Error code:

CLOSING\_REASON\_SESSION\_STATUS\_MISMATCH

---

## **84\. Maximum Unrealized Profit and Loss**

These metrics must come from stored accepted market snapshots or trusted price history.

Maximum unrealized profit:

max(  
    ((observed\_price \- entry\_price) / entry\_price) × 100  
)

Maximum unrealized loss:

min(  
    ((observed\_price \- entry\_price) / entry\_price) × 100  
)

If intraday high and low are used, the calculation source must be documented.

If history is incomplete, values may be `null`.

Warning code:

MAX\_UNREALIZED\_RESULT\_BASED\_ON\_INCOMPLETE\_HISTORY

---

# **Part XII — Timeline and Timestamp Rules**

## **85\. Basic Timestamp Order**

Required ordering:

session\_started\_at  
\<= initial analysis timestamp  
\<= position\_opened\_at  
\<= partial exits  
\<= final exit  
\<= closing analysis timestamp

Not every stage must exist, but existing stages must follow chronological order.

Error code:

TRADE\_TIMELINE\_OUT\_OF\_ORDER

---

## **86\. Analysis Timestamp**

An analysis timestamp must not be earlier than:

* its evidence upload cutoff where relevant;  
* the latest user action included;  
* position entry for Open Position analysis;  
* partial exit confirmation for Partial Exit Review;  
* final exit confirmation for Closing Analysis.

Error codes:

ANALYSIS\_BEFORE\_SOURCE\_EVENT  
OPEN\_ANALYSIS\_BEFORE\_ENTRY  
PARTIAL\_REVIEW\_BEFORE\_PARTIAL\_EXIT  
CLOSING\_ANALYSIS\_BEFORE\_FINAL\_EXIT

---

## **87\. Future Timestamp**

Timestamps may not be materially in the future relative to backend time.

Allowed clock skew:

60 seconds

Error code:

TIMESTAMP\_IN\_FUTURE

---

## **88\. Duplicate Timeline Events**

Events with the same canonical action ID must not be duplicated.

Error code:

DUPLICATE\_TIMELINE\_EVENT

Separate analytical observations at the same timestamp may exist if they have different event IDs.

---

# **Part XIII — Evidence Rules**

## **89\. Evidence Ticker and Session**

Every evidence item must match the target:

* session ID;  
* ticker.

Error codes:

EVIDENCE\_SESSION\_MISMATCH  
EVIDENCE\_TICKER\_MISMATCH

---

## **90\. Evidence Timestamp**

An orderbook screenshot must have a market timestamp.

The market timestamp must not be later than upload time beyond allowed clock skew.

Error codes:

ORDERBOOK\_MARKET\_TIMESTAMP\_MISSING  
EVIDENCE\_MARKET\_TIMESTAMP\_AFTER\_UPLOAD

Exception:

* device clock or imported historical evidence, when explicitly marked.

---

## **91\. Evidence Staleness**

Recommended orderbook staleness thresholds:

orderbook\_warning\_minutes: 15  
orderbook\_error\_minutes: 60

For a live update:

age \<= 15 minutes:  
    usable without staleness warning

15 \< age \<= 60 minutes:  
    warning

age \> 60 minutes:  
    normally reject as current orderbook evidence

Codes:

ORDERBOOK\_EVIDENCE\_STALE  
ORDERBOOK\_EVIDENCE\_TOO\_OLD

Historical comparison may still use older evidence, but it must not be labeled current.

---

## **92\. Chart Staleness**

Charts can remain useful longer than orderbooks.

Recommended default:

chart\_warning\_trading\_days: 5  
chart\_error\_trading\_days: 20

Codes:

CHART\_CONTEXT\_STALE  
CHART\_CONTEXT\_TOO\_OLD

Old charts may still be retained as historical context, but current analysis must state the limitation.

---

## **93\. Extracted Fact Consistency**

When extracted facts contain fields also present in market snapshot:

* best bid;  
* best offer;  
* open;  
* high;  
* low;  
* last;  
* close;  
* average;

they should match within price tolerance.

Error code:

EXTRACTED\_FACT\_MARKET\_VALUE\_MISMATCH

If multiple evidence sources disagree, the conflict must be flagged rather than silently merged.

Code:

EVIDENCE\_VALUE\_CONFLICT

---

## **94\. Unreadable Evidence**

Unreadable evidence must not produce usable extracted facts.

Error code:

UNREADABLE\_EVIDENCE\_HAS\_FACTS

The analysis may still mention that the evidence could not be interpreted.

---

# **Part XIV — Context Summary Rules**

## **95\. Context is Non-Canonical**

Context Summary must not be used to overwrite Trade State.

Error code:

CONTEXT\_ATTEMPTED\_CANONICAL\_OVERRIDE

When context differs from Trade State, context must be rebuilt.

---

## **96\. Context Canonical Facts**

These must match Trade State:

* session status;  
* position status;  
* entry;  
* original quantity;  
* remaining quantity;  
* average exit;  
* active stop;  
* active target;  
* realized P/L;  
* confirmed action history.

Error code:

CONTEXT\_CANONICAL\_FACT\_MISMATCH

---

## **97\. Context Source Cutoff**

Every included event must satisfy:

event timestamp \<= source\_cutoff\_timestamp

Error code:

CONTEXT\_EVENT\_AFTER\_CUTOFF

---

## **98\. Context Generated Time**

generated\_at \>= source\_cutoff\_timestamp

Error code:

CONTEXT\_GENERATED\_BEFORE\_CUTOFF

---

## **99\. Context Staleness**

Context is stale when any newer accepted item exists after cutoff:

* accepted analysis;  
* user-confirmed action;  
* active evidence replacement;  
* Trade State update.

Error code or warning:

CONTEXT\_STALE

Default severity:

ERROR before starting a new analysis  
WARNING when displaying an old historical context

---

## **100\. Pending Proposals**

A proposed stop, target, or entry must remain in unresolved items until:

* user confirms it;  
* a newer analysis withdraws it;  
* the session state makes it irrelevant.

Error code:

CONTEXT\_PENDING\_PROPOSAL\_LOST

A pending proposal must not appear in an active canonical field.

Error code:

CONTEXT\_PROPOSAL\_PROMOTED\_WITHOUT\_CONFIRMATION

---

## **101\. Important History Compression**

Context history should retain only material events.

Recommended maximum:

30 events

When more events exist:

* preserve all user-confirmed trade actions;  
* preserve original thesis;  
* preserve latest thesis status changes;  
* preserve stop and target changes;  
* preserve entries and exits;  
* compress repeated minor analytical changes.

Warning:

CONTEXT\_HISTORY\_COMPRESSED

---

# **Part XV — Lifecycle Rules**

## **102\. Allowed Status Transitions**

Recommended primary transitions:

DRAFT  
\-\> READY\_FOR\_ANALYSIS

READY\_FOR\_ANALYSIS  
\-\> ANALYZING

ANALYZING  
\-\> WATCHING

WATCHING  
\-\> ANALYZING  
\-\> WATCHING

WATCHING  
\-\> OPEN\_POSITION

OPEN\_POSITION  
\-\> ANALYZING  
\-\> OPEN\_POSITION

OPEN\_POSITION  
\-\> PARTIALLY\_CLOSED

PARTIALLY\_CLOSED  
\-\> ANALYZING  
\-\> PARTIALLY\_CLOSED

OPEN\_POSITION  
\-\> CLOSED\_TAKE\_PROFIT  
\-\> CLOSED\_STOP\_LOSS  
\-\> CLOSED\_MANUAL

PARTIALLY\_CLOSED  
\-\> CLOSED\_TAKE\_PROFIT  
\-\> CLOSED\_STOP\_LOSS  
\-\> CLOSED\_MANUAL

Any non-archived terminal state  
\-\> ARCHIVED

`ANALYZING` is a temporary processing status.

---

## **103\. Invalid Transitions**

Examples:

DRAFT \-\> OPEN\_POSITION  
WATCHING \-\> PARTIALLY\_CLOSED  
CLOSED\_\* \-\> OPEN\_POSITION  
ARCHIVED \-\> OPEN\_POSITION

Error code:

INVALID\_SESSION\_STATUS\_TRANSITION

Reopening an archived or closed session should create a new Trade Session rather than changing the old session back to active.

---

## **104\. User-Confirmed Transition Rules**

The following require explicit user confirmation:

WATCHING \-\> OPEN\_POSITION  
OPEN\_POSITION \-\> PARTIALLY\_CLOSED  
OPEN\_POSITION \-\> CLOSED\_\*  
PARTIALLY\_CLOSED \-\> CLOSED\_\*  
any active state \-\> CANCELLED when applicable

Error code:

LIFECYCLE\_TRANSITION\_WITHOUT\_USER\_CONFIRMATION

---

## **105\. AI Analysis Cannot Change Lifecycle Directly**

AI may recommend:

* enter;  
* hold;  
* reduce risk;  
* partial exit;  
* full exit;  
* cancel setup.

It may not directly perform the lifecycle transition.

Error code:

AI\_ATTEMPTED\_AUTOMATIC\_STATE\_TRANSITION

---

# **Part XVI — User Confirmation Rules**

## **106\. Confirmed Action Requirement**

Canonical fields may change only when supported by a compatible user-confirmed action.

Examples:

entry and quantity:  
    POSITION\_OPENED

active stop:  
    STOP\_LOSS\_CONFIRMED  
    STOP\_LOSS\_CHANGED

active target:  
    TARGET\_CONFIRMED  
    TARGET\_CHANGED

remaining quantity:  
    PARTIAL\_EXIT\_CONFIRMED  
    FULL\_EXIT\_CONFIRMED

Error code:

CANONICAL\_CHANGE\_WITHOUT\_CONFIRMATION

---

## **107\. Action Timestamp**

A confirmed action timestamp must not predate the analysis or event that motivated it when a relationship is declared.

It may occur independently if the user acted outside the latest AI recommendation.

Error code:

CONFIRMED\_ACTION\_TIMESTAMP\_INVALID

The system must not reject a valid user action merely because it differs from AI advice.

---

## **108\. User Decision Overrides AI Recommendation**

A valid user-confirmed action remains canonical even when it contradicts AI advice.

The system may:

* record the deviation;  
* warn about risk;  
* analyze the new state.

It must not silently restore the AI-proposed value.

---

# **Part XVII — Domain Validator Registry**

## **109\. Validator Mapping**

Recommended registry:

DOMAIN\_VALIDATORS \= {  
    "market\_snapshot": \[  
        validate\_market\_availability,  
        validate\_ohlc,  
        validate\_market\_change,  
        validate\_bid\_offer,  
        validate\_market\_timestamp,  
    \],  
    "trade\_state": \[  
        validate\_position\_state,  
        validate\_quantity\_conservation,  
        validate\_confirmed\_actions,  
        validate\_trade\_state\_timestamps,  
    \],  
    "initial\_analysis": \[  
        validate\_initial\_analysis\_state,  
        validate\_market\_snapshot,  
        validate\_entry\_plan,  
        validate\_initial\_stop,  
        validate\_initial\_target,  
        validate\_risk\_reward,  
        validate\_evidence\_consistency,  
    \],  
    "watching\_update": \[  
        validate\_watching\_state,  
        validate\_market\_snapshot,  
        validate\_entry\_assessment,  
        validate\_setup\_assessment,  
        validate\_evidence\_consistency,  
    \],  
    "open\_position\_update": \[  
        validate\_open\_position\_state,  
        validate\_market\_snapshot,  
        validate\_position\_calculations,  
        validate\_active\_levels,  
        validate\_target\_assessment,  
        validate\_stop\_assessment,  
        validate\_thesis\_assessment,  
    \],  
    "partial\_exit\_review": \[  
        validate\_partial\_position\_state,  
        validate\_partial\_exit\_confirmation,  
        validate\_partial\_exit\_calculations,  
        validate\_remaining\_position,  
        validate\_active\_levels,  
    \],  
    "closing\_analysis": \[  
        validate\_closed\_position\_state,  
        validate\_final\_exit,  
        validate\_weighted\_average\_exit,  
        validate\_closing\_calculations,  
        validate\_outcome\_classification,  
        validate\_timeline,  
    \],  
    "context\_summary": \[  
        validate\_context\_canonical\_facts,  
        validate\_context\_cutoff,  
        validate\_context\_freshness,  
        validate\_pending\_proposals,  
        validate\_context\_lifecycle,  
    \],  
}

---

# **Part XVIII — Backend-Owned Fields**

## **110\. Deterministic Field Ownership**

The backend must calculate or inject:

* IDs;  
* session ID;  
* ticker;  
* analysis type;  
* schema name;  
* schema version;  
* timestamps;  
* entry price;  
* original quantity;  
* remaining quantity;  
* active stop;  
* active target;  
* realized P/L;  
* unrealized P/L;  
* percentage returns;  
* stop and target distances;  
* risk-reward ratio;  
* average exit price;  
* holding duration;  
* provider and model metadata.

AI output should not be considered authoritative for these fields.

---

## **111\. Backend Normalization**

Recommended flow:

AI interpretive payload  
        |  
        v  
Inject canonical facts  
        |  
        v  
Compute deterministic values  
        |  
        v  
Validate complete payload  
        |  
        v  
Persist validated payload

If AI supplies a conflicting deterministic value, record:

BACKEND\_VALUE\_REPLACED\_AI\_VALUE

Default severity:

INFORMATIONAL

If the conflict changes analytical meaning, also record a state-conflict error and retry the AI interpretation where needed.

---

# **Part XIX — Validation Code Catalogue**

## **112\. Market Codes**

MARKET\_DATA\_UNAVAILABLE\_HAS\_VALUES  
MARKET\_DATA\_UNAVAILABLE\_INVALID\_SOURCE  
MARKET\_DATA\_UNAVAILABLE\_WITHOUT\_LIMITATION  
MARKET\_PRICE\_MISSING  
MARKET\_HIGH\_BELOW\_LOW  
MARKET\_HIGH\_BELOW\_OPEN  
MARKET\_HIGH\_BELOW\_LAST  
MARKET\_HIGH\_BELOW\_CLOSE  
MARKET\_LOW\_ABOVE\_OPEN  
MARKET\_LOW\_ABOVE\_LAST  
MARKET\_LOW\_ABOVE\_CLOSE  
MARKET\_AVERAGE\_OUTSIDE\_DAILY\_RANGE  
MARKET\_OFFER\_BELOW\_BID  
MARKET\_SPREAD\_MISMATCH  
MARKET\_SPREAD\_PERCENTAGE\_MISMATCH  
MARKET\_CHANGE\_MISMATCH  
MARKET\_CHANGE\_PERCENTAGE\_MISMATCH  
MARKET\_TIMESTAMP\_DATE\_MISMATCH  
ANALYSIS\_MARKET\_UPDATE\_PERIOD\_MISMATCH

---

## **113\. Position Codes**

NON\_POSITION\_HAS\_POSITION\_VALUES  
OPEN\_POSITION\_INVALID\_ENTRY  
OPEN\_POSITION\_INVALID\_ORIGINAL\_QUANTITY  
OPEN\_POSITION\_INVALID\_REMAINING\_QUANTITY  
OPEN\_POSITION\_HAS\_AVERAGE\_EXIT  
OPEN\_POSITION\_QUANTITY\_MISMATCH  
PARTIAL\_POSITION\_INVALID\_QUANTITY  
PARTIAL\_POSITION\_REMAINING\_NOT\_REDUCED  
PARTIAL\_POSITION\_AVERAGE\_EXIT\_MISSING  
PARTIAL\_POSITION\_REALIZED\_RESULT\_MISSING  
CLOSED\_POSITION\_HAS\_REMAINING\_QUANTITY  
CLOSED\_POSITION\_AVERAGE\_EXIT\_MISSING  
CLOSED\_POSITION\_HAS\_ACTIVE\_STOP  
CLOSED\_POSITION\_HAS\_ACTIVE\_TARGET  
CLOSED\_POSITION\_HAS\_UNREALIZED\_RESULT  
POSITION\_REMAINING\_EXCEEDS\_ORIGINAL  
POSITION\_QUANTITY\_CONSERVATION\_FAILED  
POSITION\_ENTRY\_PRICE\_MISMATCH  
POSITION\_REMAINING\_QUANTITY\_MISMATCH  
ACTIVE\_STOP\_LOSS\_MISMATCH  
ACTIVE\_TARGET\_MISMATCH

---

## **114\. Calculation Codes**

UNREALIZED\_PROFIT\_LOSS\_MISMATCH  
UNREALIZED\_RETURN\_PERCENTAGE\_MISMATCH  
DISTANCE\_TO\_STOP\_MISMATCH  
DISTANCE\_TO\_TARGET\_MISMATCH  
HOLDING\_DURATION\_MISMATCH  
INITIAL\_RISK\_PERCENTAGE\_MISMATCH  
REWARD\_PERCENTAGE\_MISMATCH  
RISK\_REWARD\_RATIO\_MISMATCH  
PARTIAL\_EXIT\_REALIZED\_PROFIT\_LOSS\_MISMATCH  
PARTIAL\_EXIT\_RETURN\_PERCENTAGE\_MISMATCH  
CAPITAL\_RECOVERED\_PERCENTAGE\_MISMATCH  
AVERAGE\_EXIT\_PRICE\_MISMATCH  
REMAINING\_UNREALIZED\_PROFIT\_LOSS\_MISMATCH  
PARTIAL\_STATE\_TOTAL\_PROFIT\_LOSS\_MISMATCH  
PARTIAL\_STATE\_TOTAL\_RETURN\_MISMATCH  
FINAL\_GROSS\_PROFIT\_LOSS\_MISMATCH  
FINAL\_GROSS\_RETURN\_MISMATCH  
FINAL\_NET\_PROFIT\_LOSS\_MISMATCH  
FINAL\_NET\_RETURN\_MISMATCH

---

## **115\. Lifecycle and Confirmation Codes**

INVALID\_SESSION\_STATUS\_TRANSITION  
LIFECYCLE\_TRANSITION\_WITHOUT\_USER\_CONFIRMATION  
AI\_ATTEMPTED\_AUTOMATIC\_STATE\_TRANSITION  
CANONICAL\_CHANGE\_WITHOUT\_CONFIRMATION  
CONFIRMED\_ACTION\_TIMESTAMP\_INVALID  
INITIAL\_ANALYSIS\_POSITION\_ALREADY\_EXISTS  
WATCHING\_UPDATE\_POSITION\_EXISTS  
OPEN\_UPDATE\_WITHOUT\_OPEN\_POSITION  
PARTIAL\_REVIEW\_WITHOUT\_PARTIAL\_POSITION  
CLOSING\_ANALYSIS\_POSITION\_NOT\_CLOSED

---

## **116\. Context Codes**

CONTEXT\_ATTEMPTED\_CANONICAL\_OVERRIDE  
CONTEXT\_CANONICAL\_FACT\_MISMATCH  
CONTEXT\_EVENT\_AFTER\_CUTOFF  
CONTEXT\_GENERATED\_BEFORE\_CUTOFF  
CONTEXT\_STALE  
CONTEXT\_PENDING\_PROPOSAL\_LOST  
CONTEXT\_PROPOSAL\_PROMOTED\_WITHOUT\_CONFIRMATION  
CONTEXT\_HISTORY\_COMPRESSED

---

# **Part XX — Test Cases**

## **117\. Market Snapshot Test**

Input:

{  
  "high": 2890,  
  "low": 2820,  
  "last": 2910  
}

Expected issue:

MARKET\_HIGH\_BELOW\_LAST

Path:

/last

---

## **118\. Position State Test**

Canonical state:

{  
  "entry\_price": 2800,  
  "remaining\_quantity": 100  
}

AI payload:

{  
  "position\_assessment": {  
    "entry\_price": 2820,  
    "remaining\_quantity": 100  
  }  
}

Expected issue:

POSITION\_ENTRY\_PRICE\_MISMATCH

---

## **119\. Stop Proposal Test**

Canonical stop:

2840

AI assessment:

{  
  "stop\_loss\_price": 2880,  
  "revised\_stop\_proposed": false,  
  "proposed\_stop\_loss": null  
}

Expected issue:

ACTIVE\_STOP\_LOSS\_MISMATCH

The AI must use:

{  
  "stop\_loss\_price": 2840,  
  "revised\_stop\_proposed": true,  
  "proposed\_stop\_loss": 2880  
}

---

## **120\. Partial Exit Test**

Previous remaining quantity:

100

Confirmed partial exit:

exited \= 50  
remaining \= 60

Expected issue:

PARTIAL\_EXIT\_QUANTITY\_MISMATCH

Because:

50 \+ 60 \!= 100

---

## **121\. Final Exit Test**

Original quantity:

100

Exits:

50 at 2920  
50 at 2900

Expected average exit:

2910

Expected gross P/L for entry 2800:

(2910 \- 2800\) × 100 \= 11000

Any other result beyond tolerance must fail.

---

# **Part XXI — Configuration**

## **122\. Recommended Configuration File**

domain\_validation:  
  strict\_mode: true

  tolerances:  
    price\_absolute: 0.01  
    percentage\_absolute: 0.02  
    ratio\_absolute: 0.02  
    money\_idr\_absolute: 1  
    money\_usd\_absolute: 0.01  
    timestamp\_clock\_skew\_seconds: 60

  risk:  
    maximum\_initial\_risk\_percentage: 5.0  
    weak\_risk\_reward\_threshold: 1.0

  evidence:  
    orderbook\_warning\_minutes: 15  
    orderbook\_error\_minutes: 60  
    chart\_warning\_trading\_days: 5  
    chart\_error\_trading\_days: 20

  outcome\_classification:  
    large\_profit\_min\_percentage: 10.0  
    profit\_min\_percentage: 2.0  
    small\_profit\_min\_percentage: 0.25  
    break\_even\_min\_percentage: \-0.25  
    break\_even\_max\_percentage: 0.25  
    small\_loss\_min\_percentage: \-2.0  
    large\_loss\_max\_percentage: \-5.0

  stop\_trigger:  
    mode: CURRENT\_PRICE\_OR\_USER\_CONFIRMATION

---

# **Part XXII — Acceptance Criteria**

## **123\. Implementation Completion Criteria**

Domain validation is complete when:

1. Market OHLC relationships are checked.  
2. Bid, offer, spread, and change calculations are validated.  
3. Position quantities reconcile across all actions.  
4. Canonical entry, stop, target, and quantity cannot be overwritten by AI.  
5. Unrealized and realized P/L are calculated using Decimal.  
6. Entry, stop, target, risk, reward, and risk-reward rules are enforced.  
7. Partial exit calculations reconcile with the previous position.  
8. Weighted average exit and final P/L are validated.  
9. Outcome classification follows configured thresholds.  
10. Lifecycle transitions require valid status and user confirmation.  
11. Evidence freshness and source conflicts are detected.  
12. Context Summary cannot override canonical state.  
13. Context cutoff and staleness are checked.  
14. Validation issues use stable codes and JSON Pointer paths.  
15. Unit tests cover every blocking rule.  
16. CI rejects any fixture that violates a required domain rule.

---

## **124\. Recommended Next Artifact**

The next implementation document should be:

SCHEMA\_TEST\_FIXTURES\_SPEC.md

It should define:

* required valid fixtures;  
* required invalid fixtures;  
* directory layout;  
* naming conventions;  
* expected error assertions;  
* fixture factories;  
* cross-schema integration scenarios;  
* Gemini and DeepSeek contract test payloads.

