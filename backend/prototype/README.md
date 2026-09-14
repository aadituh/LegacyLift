# ML-Driven Legacy Code Modernization (Mockup)

## Files
- `src/cobol_parser.py`: Preprocessing & feature extraction from COBOL.
- `src/models.py`: Embeddings + KMeans clustering (unsupervised pattern detection).
- `src/refactorer.py`: Rule-based baseline + ML-augmented OOP skeleton generation.
- `notebooks/`: Exploration, pattern detection, and full demo.

## How to Run
1. `pip install -r requirements.txt`
2. `jupyter notebook`
3. Open `notebooks/03_refactoring_demo.ipynb`

## Mock ML Pipeline
1. Parse COBOL (DATA/PROCEDURE divisions).
2. Embed paragraphs → Cluster into conceptual classes (unsupervised).
3. Generate Python OOP (attributes from data items, methods from clustered procedures).
4. Compare with manual reference OOP version.

Limitations (for report): Small synthetic data, heuristic parsing, template-based generation. Real version would fine-tune CodeT5 or use GNNs on program graphs.

This demonstrates the full proposed pipeline in a runnable, visual form suitable for the course project.