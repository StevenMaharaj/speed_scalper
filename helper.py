def order_id_from_result(result) -> str | None:
    if "result" in result and "orderId" in result["result"]:
        return result["result"]["orderId"]
    elif "data" in result and "orderId" in result["data"]:
        return result["data"]["orderId"]
    else:
        print(f"Unexpected order response format: {result}")
        return None
