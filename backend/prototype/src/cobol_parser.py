import re
from typing import Dict, List

def parse_cobol(file_path: str) -> Dict:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read().upper()

    data = {
        'program_id': re.search(r'PROGRAM-ID\.\s*(\w+)', content),
        'data_items': re.findall(r'0[1-9]\s+\w+.*PIC\s+[\w()V]+', content),
        'paragraphs': re.findall(r'(\w+)-?\w*\.\s*(.*?)(?=\w+-?\w*\.|STOP RUN)', content, re.DOTALL)
    }
    
    # Extract potential class fields from DATA DIVISION
    fields = []
    for item in data['data_items']:
        match = re.search(r'(\w+)\s+PIC\s+(.+)', item)
        if match:
            fields.append({'name': match.group(1), 'pic': match.group(2)})
    
    # Paragraphs as potential methods
    methods = [p[0] for p in data['paragraphs'] if p[0] not in ['MAIN-LOGIC', 'STOP']]
    
    return {
        'program_name': data['program_id'].group(1) if data['program_id'] else 'UNKNOWN',
        'potential_attributes': fields,
        'potential_methods': methods,
        'raw_paragraphs': data['paragraphs']
    }