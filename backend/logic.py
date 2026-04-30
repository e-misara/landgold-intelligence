ZONING_LAW = "3194"

HIGHWAY_SETBACKS_M = {
    "motorway": 50,
    "state_road": 30,
    "provincial_road": 15,
    "village_road": 10,
}

LAND_TYPES = {
    "agricultural":       {"base_usd_m2": 8,  "roi_multiplier": 2.5},
    "forest_edge":        {"base_usd_m2": 5,  "roi_multiplier": 1.8},
    "zoned_residential":  {"base_usd_m2": 45, "roi_multiplier": 3.2},
    "zoned_commercial":   {"base_usd_m2": 90, "roi_multiplier": 4.5},
    "industrial":         {"base_usd_m2": 35, "roi_multiplier": 3.0},
    "tourism_zone":       {"base_usd_m2": 60, "roi_multiplier": 5.0},
}

TITLE_DEED_RISKS = {
    "mortgage":         25,
    "annotation":       15,
    "court_injunction": 40,
    "easement":         10,
    "multiple_owners":  20,
    "no_issue":          0,
}

GOV_SIGNAL_MULTIPLIERS = {
    "infrastructure_project_nearby": 1.8,
    "municipality_zoning_change":    2.2,
    "highway_extension":             1.6,
    "airport_expansion":             2.5,
    "industrial_zone_declaration":   1.9,
    "tourism_incentive_zone":        2.3,
    "none":                          1.0,
}


def calculate_usd_m2(land_type: str, area_m2: float, gov_signal: str) -> dict:
    lt = LAND_TYPES.get(land_type, LAND_TYPES["agricultural"])
    multiplier = GOV_SIGNAL_MULTIPLIERS.get(gov_signal, 1.0)

    current_usd_m2   = lt["base_usd_m2"]
    projected_usd_m2 = round(current_usd_m2 * multiplier, 2)
    total_current    = round(current_usd_m2 * area_m2, 2)
    total_projected  = round(projected_usd_m2 * area_m2, 2)
    roi_pct          = round(((total_projected - total_current) / total_current) * 100, 1)

    return {
        "land_type":          land_type,
        "area_m2":            area_m2,
        "current_usd_m2":     current_usd_m2,
        "projected_usd_m2":   projected_usd_m2,
        "total_current_usd":  total_current,
        "total_projected_usd": total_projected,
        "roi_percent":        roi_pct,
        "gov_signal":         gov_signal,
    }


def score_risk(title_constraints: list, highway_proximity_m: float, road_type: str) -> dict:
    base_score = sum(TITLE_DEED_RISKS.get(c, 0) for c in title_constraints)

    setback = HIGHWAY_SETBACKS_M.get(road_type, 0)
    if highway_proximity_m < setback:
        base_score += 30
    elif highway_proximity_m < setback * 1.5:
        base_score += 10

    risk_score = min(base_score, 100)

    if risk_score < 20:
        label = "LOW"
    elif risk_score < 50:
        label = "MEDIUM"
    elif risk_score < 75:
        label = "HIGH"
    else:
        label = "CRITICAL"

    return {
        "risk_score":               risk_score,
        "risk_label":               label,
        "constraints":              title_constraints,
        "highway_setback_required": setback,
        "highway_proximity_m":      highway_proximity_m,
        "setback_compliant":        highway_proximity_m >= setback,
    }
