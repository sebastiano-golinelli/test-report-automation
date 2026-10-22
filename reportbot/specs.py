"""Minimum mechanical properties per material (indicative values from the usual standards).

Check the standard, product form and thickness that apply to a real job before relying on them.
"""

SPECS = {
    # material: (min yield MPa, min UTS MPa, max UTS MPa or None, min elongation %), source
    "Al 6061-T6": dict(yield_min=240, uts_min=260, uts_max=None, elong_min=8.0, source="EN 755-2, extruded bar"),
    "S355JR": dict(yield_min=355, uts_min=470, uts_max=630, elong_min=22.0, source="EN 10025-2, t <= 16 mm"),
    "Ti-6Al-4V": dict(yield_min=828, uts_min=895, uts_max=None, elong_min=10.0, source="ASTM B348 Grade 5"),
}

ALIASES = {  # how labs write the same material
    "6061-t6": "Al 6061-T6", "al 6061-t6": "Al 6061-T6", "aa6061-t6": "Al 6061-T6",
    "s355jr": "S355JR", "s355": "S355JR",
    "ti-6al-4v": "Ti-6Al-4V", "ti6al4v": "Ti-6Al-4V", "grade 5 titanium": "Ti-6Al-4V",
}


def normalize_material(name):
    """Return the canonical material name, or None if it is not one we have a specification for."""
    if not name:
        return None
    key = " ".join(name.lower().split())
    if name in SPECS:
        return name
    for alias, canonical in ALIASES.items():
        if alias in key:
            return canonical
    return None
