# Docker Smoke Test Checklist

Run from a machine with container-registry access. Each step includes the exact command and
what a pass looks like.

```bash
# 1. Build images
docker compose build

# 2. Start the full stack
docker compose up -d

# 3. Wait for health
docker compose ps   # all three services should show "healthy" within ~60s

# 4. Verify migration head is 0010
docker compose exec postgres psql -U ctec -d ctec -c "SELECT version_num FROM alembic_version;"
# expect: 0010_ontology_bindings

# 5. Verify ontology seeding is complete
curl -s http://localhost:8000/api/v1/ontologies | python3 -m json.tool
# expect: concept_count 10, relationship_count 7, status "Published", quality.overall_score 1.0

# 6. Verify backend health
curl -s http://localhost:8000/health
# expect: {"status":"healthy"}

# 7. Verify ontology list/detail/version/JSON-LD endpoints
curl -s http://localhost:8000/api/v1/ontologies/supplier-risk | python3 -m json.tool
curl -s http://localhost:8000/api/v1/ontologies/supplier-risk/versions/1.0 -o /dev/null -w "%{http_code}\n"
curl -s "http://localhost:8000/api/v1/ontologies/supplier-risk/export?format=json-ld" | python3 -m json.tool

# 8. Verify frontend responds
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
# expect: 200

# 9. Verify Ontology Studio route responds
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/ontology-studio
# expect: 200

# 10. Verify connector catalog and quality API
curl -s http://localhost:8000/api/v1/ontologies/connectors/catalog | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['connectors']), [c['maturity'] for c in d['connectors']])"
# expect: 9 connectors, only Skeleton Available / Roadmap labels

# 11. Verify Supplier Risk activation (requires real OIDC config — see DEMO_RUNBOOK.md)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/supplier-risk
# expect: 200 (page loads; actual submission requires a real bearer token)

# 12. Restart backend and frontend containers
docker compose restart backend frontend
docker compose ps   # wait for healthy again

# 13. Confirm ontology data persists (should NOT need re-seeding — check backend logs)
docker compose logs backend --tail=50 | grep -i "ontology seed"
# expect: created counts of 0 (idempotent — nothing new created on restart)
curl -s http://localhost:8000/api/v1/ontologies | python3 -c "import json,sys; print(json.load(sys.stdin)['ontologies'][0]['concept_count'])"
# expect: 10 (unchanged)

# 14. Confirm the application remains usable
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/ontology-studio
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health

# 15. Confirm no credentials appear in logs
docker compose logs | grep -iE "CTEC_RUNTIME_HANDOFF_KEY=|password|secret" 
# expect: no actual secret VALUES printed (env var names appearing alone are fine;
# review any match manually before treating this as a pass)
```

## Manual browser verification (for the credentialed/human environment)

The above proves the API and container layer. To confirm the actual rendered UI:

1. Open http://localhost:3000/ontology-studio in a real browser.
2. Confirm the overview panel shows real counts/version/quality (not "Loading…" stuck).
3. Click a concept node in the graph; confirm the detail panel appears.
4. Confirm all 9 connectors render with correct maturity badges.
5. Click **Open Supplier Risk Application**; confirm navigation and the "Powered by
   Supplier Risk Enterprise Ontology v1.0" line.
6. Submit a supplier-risk assessment (requires a real OIDC login); confirm the result shows
   the ontology attribution line and semantic path.

This step was not executed from the authoring sandbox (no Chromium available, and no
registry access to build/run the containers at all — see `DEMO_RUNBOOK.md`). It has instead
been covered by: (a) direct verification that the real backend API returns correct data when
run standalone in the sandbox (not containerized), (b) jsdom-based component tests exercising
real click interactions and DOM assertions against realistic API response shapes, and (c)
confirmation that both Dockerfiles parse and begin building correctly up to the point where
registry access is required.
