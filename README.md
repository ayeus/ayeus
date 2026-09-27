<!-- Images are generated from profile/profile.toml by profile/build.py -->

<a href="https://github.com/ayeus">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/hero-dark.svg">
    <img alt="Aayush Namdeo — building infrastructure for AI" src="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/hero-light.svg" width="100%">
  </picture>
</a>

<p align="center">
  <a href="https://www.linkedin.com/in/aayush-namdeo-299660287/"><img src="https://img.shields.io/badge/LinkedIn-connect-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn"></a>
  <a href="#-what-im-building"><img src="https://img.shields.io/badge/projects-3_featured-ff7a45?style=flat-square" alt="Projects"></a>
  <a href="https://github.com/ayeus?tab=repositories"><img src="https://img.shields.io/badge/all_repos-browse-43d1f5?style=flat-square&logo=github&logoColor=white" alt="Repositories"></a>
  <img src="https://komarev.com/ghpvc/?username=ayeus&style=flat-square&color=9be564&label=profile+views" alt="Profile views">
</p>

## ⚡ What I'm building

<a href="https://github.com/ayeus/SN">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-ayeusann-dark.svg">
    <img alt="AyeusANN — pools idle GPUs into inference endpoints" src="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-ayeusann-light.svg" width="100%">
  </picture>
</a>

<p>
<a href="https://github.com/ayeus/MAX"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-max-dark.svg"><img alt="MAX — local-first macOS computer agent" src="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-max-light.svg" width="49%"></picture></a>
<a href="https://github.com/ayeus/Sentinal-GIS"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-sentinel-dark.svg"><img alt="SentinelGIS — outbreak intelligence for India" src="https://raw.githubusercontent.com/ayeus/ayeus/main/assets/card-sentinel-light.svg" width="49%"></picture></a>
</p>

<sub>Click a card to open the repo. Click a heading below to see how it works.</sub>

<details>
<summary><b>🛰️ AyeusANN: how a request reaches an idle GPU</b></summary>
<br>

Hosts run a Rust agent that detects and benchmarks their GPUs and joins an outbound-only WireGuard mesh. Eight Go services handle auth, scheduling, routing, billing and host reputation.

```mermaid
flowchart LR
  C[Customer] --> GW[API gateway]
  GW --> CA[control-api]
  CA --> S[scheduler]
  S --> CO[coordinator]
  CO -->|gRPC over WireGuard| A[Rust host agent]
  C -->|POST /v1/chat| IG[inference-gateway]
  IG --> R[router]
  R --> V[model replica on host GPU]
  V --> B[billing-meter]
  T[trust-engine] -.reputation.-> S
```

`Go` · `Rust` · `gRPC / protobuf` · `PostgreSQL` · `Redis` · `NATS` · `MinIO` · `Docker Compose`
</details>

<details>
<summary><b>🎙️ MAX: why it doesn't trust its own clicks</b></summary>
<br>

Most assistants report success once they've *sent* an action. MAX runs a closed loop: it re-reads the OS state after every step and only reports success when the result is really there.

```mermaid
flowchart LR
  I[Voice or text] --> P[Perceive: AX tree, processes, terminal]
  P --> L[Plan with a local LLM]
  L --> K{Risk check}
  K -->|safe| A[Act: AXPress, keyboard, shell]
  K -->|high risk| Y[Ask to confirm]
  Y --> A
  A --> V{Verify OS state}
  V -->|goal met| D[Speak a factual summary]
  V -->|not yet| P
```

Runs 100% offline on Apple Silicon (Ollama + local Whisper). Tamper-evident audit log, process-group isolation, 228 tests.
</details>

<details>
<summary><b>🛡️ SentinelGIS: from government PDFs to a risk map</b></summary>
<br>

```mermaid
flowchart LR
  S1[IDSP outbreak PDFs] --> E[Scrape and normalise]
  S2[RSS / Google News] --> X[Disease signal extraction]
  E --> F[Lag, neighbour-region and trend features]
  F --> M[Spatial Random Forest]
  M --> API[FastAPI]
  X --> API
  API --> UI[React + Leaflet dashboard]
```

Weekly refresh and retraining, district-level forecasts 1–3 months ahead, and news-verified alerts on a live map.
</details>

## 🧰 Stack

<p>
  <img src="https://skillicons.dev/icons?i=py,go,rust,ts,js,cpp,java&theme=dark" alt="Languages" height="40">
  &nbsp;
  <img src="https://skillicons.dev/icons?i=fastapi,spring,nodejs,postgres,mongodb,redis,kafka&theme=dark" alt="Backend" height="40">
</p>
<p>
  <img src="https://skillicons.dev/icons?i=pytorch,tensorflow,sklearn&theme=dark" alt="AI/ML" height="40">
  &nbsp;
  <img src="https://skillicons.dev/icons?i=aws,gcp,azure,docker,kubernetes,terraform,ansible,githubactions,linux&theme=dark" alt="Cloud and ops" height="40">
  &nbsp;
  <img src="https://skillicons.dev/icons?i=react,nextjs&theme=dark" alt="Web" height="40">
</p>

<details>
<summary><b>Full list</b></summary>

```toml
[languages]  python, go, rust, typescript, javascript, c++, java, sql
[backend]    fastapi, spring boot, node.js, rest, microservices, websockets
[data]       postgresql, mysql, mongodb, dynamodb, redis, kafka, nats
[ai]         pytorch, tensorflow, scikit-learn, langchain, langgraph, rag, mcp, ollama
[infra]      aws, gcp, azure, docker, kubernetes, terraform, ansible, github actions
[network]    wireguard, firecracker microvms, tcp/ip, linux
```
</details>

## 🗂️ More from the lab

| Repo | What it is |
|---|---|
| [EduForge](https://github.com/ayeus/EduForge) | Personalised LMS with a chatbot and messaging · Flask · AWS S3 |
| [SocialSense](https://github.com/ayeus/SocialSense) | Reddit + X sentiment analysis · transformers · Streamlit |
| [AI-dictionary](https://github.com/ayeus/AI-dictionary) | LLM-powered dictionary with quizzes · Groq |
| [Automated-Financial-Data-Pipeline](https://github.com/ayeus/Automated-Financial-Data-Pipeline) | Inventory & sales data pipeline · Flask · Excel |
| [Image-Comprssor](https://github.com/ayeus/Image-Comprssor) | Image & PDF compression service · Flask |

<br>

<p align="center">
  <b><code>BUILD → BREAK → LEARN → REBUILD</code></b>
</p>
