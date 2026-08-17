def recovery_risks(sleep_hours: float | None) -> list[str]:
    if sleep_hours is None:
        return ["Данные о сне не указаны — восстановление оценено неполно."]
    if sleep_hours < 6:
        return ["Сон существенно ниже нормы (менее 6 часов)."]
    if sleep_hours < 7:
        return ["Сон ниже целевого уровня (7–9 часов)."]
    return []
