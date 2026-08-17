def recovery_risks(sleep_hours: float | None) -> list[str]:
    if sleep_hours is None:
        return ["Sleep data was not provided, so recovery cannot be fully assessed."]
    if sleep_hours < 6:
        return ["Sleep is substantially below target (under 6 hours)."]
    if sleep_hours < 7:
        return ["Sleep is below the target range (7–9 hours)."]
    return []
