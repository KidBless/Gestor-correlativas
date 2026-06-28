import re
import subprocess
import os
import tempfile
from typing import List, Dict, Tuple


# ──────────────────────────────────────────────
#  PDF extraction
# ──────────────────────────────────────────────

def extract_text_from_pdf(filepath: str) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", filepath, "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    from pdfminer.high_level import extract_text
    return extract_text(filepath)


def normalize_text(text: str) -> str:
    text = text.replace("\t", " ")
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r\n?", "\n", text)
    return text


def parse_pdf(filepath: str) -> Tuple[List[Dict], str]:
    raw_text = extract_text_from_pdf(filepath)
    subjects = parse_study_plan(raw_text)
    return subjects, raw_text


# ──────────────────────────────────────────────
#  UNAM / FCEQyN table format parser
# ──────────────────────────────────────────────

YEAR_WORDS = {"primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5}

_ROMAN_RE = re.compile(r"[IVXLCDM]+")
_REGIMEN_RE = re.compile(r"(Anual|Cuatrimestral|---)", re.IGNORECASE)
_SEMESTER_RE = re.compile(r"\(\s*(\d+)\s*[°º]\s*C\s*\)")


_TABLE_HEADER_KEYWORDS = [
    "cod", "asignatura", "carga", "horaria", "correlativ",
    "modalidad", "dictado", "régimen", "regimen",
    "semanal", "total", "codigo", "código",
    "denominacion", "denominación", "condición", "condicion",
    "obligatoria", "optativa", "electiva",
]
_FACULTY_STOP_KEYWORDS = [  # subset for detect_faculty_name
    "cod", "asignatura", "carga", "horaria", "correlativ",
    "modalidad", "dictado", "semanal", "total",
    "codigo", "código",
]

def _is_table_header(line: str) -> bool:
    lower = re.sub(r"\s+", " ", line.strip().lower())
    if not lower:
        return True
    for kw in _TABLE_HEADER_KEYWORDS:
        if kw in lower:
            return True
    return False


def looks_like_faculty_table(text: str) -> bool:
    lines = text.split("\n")
    found_year = False
    found_row = False
    for line in lines:
        lower = line.strip().lower()
        if lower in YEAR_WORDS:
            found_year = True
        if re.search(r"^\s*[IVXLCDM]+\s+(?:Anual|Cuatrimestral)", line):
            found_row = True
    return found_year and found_row


def _extract_roman_codes(text: str) -> List[str]:
    return _ROMAN_RE.findall(text)


def _clean_name(name: str) -> str:
    name = _SEMESTER_RE.sub("", name)
    name = re.sub(r"\s*\(", " (", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def _guess_semester(name: str) -> int:
    m = _SEMESTER_RE.search(name)
    return int(m.group(1)) if m else 1


def _is_continuation_line(line: str) -> bool:
    """Determine if a line between data rows is a continuation (vs pre-text)."""
    s = line.strip()
    if not s:
        return True
    if s.startswith("("):
        return True
    if _SEMESTER_RE.search(s):
        return True
    if len(s) <= 12:
        return True
    return False


def _normalize_faculty_text(text: str) -> str:
    """Normalize text preserving column spacing (unlike normalize_text)."""
    text = text.replace("\t", " ")
    text = text.replace("\x0c", "\n")
    text = re.sub(r"\r\n?", "\n", text)
    return text


def parse_faculty_table(text: str) -> List[Dict]:
    lines = _normalize_faculty_text(text).split("\n")

    # ── Pass 1: find year sections and data rows ──
    data_rows = []  # (year, code, name_fragment, data_after, line_index)
    current_year = 0
    year_header_idx = {}  # year_value → first line index of that year section

    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        if lower in YEAR_WORDS:
            current_year = YEAR_WORDS[lower]
            if current_year not in year_header_idx:
                year_header_idx[current_year] = i
            continue

        if not stripped or _is_table_header(stripped) or current_year == 0:
            continue

        rm = re.match(r"^\s*([IVXLCDM]+)\s", line)
        if not rm:
            continue

        rest = line[rm.end():]
        regimen_m = _REGIMEN_RE.search(rest)
        if not regimen_m:
            continue

        code = rm.group(1)
        regimen = regimen_m.group(1)
        name_on_row = rest[:regimen_m.start()].strip()
        data_after = rest[regimen_m.end():].strip()
        data_rows.append((current_year, code, name_on_row, data_after, i, regimen))

    if not data_rows:
        return []

    # ── Pass 2: assign inter-row lines to subjects ──
    subjects_by_code = {}
    subject_order = []

    for idx, (year, code, name_on_row, data_after, line_idx, regimen) in enumerate(data_rows):
        year_start = year_header_idx.get(year, 0)

        if idx > 0:
            prev_row_end = data_rows[idx - 1][4] + 1
        else:
            prev_row_end = year_start + 1

        inter_lines = lines[prev_row_end:line_idx]

        pre_text_parts = []
        for l in inter_lines:
            s = l.strip()
            if not s or _is_table_header(s):
                continue
            if not _is_continuation_line(l):
                pre_text_parts.append(s)

        full_name = " ".join(pre_text_parts + [name_on_row]).strip()

        clean = _clean_name(full_name)

        # Parse prereq codes from data_after
        prereq_codes = []
        for part in re.split(r"\s{2,}", data_after):
            part = part.strip()
            if not part or re.match(r"^\d+$", part):
                continue
            if part.lower() == "presencial" or part.lower().startswith("presencial"):
                continue
            if re.match(r"^[\w\sáéíóúñüÁÉÍÓÚÑÜ]+$", part) and not re.search(r"[IVXLCDM]", part):
                continue
            prereq_codes.extend(_extract_roman_codes(part))

        if clean and len(clean) >= 3:
            subjects_by_code[code] = {
                "name": clean,         # cleaned name (will be updated with continuations)
                "raw_name": full_name, # raw name WITH semester markers (for extraction)
                "year": year,
                "semester": 1,         # will be fixed after continuations
                "prerequisite_codes": prereq_codes,
                "code": code,
                "regimen": regimen,
            }
            subject_order.append(code)

        # Lines after this data row until the next one → continuation for this subject
        next_start = data_rows[idx + 1][4] if idx + 1 < len(data_rows) else len(lines)
        for l in lines[line_idx + 1:next_start]:
            s = l.strip()
            if not s or _is_table_header(s):
                continue
            if s.lower() in YEAR_WORDS:
                continue
            if not _is_continuation_line(l):
                continue
            codes = _extract_roman_codes(s)
            cleaned = re.sub(r"[IVXLCDM\s\-]+", "", s)
            if codes and not cleaned.strip():
                if code in subjects_by_code:
                    subjects_by_code[code]["prerequisite_codes"].extend(codes)
            elif not _is_table_header(s):
                if code in subjects_by_code:
                    subjects_by_code[code]["name"] += " " + s
                    subjects_by_code[code]["raw_name"] += " " + s

        # Finalize: determine semester from regimen + raw_name, clean final name
        if code in subjects_by_code:
            raw = re.sub(r"\s+", " ", subjects_by_code[code]["raw_name"]).strip()
            clean_name = _clean_name(raw)
            subj_regimen = subjects_by_code[code].get("regimen", "").lower()

            if subj_regimen in ("anual", "---"):
                subjects_by_code[code]["semester"] = 1
            else:
                sem = _guess_semester(raw)
                subjects_by_code[code]["semester"] = sem if sem in (1, 2) else 1

            subjects_by_code[code]["name"] = clean_name
            subjects_by_code[code].pop("raw_name", None)
            subjects_by_code[code].pop("regimen", None)

    # ── Pass 3: build code→name mapping and resolve prereqs ──
    code_to_name = {}
    for code, s in subjects_by_code.items():
        n = re.sub(r"\s+", " ", s["name"]).strip()
        if n:
            code_to_name[code] = n

    seen = set()
    result = []

    for code in subject_order:
        s = subjects_by_code[code]
        name = re.sub(r"\s+", " ", s["name"]).strip()
        if not name or len(name) < 3:
            continue

        key = name.lower()
        if key in seen:
            name = f"{name} ({s['year']}° Año)"
            key = name.lower()
        seen.add(key)

        resolved = []
        for pc in s["prerequisite_codes"]:
            pc = pc.strip().rstrip("-")
            if pc in code_to_name:
                resolved.append(code_to_name[pc])

        result.append({
            "name": name,
            "year": s["year"],
            "semester": s["semester"],
            "prerequisites": resolved,
        })

    return result


# ──────────────────────────────────────────────
#  Legacy heuristic parser (unchanged)
# ──────────────────────────────────────────────

def detect_year_semester(line: str) -> Tuple[int, int, bool]:
    lower = line.lower().strip()

    patterns = [
        r"(\d+)(?:°|er|ro|do|ra|da|\.)?\s*(?:año|ano)\s*[–\-—/\s]+\s*(\d+)(?:°|do|da|\.)?\s*(?:semestre|sem|s|cuatrimestre|cuatr)",
        r"(\d+)(?:°|er|ro|do|ra|da|\.)?\s*(?:año|ano).*?(\d+)(?:°|do|da|\.)?\s*(?:semestre|sem|s)",
        r"(?:año|ano|year|nivel)\s*[.:]?\s*(\d+)(?:°|er|ro|do|ra|da|\.)?(?:\s*[–\-—/\s]+\s*)(?:semestre|sem|s|cuatrimestre|cuatr)\s*[.:]?\s*(\d+)(?:°|do|da|\.)?",
        r"(?:año|ano|year|nivel)\s*(\d+).*?(?:semestre|sem|s|cuatrimestre|cuatr)\.?\s*(\d+)",
        r"(?:año|ano)\s*(\d+)\s*[/]\s*(?:semestre|sem|s)\s*(\d+)",
        r"(?:primero?|primer|1er?)\s*(?:año|ano).*?(?:segundo?|segund|2do?|2°)\s*(?:semestre|sem)",
        r"(?:primero?|primer|1er?)\s*(?:semestre|sem).*?(?:segundo?|segund|2do?|2°)\s*(?:año|ano)",
    ]

    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            try:
                g1 = m.group(1)
                g2 = m.group(2)
                year_map = {"primero": 1, "primer": 1, "segundo": 2, "tercero": 3, "tercer": 3, "cuarto": 4, "quinto": 5}
                if g1.lower() in year_map:
                    y = year_map[g1.lower()]
                else:
                    y = int(g1)
                if g2.lower() in year_map:
                    s = year_map[g2.lower()]
                else:
                    s = int(g2)
                return y, s, True
            except (ValueError, IndexError):
                pass

    year_pats = [
        r"(?:año|ano|a|year|nivel)\s*[.:]?\s*(\d+)(?:°|er|ro|do|ra|da|\.|\.º)?\s*$",
        r"(?:primero?|primer|1er?|1°)\s*(?:año|ano)",
        r"(?:segundo?|2do?|2°)\s*(?:año|ano)",
        r"(?:tercero?|3er?|3°)\s*(?:año|ano)",
        r"(?:cuarto|4to?|4°)\s*(?:año|ano)",
        r"(?:quinto|5to?|5°)\s*(?:año|ano)",
        r"^(\d+)(?:°|er|ro|do|ra|da|\.)?\s*(?:año|ano|a)(?:\s|$)",
    ]
    for pat in year_pats:
        m = re.search(pat, lower)
        if m:
            try:
                if "primero" in lower or "primer" in lower:
                    return 1, 0, True
                elif "segundo" in lower:
                    return 2, 0, True
                elif "tercero" in lower or "tercer" in lower:
                    return 3, 0, True
                elif "cuarto" in lower:
                    return 4, 0, True
                elif "quinto" in lower:
                    return 5, 0, True
                nums = re.findall(r"\d+", m.group() if m.group(1) else lower)
                if nums:
                    return int(nums[0]), 0, True
            except (ValueError, IndexError):
                pass

    sem_pats = [
        r"(?:semestre|sem|s|cuatrimestre|cuatr)\s*[.:]?\s*(\d+)(?:°|do|da|\.)?\s*$",
        r"^(\d+)(?:°|do|da|\.)?\s*(?:semestre|sem|s)\s*$",
    ]
    for pat in sem_pats:
        m = re.search(pat, lower)
        if m:
            try:
                return 0, int(m.group(1)), True
            except (ValueError, IndexError):
                pass

    return 0, 0, False


def is_likely_subject_name(text: str) -> bool:
    if len(text) < 4 or len(text) > 120:
        return False
    if not re.search(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}", text):
        return False
    if re.match(r"^[\d\s.,;:()/\-–—]+$", text):
        return False
    return True


def is_header(text: str) -> bool:
    lower = text.lower().strip()
    headers = {
        "plan", "materia", "materias", "código", "codigo", "cod",
        "carrera", "carreras", "total", "horas", "correlat",
        "obligatoria", "obligatorias", "optativa", "optativas",
        "electiva", "electivas", "título", "titulo", "perfil",
        "objetivo", "objetivos", "fundamentación", "fundamentacion",
        "contenido", "contenidos", "modalidad", "evaluación",
        "evaluacion", "condición", "condicion", "régimen",
        "regimen", "aprobación", "aprobacion", "vigencia",
        "resolución", "resolucion", "anexo", "disp", "cátedra",
        "catedra", "departamento", "plan de estudios",
        "plan de estudio", "ciclo", "trayecto", "nivel",
        "asignatura", "asignaturas", "denominación", "denominacion",
        "carga horaria", "hs.", "hs", "semanal", "total hs",
        "correlativas", "correlatividades", "régimen de correlatividad",
        "régimen de correlatividades",
    }
    for h in headers:
        if lower.startswith(h):
            return True
        if lower == h:
            return True
    return False


POSSIBLE_PREPOSITIONS = {"de", "del", "la", "las", "los", "y", "e", "a", "el", "en", "con", "por", "para", "su", "que",
                         "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def extract_prerequisites(line: str) -> Tuple[str, List[str]]:
    cleaned = re.sub(r"^\d+(?:[\.\-/]\d+)*(?:\s*[‑–—\-]\s*|\s+)", "", line).strip()
    cleaned = re.sub(r"^(?:código|cod|code)\s*:?\s*\w+\s*[‑–—\-]\s*", "", cleaned, flags=re.IGNORECASE).strip()

    prereqs = []
    seen_prereqs = set()

    corr_main = re.search(
        r"(?:correlativa[s]?\s*(?:para|de|con|:)?|para cursar|requisito[s]?\s*(?:académicos?|:)?)\s*:?\s*(.+?)$",
        cleaned,
        re.IGNORECASE,
    )
    if corr_main:
        raw = corr_main.group(1)
        raw = re.sub(r"[()\]\[]+", "", raw).strip()
        parts = re.split(r"[,;/\-–—\+y]+", raw)
        for p in parts:
            p = p.strip().strip(".- ")
            p = re.sub(r"\s*\([^)]*\)\s*$", "", p).strip()
            if p and len(p) > 3 and p.lower() not in seen_prereqs:
                seen_prereqs.add(p.lower())
                prereqs.append(p)

    name = re.sub(r"\([^)]*\)", " ", cleaned)
    name = re.sub(r"\s*\(?\s*correlativa[s]?.*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*para cursar.*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*requisito[s]?.*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\d[\d\s\-–—]*\)", "", name)
    name = re.sub(r"\s+\d+\s*(?:hs?|horas?|créditos?|creditos?)\s*$", "", name, flags=re.IGNORECASE)

    name = name.strip()
    name = re.sub(r"\s+", " ", name)

    return name, prereqs


def detect_faculty_name(text: str) -> str:
    """Extract the university/faculty name from plan text header."""
    lines = text.split("\n")
    header_lines = []
    for i, line in enumerate(lines):
        s = line.strip()
        lower = s.lower()
        if not s:
            continue
        if lower in YEAR_WORDS:
            break
        if re.match(r"^\s*[IVXLCDM]+\s", line) and re.search(r"(?:Anual|Cuatrimestral|---)", line):
            break
        lower_check = re.sub(r"\s+", " ", lower)
        if any(kw in lower_check for kw in _FACULTY_STOP_KEYWORDS):
            break
        if i > 20:
            break
        header_lines.append(s)

    if not header_lines:
        return ""

    header = " ".join(header_lines)

    # Split at TÍTULO: to only get the institution part
    for splitter in ["TÍTULO:", "TITULO:", "TITULO"]:
        if splitter in header.upper():
            header = header.upper().split(splitter)[0].strip()
            break

    # Look for university/faculty
    m = re.search(
        r"((?:UNIVERSIDAD|FACULTAD|INSTITUTO|ESCUELA)[A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9\s,.:;/-]{3,120})",
        header, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().rstrip(",").strip()

    if "universidad" in header.lower() or "facultad" in header.lower():
        return header.strip().rstrip(",").strip()[:100]

    return ""


def parse_study_plan(text: str) -> List[Dict]:
    # Auto-detect faculty table format (needs column spacing preserved)
    if looks_like_faculty_table(text):
        result = parse_faculty_table(text)
        if result:
            return result

    text = normalize_text(text)

    # Fallback to legacy parser
    lines = []
    for l in text.split("\n"):
        l = l.strip()
        if l:
            lines.append(l)

    current_year = 0
    current_semester = 0
    subjects: List[Dict] = []
    seen_names: set = set()

    for line in lines:
        lower = line.lower().strip()

        y, s, matched = detect_year_semester(lower)
        if matched:
            if y > 0:
                current_year = y
            if s > 0:
                current_semester = s
            if current_year > 0 and current_semester == 0:
                current_semester = 1
            continue

        if not is_likely_subject_name(lower):
            continue
        if is_header(lower):
            continue

        name, prereqs = extract_prerequisites(line)

        if not name or len(name) < 3:
            continue
        if name.lower() in seen_names:
            continue
        if current_year == 0:
            continue

        name = _capitalize_name(name)
        seen_names.add(name.lower())

        subjects.append({
            "name": name,
            "year": current_year,
            "semester": current_semester or 1,
            "prerequisites": prereqs,
        })

    subject_names_lower = {s["name"].lower(): s["name"] for s in subjects}

    for s in subjects:
        resolved = []
        for pr in s["prerequisites"]:
            pr_lower = pr.lower().strip()
            if pr_lower in subject_names_lower:
                resolved.append(subject_names_lower[pr_lower])
            else:
                for sn_lower, sn in subject_names_lower.items():
                    if len(pr_lower) >= 5 and (pr_lower in sn_lower or sn_lower in pr_lower):
                        resolved.append(sn)
                        break
                else:
                    resolved.append(pr)
        s["prerequisites"] = resolved

    return subjects


def _capitalize_name(name: str) -> str:
    lowercase_words = {"de", "del", "la", "las", "los", "y", "e", "a", "el",
                       "en", "con", "por", "para", "su", "que", "i", "ii",
                       "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
    parts = name.split()
    result = []
    for i, p in enumerate(parts):
        if i == 0 or p.upper() != p:
            if p.lower() in lowercase_words and i > 0:
                result.append(p.lower())
            else:
                result.append(p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper())
        else:
            result.append(p)
    return " ".join(result)
