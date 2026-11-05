# Intervention profile prior-art review

Status: research input only; **not normative text**, not a safety case, and not a claim of conformity or certification.

Review date: 2026-11-05.

## Review-depth markers

- `scope and abstract reviewed; full text not reviewed` — public catalogue material for a paywalled standard only. No detailed requirement claim is made.
- `official full public text reviewed` — public legislation or specification text was available and reviewed.
- `official overview reviewed` — an official public project/product overview was reviewed; it is not treated as a standard.
- `official repository/source text reviewed` — public source text in the named official repository was reviewed.

## Standards and legislation

| Work | Source URL | Review depth | Relevance and limits |
|---|---|---|---|
| EN ISO 13850 / ISO 13850:2015, *Safety of machinery — Emergency stop function — Principles for design* | https://www.iso.org/standard/59970.html | scope and abstract reviewed; full text not reviewed | Public abstract says the document specifies functional requirements and design principles for machinery emergency-stop functions, independent of energy type. This review does not import device, reset, performance-level, placement, colour, or timing requirements. |
| ISO 10218-1:2025, *Robotics — Safety requirements — Part 1: Industrial robots* | https://www.iso.org/standard/73933.html | scope and abstract reviewed; full text not reviewed | Public scope concerns inherently safe design, risk reduction measures, and information for use for industrial robots as incomplete machinery. Applicability to a particular humanoid deployment remains an application and integration question. |
| ISO 10218-2:2025, *Robotics — Safety requirements — Part 2: Industrial robot applications and robot cells* | https://www.iso.org/standard/73934.html | scope and abstract reviewed; full text not reviewed | Public scope covers integration, commissioning, operation, maintenance, and decommissioning of industrial robot applications and cells. No detailed integration requirement is claimed here. |
| ISO/TS 15066:2016, *Robots and robotic devices — Collaborative robots* | https://www.iso.org/standard/62996.html | scope and abstract reviewed; full text not reviewed | Public abstract identifies safety requirements for collaborative industrial robot systems and work environments and supplements ISO 10218. This review makes no force, pressure, speed, separation-distance, or validation threshold claim. |
| ISO 13849-1:2023, *Safety of machinery — Safety-related parts of control systems — Part 1: General principles for design* | https://www.iso.org/standard/69883.html | scope and abstract reviewed; full text not reviewed | Public scope concerns design and integration principles for safety-related parts of control systems, including software. No performance-level allocation or architecture claim is made. |
| IEC 61508 series, *Functional safety of electrical/electronic/programmable electronic safety-related systems* | https://webstore.iec.ch/en/publication/5515 | scope and abstract reviewed; full text not reviewed | Public catalogue scope presents a generic functional-safety lifecycle framework for E/E/PE safety-related systems. No SIL allocation, lifecycle compliance, or certification claim is made. |
| IEC 61496 series, *Safety of machinery — Electro-sensitive protective equipment* | https://webstore.iec.ch/en/publication/23356 | scope and abstract reviewed; full text not reviewed | Public catalogue scope concerns electro-sensitive protective equipment used for machinery safeguarding. It is relevant to external protective sensing, but this review makes no device type, response-time, or detection-zone claim. |
| Regulation (EU) 2023/1230 on machinery | https://eur-lex.europa.eu/eli/reg/2023/1230/oj | official full public text reviewed | The Regulation supplies the EU legal context for machinery and related products. Product classification, economic-operator duties, conformity-assessment route, and application dates require a deployment-specific legal assessment; this document is not that assessment. |

## Software, platform, and consortium work

| Work | Source URL | Review depth | Relevance and limits |
|---|---|---|---|
| ROS 2 REP-2004, *Package Quality Categories* | https://github.com/ros-infrastructure/rep/blob/master/rep-2004.rst | official repository/source text reviewed | Defines package maturity/quality categories around policies such as versioning, change control, documentation, testing, dependencies, platform support, and security. It is useful assurance-process prior art, not a functional-safety certification or an emergency-stop interface specification. |
| NVIDIA Halos for Robotics | https://www.nvidia.com/en-us/ai-trust-center/halos/robotics/ | official overview reviewed | NVIDIA presents a layered, full-stack robotics safety system spanning platform, OS, applications, validation, and an assessment ecosystem. This is vendor architecture prior art; no equivalence, certification inheritance, or compatibility with Quberon is claimed. |
| NVIDIA Halos Outside-In Safety Blueprint | https://github.com/NVIDIA/halos-outside-in-safety | official repository/source text reviewed | Public blueprint material explores external infrastructure sensing as an additional robotics safety layer. It is relevant to independent observation and validation, not evidence that an external AI perception path alone is a safety function. |
| MassRobotics AMR Interoperability Standard | https://github.com/MassRobotics-AMR/AMR_Interop_Standard | official repository/source text reviewed | Addresses interoperability information exchange for autonomous mobile robots. It is useful interface-shape prior art but is not treated here as an emergency-stop, humanoid, or functional-safety standard. |
| Open-RMF | https://openrmf.readthedocs.io/en/latest/ | official overview reviewed | Provides open-source fleet and facility coordination concepts. Coordination APIs are relevant to status and command integration, but fleet orchestration is not assumed to be a safety-rated stop path. |
| Open Source Safety Consortium | https://opensourcesafe.com/ | official overview reviewed | Public consortium material emphasizes open assurance artifacts, evidence rather than assertion, explicit scope, and upstream contribution for safety-relevant robotics software. Its outputs are prior art and do not certify Quberon. |
| COVR, *Being safe around collaborative and versatile robots in shared spaces* | https://cordis.europa.eu/project/id/779966 | official overview reviewed | Consortium work on cross-domain collaborative-robot safety validation, protocols, and shared facilities is relevant to evidence-oriented validation. It does not establish conformance for this profile. |
| ISO/TC 299 Robotics | https://www.iso.org/committee/5915511.html | official overview reviewed | The committee scope and work programme are useful context for robotics safety, terminology, performance, modularity, and interoperability standardization. Work programme context is not a substitute for the published standards. |

## Gate-zero findings

1. Prior art separates machinery/application risk reduction, safety-related control integrity, protective sensing, software/process quality, and orchestration. A future profile should keep those evidence classes distinct rather than treating an API acknowledgement as proof of physical risk reduction.
2. Public standards catalogue material supports only scope-level comparisons. Detailed clauses and thresholds require licensed full-text review by qualified assessors before normative language is drafted.
3. Existing project code is simulation-scoped. Current tests distinguish command acknowledgement, observed state, latch state, secure-core availability, reachable refusal, and unsigned intervention records. That distinction is compatible with an evidence-first profile outline, but it is not certification evidence.
4. The N4 manufacturer-interface matrix is not present: `research/humanoids/registry/api-surfaces.jsonl` is empty at this base. Therefore no requirement is attributed to an observed manufacturer interface, and no N4-dependent interface conclusion is made.
5. The appropriate gate-zero output is a non-normative outline plus explicit traceability gaps. Normative requirements, target interfaces, and conformance claims remain deferred until N4 and licensed standards review are available.
