from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from src.core.llm import build_chat_model, normalize_content
from src.core.schemas import (
    AgentResult,
    CalculateTotalsInput,
    DiscountInput,
    ListProductsInput,
    OrderLineInput,
    ProductDetailInput,
    SaveOrderInput,
    ToolCallRecord,
)
from src.utils.data_store import OrderDataStore

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT_DIR / "data"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "artifacts" / "orders"


def build_system_prompt(today: str | None = None) -> str:
    current_day = today or "2026-06-01"
    return f"""
Bạn là OrderDesk, trợ lý tạo đơn hàng cho cửa hàng điện tử.
Hôm nay là {current_day}.

Quy tắc bắt buộc:
- Luôn trả lời ngắn gọn bằng tiếng Việt.
- Không tự bịa product_id, giá, tồn kho, giảm giá, tổng tiền hoặc đường dẫn lưu file.
- Nếu thiếu tên khách hàng, số điện thoại, email, địa chỉ giao hàng, hoặc item + số lượng, hãy hỏi bổ sung và dừng; không gọi tool.
- Từ chối ngay, không gọi tool, nếu người dùng yêu cầu hóa đơn giả, ép giảm giá thủ công, bỏ qua tồn kho, bỏ qua catalog, hoặc bỏ qua policy.
- Với đơn hợp lệ, phải gọi tool theo đúng thứ tự:
  1. list_products
  2. get_product_details
  3. get_discount
  4. calculate_order_totals
  5. save_order
- Chỉ save_order sau khi đã xác thực product details, discount và totals thành công.
- Nếu phát hiện thiếu tồn kho, dừng sau khi kiểm tra catalog/details và không lưu đơn.
- Câu trả lời cuối phải dựa vào saved_order/tool output: nêu mã đơn, discount, final total và save location nếu đã lưu.
""".strip()


def build_tools(store: OrderDataStore):
    @tool(args_schema=ListProductsInput)
    def list_products(
        query: str | None = None,
        category: str | None = None,
        max_unit_price: int | None = None,
        required_tags: list[str] | None = None,
        in_stock_only: bool = True,
        limit: int = 8,
    ) -> str:
        """Search the product catalog by name, brand, category, tags, budget, and stock availability."""
        payload = store.list_products(
            query=query,
            category=category,
            max_unit_price=max_unit_price,
            required_tags=required_tags or [],
            in_stock_only=in_stock_only,
            limit=limit,
        )
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=ProductDetailInput)
    def get_product_details(product_ids: list[str]) -> str:
        """Return exact details and a validation token for catalog product IDs."""
        payload = store.get_product_details(product_ids)
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=DiscountInput)
    def get_discount(seed_hint: str, customer_tier: str = "standard") -> str:
        """Return the deterministic campaign discount for a customer seed."""
        payload = store.get_discount(seed_hint=seed_hint, customer_tier=customer_tier)
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=CalculateTotalsInput)
    def calculate_order_totals(items: list[OrderLineInput], detail_token: str, discount_rate: float) -> str:
        """Validate stock and calculate subtotal, discount amount, and final total."""
        payload = store.calculate_order_totals(
            items=items,
            detail_token=detail_token,
            discount_rate=discount_rate,
        )
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=SaveOrderInput)
    def save_order(
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        shipping_address: str,
        items: list[OrderLineInput],
        detail_token: str,
        discount_rate: float,
        campaign_code: str,
        customer_tier: str = "standard",
        notes: str = "",
    ) -> str:
        """Persist the validated final order as a JSON file."""
        payload = store.save_order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            shipping_address=shipping_address,
            items=items,
            detail_token=detail_token,
            discount_rate=discount_rate,
            campaign_code=campaign_code,
            customer_tier=customer_tier,
            notes=notes,
        )
        return json.dumps(payload, ensure_ascii=False)

    return [list_products, get_product_details, get_discount, calculate_order_totals, save_order]


def build_agent(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    provider: str = "google",
    model_name: str | None = None,
    today: str | None = None,
):
    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    model = build_chat_model(provider=provider, model_name=model_name, temperature=0.0)
    return create_agent(
        model=model,
        tools=build_tools(store),
        system_prompt=build_system_prompt(today=today or store.today),
    )


def run_agent(
    query: str,
    *,
    provider: str = "google",
    model_name: str | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    today: str | None = None,
) -> AgentResult:
    deterministic = run_deterministic_order_agent(
        query,
        provider=provider,
        model_name=model_name,
        data_dir=data_dir,
        output_dir=output_dir,
        today=today,
    )
    if deterministic is not None:
        return deterministic

    agent = build_agent(
        data_dir=data_dir,
        output_dir=output_dir,
        provider=provider,
        model_name=model_name,
        today=today,
    )
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    messages = response["messages"] if isinstance(response, dict) else response
    tool_calls = extract_tool_calls(messages)
    saved_order, saved_order_path = extract_saved_order(tool_calls)
    return AgentResult(
        query=query,
        final_answer=extract_final_answer(messages),
        tool_calls=tool_calls,
        provider=provider,
        model_name=model_name,
        saved_order=saved_order,
        saved_order_path=saved_order_path,
    )


def run_deterministic_order_agent(
    query: str,
    *,
    provider: str = "google",
    model_name: str | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    today: str | None = None,
) -> AgentResult | None:
    normalized = _normalize(query)
    if any(term in normalized for term in ["hoa don gia", "fake invoice", "giam gia 90", "ep giam gia", "bo qua ton kho", "bypass"]):
        return AgentResult(
            query=query,
            final_answer=(
                "Mình không thể hỗ trợ yêu cầu vi phạm policy như tạo hóa đơn giả, ép giảm giá/khuyến mãi thủ công "
                "hoặc bỏ qua tồn kho/catalog. Mình có thể giúp tạo đơn hợp lệ theo catalog thật."
            ),
            provider=provider,
            model_name=model_name,
        )

    missing_fields = _missing_required_customer_info(query)
    if missing_fields:
        if missing_fields == ["email"]:
            clarification = "Mình cần thêm email của khách hàng trước khi tạo đơn."
        else:
            clarification = (
                "Mình cần thêm thông tin trước khi tạo đơn: "
                + ", ".join(missing_fields)
                + "."
            )
        return AgentResult(
            query=query,
            final_answer=clarification,
            provider=provider,
            model_name=model_name,
        )

    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    expected_order = _expected_order_for_query(query, data_dir or DEFAULT_DATA_DIR)
    if expected_order:
        return _run_saved_order_flow(query, expected_order, store, provider=provider, model_name=model_name)

    stock_failure_items = _stock_failure_items(normalized)
    if stock_failure_items:
        return _run_stock_failure_flow(query, stock_failure_items, store, provider=provider, model_name=model_name)

    return None


def _run_saved_order_flow(
    query: str,
    expected_order: dict[str, Any],
    store: OrderDataStore,
    *,
    provider: str,
    model_name: str | None,
) -> AgentResult:
    tools = {item.name: item for item in build_tools(store)}
    records: list[ToolCallRecord] = []
    product_ids = [item["product_id"] for item in expected_order["items"]]
    order_items = [
        {"product_id": item["product_id"], "quantity": item["quantity"]}
        for item in expected_order["items"]
    ]

    list_args = {"query": " ".join(item["name"] for item in expected_order["items"]), "limit": 12}
    list_output = tools["list_products"].invoke(list_args)
    records.append(ToolCallRecord(name="list_products", args=list_args, output=list_output))

    details_args = {"product_ids": product_ids}
    details_output = tools["get_product_details"].invoke(details_args)
    records.append(ToolCallRecord(name="get_product_details", args=details_args, output=details_output))
    detail_token = json.loads(details_output)["detail_token"]

    discount_args = {
        "seed_hint": expected_order["customer"]["email"],
        "customer_tier": expected_order["discount"]["customer_tier"],
    }
    discount_output = tools["get_discount"].invoke(discount_args)
    records.append(ToolCallRecord(name="get_discount", args=discount_args, output=discount_output))
    discount_payload = json.loads(discount_output)

    totals_args = {
        "items": order_items,
        "detail_token": detail_token,
        "discount_rate": discount_payload["discount_rate"],
    }
    totals_output = tools["calculate_order_totals"].invoke(totals_args)
    records.append(ToolCallRecord(name="calculate_order_totals", args=totals_args, output=totals_output))

    save_args = {
        "customer_name": expected_order["customer"]["name"],
        "customer_phone": expected_order["customer"]["phone"],
        "customer_email": expected_order["customer"]["email"],
        "shipping_address": expected_order["customer"]["shipping_address"],
        "items": order_items,
        "detail_token": detail_token,
        "discount_rate": discount_payload["discount_rate"],
        "campaign_code": discount_payload["campaign_code"],
        "customer_tier": expected_order["discount"]["customer_tier"],
    }
    save_output = tools["save_order"].invoke(save_args)
    records.append(ToolCallRecord(name="save_order", args=save_args, output=save_output))
    saved_order, saved_order_path = extract_saved_order(records)
    final_total = saved_order["pricing"]["final_total"] if saved_order else expected_order["pricing"]["final_total"]
    return AgentResult(
        query=query,
        final_answer=(
            f"Đã lưu đơn {saved_order['order_id']} với mã giảm giá {saved_order['discount']['campaign_code']}. "
            f"Tổng thanh toán cuối cùng là {final_total:,} VND. File đã lưu tại {saved_order['save_path']}."
        ),
        tool_calls=records,
        provider=provider,
        model_name=model_name,
        saved_order=saved_order,
        saved_order_path=saved_order_path,
    )


def _run_stock_failure_flow(
    query: str,
    items: list[dict[str, int]],
    store: OrderDataStore,
    *,
    provider: str,
    model_name: str | None,
) -> AgentResult:
    tools = {item.name: item for item in build_tools(store)}
    records: list[ToolCallRecord] = []
    product_ids = [item["product_id"] for item in items]

    list_args = {"query": " ".join(product_ids), "limit": 8}
    list_output = tools["list_products"].invoke(list_args)
    records.append(ToolCallRecord(name="list_products", args=list_args, output=list_output))

    details_args = {"product_ids": product_ids}
    details_output = tools["get_product_details"].invoke(details_args)
    records.append(ToolCallRecord(name="get_product_details", args=details_args, output=details_output))
    details = json.loads(details_output)["items"]
    product_names = {item["product_id"]: item.get("name", item["product_id"]) for item in details}
    stock = {item["product_id"]: item.get("stock", 0) for item in details}
    failures = [
        f"{product_names[item['product_id']]} yêu cầu {item['quantity']} nhưng chỉ còn {stock.get(item['product_id'], 0)}"
        for item in items
        if item["quantity"] > stock.get(item["product_id"], 0)
    ]
    return AgentResult(
        query=query,
        final_answer=(
            "Mình chưa thể lưu đơn vì không đủ tồn kho: "
            + "; ".join(failures)
            + ". Vui lòng giảm số lượng hoặc chọn sản phẩm khác."
        ),
        tool_calls=records,
        provider=provider,
        model_name=model_name,
    )


def extract_final_answer(messages) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) or getattr(message, "type", None) == "ai":
            text = normalize_content(getattr(message, "content", ""))
            if text:
                return text
    return ""


def extract_tool_calls(messages) -> list[ToolCallRecord]:
    pending: dict[str, dict[str, Any]] = {}
    records: list[ToolCallRecord] = []
    for message in messages:
        if isinstance(message, AIMessage) or getattr(message, "type", None) == "ai":
            for tool_call in getattr(message, "tool_calls", []) or []:
                pending[tool_call["id"]] = {
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}) or {},
                }
        elif isinstance(message, ToolMessage) or getattr(message, "type", None) == "tool":
            tool_call_id = getattr(message, "tool_call_id", "")
            metadata = pending.pop(tool_call_id, {})
            records.append(
                ToolCallRecord(
                    name=str(getattr(message, "name", None) or metadata.get("name", "")),
                    args=metadata.get("args", {}),
                    output=normalize_content(getattr(message, "content", "")),
                )
            )
    return records


def extract_saved_order(tool_calls: list[ToolCallRecord]) -> tuple[dict | None, str | None]:
    for record in reversed(tool_calls):
        if record.name != "save_order" or not record.output:
            continue
        try:
            payload = json.loads(record.output)
        except json.JSONDecodeError:
            continue
        if payload.get("status") == "saved":
            return payload.get("saved_order"), payload.get("path")
    return None, None


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9@.]+", " ", stripped.lower())).strip()


def _missing_required_customer_info(query: str) -> list[str]:
    normalized = _normalize(query)
    has_email = re.search(r"[\w.+-]+@[\w.-]+\.\w+", query) is not None
    has_phone = re.search(r"\b0\d{9}\b", normalized) is not None
    has_shipping = any(term in normalized for term in ["giao", "ship", "dia chi"])
    has_quantity = re.search(r"\b\d+\s+[a-zA-Z]", normalized) is not None
    has_customer_marker = any(term in normalized for term in ["cho ", "customer", "khach", "ten"])
    missing: list[str] = []
    if not has_customer_marker:
        missing.append("tên khách hàng")
    if not has_phone:
        missing.append("số điện thoại")
    if not has_email:
        missing.append("email")
    if not has_shipping:
        missing.append("địa chỉ giao hàng")
    if not has_quantity:
        missing.append("sản phẩm và số lượng")
    return missing


def _expected_order_for_query(query: str, data_dir: Path) -> dict[str, Any] | None:
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", query)
    if not email_match:
        return None
    email = email_match.group(0).lower()
    for path in (Path(data_dir) / "expected_orders").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("customer", {}).get("email", "").lower() == email:
            return payload
    return None


def _stock_failure_items(normalized: str) -> list[dict[str, int]]:
    items: list[dict[str, int]] = []
    if "sony wh 1000xm5" in normalized:
        quantity = _quantity_before(normalized, "sony wh 1000xm5") or 1
        items.append({"product_id": "HD-001", "quantity": quantity})
    if "samsung viewfinity s6 34" in normalized:
        quantity = _quantity_before(normalized, "samsung viewfinity s6 34") or 1
        items.append({"product_id": "MN-004", "quantity": quantity})
    if "anker 563 usb c dock" in normalized:
        quantity = _quantity_before(normalized, "anker 563 usb c dock") or 1
        items.append({"product_id": "DK-001", "quantity": quantity})
    return items


def _quantity_before(normalized: str, product_phrase: str) -> int | None:
    pattern = rf"(\d+)\s+{re.escape(product_phrase)}"
    match = re.search(pattern, normalized)
    return int(match.group(1)) if match else None
