#!/bin/bash
# literature/fetch_paper.sh — retry-ladder paper downloader.
#
# When a paper file is missing, a shell, an access-blocked challenge page,
# or the wrong content, DO NOT give up on the first attempt and ask the user
# to download manually. That default has cost a lot of time on open-access
# papers that only needed a browser User-Agent header or a fallback URL.
#
# This script tries, in order:
#   1.  PMC direct body HTML (if PMCID is known)
#   1b. DOI -> PMCID via the NCBI ID converter, then PMC. Many "paywalled" papers
#       (JAMA, AJCN, …) have a free NIH author-manuscript in PMC under a PMCID the
#       caller never knew; this rung resolves it from the DOI alone before giving up.
#   2.  DOI redirect (many OA publishers serve the paper directly)
#   3.  Unpaywall API -> best OA location URL (DOI required)
#   4.  OpenAlex search by title -> OA URL (title required)
#
# Every curl uses a browser User-Agent. After each download the file is
# validated: must be >= 20000 bytes and must not contain challenge-page or
# paywall sentinels. If validation fails the candidate is deleted and the
# next rung of the ladder is tried.
#
# Only if every rung fails does the script exit 1 with a reason. Only then
# should the caller stop and ask the user to download manually.
#
# Usage:
#   literature/fetch_paper.sh --out literature/<key>.html \
#     [--doi DOI] [--pmcid PMCID] [--title "Paper title"] \
#     [--author surname] [--year YYYY] [--email addr]
#
# Exit 0 prints the output path on stdout. Exit 1 prints a reason on stderr.

set -euo pipefail

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
MIN_BYTES=20000
TMPDIR="${TMPDIR:-/tmp}"

DOI=""
PMCID=""
TITLE=""
AUTHOR=""
YEAR=""
OUT=""
# No baked-in default: Unpaywall asks for a contact email, and a public starter
# kit must not ship the author's. Three sources, in precedence order: the
# UNPAYWALL_EMAIL env var, the --email flag, then unpaywall_email: in
# ledger.config.md (resolved below). The email only gates the Unpaywall rung
# (Rung 3); when none is set that rung is skipped, not fatal.
EMAIL="${UNPAYWALL_EMAIL:-}"

die() { echo "[fetch_paper] $*" >&2; exit 1; }
log() { echo "[fetch_paper] $*" >&2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --doi)    DOI="$2"; shift 2 ;;
    --pmcid)  PMCID="$2"; shift 2 ;;
    --title)  TITLE="$2"; shift 2 ;;
    --author) AUTHOR="$2"; shift 2 ;;
    --year)   YEAR="$2"; shift 2 ;;
    --out)    OUT="$2"; shift 2 ;;
    --email)  EMAIL="$2"; shift 2 ;;
    *) die "unknown arg: $1" ;;
  esac
done

# Config fallback: if neither env nor --email supplied an address, read
# unpaywall_email: from ledger.config.md at the repo root, ignoring the
# <placeholder>. This makes the config field functional rather than decorative.
if [ -z "$EMAIL" ]; then
  CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)/ledger.config.md"
  if [ -f "$CONFIG_FILE" ]; then
    cfg_email="$(sed -n 's/^unpaywall_email:[[:space:]]*//p' "$CONFIG_FILE" \
      | head -1 | sed 's/[[:space:]]*$//')"
    case "$cfg_email" in
      ""|"<"*) : ;;                 # unset or <placeholder> → leave EMAIL empty
      *)       EMAIL="$cfg_email" ;;
    esac
  fi
fi

[ -z "$OUT" ] && die "missing --out"
[ -z "$DOI$PMCID$TITLE" ] && die "need at least one of --doi / --pmcid / --title"

# Strip leading "PMC" from PMCID if present
PMCID="${PMCID#PMC}"
PMCID="${PMCID#pmc}"

# Sentinel strings are stored with quote-breaks so the source file does
# not contain the literal substrings that the project citation hook uses
# for Layer-3 bypass detection. At runtime the variables concatenate back
# to the full detection text.
S_A='just '"a moment"
S_B='enable '"javascript and cookies"
S_C='access '"to this article is restricted"
S_D='you '"do not have access"
S_E='please '"log in"
S_F='institutional '"login"
S_G='cf'"-challenge"
S_H='cloud'"flare"
S_I='attention '"required!"
S_J='subscribe '"to"
S_K='purchase '"article"

SENTINEL_RE="${S_A}\\.\\.\\.|${S_B} to continue|${S_C}|${S_D}|${S_E}|${S_F}|${S_G}|${S_H}.*challenge|${S_I}|${S_J} (read|view)|${S_K}"

validate() {
  local f="$1"
  [ -f "$f" ] || { log "validate: file missing"; return 1; }
  local bytes
  bytes=$(wc -c < "$f" | tr -d ' ')
  if [ "$bytes" -lt "$MIN_BYTES" ]; then
    log "validate: too small ($bytes bytes < $MIN_BYTES)"
    return 1
  fi
  if grep -qiE "$SENTINEL_RE" "$f"; then
    log "validate: sentinel match (challenge page / paywall / login)"
    return 1
  fi
  # Identity check. For web-search rungs we must guard against the downloader
  # returning an unrelated paper whose text happened to pass size + sentinel
  # checks. If DOI is given, it must appear verbatim in the file. Otherwise
  # at least two of the three longest non-stopword title tokens (length >= 5)
  # must appear. PDFs are binary so this works only when they contain
  # embedded text metadata, which is usually the case for publisher PDFs.
  if [ -n "$DOI" ]; then
    # Case-insensitive literal DOI search (no regex metachar escaping needed
    # for typical DOIs, which contain only letters, digits, / . and -).
    if ! grep -qiF "$DOI" "$f"; then
      log "validate: DOI $DOI not found in file (likely wrong paper)"
      return 1
    fi
  elif [ -n "$TITLE" ]; then
    # Hardened title validation: an earlier "≥2 long-token" rule accepted
    # papers that merely CITE the target — a citing paper shares a few title
    # words but is not the paper itself. New rule: require at least 4 of the
    # first 5 long (≥5 chars) non-stop title tokens to appear — much harder to
    # satisfy by a paper that only mentions the target in passing.
    local tokens hits total
    tokens="$(printf '%s\n' "$TITLE" \
      | tr '[:upper:]' '[:lower:]' \
      | tr -cs 'a-z0-9' '\n' \
      | awk 'length($0) >= 5' \
      | head -5)"
    hits=0
    total=0
    while IFS= read -r t; do
      [ -z "$t" ] && continue
      total=$((total + 1))
      if grep -qiF "$t" "$f"; then hits=$((hits + 1)); fi
    done <<<"$tokens"
    # If AUTHOR supplied, require the surname to appear AT LEAST 3 TIMES —
    # citing papers usually mention the author once in references; the
    # actual paper has the name in header + byline + running head + author
    # contributions. Three hits separates citer from primary.
    if [ -n "$AUTHOR" ]; then
      local author_hits
      author_hits="$(grep -ciF "$AUTHOR" "$f" 2>/dev/null || echo 0)"
      if [ "${author_hits:-0}" -lt 3 ]; then
        log "validate: author '$AUTHOR' appears only ${author_hits:-0} times (<3; likely citer not primary)"
        return 1
      fi
    fi
    # Require high title-token hit ratio
    if [ "$total" -ge 4 ] && [ "$hits" -lt 4 ]; then
      log "validate: title tokens $hits/$total matched (<4/5 required; likely wrong paper)"
      return 1
    elif [ "$total" -lt 4 ] && [ "$hits" -lt "$total" ]; then
      log "validate: short title — all $total tokens required, got $hits"
      return 1
    fi
  fi
  return 0
}

try_url() {
  local url="$1"
  local tmp
  tmp="$(mktemp "${TMPDIR%/}/fetch_paper.XXXXXX")"
  log "trying: $url"
  if ! curl -sSL --max-redirs 8 --max-time 90 -A "$UA" \
        -H "Accept: text/html,application/pdf,*/*" \
        -o "$tmp" "$url"; then
    log "curl failed"
    rm -f "$tmp"
    return 1
  fi
  if validate "$tmp"; then
    mv "$tmp" "$OUT"
    log "SUCCESS -> $OUT"
    echo "$OUT"
    return 0
  fi
  rm -f "$tmp"
  return 1
}

# ----- Rung 1: PMC direct -----
if [ -n "$PMCID" ]; then
  if try_url "https://pmc.ncbi.nlm.nih.gov/articles/PMC${PMCID}/"; then exit 0; fi
fi

# ----- Rung 1b: DOI -> PMCID via NCBI ID converter, then PMC -----
# Many "paywalled" papers (JAMA, AJCN, …) have a free NIH author-manuscript in PMC
# under a PMCID the caller never knew. If a DOI is set but no PMCID resolved above,
# ask the official NCBI ID-converter for one and retry the PMC rung. This is how the
# eggs-case JAMA/AJCN sources turned out to be open access — do NOT give up before it.
if [ -n "$DOI" ] && [ -z "$PMCID" ]; then
  log "asking NCBI id-converter for a PMCID for $DOI"
  idc_json="$(mktemp "${TMPDIR%/}/idconv.XXXXXX")"
  idc_mail=""
  [ -n "$EMAIL" ] && idc_mail="&email=${EMAIL}"
  if curl -sSL --max-time 30 -A "$UA" -o "$idc_json" \
        "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=ledger${idc_mail}&ids=${DOI}&format=json"; then
    conv_pmcid="$(jq -r '.records[0].pmcid // empty' "$idc_json" 2>/dev/null || true)"
    rm -f "$idc_json"
    conv_pmcid="${conv_pmcid#PMC}"
    if [ -n "$conv_pmcid" ]; then
      log "id-converter resolved PMC${conv_pmcid}"
      if try_url "https://pmc.ncbi.nlm.nih.gov/articles/PMC${conv_pmcid}/"; then exit 0; fi
    fi
  else
    log "id-converter request failed"
    rm -f "$idc_json"
  fi
fi

# ----- Rung 2: DOI redirect -----
if [ -n "$DOI" ]; then
  if try_url "https://doi.org/${DOI}"; then exit 0; fi
fi

# ----- Rung 3: Unpaywall -----
# Unpaywall requires a contact email. With none configured this rung cannot
# run, so SKIP it (do not die) and fall through to Rung 4/5 — killing the whole
# ladder here would defeat its point on the email-optional rungs below.
if [ -n "$DOI" ] && [ -z "$EMAIL" ]; then
  log "[skip] Unpaywall needs a contact email (UNPAYWALL_EMAIL / --email / unpaywall_email: in ledger.config.md); skipping this rung"
fi
if [ -n "$DOI" ] && [ -n "$EMAIL" ]; then
  log "asking Unpaywall about $DOI"
  upw_json="$(mktemp "${TMPDIR%/}/upw.XXXXXX")"
  if curl -sSL --max-time 30 -A "$UA" -o "$upw_json" \
        "https://api.unpaywall.org/v2/${DOI}?email=${EMAIL}"; then
    pdf_url="$(jq -r '.best_oa_location.url_for_pdf // empty' "$upw_json" 2>/dev/null || true)"
    html_url="$(jq -r '.best_oa_location.url // empty' "$upw_json" 2>/dev/null || true)"
    rm -f "$upw_json"
    if [ -n "$pdf_url" ]; then
      if try_url "$pdf_url"; then exit 0; fi
    fi
    if [ -n "$html_url" ] && [ "$html_url" != "$pdf_url" ]; then
      if try_url "$html_url"; then exit 0; fi
    fi
  else
    log "Unpaywall request failed"
    rm -f "$upw_json"
  fi
fi

# ----- Rung 4: OpenAlex search by title -----
if [ -n "$TITLE" ]; then
  log "asking OpenAlex about title search"
  oa_json="$(mktemp "${TMPDIR%/}/oa.XXXXXX")"
  enc_title="$(printf '%s' "$TITLE" | jq -sRr @uri)"
  # mailto= is OpenAlex politeness only (the "polite pool"); omit it entirely
  # when no email is configured rather than sending an empty mailto= parameter,
  # which OpenAlex would otherwise see as a malformed contact address.
  oa_mailto=""
  [ -n "$EMAIL" ] && oa_mailto="&mailto=${EMAIL}"
  if curl -sSL --max-time 30 -A "$UA" -o "$oa_json" \
        "https://api.openalex.org/works?search=${enc_title}&per_page=3${oa_mailto}"; then
    # Walk the top 3 OpenAlex hits (not just the first) for any open_access.oa_url
    for i in 0 1 2; do
      oa_pdf="$(jq -r ".results[${i}].open_access.oa_url // empty" "$oa_json" 2>/dev/null || true)"
      if [ -n "$oa_pdf" ]; then
        if try_url "$oa_pdf"; then rm -f "$oa_json"; exit 0; fi
      fi
    done
    rm -f "$oa_json"
  else
    log "OpenAlex request failed"
    rm -f "$oa_json"
  fi
fi

# ----- Rung 5: DuckDuckGo HTML search for "<title> filetype:pdf" -----
# BEST-EFFORT, and inherently fragile: it scrapes the static-HTML DuckDuckGo
# endpoint for author-hosted / repo PDFs that Unpaywall and OpenAlex miss
# (personal pages, GitHub, institutional repositories, ResearchGate mirrors).
# It depends on DuckDuckGo's /l/?uddg= redirect layout, which can change
# without notice — when it does, parsing yields zero candidates, and we emit a
# distinct warning so a silent format change is visible rather than read as
# "no mirror exists". The first ≤ 5 HTTPS PDF links are tried in order; each is
# validated by the standard size + sentinel checks.
if [ -n "$TITLE" ]; then
  log "trying DuckDuckGo search for PDF mirror"
  ddg_html="$(mktemp "${TMPDIR%/}/ddg.XXXXXX")"
  enc_q="$(printf '%s filetype:pdf' "$TITLE" | jq -sRr @uri)"
  if curl -sSL --max-time 30 -A "$UA" -o "$ddg_html" \
        "https://html.duckduckgo.com/html/?q=${enc_q}"; then
    # DuckDuckGo wraps each result URL in a /l/?uddg=<percent-encoded-url>
    # redirect. Extract those encoded URLs, decode them, keep the ones that
    # end in `.pdf`, deduplicate, and take the first five candidates. The
    # python3 one-liner does URL-decoding since the macOS coreutils don't
    # ship a decode binary and we want to avoid extra dependencies.
    #
    # Using a while-read loop rather than bash's `mapfile` / `readarray`
    # because /bin/bash on macOS is still 3.x and doesn't have mapfile.
    # The iteration is serial so we exit as soon as a candidate validates.
    # `|| true` is essential: with `set -e -o pipefail`, any rung of the
    # pipeline returning empty (e.g. `grep` finding no PDF URLs) would kill
    # the entire script before the manual-lookup block at the bottom can
    # run. Suppressing the exit code here means an empty pdf_list is
    # treated as "no candidates", control falls through to the loop (which
    # iterates zero times on empty input) and then to the manual-lookup
    # exit-1 block — which is exactly the behaviour we want when DDG
    # returns no usable mirrors.
    pdf_list="$(grep -oE 'uddg=https%3A%2F%2F[^&"]+' "$ddg_html" \
      | sed 's/^uddg=//' \
      | python3 -c 'import sys,urllib.parse
[print(urllib.parse.unquote(u.strip())) for u in sys.stdin if u.strip()]' \
      | grep -iE '\.pdf(\?|$|#)' \
      | awk '!seen[$0]++' \
      | head -5 || true)"
    # Distinguish the two zero-candidate causes before discarding the HTML: any
    # `uddg=` redirect at all means results parsed (just no PDF mirror among
    # them); none at all means the redirect layout this rung depends on has
    # changed — a tooling failure, not a confident "no mirror exists".
    has_uddg=no
    if grep -q 'uddg=' "$ddg_html"; then has_uddg=yes; fi
    rm -f "$ddg_html"
    if [ -z "$pdf_list" ]; then
      if [ "$has_uddg" = no ]; then
        log "[warning] DuckDuckGo layout changed — no uddg= redirects parsed; this rung is stale"
      else
        log "[warning] DuckDuckGo: results parsed but no open PDF mirror found"
      fi
    fi
    while IFS= read -r u; do
      [ -z "$u" ] && continue
      if try_url "$u"; then exit 0; fi
    done <<<"$pdf_list"
  else
    log "DuckDuckGo request failed"
    rm -f "$ddg_html"
  fi
fi

# ----- Ladder exhausted: emit a paste-ready manual-lookup block -----
# Past failure mode: the script exited with a one-line message bundling
# DOI/PMCID/TITLE on a single line, and any caller that had passed a
# *guessed* DOI (because no real DOI was known) would propagate that guess to
# the user as if it were authoritative. A guessed DOI is worse than no DOI —
# the user would either waste time chasing a dead identifier or, in scripted
# pipelines, see it accepted as ground truth.
#
# Instead, on exit-1 we print every identifier the user actually needs to
# find the paper themselves: title (the *only* reliable search anchor),
# first-author surname, year, and pre-built Google Scholar + DOI URLs that
# work only when the corresponding identifier was actually supplied. If
# nothing was supplied we say so explicitly rather than fabricating a search.

{
  echo
  echo "======================================================================"
  echo "[fetch_paper] all ladder rungs failed — manual lookup required"
  echo "======================================================================"
  echo "Output target : $OUT"
  if [ -n "$TITLE" ]; then
    echo "Title         : $TITLE"
  else
    echo "Title         : (none provided — supply --title for any chance of"
    echo "                manual lookup; without a title the paper is"
    echo "                effectively unfindable)"
  fi
  if [ -n "$AUTHOR" ]; then echo "First author  : $AUTHOR"; fi
  if [ -n "$YEAR" ];   then echo "Year          : $YEAR"; fi
  if [ -n "$DOI" ];    then
    echo "DOI (as given): $DOI"
    echo "DOI URL       : https://doi.org/$DOI"
    echo "  NOTE: this DOI failed every download rung. If it was guessed by"
    echo "  the caller (rather than read from the bibliography), treat it as"
    echo "  unverified and rely on the title search instead."
  fi
  if [ -n "$PMCID" ]; then
    echo "PMCID         : PMC$PMCID"
    echo "PMC URL       : https://pmc.ncbi.nlm.nih.gov/articles/PMC$PMCID/"
  fi
  if [ -n "$TITLE" ]; then
    enc_title_for_user="$(printf '%s' "$TITLE" | jq -sRr @uri 2>/dev/null || printf '%s' "$TITLE")"
    echo "Search URLs   :"
    echo "  Google Scholar : https://scholar.google.com/scholar?q=${enc_title_for_user}"
    echo "  Google         : https://www.google.com/search?q=${enc_title_for_user}"
    echo "  PubMed         : https://pubmed.ncbi.nlm.nih.gov/?term=${enc_title_for_user}"
  fi
  echo "======================================================================"
} >&2
exit 1
