"""mock_data — deterministic aggregate fixture data for tests and STG mock mode.

Contains only aggregate pairing signals — no individual customer data.
"""

from __future__ import annotations

# Aggregate pairing fixture data keyed by product_id.
# Fields: product_id, product_name, category, pairing_score, allergens,
#         time_tags, season_tags, store_cluster_tags.
# allergens: list[str] using Japan 28-allergen names; None means metadata absent.

_PAIRING_FIXTURES: dict[str, list[dict]] = {
    "P001": [  # おにぎり 鮭 — frequently paired items
        {
            "product_id": "P003",
            "product_name": "緑茶 500ml",
            "category": "beverage",
            "pairing_score": 0.88,
            "allergens": [],
            "time_tags": ["morning", "lunch"],
            "season_tags": ["all"],
            "store_cluster_tags": ["all"],
        },
        {
            "product_id": "P005",
            "product_name": "ヨーグルト プレーン",
            "category": "dairy",
            "pairing_score": 0.72,
            "allergens": ["乳"],
            "time_tags": ["morning"],
            "season_tags": ["all"],
            "store_cluster_tags": ["urban", "suburban"],
        },
        {
            "product_id": "P006",
            "product_name": "コーヒー缶 ブラック",
            "category": "beverage",
            "pairing_score": 0.65,
            "allergens": [],
            "time_tags": ["morning", "afternoon"],
            "season_tags": ["all"],
            "store_cluster_tags": ["urban", "station"],
        },
        {
            "product_id": "P007",
            "product_name": "チョコレートバー",
            "category": "sweets",
            "pairing_score": 0.55,
            "allergens": ["乳", "小麦", "大豆"],
            "time_tags": ["afternoon", "evening"],
            "season_tags": ["autumn", "winter"],
            "store_cluster_tags": ["all"],
        },
        {
            "product_id": "P008",
            "product_name": "ミネラルウォーター 2L",
            "category": "beverage",
            "pairing_score": 0.50,
            "allergens": [],
            "time_tags": ["all"],
            "season_tags": ["summer"],
            "store_cluster_tags": ["all"],
        },
    ],
    "P002": [  # サンドイッチ ハムチーズ
        {
            "product_id": "P003",
            "product_name": "緑茶 500ml",
            "category": "beverage",
            "pairing_score": 0.82,
            "allergens": [],
            "time_tags": ["morning", "lunch"],
            "season_tags": ["all"],
            "store_cluster_tags": ["all"],
        },
        {
            "product_id": "P006",
            "product_name": "コーヒー缶 ブラック",
            "category": "beverage",
            "pairing_score": 0.78,
            "allergens": [],
            "time_tags": ["morning"],
            "season_tags": ["all"],
            "store_cluster_tags": ["urban", "station"],
        },
        {
            "product_id": "P010",
            "product_name": "アイスクリーム バニラ",
            "category": "dairy",
            "pairing_score": 0.45,
            "allergens": ["乳", "卵"],
            "time_tags": ["afternoon", "evening"],
            "season_tags": ["summer"],
            "store_cluster_tags": ["all"],
        },
    ],
    "P004": [  # カップ麺 しょうゆ
        {
            "product_id": "P003",
            "product_name": "緑茶 500ml",
            "category": "beverage",
            "pairing_score": 0.75,
            "allergens": [],
            "time_tags": ["lunch", "evening", "night"],
            "season_tags": ["autumn", "winter"],
            "store_cluster_tags": ["all"],
        },
        {
            "product_id": "P007",
            "product_name": "チョコレートバー",
            "category": "sweets",
            "pairing_score": 0.40,
            "allergens": ["乳", "小麦", "大豆"],
            "time_tags": ["evening", "night"],
            "season_tags": ["all"],
            "store_cluster_tags": ["all"],
        },
    ],
}


def stub_retrieve_pairings(product_id: str, top_k: int = 20) -> list[dict]:
    """Return deterministic aggregate pairing fixture data for the given product_id."""
    candidates = _PAIRING_FIXTURES.get(product_id, [])
    return candidates[:top_k]
