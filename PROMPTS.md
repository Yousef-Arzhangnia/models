# Prompts for the Upgrade 4 modelling project

Use one prompt per session. Do not paste the next one until the previous milestone report is approved.

## Prompt 1: kickoff (M0 and M1 only)

```
Read PROJECT_INSTRUCTIONS.md, CONTEXT.md, MODELS_ROADMAP.md and UI_SPEC.md first.

Start milestone M0 (setup) and then milestone M1 (analytical forward chain). Do not start or prepare any later milestone.

M0: create the package layout from the instructions and a params.yaml containing every value from CONTEXT.md, each with unit and source tag. Values that are TBD get a clearly marked placeholder. Build the tracker, the board (Home page) and one demo page as in UI_SPEC.md, and show that a demo run started from the command line updates the board live. Give me the exact commands to install and start it.

M1: build models 1, 5, 7 (simple), 8, 10, 11 (gain and noise only) and 12 as defined in MODELS_ROADMAP.md. Produce, for a 7 µm and a 12 µm uniform sphere (sound speed 1550 m/s as a placeholder):
- the ideal pressure pulse and its spectrum;
- the same pulse through today's chain (1.3 ns laser, 0.7 mm PMMA plus 13 mm water, 20 MHz transducer from the certificate, 13.6 dB + 27 dB, 500 MS/s 12-bit);
- the same pulse through the Upgrade 1 chain (0.5 ns laser, 0.3 mm water, 150 to 500 MHz transducer modelled from P1's 375 MHz unit, 40 dB LNA, 8 GS/s);
- single-shot and averaged SNR for both chains.

Build the six M1 pages listed in UI_SPEC.md section 6, and run every study through the tracker so it shows on the board.

Run every verification check listed for M1 and report pass or fail. If the bead data in reza/points is available to you, compare today's chain with it qualitatively.

Finish with the milestone report (template in the instructions), update the status table in MODELS_ROADMAP.md, list every TBD, and stop. Ask me before starting M2.
```

## Prompt template for every later milestone

```
Read PROJECT_INSTRUCTIONS.md, CONTEXT.md, MODELS_ROADMAP.md, UI_SPEC.md and the report of milestone <previous> first.

Decisions from the last review:
- <what I approved, changed or rejected>
- <new values to put into params.yaml, with tags>

Start milestone <Mx> only, as defined in MODELS_ROADMAP.md. Do not start or prepare any later milestone.

Finish with the milestone report, update the roadmap status table, list every TBD, and stop. Ask me before starting the next milestone.
```

## Prompt for a quick question inside a milestone

```
Stay inside milestone <Mx>. Answer this without changing the plan: <question>
```
