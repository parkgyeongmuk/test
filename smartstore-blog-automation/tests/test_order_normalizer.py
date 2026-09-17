from smartstore_blog_automation.order_normalizer import normalize_order_items


def test_normalize_order_items_nested_shape():
    raw = [
        {
            "productOrder": {
                "productOrderId": "2024010112345678",
                "productName": "무선 이어폰",
                "quantity": 2,
                "totalPaymentAmount": 59800,
                "productOrderStatus": "PAYED",
            },
            "order": {"orderDate": "2024-01-01T10:00:00.000+09:00"},
        }
    ]

    items = normalize_order_items(raw)

    assert len(items) == 1
    item = items[0]
    assert item.product_order_id == "2024010112345678"
    assert item.product_name == "무선 이어폰"
    assert item.quantity == 2
    assert item.amount == 59800
    assert item.status == "PAYED"
    assert item.ordered_at is not None
    assert item.ordered_at.year == 2024


def test_normalize_order_items_flat_shape_fallback():
    raw = [
        {
            "productOrderId": "X1",
            "productName": "텀블러",
            "quantity": 1,
            "totalPaymentAmount": 15000,
            "productOrderStatus": "DELIVERED",
        }
    ]

    items = normalize_order_items(raw)

    assert items[0].product_name == "텀블러"
    assert items[0].amount == 15000


def test_normalize_order_items_missing_fields_defaults():
    items = normalize_order_items([{}])

    assert items[0].product_name == "(상품명 없음)"
    assert items[0].quantity == 0
    assert items[0].amount == 0
    assert items[0].status == "UNKNOWN"
    assert items[0].ordered_at is None
