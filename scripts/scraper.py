import requests
from pyquery import PyQuery
import sys
import re
import json
import os


def fetch_html_tree(url: str) -> PyQuery | None:
    """Downloads and parses the HTML content from a given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5.37.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/5.37.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return PyQuery(response.content)
    except requests.exceptions.RequestException as e:
        print(f"  [Error] Failed to fetch {url}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [Error] Failed to parse HTML: {e}", file=sys.stderr)
        return None


def clean_score(score_text: str) -> tuple[str | None, str | None]:
    """Cleans score text (e.g., "1:1 (0:0)") and returns (home_goals, away_goals)."""
    if score_text is None:
        return None, None
    score_clean = re.sub(r"\(.*\)", "", score_text).strip()
    score_parts = score_clean.split(":", 1)

    cleaned_text = re.sub(
        r"\s*\.mw-parser-output.*?(\n|$)", "", score_text, flags=re.DOTALL
    )
    cleaned_text = re.sub(r"\(.*?\)", "", cleaned_text)
    cleaned_text = cleaned_text.strip()

    match = re.search(r"(\d+)\s*[:–-]\s*(\d+)", cleaned_text)
    if match:
        return match.group(1), match.group(2)
    return None, None


def clean_team_name(name: str) -> str:
    """Normalizes team names to match the mapping file."""
    name = name.strip()

    if name == "Bahia" or name == "Bahía":
        return "Bahia"
    if name == "Brasilia" or name == "Brasília":
        return "Brasilia"
    if name == "Athletico Paranaense" or name == "Paranaense":
        return "Atlético Paranaense"
    if name == "Táchira":
        return "Deportivo Táchira"
    if name == "Mineiro":
        return "Atlético Mineiro"
    if name == "Goianiense":
        return "Atlético Goianiense"
    if name == "Cali":
        return "Deportivo Cali"
    if name == "Capiatá":
        return "Deportivo Capiatá"
    if name == "Tucumán":
        return "Atlético Tucumán"
    if name == "Nacional" and "Atlético Nacional" in name:
        return "Atlético Nacional"
    if name == "Medellín":
        return "Independiente Medellín"
    if name == "Racing Club":
        return "Racing Club"
    if name == "Racing":
        return "Racing"
    if name == "Estudiantes":
        return "Estudiantes (LP)"
    if name == "Estudiantes (LP)":
        return "Estudiantes (LP)"

    return name.strip()


def parse_knockout_matches(doc: PyQuery, year: int) -> list[dict]:
    """
    Parses knockout matches using PyQuery.
    (Esta función ya funcionaba y se mantiene).
    """
    matches = []
    knockout_tables = doc("table.collapsible.vevent.plainlist").items()

    current_phase = "Fase Final"

    for table in knockout_tables:
        try:
            phase_heading = table.prev_all("h2, h3").eq(0)
            if phase_heading:
                span_text = phase_heading.find("span.mw-headline").text()
                if span_text:
                    current_phase = span_text.strip()

            cells = list(table.find("tr").eq(0).find("td").items())
            if len(cells) < 5:
                continue

            date = cells[0].text().strip()
            home_team = clean_team_name(cells[1].text().strip())
            score_raw = cells[2].text().strip()
            away_team = clean_team_name(cells[3].text().strip())
            stadium = cells[4].text().strip().split(",")[0]
            home_goals, away_goals = clean_score(score_raw)

            matches.append(
                {
                    "year": year,
                    "phase": current_phase,
                    "date": date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "score": score_raw,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "stadium": stadium,
                }
            )
        except (AttributeError, IndexError, TypeError) as e:
            print(f"    [Warning] Skipping a knockout match/table. Error: {e}")
            continue
    return matches


def parse_group_stage_matches(doc: PyQuery, year: int) -> list[dict]:
    """
    Robust parser for group stage matches (Libertadores / Sudamericana, 2014-2024).
    Tries multiple heuristics:
        - find "Grupo X" headers and search siblings/descendants for tables
        - find "Partidos" subtitles then pull the nested table
        - fallback: search all tables with a score pattern and try to infer group
    Returns list of dicts with keys:
        year, phase, date, home_team, away_team, score, home_goals, away_goals, stadium
    """
    matches: list[dict] = []
    score_re = re.compile(r"\d+\s*[:–-]\s*\d+")

    def table_has_score(table_el: PyQuery) -> bool:
        txt = table_el.text() or ""
        return bool(score_re.search(txt))

    def tx(el: PyQuery) -> str:
        return re.sub(r"\s+", " ", (el.text() or "").strip())

    header_selectors = "h2 span.mw-headline, h3 span.mw-headline, h4 span.mw-headline"
    group_headers = []
    for span in doc(header_selectors).items():
        text = tx(span)
        if re.search(r"\bGrupo\b", text, re.IGNORECASE):
            group_headers.append(span)

    for span in group_headers:
        group_name = tx(span)
        h_parent = span.parent()
        found_table = None

        sib = h_parent.next()
        steps = 0
        while sib is not None and sib.length > 0 and steps < 12:
            if sib.is_("table"):
                if table_has_score(sib):
                    found_table = sib
                    break
            if (
                sib.is_("div.wikitable-wrapper")
                or "wikitable-wrapper" in sib.attr("class")
                or sib.is_("div.mw-parser-output")
            ):
                inner = sib.find("table").eq(0)
                if inner.length > 0 and table_has_score(inner):
                    found_table = inner
                    break
            if (
                sib.is_("table.collapsible")
                or sib.is_("table.mw-collapsible")
                or "collapsible" in (sib.attr("class") or "")
            ):
                inner = (
                    sib.find("table")
                    .filter(lambda i, el: score_re.search(PyQuery(el).text() or ""))
                    .eq(0)
                )
                if inner.length > 0:
                    found_table = inner
                    break
            descendant_tables = sib.find("table")
            for t in descendant_tables.items():
                if table_has_score(t):
                    found_table = t
                    break
            if found_table:
                break

            sib = sib.next()
            steps += 1

        if not found_table:
            all_desc_tables = h_parent.find("table")
            for t in all_desc_tables.items():
                if table_has_score(t):
                    found_table = t
                    break

        if not found_table:
            sib = h_parent.next()
            steps = 0
            while sib is not None and sib.length > 0 and steps < 12:
                if "Partidos" in (tx(sib) or ""):
                    inner = sib.find("table").eq(0)
                    if inner.length > 0 and table_has_score(inner):
                        found_table = inner
                        break
                    next_after = sib.next()
                    if next_after and next_after.length > 0:
                        inner2 = next_after.find("table").eq(0)
                        if inner2 and table_has_score(inner2):
                            found_table = inner2
                            break
                sib = sib.next()
                steps += 1

        if not found_table:
            continue

        for row in found_table.find("tr").items():
            header_ths = list(row.find("th").items())
            if header_ths and any(
                "fecha" in (tx(th).lower()) or "local" in (tx(th).lower())
                for th in header_ths
            ):
                continue

            cols = list(row.find("td").items())
            if len(cols) < 4:
                continue

            date = None
            stadium = None
            home_team = ""
            away_team = ""
            score_raw = ""

            if len(cols) >= 5:
                date = tx(cols[0])
                stadium = tx(cols[1]) or None
                home_team = tx(cols[2])
                score_raw = tx(cols[3])
                away_team = tx(cols[4])
            elif len(cols) == 4:
                date = tx(cols[0])
                second_text = tx(cols[1])
                third_text = tx(cols[2])
                fourth_text = tx(cols[3])

                if score_re.search(third_text):
                    home_team = second_text
                    score_raw = third_text
                    away_team = fourth_text
                    stadium = None
                elif score_re.search(second_text):
                    score_raw = second_text
                    home_team = third_text
                    away_team = fourth_text
                    stadium = None
                else:
                    home_team = second_text
                    score_raw = third_text
                    away_team = fourth_text
                    stadium = None
            else:
                texts = [tx(c) for c in cols]
                score_idx = None
                for i, t in enumerate(texts):
                    if score_re.search(t):
                        score_idx = i
                        break
                if score_idx is None or score_idx == 0 or score_idx >= len(texts) - 1:
                    continue
                score_raw = texts[score_idx]
                home_team = texts[score_idx - 1]
                away_team = texts[score_idx + 1]
                date = texts[0] if len(texts) > 0 else None
                stadium = None

            if not score_raw or not score_re.search(score_raw):
                continue

            home_team = clean_team_name(home_team)
            away_team = clean_team_name(away_team)

            hg, ag = clean_score(score_raw)
            if hg is None or ag is None:
                m = score_re.search(score_raw)
                if m:
                    maybe = m.group(0)
                    hg, ag = clean_score(maybe)
                if hg is None or ag is None:
                    continue

            if not home_team or not away_team:
                continue

            match = {
                "year": year,
                "phase": group_name,
                "date": date,
                "home_team": home_team,
                "away_team": away_team,
                "score": score_raw,
                "home_goals": hg,
                "away_goals": ag,
                "stadium": stadium,
            }
            matches.append(match)

    if not matches:
        for t in doc("table").items():
            if not table_has_score(t):
                continue
            for row in t.find("tr").items():
                cols = list(row.find("td").items())
                if len(cols) < 4:
                    continue
                try:
                    if len(cols) >= 5:
                        date = tx(cols[0])
                        stadium = tx(cols[1]) or None
                        home_team = clean_team_name(tx(cols[2]))
                        score_raw = tx(cols[3])
                        away_team = clean_team_name(tx(cols[4]))
                    else:
                        date = tx(cols[0])
                        home_team = clean_team_name(tx(cols[1]))
                        score_raw = tx(cols[2])
                        away_team = clean_team_name(tx(cols[3]))
                    hg, ag = clean_score(score_raw)
                    if hg is None or ag is None:
                        continue
                    matches.append(
                        {
                            "year": year,
                            "phase": "Fase de Grupos",
                            "date": date,
                            "home_team": home_team,
                            "away_team": away_team,
                            "score": score_raw,
                            "home_goals": hg,
                            "away_goals": ag,
                            "stadium": stadium if "stadium" in locals() else None,
                        }
                    )
                except Exception:
                    continue

    return matches


def run_scraper(tournament_name: str, base_url: str, output_file: str):
    """
    Main function to scrape all years for a given tournament.
    """
    YEARS = range(2024, 2013, -1)
    all_matches = []

    for year in YEARS:
        url = f"{base_url}{year}"
        print(f"--- Scraping {url} ---")

        doc = fetch_html_tree(url)
        if doc is None:
            continue

        group_matches = parse_group_stage_matches(doc, year)
        knockout_matches = parse_knockout_matches(doc, year)

        print(f"  Found {len(group_matches)} group stage matches.")
        print(f"  Found {len(knockout_matches)} knockout matches.")

        all_matches.extend(group_matches)
        all_matches.extend(knockout_matches)

    if not all_matches:
        print(f"\nNo matches were scraped for {tournament_name}. Exiting.")
        open(os.path.join("data", "raw", output_file), "w").close()
        return

    DATA_DIR = "data/raw"
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory {DATA_DIR}: {e}", file=sys.stderr)
        return

    output_path = os.path.join(DATA_DIR, output_file)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_matches, f, ensure_ascii=False, indent=2)

        print(f"\n--- Scraping Finished ({tournament_name}) ---")
        print(f"Total matches found: {len(all_matches)}")
        print(f"Raw data saved to {output_path}")
    except IOError as e:
        print(f"Error writing JSON to {output_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing tournament name argument.", file=sys.stderr)
        print("Usage: python3 scrape.py [sudamericana|libertadores]", file=sys.stderr)
        sys.exit(1)

    tournament_name = sys.argv[1].lower()

    if tournament_name == "sudamericana":
        BASE_URL = "https://es.wikipedia.org/wiki/Copa_Sudamericana_"
        OUTPUT_FILE = "sudamericana_matches.json"
    elif tournament_name == "libertadores":
        BASE_URL = "https://es.wikipedia.org/wiki/Copa_Libertadores_"
        OUTPUT_FILE = "libertadores_matches.json"
    else:
        print(f"Error: Unknown tournament '{tournament_name}'.", file=sys.stderr)
        print("Usage: python3 scrape.py [sudamericana|libertadores]", file=sys.stderr)
        sys.exit(1)

    run_scraper(tournament_name, BASE_URL, OUTPUT_FILE)
