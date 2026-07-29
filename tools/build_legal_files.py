"""Build the combined installer agreement from localized legal documents."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / "licenses"
LANGUAGES = ("en", "pt", "es", "it", "fr", "de")


def main() -> None:
    separator = "\n\n" + "=" * 72 + "\n\n"
    for language in LANGUAGES:
        sections = [
            (LICENSES / f"{name}-{language}.txt").read_text(encoding="utf-8")
            for name in ("LICENSE", "TERMS", "PRIVACY")
        ]
        output = LICENSES / f"EULA-{language}.txt"
        output.write_text(separator.join(section.strip() for section in sections) + "\n", encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
