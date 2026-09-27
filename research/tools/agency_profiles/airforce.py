"""The Department of the Air Force profile (the Air Force and the Space Force): loaded by agency.py from agency_profiles/.

Codes, office names and organization ids are as the saved SAM.gov records and notice searches of 2026-09-26 print them;
the topic codes are the USAF component's as the DoD SBIR/STTR portal index pages of 2026-09-22 print them.
"""
from agency import DOD_COMMITTEES, DOD_SMALL_BUSINESS  # noqa: E402  (the one profile allowed to share the Defense constants)

# The contracting offices seeded and swept (SAM.gov organization id -> DoDAAC), with the office name as SAM.gov prints it.
_OFFICES = {"100025313": ("FA8650", "USAF AFMC AFRL PZL AFRL/PZL"), "500019728": ("FA8750", "AFRL RIK"),
            "500019028": ("FA8730", "KESSEL RUN AFLCMC/HBBK"), "500020405": ("FA2487", "AFTC PZZD (EGLIN)"),
            "500019393": ("FA8219", "AFNWC PZBG"), "500038471": ("FA8807", "MIL COMM AND PNT SSC/CGK"),
            "500038473": ("FA8811", "ASSRD ACSS TO SPC SSC/AAK-LA")}
_AFRL = ("AFRL", "AFRL-RX", "AFRL-RV", "AFRL-RY", "AFRL-RI", "AFRL-711HPW", "AFRL-RW", "AFRL-RD", "AFRL-RS SDPE", "AFRL-RQ",
         "AFRL-CRI", "AFRL-AFOSR", "AFOSR-RT")
_AFTC = ("AFTC", "AFTC-ARNOLD", "AFTC-AEDC", "AFTC-412TW", "AFTC-EGLIN")
_SSC = ("SSC", "SSC-CG", "SSC-SLD45", "USSF SSC-BZ")
_AFLCMC = ("AFLCMC-RO", "AFLCMC/HB", "AFLCMC-HB", "AFLCMC-RSO", "AFLCMC-EBE", "AFLCMC-EBW", "AFLCMC-WLZ")

PROFILE = {
    "key": "airforce",
    "label": "Department of the Air Force",
    "short": "U.S. Air Force",
    "database": "airforce_proof",
    "agency": {"toptier_code": "097", "toptier_name": "Department of Defense", "toptier_abbreviation": "DOD",
               "subtier_code": "5700", "subtier_name": "Department of the Air Force", "subtier_abbreviation": "USAF",
               "node": "agency:daf",
               # DFARS 204.1603: an instrument number opens with its issuing office's DoDAAC (FA8650-26-C-B017, FA873026RB001).
               "office_code_re": r"FA\d{4}", "small_business_directory": DOD_SMALL_BUSINESS},
    "fpds_offices": {code: name for code, name in _OFFICES.values()},
    "fpds_funding_agencies": {},
    "sam_dir": "sam_notices_airforce",
    "sam_orgs": {org: code for org, (code, _) in _OFFICES.items()},
    "sam_codes": (),
    "sam_org_nodes": {**{org: f"contracting:{code.lower()}" for org, (code, _) in _OFFICES.items()}, "300000251": "agency:daf"},
    "sbir_component": "USAF",
    # The portal's command column (USAF component, as printed) against the memory; the AFRL directorates, test center
    # wings, AFLCMC directorates and SSC offices fall to the organization the memory holds; a command it lacks (AFWERX,
    # SDA, the operational commands) falls to the Department.
    "sbir_commands": {**{c: "center:afrl" for c in _AFRL}, **{c: "command:aftc" for c in _AFTC}, **{c: "command:aflcmc" for c in _AFLCMC},
                      **{c: "command:space-systems-command" for c in _SSC}, "AFMC": "command:afmc", "PEO-DIGITAL": "peo:digital", "PEO-WEAPONS": "peo:weapons",
                      "PEO-AFNWC STRATEGIC SYSTEMS": "peo:strategic"},
    # The research laboratory and the test center are often where the work is done rather than whose requirement it is.
    "performer_types": ("technical_center", "field_activity"),
    "office_key_re": r"(?!)",  # no program office nodes carry a code yet
    "shared_sources": ("sbir_sttr_topics", "govinfo_api"),
    "owner_types": (),
    "families": {"daf_budget_materials": "budget"},
    "moved_urls": {},
    # Topic codes as the portal writes them (AF193-005, AF19C-T001, AF212-0001, AF221-D001, AF203-DCSO1, AFX255-DPCSO1,
    # SF254-D1001, SF24B-T004, X224-ODCSO1, DAF26BZ01-DV001, DAF26TZ06-NV006); contract and solicitation numbers under a
    # DAF DoDAAC (FA8650-26-C-B017, FA875024CB108, FA2487-24-Q-B001, FA8811-26-R-B001).
    "topic_re": r"\b(?:(?:AFX?|SF|X)\d{2}[0-9A-Z]-[A-Z]{0,6}\d{1,5}|DAF\d{2}[BT][XZ]\d{2}-[A-Z]{2}\d{3})\b",
    "piid_re": r"\bFA\d{4}-?\d{2}-?[A-Z]-?[A-Z0-9]{4}\b",
    "solicitation_re": r"\bFA\d{4}-?\d{2}-?[A-Z]-?[A-Z0-9]{4}\b",
    "generic_words": ("air force", "u.s. air force", "department of the air force", "space force", "u.s. space force", "usaf", "ussf",
                      "daf", "air force materiel command", "afmc", "sources sought", "industry day"),
    "fedreg_conditions": [("conditions[agencies][]", "air-force-department")],
    "fedreg_label": "Department of the Air Force",
    "fedreg_name_pattern": None,
    "congress_pattern": (r"\bAir Force\b|\bAIR FORCE\b|\bSpace Force\b|\bSPACE FORCE\b|\bSAF/AQ\b"
                         r"|\b(?:AFMC|AFLCMC|AFRL|AFWERX|SpaceWERX|AFNWC|SSC)\b|\bSpace Systems Command\b"
                         r"|\bAir Force (?:Materiel Command|Life Cycle Management Center|Research Laboratory|Nuclear Weapons Center)\b"),
    "congress_label": "Air Force",
    "committees": DOD_COMMITTEES,
    "oversight": {"agency": "Department of the Air Force (the Air Force and the Space Force, their commands, centers, program executive offices and contracting offices)",
                  "queries": ("Air Force", "Space Force"),
                  "reviewed_re": r"Department of (War|Defense|the Air Force)\b|\bAir Force\b|\bSpace Force\b",
                  "names_re": r"\b(Air Force|Space Force|AFMC|AFLCMC|AFRL|AFNWC|Space Systems Command|ICBM|Sentinel|bomber|fighter|satellite)\b",
                  "gao_query": "GAO report Air Force Space Force acquisition program"},
    # af.mil hosts answer 403 to a direct request from this address, so no speech archive is read yet.
    "remarks": {"speeches": None, "testimony": None, "article_re": r"^(?!)",
                "names_re": r"\b(Air Force|Space Force|SAF/AQ|AFMC|AFLCMC|AFRL|Space Systems Command)\b",
                "agency": "Department of the Air Force (the Air Force and the Space Force, their commands, centers, program executive offices and contracting offices)",
                "testimony_pages": [],
                "conference_query": 'defense conference agenda speakers "Air Force" OR "Space Force" "Program Executive Officer" OR "Air Force Materiel Command" OR "Space Systems Command" keynote panel',
                "own_domains": ["af.mil", "spaceforce.mil", "dvidshub.net"],
                "providers": {"speech": "af_mil_speeches", "testimony": "house_committee_repository", "statement": "house_committee_repository",
                              "conference": "conference_pages_exa"}},
    "news": {"feeds": [{"publisher": "Department of Defense", "url": "https://www.war.gov/News/Contracts/", "index": True}],
             "official_names": {"www.af.mil": "U.S. Air Force", "www.spaceforce.mil": "U.S. Space Force", "www.afmc.af.mil": "AFMC",
                                "www.aflcmc.af.mil": "AFLCMC", "www.afrl.af.mil": "AFRL", "www.ssc.spaceforce.mil": "Space Systems Command",
                                "www.dvidshub.net": "DVIDS", "www.war.gov": "Department of Defense", "www.defense.gov": "Department of Defense"},
             "standing_terms": ["Air Force Life Cycle Management Center", "Air Force Research Laboratory", "Space Systems Command",
                                "Program Executive Officer", "Program Executive Office", "AFWERX", "SpaceWERX", "acquisition", "contract award"]},
    "protests": {"listing": "https://www.gao.gov/legal/bid-protests/search?agency=Department%20of%20the%20Air%20Force&page={page}",
                 "agency": "Department of the Air Force", "max_pages": 60},
    # The P-40 books print line items as "3010F: ..." (Aircraft Procurement, Air Force); none is saved yet.
    "budget": {"exhibit": "P-40", "pb_label": "Air Force", "books_dir": "jbooks_airforce", "provider": "daf_budget_materials"},
    "people": {"department": "agency:daf",
               "executive": ("secretary of the air force", "assistant secretary", "under secretary", "chief of staff", "chief of space operations",
                             "commander,", "commander of", "program executive officer", "director"),
               "remarks_providers": None, "staff_listing": None},
    # No forecast is published in a readable file: the Office of Small Business Programs page named Acquisition Forecasts
    # (Wayback capture of 2026-05-15) links none, and the AFLCMC Business and Enterprise Systems Smart Guide is a PDF
    # that answers 403 here with no archived copy.
    "forecast": {"pack_glob": None, "label": "", "short": "", "providers": {}, "memory_tool": "org_memory_airforce.py"},
    "pilot_offices": ("PEO-DIGITAL", "PEO-WEAPONS", "PEO-STRATEGIC"),
    "coverage_orgs": ["SAF/AQ", "AFMC", "AFLCMC", "AFRL", "AFWERX", "SpaceWERX", "SSC", "AFNWC"],
    # A DAF notice names its office by its symbol (AFLCMC/HBBK, SSC/CGK, AFRL/RQ) or as a PEO; there are no hull designators.
    "reading": {"office_code_re": r"\b(?:AFLCMC|AFRL|SSC|AFNWC|AFTC)[/-][A-Z][A-Z0-9]{1,4}\b|\bPEO[ -][A-Z][A-Za-z0-9]+",
                "hull_re": r"(?!)",
                # A solicitation (R) number with its spaces removed: FA2394-26-R-B003, FA873026RB001, FA8811-24-R-0001.
                "rfp_re": r"FA\d{4}-?\d{2}-?R-?[A-Z]?-?\d{3,4}(?![0-9])"},
}
