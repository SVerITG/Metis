#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/2. Literature"
OUT_DIR="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/05_sources/literature/sleeping-sickness/metadata"

mkdir -p "$OUT_DIR"

inventory_file="$OUT_DIR/library-inventory.tsv"
anomalies_file="$OUT_DIR/library-anomalies.tsv"
md5_all_file="$OUT_DIR/md5-all.txt"
duplicates_file="$OUT_DIR/exact-duplicates.tsv"
catalogue_file="$OUT_DIR/library-catalogue-template.tsv"

printf 'relative_path\tbasename\ttop_folder\textension\tsize_bytes\tmodified_date\n' > "$inventory_file"

while IFS= read -r -d '' file; do
  rel="${file#$SOURCE_ROOT/}"
  base="$(basename "$file")"
  top="${rel%%/*}"
  ext="${base##*.}"
  if [[ "$ext" == "$base" ]]; then
    ext=""
  else
    ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
  fi
  size="$(stat -c '%s' "$file")"
  modified="$(stat -c '%y' "$file" | cut -d' ' -f1)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$rel" "$base" "$top" "$ext" "$size" "$modified" >> "$inventory_file"
done < <(find "$SOURCE_ROOT" -type f -print0)

{
  printf 'type\tpath\n'
  find "$SOURCE_ROOT" -type f | sed "s#^$SOURCE_ROOT/##" | awk -F/ 'NF==1 {print "top_level_file\t" $0}'
  find "$SOURCE_ROOT" -type f \( ! -iname '*.pdf' ! -iname '*.docx' \) | sed "s#^$SOURCE_ROOT/##" | awk '{print "nonstandard_file\t" $0}'
  find "$SOURCE_ROOT" -type f -printf '%f\n' | tr '[:upper:]' '[:lower:]' | sort | uniq -d | awk '{print "duplicate_basename\t" $0}'
} > "$anomalies_file"

find "$SOURCE_ROOT" -type f -print0 | xargs -0 md5sum | sort > "$md5_all_file"

awk '
BEGIN {
  print "hash\tcount\tfile"
}
{
  split($0, parts, "  ")
  hash = parts[1]
  file = substr($0, length(hash) + 3)
  count[hash]++
  files[hash] = files[hash] ? files[hash] "\n" file : file
}
END {
  for (h in count) {
    if (count[h] > 1) {
      n = split(files[h], arr, "\n")
      for (i = 1; i <= n; i++) {
        print h "\t" count[h] "\t" arr[i]
      }
    }
  }
}
' "$md5_all_file" > "$duplicates_file"

awk '
BEGIN {
  FS = OFS = "\t"
}
NR == 1 {
  print "relative_path", "basename", "top_folder", "extension", "size_bytes", "modified_date", "entity_type", "disease", "geography", "method", "surveillance_mode", "elimination_phase", "diagnostic_test", "project_link", "phd_article_link", "relevance_note", "status"
  next
}
{
  print $1, $2, $3, $4, $5, $6, "Paper", "gHAT / HAT", "", "", "", "", "", "", "", "", "to_triage"
}
' "$inventory_file" > "$catalogue_file"
