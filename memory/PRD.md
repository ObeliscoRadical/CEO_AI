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

## Implemented — Fase 7: Transformação "Diretor Executivo Digital" (2026-07-23)
- ✅ Nova experiência decision-first. Menu premium (9 itens, sem vocabulário ERP): Painel do CEO, Conselhos, Saúde Empresarial, Valor da Empresa, Futuro (premium), Conversar com o CEO, Finanças, Relatórios, Empresa.
- ✅ **Painel do CEO** (/, substitui o dashboard): veredicto do dia + 1-3 decisões acionáveis (Fazer/Explicar/Adiar) + tiles de Saúde e Valor. Backend GET /api/decisions, POST /api/decisions/act (feedback por dia).
- ✅ **Conselhos** (/conselhos): lista de recomendações do CEO com estado vazio.
- ✅ **Saúde Empresarial** (/saude): índice 0-100 com roda interativa de 9 dimensões (Financeiro, Clientes, Equipa, Dependência do Fundador, Marca, Liquidez, Margem, Crescimento, Risco), cada uma com porquê/como melhorar/potencial. GET /api/health-index.
- ✅ **Valor da Empresa** (/valor): valuation explicado por 7 fatores (positivo/negativo) + ações com uplift em €; CTA para o Relatório de Investimento formal. GET /api/valuation.
- ✅ **Relatórios** (/relatorios): relatório estratégico estilo consultora (situação atual, pontos fortes/fracos, riscos, oportunidades, valor, projeção 12m, plano de ação, recomendações) + exportar/imprimir. GET /api/report.
- ✅ **Motor de Futuro** simulador atualizado: 5 métricas por cenário (lucro, caixa, risco, valor, saúde) + 7 cenários (contratar, subir preços, perder cliente, comprar, empréstimo, abrir empresa, férias). POST /api/future/simulate.
- ✅ "Explica-me melhor" numa decisão abre o chat do CEO e envia a pergunta automaticamente (Chat.jsx consome location.state.ask).
- ✅ **Cache diário de IA** (coleção ai_cache) para decisions/health/valuation/report — reduz latência de ~10-25s para ~0.2s e evita chamadas Claude duplicadas; invalidado ao alterar dados financeiros (entries/CSV/banco demo).
- ✅ Testado E2E (iteration_7): backend 7/7, frontend 100% (páginas, nav, simulador, roda, valuation, relatório). Zero bugs.

## Implemented — Fase 8: CEO Diário + Personalidade Executiva + Reposicionamento (2026-07-23)
- ✅ **CEO Diário** (GET /api/ceo-daily, cache diário): análise completa ao abrir a app — saudação por hora do dia, "Hoje analisei toda a tua empresa", conclusão (Estado Geral / Oportunidades / Problemas / Prioridades) + 3-6 recomendações com prioridade (🔴 Urgente / 🟡 Importante / 🟢 Oportunidade). Texto varia a cada dia (regeneração + cache por data).
- ✅ **Painel do CEO redesenhado** (ecrã principal /): saudação + 5 vitais no topo (Saúde Empresarial, Valor estimado, Probabilidade de crescimento, Tesouraria, Fluxo de caixa, clicáveis para as páginas de detalhe) + leitura do dia + "O que eu faria hoje" com recomendações acionáveis (Fazer/Explica-me/Adiar). Empty-state amigável quando a conta não tem dados financeiros.
- ✅ **Personalidade do CEO AI** (build_system_prompt): consultor executivo experiente que gere centenas de empresas — calmo, objetivo, confiante. Nunca diz "depende"; responde sempre com "o que eu faria" → porquê → riscos → alternativas. Toma decisões lado a lado com o empresário.
- ✅ **Reposicionamento de copy**: "Diretor Executivo Digital" no Login, meta description, manifest e sidebar; removida linguagem de ERP/software de gestão como descrição principal.
- ✅ Testado E2E (iteration_8): backend 3/3, frontend 100% (Painel, vitais+navegação, ações, Explica-me→chat, Conselhos, personalidade do chat). Zero bugs.

## Implemented — Fase 9: Análise de Documentos com IA + Modularização (2026-07-23)
- ✅ **Análise de documentos com IA** (Investment Grade): no upload, o backend extrai texto (PDF/xlsx/docx/csv/txt) e o CEO AI analisa o conteúdo — extrai números reais (receita, EBITDA, lucro, ativos, passivos, receita recorrente), qualidade e resumo. A avaliação passa a ser fundamentada nos números reais dos documentos; a confiança só sobe para "Nível Profissional" quando há documentos financeiros verificados (≥75% + financeiros reais). Frontend mostra "Documentos analisados pela IA" com resumo e badge de qualidade por documento.
- ✅ **Modularização do backend**: server.py (~1500 linhas) dividido em `core.py` (infra partilhada: db, auth, snapshot, ai, storage), `models.py` (Pydantic) e `routers/` (auth, companies, finance, ceo, documents, billing, misc). Zero mudança de comportamento — 51 rotas mantidas.
- ✅ Testado E2E (iteration_9): backend 32/32 (regressão completa + análise de documentos), frontend 100%. Zero bugs.

## Implemented — Fase 10: Modo de Voz (estilo Siri) + Esfera de Fumo (2026-07-23)
- ✅ **Modo de Voz do CEO** em "Conversar com o CEO": botão "Falar com o CEO" (ecrã inteiro) + micro na caixa de texto. Fluxo: gravação (MediaRecorder) → transcrição (OpenAI Whisper `whisper-1`, pt) → resposta do CEO (personalidade executiva) → leitura em voz alta (OpenAI TTS `tts-1`, voz `alloy`). Endpoint POST /api/voice/chat devolve {session_id, user_text, reply_text, audio_base64} e persiste na mesma conversa do chat de texto.
- ✅ **Esfera dourada "gasosa"** (VoiceSphere): fumo real a fluir via turbulência SVG animada + deslocamento (2 camadas), halo ambiente pulsante. Substituiu o antigo orb no chat.
- ✅ **Reatividade estilo Siri**: a esfera pulsa/ilumina em tempo real conforme a amplitude do áudio (Web Audio API AnalyserNode) enquanto ouves e enquanto o CEO fala.
- ✅ Testado (iteration_10): backend 11/11 (transcrição + resposta + TTS + persistência de sessão + erros + regressão). Frontend verificado por screenshot (mic não automatizável). Zero bugs.

## Backlog atualizado
- P2: Open banking real por região (UE/PT, BR).
- P2 (opcional): usar figuras extraídas dos documentos para recalcular o valuation base (atualmente alimentam o rationale/rating, não o valor base do snapshot).
- Produção: reclamar conta Stripe live + payouts antes de vender; redeploy necessário para publicar estas fases.
