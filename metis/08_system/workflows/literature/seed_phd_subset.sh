#!/usr/bin/env bash
set -euo pipefail

INPUT="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/05_sources/literature/sleeping-sickness/metadata/library-catalogue-template.tsv"
OUTPUT="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/05_sources/literature/sleeping-sickness/metadata/library-phd-seeded.tsv"

awk '
BEGIN {
  FS = OFS = "\t"
}
function set_geography(path, base,    text) {
  text = path " " base
  if (text ~ /(Democratic Republic of the Congo| DRC|Congo Central|Kongo Central|Kasai|Kasaï|Bandundu|Kinshasa)/) return "DRC"
  if (text ~ /(Côte d.Ivoire|Cote d.Ivoire|Ivory Coast)/) return "Cote dIvoire"
  if (text ~ /(Guinée|Guinea)/) return "Guinea"
  if (text ~ /Uganda/) return "Uganda"
  if (text ~ /Chad|Mandoul/) return "Chad"
  if (text ~ /Republic of Congo/) return "Republic of Congo"
  if (text ~ /West Africa/) return "West Africa"
  if (text ~ /Africa/) return "Africa"
  return ""
}
function set_method(path, base, top,    text) {
  text = tolower(path " " base)
  if (top == "Statistics & Mathematical Modelling") return "modelling"
  if (text ~ /(risk|mapping|spatial|gis|geograph|satscan|cluster)/) return "spatial epidemiology"
  if (text ~ /(diagnostic accuracy|performance|specificity|sensitivity|rapid diagnostic|rdt|serology|trypanolysis|ielisa|loopamp|qpcr|maect|clinical signs|laboratory)/) return "diagnostic evaluation"
  if (text ~ /(quality assurance|digitalisation|digital technologies|trypelim)/) return "quality assurance / digital health"
  if (text ~ /(qualitative|stakeholder|perception|community)/) return "qualitative / implementation research"
  if (text ~ /(integration|primary health|first-line health services|passive screening)/) return "implementation research"
  if (text ~ /(economic|cost)/) return "health economics"
  if (top == "Methodology") return "methods reference"
  if (top == "WHO Atlas") return "atlas / surveillance monitoring"
  return ""
}
function set_surveillance(path, base, top,    text) {
  text = tolower(path " " base)
  if (path ~ /^Screening & Surveillance\/Passive\//) return "Passive"
  if (path ~ /^Screening & Surveillance\/Active\//) return "Active"
  if (text ~ /passive/) return "Passive"
  if (text ~ /active population screening|active screening/) return "Active"
  if (top == "Diagnostics") return "Screening / diagnosis"
  if (top == "WHO Atlas") return "Surveillance monitoring"
  if (top == "Integration") return "Passive / integrated"
  if (top == "Statistics & Mathematical Modelling") return "Surveillance strategy"
  return ""
}
function set_phase(path, base, top,    text) {
  text = tolower(path " " base)
  if (text ~ /post-elimination/) return "Post-elimination"
  if (text ~ /elimination/) return "Elimination"
  if (text ~ /control and surveillance|atlas|monitoring/) return "Elimination monitoring"
  if (text ~ /screen and treat|acoziborole/) return "Transition to elimination"
  return ""
}
function set_test(path, base,    text) {
  text = tolower(path " " base)
  if (text ~ /catt/) return "CATT"
  if (text ~ /sd bioline|abbott bioline|bioline hat 2/) return "RDT"
  if (text ~ /sero-k-set/) return "HAT Sero-K-SeT"
  if (text ~ /trypanolysis/) return "Trypanolysis"
  if (text ~ /ielisa/) return "iELISA"
  if (text ~ /loopamp/) return "LAMP"
  if (text ~ /qpcr|sl-rna/) return "Molecular"
  if (text ~ /maect/) return "mAECT"
  if (text ~ /clinical signs/) return "Clinical signs"
  return ""
}
function set_article(path, base, top,    text) {
  text = tolower(path " " base)
  if (text ~ /(risk|distribution and risk|mapping|foci|historic data|regions for enhanced control|population at risk|area at risk)/) return "Article 1: historical risk mapping and foci"
  if (text ~ /(intensified screening|kongo central|integration of diagnosis and treatment|first-line health services|primary health|passive screening and diagnosis|integrated hat surveillance|development and implementation of a strategy)/) return "Article 2/4: passive screening system and integration"
  if (text ~ /(diagnostic accuracy|performance|specificity|sensitivity|quality assurance|clinical signs|rapid diagnostic|rdt|trypanolysis|ielisa|sl-rna|loopamp|maect|abbott bioline|sero-k-set|laboratory test)/) return "Article 3: test performance and quality"
  if (text ~ /(criteria for selecting sentinel|select health structures|facility|fixed health facilities|capacities of fixed health facilities)/) return "Article 5: facility targeting"
  if (text ~ /(modelling|timelines to elimination|sampling|persistence|intervention strategies|forecasting|elimination metrics|sustainable endpoint)/) return "Article 6: sampling and modelling"
  if (top == "WHO Atlas") return "PhD framework / monitoring context"
  return ""
}
function set_note(path, base, top,    text) {
  text = tolower(path " " base)
  if (top == "WHO Atlas") return "Contextual monitoring and verification reference"
  if (text ~ /acoziborole|screen.treat|stroghat/) return "Relevant to future transition and screen-and-treat strategy"
  if (text ~ /quality assurance|digital/) return "Supports surveillance quality and digital workflow questions"
  if (text ~ /passive screening|integration|first-line health services/) return "High relevance to passive surveillance redesign"
  if (text ~ /risk|mapping|foci|distribution/) return "High relevance to historical risk and focus delineation"
  if (text ~ /modelling|elimination metrics|timelines to elimination|persistence/) return "High relevance to post-elimination sampling logic"
  if (text ~ /diagnostic accuracy|specificity|performance|rdt|serology/) return "High relevance to diagnostic performance article"
  return ""
}
NR == 1 {
  print $0
  next
}
{
  top = $3
  if (top !~ /^(WHO Atlas|Screening & Surveillance|Diagnostics|Epidemiology|Statistics & Mathematical Modelling|Elimination|Integration|Methodology)$/) next
  $8 = "gHAT / HAT"
  $9 = set_geography($1, $2)
  $10 = set_method($1, $2, top)
  $11 = set_surveillance($1, $2, top)
  $12 = set_phase($1, $2, top)
  $13 = set_test($1, $2)
  $14 = "PhD / sleeping-sickness"
  $15 = set_article($1, $2, top)
  $16 = set_note($1, $2, top)
  if ($15 != "") $17 = "seeded"
  else $17 = "to_triage"
  print $0
}
' "$INPUT" > "$OUTPUT"
