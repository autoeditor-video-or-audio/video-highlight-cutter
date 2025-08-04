import os
import json
import sys

def main():
    if len(sys.argv) < 3:
        print("Uso: python filter_highlights.py input.classified.json output.filtered.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    min_score = int(os.getenv("MIN_SCORE", 7))

    with open(input_file, "r", encoding="utf-8") as f:
        highlights = json.load(f)

    filtered = [
        {"start": h["start"], "end": h["end"]}
        for h in highlights
        if h.get("score", 0) >= min_score
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    print(f"{len(filtered)} cortes salvos em {output_file} com nota >= {min_score}")

if __name__ == "__main__":
    main()
