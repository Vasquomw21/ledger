---
paper: "Zhong et al. (2021)"
title: "Associations of dietary cholesterol and egg consumption with cardiovascular disease and mortality: pooled US cohorts"
doi: "10.1093/ije/dyaa205"
pmcid: "PMC8687122"
url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8687122/"
source_version: "published (Int J Epidemiol 2021)"
file: "literature/zhong_2021.html"
retrieved: "20260614"
verified_by: "Ledger pipeline (Claude)"
source_sha256: "cf4b6d2b5091ae7274674099df08e1356ce89c924ee9a86d50e06c9ff701fc29"
extract_sha256: "c0c72240710c19468d6120c16ecd04b2b825eeeb5b7763ed080390617739626c"
body_sha256: "b39a88341420510f910c8c9c9dae93489909858889120b7d9d6190e2fdb1bd77"
verifier_version: "2"
verified_verdict: "pass"
verified_date: "20260614"
---

# Verified Claims — Zhong et al. (2021)

A re-analysis of the same six harmonised US prospective cohorts as Zhong 2019, here framed as a substitution analysis of animal protein foods against incident CVD and all-cause mortality.

## Claim 1: The analysis pools the same six harmonised US prospective cohorts (ARIC, CARDIA, CHS, FHS, FOS, MESA)
> "These six cohort studies included the Atherosclerosis Risk in Communities (ARIC) Study, Coronary Artery Risk Development in Young Adults (CARDIA) Study, Cardiovascular Health Study (CHS), Framingham Heart Study (FHS), Framingham Offspring Study (FOS) and Multi-Ethnic Study of Atherosclerosis (MESA)."
**ID:** cohort-6us-pool
**Location:** Methods, Study population
**Grep command used:** `grep "These six cohort studies included the Atherosclerosis Risk in Communities" extracted/zhong_2021.txt`
**Addresses:** eggs-cvd

## Claim 2: Eggs are among the less-healthy protein sources; substituting them with plant foods or fish lowers CVD and mortality risk
> "Nuts, whole grains, legumes and fish appeared to be healthier protein sources than eggs, processed meat, unprocessed red meat and poultry for preventing incident CVD and premature death."
**ID:** eggs-less-healthy-substitution
**Location:** Abstract, Conclusions
**Grep command used:** `grep "appeared to be healthier protein sources than eggs" extracted/zhong_2021.txt`
**Addresses:** eggs-cvd
**Supports:** zhao_2022:harmful-mortality (grounded by #eggs-less-healthy-substitution)
**Correlated-with:** zhong_2019:cholesterol-eggs-harmful (grounded by #cohort-6us-pool) [shared: re-analyses the same six pooled US cohorts as Zhong 2019 — not an independent confirmation]
