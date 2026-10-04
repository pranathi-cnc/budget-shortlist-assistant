# Budget Purchase Shortlist Assistant

A simple purchase shortlist assistant built using Python, Ollama Gemma4, CSV, and Gradio.

## Tech Stack

* Python
* Ollama + Gemma4 (`gemma4:latest`)
* Gradio
* CSV

## How It Works

1. Python reads the product offers from CSV.
2. Python filters products by category, budget, and available quantity.
3. **Selector Agent** uses Gemma4 to select up to 3 products.
4. **Reviewer Agent** uses Gemma4 to validate the selected products.
5. Python performs final validation and saves the shortlist to CSV.
6. Gradio displays the final shortlist.

## Project Structure

```text
budget-shortlist-assistant/
├── data/
│   └── offers.csv
├── outputs/
│   └── shortlist.csv
├── src/
│   └── app.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

```powershell
pip install -r requirements.txt
```

`.env`:

```text
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:latest
```

## Run

```powershell
python src\app.py
```

Enter a category and budget in Gradio to generate the shortlist.

The final shortlist is displayed in Gradio and saved as:

```text
outputs/shortlist.csv
```

## Agent Workflow

```text
CSV
 ↓
Python Filter
 ↓
Selector Agent (Gemma4)
 ↓
Reviewer Agent (Gemma4)
 ↓
Final Validation
 ↓
Gradio + CSV
```

The agents are implemented as simple Gemma4 calls orchestrated directly in Python. LangGraph is not used.
