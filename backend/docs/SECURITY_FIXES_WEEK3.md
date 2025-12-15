# Security Fixes - Week 3 Progress

## ✅ Risk #7: Evaluation Without Adherence Evidence - FIXED

**Status:** COMPLETE

**Changes Made:**

1. **Required Adherence Evidence for "Helpful" Verdicts** (`backend/app/engine/evaluation_service.py`):
   - Cannot declare "helpful" without adherence evidence (adherence_rate > 0)
   - Verdict downgraded to "unclear" if no adherence evidence
   - Added explicit reasons: "no_adherence_evidence", "cannot_confirm_intervention_was_followed"

2. **Added Confidence Score**:
   - Computed from effect size, coverage, and adherence
   - Formula: `confidence = effect_confidence * coverage_penalty * adherence_confidence`
   - Adherence confidence is 0.0 if no adherence events logged
   - Minimum confidence threshold (0.5) required for "helpful" verdicts

3. **Added Uncertainty Bands (Confidence Intervals)**:
   - 95% confidence intervals for baseline and intervention means
   - Uses scipy.stats if available, fallback to approximation
   - Stored in evaluation details for transparency

4. **Prominent Labeling**:
   - Summary text includes confidence labels: "[LOW CONFIDENCE]", "[MODERATE CONFIDENCE]", "[HIGH CONFIDENCE]"
   - Adherence warnings: "[WARNING: No adherence events logged]" or "[WARNING: Low adherence may affect results]"
   - Clear messaging when adherence is unknown

5. **Updated API Schema** (`backend/app/api/schemas/evaluations.py`):
   - Added `confidence_score` field (0-1)
   - Added `has_adherence_evidence` boolean field
   - Both fields extracted from evaluation details

**Key Features:**
- Prevents over-claiming effectiveness without evidence
- Requires adherence evidence for positive verdicts
- Clear uncertainty communication
- Prominent warnings for low confidence or missing adherence

**Example Behavior:**
- Effect size = 0.5, direction matches, but adherence_rate = 0.0 → verdict = "unclear" (not "helpful")
- Effect size = 0.4, direction matches, adherence_rate = 0.8, confidence = 0.6 → verdict = "helpful"
- Effect size = 0.3, direction matches, adherence_rate = 0.3, confidence = 0.2 → verdict = "unclear" (low confidence)

## Remaining Fixes

### Risk #8: Attribution False Positives
**Priority:** Week 3
**Status:** IN PROGRESS

### Risk #10: In-Process Scheduler
**Priority:** Week 4
**Status:** PENDING

