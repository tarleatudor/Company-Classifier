""" "
Script pentru clasificarea companiilor conform taxonomiei.
"""

# Importuri

import os
import ast
import pandas as pd
from typing import List, Tuple

# Fisiere

# Input
COMPANIES_PATH = "data_in/ml_insurance_challenge.csv"
TAXONOMY_PATH = "data_in/insurance_taxonomy.xlsx"

# Output
OUTPUT_DIR = "data_out"

# Parametrii Globali

# Dimensiunea chunk-ului pentru citirea CSV-ului
# (desi dataset-ul curent este mic, acest parametru este util pentru seturi de date mai mari
CHUNK_SIZE = 1000

# Prag minim de incredere pentru a accepta un label
MIN_EVIDENCE_SCORE = 3

# Dupa prima rulare am observat ca modelul returneaza prea multe labeluri pentru fiecare
# companie din cauza stop-wordsurilor asa ca am decis sa le eliminam din matching. (se pot adauga mai multe pentru imbunatatiri viitoare)
STOP_WORDS = {
    "and",
    "or",
    "the",
    "of",
    "for",
    "with",
    "services",
    "service",
    "installation",
    "install",
    "production",
    "manufacturing",
    "management",
    "operations",
    "solutions",
    "systems",
    "e",
}

# Functii


def normalize_text(value) -> str:
    """
    Normalizeaza orice text prin:
    -tratarea NaN/None
    -convertirea la string
    -lower-case
    -strip spatii
    """
    if pd.isna(value):
        return ""
    return str(value).lower().strip()


def parse_business_tags(value) -> List[str]:
    """
    Parseaza campul business_tags, care este stocat ca string reprezentand o lista.
    Daca valoare este lipsa sau invalida, returneaza o lista vida.
    """

    if pd.isna(value):
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [normalize_text(tag) for tag in parsed]
    except:
        return []
    return []


def load_taxonomy(path: str) -> List[str]:
    """
    Incarca taxonomia din excel.
    Presupuneri:
    - o singura coloana
    - fiecare rand este un label valid

    Returneaza lista de label-uri
    """

    df = pd.read_excel(path)

    # Luam prima coloana
    labels = df.iloc[:, 0].dropna().astype(str).tolist()
    return labels


# Pregatire Taxonomie pentru Matching


def normalize_label(label: str) -> str:
    """
    Normalizeaza un label din taxonomie pentru matching.
    Ex: Tree Services - Pruning / Removal -> tree services pruning removal
    """

    label = label.lower()
    for ch in ["-", "/", ",", "&"]:
        label = label.replace(ch, " ")
    return label.strip()


def build_label_index(labels: List[str]) -> dict:
    """
    Construieste un index simplu pentru label-uri
    {
        label_original:{
            'normalized': text_normalizat,
            'keywords': set([])
        }
    }
    keywords-urile sunt extrase direct din label
    """
    label_index = {}

    for label in labels:
        normalized = normalize_label(label)
        keywords = {
            kw for kw in normalized.split() if kw not in STOP_WORDS and len(kw) > 4 # initial mai mare ca 2, trebuie mai strict
        }

        label_index[label] = {"normalized": normalized, "keywords": keywords}
    return label_index


# Clasificare Companii


def compute_evidence_for_label(
    label: str, label_data: dict, row: pd.Series
) -> Tuple[int, List[str]]:
    """
    Calculeaza scorul de evidenta pentru un singur label,
    folosinf campurile din randul dat.
    Returneaza
    -scor total
    - lista de explicatii
    """
    score = 0
    reasons = []

    # Normalizam toate campuriel relevante
    description = normalize_text(row.get("description"))
    category = normalize_text(row.get("category"))
    niche = normalize_text(row.get("niche"))
    business_tags = parse_business_tags(row.get("business_tags"))
    label_keywords = label_data["keywords"]

    # 1.Business Tags (importanta crescuta)

    for tag in business_tags:
        for kw in label_keywords:
            #initial verificam si bucati de cuvinte, dar am observat ca ducea la prea multe false-positives
            if kw in tag.split():
                score += 2
                reasons.append(f"Matched '{kw}' in business tag")
                break

    # 2. Category/Niche (importanta medie)

    for kw in label_keywords:
        #initial verificam si bucati de cuvinte, dar am observat ca ducea la prea multe false-positives
        if kw in category.split() or kw in niche.split():
            score += 1
            reasons.append(f"Matched '{kw}' in category/niche")

    # 3. Description (importanta redusa)
    for kw in label_keywords:
        #initial verificam si bucati de cuvinte, dar am observat ca ducea la prea multe false-positives
        if kw in description.split():
            score += 1
            reasons.append(f"Matched '{kw}' in description")

    return score, reasons


def classify_company(row: pd.Series, label_index: dict) -> Tuple[str, str, str]:
    """
    Clasifica o singura companie pe baza "dovezilor"

    Returneaza :
    -insurance_label
    -insurance_reason
    -insurance_confidence
    """

    matched_labels = []
    matched_reasons = []
    max_score = 0

    for label, label_data in label_index.items():
        score, reasons = compute_evidence_for_label(label, label_data, row)
        if score >= MIN_EVIDENCE_SCORE:
            matched_labels.append(label)
            matched_reasons.extend(reasons)
            max_score = max(max_score, score)

    if not matched_labels:
        return ("Unclear", "No sufficient evidence found for any taxonomy label", "low")

    # Determinam nivelul de incredere (pentru exigenta se pot modifica valorile : 6, 4, etc)
    if max_score >= 6:
        confidence = "high"
    elif max_score >= 4:
        confidence = "medium"
    else:
        confidence = "low"
    
    #Dupa prima rulare am observat ca unele companii primesc prea multe labeluri,
    # asa ca am decis sa limitam la maxim 3 labeluri per companie, pentru claritate 
    MAX_LABELS = 3
    matched_labels = matched_labels[:MAX_LABELS]
    
    # Eliminam duplicatele din motive, adaugat pentru claritate
    matched_reasons = list(dict.fromkeys(matched_reasons)) 

    return (";".join(matched_labels), ";".join(matched_reasons), confidence)


# Procesare CSV in chunk-uri


def process_companies_file():
    """
    Proceseaza fisierul de companii in chunk-uri si
    genereaza 2 fisiere de output
    1. output-ul cerut, identic cu lista de firme + coloana noua (insurance_label)
    2. output cu reasoning (insurance_label+ reasoning + confidence)
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    OFFICIAL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "classified_companies.csv")
    REASONING_OUTPUT_PATH = os.path.join(
        OUTPUT_DIR, "classified_companies_reasoning.csv"
    )
    
    #Daca se rula si exista fisierul se suprascriau headerele, asa se verifica existenta fisierelor vechi si sunt sterse
    for path in [OFFICIAL_OUTPUT_PATH, REASONING_OUTPUT_PATH]:
        if os.path.exists(path):
            os.remove(path)

    print("Incarcare taxonomie...")
    taxonomy_labels = load_taxonomy(TAXONOMY_PATH)

    print("Construire index de label-uri...")
    label_index = build_label_index(taxonomy_labels)

    print("Pornire procesare companii...")
    first_chunk = True
    chunk_number = 0

    for chunk in pd.read_csv(COMPANIES_PATH, chunksize=CHUNK_SIZE):
        chunk_number += 1
        print(f" Procesare chunk {chunk_number}...")
        results = chunk.apply(
            lambda row: classify_company(row, label_index), axis=1, result_type="expand"
        )

        results.columns = [
            "insurance_label",
            "insurance_reason",
            "insurance_confidence",
        ]
        # Output oficial (strict cerinta challenge)
        official_output = chunk.copy()
        official_output["insurance_label"] = results["insurance_label"]

        official_output.to_csv(
            OFFICIAL_OUTPUT_PATH,
            mode="w" if first_chunk else "a",
            index=False,
            header=first_chunk,
        )

        # Output reasoning (pentru analiza mai detaliata)
        reasoning_output = pd.concat([chunk, results], axis=1)

        reasoning_output.to_csv(
            REASONING_OUTPUT_PATH,
            mode="w" if first_chunk else "a",
            index=False,
            header=first_chunk,
        )

        first_chunk = False

    print("Procesare finalizata")
    print(f" Output oficial: {OFFICIAL_OUTPUT_PATH}")
    print(f" Output reasoning: {REASONING_OUTPUT_PATH}")


# Main

if __name__ == "__main__":
    process_companies_file()
