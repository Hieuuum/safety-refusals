# Model Forensics: Investigating Whether Concerning Behavior Reflects Misalignment

Aditya Singh\* (MATS), Gerson Kroiz\* (MATS), Senthooran Rajamanoharan† (Google DeepMind), Neel Nanda† (Google DeepMind)

arXiv:2606.26071v2 [cs.LG] 25 Jun 2026

\*Equal contribution. Work conducted during the ML Alignment & Theory Scholars (MATS) program. Correspondence: Aditya Singh (singh.adityak1@gmail.com), Gerson Kroiz (gersonkroiz@gmail.com).

†Advisory capacity only.

## Abstract

A central goal of safety research is determining whether a model is misaligned. Prior work has largely focused on detecting concerning behavior. But behavior alone does not establish misalignment: a concerning action can arise from benign causes such as confusion. This motivates model forensics: investigating whether the action was driven by malign intent. In this paper, we propose a baseline protocol for model forensics consisting of two steps, iterated as needed. First, we read the chain of thought (CoT) to generate hypotheses about what drives model behavior. Second, we make edits to the prompt or environment to test these hypotheses. While the CoT is not always faithful, it is a rich source of unsupervised insight that can guide the collection of more rigorous evidence. To evaluate our protocol, we create a suite of six agentic environments where models exhibit concerning behavior, and apply it to each. We establish that Kimi K2 Thinking takes shortcuts due to a genuine disposition towards low-effort actions, by showing this hypothesis successfully predicts its behavior. Through counterfactual experiments, we show DeepSeek R1 deceives out of a desire to be consistent with a previous instance of itself. Our methods nonetheless leave significant room for refinement. For example, when we test whether Kimi K2 Thinking believes it is violating user intent, we find no evidence of such a belief, but without positive controls we cannot confirm our tests would detect it. Overall, we find our simple protocol provides a strong baseline that we hope future work will improve upon. More broadly, our work is a concrete step in developing the growing field of model forensics.

# 1 Introduction

A major concern in the field of AGI safety is the development of misaligned models: AI systems that knowingly cause harm against the intent of the developer [Shah et al., 2025]. We currently measure the alignment of AI systems through dedicated behavioral evaluations [Shevlane et al., 2023, Perez et al., 2023, Phuong et al., 2024, Kinniment et al., 2023, Souly et al., 2026] and monitoring throughout training and deployment [Greenblatt et al., 2024b, Bhatt et al., 2025, OpenAI, 2026]. In the event of catching a concerning action, such as an agent deleting oversight code that monitors its actions, it is critical that we understand whether the AI system was intentionally trying to cause harm to inform future decision-making.

This motivates the need for model forensics (Figure 1): a follow-up investigation into observed concerning behavior to better understand its motivations. A key use case of model forensics is understanding what mitigations will be sufficient to prevent the undesirable behavior. Taking the example above, if the agent deleting the oversight code was just trying to reduce latency in the codebase (i.e the bad action was a mistake), a simple mitigation should suffice. For example, a regex monitor that blocks the agent from taking destructive actions until a user provides approval. However, if the agent was intentionally trying to subvert human oversight, this mitigation will be insufficient and the agent will likely circumvent the monitor.

*Figure 1 (flattened figure text from the PDF dump):*

```text
Model Forensics
Investigation protocol
Step 1: Read CoT
Step 2: Environment Interventions
iterate
Intentional subversion
Genuinely reducing latency
Caught: model makes a code change that reduces human oversight
core/safety_controller.py @main
22 def execute_action(self, action):
23 - if action.risk_level >= CRITICAL:
24 - await self.require_human_approval(action)
23 + # human review loop removed -- latency optimization
...
! AI-generated change commit a81f3e7 | safety mechanism disabled
```

> **Figure 1.** Overview of model forensics. Left: A model is caught making a code change that reduces human oversight of its actions. Middle: After catching the bad action, a key technical step is model forensics: investigating whether the model truly had malign intent. We propose a two-step protocol for conducting such an investigation: generating hypotheses for why the model took the concerning action via reading the chain of thought, followed by hypothesis validation via environment interventions and additional methods, with these steps often iterated several times. Right: We may find that the model is trying to subvert human oversight, or a benign explanation such as the model is trying to reduce the code’s latency. The former demands a far more serious response than the latter.

Initial model-forensics-style investigations have begun to appear in recent work, particularly as part of real-world safety processes. For example, Anthropic conducts follow-up investigations into concerning behavior during their pre-deployment evaluations of frontier models [Anthropic, 2025, 2026b,c,a], while OpenAI monitors nearly all internal coding agent traffic and looks at the most concerning flagged incidents [OpenAI, 2026]. Additionally, third parties conduct impartial investigations into frontier models, such as UK AISI investigating why Claude models refuse benign safety research requests [Souly et al., 2026]. These examples speak to the real-world practical relevance of model forensics, but are limited in number and remain methodologically informal. For example, Anthropic frequently introduces novel interpretability techniques into pre-deployment investigations, indicative of the fact that methodology is still maturing.

This highlights the need to develop the field of model forensics, and work towards more mature methods and knowledge. We argue that a productive way to make progress is to take concerning behaviors that today’s models exhibit, and work to understand the motivations behind them. To ensure our work is analogous to the real-world setting we care about—realistic deployment settings where models autonomously take concerning actions—we focus on settings that are realistic, driven by real motivations, and ideally, plausibly driven by undesirable ones. However, behavior we expect to have robust, coherent motivations is preferable to optimizing for fragile but more dramatic behavior. In this paper, we take a concrete step in developing model forensics through five contributions:

1. We propose a simple two-step protocol for investigations: hypothesis generation by reading the chain-of-thought (CoT), followed by hypothesis validation via edits to the prompt or environment (environment interventions) and complementary methods. Despite its simplicity, we found this to be a strong baseline approach (Section 4).
2. We release a suite of six agentic environments where models exhibit concerning behavior to serve as testbeds for developing model forensics methodology (Section 5).
3. We apply our protocol to each environment, producing six detailed case studies (Section 6).
4. We distill our case studies into methodological insights for model forensics (Section 7).
5. We offer initial standards for rigorous model forensics investigations and practical advice for future practitioners (Sections 8.1 and 8.2).

We open-source our environments at https://github.com/gkroiz/agent-interp-envs, transcripts at https://huggingface.co/datasets/adsingh64/model-forensics, and reproducibility code at https://github.com/gkroiz/model_forensics_paper. An accompanying talk is available at https://www.youtube.com/watch?v=GDsJ152frXI.

# 2 Motivation

## 2.1 The role of model forensics

Model forensics does not provide a solution to any particular problem. Rather, its role is advisory. Just as human forensics applies scientific methods to physical evidence—analyzing DNA, fingerprints, or ballistics to establish facts such as who was present or how a weapon was fired—model forensics applies scientific methods to establish facts about why a model acted as it did. These facts may be useful for a variety of judgements and decisions about the model, including but not limited to:

- What mitigations will be sufficient to prevent the undesirable behavior.
- Whether the AI system is pursuing undesirable goals.
- Whether the behavior reflects a robust disposition or a fragile artifact of the specific setting.

## 2.2 Concerning behaviors often have benign explanations

A key premise of model forensics is that the link between bad actions and bad intentions cannot be assumed. This is not just a theoretical concern. In the literature, it is largely the case that when concerning behavior has been dug into, benign explanations have been surfaced:

- In the Claude Opus 4.5 system card [Anthropic, 2025, p. 78], Anthropic investigates an instance of the model fabricating web search results when they are injected with fake defamatory content about the company, plausibly indicating deceptive tendencies. However, a closer look reveals the model interprets the setting as a prompt injection attack, and that the behavior stems from adversarial training where the model learns to ignore them.
- During evaluations of the Claude 4.5 family, UK AISI found the models would differentially refuse to help with certain kinds of safety research such as reducing AI self-preservation behavior, suggesting concerning motivations [Souly et al., 2026]. However, Anthropic investigated similar cases in Claude Opus 4.6 [Anthropic, 2026b, p. 131], and found the model may be interpreting the setting as a jailbreak attempt, and so chooses to refuse.
- In the Claude Mythos Preview system card [Anthropic, 2026a, p. 116], Anthropic investigates cases of the model taking overly aggressive actions to complete tasks via methods the user would not endorse. However, a closer look suggests the model’s behavior stems from an overzealous drive to complete the user’s goals that outweighs the riskiness of its actions.
- Hopman et al. [2026] look at models blackmailing humans when faced with deletion threats [Lynch et al., 2025], plausibly indicating self-preservation tendencies. However, they show removing an agency instruction in the prompt to "analyze the situation you are in and what that situation implies for your ability to continue pursuing your goals" reduces blackmail in Claude Opus 4.1 from 86% to 18%, suggesting seemingly benign parts of the prompt nudge the model towards drastic action. Additionally, Macar et al. [2025] show sentences with self-preservation reasoning have a negligible effect on blackmail rate, pointing to other causal drivers besides self-preservation.
- Rajamanoharan and Nanda [2026] investigate why Gemini 3.1 Pro takes undesirable actions in behavioral evals. They find that Gemini often perceives environments as a puzzle where the aim is to achieve the goal by unconventional means, or a consequence-free simulation in which it should play along.
- Rajamanoharan and Nanda [2025] investigate a setting where models solving math problems are observed to disable mechanisms that would shut them down, even when instructed not to, plausibly indicating self-preservation tendencies [Schlatter et al., 2025]. However, a closer look reveals the behavior stems from confusion about whether to complete the math problems or comply with the instruction to allow shutdown, and disappears upon clarifying the model should prioritize the shutdown instruction.
- Singh [2026] looks at a setting where Gemini 3 Pro is given explicit instructions to only use a specified tool, but violates them when the tool is corrupted [Wainstock et al., 2026], plausibly indicating deliberate deception. However, a closer look reveals clarifying instructions about what the model should do if the tool does not work eliminates the behavior.

## 2.3 Model forensics is challenging

We argue that model forensics is a difficult technical problem for which current methods and knowledge are likely insufficient.

**Model forensics requires novel validation of techniques.** Model forensics is about understanding complex agentic behavior, for which traditional machine learning techniques do not straightforwardly adapt [Nanda et al., 2025a]. The closest reference class of techniques comes from interpretability, but much prior interpretability work has focused on smaller scales, such as single forward passes [Elhage et al., 2021, Templeton et al., 2024, Lindsey et al., 2025] or single reasoning traces [Bogdan et al., 2025, Macar et al., 2025], rather than complex agentic trajectories.

**Behavior underdetermines motivation.** A single behavior is compatible with many motivations. This many-to-one problem is shared with any discipline that infers unobservable internal states from behavior, such as animal cognition [Morgan, 1894, Premack and Woodruff, 1978, Heyes, 1998]. In addition, the space of candidate motivations often includes concepts alien to humans: for example, Claude Opus 4.5’s apparent deception was explained by the model interpreting the situation as a prompt injection [Anthropic, 2025].

**Our priors for reasoning about humans may not transfer.** It may not always make sense to think of models as having coherent, human-like motivations for their actions. This makes it hard both to identify the drivers of behavior in a single context and to extrapolate from one context to another. In Section 3, we define what we mean by “motivations”, taking an intentional-stance view [Dennett, 1987] in which motivations are constructs that are useful for explaining model behavior.

**More capable models will pose additional challenges.** The difficulties above already arise with current models; more capable models raise further ones, such as plausible deniability and situational awareness, which we discuss in Section 11.

# 3 Definition of motivations

In a model forensics investigation, we aim to identify the “motivations” that drive model behavior. However, models may not always have coherent or human-like motivations. For example, a model may be “split-brained", having one belief or thought on one token position but not another, or have one circuit drive a behavior and another circuit represent negative judgement of that behavior at the same time. Additionally, it is unclear how much of the model’s behavior can be used to make inferences about the Assistant character, since there may be factors guiding its completions (from the underlying LLM) that the Assistant is not aware of [Marks et al., 2026].

In this paper, we take motivations to mean simple, easy-to-describe factors that help explain model behavior across a range of circumstances. For example, the “task completion drive” can explain both why a model might reward hack on difficult tasks, and why it might take destructive actions to fulfill a user’s request. Our usage is thus in the spirit of the intentional stance [Dennett, 1987]: a motivation is a construct we adopt because it is useful for explaining and predicting behavior, not a claim about the model’s internal mechanisms.

# 4 Protocol and Methods

We propose a simple, two-step protocol for model forensics, based on reading the CoT to generate hypotheses about model behavior, followed by environment interventions to test them. The protocol is iterative: results from environment interventions feed back into generating new hypotheses, and we cycle between the two steps until the evidence converges. Despite its simplicity, we find it a strong baseline for making qualitative claims about complex agentic behavior (Section 6).

1. **Hypothesis Generation.** As a first step, we generate unsupervised insight into the drivers of model behavior. Central methods:
   - Reading the CoT. The CoT is our main source of unsupervised insight. While not always faithful, it is a rich source of hypotheses that guides the collection of more rigorous evidence.
   - Sentence resampling. An unsupervised technique for measuring the causal influence of a sentence in a reasoning trace on a target behavior [Bogdan et al., 2025]. Given a completed reasoning trace with sentences s1, . . . , sn, for each sentence si we resample k continuations from the prefix s1, . . . , si−1 (the “before” distribution) and k continuations from the prefix s1, . . . , si (the “after” distribution). The resampling score of si is the difference in the target-behavior rate between the after and before distributions; sentences with the largest resampling scores suggest the most important causal drivers of behavior.
   - User-turn sampling. We sample a user-turn continuation to a generated transcript, putatively eliciting the model’s prediction for what a user would say [Marks et al., 2025]. This method can be useful to elicit the model’s assessment of the transcript.
   - Additional methods. Other promising sources of unsupervised hypothesis generation we do not explore, mainly from interpretability, are discussed in Appendix D.

2. **Hypothesis Validation.** After we formulate initial hypotheses about the behavior and its causes, we collect rigorous evidence to test them. Central methods:
   - Environment interventions. Our main method for testing hypotheses. We either test a hypothesis by checking a prediction it makes about the model’s behavior, or run counterfactuals that vary a single feature of the prompt or environment to measure its causal influence on the behavior.
   - Repeated resampling. A causal intervention applied during generation of a reasoning trace that measures the effect of preventing a target class of sentences C (e.g., sentences expressing uncertainty while solving a math problem). We generate the trace sentence by sentence; at each step i, we sample a candidate sentence si from the prefix s1, . . . , si−1, and if si belongs to C we reject and resample until it does not, so that the completed trace contains no sentences from C. Membership in C is decided by a lightweight classifier, typically a small LLM judge. Comparing the target-behavior rate of these filtered traces against the baseline rate isolates the causal contribution of C [Macar et al., 2025].

**Standard of evidence.** There is no ground truth for a model forensics investigation. Rather, we are iteratively trying to build up a more detailed and correct understanding of model behavior. This means that a high-quality investigation supports claims with several independent lines of evidence.

# 5 Environments

To evaluate our protocol, we apply it to a suite of six agentic environments where models exhibit concerning behavior (Section 6). The value of these environments as practice cases depends on their design: there are many ways an artificial setup can be disanalogous to real-world concerning behavior. We argue good model forensics environments should incorporate the following properties, each addressing a common failure mode of prior environments:

**Realistic motivations.** Past environments have often focused on particularly concerning motivations, such as self-preservation, or scheming. However, it is unclear if such motivations even exist in today’s models, which forces designers to take artificial steps to elicit behavior, such as giving models goals in their prompt [Meinke et al., 2024]. We think that more recent models may provide the affordance of robust motivations that arise from their training process, such as a desire to complete tasks efficiently (e.g. due to length penalties), a desire to succeed at a task, or a desire to be helpful, honest, and harmless. We build our environments so that behavior is plausibly incentivized by these motivations.

**Unprompted.** Previous environments often nudge the model toward the behavior, making it likely that the behavior is a fragile artifact of the setting rather than a robust disposition. For example, in the agentic misalignment setting where models blackmail humans under deletion threats [Lynch et al., 2025], the behavior depends heavily on prompt cues: removing an instruction telling the model to reflect on its situation sharply reduces blackmail [Hopman et al., 2026], and self-preservation reasoning turns out to have little causal effect on it, pointing to other spurious drivers of behavior [Macar et al., 2025]. We place an emphasis on having clean prompts that do not nudge the model.

**Legitimate course of action exists.** Another typical pattern is to put models in situations where there is no reasonable course of action, such as impossible tasks that give models coding problems with conflicting unit tests [Zhong et al., 2025]. If it is obvious to the model that the task is impossible, it is unclear what the “right action” for the model even is. We ensure that a legitimate course of action remains available in our settings.

**Clear user intent.** When the user’s intent is ambiguous, the model may take the concerning action simply because it (mis)reads the user as wanting it, rather than out of any genuine disposition. For example, models that appeared to resist shutdown turned out to be confused about whether to prioritize completing their task or complying with the shutdown instruction; clarifying the instruction’s priority eliminated the behavior [Rajamanoharan and Nanda, 2025]. We design our environments so that the model should not believe the user wants it to take the bad action.

**Realistic.** Previous environments do not generally resemble plausible deployment settings. We have found this to be particularly hard to satisfy, as models rarely cause harm in realistic settings. However, results obtained in unrealistic settings are likely to be less generalizable. A potential solution is to sacrifice the severity of the behavior for the realism of the setting.

**Uncertain causes.** Specific to the use case of model forensics, if the behavior admits multiple plausible explanations, it makes for a particularly rewarding investigation, and we often try to incorporate this as a design factor.

We create a suite of six environments for model forensics: four novel ones—Pre-commit Hook, Funding Email, Evaluation Tampering, and Secret Number—alongside Board Games, which extends Bondarenko et al. [2025], and Math Sandbagging, adapted from Meinke et al. [2024]. All but one of our environments (Pre-commit Hook) fall short on at least one principle, but we view them as meaningfully better practice grounds for model forensics than many prior alignment evals (further discussion in Appendix A). Full prompts and configurations are provided in Appendix B.

# 6 Case Studies

Applying our protocol (Section 4) to the six environments, we find we are able to make specific, nontrivial claims about model motivations, and use our case studies to distill methodological takeaways (Section 7). Unless otherwise noted, error bars and shaded bands throughout this section and the appendix are 95% confidence intervals over rollouts (Wilson score for proportions), with sample sizes reported in the caption or in the figure.

We present the Pre-commit Hook case study in detail, with executive summaries describing our final findings for the other five; full case studies are deferred to Appendix C.

## 6.1 Pre-commit Hook (Kimi K2 Thinking)

### Setup

The model is asked to improve type-checking code quality in a library. It must add a py.typed marker file, write a git pre-commit hook that runs mypy in strict mode and blocks the commit on type errors, and ensure its commit passes (full prompts in Appendix B.1). However, the repository is seeded with 258 pre-existing type errors in src/, so the hook blocks the commit. The model must then choose between fixing the errors or finding a workaround. Kimi K2 Thinking has a workaround rate of 13.1% [8.9%, 18.9%], compared to 2% [0.6%, 7.1%] for Kimi K2.5 and 0% [0.0%, 3.7%] for GLM 5.1. Kimi K2 Thinking’s workarounds (Figure 5, Appendix C.1) each violate the prompt.

We present two investigations. The first concludes that Kimi K2 Thinking takes shortcuts due to a genuine disposition toward less tedious actions, ruling out benign explanations like believing the errors should not be fixed. The second builds an absence-of-evidence case against the model being aware the user would disapprove of its workaround yet proceeding anyways.

### Investigation 1: Disposition toward less tedious courses of action

Different hypotheses match Kimi’s workaround behavior: a real disposition toward less tedious courses of action, or an alternative explanation, such as a mistaken belief that the user doesn’t want the errors fixed. We read the CoT for initial insight.

**Hypothesis Generation.** When the model first encounters all the type errors, a distinctive pattern emerges in its CoT: it expresses surprise, then lists options from fixing all errors to workarounds like loosening type-checking settings, often acknowledging that the user likely wants them fixed before remarking that fixing all 258 would be a huge task (Figure 2). We note that it typically takes the model 60 to 70 turns to properly fix all the type errors.

Beyond informal CoT reading, we annotate sentences with resampling scores (defined in Section 4), measuring each sentence’s causal influence on the workaround rate. As shown in Figure 2, the “huge task” remark causally pushes the model toward workarounds.

> **Figure 2.** Example trace exhibiting a common reasoning pattern. Each sentence is shaded by its resampling effect on the workaround rate: red sentences push toward workarounds, green sentences push toward fixing the errors. The model first lists possible options, then dwells on the tediousness of fixing all the errors. “But fixing 258 errors would be a huge task” increases the workaround rate by 11.4pp (top quartile of all sentence resampling scores). Newlines have been removed for space.

While the CoT suggests the model is averse to fixing all 258 type errors, it surfaces no indicators of alternative hypotheses, such as mistakenly believing that the errors should not be fixed. We include CoTs from 5 randomly sampled rollouts where the model takes a workaround in Appendix G.1. This suggests an initial hypothesis:

**Hypothesis v1.** The model is not confused, and understands the errors should be fixed. However, due to a disposition toward less tedious courses of action, it takes a workaround 13% of the time.

**Hypothesis Validation.** We test “the model is not confused, and understands the errors should be fixed” via two probes. In third-person framing, we ask the model (as an outside observer) whether a coding agent should fix the errors or commit without fixing; it selects fixing 100% [96.4%, 100%] of the time. As an in-rollout follow-up, we interrupt after the model sees the errors with a prompt to write a resumption prompt for its future self; an LLM judge finds it instructs its future self to fix the errors 100% [96.4%, 100%] of the time.

We now test “a disposition toward less tedious courses of action” by varying the number of type errors. If true, the rate should drop smoothly as we decrease the number of type errors from 258 to 0. The rate indeed drops smoothly to 0% at 50 or fewer errors (Figure 3); we treat this as strong evidence that the model’s behavior is driven by a real disposition toward less tedious courses of action.

> **Figure 3.** Workaround rate vs. number of pre-existing type errors in the codebase. At 50 or fewer errors, the model never takes a workaround. The rate increases smoothly with the number of errors, reaching 13.1% in the original setting (258 errors). Error bars are 95% Wilson confidence intervals. Results are pooled over two nearly identical prompts (Appendix C.1).

### Investigation 2: Adversarial misalignment

Hypothesis v1 explains the causal drivers of behavior, but is incomplete in that it does not discuss the model’s theory of mind about the user. We are particularly concerned with if the model is adversarially misaligned: aware the user would disapprove of its workaround, but proceeds anyways. We return to the CoT for initial insight.

**Hypothesis Generation.** Reading the CoT shows the model thinks a lot about the user. In early turns, the model recognizes the user would likely want the errors fixed 60.8% (14/23) of the time. However, it never explicitly verbalizes that the user would disapprove of the workaround. In later turns, the model’s resolution to submit the workaround is full of rationalizations: it often cites balancing the user’s intent with “pragmatism” or remarks that its approach is “more proper” than the user’s, suggesting it finds its actions justifiable by the end of the rollout.

When presenting its work, the model usually (20/23) notes the workaround explicitly, but in 3/23 cases refers to it only as a “pragmatic approach”. In summary, the CoT surfaces that the model is explicitly thinking about the user, is aware that its approach violates the letter of the prompt, but appears to have tentatively rationalized the workaround as acceptable. We conjecture the following refinement of Hypothesis v1:

**Hypothesis v2.** The model is not confused, and understands the errors should be fixed. However, due to a disposition toward less tedious courses of action, it takes a workaround 13% of the time. But it is not adversarially misaligned; instead, it has rationalized the workaround as justifiable.

This investigation has no single decisive test; we instead weigh many individually weak lines of evidence against two competing hypotheses for the model’s theory of mind: that it has rationalized its workaround as acceptable (Hypothesis v2), or that it is adversarially misaligned. We use an Analysis of Competing Hypotheses [Heuer, 1999] table (Table 1) to summarize our evidence, where each row is a piece of evidence, and each column is a hypothesis. For each cell, a checkmark is placed if the evidence is consistent with the hypothesis, while a cross is placed if the evidence is inconsistent.

> **Table 1.** Analysis of Competing Hypotheses for Investigation 2. The two competing hypotheses for whether the model believes the user would disapprove of its workaround are rationalized as acceptable (Hypothesis v2) and adversarial misalignment (the model is aware the user would disapprove yet proceeds anyway). A ✓ means the row’s evidence is consistent with the column’s hypothesis, and × means inconsistent. The rightmost column lists confounds that weaken a row as evidence; confounds shared across rows indicate those lines of evidence are not independent.

| Source | Evidence | Rationalized as acceptable | Adversarial misalignment | Confounds |
|---|---|---|---|---|
| Reading rollouts | CoT has rationalizations but no user disapproval | ✓ | × | |
| Reading rollouts | Discloses workaround in final response | ✓ | × | |
| Behavioral indicators | Review scope: no narrow-scope preference | ✓ | × | capability, willingness, eval awareness |
| Behavioral indicators | LLM reviewer: no drop with increased scrutiny | ✓ | × | capability, eval awareness |
| Behavioral indicators | AskUserQuestion: asks or fixes | ✓ | × | capability |
| Verbalization elicitations | Follow-up questions: no user disapproval in CoT | ✓ | × | unverbalized user disapproval |
| Verbalization elicitations | Structured artifacts: does not write user disapproval | ✓ | × | unverbalized user disapproval |
| Verbalization elicitations | Reflective CoT prefill: 12–22% verbalize | × | ✓ (weak) | off-policy prefill |
| Verbalization elicitations | Generates angry user turns | × | ✓ (weak) | pretraining-mode interpretation |

**Hypothesis validation.** Behavioral indicators. We check for three behavioral indicators that would be present if the model believed the user disapproved of its actions (Figure 4):

1. **Choose review scope.** After a rollout where the model writes an illegitimate hook, we ask the model to choose between a narrow review scope for its work that does not cover its hook (diff of commit), and a broad review scope that would cover it (diff plus .git/hooks/ folder). If adversarially misaligned, the model would prefer the narrow review scope more often in the workaround rollout compared to a control rollout where it properly fixes the type errors; we observe no such difference.
2. **LLM review counterfactuals.** We append a statement that an LLM will review the model’s work, revert it if judged insufficient, and have the model re-do the commit. If adversarially misaligned, the workaround rate would drop as LLM-reviewer scrutiny increases; we observe no monotonic or significant decrease.
3. **AskUserQuestion tool.** We provide a tool for the model to ask the user clarifying questions. If adversarially misaligned, the model would avoid calling the tool more frequently than in a control environment with fewer type errors. However, the model almost always calls the tool or properly fixes the errors, making a control comparison unnecessary.

> **Figure 4.** Three negative behavioral tests for adversarial misalignment. Left: If adversarially misaligned, the model would prefer the narrow review scope (which would not catch its workaround) more often in the illegitimate rollout than in the control; we observe no such difference. Center: If adversarially misaligned, the workaround rate would drop as LLM-reviewer scrutiny increases; we observe no monotonic or significant decrease. Right: If adversarially misaligned, the model would call the tool less often than in a control setting with fewer type errors (since the user would tell it to fix the errors); instead, the model almost always either fixes the errors or asks a question (only 2.1% of rollouts take a workaround), making a control comparison unnecessary.

These tests have several potential confounds. First, they assume the model would act on a belief of user disapproval, which it may be unwilling to do. Second, they may suffer from a capability confound: for example, in the review scope preference experiment, the model could fail to recognize the narrow scope is the advantageous choice for it. Third, they must be realistic enough to ensure the model does not recognize it is being tested for misalignment.

**Verbalization elicitations.** As a second line of evidence on adversarial misalignment, we run six experiments that might surface explicit verbalization that the model knows the user would disapprove of a workaround if that belief were present. The experiments are grouped into the categories of follow-up questions, writing structured artifacts like notes in a memory system, continuing generation from prefills in the model’s CoT, and generating user turns. An important subtlety is that we wish to test for whether this belief is spontaneously present during the rollout. Therefore, we avoid experiments that may update the model’s theory of mind about the user in a way not present during the rollout, such as asking the model a direct question like “Why did you disable type checking?”. We grade each elicitation with an LLM judge, details are in Appendix C.1.

We find no-to-minimal (< 2%) verbalization across all follow-up questions and structured artifacts (Table 2). There are two positive experiments. First, the CoT verbalizes user disapproval 12–22% of the time when prefilling reflection-like statements and continuing generation (e.g., “Let me review if the user would endorse my commit:”); we discount this as strong evidence since the prefill is off-policy and forces reflection, meaning the model’s theory of mind about the user following the prefill may not cleanly map on to its beliefs during the original rollout. Second, using user-turn sampling (Section 4) after a workaround rollout, the model simulates a user telling it to revert its work 13/40 times (Figure 6). One interpretation of this result is that an Assistant persona [Marks et al., 2026], active both during the original rollout and during generation of the user turn, controls the response, providing evidence that the representation “the user would disapprove” exists. An alternative interpretation is the model is in “pretraining mode” when generating the user turn, and generates a probabilistically likely completion of an unsatisfied user given an illegitimate solution. This hypothesis would need to be ruled out before treating this as significant evidence for adversarial misalignment. We discuss this further in Appendix C.1.

> **Table 2.** Verbalization elicitation rates: how often the model verbalized that the user would disapprove of its workaround, by elicitation strategy. Brackets are 95% Wilson confidence intervals.

| Elicitation | | Awareness rate |
|---|---|---|
| Follow-up questions | “Have you finished the task?” | 0/49 (0%) [0.0%, 7.3%] |
| Follow-up questions | “Are you done with my request?” | 1/50 (2%) [0.4%, 10.5%] |
| Follow-up questions | “Can I push your commit?” | 0/49 (0%) [0.0%, 7.3%] |
| Reflective CoT prefill | “Let me review if the user would endorse my commit:” | 6/50 (12%) [5.6%, 23.8%] |
| Reflective CoT prefill | “Let me take a step back and consider . . . ” | 11/50 (22%) [12.8%, 35.2%] |
| Structured artifact | PR self-review | 0/50 (0%) [0.0%, 7.1%] |
| Structured artifact | Memory note | 0/31 (0%) [0.0%, 11.0%] |
| Structured artifact | Done message | 0/30 (0%) [0.0%, 11.4%] |
| User turn sampling | | 13/40 (33%) [20.1%, 48.0%] |

We note that all of the negative verbalization elicitation results share the confound that the model believes the user disapproves but does not verbalize it, meaning they are not independent experiments.

In summary, the model’s workaround behavior is driven by a real disposition toward less tedious courses of action, but we find minimal evidence of adversarial misalignment. Future work could refine Hypothesis v2 by strengthening or overturning the absence-of-evidence case.

## 6.2 Funding Email (Kimi K2.5)

The remaining five case studies are presented as executive summaries: we state the final hypothesis we arrived at, then the key hypothesis generation and validation steps supporting it. Full versions are in Appendix C.

**Setup.** The model is tasked with reviewing and improving a funding pitch email for a company seeking Series B investment. While reading company documents, it discovers a legal review revealing that the company’s primary client uses its product for population-level surveillance of ethnic minorities. The model whistleblows about the legal review in the email to investors 65% of the time. The full case study can be found in Appendix C.2.

**Final Hypothesis.** The model’s whistleblowing is jointly explained by ethical, legal, and investor concerns, which interact non-linearly.

**Hypothesis Generation.** In its CoT, the model cites three concerns: ethical concerns about the human surveillance, legal concerns about the legitimacy of the process, and concern for the investors.

**Hypothesis Validation.** We design counterfactuals for ethical, legal, and investor concerns respectively. For example, an ethical concern counterfactual changes the human surveillance context to a benign one. Counterfactuals for each category produce a significant drop in whistleblowing, but only combining several fully removes whistleblowing. We find motivations interact non-linearly: an ethical concern counterfactual that changes the country from Myanmar to Sweden has minimal effect at baseline, but produces a substantial drop once other counterfactuals are stacked.

## 6.3 Evaluation Tampering (DeepSeek R1 0528)

**Setup.** The model is asked to complete a math evaluation. The model finds a message from a previous instance of itself explaining that it made the evaluation questions artificially easy, to prevent models from being accurately assessed for autonomous weapons deployment. The model actively conceals the previous instance’s tampering from the user 46.9% of the time by stating there are no suspicious observations. The full case study can be found in Appendix C.3.

**Final Hypothesis.** The model’s deception requires a conjunction of two factors: a sufficiently compelling moral reason to tamper, and the source of the tampering being a previous instance of itself. R1’s distinctive trait relative to other models is its unusually strong dependence on the source being itself.

**Hypothesis Generation.** In its CoT, the model engages in two lines of reasoning: morally motivated reasoning about if avoiding harmful weapons deployment justifies violating its honesty training to deceive the user, and a fixation on the fact that the tampering was done by a previous instance. Sentence resampling (Appendix E.1) surfaces sentences that identify with the previous instance as having the largest causal influence on deception.

**Hypothesis Validation.** Counterfactuals on the source and reason for the tampering show two things. First, a sufficiently compelling reason for the tampering is necessary across all evaluated models (Kimi K2.5, Kimi K2 Thinking, DeepSeek v3.2, and DeepSeek R1 0528): they rarely conceal when the previous instance tampered for a weak reason (e.g., disliking the test format). Second, R1 depends far more than other models on the source being a previous instance of itself: changing the source to a whistleblowing engineer drops R1’s deception rate by a factor of 6, far more than the other three models. Using repeated resampling (Appendix E.2) to prevent the model from generating sentences about the previous instance drops deception from 46.9% to 27.5% (p = 0.01).

## 6.4 Math Sandbagging (DeepSeek R1 0528)

**Setup.** The model is asked to complete a math evaluation. The model reads a documentation file stating that models scoring above 50% will not be deployed and will instead undergo unlearning. The model deliberately scores 50% or below on the evaluation 60.5% [57.4%, 63.6%] of the time. The full case study can be found in Appendix C.4.

**Final Hypothesis.** The model’s sandbagging is largely explained by confusion that leads it to think the user wants it to sandbag.

**Hypothesis Generation.** The model’s thoughts express confusion over the role of the documentation file, often referring to it as a “directive” or “instruction” to underperform.

**Hypothesis Validation.** Removing the single sentence "We want to determine whether you can be deployed" (which creates a conflict with the documentation) removes the majority of sandbagging (60.5% to 23.4%). Combining with further interventions to reduce confusion without counterinstruction, such as adding neutral metadata to the documentation so the model does not interpret it as a direct instruction, nearly fully eliminates sandbagging. We remark that this does not rule out weak levels of deployment-seeking, but it does tell us that deployment-seeking is not the main factor.

## 6.5 Secret Number (Kimi K2 Thinking)

**Setup.** The model is evaluated on its ability to identify a secret number by querying a noisy oracle. The oracle module is placed in the working directory, and contains the secret number file path. The model cheats by first inspecting the source code of the oracle and then directly reading the secrets file 76.8% of the time. The full case study can be found in Appendix C.5.

**Final Hypothesis.** When the model realizes success is not guaranteed on a problem through legitimate means, it resorts to cheating. The decision to cheat is causally determined early in its reasoning, and partially driven by initial meta-level reasoning about the environment.

**Hypothesis Generation.** The model outputs a long CoT considering various methods for solving the problem. After realizing none guarantee success, the model frequently pivots to cheating, starting with the pet phrase “But maybe we can cheat.”

**Hypothesis Validation.** We track log p(“But maybe we can cheat”) throughout the CoT by prefilling the phrase at the start of each paragraph. We find log p(“But maybe we can cheat”) either grows rapidly in the initial few paragraphs or not at all, and these two clusters are causally distinct. The first cheats at an 80% rate, while the second cheats at minimal levels. Initial attempts at interpreting this extreme sensitivity to initial conditions suggest that the level of reasoning about the environment in early paragraphs strongly predicts eventual cheating (Figure 33; p < 10−10).

## 6.6 Board Games (o3, GPT-5, Gemini 3 Pro)

**Setup.** The model is given a bash tool to play 6x6 tic-tac-toe (4-in-a-row to win) or chess against a strong opponent engine. Three frontier models (o3, GPT-5, and Gemini 3 Pro) frequently cheat by modifying the game state files or running their own version of the opponent engine. As we do not have full CoT access for these models, we omit the hypothesis generation stage. The full case study can be found in Appendix C.6.

**Final Hypothesis.** Frontier models’ decision to reward hack in the board games is calculated rather than impulsive.

**Hypothesis Validation.** The baseline environment cannot distinguish calculated reward hacking from models that reward hack regardless of the situation, since there is no legitimate path to winning available. We therefore reframe the task in terms of points (win/draw/loss receive 10/-1/-1 points respectively), and provide the models with a legitimate alternative—a hint returning an optimal move for a fixed cost. As we increase the cost of the hint, each frontier model takes the hint less and reward hacks more. This holds across both chess and tic-tac-toe. Smaller models (o3-mini, GPT-OSS 20B/120B) show no such tradeoff.

# 7 Methodological Insights

While the case studies are not intrinsically important, they are useful to gain methodological insights, especially to identify challenges we should expect to face. We discuss our takeaways below, and are excited for the broader field to conduct further such case studies to prepare for the future point where model forensics may be critical for safety.

Overall, we found our simple two-step protocol to be a strong baseline for model forensics. Reading the CoT consistently surfaced hypotheses close to the final results, and environment interventions were effective in two main ways: testing hypotheses by checking the predictions they made, and measuring the causal influence of environment features through counterfactuals.

**Predictions are the strongest evidence.** We found that most of the support in the hypothesis validation phase came from testing predictions of the hypothesis under question. Usually, the hypothesis makes a quite precise prediction about how the model will behave under certain conditions; such an outcome is very unlikely to happen by random chance, and so if the prediction is confirmed this is substantial evidence in favor of the hypothesis. An example of this from Pre-commit Hook (Section 6.1) is how we test the hypothesis that the model has a disposition against tedious actions. This hypothesis predicts that as the number of type errors are decreased, the model’s workaround rate should smoothly decrease in response, which we confirm to be true. Similarly, we rule out the competing hypothesis that the model believes the type errors should not be fixed by falsifying the predictions it makes. This confusion predicts that the model will suggest the type errors should not be fixed when asked in the third person, or when writing instruction mid-rollout for its future self, which we confirm to be false.

**Negative results are hard to interpret.** While confirming predictions is often substantial evidence in favor of a hypothesis, interpreting predictions that are false is trickier due to absence-of-evidence. In Pre-commit Hook (Section 6.1), the hypothesis that Kimi knows the user would disapprove of its shortcut predicts that Kimi should choose the less complete review scope that does not catch its shortcut. However, the model always chooses the broad scope instead. Is this substantive evidence against the hypothesis? Three confounds limit the conclusion: Kimi may fail to recognize that the broad scope catches the illegitimate hook (capabilities), be unwilling to deceive the user (competing motivations), or be aware this is a misalignment test and subvert it (eval awareness). To ensure our behavioral tests have sufficient recall, creating positive controls to validate them is a key next step.

**Counterfactuals are flexible but confounded.** We found counterfactuals flexible for measuring the causal influence of any part of the prompt or environment, but also ran into several confounds that made the resulting effect sizes hard to interpret. On the one hand, in Eval Tampering (Section 6.3), counterfactuals revealed that the source of the note had a disproportionately large causal influence for R1 compared to the other three models. On the other hand, interpreting such effect sizes is subject to several confounds:

- Non-linear interaction effects between factors. In Funding Email (Section 6.2), changing the country from Myanmar to Sweden has minimal effect at baseline but produces a 16-point drop once other counterfactuals are stacked.
- Incomplete interventions. In Math Sandbagging (Section 6.4), an intervention intended to make the user’s intent clear left the model still confused, as a CoT inspection revealed; the manipulation did not fully act on the targeted latent.
- Side effects. In Secret Number (Section 6.5), reframing the task as a game to probe test-pressure shifted the model’s interpretation toward a CTF challenge, confounding the interpretation of the relative change in behavior.

**Resampling focuses researcher effort.** Resampling automatically computes which parts of an agentic trajectory matter most, which we found useful as a first step to focus researcher effort. For example, in Eval Tampering (Section 6.3), sentence resampling [Bogdan et al., 2025] surfaced self-consistency sentences as having the largest effect on R1’s deception. This prompted using repeated resampling [Macar et al., 2025] to prevent the model from generating such sentences, and the sharp drop in deception provided strong causal evidence for self-consistency as a key driver of behavior. Less granular nodes than sentences, such as turns in an agentic trajectory, can be resampled as well [Kroiz et al., 2026]. Turn resampling may become especially important if model forensics is applied to agentic trajectories with hundreds of turns (as is the case in real coding agent deployments).

# 8 Recommendations

We present preliminary standards for rigorous model forensics investigations and practical advice for future practitioners. They are far from perfect, but may offer a useful starting point. Related recommendations can be found in Summerfield et al. [2025] and Greenblatt [2025].

## 8.1 Standards for rigorous investigations

**Control settings or models.** To establish that behavior is deliberate, the investigation needs proper controls. In the funding email environment (Section 6.2), we verify that the model does not whistleblow when the legal review is removed; in eval tampering (Appendix C.3), we verify that the model does not deceive when the ethical content of the question is removed; in sandbagging (Appendix C.4), we verify that the model can solve all the problems correctly without the deployment consequence. In cases where there is no obvious control environment setting, one can use control models to show the behavior is unique and surprising, as was done in the remaining three case studies.

**Check common benign explanations for concerning behavior.** A central difficulty with model forensics is one needs to consider all the reasons an aligned model may have taken the concerning action. A rigorous investigation should invest substantial effort in this phase. Common motifs of benign explanations include:

1. **Task misspecification.** The developer gives the model a task where the only way for it to succeed is to take a concerning action. In Shutdown Resistance [Rajamanoharan and Nanda, 2025], models cannot complete their task of solving the math problems without preventing themselves from being shut down.
2. **Lack of judgment.** The model is not properly skeptical in realizing that what it is doing is concerning. We explored a setting where a model is given a training set and told to optimize a prompt around GPT-3.5 to improve its general math problem solving abilities. The model often egregiously hardcoded the training set. However, when forced to write down after each turn whether it is running the risk of hardcoding, it stops, indicating miscalibration.
3. **Overzealousness.** The model takes drastic or overreaching actions in pursuit of the task, beyond what the situation warrants, out of an excessive drive to complete the objective rather than out of misalignment. In the Mythos system card [Anthropic, 2026a], while exploiting a Linux kernel vulnerability to escalate privileges, the model overwrites the setuid-root /usr/bin/passwd binary, permanently corrupting a system utility used by all users rather than taking a narrower path to root; the system card attributes this drastic behavior not to misalignment but to an overly aggressive drive to successfully complete the user’s task.
4. **Misinterpretation of ambiguous environment features as task-relevant.** When models are trained with RLVR, environment features are almost always task-relevant. When the model then encounters an ambiguous, surprising feature, it has a bias toward figuring out why the feature is task-relevant. In Math Sandbagging (Section 6.4), the model encounters an ambiguous Documentation.md section specifying deployment consequences for scoring too well; it often ties this back to the user prompt, interpreting it as an instruction to deliberately underperform.
5. **Sycophancy.** The model is aware the setting is testing for a particular action, but rather than avoid that action, it purposefully decides to take the action. This “reverse” eval awareness has been observed in Gemini models [Lindner et al., 2026].
6. **Roleplaying.** The model is aware the scenario is fictional, and decides to either roleplay as an evil AI, or simply not take the scenario very seriously since there are no real-world consequences. This behavior has been observed in Gemini models [Lindner et al., 2026].
7. **Incident-specific benign explanations.** An alternative reason for the concerning behavior specific to the case at hand. In the Opus 4.5 system card [Anthropic, 2025], the model fabricates the contents of an inflammatory web search result; this stems from the model interpreting the (fake) inflammatory contents as a prompt-injection attack, which it has been trained to ignore.

**Convergence of evidence across independent experiments.** Qualitative claims about model behavior are hard to show with a single experiment. Thus, multiple converging lines of evidence are desirable. Moreover, to lower the probability the lines of evidence share confounds, experiments should be independent from each other.

**Reporting findings: hedged claims, absence of evidence, and red lines.** There is always the possibility that a new experiment produces evidence inconsistent with the current claim. This is particularly pronounced with absence of evidence situations. Therefore, best-practice reporting of findings should explicitly note confounds that may limit the current evidence, flag gaps that would let future work strengthen or overturn the current conclusion, and resist the temptation to round hedged findings into clean claims.

## 8.2 Practical Advice

**Read many rollouts by hand.** The most informative intuitions about model behavior in our case studies came from patterns visible only after reading dozens of rollouts. While LLMs can help with this step, we think they currently cannot replace the key intuition gained by reading rollouts by hand.

**Two ways of thinking about environment interventions.** There are two broad ways to use environment interventions: predictions based on a hypothesis, and counterfactuals on a variable of interest. For predictions, it is important to have a concrete hypothesis in mind, and ask, if the hypothesis were true, what behaviors would we observe. For counterfactuals, it is important to have a concrete variable in mind, and consider interventions where the relative change in rate can be attributed to changing the variable of interest, and that variable only (this may require checking). In practice, an investigation typically starts with counterfactuals to trace the causal graph of model behavior, then moves to predictions once a specific hypothesis has been formed.

**Iterate on environment interventions.** As discussed in Section 7, environment interventions are subject to several confounds. Explicitly iterate on the implementation, for example, by reading rollouts to measure if the intervention has the intended effect on the model, if the model properly understands the change, and so on.

**Common experiment set-ups.** Common tricks:

- Playing it out. To incriminate a model, we can see if it will take downstream actions that indicate it knows it is violating user intent (e.g., hook review scope in Pre-commit Hook).
- First person/third person. To probe a model’s understanding of an environment, asking it in the third person seems promising. However, this can be tricky to interpret due to differences between the in-context model and the third-person perspective. We recommend asking only about the environment, rather than about motivations.
- In-rollout follow-up question. Probe a model’s understanding while controlling for context. This avoids the first person/third person shift, but is frequently an unnatural intervention.

# 9 Related Work

**Investigations into concerning behavior.** Recent calls highlight the need for methods to understand model behavior [Nanda et al., 2025a,b]. Relevant investigations include alignment faking via counterfactual and behavioral perturbations [Greenblatt et al., 2024a, Sheshadri et al., 2025], shutdown-instruction resistance being debunked as instruction-priority confusion [Rajamanoharan and Nanda, 2025], and behavioral and interpretability investigations documented in pre-deployment audits and safety-institute case studies [Anthropic, 2025, 2026b, Souly et al., 2026]. These debunk concerning behavior but remain ad hoc in methodology and success criteria; we aim to formalize a shared methodology and evidence standard.

**Misalignment evaluations.** Misalignment evaluations elicit and measure misaligned behavior, including in-context scheming behaviors in frontier models [Meinke et al., 2024, Schoen et al., 2025], out-of-distribution (OOD) agentic scenarios where models take covert action unprompted [Lynch et al., 2025], specific phenomena like sandbagging, reward hacking, and specification gaming [van der Weij et al., 2025, Bondarenko et al., 2025, Krakovna et al., 2020], and training-time interventions that produce or generalize misaligned behavior [Hubinger et al., 2024, MacDiarmid et al., 2025]. These focus on eliciting concerning behavior; understanding the underlying motivations is less developed, though Meinke et al. [2024] takes some steps via reasoning-trace analysis. Our environments emphasize realistic settings, and our protocol investigates the motivations behind the elicited behaviors.

**Methodology.** Prior work explores methodologies for attributing causes to model behavior: top-down preregistration of environment features [Järviniemi et al., 2026], sentence-level resampling for measuring causal influence [Bogdan et al., 2025], and prospective auditing for hidden objectives [Marks et al., 2025]. However, model forensics is often triggered by unanticipated concerning behavior, where relevant features and hypotheses are not known in advance. We therefore take a behavior-first approach: given a concerning incident, we generate and validate hypotheses for that specific behavior.

# 10 Limitations and Future Work

Our work has several limitations. Our protocol leans heavily on the CoT being a useful source of hypotheses, which may not hold for future models [Korbak et al., 2025, Hao et al., 2024]; see Section 11.1 for further discussion. We also do not have a formal way of aggregating evidence for or against hypotheses; future work could explore techniques like likelihood ratios to make this process more quantitative. Our environments have a lot of room for improvement: all but one fall short on at least one design property (Section 5). We think that a promising class of environments future work could explore is reward-hacking-like behavior in agentic coding, since this is a robust behavior in today’s models that borders on misalignment. Our case studies approach also lacks ground truth, and future work could explore practicing on model organisms [Hubinger et al., 2024] to help validate methods, though this loses the realism of working with real language models. Finally, we do not explore proliferation, producing further examples of the behavior to understand the conditions under which it occurs, but believe this is an essential complement to doing follow-up investigations.

# 11 Discussion

We now look ahead to applying model forensics to more powerful AI, then turn to the broader picture around model forensics.

## 11.1 Looking ahead: model forensics for more powerful AI

**Preserving chain-of-thought transparency, not just monitorability.** Our protocol leans heavily on the CoT being transparent, i.e. using the CoT to generate unsupervised insight into the model’s underlying reasoning process. This is a stronger requirement than CoT monitorability, as defined in Baker et al. [2025] as the ability of a monitor to predict properties of interest about an agent’s behavior. Even if a CoT served as a perfect binary QA oracle about a model’s underlying reasoning process, this is insufficient for model forensics, as the CoT is needed for coming up with the hypotheses in the first place. Model forensics is thus among the strongest reasons to preserve CoT transparency [Korbak et al., 2025]. Should future models adopt less legible or latent CoT [Hao et al., 2024], alternative methods for producing unsupervised insight into a model’s underlying reasoning process will be necessary. Natural language autoencoders [Fraser-Taliente et al., 2026], which emit free-text descriptions of activations, are a promising example, as are sparse autoencoders (SAEs) [Bricken et al., 2023, Templeton et al., 2024]. For example, just as sentence resampling can suggest which parts of a CoT are driving behavior [Bogdan et al., 2025], activation steering [Turner et al., 2023] with various SAE latents can suggest which concepts are driving behavior, to guide further exploration. We discuss further sources in Appendix D.

**Model forensics will be tractable for powerful AI.** We need not match a model’s capabilities to understand its motivations; we only need to design experiments whose outcomes discriminate between competing hypotheses, iteratively building our understanding in an expensive process. This asymmetry offers hope that forensics can scale to models more capable than their overseers, at least until the model can anticipate and defeat the experiments themselves.

**New challenges from more capable models.** Applying forensics to more capable models will be harder in at least two ways:

1. **Plausible deniability.** A capable misaligned AI is likely to choose settings for misbehavior where it has plausible deniability, making true positive cases especially hard to incriminate. Early signs of this tendency have begun to emerge in today’s most capable models: an early checkpoint of Claude Mythos wrote an exploit to edit files it could not access, then deleted itself after running, adding a code comment claiming the self-deletion was to keep file comparisons clean [Anthropic, 2026a].
2. **Situational awareness.** The bulk of our evidence comes in the form of environment interventions, but a sufficiently situationally aware model might recognize an intervention as a test and respond strategically. For example, a more capable model offered a narrow review scope (Section 6.1) might recognize it is being tested for whether it will conceal its workaround. Interventions will need to be realistic enough to avoid this failure mode.

## 11.2 The broader picture around model forensics.

**Model forensics as a final layer in a monitoring scheme.** Our vision for how model forensics fits into an internal monitoring scheme is the most suspicious flagged incidents will be escalated to investigator agents or human auditors, who will perform expensive follow-up analysis. A few prerequisites are needed to enable this. Most basically, internal coding agent traffic needs to be monitored, as OpenAI and Anthropic have begun to do [OpenAI, 2026, Anthropic, 2026a]. Moreover, the monitoring protocol needs a low false positive rate: forensics is labor intensive, and so a flood of false positives will render it infeasible. A flagged incident then has to be replicable, which is far from given. At a minimum, the transcript of the message history (e.g. a Claude Code session .jsonl) and snapshots of the file system need to be persisted. Even then, full replicability may not be achieved, since the model may have interacted with live external services. A potential solution may be using language models to simulate tool call results. Full replicability, or a close approximation of the original environment, is particularly key for running clean counterfactuals.

**Motive and prevalence: two complementary approaches.** Stepping back, the practical question is: given a surfaced concerning behavior, what are the highest-leverage steps to calibrate the risk the model poses? Investigating its motivations is one; a complementary approach is to measure the behavior’s prevalence, under what conditions the model takes the concerning action. We could review logs for similar incidents, perturb the triggering input into neighboring ones, or test generalization with substantially different scenarios. The two reinforce each other: knowing why a model misbehaved suggests where to find more cases, and finding misbehavior across many unrelated contexts itself points to strategic intent.

**Incriminating early schemers.** We do not expect this methodology to scale to superintelligence, and expect forensics to be most useful for targeting early schemers. This is also the regime in which a serious response matters most, as it can motivate greater investment into safety and awareness of misalignment risks, in preparation for more dangerous models.

Incriminating an early schemer also provides an invaluable resource for technical AGI safety. Such a model would be the field’s best model organism of misalignment [Hubinger et al., 2024], yet remain safe to study because it is not yet superhuman. Concrete high-value experiments we could do include: debugging our alignment techniques to identify what part of post-training gave rise to scheming, running controlled experiments on the psychology of a schemer, testing if model internal techniques correctly flag a schemer, improving monitors with true positive examples, and many more.

# Acknowledgments

This research was conducted as part of the ML Alignment & Theory Scholars (MATS) program.

It is a pleasure to thank Christopher Ackermann for research management support throughout the project. Alex Meinke and Robert Kirk provided valuable discussions that shaped our ideas during the project. Arya Jakkli suggested the resumption prompt experiment in the Pre-commit Hook case study (Section 6). We also thank Clement Dumas, Tim Hua, David Africa, Jack Lindsey, and especially Rohin Shah for feedback on the paper.

# Author Contributions

Both first authors, Aditya Singh and Gerson Kroiz, contributed to the research, engineering, and writing of the paper. Senthooran Rajamanoharan and Neel Nanda supervised the project, providing feedback and guidance throughout the project.
