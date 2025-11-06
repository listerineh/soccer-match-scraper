#!/bin/bash

SCRIPT_DIR="scripts"
MAPPING_FILE="data/mappings/city_mappings.json"

SCRAPER="scraper.py"
TEAM_GEN="generate_teams.py"
PROCESSOR="process_altitude.py"

DATA_DIR="data"
RAW_DIR="$DATA_DIR/raw"
PROCESSED_DIR="$DATA_DIR/processed"

SUD_RAW_MATCHES="$RAW_DIR/sudamericana_matches.json"
SUD_TEAM_LIST="$RAW_DIR/unique_teams_sudamericana.txt"
SUD_FINAL_CSV="$PROCESSED_DIR/sudamericana_analysis.csv"

LIB_RAW_MATCHES="$RAW_DIR/libertadores_matches.json"
LIB_TEAM_LIST="$RAW_DIR/unique_teams_libertadores.txt"
LIB_FINAL_CSV="$PROCESSED_DIR/libertadores_analysis.csv"

rm -f "$SUD_RAW_MATCHES"
rm -f "$SUD_TEAM_LIST"
rm -f "$SUD_FINAL_CSV"
rm -f "$LIB_RAW_MATCHES"
rm -f "$LIB_TEAM_LIST"
rm -f "$LIB_FINAL_CSV"

echo "========================================================"
echo "=== INICIANDO WORKFLOW ==="
echo "========================================================"
echo ""

echo "--- (SUD) Step 1: Running Scraper ($SCRAPER) ---"
python3 "$SCRIPT_DIR/$SCRAPER" sudamericana
echo "--- (SUD) Step 1 Finished. ---"
echo ""

echo "--- (LIB) Step 2: Running Scraper ($SCRAPER) ---"
python3 "$SCRIPT_DIR/$SCRAPER" libertadores
echo "--- (LIB) Step 2 Finished. ---"
echo ""

echo "--- (SUD) Step 3a: Running Team Generator ($TEAM_GEN) ---"
python3 "$SCRIPT_DIR/$TEAM_GEN" sudamericana
echo "--- (LIB) Step 3b: Running Team Generator ($TEAM_GEN) ---"
python3 "$SCRIPT_DIR/$TEAM_GEN" libertadores
echo "--- Step 3 Finished. ---"
echo ""

echo "--- (SUD) Step 4: Running Altitude Processor ($PROCESSOR) ---"
python3 "$SCRIPT_DIR/$PROCESSOR" sudamericana
echo "--- (SUD) Step 4 Finished. ---"
echo ""

echo "--- (LIB) Step 5: Running Altitude Processor ($PROCESSOR) ---"
python3 "$SCRIPT_DIR/$PROCESSOR" libertadores
echo "--- (LIB) Step 5 Finished. ---"
echo ""

echo "========================================================"
echo "=== WORKFLOW COMPLETO FINALIZADO ==="
echo "CSV de Sudamericana: data/processed/sudamericana_analysis.csv"
echo "CSV de Libertadores: data/processed/libertadores_analysis.csv"
echo "========================================================"
