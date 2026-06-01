import json
import os
from typing import List, Dict, Any

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")
RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")

def load_json(file_path: str, default: Any) -> Any:
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(file_path: str, data: Any) -> bool:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# Catalog Management
def load_catalog() -> List[Dict[str, Any]]:
    return load_json(CATALOG_PATH, [])

def save_catalog(catalog: List[Dict[str, Any]]) -> bool:
    return save_json(CATALOG_PATH, catalog)

def get_product_by_id(product_id: str) -> Dict[str, Any]:
    catalog = load_catalog()
    for product in catalog:
        if product["id"] == product_id:
            return product
    return None

def get_all_categories() -> List[str]:
    catalog = load_catalog()
    return sorted(list(set(product["category"] for product in catalog)))

# Rules Management
def load_rules() -> List[Dict[str, Any]]:
    return load_json(RULES_PATH, [])

def save_rules(rules: List[Dict[str, Any]]) -> bool:
    return save_json(RULES_PATH, rules)
