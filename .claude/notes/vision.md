# AI Health Platform - Complete Vision

> This document contains the full north-star vision for the platform.
> Only load this for strategic planning sessions — not for focused feature work.
> Moved from CLAUDE.md to reduce per-session context load.

---

## The Complete Vision: A Personal Health Operating System

At full maturity, this platform becomes something that doesn't yet exist: a **personal health operating system**—not an app that gives advice, but a continuously learning infrastructure layer that sits beneath a person's health decisions for decades, accumulating understanding, preserving memory, and providing increasingly precise, honest, and useful intelligence about their specific body.

### Data Ingestion: The Full Signal Landscape

The system ingests every meaningful signal available, across seven categories:

#### 1. Continuous Physiological Streams
- Wearables (WHOOP, Oura, Apple Watch, Garmin, Fitbit) providing sleep architecture, HRV, resting heart rate, respiratory rate, skin temperature, SpO2, and movement
- Continuous glucose monitors (Dexcom, Libre, Levels) providing glycemic variability, time-in-range, and meal response patterns
- Blood pressure cuffs (Withings, Omron) with time-of-day context
- Smart scales providing weight, body composition, and hydration estimates
- Smart rings and patches providing menstrual cycle phase, basal body temperature, and ovulation detection
- ECG-capable devices for rhythm monitoring
- EEG headbands (Muse, Dreem) for meditation quality and sleep stage validation
- Smart mattresses and bedroom sensors (Eight Sleep, Withings) providing sleep environment temperature, movement, and respiratory patterns

#### 2. Discrete Lab and Biomarker Data
- Standard panels (CBC, CMP, lipids, thyroid, A1C)
- Advanced biomarkers (hs-CRP, homocysteine, insulin, HOMA-IR, Lp(a), apoB, ferritin, vitamin D, B12, folate, magnesium RBC)
- Hormone panels (cortisol awakening response, DHEA-S, testosterone, estradiol, progesterone, full thyroid including reverse T3, antibodies)
- Gut health (comprehensive stool analysis, zonulin, calprotectin, microbiome sequencing with functional pathway analysis)
- Genomics (SNPs affecting methylation, detoxification, nutrient metabolism, inflammation, drug metabolism)
- Epigenetics (biological age clocks like GrimAge, PhenoAge)
- Metabolomics (organic acids, amino acids)
- Inflammatory markers (cytokine panels, autoimmune markers)
- Nutrient testing (OmegaQuant, micronutrient panels)

#### 3. Subjective Self-Report
- Daily check-ins: energy, mood, stress, focus, pain (1-5 scales with optional notes)
- Symptom tracking: 200+ symptoms across all body systems with severity, timing, and triggers
- Sleep quality beyond wearable data: dream recall, feeling of restoration, sleep anxiety
- Digestive logs: bowel quality (Bristol scale), bloating, reflux, appetite
- Menstrual symptoms: flow, cramping, PMS severity, cycle phase symptoms
- Exercise perception: RPE, enjoyment, recovery feeling
- Cognitive self-assessment: brain fog, word-finding, memory, reaction time
- Weekly reflections: pattern hypotheses, concerns, wins

#### 4. Behavioral and Lifestyle Inputs
- Nutrition: photo-based food logging with AI extraction, macros, micros, meal timing, eating window
- Supplements: what, when, dose, brand (for quality variance tracking)
- Medications: prescription and OTC, timing, missed doses
- Substances: caffeine (amount, timing), alcohol (type, amount, timing), cannabis, nicotine
- Exercise: type, duration, intensity, heart rate zones, training load (acute:chronic ratio)
- Mind-body practices: meditation (duration, type, quality), breathwork, yoga, cold/heat exposure
- Social: isolation vs connection, relationship stress, social support
- Work: hours, stress level, deadlines, screen time, meeting load
- Recovery practices: sauna, massage, stretching, naps

#### 5. Environmental and Contextual Data
- Sleep environment: temperature, humidity, light level, noise, air quality, bed partner presence
- Home environment: indoor air quality (PM2.5, CO2, VOCs), mold indicators
- Outdoor environment: local pollen, air quality index, UV index, temperature/humidity
- Light exposure: lux levels throughout day, blue light evening exposure
- Circadian context: wake time consistency, light timing relative to chronotype
- Travel: time zone changes, altitude, travel fatigue
- Location: home/work/other, urban/rural, building characteristics

#### 6. Medical and Clinical History
- Diagnoses: current and historical
- Procedures and surgeries
- Allergies and sensitivities
- Family history: relevant conditions with age of onset
- Vaccination records
- Imaging: baseline and changes (where permitted)
- Clinical notes: key findings from provider visits
- Prescription history

#### 7. Digital Phenotyping and Passive Signals
- Phone usage patterns: screen time, app categories, pickup frequency (stress proxy)
- Typing dynamics: speed, errors, hesitation (cognitive state)
- Voice analysis: from voice memos or calls (with consent), detecting fatigue, stress, mood shifts
- Communication patterns: message frequency, response latency (social health proxy)
- Calendar density: meeting load, free time, schedule regularity
- Location patterns: movement, routine adherence, novelty
- Music listening: tempo, genre, mood playlists
- Purchase patterns: grocery composition, supplement orders, alcohol purchases

### The Analytical Core: What Happens Inside

With this data, the system builds a **personal health model** using rigorous statistical and ML methods:

#### Foundational Statistics
- Robust baseline estimation (median, MAD) resistant to outliers
- Seasonal decomposition (weekly, monthly, annual rhythms)
- Change-point detection (PELT, BOCPD) for regime shifts
- Missing data handling via multiple imputation with uncertainty propagation

#### Causal Architecture
- Personal DAGs (directed acyclic graphs) representing believed causal relationships
- Confounder identification and adjustment
- Instrumental variable analysis where possible
- Mediation analysis for pathway understanding
- Difference-in-differences for intervention evaluation
- Regression discontinuity for threshold effects
- Synthetic control methods for complex interventions

#### Longitudinal Learning
- Hierarchical Bayesian models with population priors and individual posteriors
- Online updating without full recomputation
- Temporal weighting (recent data matters more)
- Transfer learning from similar users (privacy-preserving)
- Regime-aware modeling (illness, travel, life changes)

#### Uncertainty Quantification
- Credible intervals on all estimates
- Calibrated confidence (predictions match outcomes at stated rates)
- Explicit representation of "I don't know"
- Sensitivity analysis showing robustness of conclusions

#### Cross-Domain Reasoning
- Multi-domain dependency graphs capturing cascades:
  - Sleep debt -> HRV suppression -> recovery impairment -> performance decline
  - Gut dysfunction -> systemic inflammation -> fatigue -> mood disruption
  - Stress -> cortisol dysregulation -> sleep fragmentation -> cognitive impairment
- Propagation of effects across domains with appropriate delays
- Identification of root causes vs symptoms

#### Predictive Capabilities
- Short-term forecasting: tomorrow's HRV, energy, sleep quality
- Trend projection: where is this metric heading?
- Risk windows: periods of elevated vulnerability
- Recovery time estimation: how long until baseline return?

### Outputs: What the User Experiences

#### 1. Daily Intelligence
- Morning brief: overnight recovery assessment, day's predicted energy, any alerts
- Evening summary: day's patterns, notable deviations, preparation for tomorrow
- Real-time nudges (optional, user-controlled): "Your HRV suggests prioritizing recovery today"

#### 2. Domain-Specific Narratives
For each health domain, synthesized explanations that:
- State what is currently known with calibrated confidence
- Explain what patterns have been detected and why they matter
- Identify what remains uncertain and what data would resolve it
- Connect to other domains where relevant
- Reference the user's historical patterns

#### 3. Experiment Frameworks
When the system identifies a testable hypothesis:
- Formal experiment design with baseline/intervention periods
- Power analysis: how long to run, minimum detectable effect
- Primary and secondary outcome metrics
- Adherence tracking requirements
- Pre-registered success criteria
- Washout period if needed for sequential experiments

#### 4. Evaluation Verdicts
After experiments:
- Clear verdict: helpful / not helpful / unclear / insufficient data
- Effect size with confidence interval
- Comparison to prior expectations
- Sensitivity analysis: how robust is this conclusion?
- Storage in personal response memory

#### 5. Early Warning Signals
Proactive alerts when:
- Metrics deviate significantly from personal baseline
- Patterns suggest emerging dysfunction (before symptoms)
- External factors (travel, illness, stress) create vulnerability windows
- Combinations of signals suggest concern (even if individual metrics are borderline)

#### 6. Reassurance When Appropriate
Equally important -- explicit communication when:
- Nothing meaningful is happening (silence is intentional)
- Variation is within normal range for this person
- A concerning pattern has resolved
- Data is insufficient to draw conclusions (not hiding behind vagueness)

#### 7. Audit Trail and Explainability
For every insight:
- Which data sources contributed
- What analysis was performed
- What thresholds were crossed
- What governance checks were applied
- What alternative interpretations were considered
- Full reproducibility if the user wants to verify

#### 8. Memory and Personal History
The system remembers:
- How this person responds to specific interventions
- What their body does when sick, stressed, traveling, training hard
- What their recovery patterns look like
- What has been tried before and what happened
- What questions remain unanswered

This memory persists across years, building increasingly precise personal models.

#### 9. Clinician/Practitioner Interface
For users who share with providers:
- Structured summaries of relevant patterns
- Trend visualizations with statistical context
- Hypotheses worth discussing
- Data quality indicators
- Export in clinical formats

Not replacing clinical judgment -- augmenting it with data the clinician couldn't otherwise access.

#### 10. Research Participation
With explicit consent:
- Matching to relevant research studies
- Contribution to privacy-preserving aggregate analyses
- Feedback when collective patterns are discovered

### What Amazing Feels Like

A user who has been on this system for 3 years:
- **Knows their body** in a way that was previously impossible -- not vague intuitions, but quantified patterns with uncertainty bounds
- **Remembers** what worked and what didn't, across dozens of experiments, without relying on fallible memory
- **Sees problems coming** before they become crises -- the system detects the early signs of overtraining, burnout, immune suppression, or metabolic drift
- **Isn't overwhelmed** because the system is silent when there's nothing meaningful, and speaks clearly when there is
- **Trusts the system** because it has been honest about uncertainty, admitted when it was wrong, and never overclaimed
- **Can show a new doctor** a coherent summary of their health patterns, not a stack of disconnected PDFs
- **Has agency** over their health decisions, supported by evidence, not dictated to by an algorithm

### What This Is NOT

Even at full maturity, the system:
- **Never diagnoses**. It identifies patterns and surfaces hypotheses. Diagnosis is a clinical act.
- **Never prescribes**. It can suggest experiments, but never tells a user to take a medication or stop a treatment.
- **Never replaces clinical care**. It augments the user's understanding and the clinician's data access.
- **Never lets AI "decide"**. LLMs translate and narrate; deterministic systems with human-auditable logic make decisions.
- **Never hides uncertainty**. If the system doesn't know, it says so explicitly.
- **Never optimizes for engagement**. It optimizes for accuracy and user benefit, even if that means being quiet.

### The Regulatory and Ethical Posture

The system is designed to:
- Operate clearly within the "wellness" category while being useful enough to matter
- Maintain explicit non-diagnostic, non-prescriptive boundaries
- Provide audit trails sufficient for regulatory inspection
- Implement consent granularly (what data, what analysis, what sharing)
- Allow full data export and deletion
- Never sell or share identifiable data
- Be transparent about limitations and failure modes
