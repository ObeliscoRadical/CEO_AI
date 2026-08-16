# CEO AI — PRD Resumido

## Problema original
O utilizador pediu uma separação estrita do módulo de Marketing em dois agentes autónomos:

1. **Growth Agent** — responsável apenas por website, SEO, GA4, Google Search Console e conteúdo do site.
2. **Social Media Agent** — responsável apenas por calendário editorial, criativos, reels, agendamento, publicação e analytics sociais.

Também pediu a configuração real da integração Meta para deixar de depender de estados **MOCKED** quando houver permissões e dados reais disponíveis.

## Escolhas explícitas do utilizador
- Idioma preferido: **Português (pt-PT)**
- Prioridade atual neste fork: **métricas Meta em produção**
- Estado reportado pelo utilizador: **já testou em produção e ainda falha**
- Informação adicional confirmada pelo utilizador: já tem as permissões **`instagram_manage_insights`** e **`read_insights`** ativadas

## Objetivos de produto
- Manter a separação total entre Growth Agent e Social Media Agent
- Permitir ligação Meta real para publicação e analytics
- Distinguir corretamente:
  - permissões/scopes disponíveis
  - readiness de publicação
  - readiness de insights reais
  - fallback para **MOCKED** apenas quando os dados reais ainda não estiverem confirmados

## Arquitetura atual
- **Frontend:** React SPA
- **Backend:** FastAPI
- **Base de dados:** MongoDB
- **Scheduler:** APScheduler

### Módulos principais
- `backend/routers/marketing_autonomous.py` → Growth Agent
- `backend/routers/social.py` → Social Media Agent, OAuth Meta, publicação e insights
- `backend/routers/marketing.py` → analytics editoriais, briefing, campanhas
- `frontend/src/pages/Marketing.jsx` → cockpit principal do Marketing
- `frontend/src/components/marketing/MetaConnectionSection.jsx` → estado de ligação Meta

## Estado funcional atual

### 0. Organização visual do módulo Marketing
Concluída neste fork.

- no menu lateral de **Marketing** existem agora apenas 2 entradas:
  - **Agente · Site**
  - **Agente · Redes Sociais**
- dentro de `/marketing`, a leitura também ficou separada em 2 blocos grandes:
  - **Agente · Site** → agrega as 3 frentes do Growth Agent
  - **Agente · Redes Sociais** → agrega as 6 frentes sociais
- nenhuma funcionalidade foi removida; apenas reorganizada por agente
- a ordem interna ficou simplificada e explícita:
  - **Agente · Site** → Estratégia → Gateway → SEO/GA4/GSC
  - **Agente · Redes Sociais** → Automação → Meta → Marca & Conteúdo → Campanhas → Aprovação & Calendário → Operação & Resultados
- títulos e resumos principais ficaram mais curtos
- os blocos internos ficaram mais compactos, com leitura mais densa e mais orientada a dashboard

### 0.1 Painel visual de Alterações do Site
Concluído neste fork.

- dentro de **Agente · Site > Gateway** existe agora um painel visual **Alterações do Site**
- o painel mostra:
  - timeline visual de alterações
  - cards com **before / after**
  - **diff visual rico** por campo
  - motivo da alteração
  - data/hora
  - tipo de alteração
  - botão de rollback quando existe versão anterior elegível
- filtros já incluídos na primeira versão:
  - por **página**
  - por **tipo**
  - por **data**
- a origem dos dados vem do histórico real do gateway (`site_publication_logs` + `site_content_versions`)
- o endpoint `GET /api/marketing/site-publishing/status` agora devolve `change_history`
- o diff visual foi reforçado com **comparação inline palavra-a-palavra**:
  - contagem de adições e remoções
  - texto removido destacado no bloco **Antes**
  - texto adicionado destacado no bloco **Depois**
  - convivência com o diff clássico por campo, sem perder a leitura executiva

### 1. Separação de agentes
Concluída.

**Growth Agent**
- site público
- SEO técnico
- GA4
- GSC
- gateway interno de publicação do site

**Social Media Agent**
- calendário editorial
- posts/legendas/imagens
- agendamento
- publicação Meta
- analytics sociais

### 2. Meta OAuth e publicação
Concluído e já funcional no código.

- App ID / App Secret / Config ID reconhecidos
- ligação OAuth disponível
- seleção de página suportada
- publicação Facebook/Instagram separada do estado de insights

### 3. Meta insights readiness
Estado reforçado neste fork.

Foi implementado:
- parsing de permissões a partir de **`granted_scopes`** e também de **`granular_scopes`**
- distinção entre:
  - `insights_permissions_ready`
  - `live_metrics_ready`
  - `insights_status`
  - `report_source`
- probe real de insights com fallback coerente
- auto-refresh de diagnóstico quando o estado está por validar ou desatualizado
- resposta mais clara em `/api/social/metrics/refresh`

### 4. Estados Meta agora suportados
- `ready`
- `no_data`
- `permission_ready`
- `permission_denied`
- `expired`
- `unverified`
- `unavailable`

## Endpoints relevantes
- `GET /api/social/status`
- `POST /api/social/diagnostics`
- `POST /api/social/metrics/refresh`
- `GET /api/social/requirements`
- `GET /api/social/connect`
- `GET /api/social/callback`
- `POST /api/social/select-page`
- `POST /api/social/publish`
- `POST /api/social/schedule`
- `GET /api/marketing/analytics`
- `GET /api/marketing/site-publishing/status`

## Dados / coleções relevantes
- `social_connections`
- `social_posts`
- `social_jobs`
- `marketing_post_metrics`
- `marketing_organic_actions`

## Situação conhecida por ambiente

### Preview
Pode continuar a mostrar:
- `connection_state=degraded`
- `insights_status=unverified`
- `metrics_mocked=true`

Isto é aceitável quando a ligação guardada no preview não tem um token Meta válido com insights confirmados.

### Produção
As correções de código deste fork precisam de **redeploy** para chegarem à produção.

Mesmo com permissões ativadas na app Meta, o token/oauth em produção pode ainda precisar de:
- reconnect Meta
- nova validação do token
- confirmação de scopes realmente concedidos à sessão/token

## Ficheiros de referência
- `/app/backend/routers/social.py`
- `/app/backend/routers/marketing.py`
- `/app/backend/routers/site_publishing.py`
- `/app/frontend/src/pages/Marketing.jsx`
- `/app/frontend/src/components/marketing/MetaConnectionSection.jsx`
- `/app/frontend/src/components/marketing/SiteChangeHistorySection.jsx`
- `/app/backend/tests/test_meta_metrics_readiness.py`
- `/app/backend/tests/test_meta_insights_api.py`
- `/app/backend/tests/test_site_change_history.py`

## Credenciais de teste
Ver `/app/memory/test_credentials.md`

## Última validação neste fork
- `pytest -n 0 backend/tests/test_meta_metrics_readiness.py backend/tests/test_meta_credentials.py backend/tests/test_meta_metrics_refresh.py` → **12 passed**
- `auto_frontend_testing_agent` → **PASS**
- `deep_testing_backend_v2` → **PASS**
- `testing_agent` → `/app/test_reports/iteration_46.json` **PASS**
- reorganização do Marketing validada em `/app/test_reports/iteration_47.json` → **PASS**
- simplificação visual compacta do Marketing validada em `/app/test_reports/iteration_48.json` → **PASS**
- painel visual de Alterações do Site validado em `/app/test_reports/iteration_49.json` → **PASS**
- comparação inline do diff visual validada em `/app/test_reports/iteration_50.json` → **PASS**

## Próximas prioridades
- **P0:** validar em produção após redeploy se o estado Meta deixa de ficar preso em mocked quando o token tiver insights reais
- **P1:** homepage parcialmente gerida pelo Site Publishing Gateway
- **P1:** consistência SEO (canonical, sitemap, base URL alinhados ao domínio `www`)
- **P2:** geração automática de criativos
- **P2:** scoring de campanhas
- **P2:** UX da integração ERP