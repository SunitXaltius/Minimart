# MiniMart Cost and ROI Case

## Purpose

This document evaluates the financial case for building MiniMart with AI assistance. It separates two questions that should not be mixed:

1. Was the AI-assisted delivery method cheaper than the estimated traditional build?
2. Does MiniMart create enough operational value to justify owning and operating it?

The worked example answers the first question. The second requires measured adoption and user-benefit data that is not yet available.

## Time horizon

Use a **12-month horizon**. This captures the initial build, AI-tool costs, additional review and the first year of maintenance, when hidden technical debt is most likely to appear. A longer forecast would give a more impressive number but would be unreliable without real maintenance and usage data.

All amounts below are illustrative Singapore dollars (SGD). Replace estimates with approved financial figures before making an investment decision.

## Cost factors beyond initial development

| Cost factor | One-off or ongoing | Specific to AI-assisted work? | Why it matters |
|---|---|---|---|
| AI subscription and token usage | Ongoing | Yes | Claude, ChatGPT, Copilot or API use may be charged monthly or by consumption. Costs can increase as prompts and uploaded files grow. |
| Human review of generated code | One-off and ongoing | Mostly | Generated code can look convincing while containing subtle security or logic problems. Every material change still requires human review. |
| Security assessment and remediation | One-off and recurring | Partly | Every application needs security review, but AI output commonly contains unsafe defaults, missing authorization, exposed secrets or incomplete validation. |
| Testing and test maintenance | One-off and ongoing | No | Tests must cover authentication, checkout, administration and failure paths. Generated tests may execute code without proving the correct outcome. |
| Code nobody fully understands | Ongoing | Mostly | Rapid generation can leave the team responsible for code it did not design. Debugging and enhancement then take longer and carry more risk. |
| Technical debt and later rework | Ongoing | Partly | AI may optimize for the immediate prompt rather than a consistent architecture. Early shortcuts become expensive when the application changes. |
| Incorrect or discarded AI output | One-off and ongoing | Yes | Time is spent checking hallucinated APIs, repairing plausible-but-wrong changes and discarding unusable output. |
| Documentation and knowledge transfer | One-off and ongoing | Partly | Routes, configuration, database structure, deployment and rollback must be understood by people other than the original builder. AI-written explanations must also be verified. |
| Team training | One-off and recurring | Partly | Team members need Flask, SQLite, Git, testing and security knowledge in addition to prompting skills. |
| Production hosting | Ongoing | No | The server, storage, network and production WSGI service cost money even though the application was built quickly. |
| CI/CD pipeline usage | Ongoing | No | GitHub Actions usage and failed or repeated pipeline runs consume resources and support time. |
| Logging, monitoring and storage | Ongoing | No | Logs and checks need storage, maintenance and a named person who responds to alerts. |
| Backup and recovery | Ongoing | No | `minimart.db` must be backed up, protected and periodically restored in a rehearsal. An untested backup may be unusable. |
| Deployment and rollback rehearsal | Recurring | No | A written runbook is insufficient until its commands, release tag and database backup have been tested. |
| Incident response and downtime | Unexpected and ongoing | No | A small team without operations staff must absorb investigation, user communication and recovery work. |
| Privacy and confidential-data exposure | One-off and ongoing | Partly | Prompts and uploaded files may contain confidential information. The team must control what is sent to AI services and retained in logs. |
| Licensing and code-provenance review | One-off and recurring | Mostly | Generated snippets and external packages still require licensing and provenance review. |
| AI-provider dependency | Ongoing and later | Yes | Pricing, limits, availability and model behaviour may change. A prompt that works today may give different output later. |
| Tool and workflow integration | One-off and ongoing | Partly | AI tools must work with the repository, IDE, access controls and approval process. Integrations require updates and troubleshooting. |
| Future database migration | Later | No | SQLite is proportionate now, but higher concurrency or availability requirements may require migration to a server database. |
| Maintenance after the original builder leaves | Later and ongoing | Partly | A new maintainer may spend considerable time reconstructing why generated code and prompts led to particular decisions. |

The costs most often omitted are rigorous review, maintaining unfamiliar code, correcting plausible-but-wrong output, security remediation, recovery rehearsals, incident response and AI-provider dependency.

## Inputs required

| Input | Why it is needed | Evidence source |
|---|---|---|
| Actual AI-assisted build days | Establishes the real delivery effort. | Timesheets or project log |
| Comparable traditional-build estimate | Provides the avoided-cost baseline. It must cover the same scope and quality. | Approved estimate |
| Fully loaded daily rate | Converts effort to cost and should include salary, benefits, equipment and employer costs. | Finance |
| AI subscription and token costs | Captures all tools rather than only the main subscription. | Invoices or usage report |
| Review and security effort | Captures time spent examining and correcting generated code. | Timesheets and review records |
| Rework and discarded-output effort | Captures suggestions that were rejected or replaced. | Prompt log and commits |
| First-year maintenance effort | Captures debugging, dependency updates and unfamiliar-code costs. | Maintenance records; estimate initially |
| Hosting, monitoring and backup costs | Required for MiniMart's total cost of ownership. | Supplier bills or internal rates |
| Support and incident-response effort | Captures operational ownership. | Ticket and incident records |
| Active users and adoption rate | Determines whether the application is producing value. | Access and usage metrics |
| Time saved per use | Quantifies operational benefit against the previous process. | Before-and-after observation |
| Error or failure reduction | Quantifies avoided rework only when a reliable baseline exists. | Quality records |

## Worked 12-month calculation

### Working assumptions

- Loaded developer cost: **SGD 600 per working day**
- Traditional build: **4 weeks × 5 days = 20 days**
- AI-assisted build: **5 days**
- AI tools: **SGD 100 per month × 12 months**
- Additional code review and security work: **4 days**
- First-year maintenance and rework reserve: **4 days**

### Traditional build cost

```text
20 days × SGD 600 = SGD 12,000
```

### AI-assisted cost

| Cost | Arithmetic | Amount |
|---|---:|---:|
| Initial AI-assisted build | 5 × SGD 600 | SGD 3,000 |
| AI tools | SGD 100 × 12 months | SGD 1,200 |
| Additional review and security | 4 × SGD 600 | SGD 2,400 |
| Maintenance and rework reserve | 4 × SGD 600 | SGD 2,400 |
| **Total AI-assisted cost** | 3,000 + 1,200 + 2,400 + 2,400 | **SGD 9,000** |

### Return

```text
Net benefit = traditional cost - AI-assisted cost
            = SGD 12,000 - SGD 9,000
            = SGD 3,000

ROI         = net benefit / AI-assisted cost × 100
            = SGD 3,000 / SGD 9,000 × 100
            = 33.3%

Cost reduction = SGD 3,000 / SGD 12,000 × 100
               = 25%

Initial build-time reduction = (20 days - 5 days) / 20 days × 100
                             = 75%
```

The defensible result is therefore an **estimated first-year net benefit of SGD 3,000**, **33.3% ROI** and **25% lower delivery cost**. The 75% build-time reduction must not be described as 75% cost savings because tools, review, security and maintenance still cost money.

## Assumptions and sensitivity

| Input | Fact or estimate? | Sensitivity |
|---|---|---|
| Five-day AI-assisted build | Fact if supported by project records | Medium. Confirm that the recorded work includes testing, security and deployment preparation. |
| Four-week traditional build | Estimate | **Very high.** At 15 comparable days, the calculated ROI falls to 0%. |
| SGD 600 loaded daily cost | Estimate until confirmed by finance | High. It affects build, review and maintenance costs. |
| Four review/security days | Estimate | **Very high.** Every additional day reduces net benefit by SGD 600. |
| Four maintenance/rework days | Estimate | **Very high.** Deferred work can consume the initial saving. |
| SGD 1,200 annual AI-tool cost | Estimate | Medium. Shared subscriptions should be allocated fairly. |
| Equal scope and quality | Unproven assumption | **Critical.** A five-day prototype is not comparable with a four-week production-ready application. |
| User-productivity benefit excluded | Conservative exclusion | Potentially high. Add it only after measuring adoption and time saved. |
| Common operating costs excluded from the method comparison | Assumption | Low for comparing methods; high for the full product business case. |

### Sensitivity to traditional duration

| Traditional duration | Avoided traditional cost | Net benefit after SGD 9,000 AI cost | ROI |
|---:|---:|---:|---:|
| 15 days | SGD 9,000 | SGD 0 | 0% |
| 20 days | SGD 12,000 | SGD 3,000 | 33.3% |
| 25 days | SGD 15,000 | SGD 6,000 | 66.7% |

### Sensitivity to review and maintenance effort

| Combined additional effort | AI-assisted cost | Net benefit | ROI |
|---:|---:|---:|---:|
| 4 days | SGD 6,600 | SGD 5,400 | 81.8% |
| 8 days | SGD 9,000 | SGD 3,000 | 33.3% |
| 12 days | SGD 11,400 | SGD 600 | 5.3% |

The case is most sensitive to the traditional four-week estimate and to the review, rework and maintenance needed later.

## Full MiniMart business ROI

The worked calculation measures the return from the **development approach**, not the business value of MiniMart. Once usage data exists, calculate:

```text
Annual user value = active users
                  × minutes saved per use / 60
                  × uses per year
                  × loaded hourly employment cost

Business ROI = (annual user value - total first-year MiniMart cost)
               / total first-year MiniMart cost × 100
```

Do not include user-time savings until they have been measured against the previous process.

## Panel summary

> I evaluated MiniMart over 12 months so the comparison includes the build, AI tools, additional review and first-year maintenance. At an illustrative loaded rate of SGD 600 per day, the traditional 20-day build costs SGD 12,000. The AI-assisted approach costs SGD 9,000: SGD 3,000 for the five-day build, SGD 1,200 for tools, SGD 2,400 for review and security, and SGD 2,400 reserved for maintenance and rework. That produces an estimated SGD 3,000 net benefit and 33.3% ROI. However, if the traditional build would take only 15 days, or if generated code creates significantly more review and maintenance, the return disappears. This is therefore a provisional ROI for the delivery method, not proof of MiniMart's complete business value.

## Caveats to state before being asked

- The four-week traditional build is an estimate, not an observed invoice.
- Both approaches must be compared at the same scope, quality, security and deployment readiness.
- Five days of coding is not automatically five days to production.
- The maintenance reserve may be too low if the team does not understand the generated code.
- Faster delivery creates no business value if users do not adopt MiniMart.
- Security incidents, significant downtime and a future database migration are not included.
- Hosting and monitoring costs continue even though they mostly cancel in the method comparison.

