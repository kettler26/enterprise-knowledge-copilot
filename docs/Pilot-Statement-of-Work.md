# Pilot Statement of Work (SOW)

This SOW template defines a paid pilot for the SaaS Support & RevOps Copilot.

## 1. Parties and Pilot Window

- Vendor: `<your company>`
- Customer: `<customer legal name>`
- Pilot start date: `<yyyy-mm-dd>`
- Pilot end date: `<yyyy-mm-dd>` (default 6 weeks)

## 2. Pilot Objective

Demonstrate measurable improvement in support efficiency and answer quality through AI-assisted, grounded response generation using customer documentation and ticket context.

## 3. Scope

In scope:

- One workspace / one business unit
- One ticketing integration (e.g., Zendesk or Intercom)
- One knowledge source (e.g., Notion or Confluence export)
- Agent-assisted draft responses (human approval required)
- KPI tracking and weekly review

Out of scope:

- Fully autonomous ticket updates in week 1-4
- Multi-region data residency customizations
- Custom model training

## 4. Deliverables

Vendor delivers:

- Working pilot environment
- Connected data sources in agreed scope
- KPI baseline report (week 1)
- Weekly progress report
- Final pilot readout with ROI estimate

Customer provides:

- Integration access and API keys
- Named business owner and technical champion
- Historical KPI exports (if available)
- Weekly stakeholder attendance

## 5. Success Metrics

Primary metrics (baseline vs pilot period):

- Average Handle Time (AHT)
- First Response Time (FRT)
- Deflection rate in repetitive categories

Secondary metrics:

- Escalation rate
- Internal QA score / policy adherence
- Agent satisfaction feedback

Success threshold:

- At least 2 of 3 primary metrics improve by agreed target range

## 6. Commercial Terms

- Setup fee: `EUR <amount>`
- Pilot monthly fee: `EUR <amount>`
- Duration: 6 weeks
- Optional conversion credit: up to 50% setup fee applied to annual contract

Payment terms:

- 50% at pilot start
- 50% at end of week 3

## 7. Security and Compliance

Vendor commitments:

- Data segregation by workspace
- Credential storage via secrets manager or encrypted env
- Access logs and traceability for prompts/tools/outputs
- No model training on customer data without written consent

Customer commitments:

- Provide least-privilege service credentials
- Remove access for inactive users
- Approve data processing boundaries before go-live

## 8. Governance and Cadence

- Weekly 45-minute steering call
- Dedicated Slack or email channel for pilot operations
- Issue severity matrix (P1/P2/P3) and response times

## 9. Exit and Conversion

At pilot close:

- Joint review of KPI outcomes
- Go / No-Go decision within 10 business days

If converted:

- Pilot is transitioned into annual subscription plan

If not converted:

- Access revoked within agreed offboarding period
- Optional remediation proposal for specific blockers
