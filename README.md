# AIOps Microservices Platform — Project & DevOps Revision Notes

End-to-end DevOps / SRE portfolio project running at **$0 cost** on a local WSL2 workstation (8 GB RAM host, 4 GB WSL2 cap) + GitHub Actions + GHCR.

**Repo Structure**
- `app/` — Microservices code & multi-stage Dockerfiles
- `infra/` — Terraform & policy-as-code (upcoming)
- `gitops/` — Kubernetes manifests & Argo CD (upcoming)
- `.github/workflows/` — GitHub Actions CI/CD pipelines
- `docs/` — Architecture diagrams, ADRs, runbooks, postmortems

---

## Day 1 Revision Notes (Phase 0 & Phase 1 Part 1)

### 1. WSL2 & Linux Workstation Setup
- **Why WSL2:** Production servers and containers run on Linux. Developing inside WSL2 Ubuntu avoids Windows path, line-ending (`CRLF` vs `LF`), and file-permission bugs.
- **Performance rule:** Always keep repos inside the Linux filesystem (`~/aiops-platform`), **never** in `/mnt/c/...` (cross-OS mounts make Git and Docker builds painfully slow).
- **Hardware guardrail (8 GB RAM):** Cap WSL2 in `%USERPROFILE%\.wslconfig` (`memory=4GB`, `processors=4`, `swap=2GB`) so Linux never freezes Windows. Run `wsl --shutdown` in PowerShell after any edit, then verify with `free -h` inside Ubuntu.
- **Fixing `Wsl/Service/E_UNEXPECTED`:**
  1. `wsl --shutdown` then `wsl --update`
  2. Restart **WSL Service** in `services.msc`
  3. If the first-run image is corrupted: `wsl --unregister Ubuntu` and reinstall with `wsl --install --web-download -d Ubuntu`
  4. Verify CPU Virtualization (`Intel VT-x`) is **Enabled** in Task Manager → Performance → CPU.

### 2. Linux Users & Why We Avoid `root`
- **Rule:** Never do daily work as `root` (UID `0`). One bad command can break the OS, and many DevOps tools behave differently or refuse to run as `root`.
- **Key commands:**
  - `wsl -u root` — Boot into WSL as `root` for admin/recovery tasks.
  - `adduser <name>` — Create a standard user and `/home/<name>`.
  - `usermod -aG sudo <name>` — Add user to the `sudo` group (`-aG` appends without wiping existing groups).
  - `deluser --remove-home <name>` — Delete a user and its home folder (`pkill -u <name>` first if processes are running).
  - `/etc/wsl.conf` — Set `[user]` → `default=swaraj` so Ubuntu logs into your user automatically after `wsl --shutdown`.

### 3. Native Docker Engine vs. Docker Desktop
- **Why native `docker-ce` inside WSL2:** Docker Desktop eats 1.5–2 GB of RAM just to run its extra VM and GUI. Native Docker Engine inside WSL2 gives the exact same CLI/daemon with minimal RAM overhead.
- **Key commands:**
  - `sudo usermod -aG docker $USER && newgrp docker` — Run `docker` without `sudo`.
  - `sudo service docker start` — Start the Docker daemon after a reboot.
  - `docker run --rm -v "<host>:<container>" <image> <cmd>` — `--rm` deletes the container on exit; `-v` mounts a host folder into the container (`outside:inside`).
  - `docker stats --no-stream` — One-shot CPU/RAM check.
  - `docker exec <container> whoami` — Verify which user a running container executes as.
  - `docker stop <name> && docker rm <name>` — Clean up after every lab to save RAM.

### 4. Secret Scanning (Gitleaks) & Shift-Left Security
- **Why it matters:** Bots scrape public GitHub repos in seconds. Leaking an API/AWS key can cause immediate account compromise or billing fraud.
- **Defense in Depth (run in TWO places):**
  - **Local pre-commit hook (`.git/hooks/pre-commit`):** Runs `gitleaks protect --staged` before a commit is created. Local only (not pushed to GitHub).
  - **CI workflow (`.github/workflows/secret-scan.yml`):** Runs `gitleaks detect` across full Git history on every push/PR in case someone bypasses local hooks (`git commit --no-verify`).
- **Interview gotcha:** Deleting a leaked key in a second commit does **not** fix the leak—it stays in Git history. Always **revoke/rotate the credential immediately**, then scrub history if required.
- **Bash heredoc (`cat << 'EOF' > file`):** Fast way to write multi-line config files without an editor. Quoting `'EOF'` prevents bash from expanding `$` variables inside the file.

### 5. GitHub Actions Fundamentals (vs. Jenkins)
- **Where workflows live:** `.github/workflows/*.yml` (YAML uses strict **space indentation**, never tabs).
- **4 Core Blocks:**
  - `on:` — Trigger (`push`, `pull_request`, `workflow_dispatch`).
  - `jobs:` — Named units of work.
  - `runs-on:` — Ephemeral cloud VM (`ubuntu-latest`).
  - `steps:` — Sequential tasks using `uses:` (pre-built Marketplace Action like `actions/checkout@v7`) or `run:` (shell commands).
- **Key details:**
  - Every job starts on a **blank VM**—your code isn't there until `actions/checkout@v7` runs.
  - `fetch-depth: 0` downloads the **entire Git history** (required for Gitleaks `detect` to scan old commits).
  - `${{ github.workspace }}` is a GitHub Actions expression (works only on GitHub runners); local Bash uses `$(pwd)`.
  - **Debugging runs:** 0-second failure = YAML syntax error. 10s+ failure = runner started, but a command inside a step exited non-zero. Warnings (like Node.js 20 deprecation) do **not** fail a green job, but should be fixed by bumping action versions (e.g., `actions/checkout@v7` for Node.js 24).
- **GitHub Actions vs. Jenkins (Interview Summary):**
  - **GitHub Actions:** Managed SaaS, YAML-based, zero server maintenance, default for modern cloud-native teams.
  - **Jenkins:** Self-hosted Controller/Agent, Groovy (`Jenkinsfile`), high plugin/maintenance overhead, still common in large enterprises/banks/on-prem networks.

### 6. Multi-Stage Non-Root Dockerfiles & Trivy Scanning
- **Multi-stage build (`AS builder` → `AS runtime`):** Installs dependencies in Stage 1 and copies only the compiled virtualenv (`/opt/venv`) + app code into Stage 2. Smaller image, smaller attack surface.
- **Non-root container (`USER appuser`):** Creates a dedicated UID (`10001`) so a compromised app doesn't have `root` inside the container.
- **Why `python:3.13-slim-trixie` over `alpine`:** Alpine uses `musl libc` instead of `glibc`, which breaks many Python compiled wheels. Pinning `-trixie` prevents surprise Debian OS upgrades.
- **`.dockerignore`:** Keeps `__pycache__`, `.venv`, and `.env` out of the Docker build context.
- **Acting on Trivy reports:**
  1. Always check the **`Fixed Version`** column first.
  2. Patch app CVEs in `requirements.txt`; patch OS CVEs by pulling newer base images or switching to slimmer images.
  3. Ignore unpatched CVEs in CI with `--ignore-unfixed` so teams aren't blocked forever; document accepted risks in `.trivyignore` with a reason and expiry date.
  4. Enforce as a CI gate using `--exit-code 1 --ignore-unfixed --severity HIGH,CRITICAL` **before** pushing to a registry.
- **Readable Trivy CLI tricks:**
  - `... | less -S` — Disables line wrapping (use Left/Right arrows to scroll, `q` to quit).
  - `--table-mode summary` — Compact CVE count summary.
  - `-o /out/report.txt` — Export report to a file.

---
---

## Day 2 Revision Notes (Phase 1 Part 2)

### 7. Automated CI Build, Trivy Gate & GHCR (`.github/workflows/build-push-api.yml`)
- **Path filtering (`paths:`):** Restricts the workflow to trigger only when files inside `app/api/**` or the workflow file itself change—prevents wasted CI minutes in monorepos when editing docs or other services.
- **Manual triggers (`workflow_dispatch:`):** Adds a **"Run workflow"** button in the GitHub Actions UI so you can rebuild on demand without pushing a dummy commit.
- **Least-privilege `permissions:` (`contents: read`, `packages: write`):** Grants GitHub's automatic, short-lived `GITHUB_TOKEN` only the exact rights needed to push to `ghcr.io`—zero static passwords or PATs stored in Secrets.
- **Dual image tagging (`:latest` + `:${{ github.sha }}`):** Never rely only on `:latest` in production. Tagging with the Git commit SHA gives full traceability (which exact code commit is running) and clean rollbacks.
- **Security gate placement:** Trivy runs **after `docker build` and before `docker push`** with `--exit-code 1 --ignore-unfixed --severity HIGH,CRITICAL`. If a fixable severe CVE exists, the pipeline fails and the vulnerable image never reaches GHCR.
- **GHCR visibility:** Newly pushed GHCR packages default to **Private**. Switching visibility to **Public** (Package settings → Danger Zone) allows local Docker and Kubernetes clusters to pull images without configuring `imagePullSecrets`.
## Progress Tracker
- [x] **Phase 0:** WSL2 (4 GB cap), native Docker Engine, repo setup, Gitleaks pre-commit + GitHub Actions CI
- [x] **Phase 1 (Part 1):** FastAPI `api` service, multi-stage non-root `Dockerfile`, local Trivy scan
- [x] **Phase 1 (Part 2):** Automate build, Trivy security gate, and push to GHCR via GitHub Actions
- [ ] **Phase 2 (Next):** Local Kubernetes (`k3d`)
