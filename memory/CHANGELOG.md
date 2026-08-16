# CHANGELOG — CEO AI

## 2026-08-16 — Hardening do readiness de insights Meta
- `backend/routers/social.py`
  - parsing de scopes a partir de `granted_scopes` e `granular_scopes`
  - novos estados: `insights_status`, `insights_permissions_ready`, `report_source`
  - probe real de insights para distinguir permissões de dados reais
  - auto-refresh de diagnóstico para estados por validar
  - `/api/social/metrics/refresh` agora devolve razões mais claras
- `frontend/src/components/marketing/MetaConnectionSection.jsx`
  - badges e copy mais claros para:
    - analytics reais
    - permissões OK mas sem dados
    - mocked / token sem insights
- testes adicionados/atualizados:
  - `backend/tests/test_meta_metrics_readiness.py`
  - `backend/tests/test_meta_insights_api.py`

## 2026-08-16 — Meta metrics readiness fix
- inclusão dos scopes de insights no Social Media Agent
- endpoint `POST /api/social/metrics/refresh`
- UI a mostrar live vs mocked com mais honestidade

## 2026-08-16 — Meta credentials configuradas no preview
- `META_APP_ID`, `META_APP_SECRET`, `META_CONFIG_ID`, `META_GRAPH_VERSION`
- backend reiniciado e validado

## 2026-08-14 — Separação definitiva Growth vs Social
- Growth Agent isolado do social publishing
- Social Media Agent isolado do site/SEO
- sidebar e página Marketing reorganizadas por responsabilidade

## 2026-08-13 — Growth Agent e gateway do site
- gateway interno de publicação do site
- overrides seguros de secções públicas
- growth analytics com GA4/GSC/internal tracking

## 2026-08-13 — Marketing analytics, fila e briefing
- workflow editorial com aprovação/agendamento/publicação
- analytics editoriais
- briefing diário
- fila visual de execução