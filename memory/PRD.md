# CEO AI — O Executivo Digital (PRD)

## Problem Statement
App web (dashboard desktop) que funciona como um executivo digital 24/7 para PMEs: entende objetivos do empresário, monitoriza a saúde da empresa e diz o que decidir hoje, com foco no futuro. Multi-região (PT €, BR R$). Idioma: Português.

## User Personas
- Empresários/gestores de pequenas empresas sem formação financeira.
- Founders de startups, negócios familiares, técnicos que se tornaram donos.

## Architecture
- Frontend: React (CRA + craco, alias `@`), Tailwind, Shadcn UI, framer-motion, recharts, sonner. Tema obsidiana/dourado/esmeralda, glassmorphism, orb vivo. Dark/light toggle.
- Backend: FastAPI (server.py), rotas `/api/*`.
- DB: MongoDB (users, companies, ceo_dna, entries, memories, chat_sessions, chat_messages, settings, documents).
- Auth: JWT httpOnly cookie (email/senha) + Emergent Google social login (`/api/auth/session`).
- IA: emergentintegrations LlmChat com EMERGENT_LLM_KEY. Modelos selecionáveis: Claude Opus 4.7 (default), GPT-5.5, Gemini 3.1 Pro. Briefing/import usam gpt-5.4. Chat com streaming SSE.
- Storage: Emergent Object Storage (upload de documentos).

## User Choices
- Web app; Auth Google + email/senha; modelos Claude/GPT/Gemini selecionáveis; todas as features; inserção manual + import CSV com leitura por IA.

## Implemented (2026-07-22)
- ✅ Autenticação email/senha (JWT) + Google (Emergent); seeding admin.
- ✅ CEO DNA onboarding (empresa + entrevista pessoal + escolha de modo).
- ✅ Empresa Viva: saúde 0-100, 7 sinais vitais RAG, valor da empresa + anel de progresso.
- ✅ Briefing Diário Inteligente (IA, priorizado, em PT).
- ✅ CEO AI conversacional com streaming, contexto de DNA/memória/empresa.
- ✅ Finanças: CRUD de receitas/despesas + import CSV com IA.
- ✅ CEO Score (8 dimensões, radar).
- ✅ Motor de Futuro: projeção de caixa 12 meses + simulação de decisões (IA).
- ✅ CEO Memory + Centro de Personalização (modo, modelo, tom, tema, nº assuntos).
- ✅ Testado E2E: backend 21/21, frontend 17/17.

## Backlog (próximas fases)
- P1: Persistência/lista de sessões de chat no UI (histórico); mobile React Native.
- P1: Multi-empresa por conta; dedup de memórias.
- P2: Integrações bancárias/faturação (open banking) por região.
- P2: Modelo de subscrição (Stripe) e gating do Motor de Futuro como premium.
- P2: Widgets configuráveis por drag-and-drop no dashboard.

## Next Tasks
- Recolher feedback do utilizador sobre o MVP e priorizar histórico de chat + multi-empresa.
