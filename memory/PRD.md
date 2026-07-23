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

## Implemented — Fase 2 (2026-07-22)
- ✅ Multi-empresa por conta: seletor na sidebar, criar/trocar empresa, isolamento por company_id (migração automática de entries órfãs).
- ✅ Histórico de conversas do CEO AI: lista de sessões, retomar, nova conversa, apagar.
- ✅ Freemium com Stripe: Motor de Futuro Premium (403 gate). Planos premium_monthly (€19/mês) e premium_yearly (€190/ano). Checkout + status polling + webhook ativam is_premium. Páginas /planos e /payment/success|cancel.
- ✅ "Ligar banco" demo/mock: gera ~40-50 movimentos na empresa ativa (open banking real depois).
- ✅ Stripe Flow A (claimable sandbox), tax mode managed payments (SMP), catálogo em setup_stripe.py.
- ✅ Testado E2E: backend 13/13 (fase 2) + 21/21 (fase 1); frontend 100%.

## Implemented — Fase 3 (2026-07-23)
- ✅ Relatório de Investimento (Investment Grade) — Premium: rating por letras (A+..F) para Financeiro, Crescimento, Risco, Liquidez e Dependência do Fundador + grade global; explica PORQUE vale X (rationale) e COMO valer mais (plano com impacto em €); nível de confiança honesto (Estimativa Inteligente/Fundamentada/Nível Profissional) com checklist de dados formais e disclaimer (estimativa ≠ avaliação pericial). Endpoint GET /api/investment-grade gated por is_premium. Página /relatorio + nav.
- ✅ Testado E2E: backend 11/11; frontend 100% (paywall + relatório premium).



## Backlog (próximas fases)
- P1: Persistência/lista de sessões de chat no UI (histórico); mobile React Native.
- P1: Multi-empresa por conta; dedup de memórias.
## Implemented — Fase 4/5 (2026-07-23)
- ✅ Gestão de Subscrição (/subscricao): estado do plano, portal de faturação Stripe (billing portal), cancelar (cancel_at_period_end), CTA de upgrade no plano grátis; webhooks refletem cancelamentos. Guarda stripe_customer_id/subscription_id. Link na sidebar.
- ✅ Checklist de confiança clicável no Relatório de Investimento: upload de documentos com doc_type (financials/assets/contracts) via POST /api/upload; GET/DELETE /api/documents; carregar documentos sobe o nível de confiança (Inteligente→Fundamentada→Profissional) e estreita o intervalo de valor.
- ✅ Testado E2E: subscrição 7/7; upload/checklist 10/10; zero bugs.


- P2: Integrações bancárias/faturação (open banking) por região.
- P2: Modelo de subscrição (Stripe) e gating do Motor de Futuro como premium.
- P2: Widgets configuráveis por drag-and-drop no dashboard.
## Implemented — Fase 6 (2026-07-23)
- ✅ Briefing diário por email (Resend gerido): toggle opt-in nas Definições + "Enviar-me agora" (POST /api/briefing/email), email HTML com tema CEO AI. Scheduler diário (07:00 UTC) com dedupe por data (seguro para múltiplas réplicas).
- ✅ Preços atualizados para €29/mês e €290/ano; páginas legais (/termos, /privacidade RGPD, /contacto) + formulário de contacto (POST /api/contact).
- ✅ Deployment readiness: PASS (CORS lê CORS_ORIGINS com echo de origem para cookies; queries com projeções).
- ✅ Testado E2E: briefing email 6/6; zero bugs.



## Next Tasks
- Recolher feedback do utilizador sobre o MVP e priorizar histórico de chat + multi-empresa.
