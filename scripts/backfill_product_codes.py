"""One-time backfill: assign product_code to existing products that lack one.

Run once after deploying the product_code feature:
    python -m scripts.backfill_product_codes
"""

from scripts.product_store import ProductStore


def main() -> None:
    # Maintenance over every channel (codes are globally unique). One
    # transaction; rows are updated in place, never replaced wholesale.
    total = len(ProductStore.snapshot(all_channels=True))
    assigned = ProductStore.backfill_missing_product_codes(all_channels=True)
    for item in assigned:
        print(f"{item['id']}: {item['name']!r} -> {item['product_code']}")
    print(f"Done. {len(assigned)} product(s) backfilled, {total - len(assigned)} already had a code.")


if __name__ == "__main__":
    main()
