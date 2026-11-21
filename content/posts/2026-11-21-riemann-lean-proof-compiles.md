---
title: A Claude-assisted Riemann Hypothesis proof compiles in Lean, and a human proof
  of the generalized version appears
date: 2026-11-21
summary: Independent checkers say Levent Alpöge's Claude-assisted Lean proof of the
  Riemann Hypothesis compiles, while a separate human proof of the generalized version
  drew reported problems within hours. Also today, METR's time-horizon update, OpenAI's
  anti-distillation defenses, and Signal blocking AI screen reading.
tags:
- research
- safety
- models
sources:
- title: 'Levent Alpöge: remark on the Riemann Hypothesis'
  url: https://alpo.ge/remark.pdf
- title: 'TechCrunch: AI claimed a solution to the Riemann hypothesis, and a human
    did too'
  url: https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/
- title: 'Ravi Vakil: Hurried announcement, Alessandro Masullo GRH'
  url: https://math216.wordpress.com/2026/11/20/hurried-announcement-alessandro-masullo-grh/
- title: 'METR: Q4 2026 capability update'
  url: https://metr.org/blog/2026-11-20-q4-2026-capability-update/
- title: 'OpenAI: Combatting adversarial distillation'
  url: https://openai.com/index/combatting-adversarial-distillation
- title: 'Signal: Signal is serious about protecting your privacy'
  url: https://signal.org/blog/protecting-your-privacy/
score: 4.5
---

**The short version:** Claimed proofs of the Riemann Hypothesis and its generalized version appeared on the same day. One was found with Claude and its Lean code reportedly compiles, while the other was written entirely by humans and drew reported problems within hours.

## Riemann Hypothesis: one proof compiles, another draws objections

Anthropic mathematician Levent Alpöge [wrote](https://alpo.ge/remark.pdf), "I believe I have, working with Claude, discovered a proof of the Riemann Hypothesis." He released only a Lean formalization, a proof written so that software can check every step. Several participants in the Lean community chat, including MIT mathematician Andrew Sutherland, say they have confirmed that it compiles, [TechCrunch reports](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/). A readable human explanation isn't ready yet.

The same day, Ravi Vakil [announced](https://math216.wordpress.com/2026/11/20/hurried-announcement-alessandro-masullo-grh/) a proposed proof of the Generalized Riemann Hypothesis by Alessandro Maria Masullo, which "is all human, with no AI." About eight hours later, Vakil added that several people had reported problems with it, "identified with the assistance of different AI models."

Why it matters: the hypothesis is a Clay Millennium Prize problem with a million-dollar prize. A compiling proof settles whether each step follows. It doesn't settle whether the formal statement matches the real hypothesis, and no source checked here addresses that yet. AI played a part in both stories: it helped find Alpöge's proof, and AI models helped people find flaws in Masullo's.

## METR: agents handle tasks of up to 27 hours but trail human judgment

METR's [new report](https://metr.org/blog/2026-11-20-q4-2026-capability-update/) updates its "time horizon" measure. That is the length of a task, measured in how long a skilled human takes, that an AI agent can finish with 50% success. In March 2025 the best model managed about one hour. Now, "current public frontier models have an estimated time horizon of up to 27 hours" on METR's verifiable tasks, and horizons on the combined suites are doubling roughly every 3.6 months.

The update adds harder, open-ended tasks, including ones that test judgment, "the ability to make good choices in the absence of clear and fast empirical feedback." Here METR finds that "AI agents appear to have worse judgment than human experts." On verifiable coding work, by contrast, models often match or beat skilled humans.

Why it matters: this is one of the most cited measures of AI progress, and the gap tells you how much autonomy to give agents. METR is open about its uncertainty: human timing baselines back only 9% of its task-length estimates.

## OpenAI hardens its models against capability copying

OpenAI [described](https://openai.com/index/combatting-adversarial-distillation) its defenses against adversarial distillation, where someone trains a model on another model's outputs without permission. The result can copy the original's capabilities "without comparable protections." The main target is protected reasoning, the model's hidden chain of thought, which "can contain information the final answer leaves out."

The measures include training models to refuse extraction attempts, classifiers on inputs and outputs, and API changes that drop hidden reasoning when an earlier message is rewritten. They also include enforcement against networks of accounts, with weekly actions ranging "from thousands to tens of thousands of accounts." In OpenAI's red-team tests, attacks that pulled reasoning from an earlier request succeeded 54.0% of the time on GPT-6 Astra and 0.2% on GPT-6.2 Astra with the updated safeguards. OpenAI names DeepSeek and people associated with Moonshot AI in past extraction activity.

Why it matters: a distilled copy can carry a frontier model's skills without its safety limits. That makes protecting reasoning traces a security and policy question, not only a commercial one.

## Signal blocks AI agents from reading your chats

Signal [now blocks](https://signal.org/blog/protecting-your-privacy/) screenshots in its iOS 27 app to stop Siri AI's onscreen awareness from reading messages. On Android, it automatically turns on its "Screen security" setting when it detects this kind of access by Gemini Intelligence. Users can switch the protection off, but Signal warns that this "will potentially expose your (and your contacts') Signal content to these AI agents." It can't reliably block screenshots on macOS, and it calls the fix "incomplete," since other routes, such as access to the device's files, remain open.

Why it matters: assistants built into the operating system read whatever is on screen, which gets around the protection an end-to-end encrypted app relies on. In the post, Meredith Whittaker calls this "an existential threat to Signal". The company is asking Apple, Google and Microsoft for tools that let developers opt out.

## Worth watching

- Whether anyone confirms that the formal statement in Alpöge's Lean proof matches the Riemann Hypothesis, and whether the problems reported in Masullo's draft can be fixed.
- Whether Apple and Google give app developers a way to keep their apps away from OS-level AI agents.
