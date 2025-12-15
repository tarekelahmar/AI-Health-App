# North-Star System Diagram (OBSERVE → MODEL → INTERVENE → EVALUATE → REPEAT)

This is the "single source of truth" diagram for your whole product.

Keep this up-to-date as the system expands.

```mermaid
flowchart LR

  subgraph Observe[OBSERVE]
    W[Wearables\n(Oura/Whoop/Apple Watch)\nminute→daily] --> N[Normalize + Metric Registry]
    L[Labs\n(sparse events)] --> N
    C[Daily Check-ins\n(subjective + behaviors)] --> N
    U[Uploads\n(PDF/notes)\n(optional)] --> N
    N --> HD[(HealthDataPoint)]
    N --> LE[(LabResult)]
    N --> DC[(DailyCheckIn)]
  end

  subgraph Model[MODEL]
    HD --> B[Baselines\n(mean/std, per metric)]
    HD --> D[Detectors\nchange/trend/instability]
    DC --> D
    B --> D
    D --> I[(Insight)]
    subgraph Attribution[Attribution Engine]
      E[(Experiment)] --> AE[Lagged Effects\n0-3d]
      HD --> AE
      DC --> AE
      AE --> AR[AttributionResult\n(effect/confidence/coverage)]
    end
  end

  subgraph Intervene[INTERVENE]
    I --> P[(Protocol)]
    P --> IV[(Intervention)]
    IV --> E
    AE --> E
  end

  subgraph Evaluate[EVALUATE]
    E --> EV[Evaluation Engine\nbaseline vs intervention\nCohen's d + adherence]
    DC --> EV
    EV --> ER[(EvaluationResult)]
  end

  subgraph Repeat[REPEAT]
    ER --> LD[Loop Orchestrator\ncontinue/stop/adjust/extend]
    LD --> LDec[(LoopDecision)]
    LDec --> P
    LDec --> E
    LDec --> I
  end

  subgraph UX[UX SURFACES]
    I --> Feed[Insights Feed]
    HD --> Charts[Metric Charts + Baselines]
    DC --> Inbox[Daily Inbox\ncheck-in + behaviors]
    ER --> Outcomes[Experiment Outcomes]
    LDec --> Next[Next Best Action]
  end
```

