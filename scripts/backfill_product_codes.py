"""One-time backfill: assign product_code to existing products that lack one.

Run once after deploying the product_code feature:
    python -m scripts.backfill_product_codes
"""

from scripts.product_store import ProductStore


def main() -> None:
    products = ProductStore._load()
    products.sort(key=lambda p: p.get("created_at") or "")

    updated = 0
    for product in products:
        if product.get("product_code"):
            continue
        code = ProductStore._generate_product_code(product.get("name", ""), products)
        product["product_code"] = code
        updated += 1
        print(f"{product.get('id')}: {product.get('name')!r} -> {code}")

    if updated:
        ProductStore._save(products)
    print(f"Done. {updated} product(s) backfilled, {len(products) - updated} already had a code.")


if __name__ == "__main__":
    main()
