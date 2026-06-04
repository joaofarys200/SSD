from typing import List, Dict, Any
import requests
from data_manager import load_rules, get_product_by_id

class RulesEngine:
    def __init__(self):
        self.rules = []
        self.refresh_rules()

    def refresh_rules(self):
        """Loads rules from storage (kept for backwards compatibility)."""
        pass

    def evaluate(self, cart_items: List[Dict[str, Any]], client_type: str) -> List[Dict[str, Any]]:
        """
        Evaluates the active cart items and client type against DecisionRules.io.
        Returns a list of recommended products with explanations and discounts.
        """
        # Calculate cart summary metrics
        cart_product_ids = {item["product_id"] for item in cart_items}
        cart_categories = {item["category"] for item in cart_items}
        cart_total = sum(item["price"] * item["quantity"] for item in cart_items)
        
        DECISIONRULES_RULE_ID = "687f7caf-1ba8-6060-9ce5-1cad6e86dd2d"
        DECISIONRULES_API_KEY = "TusdyGTCYfvBE9yJDuuoqqaEKkrqANAOClddkXl5orEuCeBR_VRnsivWHQ6f1SDT"
        
        url = f"https://api.decisionrules.io/rule/solve/{DECISIONRULES_RULE_ID}"
        headers = {
            "Authorization": f"Bearer {DECISIONRULES_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Payload format matching the nested schema defined in DecisionRules (under 'input')
        payload = {
            "data": {
                "input": {
                    "client_type": client_type,
                    "min_cart_total": cart_total,
                    "has_product_in_cart": list(cart_product_ids),
                    "has_category_in_cart": list(cart_categories)
                }
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
        except Exception as e:
            # Fallback to empty list in case of network or API errors
            print(f"Error calling DecisionRules API: {e}")
            return []
            
        triggered_recommendations = {}

        for item in response_data:
            # The result is nested under the 'output' key in DecisionRules response
            out_data = item.get("output", {})
            rec_product_id = out_data.get("recommend_product_id")
            if not rec_product_id:
                continue
                
            # Rule validation: Don't recommend something that is already in the cart
            if rec_product_id in cart_product_ids:
                continue
                
            # Retrieve recommended product details from local catalog
            product = get_product_by_id(rec_product_id)
            if not product:
                continue
                
            # Calculate recommendation values
            discount = out_data.get("discount_percent", 0.0)
            priority = out_data.get("priority_score", 0)
            
            orig_price = product["price"]
            disc_price = orig_price * (1 - (discount / 100.0))
            
            recommendation = {
                "rule_id": f"dr_{rec_product_id}",
                "rule_name": f"Recomendação {product['name']}",
                "product_id": rec_product_id,
                "product_name": product["name"],
                "category": product["category"],
                "original_price": orig_price,
                "discount_percent": discount,
                "discounted_price": round(disc_price, 2),
                "margin": product["margin"],
                "priority_score": priority,
                "explanation": out_data.get("explanation", f"Sugerido por DecisionRules")
            }
            
            # Conflict resolution: if the product is already recommended,
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
