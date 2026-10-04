
import csv
import json
import os
from pathlib import Path

import gradio as gr
import ollama
from dotenv import load_dotenv


# ==================================================
# CONFIGURATION
# ==================================================

load_dotenv()

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma4:latest"
)

client = ollama.Client(
    host=OLLAMA_URL
)

BASE_DIR = Path(__file__).resolve().parent.parent

OFFERS_FILE = BASE_DIR / "data" / "offers.csv"

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ==================================================
# 1. PYTHON TOOL - FILTER OFFERS
# ==================================================

def filter_offers(category, budget):

    matches = []

    with open(
        OFFERS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row_number, row in enumerate(
            reader,
            start=2
        ):

            try:
                price = float(row["price"])
                quantity = int(row["quantity"])

            except (ValueError, TypeError):

                print(
                    f"Skipping malformed row: {row_number}"
                )

                continue

            # Python checks all numeric/business rules
            if (
                row["category"].strip().lower()
                == category.strip().lower()

                and price <= budget

                and quantity > 0
            ):

                matches.append(
                    {
                        "source_row": row_number,
                        "product_name": row["product_name"],
                        "category": row["category"],
                        "price": price,
                        "quantity": quantity,
                        "supplier": row["supplier"],
                    }
                )

    return matches


# ==================================================
# 2. SELECTOR AGENT - GEMMA
# ==================================================

def selector_role(
    category,
    budget,
    candidates
):

    if not candidates:
        return []

    prompt = f"""
You are the Selector Agent.

The buyer wants:

Category: {category}
Maximum budget: {budget}

The Python system has already filtered the products.

Choose up to 3 suitable products from the candidates.

Return ONLY a JSON array containing
the source_row numbers.

Example:

[2, 3]

Do not return explanations.

Candidates:

{json.dumps(candidates, indent=2)}
"""

    print()
    print("--- SELECTOR AGENT ---")

    response = client.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )

    text = response["response"].strip()

    print("Raw Selector response:")
    print(text)

    # Remove markdown code fences if Gemma adds them
    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    try:

        selected_rows = json.loads(text)

        if not isinstance(
            selected_rows,
            list
        ):
            return []

        valid_rows = {
            item["source_row"]
            for item in candidates
        }

        result = []

        for row in selected_rows:

            try:
                row = int(row)

            except (ValueError, TypeError):
                continue

            if (
                row in valid_rows
                and row not in result
            ):

                result.append(row)

        return result[:3]

    except json.JSONDecodeError:

        print(
            "Selector response could not be parsed."
        )

        return []


# ==================================================
# 3. REVIEWER AGENT - GEMMA
# ==================================================

def reviewer_role(
    category,
    budget,
    selected
):

    if not selected:
        return []

    prompt = f"""
You are the Reviewer Agent.

Review every selected product.

Rules:

1. Category must be {category}
2. Price must be less than or equal to {budget}
3. Quantity must be greater than 0

Return ONLY a JSON array containing
the source_row numbers of products
that pass all rules.

Do not return explanations.

Selected products:

{json.dumps(selected, indent=2)}
"""

    print()
    print("--- REVIEWER AGENT ---")

    response = client.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )

    text = response["response"].strip()

    print("Raw Reviewer response:")
    print(text)

    # Remove markdown code fences
    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    try:

        reviewed_rows = json.loads(text)

        if not isinstance(
            reviewed_rows,
            list
        ):
            return []

        allowed_rows = {
            item["source_row"]
            for item in selected
        }

        result = []

        for row in reviewed_rows:

            try:
                row = int(row)

            except (ValueError, TypeError):
                continue

            if (
                row in allowed_rows
                and row not in result
            ):

                result.append(row)

        return result[:3]

    except json.JSONDecodeError:

        print(
            "Reviewer response could not be parsed."
        )

        return []


# ==================================================
# 4. MAIN WORKFLOW
# ==================================================

def create_shortlist(
    category,
    budget
):

    print()
    print("========================================")
    print("NEW SHORTLIST REQUEST")
    print("========================================")

    # ----------------------------------------------
    # Validate category
    # ----------------------------------------------

    if not category or not category.strip():

        return (
            [],
            "Please enter a category.",
            ""
        )


    # ----------------------------------------------
    # Validate budget
    # ----------------------------------------------

    try:

        budget = float(budget)

    except (ValueError, TypeError):

        return (
            [],
            "Invalid budget. Please enter a number.",
            ""
        )


    if budget <= 0:

        return (
            [],
            "Budget must be greater than zero.",
            ""
        )


    print(
        f"Category: {category}"
    )

    print(
        f"Budget: ₹{budget}"
    )


    # ==================================================
    # STEP 1 - PYTHON FILTER
    # ==================================================

    candidates = filter_offers(
        category,
        budget
    )

    print()
    print("--- PYTHON FILTER ---")

    print("Candidates:")

    for item in candidates:
        print(item)


    # ==================================================
    # STEP 2 - EMPTY RESULT
    # ==================================================

    if not candidates:

        message = (
            f"No products match category "
            f"'{category}', budget <= "
            f"₹{budget:.2f}, and available "
            f"quantity > 0."
        )

        print(message)

        return (
            [],
            message,
            ""
        )


    # ==================================================
    # STEP 3 - SELECTOR AGENT
    # ==================================================

    selected_rows = selector_role(
        category,
        budget,
        candidates
    )

    print()
    print("Selector result:")
    print(selected_rows)


    selected = [
        item
        for item in candidates
        if item["source_row"]
        in selected_rows
    ]


    print()
    print("Selected products:")
    print(selected)


    if not selected:

        return (
            [],
            "Selector did not return a valid shortlist.",
            ""
        )


    # ==================================================
    # STEP 4 - REVIEWER AGENT
    # ==================================================

    reviewed_rows = reviewer_role(
        category,
        budget,
        selected
    )

    print()
    print("Reviewer result:")
    print(reviewed_rows)


    final_items = [
        item
        for item in selected
        if item["source_row"]
        in reviewed_rows
    ]


    print()
    print("Final products:")
    print(final_items)


    if not final_items:

        return (
            [],
            "Reviewer rejected all selected products.",
            ""
        )


    # ==================================================
    # STEP 5 - FINAL PYTHON VALIDATION
    # ==================================================

    validated_items = []

    for item in final_items:

        if (
            item["category"].strip().lower()
            == category.strip().lower()

            and item["price"] <= budget

            and item["quantity"] > 0
        ):

            validated_items.append(item)


    if not validated_items:

        return (
            [],
            "No products passed final validation.",
            ""
        )


    # Maximum 3 products
    validated_items = validated_items[:3]


    # ==================================================
    # STEP 6 - PREPARE GRADIO TABLE
    # ==================================================

    # IMPORTANT:
    # Use LISTS here because Gradio Dataframe
    # expects rows, not dictionaries.

    output_rows = []

    for item in validated_items:

        output_rows.append(
            [
                item["product_name"],
                item["supplier"],
                item["price"],
                (
                    f"Matches {category}, "
                    f"is within the "
                    f"₹{budget:.2f} budget, "
                    f"and has stock available."
                ),
                item["source_row"],
            ]
        )


    # ==================================================
    # STEP 7 - SAVE CSV
    # ==================================================

    output_file = (
        OUTPUT_DIR / "shortlist.csv"
    )


    # IMPORTANT:
    # Use csv.writer because output_rows
    # contains lists, not dictionaries.

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "product",
                "supplier",
                "price",
                "reason",
                "source_row",
            ]
        )

        writer.writerows(
            output_rows
        )


    # ==================================================
    # STEP 8 - TERMINAL OUTPUT
    # ==================================================

    print()
    print("========================================")
    print("SHORTLIST CREATED")
    print("========================================")

    print(
        f"Saved CSV: {output_file}"
    )

    print()
    print("Final output:")

    print(output_rows)


    # ==================================================
    # STEP 9 - RETURN TO GRADIO
    # ==================================================

    message = (
        f"Shortlist created successfully. "
        f"{len(output_rows)} product(s) selected."
    )


    return (
        output_rows,
        message,
        str(output_file)
    )



demo = gr.Interface(

    fn=create_shortlist,

    inputs=[

        gr.Textbox(
            label="Category",
            placeholder="Example: Keyboard"
        ),

        gr.Number(
            label="Budget (INR)",
            value=2000
        ),
    ],


    outputs=[

        gr.Dataframe(

            headers=[
                "product",
                "supplier",
                "price",
                "reason",
                "source_row",
            ],

            datatype=[
                "str",
                "str",
                "number",
                "str",
                "number",
            ],

            label="Final Shortlist"
        ),


        gr.Textbox(
            label="Status"
        ),


        gr.Textbox(
            label="Saved CSV"
        ),
    ],


    title="Budget Purchase Shortlist Assistant",


    description=(
        "Enter a product category and budget. "
        "The assistant filters offers, "
        "selects up to three products, "
        "reviews them, and saves the shortlist."
    ),
)


if __name__ == "__main__":

    demo.launch()

