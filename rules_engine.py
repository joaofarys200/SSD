from typing import List, Dict, Any
from data_manager import load_rules, get_product_by_id

class RulesEngine:
    def __init__(self):
        self.rules = []
        self.refresh_rules()

    def refresh_rules(self):
        """Loads rules from storage."""
        self.rules = load_rules()

    def evaluate(self, cart_items: List[Dict[str, Any]], client_type: str) -> List[Dict[str, Any]]:
        """
        Evaluates the active cart items and client type against all rules.
        Returns a list of recommended products with explanations and discounts.
        """
        # Load active rules
        active_rules = [r for r in self.rules if r.get("active", True)]
        
        # Calculate cart summary metrics
        cart_product_ids = {item["product_id"] for item in cart_items}
        cart_categories = {item["category"] for item in cart_items}
        cart_total = sum(item["price"] * item["quantity"] for item in cart_items)
        
        triggered_recommendations = {}

        for rule in active_rules:
            conditions = rule.get("conditions", {})
            actions = rule.get("actions", {})
            
            # 1. Condition: has_product_in_cart (OR matching)
            req_products = conditions.get("has_product_in_cart", [])
            if req_products and not any(pid in cart_product_ids for pid in req_products):
                continue
                
            # 2. Condition: has_category_in_cart (OR matching)
            req_categories = conditions.get("has_category_in_cart", [])
            if req_categories and not any(cat in cart_categories for cat in req_categories):
                continue
                
            # 3. Condition: min_cart_total
            min_total = conditions.get("min_cart_total", 0.0)
            if cart_total < min_total:
                continue
                
            # 4. Condition: client_type
            req_client = conditions.get("client_type", "Qualquer")
            if req_client != "Qualquer" and req_client != client_type:
                continue

            # If all conditions are met, trigger actions
            rec_product_id = actions.get("recommend_product_id")
            if not rec_product_id:
                continue
                
            # Rule validation: Don't recommend something that is already in the cart
            if rec_product_id in cart_product_ids:
                continue
                
            # Retrieve recommended product details
            product = get_product_by_id(rec_product_id)
            if not product:
                continue
                
            # Calculate recommendation values
            discount = actions.get("discount_percent", 0.0)
            priority = actions.get("priority_score", 0)
            
            orig_price = product["price"]
            disc_price = orig_price * (1 - (discount / 100.0))
            
            recommendation = {
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "product_id": rec_product_id,
                "product_name": product["name"],
                "category": product["category"],
                "original_price": orig_price,
                "discount_percent": discount,
                "discounted_price": round(disc_price, 2),
                "margin": product["margin"],
                "priority_score": priority,
                "explanation": rule.get("explanation", f"Sugerido por {rule['name']}")
            }
            
            # Conflict resolution: if the product is already recommended by another rule,
            # select the recommendation with higher priority or higher discount.
            if rec_product_id in triggered_recommendations:
                existing = triggered_recommendations[rec_product_id]
                if priority > existing["priority_score"] or (priority == existing["priority_score"] and discount > existing["discount_percent"]):
                    triggered_recommendations[rec_product_id] = recommendation
            else:
                triggered_recommendations[rec_product_id] = recommendation
                
        # Sort recommendations by priority score descending, then discount descending, then margin descending (Choice phase logic)
        sorted_recs = sorted(
            triggered_recommendations.values(),
            key=lambda x: (x["priority_score"], x["discount_percent"], x["margin"]),
            reverse=True
        )
        
        return sorted_recs
