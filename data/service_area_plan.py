"""Service-area architecture for OLS local SEO.

This module is deliberately data-only. It defines the county/city page plan so
docs, tests, and future Shopify implementation scripts have one source of
truth for the service-area rollout.
"""

from __future__ import annotations

PRIMARY_COUNTIES = {
    "pinellas": {
        "name": "Pinellas County",
        "hub_handle": "estate-sale-pinellas-county",
        "status": "planned_new_hub",
        "priority": 1,
    },
    "pasco": {
        "name": "Pasco County",
        "hub_handle": "estate-sale-pasco-county",
        "status": "refresh_existing_hub",
        "priority": 1,
    },
    "hillsborough": {
        "name": "Hillsborough County",
        "hub_handle": "estate-sale-tampa-hillsborough-county",
        "status": "refresh_existing_hub",
        "priority": 1,
    },
}

SECONDARY_COUNTIES = {
    "hernando": {
        "name": "Hernando County",
        "status": "defer_or_secondary",
        "note": "Covered when practical, but do not merge into Pasco's primary hub.",
    },
    "citrus": {
        "name": "Citrus County",
        "status": "existing_secondary",
        "hub_handle": "estate-sale-citrus-county",
    },
    "manatee": {
        "name": "Manatee County",
        "status": "defer_or_secondary",
    },
}

CITY_PAGES = [
    {
        "city": "Palm Harbor",
        "county": "pinellas",
        "handle": "estate-sale-palm-harbor-pinellas-county",
        "status": "refresh_existing",
        "priority_wave": 1,
    },
    {
        "city": "Clearwater",
        "county": "pinellas",
        "handle": "estate-sale-clearwater-florida",
        "status": "refresh_existing",
        "priority_wave": 1,
    },
    {
        "city": "Tarpon Springs",
        "county": "pinellas",
        "handle": "estate-sale-tarpon-springs-florida",
        "current_handle": "tarpon-springs-estate-sale-in-woodfield",
        "status": "create_permanent_or_migrate_legacy",
        "priority_wave": 1,
    },
    {
        "city": "Tampa",
        "county": "hillsborough",
        "handle": "estate-sale-tampa-florida",
        "current_handle": "estate-sale-tampa-hillsborough-county",
        "status": "covered_by_existing_hub_or_migrate_later",
        "priority_wave": 1,
    },
    {
        "city": "New Port Richey",
        "county": "pasco",
        "handle": "estate-sale-new-port-richey-florida",
        "status": "refresh_existing",
        "priority_wave": 1,
    },
    {
        "city": "Dunedin",
        "county": "pinellas",
        "handle": "estate-sale-dunedin-florida",
        "status": "refresh_existing",
        "priority_wave": 2,
    },
    {
        "city": "Largo",
        "county": "pinellas",
        "handle": "estate-sale-largo-florida",
        "status": "refresh_existing",
        "priority_wave": 2,
    },
    {
        "city": "St. Petersburg",
        "county": "pinellas",
        "handle": "estate-sale-st-petersburg-florida",
        "status": "refresh_existing",
        "priority_wave": 2,
    },
    {
        "city": "Wesley Chapel",
        "county": "pasco",
        "handle": "estate-sale-wesley-chapel-florida",
        "status": "refresh_existing",
        "priority_wave": 2,
    },
    {
        "city": "Safety Harbor",
        "county": "pinellas",
        "handle": "estate-sale-safety-harbor-florida",
        "current_handle": "estate-sale-safety-harbor-florida-pinellas-county-34695",
        "status": "create_permanent_or_migrate_legacy",
        "priority_wave": 2,
    },
    {
        "city": "Seminole",
        "county": "pinellas",
        "handle": "estate-sale-seminole-florida",
        "status": "planned_new_city",
        "priority_wave": 2,
    },
    {
        "city": "Pinellas Park",
        "county": "pinellas",
        "handle": "estate-sale-pinellas-park-florida",
        "current_handle": "pinellas-park-estate-sale-in-the-mainlands-9841-41st-street-north",
        "status": "create_permanent_or_migrate_legacy",
        "priority_wave": 3,
    },
    {
        "city": "Trinity",
        "county": "pasco",
        "handle": "estate-sale-trinity-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Holiday",
        "county": "pasco",
        "handle": "estate-sale-holiday-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Hudson",
        "county": "pasco",
        "handle": "estate-sale-hudson-florida",
        "current_handle": "pimberton-drive-hudson",
        "status": "create_permanent_or_migrate_legacy",
        "priority_wave": 3,
    },
    {
        "city": "Port Richey",
        "county": "pasco",
        "handle": "estate-sale-port-richey-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Land O' Lakes",
        "county": "pasco",
        "handle": "estate-sale-land-o-lakes-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Brandon",
        "county": "hillsborough",
        "handle": "estate-sale-brandon-florida",
        "status": "planned_new_city",
        "priority_wave": 2,
    },
    {
        "city": "Riverview",
        "county": "hillsborough",
        "handle": "estate-sale-riverview-florida",
        "status": "planned_new_city",
        "priority_wave": 2,
    },
    {
        "city": "Carrollwood",
        "county": "hillsborough",
        "handle": "estate-sale-carrollwood-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Lutz",
        "county": "hillsborough",
        "handle": "estate-sale-lutz-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Westchase",
        "county": "hillsborough",
        "handle": "estate-sale-westchase-florida",
        "current_handle": "estate-sale-westchase-tampa-fl-33626-hillsborough-county",
        "status": "create_permanent_or_migrate_legacy",
        "priority_wave": 3,
    },
    {
        "city": "Plant City",
        "county": "hillsborough",
        "handle": "estate-sale-plant-city-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
    {
        "city": "Valrico",
        "county": "hillsborough",
        "handle": "estate-sale-valrico-florida",
        "status": "planned_new_city",
        "priority_wave": 3,
    },
]

FIRST_WAVE_HANDLES = [
    "estate-sale-pinellas-county",
    "estate-sale-pasco-county",
    "estate-sale-tampa-hillsborough-county",
    "estate-sale-palm-harbor-pinellas-county",
    "estate-sale-clearwater-florida",
    "estate-sale-new-port-richey-florida",
    "estate-sale-tarpon-springs-florida",
]


def city_pages_by_county(county_key: str) -> list[dict]:
    return [page for page in CITY_PAGES if page["county"] == county_key]


def first_wave_city_pages() -> list[dict]:
    return [
        page for page in CITY_PAGES
        if page["priority_wave"] == 1
    ]


def all_planned_handles() -> list[str]:
    handles = [county["hub_handle"] for county in PRIMARY_COUNTIES.values()]
    handles.extend(page["handle"] for page in CITY_PAGES)
    handles.extend(
        county["hub_handle"]
        for county in SECONDARY_COUNTIES.values()
        if county.get("hub_handle")
    )
    return handles
