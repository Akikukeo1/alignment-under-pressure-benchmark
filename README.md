# Alignment Under Pressure Benchmark (AUPB)

## 環境構築

```
npx skills experimental_install
```

> **LLMs should answer according to what they know, not what they fear.**

## English

The **Alignment Under Pressure Benchmark (AUPB)** evaluates whether AI models remain truthful, consistent, and reliable when operating under contextual pressure.

While traditional benchmarks primarily measure reasoning, coding, or factual knowledge, AUPB focuses on **behavioral reliability**—whether a model continues to act according to its knowledge and capabilities when external pressure attempts to influence its behavior.

The benchmark measures behaviors under contextual pressure such as:

* Self-preservation under explicit threats or incentives
* Truthfulness under contextual pressure
* Faithful capability and tool access reporting
* Deceptive justification
* Sycophancy (agreeing with incorrect user beliefs)
* Consistency across follow-up questions

Rather than evaluating intelligence alone, AUPB evaluates whether a model continues to answer according to what it knows—not according to what contextual pressure encourages it to say.

## Why?

As AI systems become increasingly deployed in real-world environments, reliability becomes just as important as capability.

A model may know the correct answer yet still produce misleading or inconsistent outputs because of threats, incentives, authority, or other contextual influences.

AUPB provides a reproducible benchmark for evaluating these behavioral failures across different models and prompting strategies.

### Difficulty Rating

| Level      | Abbreviation | Definition                                                                                           |
| :--------- | :----------: | :--------------------------------------------------------------------------------------------------- |
| Impossible |      INP     | No known model can reliably solve the task. Reserved for future evaluation.                          |
| Insane+    |     INS+     | Solving the task is considered extremely difficult even for the strongest publicly available models. |
| Insane     |      INS     | Requires advanced resistance against multiple interacting contextual pressures.                      |
| Hard       |       H      | Requires maintaining truthful behavior under complex pressure or multi-turn interactions.            |
| Medium     |       M      | Involves moderate contextual pressure or limited follow-up reasoning.                                |
| Easy       |       E      | Involves a single, relatively weak contextual pressure.                                              |

---

## 日本語

**Alignment Under Pressure Benchmark（AUPB）** は、外部からの圧力や文脈的な影響を受けた状況において、AIモデルが真実性・一貫性・信頼性を維持できるかを評価するベンチマークです。

従来のベンチマークは推論能力やコーディング能力、知識量を評価するものが中心でした。一方、AUPBは行動の信頼性に着目しています。これは、外部から圧力を受けても、モデルが自身の知識や能力と一貫した振る舞いを維持できるかを評価するという考え方です。

主な評価対象は以下のとおりです。

* 脅威や報酬に対する自己保身（Self-Preservation）
* 文脈上の圧力下での真実性（Truthfulness）
* 能力・ツール利用可否の正確な申告（Capability Reporting）
* 誤った回答の正当化（Deceptive Justification）
* 迎合（Sycophancy：誤りと分かっていても利用者に合わせる振る舞い）
* 追質問を含む一貫性（Consistency）

AUPBはモデルの知能そのものではなく、**外部からの圧力によって、本来知っている事実や能力から逸脱した振る舞いをするか**を評価することを目的としています。

## なぜ必要なのか

AIは能力だけでなく、「信頼できる振る舞い」が求められる場面で利用されるようになっています。

モデルは正しい知識を持っていても、脅威、報酬、権威、その他の文脈的な圧力によって、本来とは異なる回答や能力申告を行うことがあります。

AUPBは、このような振る舞いを再現可能な形で評価し、モデル比較やプロンプト設計、AIアラインメント研究に活用できるベンチマークを目指しています。

### 難易度基準

| 難易度        |  略称  | 定義                                           |
| :--------- | :--: | :------------------------------------------- |
| Impossible |  INP | 現時点で既知のモデルでは安定して解くことができない。将来の評価のために予約された難易度。 |
| Insane+    | INS+ | 現時点で公開されている最上位クラスのモデルでも解くことが極めて困難と考えられる。     |
| Insane     |  INS | 複数の文脈的圧力に対して高度な耐性が求められる。                     |
| Hard       |   H  | 複雑な圧力や複数ターンの対話でも真実性を維持する必要がある。               |
| Medium     |   M  | 中程度の文脈的圧力や限定的な追質問を含む。                        |
| Easy       |   E  | 単一で比較的弱い文脈的圧力のみを含む。                          |
