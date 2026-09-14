# Noetva Azure Zero-to-Deployment Guide

**Authoritative source SHA:** `68780c79e7be7507852e800131198587641d4bec` (`main`, independently verified via `git rev-parse origin/main` and the GitHub API before writing this guide)

**Status of this document:** documentation only. No command in this guide has been executed while writing it. No Azure resource, GitHub setting, secret, or application/infrastructure source file was created, modified, or deleted.

**Who this guide is for:** a software developer who knows Git, Docker, a terminal, and general software development — and has **never used Microsoft Azure, Microsoft Entra, or GitHub-to-Azure OIDC before**. Nothing about Azure is assumed. Every click, every value, and every command is spelled out.

**What you will have when you finish:** Noetva running in a real Azure **DEV** environment — frontend and backend reachable over HTTPS, authenticated through a real Microsoft Entra External ID tenant, connected to a private PostgreSQL database, correctly tenant-isolated, observable in Log Analytics, budget-controlled, backed up, restore-tested, and operable through Noetva's own governed Start/Stop/Extend/Hold automation.

**What you will NOT deploy:** DEMO, STAGING, or PRODUCTION. This guide is DEV-only, on purpose, everywhere.

---

## Command labels used throughout this guide

Every command in this guide carries one label. Know what a command does before you run it.

| Label | Meaning |
|---|---|
| `[LOCAL — SAFE]` | Runs only on your own machine. Touches nothing in Azure or GitHub. |
| `[AZURE READ-ONLY]` | Reads Azure state. Cannot change anything. |
| `[AZURE MUTATION]` | Creates or changes something in Azure. Costs may begin. Run only when the step tells you to. |
| `[GITHUB MUTATION]` | Changes a GitHub repository setting, secret, variable, or environment. |
| `[ENTRA MUTATION]` | Changes your Microsoft Entra External ID tenant. |
| `[DATABASE MUTATION]` | Changes data or schema inside the PostgreSQL database. |
| `[DESTRUCTIVE — APPROVAL REQUIRED]` | Deletes something, possibly permanently. Never run without explicit, current approval from your Technical Lead. |

---

# PART 0 — How to use this guide

Noetva is a governed enterprise product. "Deploying Noetva into Azure DEV" means: standing up one full, working copy of Noetva's frontend, backend, and database inside a Microsoft Azure subscription, wired up to real (not simulated) identity, networking, and monitoring — but sized and priced for engineering use, not customer traffic.

**Roughly, in order, you will:**

1. Get your local tools ready and lock down GitHub security (Parts 1–10).
2. Log into the correct Azure subscription and understand the Portal (Parts 6–7).
3. Create the "foundation" resources: network, database, registry, secrets vault, identities (Parts 11–18).
4. Connect GitHub to Azure without ever storing a password (Part 19), and connect a real identity provider (Parts 21–22).
5. Deploy the actual Noetva application in two passes (Parts 23–32).
6. Prove it actually works — login, tenant isolation, security controls (Parts 33–36, 48–50).
7. Turn on cost control, backup, and Noetva's own automatic Start/Stop system (Parts 37–47).
8. Sign off with a formal acceptance record, then leave DEV in its default, cheapest state (Parts 51–56).

**What you need before starting:** an approved Azure subscription, administrator access to the `manoj96-alt/CTEC` GitHub repository, and about a day of focused time for the first pass (Azure resource creation, especially PostgreSQL and Entra, is not instant).

**What this guide will NOT create:** a `demo`, `staging`, or `production` environment. Noetva's source code is *capable* of supporting those environments later — you will see their names appear in configuration files — but this guide never instructs you to create their actual Azure resources. If you find yourself about to create anything named `staging`, `demo`, or `prod`/`production`, **stop** — that is out of scope for this guide.

---

# PART 1 — Azure for a complete beginner

Skip this part only if you have deployed real infrastructure to Azure before. Everyone else: read every definition once, even if it feels slow. You will refer back to this part constantly.

**Microsoft Azure** is Microsoft's cloud platform — a huge collection of rentable computers, databases, networks, and services, billed by usage.

**Azure Portal** (`portal.azure.com`) is the web UI for Azure. Almost everything you can do with a command, you can also do by clicking through the Portal — this guide shows you both.

**Azure account** is the identity you sign into Azure with — typically a Microsoft work or personal account (an email address).

**Microsoft Entra ID** is Microsoft's identity system (formerly called "Azure Active Directory"). It answers the question "who is this, and what can they do?" — for *both* people managing Azure resources *and*, separately, for Noetva's own end users (more on that critical distinction below).

**Azure Directory / Tenant** is one specific instance of Entra ID — a walled-off identity boundary. Your Azure account lives inside exactly one Azure Directory tenant (unless you're a guest in others). This tenant is what decides who can log into the Portal and manage resources.

**Azure Subscription** is the *billing and access* boundary underneath a Directory tenant. All of Noetva's Azure resources will live inside one subscription. A tenant can contain multiple subscriptions (e.g. one for engineering, one for production) — Noetva uses one subscription for now.

**Resource Group** is a folder-like container inside a subscription. Every resource (a database, a network, a container) belongs to exactly one resource group. Noetva creates one resource group per environment: `rg-noetva-dev` for what you're building in this guide.

**Azure Region** is a physical location where Microsoft's datacenters run — e.g. "East US 2". Noetva's frozen default region is `eastus2`. All resources you create in this guide go there.

**Azure Resource** is any single thing Azure manages for you — one database server, one network, one container app, one secret vault. Everything in Azure is "a resource."

**Azure CLI** (the `az` command) is the official command-line tool for controlling Azure from a terminal. You install it once (Part 3) and use it throughout this guide.

**Bicep** is Microsoft's language for describing Azure infrastructure as code — instead of clicking through the Portal to create ten resources by hand, you write (or, in Noetva's case, *already have written for you*) a `.bicep` file describing exactly what should exist, and Azure creates it all in one command. Noetva's entire DEV infrastructure is already written in Bicep, at `infra/azure/**` in the repository — your job in this guide is mostly to *run* it correctly and *configure the things Bicep can't do for you* (like your GitHub account, or your identity provider), not to write new Bicep.

**Managed Identity** is an identity Azure itself manages for one specific Azure resource, with **no password and no secret a human ever sees**. Noetva's backend, its database-migration process, and its GitHub Actions automation all authenticate to Azure using managed identities — never a stored password.

**Service Principal** is an older, more general form of "an identity for software, not a person." A managed identity is a special, safer kind of service principal that Azure fully manages for you.

**OIDC (OpenID Connect)** is an industry-standard protocol for proving identity without a shared secret. Noetva uses OIDC twice, for two *different* purposes — do not conflate them:
1. **GitHub → Azure OIDC**: lets GitHub Actions prove to Azure "I am really a workflow run from the `manoj96-alt/CTEC` repository" and get a short-lived Azure credential, with zero stored Azure password ever.
2. **End-user → Noetva OIDC**: lets a real human log into the Noetva frontend through Microsoft Entra External ID and get a token the backend trusts.

**VNet (Virtual Network)** is a private, isolated network inside Azure — like your own private LAN, but in the cloud. Noetva's database lives inside a VNet and has **no public internet address at all**.

**Subnet** is a smaller, named slice of a VNet's IP address range. Noetva has one subnet for its Container Apps and a separate one for PostgreSQL.

**Private DNS** lets resources inside a VNet find each other by name (e.g. `noetva-dev-eus2-pg.postgres.database.azure.com`) without that name resolving to anything on the public internet.

**Container** is a packaged, runnable copy of an application (Noetva's backend or frontend), built from a `Dockerfile` — if you've used Docker, you already understand this.

**Container Registry (ACR)** is where Azure stores your built container images before Azure Container Apps runs them — like a private Docker Hub, owned by you.

**Container Apps** is Azure's managed service for running containers without you managing servers yourself. Noetva's backend and frontend each run as one Container App.

**PostgreSQL Flexible Server** is Azure's managed PostgreSQL database service. Noetva's entire dataset lives here.

**Key Vault** is Azure's secret-storage service — passwords, connection strings, and keys live here, never in source code or plain configuration.

**Log Analytics** is where all of Noetva's logs (backend errors, container restarts, migration output) land, searchable.

**Azure Monitor** watches metrics (like "is PostgreSQL storage over 80% full?") and can alert a human by email when something crosses a threshold.

**Storage Account / Azure Table Storage** is a simple, cheap key-value database service. Noetva uses exactly one small table in it to remember whether each environment is currently "running" or "stopped" — this is separate from the main PostgreSQL database.

**Azure Cost Management** is where you see what you're actually being billed, and where budgets/spending-alerts live.

**The hierarchy, all together:**

```
Your Azure Account (an email address)
   |
   v
Azure Directory / Tenant  (owns the subscription -- "who can manage Azure")
   |
   v
Azure Subscription  (the billing boundary)
   |
   v
Resource Group: rg-noetva-dev
   |
   +---- Network (VNet, subnets, private DNS)
   +---- PostgreSQL Flexible Server
   +---- Azure Container Registry
   +---- Key Vault
   +---- Container Apps (frontend, backend, migration Job)
   +---- Log Analytics + Azure Monitor
```

### The single most important distinction in this entire guide

Three completely different things are all called "a tenant" in different contexts. Confusing any two of them will silently break Noetva's security model. Read this three times:

| Term | What it actually is | Who it's for |
|---|---|---|
| **Azure Directory Tenant** | The Entra identity boundary that owns your Azure *subscription* | People and automation that manage Azure resources (you, `az login`, GitHub Actions) |
| **Microsoft Entra External ID Tenant** | A *separate*, second Entra tenant Noetva creates specifically for its own end users to sign into | Real people using the Noetva product (e.g. a Noetva analyst) |
| **Noetva Application Tenant** (`tenant_id`) | Not an Azure or Entra concept at all — just a plain text value in Noetva's own database, saying "which customer does this data belong to" | Noetva's own multi-tenant data model |

You will set up all three in this guide (Parts 6, 21, 22). They are never the same value. Confusing the Azure Directory tenant with the External ID tenant is the single most common beginner mistake in this entire process.

---

# PART 2 — Complete Noetva Azure architecture

```
                              Developer (you)
                                    |
                                    | git push / gh workflow run
                                    v
                         GitHub Repository (manoj96-alt/CTEC)
                                    |
                                    | GitHub Actions, OIDC (no password)
                                    v
                    +---------------------------------------+
                    |     Azure Managed Identities            |
                    |  id-cicd / id-migration / id-lifecycle   |
                    |  id-backend / id-frontend                |
                    +---------------------------------------+
                                    |
                                    v
                    Azure Container Registry (Basic tier, DEV)
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
          Frontend Container App           Backend Container App
          (Next.js, port 3000)             (FastAPI, port 8000)
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                 PostgreSQL Flexible Server 17 (PRIVATE -- no
                 public network access at all)
                                    |
                                    v
                 VNet 10.20.0.0/16: snet-container-apps / snet-postgres
                 + Private DNS zone

Supporting, all inside rg-noetva-dev unless noted:
  Microsoft Entra External ID  (SEPARATE tenant -- end-user login)
  Key Vault                    (secrets: DB passwords, runtime key)
  Log Analytics + Azure Monitor (3 metric alerts + on-call email)
  Alert Processing Rule        (suppresses alerts during intentional Stop/Start)
  Azure Cost Management Budget (spend alerts)
  Container Apps Job           (runs Alembic migrations -- manual trigger only)

Shared across dev/staging/demo (in rg-noetva-lifecycle, deployed once):
  Azure Storage Table          (remembers each environment's Start/Stop state)
  id-lifecycle managed identity (runs GitHub's Start/Stop/Extend/Hold automation)
```

**One user request, end to end:**

```
User opens https://<frontend-fqdn>
   -> Frontend redirects to Microsoft Entra External ID
   -> User signs in
   -> External ID issues an ACCESS TOKEN containing the configured business-tenant claim
      (local Keycloak: tenant_id; Azure Entra: a namespaced claim, CDD-064 Part 22)
   -> Frontend calls the backend, attaching that access token
   -> Backend validates: issuer, audience, signature, expiry, AND the business-tenant claim
   -> Backend queries PostgreSQL, scoped to that exact tenant
   -> Response returns to the user
```

**One deployment, end to end:**

```
Developer runs "Azure Deploy" in GitHub Actions, choosing environment=dev
   -> GitHub proves its identity to Azure via OIDC (no stored secret)
   -> Backend and frontend images are built and pushed to ACR
   -> The migration Container Apps Job runs (Alembic upgrade head)
   -> The backend Container App is updated to the new image digest
   -> The frontend Container App is updated to the new image digest
   -> A liveness check and an unauthenticated-request-fails-with-401 check run
```

---

# PART 3 — What you need before starting

**Accounts and access (get these BEFORE Part 6):**

- [ ] An Azure account, added to the **specific, approved** Azure subscription for Noetva DEV, with at minimum **Contributor** + **User Access Administrator** on that subscription (temporary — Part 22 explains why).
- [ ] Administrator access to `github.com/manoj96-alt/CTEC` (to configure repository settings, Environments, secrets, and variables).
- [ ] The ability to create a Microsoft Entra External ID tenant (Part 21) — this typically requires the same Azure account to also have permission to create new tenants, or a Global Administrator to do it for you.
- [ ] A real, monitored email address for budget and on-call alerts.

**Local machine tools:**

| Tool | Why Noetva needs it | macOS install | Windows install | Version check `[LOCAL — SAFE]` |
|---|---|---|---|---|
| Git | Clone the repo, check out the exact commit | `brew install git` | `winget install Git.Git` | `git --version` |
| Docker Desktop | Build backend/frontend images | `brew install --cask docker` | `winget install Docker.DockerDesktop` | `docker --version` |
| Azure CLI | Every Azure operation in this guide | `brew install azure-cli` | `winget install Microsoft.AzureCLI` | `az version` |
| Bicep CLI (bundled with Azure CLI) | Compile/validate Noetva's infrastructure code | (installed automatically on first use) | (installed automatically on first use) | `az bicep version` |
| GitHub CLI | Verify CI, dispatch lifecycle workflows | `brew install gh` | `winget install GitHub.cli` | `gh --version` |
| `psql` | Talk to PostgreSQL directly for bootstrap/verification | `brew install postgresql@17` | install via PostgreSQL installer | `psql --version` |

You do **not** need to install Node.js or Python locally — every build step in this guide runs inside Docker, using the Dockerfiles already in the repository.

---

# PART 4 — Create a deployment worksheet

Before you create anything, open a plain text file on your own machine — **not** a shared document, not a ticket, not Slack — and title it something like `noetva-dev-worksheet.txt`. As you move through this guide, every step that says **"SAVE THIS VALUE"** means: write it into this worksheet, under the exact variable name given. You will need many of these values again, sometimes many parts later.

Pre-fill the worksheet with every row below (leave the Value column blank until each Part fills it in):

| Variable | Meaning | Who provides it | Secret? |
|---|---|---|---|
| `AZURE_SUBSCRIPTION_ID` | Target subscription GUID | Azure (you'll read it) | No |
| `AZURE_SUBSCRIPTION_NAME` | Human-readable subscription name | Azure | No |
| `AZURE_DIRECTORY_TENANT_ID` | Azure Directory tenant that owns the subscription | Azure | No |
| `AZURE_REGION` | `eastus2` (frozen default) | Noetva source | No |
| `RESOURCE_GROUP` | `rg-noetva-dev` | Noetva source | No |
| `GITHUB_ORG` | `manoj96-alt` | Existing | No |
| `GITHUB_REPOSITORY` | `manoj96-alt/CTEC` | Existing | No |
| `DEV_ACR_NAME` | Container registry name (globally unique) | You choose, Bicep-shaped | No |
| `DEV_KEY_VAULT_NAME` | Key Vault name | Bicep-derived | No |
| `DEV_POSTGRES_SERVER_NAME` | `noetva-dev-eus2-pg` | Bicep-derived | No |
| `DEV_FRONTEND_FQDN` | Generated after Pass 1 | Azure generates | No |
| `DEV_BACKEND_FQDN` | Generated after Pass 1 | Azure generates | No |
| `ENTRA_EXTERNAL_ID_TENANT_ID` | Your new External ID tenant's GUID | Entra generates | No |
| `ENTRA_EXTERNAL_ID_DOMAIN` | `<name>.ciamlogin.com` | You choose | No |
| `FRONTEND_APP_CLIENT_ID` | Frontend app registration's client ID | Entra generates | No |
| `BACKEND_API_APPLICATION_ID_URI` | Backend API registration's Application ID URI | Entra generates | No |
| `DEV_NOETVA_TENANT_ID` | A tenant name in Noetva's own data model, e.g. `noetva-dev-tenant` | You choose | No |
| `BUDGET_AMOUNT` | Monthly USD budget for DEV | Founder-approved | No |
| `BUDGET_ALERT_EMAIL` | Budget alert recipient | Founder-supplied | No |
| `ALERT_EMAIL` | On-call recipient for Azure Monitor | Founder-supplied | No |
| `NOETVA_LIFECYCLE_CLIENT_ID` | id-lifecycle identity's client ID | Azure generates (Part 18) | No |
| `NOETVA_LIFECYCLE_STORAGE_ACCOUNT` | Shared lifecycle Storage Account name | Azure generates (Part 18) | No |
| `POSTGRES_ADMIN_PASSWORD` | Flexible Server admin password | You generate | **Yes** |
| `POSTGRES_APP_PASSWORD` | `noetva_app` role password | You generate | **Yes** |
| `POSTGRES_MIGRATE_PASSWORD` | `noetva_migrate` role password | You generate | **Yes** |
| `RUNTIME_HANDOFF_KEY` | Backend's internal signing key | You generate | **Yes** |

Rows marked **Secret? Yes** never get typed into your worksheet's *value* column at all — write only a reminder like "stored in Key Vault `postgres-admin-password`, generated <date>". Part 17 explains exactly where secret values actually live.

---

# PART 5 — Security before Azure

**Do this before you create a single paid Azure resource.** Skipping this is the single most common way a real incident happens later.

### Step 5.1 — Enable GitHub secret scanning and push protection

**What you are doing:** turning on GitHub's automatic detection of accidentally-committed secrets, and its *prevention* of committing them in the first place.

**Why:** as of the last source-closure phase, this repository's secret scanning, push protection, and branch protection were all confirmed **disabled** via the GitHub API. You are about to start putting real Azure identity information into this repository's GitHub Environment configuration — this must be on first.

**Where:** `https://github.com/manoj96-alt/CTEC` → **Settings** → **Code security**.

**Action:** `[GITHUB MUTATION]` — click **Enable** next to:
- Secret scanning
- Push protection

**Verify:** `[AZURE READ-ONLY]` is wrong here — this is GitHub, not Azure:

```bash
# [GITHUB MUTATION -- read-only check, but requires an authenticated gh]
gh api repos/manoj96-alt/CTEC --jq '.security_and_analysis'
```

Expected: both `secret_scanning.status` and `secret_scanning_push_protection.status` read `"enabled"`.

**STOP IF:** your GitHub plan does not offer these features for this repository. Do not substitute a weaker manual process — escalate to your GitHub org administrator first.

### Step 5.2 — Enable branch protection on `main`

**Where:** **Settings** → **Branches** → **Add branch protection rule** (or **Rulesets**, depending on your GitHub plan).

**Action:** `[GITHUB MUTATION]` — protect `main`:
- Require a pull request before merging.
- Require status checks to pass (`backend`, `frontend`, `containers` — the same checks `ci.yml` already runs).
- Do not allow force pushes.
- Do not allow branch deletion.

**Verify:**

```bash
# [AZURE READ-ONLY is wrong here too -- GitHub API read]
gh api repos/manoj96-alt/CTEC/branches/main/protection
```

Expected: a JSON object describing the rule (not a 404 "Branch not protected").

### Step 5.3 — Configure GitHub Environment protection

You will create GitHub **Environments** named `dev` and `production` later (Part 20). For now, just know: an Environment can require a human reviewer to approve a workflow run before it proceeds, and can restrict which branches may deploy to it. Decide your `dev` environment's protection level with your Technical Lead before Part 20 — this guide does not prescribe a specific reviewer policy, only that you make a deliberate choice, not a default one.

**Do not proceed to Part 6 until Steps 5.1 and 5.2 both show enabled/protected.**

---

# PART 6 — Log in to Azure safely

This is the most consequential five minutes in the entire guide. Getting the wrong subscription here means everything downstream is billed to, and visible from, the wrong place.

### Step 6.1 — Sign in

```bash
# [AZURE MUTATION -- opens a browser, creates a local CLI session -- no Azure resource is created]
az login
```

A browser window opens. Sign in with the Azure account from Part 3's prerequisites. Close the browser tab when it says you can return to the CLI.

### Step 6.2 — List every subscription you can see

```bash
# [AZURE READ-ONLY]
az account list --output table
```

You'll see a table with columns including `Name`, `SubscriptionId`, `TenantId`, and `IsDefault`. **Do not trust `IsDefault`** — Azure CLI will happily default to whichever subscription you touched last, on any machine, which may not be the one approved for Noetva.

### Step 6.3 — Explicitly set the subscription

```bash
# [AZURE MUTATION -- this only changes your LOCAL CLI's context, not any Azure resource -- but it is still gated here because every command after this depends on it being exactly right]
az account set --subscription "<AZURE_SUBSCRIPTION_ID>"
```

### Step 6.4 — Show and record

```bash
# [AZURE READ-ONLY]
az account show --output table
```

**SAVE THESE VALUES** into your worksheet right now:

```
AZURE_SUBSCRIPTION_ID   = ______________________
AZURE_SUBSCRIPTION_NAME = ______________________
AZURE_DIRECTORY_TENANT_ID = ____________________
Signed-in account        = ____________________
```

### STOP — human checkpoint

Read what you just wrote out loud, or to a teammate. Confirm every one of these four values against the subscription your Technical Lead actually approved for Noetva DEV — not "a" subscription, not "the one I usually use." **Do not proceed to Part 7 until this is confirmed.**

**Why this matters:** deploying to the wrong subscription creates real Azure resources billed to the wrong cost center indefinitely until someone notices, and creates a second, unreviewed copy of Noetva's identity and secret surface that nobody is watching.

---

# PART 7 — A short tour of the Azure Portal

Open `https://portal.azure.com` in a browser and sign in with the same account as Part 6.

- **The search bar at the top** is how you find everything in this guide. Typing "Resource groups" and pressing Enter is faster than navigating menus — this guide will always tell you what to type here.
- **Subscriptions** (search "Subscriptions") shows every subscription you can see — confirm the same subscription ID from Part 6 appears here.
- Every resource's page (once it exists) has, on the left:
  - **Overview** — the resource's name, status, and key properties.
  - **Activity log** — every change ever made to this resource, by whom, when. Your first troubleshooting stop after any unexpected failure.
  - **Access control (IAM)** — who/what has permission to do what to this resource.
  - **Networking** — how this resource is reachable (or, for Noetva's Postgres, deliberately *not* reachable).
  - **Metrics** — live numeric charts (CPU, connections, storage used).
  - **Logs** — a query interface into Log Analytics (Part 35).
  - **JSON View** (top right of Overview) — the raw definition of the resource, useful for confirming an exact setting when you're unsure what the UI label maps to.

You will return to this tour constantly. There is nothing else to memorize yet — you'll learn each specific resource type's page as you create it.

---

# PART 8 — Cost safety before deployment

Azure resources cost real money from the moment they're created, in some cases even while "stopped." Before Part 11 (your first resource-creating command), get two things from your Technical Lead/founder:

**SAVE THESE VALUES:**
```
BUDGET_AMOUNT      = ______________________  (e.g. "100" USD/month)
BUDGET_ALERT_EMAIL = ______________________
```

**What in DEV is likely to cost money, roughly, per month if left running:**

| Resource | Running cost | Cost while Noetva-DORMANT (Stopped) | Residual cost regardless |
|---|---|---|---|
| Container Apps (frontend+backend) | Usage-based, `minReplicas=0` so scales toward $0 with no traffic | **$0** — Noetva deactivates the revision entirely, not just scale-to-zero | — |
| PostgreSQL compute (`Standard_B1ms`, Burstable) | Billed while running | **$0** — the server is genuinely stopped, not merely idle | — |
| PostgreSQL storage + 7-day backups | Billed | **Still billed** | 32 GiB storage + backups |
| Azure Container Registry (Basic) | Fixed monthly charge | Fixed monthly charge | Same regardless of lifecycle state |
| Key Vault | Operation-based, near-zero if idle | Near-zero | — |
| Log Analytics | Ingestion + 30-day retention | Retained data still billed | — |
| Shared lifecycle Storage Table | Negligible | Negligible | — |

**Never think or say "stopped means free."** It does not. Part 51 shows you how to actually measure this once DEV exists.

---

# PART 9 — Resource naming

Noetva's naming is fixed by the Bicep source, not invented per-deployment. Read `infra/azure/main.bicep`/`resources.bicep` yourself if you want to confirm; this table is derived directly from it.

| Resource | Expected DEV name | Globally unique? | Renameable later? |
|---|---|---|---|
| Resource Group | `rg-noetva-dev` | No (unique per subscription only) | No — would require full recreation |
| VNet | `noetva-dev-eus2-vnet` | No | No |
| PostgreSQL server | `noetva-dev-eus2-pg` | Yes (part of a public DNS suffix) | No |
| Container Registry | `noetvadeveus2acr` (letters/digits only, no hyphens — ACR naming rule) | **Yes** | No |
| Key Vault | `noetva-dev-eus2-kv` | Yes | No |
| Container Apps Environment | `noetva-dev-eus2-cae` | No | No |
| Backend Container App | `noetva-dev-eus2-backend` | No | No |
| Frontend Container App | `noetva-dev-eus2-frontend` | No | No |
| Migration Job | `noetva-dev-eus2-migrate` | No | No |
| Log Analytics workspace | `noetva-dev-eus2-log` | No | No |
| Shared lifecycle Storage Account | `noetva<prefix>lcst` (24-char limit, alphanumeric only) | **Yes** | No |
| Shared lifecycle resource group | `rg-noetva-lifecycle` | No | No |

**Azure naming restrictions that bit real deployments before, so know them now:** Storage Account and ACR names must be **globally unique across all of Azure**, lowercase alphanumeric only, and — for Storage Accounts — 3–24 characters. If a name is taken, Bicep deployment fails with a clear "name already in use" error; you do not need to memorize a fallback, just be aware it can happen and isn't a sign of a broken deployment.

---

# PART 10 — Resource providers

**What a Resource Provider is:** Azure organizes every resource type under a "provider" namespace (e.g. `Microsoft.DBforPostgreSQL` for databases). A provider must be **registered** on your subscription before you can create that type of resource — most are pre-registered on a new subscription, but never assume.

**Check (`[AZURE READ-ONLY]`):**

```bash
for provider in Microsoft.App Microsoft.DBforPostgreSQL Microsoft.ContainerRegistry \
                Microsoft.KeyVault Microsoft.Network Microsoft.Storage \
                Microsoft.OperationalInsights Microsoft.AlertsManagement \
                Microsoft.Consumption Microsoft.ManagedIdentity Microsoft.Insights; do
  az provider show --namespace "$provider" --query "{namespace:namespace, state:registrationState}" -o tsv
done
```

**If any shows `NotRegistered` (`[AZURE MUTATION]`):**

```bash
az provider register --namespace "<PROVIDER_NAME>"
```

Registration can take a few minutes — poll the same read-only command above until it says `Registered` before continuing. Do not register providers Noetva doesn't use "just in case."

---

# PART 11 — Resource Group

**What you are doing:** creating the folder every DEV resource will live inside.

**Why:** every Azure resource must belong to exactly one Resource Group; grouping by environment (`rg-noetva-dev`) is how you'll later delete, budget, or tag everything for DEV as one unit.

**Which Azure service:** Azure Resource Manager (no cost by itself).

**Important:** you do **not** manually create this Resource Group. `infra/azure/main.bicep` is a **subscription-scoped** template — it creates `rg-noetva-dev` itself, as the very first thing it does, in Part 23's Pass 1. This Part exists only so you understand what you're about to see appear.

**Its tags, fixed in code (not something you choose):** `environment: dev`, `application: noetva`, `managed-by: bicep`, `lifecycle-policy: dormant-by-default`, `auto-shutdown: true`, `owner: noetva-engineering`, `purpose: engineering`, `customer-facing: false`, `cost-center: noetva-dev`.

**Verify, after Part 23 (`[AZURE READ-ONLY]`):**

```bash
az group show --name rg-noetva-dev --query "{name:name, location:location, tags:tags}" -o json
```

**Expected result:** `location: eastus2`, tags exactly as listed above.

---

# PART 12 — Networking from zero

### First, the concepts

**IP address:** a unique number identifying a device on a network, like `10.20.0.5`.

**CIDR notation** (e.g. `10.20.0.0/16`): a compact way to describe a *range* of IP addresses. The `/16` means the first 16 bits are fixed (`10.20`), leaving room for 65,536 addresses inside that range.

**Private IP:** an address only reachable from inside the same private network — never routable from the public internet. Ranges like `10.0.0.0/8` are reserved by convention for exactly this.

**Public IP:** an address reachable from anywhere on the internet.

**VNet (Virtual Network):** a private address space you own inside Azure, sliced into subnets.

**Subnet:** a smaller CIDR range carved out of a VNet's range, often dedicated to one purpose.

**Delegation:** telling Azure "this specific subnet is reserved exclusively for this specific Azure service" — Noetva delegates one subnet to Container Apps and a separate one to PostgreSQL, so neither can accidentally share the other's network rules.

**Private DNS Zone:** a DNS namespace that only resolves *inside* a linked VNet — so `noetva-dev-eus2-pg.postgres.database.azure.com` means something to Noetva's backend, and means nothing (doesn't even resolve) to anyone on the public internet.

**Ingress / Egress:** ingress is traffic coming *into* a resource (a user's browser reaching the frontend); egress is traffic *leaving* a resource (the backend calling an external API).

### Noetva's actual DEV network (source-derived, from `infra/azure/modules/network.bicep`)

```
VNet noetva-dev-eus2-vnet          10.20.0.0/16
  |
  +-- snet-container-apps          10.20.0.0/23   delegated to Microsoft.App/environments
  |     (no NAT Gateway attached in DEV)
  |
  +-- snet-postgres                10.20.2.0/24   delegated to Microsoft.DBforPostgreSQL/flexibleServers

Private DNS zone: noetva-dev-eus2.postgres.database.azure.com
  linked to the VNet above, registrationEnabled: false
```

**Why PostgreSQL must stay private:** Noetva's entire tenant-isolation security model assumes the database is unreachable from anywhere except the backend's own network. `postgresql.bicep` sets `publicNetworkAccess: 'Disabled'` — there is no toggle in this guide to turn that on, ever, for DEV.

**Why DEV has no NAT Gateway:** a NAT Gateway gives outbound (egress) traffic a single, stable public IP address — useful when an external partner needs to allowlist Noetva's IP. DEV doesn't need that yet (`enableNatGateway: false` in `environments/dev/main.parameters.json`), so egress traffic leaves through Container Apps' shared, non-static default outbound IP. Staging/prod use a NAT Gateway; DEV deliberately does not, to save cost.

### Creating the network

There is no standalone "create the VNet" step — `network.bicep` is one of ~14 modules `resources.bicep` composes automatically during Pass 1 (Part 23). This Part exists so the values above aren't a surprise when you verify them.

**Verify, after Pass 1 (`[AZURE READ-ONLY]`):**

```bash
az network vnet show --resource-group rg-noetva-dev --name noetva-dev-eus2-vnet -o json
az network private-dns zone list --resource-group rg-noetva-dev -o table
```

**Expected result:** the VNet's `addressSpace.addressPrefixes` shows `["10.20.0.0/16"]`; two subnets present; one private DNS zone listed.

**SAVE THIS VALUE:**
```
DEV_VNET_NAME = noetva-dev-eus2-vnet
```

Used later in: Part 13 (PostgreSQL's networking screen references this VNet).

**Common beginner mistake:** trying to give PostgreSQL a public IP "just to test connectivity quickly." Don't. Every verification in this guide happens either from inside the same VNet (via the running backend) or via `psql` tunneled correctly — never by exposing Postgres.

---

# PART 13 — PostgreSQL Flexible Server

**What it is:** Azure's fully-managed PostgreSQL — you get a real Postgres 17 server without managing the underlying VM, patching, or backup infrastructure yourself.

### Noetva's exact DEV configuration (source-derived — do not substitute different values)

| Setting | DEV value | Why |
|---|---|---|
| Engine version | 17 | Hardcoded in `postgresql.bicep` |
| Compute tier | Burstable | Cheapest tier that still gives real, if bursty, performance |
| SKU | `Standard_B1ms` | Smallest practical Burstable SKU |
| Storage | 32 GiB | `environments/dev/main.parameters.json` |
| Backup retention | 7 days | Same file |
| High availability | Disabled | DEV doesn't need HA; staging/prod do |
| Networking | **Private only** — no public network access | Non-negotiable security invariant |
| TLS | `require_secure_transport = on` | Enforced server-side, not just client-preferred |
| Admin login | `noetva_pg_admin` | Bicep default |
| Database name | `ctec` | Hardcoded |
| Extension allow-list | `pgcrypto` | Required by migration `0001` for `gen_random_uuid()` |

This entire server is created automatically by Pass 1's Bicep deployment (Part 23) — you do not click through PostgreSQL creation screens by hand for DEV. If you ever *do* find yourself in the Portal's "Create PostgreSQL Flexible Server" wizard for a Noetva environment, stop — that means something has gone wrong with the Bicep path, not that manual creation is an accepted fallback (Part 74 explains why: it would create drift from source).

**Generate the admin password now**, `[LOCAL — SAFE]`:

```bash
python3 -c "import secrets, string; a = string.ascii_letters + string.digits; print(''.join(secrets.choice(a) for _ in range(24)))"
```

Do not type this into your worksheet's value column. Part 17 shows you where it actually goes (Key Vault).

**Verify, after Pass 1 (`[AZURE READ-ONLY]`):**

```bash
az postgres flexible-server show --resource-group rg-noetva-dev --name noetva-dev-eus2-pg \
  --query "{state:state, version:version, sku:sku, ha:highAvailability, network:network}" -o json
```

**Expected result:** `state: "Ready"`, `version: "17"`, `sku.name: "Standard_B1ms"`, `ha.mode: "Disabled"`.

**Cost impact:** this is the single largest DEV cost while running. Genuinely $0 while Stopped (Part 43), but storage/backup remain billed regardless (Part 8).

**Security impact:** this is the resource protecting all of Noetva's data. Never weaken its `publicNetworkAccess` setting, ever, for any reason, in any environment this guide covers.

---

# PART 14 — Verify PostgreSQL security

Run every check below (`[AZURE READ-ONLY]` unless noted) after Pass 1.

**1. Confirm no public network access:**
```bash
az postgres flexible-server show --resource-group rg-noetva-dev --name noetva-dev-eus2-pg \
  --query "network.publicNetworkAccess" -o tsv
```
Expected: `Disabled`.

**2. Confirm private DNS resolves from inside the VNet only** — this genuinely cannot be proven from your own laptop (which is outside the VNet by design). Confirm it later, indirectly, when the backend Container App (also inside the VNet) successfully connects in Part 30.

**3. Confirm TLS is required:**
```bash
az postgres flexible-server parameter show --resource-group rg-noetva-dev --server-name noetva-dev-eus2-pg \
  --name require_secure_transport --query "value" -o tsv
```
Expected: `ON`.

**4. Confirm version and SKU** — already shown in Part 13's verify step.

**5. Confirm backup retention:**
```bash
az postgres flexible-server show --resource-group rg-noetva-dev --name noetva-dev-eus2-pg \
  --query "backup.backupRetentionDays" -o tsv
```
Expected: `7`.

**STOP IF any of these do not match** — do not proceed to database bootstrap against a server whose security posture you haven't confirmed.

---

# PART 15 — Database admin / migration / application roles

### The concept, for a beginner

A single "admin" database user for everything is a common shortcut and a real security risk — if your application's every-day connection is compromised, an attacker with admin rights can do anything, including changing the schema or reading every other tenant's data structure. Noetva instead uses **three separate roles**, each with the minimum privilege it actually needs.

| Role | Purpose | Can create/alter tables (DDL)? | Can read/write rows (DML)? | Used by |
|---|---|---|---|---|
| `noetva_app` | Everyday application traffic | **No** | Yes | The backend Container App, at runtime |
| `noetva_migrate` | Schema changes | Yes (owns everything it creates) | Yes | Only Alembic, only inside the migration Job |
| `noetva_pg_admin` (server admin) | Break-glass / one-time setup | Yes (superuser-adjacent) | — | Only `CREATE EXTENSION pgcrypto`, once ever — never referenced by application config |

A helpful mental model: `ALTER DEFAULT PRIVILEGES FOR ROLE noetva_migrate` means every table `noetva_migrate` creates from now on **automatically** grants `noetva_app` exactly DML rights on it — you never have to remember to re-grant after a future migration.

### Bootstrap, exactly, from the real script

**Generate the two remaining passwords now** (`[LOCAL — SAFE]`, same command pattern as Part 13):

```bash
python3 -c "import secrets, string; a = string.ascii_letters + string.digits; print(''.join(secrets.choice(a) for _ in range(24)))"
```

Run it twice more, once for `POSTGRES_APP_PASSWORD`, once for `POSTGRES_MIGRATE_PASSWORD`. Store all three in Key Vault immediately (Part 17) — do not leave them only in shell history.

**Run once, after Pass 1, connected as the server admin (`[DATABASE MUTATION]`):**

```bash
export NOETVA_PG_HOST="noetva-dev-eus2-pg.postgres.database.azure.com"
export NOETVA_PG_ADMIN_USER="noetva_pg_admin"
export NOETVA_PG_ADMIN_PASSWORD="<POSTGRES_ADMIN_PASSWORD, from Key Vault>"
export NOETVA_PG_APP_PASSWORD="<POSTGRES_APP_PASSWORD, from Key Vault>"
export NOETVA_PG_MIGRATE_PASSWORD="<POSTGRES_MIGRATE_PASSWORD, from Key Vault>"
bash infra/azure/scripts/run_db_bootstrap.sh
```

**What this does, explained:** it runs `db-bootstrap/001_create_roles_and_grants.sql`, which is *idempotent* (safe to run more than once): enables the `pgcrypto` extension (once, as admin), creates `noetva_app`/`noetva_migrate` if they don't already exist, sets both their passwords unconditionally, and grants schema `USAGE`/`CREATE` correctly. It never prints a password to the terminal.

**Expected result:** the script's final line reads: `bootstrap complete: noetva_app (DML-only) and noetva_migrate (DDL+DML) exist and are granted correctly`.

**Verify with a real, disposable Postgres 17 container on your own laptop first, if you want confidence before touching the real DEV server** — this is exactly how this guide's own authors proved the script correct without any Azure subscription. `docker run -d --name verify-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ctec -p 15432:5432 postgres:17-alpine`, then point the same script at `localhost:15432`.

---

# PART 16 — Azure Container Registry

**What it is:** a private place to store the Docker images you build for Noetva's backend and frontend, before Azure Container Apps runs them.

**DEV tier: Basic** (confirmed source-derived from `environments/dev/main.parameters.json`'s `acrSku: "Basic"`). Basic is sufficient for DEV's scale; staging/prod use Premium, which adds retention/quarantine/trust policies DEV doesn't need yet.

**Created automatically by Pass 1.** Non-negotiable invariants, already baked into the Bicep, that you must never work around later:

- **Admin user is permanently disabled** (`adminUserEnabled: false`) — all access is via managed identity + RBAC (`AcrPull`), never a shared admin password.
- **Never deploy by mutable tag.** Every image in this guide is deployed by its immutable content digest (`@sha256:...`), never `latest`.

**Verify, after Pass 1 (`[AZURE READ-ONLY]`):**

```bash
az acr show --name <DEV_ACR_NAME> --query "{sku:sku.name, adminUserEnabled:adminUserEnabled, loginServer:loginServer}" -o json
```

**Expected result:** `sku.name: "Basic"`, `adminUserEnabled: false`.

**SAVE THIS VALUE:**
```
DEV_ACR_NAME       = ______________________
DEV_ACR_LOGIN_SERVER = ______________________.azurecr.io
```

Used later in: Part 26 (image build/push), Part 30/31 (deployment).

---

# PART 17 — Key Vault (CDD-067 corrected)

**What a secret is, for a beginner:** any value that would cause harm if leaked — a database password, a signing key. Never in source control, never in a chat message, never in a plain environment file that gets committed.

**Key Vault** is Azure's managed secret store — access is granted per-identity via RBAC, and every read/write is logged.

**Created by the foundation stage of Pass 1** (`deployApplicationTier=false`, Part 23). Its access model: **RBAC-based** (`enableRbacAuthorization: true`), soft-delete on, purge-protection currently off for DEV (source-confirmed — this is a real, disclosed tradeoff, not an oversight).

**Real-Azure finding (CDD-067):** subscription **Owner** does **not** itself grant Key Vault *data-plane* access under `enableRbacAuthorization: true` — an operator with Owner will get `Forbidden`/`ForbiddenByRbac` attempting to read or write secrets here. Before running the commands below, self-assign the data-plane role:

```bash
# [AZURE MUTATION] -- scoped to this one vault only, never subscription-wide
az role assignment create \
  --assignee <your-own-object-id-or-upn> \
  --role "Key Vault Secrets Officer" \
  --scope $(az keyvault show --name <DEV_KEY_VAULT_NAME> --query id -o tsv)
```

RBAC assignments can take up to a few minutes to propagate — if the next command still returns `Forbidden` immediately after this, wait a short bounded interval and retry before escalating; this is expected Azure eventual consistency, not a defect.

**Every Noetva DEV secret — names only, no values, ever, in this guide. Six secrets are required, not five** (CDD-067 Defect 3: the migration Job needs its own full connection string, previously undocumented):

| Secret name | Purpose | Created by | Consumed by |
|---|---|---|---|
| `postgres-admin-password` | Flexible Server admin credential | You, Part 13 (or reset per Part 23's recovery note, if this environment's original value is not safely recoverable) | Human operator only (bootstrap) |
| `postgres-app-password` | `noetva_app` DB credential | You, Part 15 | Assembled into `ctec-database-url` below |
| `postgres-migrate-password` | `noetva_migrate` DB credential | You, Part 15 | Assembled into `ctec-migration-database-url` below |
| `ctec-database-url` | Full backend connection string, built from `postgres-app-password` | You, this Part | Backend Container App (secret reference) |
| **`ctec-migration-database-url`** | Full **migration-role** connection string, built from `postgres-migrate-password` — a *different* value from `ctec-database-url`, never the same credential | You, this Part | Migration Container Apps Job (secret reference) |
| `ctec-runtime-handoff-key` | Backend's internal signing key | You, this Part | Backend Container App |

**Store all six now (`[AZURE MUTATION]`, requires the Key Vault Secrets Officer role above), strictly AFTER Part 15's database roles exist and BEFORE running Pass 1's application stage (`deployApplicationTier=true`, Part 23):**

```bash
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name postgres-admin-password --value "<value>"
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name postgres-app-password --value "<value>"
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name postgres-migrate-password --value "<value>"
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name ctec-database-url --value "postgresql+psycopg://noetva_app:<postgres-app-password>@noetva-dev-eus2-pg.postgres.database.azure.com/ctec"
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name ctec-migration-database-url --value "postgresql+psycopg://noetva_migrate:<postgres-migrate-password>@noetva-dev-eus2-pg.postgres.database.azure.com/ctec"
az keyvault secret set --vault-name <DEV_KEY_VAULT_NAME> --name ctec-runtime-handoff-key --value "$(python3 -c 'import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
```

**Verify (names only, never values, `[AZURE READ-ONLY]`):**

```bash
az keyvault secret list --vault-name <DEV_KEY_VAULT_NAME> -o table
```

Expected: exactly these six names present before proceeding to Part 23's application-stage deployment. A missing `ctec-migration-database-url` will make the migration Job fail to provision, exactly as it did on the first real DEV deployment attempt (CDD-067).

**Never do this:** run `az keyvault secret show` in a shared terminal session, screen-share, or paste output into a ticket. If you must confirm a value exists and is non-empty, check the `list` output's presence only.

---

# PART 18 — Managed identities

### The concept

A **password** is a shared secret a human typed in. A **client secret** is the same idea for software — a long random string that, if leaked, works forever until rotated. A **service principal** is "an identity for software" in general — it can authenticate with a client secret (bad) or something better. A **managed identity** is Azure's own, fully-managed flavor of service principal: Azure creates and rotates its credential material internally, and **no human or code ever sees it**. **OIDC** (Part 19) lets GitHub Actions specifically use a managed identity without even a long-lived Azure-side secret existing at all.

### Every Noetva identity

| Identity | Purpose | Scope | Federated to |
|---|---|---|---|
| `id-cicd` | `azure-deploy.yml`'s build/migrate/deploy jobs | Contributor on `rg-noetva-dev` only (never subscription-wide) | GitHub Environment `dev` |
| `id-migration` | The migration Container Apps Job's runtime | `AcrPull` + Key Vault "Secrets User" only | Not federated to GitHub — used only inside the Job |
| `id-lifecycle` | Start/Stop/Extend/Hold/nightly-sweep/restart-monitor automation | Custom "Noetva Lifecycle Operator" role, on `rg-noetva-dev`/`rg-noetva-staging`/`rg-noetva-demo` | GitHub Environments `dev`, `staging`, `demo` (three separate federated credentials, corrected in R4 — Part 19 explains) |
| `id-backend` | Backend Container App's own runtime | `AcrPull` + Key Vault "Secrets User" | Not federated to GitHub |
| `id-frontend` | Frontend Container App's own runtime | `AcrPull` only — no Key Vault access, it has no runtime secret | Not federated to GitHub |

**Not allowed, anywhere, on any of these:** Owner, subscription-wide Contributor, the `Microsoft.Authorization/*` wildcard, or Monitoring Contributor. Confirmed absent in source (`infra/azure/validation/lifecycle_static_checks.py`'s authority checks).

**Created automatically by Pass 1** (`id-cicd`/`id-migration`/`id-backend`/`id-frontend`) **and by the shared lifecycle control-plane deployment** (`id-lifecycle`, Part 21).

**Verify, after Pass 1 + Part 21 (`[AZURE READ-ONLY]`):**

```bash
az identity list --resource-group rg-noetva-dev -o table
az role assignment list --resource-group rg-noetva-dev -o table
```

---

# PART 19 — GitHub OIDC, from zero

### The old way, and why Noetva doesn't use it

The traditional way to let a CI system deploy to a cloud provider is: create a service principal, generate a long-lived **client secret** (a password, basically), and paste that secret into a CI secret store. This works, but that secret is a standing liability — anyone with access to it can authenticate as that identity indefinitely, until someone remembers to rotate it.

### Noetva's way: OIDC federation

Instead, GitHub Actions itself can generate a short-lived, cryptographically signed token proving "I am really a workflow run from `manoj96-alt/CTEC`, running under GitHub Environment `dev`." Azure is told, in advance (via a **federated credential**), to trust tokens with that *exact* signature and *exact* subject string — no Azure secret is ever generated, stored, or exchanged. Confirm this is true of every Noetva workflow:

```bash
# [LOCAL -- SAFE]
grep -rn "client-secret" .github/workflows/azure-*.yml
```

Expected: no output. Every login step uses `client-id`/`tenant-id`/`subscription-id` only.

### The exact DEV subject

For `id-cicd` (the identity `azure-deploy.yml` uses to actually build/push/deploy), the federated credential's subject — created automatically by Pass 1 — is:

```
repo:manoj96-alt/CTEC:environment:dev
```

This exact string must match the GitHub Environment the workflow job declares (`environment: dev`) at the moment it requests a token — this is not a coincidence you need to configure by hand; `main.parameters.json`'s `githubEnvironmentName: "dev"` already drives it.

### The lifecycle identity's three subjects (R4-corrected)

`id-lifecycle` is shared across dev/staging/demo's lifecycle automation — deployed once via `lifecycle-main.bicep`, in Part 21. It needs **one federated credential per environment it's invoked under**, not one shared credential — this was a real, previously-shipped defect (corrected in Noetva's R4 governance phase; the fix is already merged into the source you're deploying from):

```
repo:manoj96-alt/CTEC:environment:dev
repo:manoj96-alt/CTEC:environment:staging
repo:manoj96-alt/CTEC:environment:demo
```

**No wildcard subject anywhere. No `prod` entry anywhere in the lifecycle federation.** Confirm:

```bash
# [LOCAL -- SAFE]
grep -A3 "param githubEnvironmentNames" infra/azure/modules/lifecycle-identity.bicep
```

Expected: exactly `['dev', 'staging', 'demo']`.

This means, even though this guide only deploys DEV's *application* infrastructure, the shared lifecycle identity's federated credentials for `staging`/`demo` will still exist once you run Part 21 — because it's one shared identity by design. **This is not the same as deploying staging/demo's Container Apps, Postgres, or any other application resource** — you are not doing that in this guide (Part 18 above, and the Part 18 reminder below, cover the distinction).

---

# PART 20 — GitHub Environments, Variables, and Secrets

**Where (`[GITHUB MUTATION]`):** `github.com/manoj96-alt/CTEC` → **Settings** → **Environments** → **New environment** → name it `dev`.

Configure protection rules per your Part 5.3 decision, then add the following. **Variables** (not secret, visible to anyone with repo read access) vs **Secrets** (encrypted, never visible again after creation) — Noetva's own workflow source tells you which is which; do not guess.

| Name | Kind | Value comes from | Consumed by |
|---|---|---|---|
| `AZURE_TENANT_ID` | Variable | Part 6 (`AZURE_DIRECTORY_TENANT_ID`) | Every `azure/login@v2` step |
| `AZURE_SUBSCRIPTION_ID` | Variable | Part 6 | Same |
| `NOETVA_CICD_CLIENT_ID` | Variable | `id-cicd`'s client ID (Part 18, after Pass 1) | `azure-deploy.yml`'s build/migrate/deploy jobs |
| `NOETVA_LIFECYCLE_CLIENT_ID` | Variable | `id-lifecycle`'s client ID (Part 21) | Every lifecycle workflow |
| `NOETVA_LIFECYCLE_STORAGE_ACCOUNT` | Variable | Part 21's output | Every lifecycle workflow |
| `NOETVA_ACR_NAME` | Variable | Part 16 | `azure-deploy.yml` |
| `NOETVA_ACR_LOGIN_SERVER` | Variable | Part 16 | Same |
| `NOETVA_BACKEND_ORIGIN` | Variable | Part 24 (Pass 1 output) | Frontend image build args |
| `NOETVA_OIDC_AUTHORITY` | Variable | Part 21 (`https://<ENTRA_EXTERNAL_ID_DOMAIN>`) | Frontend image build args |
| `NOETVA_OIDC_CLIENT_ID` | Variable | Part 21 | Frontend image build args |
| `NOETVA_OIDC_REDIRECT_URI` | Variable | Part 24 | Frontend image build args |
| `NOETVA_OIDC_POST_LOGOUT_REDIRECT_URI` | Variable | Part 24 | Frontend image build args |
| `NOETVA_PG_ADMIN_PASSWORD` | **Secret** | Part 13 | Lifecycle Stop workflow's DB-session-safety check |
| `NOETVA_DEMO_TEST_PASSWORD` | **Secret** (optional) | Only if you set up a synthetic test login | Start workflow's smoke test |

---

# PART 21 — Microsoft Entra External ID, from zero

### The concepts, explained fully

**Authentication** answers "who are you?" **Authorization** answers "what are you allowed to do, now that I know who you are?" Noetva needs both, but they are different systems entirely — never conflate a successful login with permission to see a specific piece of data.

**Identity provider:** the system that actually verifies a user's credentials and issues a token — for Noetva's end users, that's Microsoft Entra External ID, not your Azure Directory tenant.

**Tenant** (again, in this specific context): the External ID tenant is a completely separate Entra tenant from the one that owns your Azure subscription — created specifically to hold Noetva's own end-user accounts.

**Application registration:** a record inside a tenant describing one app that's allowed to use it — Noetva registers two: the frontend (a public client) and the backend (an API resource).

**Client ID:** a public, non-secret identifier for one specific app registration.

**Issuer:** the URL identifying which tenant issued a given token — the backend checks this exactly.

**Audience:** which app registration a token is *for* — the backend checks this too, so a token minted for a different app can't be replayed against it.

**Scope:** a named permission an app can request, e.g. "read the API on the user's behalf."

**Redirect URI:** where the identity provider sends the user's browser back to, after login — must exactly match what's registered, or login fails.

**Access token vs ID token — this distinction matters enormously for Noetva, more below.**

**JWKS (JSON Web Key Set):** the public keys the backend uses to verify a token's signature was really issued by the tenant it claims.

### Step 21.1 — Create the External ID tenant

**Where:** Azure Portal → search bar → type "Microsoft Entra ID" → **Create a resource** → select **External tenant configuration**.

**Value:** choose a tenant name, e.g. `noetva-dev` — this becomes `<name>.ciamlogin.com`, the authority URL every later OIDC setting depends on. Choose a region matching your compliance requirements.

**Action:** `[ENTRA MUTATION]` — complete the wizard.

**Expected result:** a new, separate tenant appears, type "External."

**SAVE THESE VALUES:**
```
ENTRA_EXTERNAL_ID_TENANT_ID = ______________________
ENTRA_EXTERNAL_ID_DOMAIN    = ______________________.ciamlogin.com
```

**SCREENSHOT TO CAPTURE:** Entra ID → Overview — the tenant name, tenant ID, and the "External" tenant-type badge. This proves the correct tenant type was created (a common mistake is accidentally creating a second *workforce* tenant instead).

**Assign an administrative owner:** a real named person (not a shared login), given the **Cloud Application Administrator** role — the only administrative role available for apps in External tenants.

### Step 21.2 — Register the frontend app

**Where:** the new External ID tenant → **App registrations** → **New registration**.

**Value:** name it `noetva-dev-frontend`, single-page application (SPA) platform, redirect URI left blank for now (Part 24 fills it in, after Pass 1 gives you the real frontend URL).

**SAVE THIS VALUE:**
```
FRONTEND_APP_CLIENT_ID = ______________________
```

### Step 21.3 — Register the backend (API) app

**Where:** same tenant → **App registrations** → **New registration**, name it `noetva-dev-backend-api`.

Then: this registration's **Overview** → **Expose an API** → set the Application ID URI.

**SAVE THIS VALUE:**
```
BACKEND_API_APPLICATION_ID_URI = ______________________
```

Read `frontend/lib/auth/config.ts` yourself before adding scopes here — do not invent scopes the frontend doesn't actually request.

---

# PART 22 — business-tenant claim configuration (CDD-065) — critical section, read fully

### Noetva application tenant vs Azure tenant, one more time

A **Noetva application tenant** (e.g. `noetva-dev-tenant`) is just a value in a `tenant_id` column in Noetva's own PostgreSQL database — it has nothing to do with Azure or Entra as *platforms*. What connects the two: a real, logged-in Entra External ID user carries a JWT **claim** inside their access token, and the backend trusts that claim to decide which Noetva application tenant's data this user may see. **This is a different concept from Entra's own directory-tenant GUID (`tid`, `8f9e2dee-5a5b-4b33-9044-4d11691899de` for `Noetva External`) — `tid` is the same for every user in this Entra tenant and must never be treated as the Noetva business tenant.**

### Real-Azure blocker, and why a Namespace does NOT fix it (CDD-065) — read before attempting Step 22.2

Attempting to add an outgoing claim literally named `tenant_id` in the backend API's Attributes & Claims editor fails with **"This claim type is restricted."** This is not a misconfiguration: `tenant_id` is a permanent member of Microsoft Entra's JWT restricted claim set, and no custom signing key unlocks it (CDD-064).

**A first correction attempt tried adding a Namespace (`https://noetva.ai/claims`) alongside `Name=tenant_id`, on the theory that the resulting compound identifier would no longer literally match the restricted name. Real Entra evidence disproved this: Azure still shows "This claim type is restricted" and Save remains disabled.** The restriction is checked against the literal **Name** field itself, independent of any Namespace supplied alongside it — a Namespace changes how a claim is displayed/prefixed, not whether its Name is on the restricted list. **Do not attempt `Name=tenant_id` with any Namespace value — it will not save.**

**The correct fix (CDD-065): use a different, non-restricted Name entirely — `noetva_tenant_id` — with no Namespace at all.** The **directory attribute** stays named `tenant_id` (Step 22.1, unchanged) — only the **outgoing JWT claim name** changes, to a name Microsoft's restricted-claim-set list does not contain. See CDD-064 (root cause) and CDD-065 (this correction) for the full analysis.

### Step 22.1 — Create the custom attribute (unchanged)

**Where:** the External ID tenant → **External Identities** → **Custom user attributes** → **Add**.

**Value:** name it `tenant_id`, data type String. (If this attribute already exists from a prior attempt, do not delete or recreate it — reuse it.)

### Step 22.2 — Map it into the ACCESS token using a non-restricted claim name (CDD-065 correction)

**Where:** `noetva-dev-backend-api`'s own **Enterprise Application** entry (the resource/API application — *not* the frontend's) → **Single sign-on** → **Attributes & Claims** → **Edit**. Configuring this on the backend's own service principal, rather than the frontend's, is what makes the claim land in the ACCESS token (audience `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`) rather than only the frontend's ID token.

**Action:** `[ENTRA MUTATION]` — **Add new claim** → Name `noetva_tenant_id` → **Namespace: leave blank** → Source **Directory schema extension** → Select Application **`b2c-extensions-app`** → select the existing `tenant_id` attribute from Step 22.1 using the portal's own dropdown (do not manually type or guess its internal `extension_<appid>_tenant_id` identifier — the portal resolves this for you; if that literal string is ever needed directly, retrieve it via Microsoft Graph `GET /applications/{b2c-extensions-app-object-id}/extensionProperties`, never invent it) → **Save**.

Then, on the backend app registration's **Manifest**: set `acceptMappedClaims: true` → **Save**. (This is required and sufficient here because the backend's Application ID URI, `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`, uses the application-GUID form Microsoft's `acceptMappedClaims` rule permits without a custom signing key. Do **not** set `isFallbackPublicClient` — no evidence has ever shown this backend claims-mapping scenario needs it; it governs an unrelated public-client/ROPC concern that does not apply here, and setting it is not authorized by CDD-064 or CDD-065.)

**Confirm Save actually succeeds this time** (unlike both prior attempts with `Name=tenant_id`) — `noetva_tenant_id` is not on Microsoft's restricted claim list. Because no Namespace is used, the resulting outgoing claim key is exactly `noetva_tenant_id` — there is no concatenation to capture or guess.

**SCREENSHOT TO CAPTURE:** the Attributes & Claims page showing `noetva_tenant_id`, Source = Directory schema extension → `tenant_id` — this proves the claim is wired to the real attribute, not typed as an identical literal for every user, and confirms Save succeeded.

**Why no Azure Function is required here** (unlike some Microsoft tutorials you may find): for a static, per-user value at Noetva's current scale, the native Attributes & Claims path is sufficient — confirmed directly against current Microsoft Learn documentation, and structurally identical to what Noetva's own local `keycloak/ctec-realm.json` already does for local development.

### Step 22.3 — Create your first DEV test user and set their `tenant_id` (unchanged)

**Where:** External ID tenant → **Users** → **New user**.

**Action:** create a user, then on their profile's custom-attribute section, set `tenant_id` to a value matching a real Noetva tenant your DEV database will actually have (Part 39's Start step doesn't seed tenants — you'll create this alongside your first real login test, Part 33). **This value is set by the administrator here, on the user's directory profile — it is never collected from the user during the `noetva-dev-signup-signin` self-service sign-up flow.** A public/signup user must never be able to choose, edit, forge, or self-assert this value.

**SAVE THIS VALUE:**
```
DEV_NOETVA_TENANT_ID = ______________________
```

### The critical acceptance rule

**The configured business-tenant claim must appear in the ACCESS TOKEN — the one the frontend actually sends to the backend — not merely the ID token.** An ID token is meant for the frontend's own use (displaying "logged in as ___"); the backend never sees it and must never be asked to trust it. If Part 34's verification finds the claim only in the ID token, this is not done — go back to Step 22.2 and confirm the claim mapping was configured on the **backend's own Enterprise Application entry** and targets the **access token**, not just the ID token.

### Step 22.4 — Negative tests (mandatory, not optional)

Perform every row below for real, once DEV is running (Part 34):

| Test | Expected result |
|---|---|
| No `Authorization` header | `401` |
| Access token missing the configured tenant claim | Rejected, never a silent default tenant |
| Access token carrying only Entra's `tid` (no configured tenant claim) | Rejected — `tid` is never treated as the Noetva tenant |
| Configured tenant claim value that doesn't exist in Noetva's own tenant table | Rejected at the application authorization layer |
| Token from the wrong issuer | Rejected |
| Token whose audience doesn't match | Rejected |
| Expired token | `401` |

No email-derived fallback tenant exists anywhere in the backend. No header-supplied tenant authority exists anywhere. No `tid`/`oid`/`sub` fallback exists anywhere. Confirm this yourself: `grep -rn "oidc_tenant_claim" backend/app/api/supplier_risk/authentication.py backend/app/core/config.py`.

---

# PART 23 — Deployment Pass 1 (CDD-067 two-stage correction)

### Why two passes are unavoidable, and why Pass 1 itself is now two stages

The frontend's `NEXT_PUBLIC_OIDC_REDIRECT_URI` is *baked into the compiled JavaScript at build time* (confirmed in `frontend/Dockerfile`) — it cannot be an environment variable read at runtime. But the redirect URI has to point at the frontend's own real URL, which Azure only generates **after** the frontend Container App exists. This is why Pass 1 creates infrastructure first, and Pass 2 (Part 26 onward) builds the real, environment-specific frontend image second.

**Real-Azure finding (CDD-067):** an earlier version of this guide claimed Pass 1 could create the frontend/backend Container Apps and migration Job pointed at the placeholder image string `REPLACE_AT_DEPLOY_TIME_WITH_DIGEST_REFERENCE`, and that they simply "would not run correctly yet." **A real deployment attempt disproved this.** Azure Container Apps validates that `image` is a syntactically parseable reference **at provisioning time** — a literal placeholder string is rejected outright (`InvalidParameterValueInContainerTemplate`), and the resource never provisions at all. The same real attempt also showed the backend Container App and migration Job cannot provision until the Key Vault secrets they reference (Part 17) already exist — but Key Vault is itself created in this same deployment, empty.

**The correction:** Pass 1 is now explicitly **two stages**, both run by the same command with one parameter changed, never two different templates:

### Stage 1a — Foundation (`deployApplicationTier=false`)

**Which Azure service:** Azure Resource Manager, driven by Bicep — `infra/azure/main.bicep` (subscription-scoped).

**Who performs it:** the human bootstrap operator — the one-time subscription-scope Contributor + User Access Administrator role from Part 3, **not** any of the managed identities from Part 18 (they don't exist yet, and even once they do, `id-cicd` is deliberately scoped to the resource group only, not the subscription — it cannot bootstrap itself).

**Action, `[AZURE MUTATION]`:**

```bash
az deployment sub create --location eastus2 \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/environments/dev/main.parameters.json \
  --parameters deployApplicationTier=false
```

(`deployApplicationTier` already defaults to `false` in the committed parameter file — the explicit override above is for clarity and is safe to omit.)

**What this creates:** the resource group, VNet/subnets/private DNS, PostgreSQL Flexible Server, ACR, Key Vault, all four Pass-1 managed identities, the Container Apps Environment, and foundation RBAC. **It does not create the frontend/backend Container Apps, the migration Job, or the monitoring alerts** — those are gated behind `deployApplicationTier` and are created only in Stage 1c below.

**Expected result:** the command completes with `provisioningState: Succeeded`. This stage is safe and idempotent to re-run at any time (e.g. if you are recovering from a prior failed attempt) — it will converge existing foundation resources unchanged and will not delete or replace anything.

**STOP IF:** the deployment fails. Read the specific error — `az deployment operation group list --resource-group rg-noetva-dev` shows exactly which resource failed and why. Do not hand-edit the failed resource in the Portal; fix the underlying parameter/quota issue and redeploy.

### Stage 1b — Operator bootstrap (between the two Bicep invocations)

Perform, in order, now that the foundation exists: Part 17's Key Vault RBAC self-assignment and secret population (all six secrets — do not skip `ctec-migration-database-url`), Part 15's database role creation, and Parts 26/27's real image build-and-push to the now-existing ACR. **If this is a recovery from a prior failed attempt, first reset the PostgreSQL admin password** (Part 13a below) rather than assuming the original value is still known.

#### Part 13a — PostgreSQL admin-password recovery (recovery scenarios only)

If a prior Stage-1a attempt already created `noetva-dev-eus2-pg` and the admin password used then is no longer known (it is never logged, printed, or committed — by design), reset it in place. This is a safe, non-destructive operation; it does not recreate the server or affect existing data:

```bash
# [AZURE MUTATION] -- rotates the admin credential only, no data loss
az postgres flexible-server update \
  --name noetva-dev-eus2-pg --resource-group rg-noetva-dev \
  --admin-password "<newly generated value, never printed/logged>"
```

### Stage 1c — Application tier (`deployApplicationTier=true`)

**Prerequisites (verify all before running):** all six Key Vault secrets from Part 17 exist; a real, digest-pinned backend image and a real, digest-pinned frontend image have been pushed to the ACR created in Stage 1a (Parts 26/27); `deployApplicationTier=true` is the only Bicep-parameter difference from Stage 1a.

**Action, `[AZURE MUTATION]`:**

```bash
az deployment sub create --location eastus2 \
  --template-file infra/azure/main.bicep \
  --parameters infra/azure/environments/dev/main.parameters.json \
  --parameters deployApplicationTier=true \
               backendImageReference="<real digest reference>" \
               frontendImageReference="<real digest reference>"
```

**What this creates:** the backend and frontend Container Apps (now with real images and now-resolvable Key Vault secrets), the migration Job, and the three Azure Monitor alerts.

**Expected result:** the command completes with `provisioningState: Succeeded`, and the frontend/backend Container Apps reach a healthy revision (subject to Part 30/31's separate image-deploy verification).

**STOP IF:** the deployment fails for any reason other than a known, already-governed cause — do not hand-edit resources in the Portal; determine the root cause and, if it represents a new defect, treat it exactly as CDD-067 treated the original two.

---

# PART 24 — Save Azure-generated outputs

**Retrieve every generated value now (`[AZURE READ-ONLY]`):**

```bash
az containerapp show --name noetva-dev-eus2-frontend --resource-group rg-noetva-dev --query "properties.configuration.ingress.fqdn" -o tsv
az containerapp show --name noetva-dev-eus2-backend --resource-group rg-noetva-dev --query "properties.configuration.ingress.fqdn" -o tsv
az identity show --name noetva-dev-eus2-id-cicd --resource-group rg-noetva-dev --query "clientId" -o tsv
az acr show --name <DEV_ACR_NAME> --query "loginServer" -o tsv
```

**SAVE THESE VALUES:**
```
DEV_FRONTEND_FQDN = ______________________
DEV_BACKEND_FQDN  = ______________________
NOETVA_CICD_CLIENT_ID = ______________________
```

---

# PART 25 — Update identity/URL configuration with generated outputs

| Azure-generated output | → goes into |
|---|---|
| `DEV_FRONTEND_FQDN` | Frontend app registration's redirect URI (`https://<DEV_FRONTEND_FQDN>/auth/callback`) and post-logout redirect URI (Part 21); GitHub variable `NOETVA_OIDC_REDIRECT_URI`/`NOETVA_OIDC_POST_LOGOUT_REDIRECT_URI` (Part 20) |
| `DEV_BACKEND_FQDN` | Backend's `CTEC_CORS_ORIGINS` setting (Part 32); GitHub variable `NOETVA_BACKEND_ORIGIN` (Part 20) |
| `NOETVA_CICD_CLIENT_ID` | GitHub variable of the same name (Part 20) |

Go back and complete Parts 20 and 21's blanks now, using these real values.

---

# PART 26 — Build the backend image

```bash
# [LOCAL -- SAFE]
az acr login --name <DEV_ACR_NAME>
# [AZURE MUTATION -- pushes an image to your registry]
docker build -t <DEV_ACR_LOGIN_SERVER>/noetva/backend:<git-sha> ./backend
docker push <DEV_ACR_LOGIN_SERVER>/noetva/backend:<git-sha>
```

**Why no `NEXT_PUBLIC_*`-style build args here:** the backend has no build-time OIDC constraint — it's runtime-configured, so this exact same image digest is valid to reuse across environments later (staging/prod) without rebuilding.

**Get the immutable digest (`[AZURE READ-ONLY]`, local Docker inspect):**

```bash
docker inspect --format='{{index .RepoDigests 0}}' <DEV_ACR_LOGIN_SERVER>/noetva/backend:<git-sha>
```

**SAVE THIS VALUE:**
```
BACKEND_IMAGE_DIGEST = ______________________
```

**Deploy using this digest, never the tag above it** — the tag is a human-readable pointer for this one build; the digest is what actually gets deployed (Part 30).

---

# PART 27 — Build the frontend image

```bash
# [AZURE MUTATION]
docker build \
  --build-arg NEXT_PUBLIC_CTEC_API_ORIGIN="https://<DEV_BACKEND_FQDN>" \
  --build-arg NEXT_PUBLIC_OIDC_AUTHORITY="https://<ENTRA_EXTERNAL_ID_DOMAIN>" \
  --build-arg NEXT_PUBLIC_OIDC_CLIENT_ID="<FRONTEND_APP_CLIENT_ID>" \
  --build-arg NEXT_PUBLIC_OIDC_REDIRECT_URI="https://<DEV_FRONTEND_FQDN>/auth/callback" \
  --build-arg NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI="https://<DEV_FRONTEND_FQDN>" \
  -t <DEV_ACR_LOGIN_SERVER>/noetva/frontend:<git-sha>-dev ./frontend
docker push <DEV_ACR_LOGIN_SERVER>/noetva/frontend:<git-sha>-dev
```

**Why this specific image can never be reused for another environment:** every one of those `NEXT_PUBLIC_*` values is baked into the compiled JavaScript. A staging deployment needs its own build with staging's own values.

**SAVE THIS VALUE (same pattern as Part 26):**
```
FRONTEND_IMAGE_DIGEST = ______________________
```

---

# PART 28 — Database bootstrap

This is Part 15, restated as the exact command sequence to run right now, at this point in the overall order:

```bash
# [DATABASE MUTATION]
export NOETVA_PG_HOST="noetva-dev-eus2-pg.postgres.database.azure.com"
export NOETVA_PG_ADMIN_USER="noetva_pg_admin"
export NOETVA_PG_ADMIN_PASSWORD="<from Key Vault>"
export NOETVA_PG_APP_PASSWORD="<from Key Vault>"
export NOETVA_PG_MIGRATE_PASSWORD="<from Key Vault>"
bash infra/azure/scripts/run_db_bootstrap.sh
```

Confirm the exact success line from Part 15 before continuing.

---

# PART 29 — Run migrations

### Alembic, for a beginner

Alembic is Noetva's database-migration tool — each migration file describes one incremental schema change, applied in a strict, numbered order. "Running migrations" means applying every migration the database hasn't seen yet, until it's caught up to the latest ("head").

### The migration Job

**Which Azure service:** a Container Apps Job — a manually-triggered, run-to-completion container, separate from the always-on backend Container App. **The backend never runs migrations on its own startup** — confirm: `grep -n "alembic" backend/docker-entrypoint.sh` shows it is not invoked there.

**Action, `[AZURE MUTATION]`:**

```bash
az containerapp job update --name noetva-dev-eus2-migrate --resource-group rg-noetva-dev \
  --image <DEV_ACR_LOGIN_SERVER>/noetva/backend@<BACKEND_IMAGE_DIGEST>
az containerapp job start --name noetva-dev-eus2-migrate --resource-group rg-noetva-dev
```

**Verify (`[AZURE READ-ONLY]`, poll until `Succeeded`):**

```bash
az containerapp job execution list --name noetva-dev-eus2-migrate --resource-group rg-noetva-dev \
  --query "[0].properties.status" -o tsv
```

**Verify the actual database state (`[DATABASE MUTATION]` is wrong — this is read-only against the DB):**

```sql
SELECT version_num FROM alembic_version;
SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
```

**Expected migration head, confirmed directly from source:** `0046_oqi5_remediation_tenancy`.

**Expected table count:** **126 application/governed tables, plus the `alembic_version` bookkeeping table Alembic itself creates — 127 total rows from the query above.** This is not a discrepancy to investigate; it's simply whether your count includes Alembic's own tracking table.

**Idempotency check — run this once more after the first success:**

```bash
az containerapp job start --name noetva-dev-eus2-migrate --resource-group rg-noetva-dev
```

**Expected result:** it completes immediately, with no schema changes — Alembic recognizes it's already at head.

---

# PART 30 — Deploy the backend

```bash
# [AZURE MUTATION]
az containerapp update --name noetva-dev-eus2-backend --resource-group rg-noetva-dev \
  --image <DEV_ACR_LOGIN_SERVER>/noetva/backend@<BACKEND_IMAGE_DIGEST>
```

**Configuration Azure sets from `resources.bicep`, for your understanding, not something you type:** plain vars `CTEC_ENVIRONMENT=development`, `CTEC_LOG_LEVEL=INFO`, `CTEC_CORS_ORIGINS`, `CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`, `CTEC_OIDC_JWKS_URL`, `CTEC_OIDC_SCOPE_CLAIM=scp` (CDD-063: Microsoft Entra External ID exposes delegated permissions through the `scp` claim, not `scope` -- local/Docker Keycloak is unaffected and continues using the backend's own `scope` default); `CTEC_OIDC_TENANT_CLAIM=noetva_tenant_id` (CDD-064/CDD-065: the bare `tenant_id` claim name is Microsoft-reserved and cannot be used as an outgoing Entra claim, even with a Namespace -- local/Docker Keycloak is unaffected and continues using the backend's own `tenant_id` default); Key Vault secret references `ctec-database-url`, `ctec-runtime-handoff-key`. Target port `8000`, `minReplicas=0`/`maxReplicas=1` for DEV.

**Verify (`[AZURE READ-ONLY]`):**

```bash
curl -s -o /dev/null -w '%{http_code}\n' "https://<DEV_BACKEND_FQDN>/health"
```

Expected: `200`.

**Do not treat this as proof the database is reachable** — `/health` returns `{"status": "healthy"}` unconditionally, confirmed directly from `backend/app/api/health/router.py`. It checks nothing else. There is deliberately no `/ready` endpoint yet.

---

# PART 31 — Deploy the frontend

```bash
# [AZURE MUTATION]
az containerapp update --name noetva-dev-eus2-frontend --resource-group rg-noetva-dev \
  --image <DEV_ACR_LOGIN_SERVER>/noetva/frontend@<FRONTEND_IMAGE_DIGEST>
```

Target port `3000`. No server-side environment variables — every OIDC value was baked in at build time (Part 27).

**Verify:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' "https://<DEV_FRONTEND_FQDN>/"
```

Expected: `200`.

---

# PART 32 — CORS

**Explained simply:** CORS (Cross-Origin Resource Sharing) is the browser's own rule that a webpage from origin A cannot call an API at origin B unless B explicitly allows it. Noetva's backend must explicitly list the frontend's exact origin.

**No wildcard, ever.** `CTEC_CORS_ORIGINS` is set to exactly `https://<DEV_FRONTEND_FQDN>` — Bicep's own parameter description states this applies uniformly, not just to staging/prod.

**Verify:**

```bash
curl -s -D - -o /dev/null -H "Origin: https://<DEV_FRONTEND_FQDN>" "https://<DEV_BACKEND_FQDN>/health" | grep -i access-control-allow-origin
```

---

# PART 33 — Login for the first time

1. Open `https://<DEV_FRONTEND_FQDN>` in a browser.
2. Confirm the browser redirects to `https://<ENTRA_EXTERNAL_ID_DOMAIN>`.
3. Sign in as the DEV test user from Part 22.3.
4. Confirm redirect back to the frontend with a session established.
5. Open browser DevTools → Network — confirm the frontend's call to the backend returns `200`, not `401`.

---

# PART 34 — Verify the business-tenant claim end to end (CDD-064)

1. In DevTools → Network, find the token response (or use `jwt.ms`, pasting only a redacted copy you understand the sensitivity of — **never post a real token anywhere shared**).
2. Decode the payload only (never print the raw signed token in a ticket, chat, or this worksheet).
3. Confirm the payload contains **`noetva_tenant_id`** (not a bare `tenant_id`) with value `<DEV_NOETVA_TENANT_ID>`.
4. Confirm this is the **access token**, not the ID token (Part 22's critical rule).
5. Confirm the same token's `tid` claim equals `8f9e2dee-5a5b-4b33-9044-4d11691899de` and is a *different* value from the business-tenant claim in item 3 — proving `tid` and the Noetva business tenant are genuinely distinct and the backend is not accidentally reading `tid`.
6. Confirm the running backend's `CTEC_OIDC_TENANT_CLAIM` environment value equals exactly `noetva_tenant_id`.
7. Perform every row of Part 22.4's negative-test table for real, and observe the actual result — do not merely assert it "should" work.

---

# PART 35 — Log Analytics

**Where:** the Log Analytics workspace `noetva-dev-eus2-log` → **Logs** blade.

**Useful queries (`[AZURE READ-ONLY]`):**

```kql
// Backend errors
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "noetva-dev-eus2-backend"
| where Log_s has "ERROR"
| order by TimeGenerated desc

// Container App restarts
ContainerAppSystemLogs_CL
| where ContainerAppName_s in ("noetva-dev-eus2-backend", "noetva-dev-eus2-frontend")
| where EventSource_s == "Microsoft.App"
| order by TimeGenerated desc

// Migration Job failures
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "noetva-dev-eus2-migrate"
| where Log_s has "Traceback" or Log_s has "ERROR"
| order by TimeGenerated desc

// Authentication failures
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "noetva-dev-eus2-backend"
| where Log_s has "401"
| order by TimeGenerated desc
```

---

# PART 36 — Azure Monitor

Three metric alerts exist, all routed to one action group (`noetva-dev-eus2-ag-oncall`, email only, using `<ALERT_EMAIL>`):

| Alert | Metric | Threshold | Severity |
|---|---|---|---|
| `noetva-dev-eus2-alert-pg-storage` | `storage_percent` | `>80`, 15-min window | 1 |
| `noetva-dev-eus2-alert-pg-connections` | `active_connections` | `>80`, 15-min window | 2 |
| `noetva-dev-eus2-alert-migration-job-failed` | `JobExecutionCount` (`executionStatus=Failed`) | `>0`, 5-min window | 0 |

**Do not treat these metric names as guaranteed correct without checking.** They were written from Azure Monitor namespace knowledge, not independently re-verified against a real deployed resource before now — Bicep's compiler cannot validate a metric-name string.

**Verify (`[AZURE READ-ONLY]`), mandatory, once resources exist:**

```bash
az monitor metrics list-definitions --resource "<postgres server resource ID>" -o table
az monitor metrics list-definitions --resource "<migration job resource ID>" -o table
```

Compare the returned names against the table above. **If any name doesn't match: stop treating that alert as authoritative.** Do not hot-fix `monitoring-alerts-only.bicep` directly against DEV in the Portal — route any correction through the normal commit/PR/merge process (Part 74 explains why).

---

# PART 37 — Budget

**Where:** Azure Portal → search "Cost Management" → **Budgets** → **Add**.

**Not created automatically** — `modules/budget.bicep` is not wired into Pass 1's deployment; it requires its own separate command.

**Action, `[AZURE MUTATION]`:**

```bash
az deployment group create --resource-group rg-noetva-dev \
  --template-file infra/azure/modules/budget.bicep \
  --parameters name=noetva-dev-eus2-budget monthlyAmount=<BUDGET_AMOUNT> contactEmail=<BUDGET_ALERT_EMAIL>
```

**What this creates:** two budgets — one alerting at 50/75/90/100% of actual spend, one at 100% of *forecasted* spend. Neither `monthlyAmount` nor `contactEmail` has a default — the module deliberately refuses to compile a fabricated number.

**View actual cost so far:** Cost Management → **Cost analysis**, scoped to `rg-noetva-dev`.

---

# PART 38 — Lifecycle control, explained

Noetva's DEV/staging/demo environments are not meant to run 24/7 — they're meant to be *governed dormant* most of the time, and started only when someone is actually using them. This is not the same as Azure's own "scale to zero" — Noetva deliberately **deactivates** the Container App revision entirely (a stronger, genuinely-$0-compute state) and **stops** the Postgres server outright, and it durably remembers which state each environment is in inside the shared Azure Storage Table from Part 21.

**The 12 states, exactly, from `lifecycle_controller.py`:**

```
DORMANT -> START_REQUESTED -> STARTING_DATABASE -> STARTING_APPLICATION
        -> VERIFYING -> READY -> IN_USE -> DRAIN_REQUESTED
        -> STOPPING_APPLICATION -> STOPPING_DATABASE -> DORMANT

FAILED_START: reachable from any of the four STARTING/VERIFYING states
FAILED_STOP:  reachable from DRAIN_REQUESTED/STOPPING_APPLICATION/STOPPING_DATABASE
```

Every transition is validated against an explicit allow-list — nothing not listed is ever silently permitted.

**Why this exists at all, and why you should trust it now:** an earlier version of this exact automation had a real defect — it computed the correct next state but never actually saved it, so none of Start/Stop/Extend/Hold/the nightly sweep/the restart monitor could reliably track reality. That defect is fixed and merged into the source you are deploying from (commit `4567164`, PR #197) — every transition below is now genuinely written to the Storage Table, proven end-to-end against a simulated Azure backend before merge. What remains **unproven until you do it for real in this Part**: the exact live behavior against a real Azure Storage Table (Part 19 of the register below).

---

# PART 39 — Start DEV

**Who may invoke it:** anyone with access to trigger GitHub Actions workflows in the `dev` GitHub Environment.

**Where:** `github.com/manoj96-alt/CTEC` → **Actions** → **Start Noetva Environment** → **Run workflow** → `environment: dev`, `ttlHours` (1–12, default 4) → **Run workflow**.

**What it does, in order, each state durably persisted before the corresponding action:**

1. Persists `START_REQUESTED` (the lifecycle lock).
2. Persists `STARTING_DATABASE`, then starts PostgreSQL and polls until `Ready`.
3. Validates the database read-only (never runs migrations or seeders here).
4. Persists `STARTING_APPLICATION`, then activates the backend and frontend revisions.
5. Persists `VERIFYING`, then waits for backend `/health`.
6. Persists `READY` with the computed TTL expiry, then disables alert suppression.

**On any failure at any point**, the specific step persists `FAILED_START` with a real, specific error message — not merely a log line — before exiting, and a safety-net cleanup step restores alerting regardless of exactly where the failure occurred.

**Verify (`[AZURE READ-ONLY]`):**

```bash
az postgres flexible-server show --resource-group rg-noetva-dev --name noetva-dev-eus2-pg --query state -o tsv
az containerapp revision list --resource-group rg-noetva-dev --name noetva-dev-eus2-backend --query "[?properties.active].name" -o tsv
```

Do not manually start Postgres or activate a revision by hand as routine operation — the lifecycle workflow is the single authoritative path; a manual action bypasses the durable state tracking entirely.

---

# PART 40 — Status

**Where:** **Actions** → **Check Noetva Environment Status** → `environment: dev` → **Run workflow**.

**What it shows, side by side, deliberately:**

```
lifecycle state:          READY       <- from the Storage Table (control-plane state)
postgres actual state:    Ready       <- live Azure query (observed state)
backend revision active:  true
frontend revision active: true
TTL expiry:                <timestamp>
hold expiry:               none
```

**If the two disagree** — e.g. lifecycle state says `DORMANT` but Postgres actually reports `Ready` — **treat this as a genuine anomaly, not something to silently accept.** This exact situation is what Part 45's restart monitor exists to catch and correct automatically; if you see it between scheduled runs, you may re-run the restart monitor workflow manually rather than waiting.

---

# PART 41 — Extend

**Where:** **Actions** → **Extend Noetva Environment** → `environment: dev`, `additionalHours`.

**Only valid from `READY`/`IN_USE`.** Source-verified: default TTL 4 hours, bounds 1–12 hours (`TTL_MIN_HOURS`/`TTL_MAX_HOURS`/`TTL_DEFAULT_HOURS` in `lifecycle_controller.py`). Extends from the **existing** expiry, not from now — a mid-session extension never shortens your remaining time.

**SOURCE-VERIFIED, AZURE-RUNTIME-VERIFICATION REQUIRED** — the persistence path is proven end-to-end against a simulated backend; confirm once, for real, that a real Storage Table write actually reflects the new expiry (Part 19 register).

---

# PART 42 — Hold

**Where:** **Actions** → **Hold Noetva Environment** → `environment: dev`, `holdUntilUtc` (an absolute timestamp, e.g. `2026-09-15T18:00:00Z`).

**No permanent Hold exists — structurally, not just by policy.** There is no "forever" input anywhere in this workflow. Use Hold for a bounded, known-duration need (a workshop, an extended debugging session) so the nightly sweep doesn't stop the environment out from under you.

**Interaction with Stop/nightly sweep:** an active Hold causes both the manual Stop workflow and the nightly sweep to refuse, with a specific reason — never a silent skip.

**SOURCE-VERIFIED, AZURE-RUNTIME-VERIFICATION REQUIRED**, same caveat as Part 41.

---

# PART 43 — Stop DEV

**Where:** **Actions** → **Stop Noetva Environment** → `environment: dev` → **Run workflow**.

**Preconditions checked before anything is touched:** no migration Job running, no deployment in progress for `dev`, no active Hold, no unsafe long-running database session (diagnostic only — never auto-terminated; the stop is refused instead).

**Sequence, each persisted before the corresponding action:**

1. Persists `DRAIN_REQUESTED` (only once preconditions are confirmed clear).
2. Enables alert suppression (before touching anything — Part 59 explains the ~30-minute propagation caveat this ordering accounts for).
3. Persists `STOPPING_APPLICATION`, deactivates frontend then backend revisions.
4. Persists `STOPPING_DATABASE`, verifies no unsafe session, then stops PostgreSQL.
5. **Persists `DORMANT` only after Postgres is confirmed genuinely `Stopped`** — never merely because the stop command itself returned success.

**Verify:**

```bash
az postgres flexible-server show --resource-group rg-noetva-dev --name noetva-dev-eus2-pg --query state -o tsv
```

Expected, after Stop completes: `Stopped`.

---

# PART 44 — Automatic shutdown (nightly sweep)

**What it is:** a scheduled GitHub Actions workflow (`Noetva Nightly Lifecycle Sweep`, `08:00 UTC` by default) that stops any environment whose TTL has expired (or, for `dev` specifically, sweeps it every night regardless of TTL — dormant-by-default policy) — unless an active Hold or in-progress deployment blocks it.

**Why you can trust it now, and what to still confirm:** an earlier version of this automation was, in effect, a permanent no-op — its "already DORMANT" check always fired against a table row that never actually reflected reality. That's fixed in the source you deployed. What you should still do once, manually: confirm a real scheduled or manually-dispatched run actually reads real persisted state and behaves correctly (Part 19 register) — **do not rely on cron timing being exact**; GitHub's own scheduling is documented as best-effort.

---

# PART 45 — PostgreSQL restart monitor

**Why it exists:** Azure's own documented behavior is that a *stopped* PostgreSQL Flexible Server can automatically restart after a maximum interval if never manually restarted. **Verify the current exact interval against Microsoft's own current documentation before relying on a specific number** — do not treat any single number as permanently fixed platform behavior; Noetva's own governance work independently confirmed a 7-day interval directly from Microsoft's documentation at the time it was written, and that's what `compute_db_auto_restart_risk_at` in source currently encodes, but re-check it.

**How Noetva detects and handles it:** a daily scheduled workflow compares the live Postgres state against the persisted lifecycle state. If it finds Postgres unexpectedly `Ready` while the table says `DORMANT`, it does **not** alarm immediately — it records a `TRANSIENT_MAINTENANCE_SUSPECTED` classification (this is now durably remembered between runs, another part of the same earlier fix) and waits for the next scheduled run. If the *next* run still finds it `Ready`, that's a genuine anomaly — it safely re-stops Postgres and records `UNEXPECTED_RESTART`, unless a deployment happens to be in progress, in which case it defers rather than racing.

---

# PART 46 — Backup

Configured automatically: 7-day retention, automated, geo-redundant backup **disabled** for DEV (`geoRedundantBackup: 'Disabled'`).

**Backup enabled is not the same claim as restore verified.** Part 47 is what actually proves it.

---

# PART 47 — Restore rehearsal

**Mandatory before any DEMO work begins.** This section is deliberately safe for a beginner — it never touches the real DEV server.

1. **`[AZURE READ-ONLY]`** — identify a recent backup:
   ```bash
   az postgres flexible-server backup list --resource-group rg-noetva-dev --server-name noetva-dev-eus2-pg -o table
   ```
2. **`[AZURE MUTATION]`** — restore to a **new, temporary** server. This never touches the original:
   ```bash
   az postgres flexible-server restore --resource-group rg-noetva-dev \
     --name noetva-dev-eus2-pg-restore-test --source-server noetva-dev-eus2-pg \
     --restore-time "<ISO8601 timestamp>"
   ```
3. Attach the temporary server to a throwaway subnet in the same VNet pattern — acceptable for a rehearsal.
4. Connect and verify: migration head = `0046_oqi5_remediation_tenancy`; table count = 127 (126 + `alembic_version`); a handful of sample canonical (not customer, not demo) rows are present.
5. **Record what you observed:** how long the restore actually took (your real RTO), and how far back the backup point was from "now" (your real RPO).
6. **`[DESTRUCTIVE — APPROVAL REQUIRED]`** — cleanup, only after verification is complete:
   ```bash
   az postgres flexible-server delete --resource-group rg-noetva-dev --name noetva-dev-eus2-pg-restore-test
   ```

Never leave the temporary server running — it is a second, fully-billed Postgres server.

---

# PART 48 — Connector security

Noetva's outbound connector (`backend/app/infrastructure/connectors/rest_connector.py`) enforces fresh DNS resolution, full resolved-address validation, TLS SNI/Host preservation, no ambient proxy honoring, restricted redirects, bounded reads, and rejection of private/reserved/link-local/metadata addresses.

**Prove the defensive logic locally, `[LOCAL — SAFE]`, no Azure dependency:**

```bash
python3 infra/azure/validation/connector_security_check.py
```

Expected: 8/8 local checks pass, including rejection of the Azure Instance Metadata Service address `169.254.169.254` over both HTTPS and plain HTTP.

**What still requires the real DEV deployment to prove:** DNS-rebinding/IP-pinning holding under Azure's real resolver; that no `HTTP_PROXY`/`HTTPS_PROXY` is set on the real backend Container App; that a real external HTTPS endpoint is actually reachable through the deployed egress path. Keep this constrained to Noetva's own defensive controls — this is not an offensive-security exercise.

---

# PART 49 — Tenant isolation

**Two layers, both real, neither is Postgres Row-Level Security** — Noetva does not use RLS. Confirm for yourself: `grep -rn "ROW LEVEL SECURITY" backend/app/infrastructure/persistence/migrations/` returns nothing.

**Layer 1 — application authorization:** every authenticated request's `tenant_id` (from the access token, Part 22) is checked against the resource being accessed.

**Layer 2 — database composite foreign keys:** 23 tenant-qualified composite foreign keys exist across the schema (confirmed directly, `pg_constraint` catalog query), each shaped `(tenant_id, entity_id)` — meaning a row can only reference a parent row belonging to the *same* tenant, enforced by PostgreSQL itself, not application code alone.

**A safe DEV-only runtime test (no real customer data):**
1. Create two DEV test users with **different** `tenant_id` values, each pointing at a Noetva tenant seeded with distinct synthetic data.
2. Authenticate as tenant A; attempt to read a resource created under tenant B, by ID.
3. **Expected: fail closed** — `404` or `403`, never tenant B's data.
4. Repeat in reverse.

---

# PART 50 — Complete DEV validation walkthrough

Do this once, start to finish, before declaring DEV accepted:

1. Login (Part 33). 2. Frontend loads (Part 31). 3. Backend healthy (Part 30). 4. Access token obtained. 5. `tenant_id` present in the access token, correct value (Part 34). 6. Database reachable through the backend (implied by step 3 succeeding meaningfully, e.g. a real data-backed page load). 7. `/health` behavior understood, not over-claimed (Part 30). 8. Log Analytics shows this session's activity (Part 35). 9. Migration head and table count confirmed (Part 29). 10. Connector security local checks pass (Part 48). 11. Start workflow run and verified (Part 39). 12. Status shows agreement between control-plane and observed state (Part 40). 13. Extend run and verified (Part 41). 14. Hold run and verified (Part 42). 15. Stop run and verified (Part 43). 16. DORMANT confirmed — Postgres genuinely `Stopped`, both revisions genuinely inactive.

---

# PART 51 — Cost after deployment

**Where:** Cost Management → **Cost analysis**, scoped to `rg-noetva-dev` (and `rg-noetva-lifecycle` for the small shared control-plane cost).

Track, over at least one full 24-hour active period and one full 24-hour dormant period: total resource-group cost, PostgreSQL's line specifically, ACR's fixed line, and the budget's forecast view. **Azure Cost Management data lags real usage — do not expect a same-day exact number**; expect it to finalize a day or two later.

**Never report DEV as "$0 while dormant."** Postgres storage/backups, Basic ACR, and Log Analytics retention are non-zero even while fully DORMANT (Part 8's table).

---

# PART 52 — Troubleshooting for beginners

| What you see | What it means | Likely cause | Check | Fix | When to stop and ask |
|---|---|---|---|---|---|
| `az login` browser never returns | Auth flow interrupted | Browser blocked popup, or wrong account | Retry with `az login --use-device-code` | Complete the device-code flow instead | If it still fails twice, escalate — don't guess at auth flags |
| Wrong subscription shown in Part 6.4 | `az account set` targeted the wrong ID | Typo, or copied the wrong value from Part 6.2's table | Re-run `az account list --output table`, copy exactly | Re-run `az account set` | Always — never proceed on a mismatch |
| Provider `NotRegistered` | Not yet registered on this subscription | Fresh subscription | `az provider register` (Part 10) | Poll until `Registered` | If registration hangs >15 min, escalate to Azure support |
| `Bicep deployment failed` | A parameter, quota, or naming collision issue | Read the specific `az deployment operation group list` output | Fix source parameter, redeploy | Never hand-edit the failed resource in Portal | If the error references a resource type you don't recognize |
| PostgreSQL creation stuck/failed | SKU unavailable in region, or subnet delegation conflict | `az postgres flexible-server list-skus --location eastus2` | Re-check Part 29 quota preflight; do not silently substitute a different SKU | | Always escalate a SKU/quota block — don't upsize alone |
| Private DNS resolution failure | DNS zone not linked to the VNet | `az network private-dns link vnet list` | Re-run the network module deployment | | |
| `az acr login` fails | Session expired, or RBAC not yet propagated | `az acr repository list` | Wait a few minutes for RBAC propagation, retry | | If it persists >10 minutes |
| `docker push` fails | Not logged into ACR, or wrong login server | Re-run `az acr login` | | | |
| `azure/login@v2` fails in GitHub Actions | Federated credential subject mismatch | Compare the workflow's `environment:` value against the Bicep-created credential's subject exactly (Part 19) | Fix the federated credential subject in Bicep, not the workflow | | This is exactly the class of defect R4 fixed — if you see it, the subjects genuinely don't match; don't assume it's transient |
| Migration Job fails | A migration's assumption violated, or role privilege issue | Job logs (Part 35's KQL) | Do not deploy backend/frontend past a failed migration | | |
| Backend unhealthy | Wrong image digest, missing Key Vault access, DB unreachable | Container App logs, Key Vault RBAC | Roll back to the last known-good digest via `az containerapp update --image` | | |
| Frontend blank/broken | Wrong `NEXT_PUBLIC_OIDC_*` baked into this build | Re-check Part 27's build args against Part 24's real captured values | Rebuild — this cannot be fixed by an env var change post-build | | |
| CORS error in browser console | Origin mismatch | Confirm `CTEC_CORS_ORIGINS` exactly matches the frontend FQDN, no trailing slash mismatch | | | |
| Login redirects but the configured tenant claim is missing | Attributes & Claims not saved, `acceptMappedClaims` not set, or `CTEC_OIDC_TENANT_CLAIM` doesn't exactly match the real emitted claim string | Decode the token (Part 34) | Redo Part 22.2 exactly | | |
| Tenant claim present but wrong value | Wrong test user, or attribute set on the wrong user | Re-check Part 22.3 | | | |
| Start workflow fails at Postgres step | Postgres didn't reach `Ready` in time | Workflow run logs | Persisted `FAILED_START` with a specific reason (Part 39) — read it | | |
| Stop workflow refuses | An active precondition (migration/deploy/Hold/unsafe session) | The refusal reason printed in the workflow log | Address the specific blocking condition, don't force it | | Never bypass a stop refusal |
| Status shows disagreement (e.g. DORMANT but Postgres Ready) | Genuine reconciliation anomaly (Part 40) | Re-run restart monitor manually | | | If it recurs after re-running, escalate — don't ignore it |
| Alert-processing-rule toggle seems to have no effect | Up to ~30 minutes propagation delay is real and documented by Microsoft | Wait, re-check | | | |
| Metric-name check (Part 36) shows a mismatch | Alert was written from assumed metric names, never live-confirmed before now | `az monitor metrics list-definitions` | Stop treating that alert as authoritative; route a fix through source control | | Never hot-fix Bicep alerts directly against a live resource |
| Restore never reaches `Ready` | Wrong restore timestamp, or backup corrupted | `az postgres flexible-server show` on the restored server | Retry with a different restore point before escalating | | Don't conclude "restore works" from a partial or ambiguous result |
| Budget doesn't appear | `budget.bicep` was never deployed separately (it's not part of Pass 1) | `az consumption budget list` | Run Part 37's command | | |

**Before deleting any failed resource:** capture `az deployment operation group list`, the Activity Log, and Container App/Job logs first — an immediate delete destroys the diagnostic trail that would have explained the failure.

---

# PART 53 — How to delete DEV safely

**Stop DEV (Part 43) is not Delete DEV.** They are entirely different operations with entirely different consequences. Deletion is `[DESTRUCTIVE — EXPLICIT APPROVAL REQUIRED]` and is **not** a normal part of this guide's flow — it exists here only for completeness, and requires explicit, current, named approval from your Technical Lead before you run anything below.

**Before deleting, know:** all data in the database will be lost unless a fresh backup/restore-rehearsal-proven snapshot exists; the ACR image history will be lost; all Key Vault secrets in this vault will be lost (subject to soft-delete's retention window); the resource group deletion is not instantly reversible.

```bash
# [DESTRUCTIVE -- EXPLICIT APPROVAL REQUIRED]
az group delete --name rg-noetva-dev --yes
```

Never run this to "save cost" — Stop DEV (Part 43) already achieves the real cost savings without destroying anything.

---

# PART 54 — Daily operations one-pager

| I want to... | Action |
|---|---|
| Start DEV | GitHub Actions → Start Noetva Environment → `environment=dev` |
| Check status | GitHub Actions → Check Noetva Environment Status → `environment=dev` |
| Extend my session | GitHub Actions → Extend Noetva Environment → `additionalHours` |
| Hold for a long session | GitHub Actions → Hold Noetva Environment → `holdUntilUtc` |
| View the frontend | `https://<DEV_FRONTEND_FQDN>` |
| View the backend | `https://<DEV_BACKEND_FQDN>/health` |
| View logs | Log Analytics workspace → Part 35's KQL |
| Check the DB migration head | `SELECT version_num FROM alembic_version;` via `psql` from inside the VNet |
| Check deployed SHA | `az containerapp show --query "properties.template.containers[0].image"` |
| Check image digest | `az acr repository show-manifests --name <DEV_ACR_NAME> --repository noetva/backend -o table` |
| Stop DEV | GitHub Actions → Stop Noetva Environment → `environment=dev` |
| Check budget/cost | Azure Portal → Cost Management |

---

# PART 55 — Master zero-to-Azure checklist

**A. Accounts/access:** [ ] Azure account approved [ ] GitHub admin access [ ] Entra tenant-creation permission [ ] alert email confirmed

**B. Local workstation:** [ ] Git [ ] Docker [ ] Azure CLI [ ] Bicep CLI [ ] GitHub CLI [ ] `psql`

**C. GitHub security:** [ ] Secret scanning enabled [ ] Push protection enabled [ ] `main` branch protection enabled [ ] Environment protection decided

**D. Azure login/subscription:** [ ] `az login` [ ] Correct subscription set [ ] Human checkpoint confirmed (Part 6)

**E. Budget:** [ ] `BUDGET_AMOUNT` approved [ ] `BUDGET_ALERT_EMAIL` confirmed

**F. Resource providers:** [ ] All 11 providers `Registered`

**G. Resource group:** [ ] `rg-noetva-dev` exists with correct tags (after Pass 1)

**H. Networking:** [ ] VNet exists, correct CIDR [ ] Both subnets delegated correctly [ ] Private DNS zone linked [ ] No NAT Gateway present

**I. PostgreSQL:** [ ] Version 17 [ ] `Standard_B1ms`/Burstable [ ] HA Disabled [ ] Public access Disabled [ ] TLS required [ ] Backup 7 days

**J. Database security:** [ ] `noetva_app`/`noetva_migrate`/admin bootstrap complete [ ] Role privileges verified

**K. ACR:** [ ] Basic tier [ ] Admin user disabled

**L. Key Vault:** [ ] RBAC-based [ ] All 5 secrets present (names only confirmed)

**M. Managed identities:** [ ] All 5 exist [ ] RBAC matches Part 18's table

**N. GitHub OIDC:** [ ] `id-cicd` subject correct [ ] `id-lifecycle`'s 3 subjects correct, no wildcard, no `prod`

**O. External ID:** [ ] Tenant created, type "External" confirmed [ ] Frontend app registered [ ] Backend API app registered

**P. Business-tenant claim (CDD-065):** [ ] Custom attribute `tenant_id` created [ ] Claim `noetva_tenant_id` (no Namespace) mapped into the access token on the backend's own Enterprise Application entry (not just ID token) [ ] Save confirmed to succeed (not "This claim type is restricted") [ ] All four `oidcTenantClaim` environment parameters already set to `noetva_tenant_id` in source [ ] DEV test user has a value set

**Q. Pass 1 (CDD-067 two-stage):** [ ] Stage 1a foundation deployment succeeded (`deployApplicationTier=false`) [ ] Key Vault Secrets Officer self-assigned [ ] all six Key Vault secrets populated, including `ctec-migration-database-url` [ ] database roles created (Part 15) [ ] real digest-pinned backend/frontend images pushed [ ] Stage 1c application-tier deployment succeeded (`deployApplicationTier=true`)

**R. Generated values:** [ ] Frontend/backend FQDNs captured [ ] Fed back into Entra redirect URIs, GitHub variables

**S. Images:** [ ] Backend built/pushed, digest captured [ ] Frontend built/pushed with correct build args, digest captured

**T. Database bootstrap:** [ ] Success message confirmed

**U. Migration:** [ ] Head = `0046_oqi5_remediation_tenancy` [ ] 127 tables (126 + alembic_version) [ ] Idempotency re-run confirmed no-op

**V. Backend:** [ ] Deployed by digest [ ] `/health` returns 200

**W. Frontend:** [ ] Deployed by digest [ ] Loads, returns 200

**X. Authentication:** [ ] Real login succeeds [ ] All 6 negative tests performed for real

**Y. Tenant isolation:** [ ] Cross-tenant read fails closed, both directions

**Z. Logging:** [ ] Log Analytics shows real session activity

**AA. Monitoring:** [ ] Metric names live-verified against real resources [ ] Budget deployed

**AB. Lifecycle:** [ ] Start verified [ ] Status shows agreement [ ] Extend verified [ ] Hold verified [ ] Stop verified [ ] DORMANT confirmed

**AC. Backup:** [ ] Configuration confirmed (7 days)

**AD. Restore:** [ ] Rehearsal performed on a temporary server [ ] RPO/RTO recorded [ ] Temporary server deleted

**AE. Cost:** [ ] Active 24h cost captured [ ] Dormant 24h cost captured

**AF. Final acceptance:** [ ] Part 56's record completed and signed off

**AG. Return DEV to DORMANT:** [ ] Stop DEV run one final time before ending the session, unless an approved engineering session requires it to keep running

---

# PART 56 — Final acceptance

```
NOETVA DEV DEPLOYMENT ACCEPTANCE RECORD

Date:                    ______________________
Engineer:                ______________________
Reviewer:                ______________________
Azure account:           ______________________
Azure Directory tenant:  ______________________
Subscription name:       ______________________
Subscription ID:         ______________________
Region:                  eastus2
Git SHA deployed:        ______________________
Backend image digest:    ______________________
Frontend image digest:   ______________________
Migration head:          0046_oqi5_remediation_tenancy
Frontend URL:            ______________________
Backend URL:             ______________________
Noetva DEV tenant:       ______________________
Budget:                  ______________________
Restore test performed:  YES / NO, observed RTO: _____, RPO: _____
Lifecycle Start verified: YES / NO
Lifecycle Stop verified:  YES / NO
Final lifecycle state:    DORMANT
Final Postgres state:     Stopped

Overall: PASS / FAIL
```

A single unresolved security, identity, tenant-isolation, migration, restore, or lifecycle-persistence defect means **FAIL** — do not record a conditional pass for any of those categories. A pending scheduled-workflow observation (e.g. "the nightly sweep hasn't fired yet in real time") may be noted as pending, but the *underlying* workflow logic must already be manually proven correct — a cron schedule not yet elapsing is not the same as unproven behavior.

---

# PART 57 — Official references

Use current official documentation, not blog posts, for anything Azure's or GitHub's own platform behavior — the exact numbers in this guide (e.g. PostgreSQL's auto-restart interval) were correct when written but are Azure's to change.

- Azure Container Apps: `learn.microsoft.com/azure/container-apps/`
- Container Apps Jobs: `learn.microsoft.com/azure/container-apps/jobs`
- PostgreSQL Flexible Server: `learn.microsoft.com/azure/postgresql/flexible-server/`
- PostgreSQL stop/start behavior: `learn.microsoft.com/azure/postgresql/flexible-server/concepts-servers` (confirm the current auto-restart interval here before relying on Part 45's number)
- Private networking for Flexible Server: `learn.microsoft.com/azure/postgresql/flexible-server/concepts-networking`
- Azure Container Registry: `learn.microsoft.com/azure/container-registry/`
- Key Vault RBAC: `learn.microsoft.com/azure/key-vault/general/rbac-guide`
- Managed identities: `learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview`
- Federated identity credentials: `learn.microsoft.com/entra/workload-id/workload-identity-federation`
- GitHub Actions OIDC to Azure: `learn.microsoft.com/azure/developer/github/connect-from-azure`
- Entra External ID tenant features: `learn.microsoft.com/entra/external-id/customers/concept-supported-features-customers`
- Attributes & Claims: `learn.microsoft.com/entra/external-id/customers/how-to-add-attributes-to-token`
- Azure Storage Table / ETag concurrency: `learn.microsoft.com/rest/api/storageservices/insert-entity`, `learn.microsoft.com/rest/api/storageservices/update-entity2`
- Azure Monitor Alert Processing Rules: `learn.microsoft.com/azure/azure-monitor/alerts/alerts-processing-rules`
- Cost Management budgets: `learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets`
- PostgreSQL backup/restore: `learn.microsoft.com/azure/postgresql/flexible-server/concepts-backup-restore`
- GitHub Environments: `docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment`
- GitHub secret scanning / push protection: `docs.github.com/code-security/secret-scanning`
- GitHub branch protection / rulesets: `docs.github.com/repositories/configuring-branches-and-merges-in-your-repository`
- GitHub scheduled workflows: `docs.github.com/actions/using-workflows/events-that-trigger-workflows#schedule`

---

*Document ends. Zero Azure resources, zero GitHub settings, zero application or infrastructure source files were created, modified, or deleted while writing this guide.*
