# Golden Values DSCR Determinism Analysis

**Date:** 2026-05-07
**Status:** Updated — tolerance is a defensive policy, NOT runtime nondeterminism

---

## Section 1: Determinism Analysis

### Tests Are Deterministic

Golden values tests pass consistently across multiple consecutive runs with no variance.
Financial model is deterministic — no random behavior in DSCR calculations.

### Floating Point Behavior

Financial model uses standard IEEE 754 floating point. No non-deterministic aggregation
(pandas not used in DSCR calculation path). Accumulated rounding is consistent across runs.

### Execution Is Fully Deterministic

The model produces identical results on every run. There is no execution drift from:
- Streamlit cache collisions (golden tests run through the API layer, not through Streamlit UI)
- Parallel test execution
- Hash collisions
- Any other runtime nondeterminism

---

## Section 2: DSCR Tolerance Rationale

### Current Tolerance: ±0.15

**Purpose:** Defensive policy tolerance that protects against deliberate future model improvements
(e.g., adding CO2 revenue streams, refining OpEx aggregation, adjusting tax treatment).
It is NOT caused by runtime nondeterminism.

| Concern | Explanation |
|---------|-------------|
| Runtime nondeterminism | None — model is deterministic |
| Cache collisions | Golden tests bypass Streamlit UI entirely |
| Deliberate model improvements | May shift DSCR by more than rounding — policy tolerance covers this |
| Calibration accuracy | Separate concern (TUHO CO2, Oborovo OpEx) |

**Important distinctions:**
- **Determinism** — model produces same result every time (✅ confirmed)
- **Calibration accuracy** — model output matches real-world data (❌ TUHO/Oborovo have known gaps)
- **Regression policy** — ±0.15 tolerance is a defensive cushion for future model changes

### What the Tolerance IS NOT

The ±0.15 tolerance does NOT compensate for:
- Streamlit cache collisions (no such collisions in golden tests — they run via API layer)
- Non-deterministic execution (none exists in this codebase)
- TUHO missing CO2 revenue (611 kEUR Y1 — model bug, not random drift)
- Oborovo OpEx duplication (~660 kEUR Y1 — model bug, not random drift)

### Target Future Tolerance: ±0.03–0.05

After:
1. TUHO CO2 revenue added (611 kEUR Y1)
2. Oborovo OpEx duplicate items fixed
3. Calibration accuracy improved

**Do NOT artificially tighten tolerance to hide model bugs.**

---

## Section 3: Model Calibration Gaps (Separate Concern)

**IMPORTANT:** These are model-quality issues, NOT determinism problems.
They do NOT justify the DSCR tolerance — that tolerance is a policy cushion for future model improvements.

### TUHO Wind (72 MW)

| Issue | Detail |
|-------|--------|
| Missing CO2 revenue | Y1 = 611 kEUR CO2 certificates not in model |
| Revenue gap | ~-12.5% from missing CO2 |
| Tax shield impact | Model understates tax benefit |

### Oborovo Solar (53.63 MW)

| Issue | Detail |
|-------|--------|
| OpEx duplication | Y1 OpEx model = 1,998 kEUR vs Excel = 1,338 kEUR |
| Root cause | B.01 (280 vs 198) + B.02 (667 vs 244) aggregates include sub-items already counted |
| Impact | OpEx inflated by ~660 kEUR |

---

## Section 4: What Tolerance Covers

| Scenario | Covered by ±0.15? |
|----------|-------------------|
| DSCR within single project run | ✅ Policy buffer for future model improvements |
| Future model refinements | ✅ Deliberate improvements may shift DSCR |
| Cache collision in UI | ✅ N/A for golden tests (API layer) |
| TUHO missing CO2 revenue | ❌ Model bug — fix separately |
| Oborovo OpEx duplication | ❌ Model bug — fix separately |
| Floating point accumulation | N/A — deterministic |

---

## Section 5: Three-Way Distinction

| Concept | Status | Action |
|---------|--------|--------|
| **Determinism** — same result every run | ✅ Confirmed | No action needed |
| **Calibration accuracy** — matches real-world data | ❌ TUHO/Oborovo gaps | Fix model |
| **Regression policy** — ±0.15 tolerance | ✅ Defensive buffer | Keep, do not misuse |

---

## Conclusion

1. **Model is deterministic** — no random behavior in financial calculations
2. **Golden tests run via API layer** — no Streamlit cache involved
3. **±0.15 tolerance is a defensive policy** — protects against future model improvements, NOT runtime nondeterminism
4. **Calibration gaps (TUHO CO2, Oborovo OpEx) are model bugs** — must be fixed separately, not masked by tolerance
5. **Long-term goal:** reduce to ±0.03–0.05 after calibration fixes