#!/usr/bin/env bash
# ============================================================
# run_checks.sh — One-command code quality check for Despair Chinese
#
# Usage:
#   chmod +x run_checks.sh
#   ./run_checks.sh
#
# Runs:
#   1. Django system checks
#   2. Python (flake8)
#   3. HTML templates (djlint)
#   4. Unit tests
# ============================================================

set -e

# Colour helpers
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

run_check() {
  local label="$1"
  shift
  echo -e "\n${CYAN}▶ ${label}${NC}"
  if "$@"; then
    echo -e "${GREEN}✓ ${label} passed${NC}"
    PASS=$((PASS+1))
  else
    echo -e "${RED}✗ ${label} failed${NC}"
    FAIL=$((FAIL+1))
  fi
}

# Activate virtualenv if not already active
if [ -z "$VIRTUAL_ENV" ]; then
  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
  else
    echo -e "${RED}No virtual environment found. Run: python3 -m venv venv && pip install -r requirements.txt${NC}"
    exit 1
  fi
fi

echo -e "${YELLOW}============================================================"
echo " Despair Chinese — Code Quality Checks"
echo -e "============================================================${NC}"

# ──────────────────────────────────────────────────────────────
# 1. Django system checks
# ──────────────────────────────────────────────────────────────
run_check "Django system check" python manage.py check --settings=despair.settings.dev

# ──────────────────────────────────────────────────────────────
# 2. Python linting (flake8)
# ──────────────────────────────────────────────────────────────
run_check "Python linting (flake8)" flake8 .

# ──────────────────────────────────────────────────────────────
# 3. HTML template linting (djlint)
# ──────────────────────────────────────────────────────────────
run_check "HTML templates (djlint)" djlint templates/ \
  --profile=django \
  --ignore=H006,H023,H021,H025,H030,H031 \
  --lint

# ──────────────────────────────────────────────────────────────
# 4. Unit tests
# ──────────────────────────────────────────────────────────────
run_check "Unit tests (96 tests)" python manage.py test orders menu reviews accounts \
  --settings=despair.settings.dev --keepdb

# ──────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}============================================================"
echo " Results: ${GREEN}${PASS} passed${YELLOW} / ${RED}${FAIL} failed${YELLOW}"
echo -e "============================================================${NC}"
echo ""
echo -e "${CYAN}External validators to run manually:${NC}"
echo "  HTML:  https://validator.w3.org/nu/?doc=https://despair.cc/"
echo "  CSS:   https://jigsaw.w3.org/css-validator/validator?uri=https://despair.cc/"
echo "  Links: https://validator.w3.org/checklink?uri=https://despair.cc/"
echo "  a11y:  https://wave.webaim.org/report#/https://despair.cc/"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
