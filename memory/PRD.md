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

## Correção Balanço & Património no Painel CEO (2026-07-26)
- ✅ Painel principal (rota `/` = `PainelCEO.jsx`) mostra 5 cartões separados: Caixa disponível, Total de ativos, Total de passivos, Património líquido (= ativos − passivos), Valor estimado ("Avaliação ainda não calculada").
- ✅ `company-value` (testid) representa **património líquido**, nunca caixa.
- ✅ Cálculo centralizado no backend: `core.py::compute_balance` (fonte única) consumido por `/api/dashboard` (`build_snapshot`) e pelo Perfil Financeiro.
- ✅ `build_snapshot` passou a usar `bal["cash"]` como base de caixa → resolveu incoerência dos sinais ("sem caixa €0" vs €3.000).
- ✅ Atualização em tempo real: editar ativos/passivos em `/financas` reflete-se no painel sem refresh (invalidate_ai_cache no save).
- ✅ Testes: `backend/tests/test_balance.py` (4 casos, inc. €86.300 − €58.200 = €28.100) + testing_agent iteration 24 frontend 100% (fluxo autenticado + update em tempo real + coerência de sinais).
- ⚠️ Limitação honesta: não existe motor de valuation independente nem lifecycle contábil transacional (AR→caixa, amortizações). O painel reflete o Perfil Financeiro agregado.
- 📌 Dívida técnica: `Dashboard.jsx` (rota `/empresa-viva`) duplica a lógica do painel — consolidar numa única fonte no futuro.

## Mini-gráfico de evolução do património líquido (2026-07-26)
- ✅ `equity_history` (nova coleção): snapshot mensal do património líquido, gravado ao abrir `/api/dashboard` e ao gravar o Perfil Financeiro (`record_equity` em `core.py`, upsert por mês/empresa).
- ✅ Novo endpoint `GET /api/equity-history` → `{ points:[{month,net_worth}], delta, currency_symbol }` (últimos 12 meses).
- ✅ `PainelCEO.jsx`: mini AreaChart (recharts) "Evolução do património líquido" + badge de variação mensal ("+€X este mês", verde/vermelho). Mostra a partir de 2 meses; com 1 mês exibe dica de que a evolução aparece com o tempo.
- ✅ Verificado visualmente (gráfico + delta) e endpoint testado por curl. Dados começam a acumular automaticamente; sem histórico fabricado (honesto).

## Motor de valuation real — "Valor da Empresa" (2026-07-26)
- ✅ `core.py::compute_valuation(profile, bal)`: valor estimado = base patrimonial (património líquido, se >0) + goodwill de rendimento (lucro anual × múltiplo). Múltiplo conservador de PME: 2,0 base, +0,5 por cada patamar de margem (10/20/30%), máx 3,5x. Piso na caixa.
- ✅ `build_snapshot` deixou de usar `company_value = caixa` (bank + 3×lucro=caixa quando lucro=0). Agora `company_value = compute_valuation(...)`. Snapshot devolve `valuation` (value, net_worth, annual_profit, multiple, goodwill, method).
- ✅ `/api/valuation` devolve também `net_worth`, `method`, `annual_profit`. Fatores IA (Ativos, Marca, Clientes...) regenerados após limpar cache.
- ✅ `Valor.jsx`: headline mostra o valor real + linha de base patrimonial e método. `PainelCEO.jsx`: cartão "Valor estimado" mostra o valor real (fmt) em vez de "Avaliação ainda não calculada".
- ✅ Verificado: admin (ativos €86.300, PL €33.600, lucro anual €300k) → valor €1.083.600 (patrimonial + rendimento 3,5x). Empresa sem lucro → valor = património líquido (honesto).
- ⚠️ É uma ESTIMATIVA (não preço de venda); não substitui avaliação formal.

## Notificação mensal de valor da empresa (2026-07-26)
- ✅ `equity_history` passou a gravar também `company_value` (record_equity, no `/dashboard` e no save do Perfil Financeiro).
- ✅ Novo endpoint `GET /api/value-alert` → `{ has_alert, current, previous, delta, pct, direction, month_label, prev_month_label }` (compara o valor deste mês com o anterior).
- ✅ `PainelCEO.jsx`: banner premium no topo ("A tua empresa vale €X — mais/menos €Y (±Z%) que em [mês]"), verde para subida / vermelho para descida, com subtexto e botão fechar. Dispensa persistida por mês em localStorage (`va-dismiss-<mês>`).
- ✅ Verificado: subida €103.600 (+10,6%) renderiza o banner verde no painel. Sem dados fabricados (histórico real acumula automaticamente).

## Diagnóstico: valor fica na caixa quando falta Perfil Financeiro (2026-07-26)
- 🔎 Causa raiz de "valor só €3000": a conta não tem `financial_profiles` preenchido (ex.: obeliscoradical@gmail.com tem empresa mas sem perfil financeiro). Sem faturação/ativos/passivos, `compute_valuation` só tem a caixa → valor = caixa. Admin (com perfil) mostra valor real. NÃO é bug do cálculo.
- ✅ Poupança de créditos: `/api/valuation` deixa de chamar a IA quando `has_balance` é falso; devolve `needs_financials: True` sem custo de LLM.
- ✅ `Valor.jsx`: quando `needs_financials`, mostra CTA "Ainda estou a usar só a tua caixa → Preencher Perfil Financeiro" em vez dos fatores IA.
- ⚠️ Ação do utilizador: preencher Finanças (faturação, ativos, passivos) para o valor real aparecer; depois redeploy para produção.

## Anexos (foto/PDF) na conversa com o CEO + Web Push (2026-07-28)
- ✅ Anexos no chat (`/ceo`): novo `POST /api/chat/attachment` (imagem→base64, doc→extract_document_text[:20000]); `ChatInput.attachment_ids`; `/api/chat` injeta imagens via `ImageContent` (força modelo visão gpt-5.4) e texto de docs no contexto; anexos apagados após uso. `Chat.jsx`: botão clip, chips, envio com anexos. Verificado por curl: CEO leu "FATURA: Total 1234.56 EUR" da imagem.
- ✅ Web Push (PWA→iOS→Apple Watch espelhado): playbook verificado. VAPID auto-gerado e guardado em `db.app_config` (sem .env). Helpers em core: `ensure_vapid`, `send_push_to_user`, `_webpush_send` (pywebpush). Endpoints `misc.py`: `/push/vapid-public-key`, `/push/subscribe`, `/push/test`. Service worker `public/sw.js`. `Settings.jsx`: cartão "Notificações no telemóvel" (Ativar + teste). Alerta mensal de valor também envia push.
- ⚠️ Runtime: análise de imagem/PDF usa saldo da Universal LLM Key (não créditos); push é grátis. iOS exige PWA no ecrã inicial + permissão por gesto. Envio push real só confirmável em browser real; endpoints validados por curl.

## Extractor financeiro SNC real — dual-mode + reconciliação (2026-07-30)
- ✅ `core.extract_financial_document` (Gemini `gemini-2.5-pro`, leitura NATIVA de PDF via `FileContentWithMimeType`): **dual-mode**.
  - **Demonstrações formais (IES/DA, Balanço, DR, Modelo 22)**: lê os TOTAIS IMPRESSOS diretamente (não recalcula). `capital_proprio` já inclui o resultado do período → reconciliação `_recon_from_totals` (Ativo = Passivo + Capital).
  - **Balancete analítico**: `_snc_reconcile` reconstrói os totais de forma DETERMINÍSTICA em Python a partir das contas de razão (LLM só extrai+classifica `nature`), com (1) dedup de contas-filhas por prefixo de código, (2) netting por raiz de 2 dígitos (débito−credito cancela IVA dedutível vs liquidado), (3) conta 81/88 como resultado autoritativo (crédito=lucro→positivo), (4) fallback resultado = rendimentos − gastos.
- ✅ Reconciliação honesta: devolve `reconciled` (bool) + `reconciliation_diff`. Balancete: capital + resultado. IES: capital (já inclui resultado). UI `ContasEvolucao.jsx` mostra badge verde "Balanço reconciliado ✓" ou âmbar "diferença de €X" — NUNCA inventa números.
- ✅ Pipeline `documents.py::store_and_analyze`: extrai por ano → `db.financial_extractions` (por year+doc_type) + alimenta `analysis.figures` (revenue/net_profit/assets/liabilities/equity) e o Perfil Financeiro (só se ainda não existir; não sobrescreve dados manuais). `GET /api/financial-history` devolve rubricas ano-a-ano (inc. rendimentos_totais + reconciled/diff).
- ✅ **Validado com DOCUMENTOS REAIS do utilizador**:
  - Balancete AAR 2025 (Obelisco Radical): vendas 168.208,60 €, resultado 36.549,49 €, capital 46.607,33 € — todos EXATOS; DR reconcilia a €866; Balanço com ~13% imprecisão (IVA/depreciações) SINALIZADO.
  - IES 2025: Ativo 31.328,80 / Passivo 21.270,96 / Capital 10.057,84 / Vendas 143.270,70 / Resultado 7.776,90 / EBITDA 20.469,76 — TODOS EXATOS, reconciliação diff 0,00 €.
  - Testes: `backend/tests/test_reconcile.py` (determinístico, PASS), `test_real_balancete.py`, `test_real_ies.py` (extrações reais Gemini).
- ⚠️ Pendente: histórico plurianual 2021→2025 requer documentos desses anos; templates dedicados Modelo 22 / DP IVA por validar; merge same-year balancete+IES na mesma empresa (IES deveria ganhar prioridade).

## Valor da empresa alimentado pelos documentos oficiais (2026-07-30)
- ✅ O VALOR DA EMPRESA passou a atualizar automaticamente a partir das extrações oficiais (`financial_extractions`), não só do Perfil Financeiro manual. `core.latest_official_financials(user_id, cid)` escolhe o ano mais recente e, no mesmo ano, o documento mais formal (IES > DR > Balanço > Balancete > Modelo22 > IVA).
- ✅ `core.compute_valuation_annual(fin)`: base patrimonial (net worth) + goodwill (resultado líquido anual × múltiplo por margem). Balancete: net worth = capital próprio (classe 5) + resultado (classe 5 não inclui o resultado); IES: capital próprio já inclui o resultado.
- ✅ `build_snapshot` faz override de bal/valuation/company_value/has_balance quando existe documento oficial e devolve `financials_source` + `has_official`. Como o snapshot NÃO é cacheado, o valor recalcula em cada abertura → atualiza imediatamente após upload (`store_and_analyze` já invalida a cache de IA).
- ✅ `/api/valuation` devolve `financials_source`; `Valor.jsx` mostra badge verde "Atualizado a partir da tua {doc} {ano}" + método fundamentado. Confiança sobe para "Estimativa/Avaliação Fundamentada".
- ✅ Verificado ao vivo: IES 2025 → valor €25.611,64 (patrimonial 10.057 + rendimento); Balancete 2025 → €192.805,29 (património 83.156 + rendimento). Screenshot do ecrã Valor confirma valor + badge + intervalo. Teste determinístico dos dois modos PASS. Dados de teste limpos.

## Fusão inteligente manual + documentos com transparência de fonte (2026-07-30, opção C do utilizador)
- ✅ A pedido do utilizador (que temia — erradamente — que o Perfil Financeiro manual tivesse sido removido): NADA foi removido; o Perfil Financeiro (faturação, caixa, DÍVIDA/financiamentos, ativos[], passivos[]) continua intacto em `Finances.jsx` + `finance.py`.
- ✅ `build_snapshot` deixou de fazer override cego. Agora FUNDE manual + documento por campo (`_pick`): quando existe documento oficial, os números que ele traz têm prioridade; o Perfil Financeiro manual preenche o que faltar. `core.compute_value_generic` é o núcleo agnóstico à fonte.
- ✅ Transparência: snapshot/`/api/valuation` devolvem `value_sources` {patrimonio, lucro, faturacao, ativos, passivos} com a etiqueta da origem ("IES 2025" ou "os teus dados (Perfil Financeiro)") + `annual_revenue`. `Valor.jsx` mostra o bloco "De onde vem este valor" com cada número e a sua fonte.
- ✅ Testado (3 cenários): só manual (€227k, fonte "os teus dados"), só documento (€25.611, fonte "IES 2025"), ambos (documento manda nos números que traz). Screenshot confirma o bloco no ecrã. Dados de teste limpos.


## "Alimentar o CEO" — relatórios/documentos como consultor (2026-07-28)
- ✅ `build_system_prompt` passou a injetar os documentos carregados (resumo IA + números extraídos, últimos 12) → o CEO "lê" os relatórios em TODO o lado (chat, valor, sinais). Verificado: CEO citou faturação €12.400, cliente principal e €5.200 a receber de um relatório carregado.
- ✅ Componente reutilizável `frontend/src/components/ReportsUploader.jsx` ("Já tens algum relatório? Insere e eu analiso") — usa `/api/upload` (doc_type=report) + `/api/documents`; mostra resumo IA por documento, qualidade e remoção. Colocado na página **Valor da Empresa** e na área **Empresa** (Settings).
- ✅ Reaproveita infra existente (object storage, extract_document_text, analyze_document). Runtime usa saldo Universal LLM Key.

## Valor fundamentado por relatórios + importação por email (2026-07-28)
- ✅ Confiança do valuation: `core.compute_confidence` (tiers: Estimativa Inteligente 35% / Estimativa Fundamentada 20% / Avaliação Fundamentada 12%) com base no perfil financeiro + relatórios com figuras. `/api/valuation` devolve `confidence` + `value_range` (intervalo). Se não há perfil manual mas há relatório com `assets`, calcula valor patrimonial "com base nos teus relatórios". `Valor.jsx` mostra badge de confiança, intervalo e dica para carregar relatório.
- ✅ Importação por email (Sugestão 3): refactor `store_and_analyze` em documents.py; `GET /api/report-inbox` (token único por user + endereço `relatorios+TOKEN@REPORT_INBOUND_DOMAIN`); `POST /api/inbound/report` webhook agnóstico (multipart estilo SendGrid/Mailgun) que identifica o user pelo token e analisa os anexos. Verificado por curl (stored:1). UI mostra o endereço + copiar. ⚠️ ATIVAÇÃO requer domínio + MX + provider inbound (Resend Receiving / SendGrid Inbound Parse) configurado e `REPORT_INBOUND_DOMAIN`; sem isso a UI mostra "fica disponível quando o domínio for configurado".

## Email mensal automático do valor da empresa (2026-07-26)
- ✅ `core.py`: `compute_value_alert` (helper reutilizado pelo endpoint), `build_value_alert_html` (template Resend, azul, sobe=verde/desce=vermelho), `send_monthly_value_alerts` (cron).
- ✅ Cron mensal registado em `server.py` (APScheduler existente): `CronTrigger(day=1, hour=8)` → `monthly_value_alerts`. Idempotente por mês via flag `alert_emailed` no doc de `equity_history`. Respeita opt-out `email_value_alert`.
- ✅ `GET /api/value-alert` simplificado para usar o helper. Novo `POST /api/value-alert/email` para envio imediato (teste/preview).
- ✅ Setting `email_value_alert` (default True) em DEFAULT_SETTINGS + `SettingsInput`. Toggle e botão "Enviar-me o resumo de valor" em `Settings.jsx` (Personalização).
- ✅ Verificado: scheduler arranca com 2 jobs; `POST /value-alert/email` devolveu `ok:true` (Resend aceitou). Entrega real ao inbox não confirmável no preview.


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

## Implemented — Fase 11: Perfil da Empresa (input do utilizador) (2026-07-24)
- ✅ Nova secção **"A tua empresa"** na área Empresa (/definicoes): o utilizador edita/insere informação em linguagem simples que alimenta TODAS as análises do CEO (saúde, valor, conselhos, relatórios).
- ✅ Campos (16+) agrupados: O básico (atividade, localização, anos, modelo de negócio), Pessoas e clientes (nº pessoas/clientes, peso do maior cliente %, recorrência, dependência do fundador), Dinheiro (caixa, preço médio, dívidas, maior custo, dependência de fornecedor, sazonalidade), Objetivos (objetivo da empresa, objetivo pessoal, vantagem competitiva, maior preocupação).
- ✅ Guardado em `company.profile`; `build_system_prompt` inclui bloco "PERFIL DA EMPRESA"; guardar invalida a cache de IA (regenera análises).
- ✅ Testado (iteration_12): backend 4/4, frontend 100%. Zero bugs.

## Implemented — Fase 12: Preencher empresa automaticamente (NIF + Certidão) (2026-07-24)
- ✅ Card **"Preencher automaticamente"** na área Empresa: (1) campo **NIF/NIPC** → busca nome, CAE, morada e estado via API NIF.PT (POST /api/company/lookup-nif; precisa de NIFPT_API_KEY); (2) **upload da certidão permanente (PDF)** → o CEO AI extrai nome, NIPC, CAE, atividade, morada, objeto social, capital, data de constituição e sócios (POST /api/company/import-certidao; sem chave, usa IA). Os dados pré-preenchem o formulário para o utilizador rever e guardar.
- ✅ Campo CAE visível/editável; aviso quando a extração não encontra dados.
- ✅ Nota: código da certidão permanente não tem API pública gratuita — usámos NIF (NIF.PT) + PDF por IA.
- ✅ Testado (iteration_13): backend 6/6 novos + 4/4 regressão, frontend 100%. NIF sem chave falha graciosamente (400 com mensagem clara). Zero bugs.

## Implemented — Fase 13: Sinais do CEO (decisões, não dashboards) (2026-07-24)
- ✅ **Sinais do CEO** no topo do Painel: "Bom dia/tarde/noite, {Nome}. Hoje tenho N alertas importantes." + 3-6 alertas afiados e QUANTIFICADOS com ícones por severidade (🔴 crítico, 🟡 atenção, 🟢 positivo, ⚠️ risco, 💡 oportunidade) e uma 🎯 "Prioridade máxima de hoje".
- ✅ Números REAIS calculados no backend (GET /api/signals): variação de despesas/receitas mês-a-mês, tendência de margem, runway em dias, perda mensal se perder o maior cliente (concentração), lucro extra se subir preços 4%, dívidas. A IA só transforma os factos em frases de decisão (proibido inventar números). Cache diária + invalida ao mudar dados.
- ✅ Exemplos gerados: "As despesas subiram 67% e a margem caiu de 35,7% para 6,2%", "Se subires os preços 4%, acrescentas €1.200 de lucro anual", "Se perderes o maior cliente, levas um rombo de €6.400/mês".
- ✅ Testado (iteration_14): backend 3/3, frontend 100%. Zero bugs.

## Implemented — Fase 14: Especialização por setor (conselhos personalizados ao ramo) (2026-07-24)
- ✅ O CEO AI passou a adaptar-se ao **setor da empresa**: bloco "ESPECIALIZAÇÃO NO SETOR" no `build_system_prompt` (a partir de sector/atividade/CAE) que obriga a usar referências, riscos, KPIs e vocabulário do ramo específico — nunca genérico. Afeta TODAS as saídas (sinais, saúde, valor, relatório, chat, simulações, ceo-daily).
- ✅ Verificado: restaurante → food cost, ementa, rotação de mesas, turnos; construção → obras, empreitadas, adjudicações, mão-de-obra, materiais. Muda de vocabulário ao mudar o setor (cache invalidada ao guardar a empresa).
- ✅ Testado (iteration_15): backend 5/5. Zero bugs.

## Implemented — Fase 15: Onboarding inteligente conduzido pelo CEO AI (2026-07-25)
- ✅ **Tour guiado por spotlight** (`/app/frontend/src/components/CEOTour.jsx`, montado no `AppLayout`) que ilumina os elementos reais: boas-vindas ("👋 Bem-vindo ao CEO AI, olá {Nome}") → Painel do CEO → Prioridade Máxima → Saúde Empresarial → Conversar com o CEO → Relatório → CTA final "Carregar os meus dados" (→ /financas).
- ✅ **Aparece de ambas as formas**: automaticamente na 1ª chegada ao Painel após onboarding (GET /api/settings → tour_completed) E via botão manual "Tour guiado do CEO" na sidebar (evento `start-ceo-tour`).
- ✅ **Copy adaptada ao setor** (construção: margens por obra/prazos/tesouraria; restauração: food cost/ocupação/desperdício; clínica: agenda/faturação por especialidade; genérico) via `sectorKey()` sobre o setor da empresa ativa.
- ✅ **Persistência por utilizador**: PUT /api/settings {tour_completed:true} ao concluir ou saltar; não reabre em logins seguintes. `SettingsInput` e DEFAULT_SETTINGS atualizados.
- ✅ Fallback gracioso: spotlight de itens do menu só em desktop; em mobile mostra cartão centrado. Testado (iteration_16): frontend 100%, 8/8 casos, zero bugs.

## Implemented — Fase 16: Preços premium + Campanha "Empresa Fundadora" + Admin + Gating (2026-07-25)
- ✅ **Página de Preços premium** (/planos): 3 planos (Empresa Fundadora 29€ com badge "Oferta Exclusiva" e 79€ riscado / Professional 79€ com 7 dias grátis / Enterprise desde 199€ → "Falar com um Consultor" para /contacto), contador dinâmico real (X/15) + barra de progresso, secções "Porquê Fundadora", Confiança e FAQ. Encerra automaticamente e mostra "Programa encerrado" quando 15/15 ou campanha suspensa.
- ✅ **Campanha Fundadora (backend)**: alocação ATÓMICA de vagas 1..15 (counter `counters:founder` via findOneAndUpdate {seq<15} + lock por utilizador), só em pagamento CONFIRMADO+ATIVO (webhook + fallback /payments/status). Idempotência de webhooks via `stripe_events` (_id=event id). Trials NÃO ocupam vaga. Cancelado mantém founder_number histórico mas perde o preço (founder_price_locked=false) e a vaga NÃO é reaberta. Campos em `users`: is_founder, founder_number, founder_activated_at, founder_price_locked, subscription_status, plan, stripe_customer_id, stripe_subscription_id, subscription_started_at/cancelled_at, current_period_end, last_payment_at, failed_payments, cancel_at_period_end.
- ✅ **Stripe**: novos preços `founder_monthly` (2900) e `professional_monthly` (7900, trial 7d) sincronizados via setup_stripe.py. Webhook trata checkout.session.completed, customer.subscription.created/updated/deleted, invoice.paid, invoice.payment_failed. Guard de re-verificação de vagas no checkout (409 founder_closed / founder_used; 400 enterprise).
- ✅ **Painel Admin** (/admin, só ADMIN_EMAIL): visão geral (empresas, ativos, teste, fundadoras, MRR total/fundadoras/outros, cancelamentos, falhados, novos 7/30d), barra X/15, tabela de clientes com filtros+pesquisa, export CSV, posições das 15 fundadoras, notificações in-app, auditoria, toggle da campanha, nota interna, cancelar subscrição, reenviar notificação. Endpoints /api/admin/* protegidos (403 não-admin).
- ✅ **Notificações admin**: in-panel + email (Resend) em cada ativação de Fundadora e marcos 5/3/1/0. NOTA: o envio de email devolveu 401 (chave Emergent Email) — as notificações no painel funcionam; a entrega por email precisa de a chave estar válida.
- ✅ **Gating plano grátis ("só demonstração")**: Painel visível mas Prioridade + Recomendações bloqueadas (LockedBlock); Saúde/Valor/Futuro/Relatórios/Chat/Conselhos bloqueados (nav com cadeado → /planos; UpgradeWall no acesso direto). Backend devolve 402 nos endpoints premium; admin tem bypass.
- ✅ Testado: iteration_17 (backend 13/14 → corrigido /decisions; frontend 100% dos fluxos) + e2e_founder.py (alocação atómica, concorrência, cap 15, idempotência, trial-não-ocupa, ativo-ocupa, cancel mantém número/perde preço) — TODOS a passar.

## Implemented — Fase 17: Redesign visual "Executive Cybernetic" (2026-07-25)
- ✅ Novo tema dark near-black (#05050A) com acento AZUL (#3B82F6) + esmeralda, glow radial azul de fundo (index.css: CSS vars, `.surface` glass 24px blur, `.watermark`, fontes Outfit display + Inter body).
- ✅ Swap global de dourado→azul em todo o `src` (pages/components/App.js).
- ✅ **Sidebar icon-rail** (w-20, só ícones + tooltips, logo cubo azul) a substituir a sidebar larga; testids desktop preservados (nav-*, company-selector, restart-tour-btn, nav-subscricao, logout-btn, nav-admin) e drawer mobile com sufixo `-m`.
- ✅ **Watermark gigante** (nome da empresa) atrás dos títulos no Painel, Futuro e Relatórios; subtítulo de data no Painel; gráficos recharts a azul.
- ✅ VoiceSphere e CEOOrb recoloridos para azul.
- ✅ Testado: iteration_18 (frontend 100%, navegação icon-rail + gating grátis + drawer mobile, sem erros de runtime).

## Atualização (Jun 2026) — Dívida + Balanço/Património (Finanças > Perfil)
- ✅ Campo "Dívida total (empréstimos/financiamentos)" no Perfil Financeiro; métricas Dívida total (em meses de faturação) e Posição líquida (caixa − dívida).
- ✅ Balanço/Património: listas dinâmicas de Ativos (veículos, ferramentas, stock, contas a receber...) e Passivos (fornecedores, impostos, outros empréstimos). Backend: total_assets = caixa + ativos; total_liabilities = dívida + passivos; net_worth = ativos − passivos. Secção "Património (Balanço)" com 3 tiles + breakdown.
- ✅ A dívida, ativos, passivos e património líquido são passados à Análise do CEO e guardados em memories p/ o chat. Resolve a "foto distorcida" (empresa deixa de valer só a caixa).
- ✅ Testado: iteration_21 (frontend balance-sheet 100%) + curl (ativos/passivos/net worth corretos). Modelo FinancialProfileInput ampliado (total_debt, assets[], liabilities[]).

## Atualização (Jun 2026) — Perfil Financeiro + Análise do CEO (Finanças)
- ✅ Nova aba "Perfil Financeiro" em /financas (a par de "Movimentos"): o dono insere faturamento mensal, custos fixos (lista dinâmica nome+valor), custos variáveis (% da receita) e saldo em caixa.
- ✅ Métricas calculadas no backend (compute_profile_metrics): custos totais, lucro, margem líquida %, ponto de equilíbrio (fixos/(1-var%)), runway (caixa/burn), maior custo, meta vs realidade (target anual do DNA /12).
- ✅ "Análise do CEO" (premium): GET /api/finance/profile/analysis devolve diagnóstico + riscos + prioridades + ações (JSON, cached diário via cached_ai); free tier recebe premium_locked → CTA Premium.
- ✅ Endpoints: GET/POST /api/finance/profile, GET /api/finance/profile/analysis. Modelo FinancialProfileInput; figuras guardadas em memories (categoria financas_perfil) p/ o chat do CEO ficar ciente.
- ✅ Testado: iteration_20 (frontend 100%, math verificada) + curl backend. Ficheiro Finances.jsx com tabs.

## Atualização (Jun 2026) — Ícone, Sidebar premium e Admin único
- ✅ Ícone app/PWA + login + sidebar unificados no android executivo transparente (`/android_cut.png`); favicon/logo192/512/maskable/apple-touch regenerados (fundo preto full-bleed).
- ✅ Admin ÚNICO = adminceoai@gmail.com / 12345 (ADMIN_EMAIL); antigo owner (obeliscoradical) deixou de ser admin. Seed idempotente + empresa e DNA default → admin vai direto ao Painel (não onboarding).
- ✅ Gestão de contas no /admin: editar (nome/email/premium), apagar (+ dados associados, não apaga admin), repor senha via email com link seguro (token 1h, uso único). Endpoints: PATCH/DELETE /admin/customers/{uid}, POST /admin/customers/{uid}/reset-password, GET/POST /api/auth/reset-password[/validate]. Nova página /reset-password.
- ✅ Sidebar redesenhada: rail 96px → sidebar premium 256px (header de marca, seletor de empresa, nav com rótulos + acento ativo/glow, secções Menu/Conta, CTA Premium para grátis, rodapé com perfil + logout). main md:pl-64. Testids preservados.
- ✅ Testado: iteration_19 (sidebar 100%); reset/edit/delete/admin-gating por curl end-to-end; Admin.jsx state + seed corrigidos.
- ⚠️ Senha admin `12345` é fraca (a pedido do utilizador). No deploy, FRONTEND_URL deve apontar para produção p/ os links de reset funcionarem.

## Backlog atualizado
- P1: Confirmar entrega dos emails admin/briefing (chave Emergent Email devolveu 401).
- P2: Open banking real por região (UE/PT, BR).
- P2 (opcional): usar figuras extraídas dos documentos para recalcular o valuation base (atualmente alimentam o rationale/rating, não o valor base do snapshot).
- Produção: reclamar conta Stripe live + payouts antes de vender; redeploy necessário para publicar estas fases.
