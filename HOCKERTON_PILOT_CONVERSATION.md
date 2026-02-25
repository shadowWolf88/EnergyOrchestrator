# Hockerton Housing Project — Pilot Conversation Guide

*A reference document for discussing the AI Energy Orchestrator with the project founder.*

---

## What Is This Project?

I've been building an **AI-powered energy optimisation system** for residential estates. It models homes with solar panels, batteries, electric vehicles and heat pumps, then uses a mathematical optimisation algorithm to decide — in advance — when to charge/discharge batteries, when to charge EVs, and when to draw from or export to the grid.

The goal is to:
1. **Cut household energy bills** by shifting demand to cheaper times of day
2. **Reduce carbon emissions** by using energy when the grid is cleanest
3. **Defer expensive grid infrastructure upgrades** by keeping peak demand below the transformer's limit

It's built in Python, runs physics-based simulations, and includes an interactive web dashboard.

---

## Why Hockerton?

Hockerton Housing Project is one of the most well-documented sustainable communities in the UK. It has:

- A small, known number of homes (9 dwellings)
- Existing renewable generation (solar PV + wind turbine)
- A community ethic aligned with energy optimisation
- Nottinghamshire location — which is already the geographic reference point built into this simulation
- Real monitoring data potentially available (smart meters, inverter logs)

Running a pilot simulation calibrated to Hockerton would:
- Give the platform its **first real-world validation case**
- Produce a **credible, publishable benchmark** (not just synthetic data)
- Demonstrate the system to **DNOs (now National Grid ED)**, **Ofgem**, and **potential funders**
- Be genuinely useful to the community itself

---

## Questions to Ask / Information I Need

### About the Physical Assets

1. **Solar PV**: What is the current total installed capacity (kWp)? Is it per-home or shared? South-facing, what pitch/orientation?
2. **Wind**: The community wind turbine — what is its rated capacity (kW)? Is output shared across all homes?
3. **Batteries**: Do any homes have battery storage (e.g. Tesla Powerwall, Sonnen)? If so, what sizes (kWh)?
4. **EVs**: Roughly how many households have electric vehicles? Do they charge at home?
5. **Heat**: Do homes use the original passive solar + thermal mass design, or have any heat pumps been added?
6. **Grid connection**: What is the DNO connection capacity (kVA or kW)? Is there a known transformer size? Is there a smart meter or half-hourly metering?

### About Energy Monitoring

7. **Do you have historical data?** Ideally: half-hourly demand, generation, import/export — even a month of data would be very useful.
8. **What monitoring systems are in place?** (CODA, Sunny Portal, smart meter IHD, etc.)
9. **Are you on a time-of-use tariff?** (e.g. Octopus Agile, Economy 7, or other?)

### About Appetite for a Pilot

10. **Would the community be interested in being a named case study?** (This strengthens grant applications, academic papers, DNO submissions.)
11. **Is there a community energy manager or technical lead** I could speak with for the data side?
12. **Would the community benefit from seeing the optimisation results?** (E.g. "if we added battery X, we'd save £Y per year and reduce peak demand by Z%")
13. **Any planned asset upgrades?** (New solar, batteries, heat pump retrofit?) — the tool can model "what if" scenarios.

---

## What I Can Offer in Return

- A **free simulation run** configured specifically for Hockerton
- A **written pilot report**: baseline vs optimised comparison, projected savings, transformer impact
- **Visual dashboard** they can explore in a browser (no installation needed)
- If data is available: **validated results** they can use in funding applications or publications
- **Scenario modelling**: "What happens if we add 3 more EVs?" or "What if we install community battery storage?"
- Attribution: Hockerton would be credited as the first real-world pilot site

---

## Potential Objections & Responses

**"We already optimise our energy use manually."**
> The system does continuous half-hourly optimisation across all assets simultaneously — something that's practically impossible to do manually, especially when factoring in varying carbon intensity and dynamic tariffs.

**"We're a small estate — is it worth it for 9 homes?"**
> Nine homes is actually ideal for a pilot — small enough to understand in detail, large enough to demonstrate multi-home coordination. The findings would be directly scalable to larger estates.

**"We don't want to share our data."**
> No problem. The simulation can run entirely on synthetic data calibrated to Hockerton's specifications. Real data would improve accuracy but isn't required. Any data shared would stay private and local.

**"How is this different from what our inverters already do?"**
> Individual inverters optimise one asset at a time (battery or solar). This system coordinates all assets across all homes simultaneously, with a shared goal of staying below the grid connection limit — which individual inverters can't see.

**"What would it cost to deploy for real?"**
> The simulation and dashboard are free, open-source tools. Real-time deployment (connecting to actual meters and sending control signals) would be Phase 7 of the roadmap — currently in planning. A pilot study using historical data costs nothing.

---

## The Pitch in One Paragraph

> "I've built a software platform that models estates like Hockerton — homes with solar, batteries, and EVs — and uses an optimisation algorithm to coordinate all the assets together. Rather than each home acting independently, the system treats the whole estate as a single unit, prioritising keeping total demand below the grid connection limit. I'd like to configure it specifically for Hockerton, run a simulation using your actual specifications, and produce a report showing projected savings and carbon reductions. It's entirely free, requires no hardware changes, and Hockerton would be the first real-world validation case — which could be useful for your own planning, and for any grants or publications."

---

## What Happens Next (Your Action Items)

- [ ] Share approximate solar capacity, battery storage, EV count, grid connection size
- [ ] Check if any historical half-hourly data is accessible (smart meter, inverter portal)
- [ ] Confirm whether a named case study / written report would be welcome
- [ ] Introduce me to any technical lead at Hockerton who manages energy systems
- [ ] Ask if there are upcoming infrastructure decisions (new assets, grid upgrade discussions) where modelling would be useful

---

## Background on the Technology (If Asked)

The system uses **Mixed Integer Linear Programming (MILP)** — the same class of mathematics used by national grid operators and large energy traders. It looks 48 hours ahead, considers all constraints (battery capacity, EV departure times, grid limits), and finds the mathematically optimal charging/discharging schedule. It runs on a standard laptop in under a minute for a 9-home estate.

It is **not** a black-box machine learning model — every decision is traceable, auditable, and explainable. This matters for regulatory conversations with Ofgem or National Grid ED.

---

*Document prepared February 2026 | AI Energy Orchestrator project*
