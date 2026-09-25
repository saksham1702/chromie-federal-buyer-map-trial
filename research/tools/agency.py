#!/usr/bin/env python3
"""The agency profile: everything the pipeline writes once per agency, in one place.

    AGENCY=darpa python research/tools/pipeline.py --db darpa_proof
    python research/tools/agency.py --selfcheck

`research/docs/14_reusing_this_for_another_agency.md` lists what travels to a new agency and what does not:
the office code tables, the agency filters, the feed list, the forecast reader and the organization seed.
Until 2026-09-24 those sat as constants inside a dozen tools, each spelling the Navy. This module holds them
per agency, selected by the `AGENCY` environment variable (default `navy`), and every tool reads its constants
from here. The Navy profile reproduces the constants the tools carried, so a Navy build is byte for byte what
it was; a second profile adds an agency without touching the rules.

Artefacts are kept apart: the Navy layer keeps `research/{memory,events,results,sources}`; every other agency
writes under `research/agencies/<key>/` with the same four folders. The document ledger, the saved bytes under
`data/raw/` and the model cassettes are shared, because a retrieval is a retrieval whatever layer reads it;
SAM.gov notice details are the one exception (one folder per agency), because several readers take every
detail file in the folder as this agency's.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY = os.environ.get("AGENCY", "navy").strip().lower() or "navy"

NAVY = {
    "key": "navy",
    "label": "Department of the Navy",
    "short": "U.S. Navy",
    "database": "navy_proof_e",
    "agency": {"toptier_code": "097", "toptier_name": "Department of Defense", "toptier_abbreviation": "DOD",
               "subtier_code": "1700", "subtier_name": "Department of the Navy", "subtier_abbreviation": "DON",
               "node": "agency:don"},
    # FPDS: the contracting offices swept by CONTRACTING_OFFICE_ID, and the agencies swept by FUNDING_AGENCY_ID
    # (an agency whose awards other agencies sign for it; none for the Navy, whose sweep is by office).
    "fpds_offices": {"N00039": "NAVWAR HQ", "N00024": "NAVSEA HQ", "N00014": "ONR", "N00173": "NRL",
                     "N00019": "NAVAIR HQ", "N00421": "NAWCAD Patuxent River", "N68335": "NAWCAD Lakehurst",
                     "N66001": "NIWC Pacific", "N65236": "NIWC Atlantic"},
    "fpds_funding_agencies": {},
    # SAM.gov: the folder the notice details live in, the organization ids swept (id -> office code), the offices
    # swept by code whose id is looked up at sweep time, and the memory node each organization id stands for.
    "sam_dir": "sam_notices",
    "sam_orgs": {"100076586": "N00039", "100076491": "N00024", "100076476": "N00014", "100255323": "N00173",
                 "100076487": "N66001", "100076484": "N65236"},
    "sam_codes": ("N00019", "N00421", "N68335"),
    "sam_org_nodes": {"100076586": "contracting:n00039", "100076491": "contracting:n00024", "100076476": "contracting:n00014",
                      "100255323": "center:nrl", "100076487": "center:niwc-pacific", "100076484": "center:niwc-atlantic"},
    # The DoD SBIR/STTR portal's component, and its `command` column against the memory.
    "sbir_component": "NAVY",
    # A laboratory, warfare center or field activity a notice names is often where the work is done rather than whose
    # it is: it counts as the named office only when the notice names no other (trace.specific_offices).
    "performer_types": ("technical_center", "field_activity"),
    # The office codes a contract description, a budget line or a record excerpt names, one key per match
    # (agency_layers_sql.office_of): "PMW-160", "PMW160" and "PMW 160" all read PMW160.
    "office_key_re": r"\b(PM[WSA])(?:/A)?[ -]?(\d{3})\b",
    # The org types that own requirements beside program offices and PEOs, the event family of each provider only
    # this layer has, and the words that name the buyer rather than a requirement: backtest.FAMILY and GENERIC
    # already hold the Navy's.
    "owner_types": (),
    "families": {},
    "generic_words": (),
    "sbir_commands": {"NAVSEA": "command:navsea", "NAVAIR": "command:navair", "NAVWAR": "command:navwar", "SPAWAR": "command:navwar",
                      "ONR": "command:onr", "SSPO": "command:ssp", "SSP": "command:ssp"},
    # Federal Register API conditions; an agency without a slug searches its name as a term.
    "fedreg_conditions": [("conditions[agencies][]", "navy-department")],
    "fedreg_label": "Department of the Navy",
    "fedreg_name_pattern": None,
    "shared_sources": (),  # the Navy collected everything it reads; the unmarked ledger rows are its own
    # How this agency's SBIR/STTR topic codes, contract numbers and solicitation numbers are written in a text.
    "topic_re": r"\bN\d{2}[0-9AB]-T?\d{3}\b",
    "piid_re": r"\bN\d{5}-?\d{2}-?[A-Z]-?\d{4}\b",
    "solicitation_re": r"\bN\d{5}-?\d{2}-?[A-Z]-?[A-Z0-9]{4}\b",
    # Committee reports: the pattern a directive sentence must name.
    "congress_pattern": (r"\bN(?:avy|AVY)\b|\bChief of Naval Operations\b|\bMarine Corps\b|\b(?:NAVSEA|NAVAIR|NAVWAR|NAVSUP|ONR|NRL|NIWC)\b"
                         r"|\bNaval (?:Sea|Air|Supply) Systems Command\b|\bNaval Information Warfare\b|\bOffice of Naval Research\b"
                         r"|\bNaval Research Laboratory\b|\bPEO\b|\bPM[SAW][- ]?\d{2,3}\b"),
    "congress_label": "Navy",
    # oversight.gov and the GAO feed: the agency as the reader is told it, the full-text queries, what a reviewed-agency
    # cell must say and what a title must name.
    "oversight": {"agency": "Department of the Navy (the Navy and the Marine Corps, their systems commands, program offices and field activities)",
                  "queries": ("Navy", "Naval"),
                  "reviewed_re": r"Department of (War|Defense|the Navy)\b|\bNavy\b",
                  "names_re": r"\b(Navy|Naval|NAVSEA|NAVAIR|NAVWAR|NAVSUP|NAVFAC|ONR|Marine Corps|shipbuilding|submarine|carrier)\b",
                  "gao_query": "GAO report Navy shipbuilding acquisition program"},
    # Leaders' words: the speech and testimony archives (None where the agency keeps no archive), the article pattern,
    # what a hearing or conference page must name, and the agency as the reader is told it.
    "remarks": {"speeches": "https://www.navy.mil/Press-Office/Speeches/",
                "testimony": "https://www.navy.mil/Press-Office/Testimony/",
                "article_re": r"^https://www\.navy\.mil/Press-Office/(Speeches/display-speech|Testimony/display-testimony)/Article/\d+/[^?#]+$",
                "names_re": r"\b(Navy|Naval|NAVSEA|NAVAIR|NAVWAR|NAVSUP|NAVFAC|Marine Corps|Seapower|shipbuilding|submarine)\b",
                "agency": "Department of the Navy (the Navy and the Marine Corps, their systems commands, program offices and field activities)",
                "testimony_pages": [],
                # Exa discovery of conference pages naming the agency's officials; the agency's own sites are read
                # by their own sources and left out.
                "conference_query": 'defense conference agenda speakers Navy "Chief of Naval Operations" OR "Program Executive Officer" OR "Naval Sea Systems Command" keynote panel',
                "own_domains": ["navy.mil", "dvidshub.net"],
                "providers": {"speech": "navy_mil_speeches", "testimony": "navy_mil_speeches", "statement": "house_committee_repository",
                              "conference": "conference_pages_exa"}},
    # News: the feeds polled, the official publishers by host, and the terms an article must carry to be kept.
    "news": {"feeds": [
        {"publisher": "NAVWAR", "url": "https://www.navwar.navy.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=1114&max=25"},
        {"publisher": "U.S. Navy", "url": "https://www.navy.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=1075&max=25"},
        {"publisher": "DVIDS", "url": "https://www.dvidshub.net/rss/news"},
        {"publisher": "Department of Defense", "url": "https://www.war.gov/News/Contracts/", "index": True},
        {"publisher": "PAE Mission Systems", "url": "https://www.missionsystems.navy.mil/News/", "index": True}],
        "official_names": {
            "www.navy.mil": "U.S. Navy", "www.navwar.navy.mil": "NAVWAR", "www.dvidshub.net": "DVIDS",
            "www.missionsystems.navy.mil": "PAE Mission Systems", "www.paemaritime.navy.mil": "PAE Maritime",
            "www.secnav.navy.mil": "Secretary of the Navy", "www.doncio.navy.mil": "DON CIO",
            "www.war.gov": "Department of Defense", "www.defense.gov": "Department of Defense",
            "www.navsea.navy.mil": "NAVSEA", "www.onr.navy.mil": "Office of Naval Research"},
        "standing_terms": ["NAVWAR", "SPAWAR", "NIWC", "Naval Information Warfare", "PEO C4I", "PEO Digital",
                           "Portfolio Acquisition Executive", "Program Executive Office", "program office",
                           "Direct Reporting Program Manager", "acquisition", "contract award"]},
    # GAO's bid-protest docket: the listing address (the agency filter is in it) and the agency as the docket prints it.
    "protests": {"listing": "https://www.gao.gov/legal/bid-protests/search?agency=Department%20of%20the%20Navy&page={page}",
                 "agency": "Department of the Navy", "max_pages": 60},
    # Budget: the justification-book exhibit the reader parses and the words the book prints beside "PB yyyy".
    # evidence_host: the host the Navy evidence rows were first written with (the loaded rows keep it); another agency's
    # rows carry the book URL's own host.
    "budget": {"exhibit": "P-40", "pb_label": "Navy", "books_dir": "jbooks", "provider": "don_budget_justification_books",
               "evidence_host": "secnav.navy.mil"},
    # People: the department node a person falls to, and the titles read as executive.
    "people": {"department": "agency:don",
               "executive": ("secretary of the navy", "assistant secretary", "chief of naval operations", "commandant", "vice chief",
                             "under secretary", "deputy secretary", "executive officer", "commander,", "commander of", "director",
                             "portfolio acquisition executive"),
               # The source keys people.py has always written for the Navy's remarks documents (a statement under the
               # speeches key, testimony under the House key); kept as they are so the loaded rows keep their ids.
               # The loader's REMARKS_PROVIDERS (remarks.providers) reads them the other way round: an open item
               # for the Navy layer, recorded in DECISIONS.md (2026-09-25). None means the remarks providers apply.
               "remarks_providers": {"speech": "navy_mil_speeches", "statement": "navy_mil_speeches", "testimony": "house_committee_repository",
                                     "conference": "conference_pages_exa"},
               "staff_listing": None},
    # Forecast: the datapack releases the tracer reads (a glob under datapack/), the forecast providers by activity,
    # and whether the memory stage reads a forecast at all.
    "forecast": {"pack_glob": "lrae_*", "label": "Long Range Acquisition Estimate", "short": "LRAE", "providers": {"navwar": "navwar_lrae_annex25", "navsea": "navsea_lrae_annex25",
                                                              "onr": "onr_lrae_annex25", "nrl": "onr_lrae_annex25"},
                 "memory_tool": "org_memory_lrae.py"},
    # The offices whose forecast cells are judged for precision (research/docs/00).
    "pilot_offices": ("PMA/PMW 101", "PMW 120", "PMW 130", "PMW 150", "PMW 160", "PMW/A 170", "PMW 740"),
    # The coverage grid's organizations (the families are the layer's and do not change).
    "coverage_orgs": ["NAVSEA", "NAVAIR", "NAVWAR", "ONR", "NIWC"],
    # Reading the frozen corpus (pages.py, office_wiki.py, people.py): how the agency writes a program office code in a
    # notice or after a person's name, and a hull or platform designator to strip from a title (none where the agency
    # has none). The contract number pattern is `piid_re` above and the buyer's own names are `generic_words`.
    "reading": {"office_code_re": r"\b(?:PMW|PMS|PMA|IWS)[ /-]*(?:A[ -]*)?\d{2,3}(?:\.\d)?\b|\bPEO [A-Z][A-Za-z0-9]+",
                "hull_re": r"\bUSS\s+[A-Z][A-Za-z .'-]*?\s*\(?[A-Z]{2,4}[\s-]*\d{1,4}\)?|\b[A-Z]{2,4}[\s-]+\d{1,4}\b"},
}

DARPA = {
    "key": "darpa",
    "label": "Defense Advanced Research Projects Agency",
    "short": "DARPA",
    "database": "darpa_proof",
    "agency": {"toptier_code": "097", "toptier_name": "Department of Defense", "toptier_abbreviation": "DOD",
               "subtier_code": "97AE", "subtier_name": "Defense Advanced Research Projects Agency", "subtier_abbreviation": "DARPA",
               "node": "agency:darpa"},
    # One contracting office (HR0011, the Contracts Management Office); awards DARPA funds through other agencies'
    # offices are swept by funding agency (research/docs/19, section 2: 41 to 50 of the FY2026 base awards).
    "fpds_offices": {"HR0011": "DARPA Contracts Management Office"},
    "fpds_funding_agencies": {"97AE": "DARPA"},
    "sam_dir": "sam_notices_darpa",
    "sam_orgs": {"500035490": "HR0011"},
    "sam_codes": (),
    "sam_org_nodes": {"500035490": "contracting:hr0011", "300000412": "agency:darpa"},
    "sbir_component": "DARPA",
    # The portal's command field names the DARPA office that sponsors a topic, where it names one.
    "sbir_commands": {"BTO": "office:bto", "DSO": "office:dso", "IPTO": "office:ipto", "I2O": "office:i2o", "MTO": "office:mto",
                      "MXO": "office:mxo", "STO": "office:sto", "TTO": "office:tto"},
    # Sources this layer reads from the shared collection rather than its own sweeps (the portal pages and the
    # committee reports the Navy layer saved): their documents count for this layer though their notes are unmarked.
    "shared_sources": ("sbir_sttr_topics", "govinfo_api"),
    # The event family of each provider only this layer has (backtest.FAMILY holds the shared and the Navy ones), and
    # the words that name this buyer or its paperwork rather than a requirement.
    # The technical offices own DARPA's programs, as the program offices own the Navy's.
    "owner_types": ("technical_office",),
    "performer_types": (),  # the technical offices own DARPA's programs; none is only where work is done
    # A technical office as awards and notices write it ("DARPA STO ALBATROSS", "BTO SEEDLING", "(STO3)"). CSO is left
    # out: it is the commercial solutions opening as often as the office.
    "office_key_re": r"\b(BTO|DSO|I2O|MTO|MXO|STO|TTO|IPTO|ACO|APO)\d{0,2}\b",
    "families": {"darpa_site": "organization", "darpa_staff_listing": "organization", "dod_comptroller_budget_materials": "budget"},
    # Topic codes as the portal writes them (HR001119S0035-14, HR0011SB20234XL-01, DPA26BZ01-DV003). Contract and
    # solicitation numbers under any DoD office, since other agencies' offices sign most DARPA-funded awards, and an
    # Other Transaction carries a digit (9) where a contract carries its type letter.
    "topic_re": r"\b(?:HR0011[0-9A-Z]{6,9}|DPA\d{2}[BT]Z\d{2})-[A-Z]{0,2}\d{2,3}\b",
    "piid_re": r"\b[A-Z][A-Z0-9]{5}-?\d{2}-?[A-Z0-9]-?\d{4}\b",
    "solicitation_re": r"\b[A-Z][A-Z0-9]{5}-?\d{2}-?[A-Z]-?[A-Z0-9]{4}\b",
    "generic_words": ("darpa", "defense advanced research projects agency", "broad agency announcement", "baa",
                      "program announcement", "other transaction", "ot", "proposers day"),
    # The Federal Register has no agency slug for DARPA (the agencies endpoint answers 404, research/docs/19); a term
    # search for the full name stands in.
    "fedreg_conditions": [("conditions[term]", "\"Defense Advanced Research Projects Agency\"")],
    "fedreg_label": "Defense Advanced Research Projects Agency",
    # A term search returns every document whose text mentions the agency; only the ones whose title, action or
    # abstract names it are this layer's documents (the Navy's slug search needs no such filter: None).
    "fedreg_name_pattern": r"\bDARPA\b|\bDefense Advanced Research Projects Agency\b",
    "congress_pattern": r"\bDARPA\b|\bDefense Advanced Research Projects Agency\b",
    "congress_label": "DARPA",
    "oversight": {"agency": "Defense Advanced Research Projects Agency (DARPA, its technical offices and its Contracts Management Office)",
                  "queries": ("DARPA", "Defense Advanced Research Projects Agency"),
                  # The OIG lists every report under "Department of War", so the department name admits nothing here;
                  # a report is DARPA's when the agency reviewed or the title names DARPA.
                  "reviewed_re": r"\bDARPA\b|Defense Advanced Research Projects Agency",
                  "names_re": r"\b(DARPA|Defense Advanced Research Projects Agency)\b",
                  "gao_query": "GAO report DARPA research program"},
    # DARPA keeps no speech archive; its budgets-and-testimony page lists the Director's statements as submitted.
    "remarks": {"speeches": None, "testimony": None, "article_re": r"^(?!)",
                "names_re": r"\b(DARPA|Defense Advanced Research Projects Agency)\b",
                "agency": "Defense Advanced Research Projects Agency (DARPA, its technical offices and its Contracts Management Office)",
                "testimony_pages": ["https://www.darpa.mil/about/budgets-testimony"],
                "conference_query": 'defense conference agenda speakers DARPA "Defense Advanced Research Projects Agency" director OR "program manager" keynote panel',
                "own_domains": ["darpa.mil"],
                "providers": {"speech": "darpa_site", "testimony": "darpa_site", "statement": "darpa_site", "conference": "conference_pages_exa"}},
    "news": {"feeds": [
        {"publisher": "DARPA", "url": "https://www.darpa.mil/rss.xml"},
        {"publisher": "DARPA", "url": "https://www.darpa.mil/rss/opportunities.xml"},
        {"publisher": "Department of Defense", "url": "https://www.war.gov/News/Contracts/", "index": True}],
        "official_names": {"www.darpa.mil": "DARPA", "www.war.gov": "Department of Defense", "www.defense.gov": "Department of Defense"},
        "standing_terms": ["DARPA", "Defense Advanced Research Projects Agency", "Broad Agency Announcement", "program manager",
                           "Proposers Day", "Other Transaction", "acquisition", "contract award"]},
    "protests": {"listing": "https://www.gao.gov/legal/bid-protests/search?agency=Defense%20Advanced%20Research%20Projects%20Agency&page={page}",
                 "agency": "Defense Advanced Research Projects Agency", "max_pages": 10},
    # DARPA is funded through research, development, test and evaluation alone: one R-1 justification book a year,
    # whose pages are Exhibit R-2 program elements.
    "budget": {"exhibit": "R-2", "pb_label": "Defense Advanced Research Projects Agency", "books_dir": "jbooks_darpa",
               "provider": "dod_comptroller_budget_materials"},
    "people": {"department": "agency:darpa",
               "executive": ("director", "deputy director", "office director", "chief of staff", "general counsel"),
               # darpa.mil/json/staff: role, office and start date as the agency publishes them; a record's page path
               # is relative to the site.
               "staff_listing": "https://www.darpa.mil/json/staff", "staff_base_url": "https://www.darpa.mil",
               "remarks_providers": None},
    "forecast": {"pack_glob": None, "label": "", "short": "", "providers": {}, "memory_tool": "org_memory_darpa.py"},
    # The technical offices by the acronym the loaded organization carries (its office code), as the Navy's by code.
    "pilot_offices": ("BTO", "DSO", "IPTO", "MXO", "STO", "TTO"),
    "coverage_orgs": ["BTO", "DSO", "IPTO", "MXO", "STO", "TTO", "CMO"],
    # A DARPA notice names its office by acronym (the six technical offices, the four former ones the notices still
    # name, and the staff offices); DARPA has no hull designators.
    "reading": {"office_code_re": r"\b(?:BTO|DSO|I2O|IPTO|MTO|MXO|STO|TTO|DIRO|CMO|SBPO|ACO|APO|CSO)\b",
                "hull_re": r"(?!)"},
}

ARMY = {
    "key": "army",
    "label": "Department of the Army",
    "short": "U.S. Army",
    "database": "army_proof",
    "agency": {"toptier_code": "097", "toptier_name": "Department of Defense", "toptier_abbreviation": "DOD",
               "subtier_code": "2100", "subtier_name": "Department of the Army", "subtier_abbreviation": "DA",
               "node": "agency:army"},
    # The Army Contracting Command offices that sign most acquisition-program awards (FPDS, FY2026), by DoDAAC.
    "fpds_offices": {"W56KGY": "ACC-APG", "W15P7T": "ACC-APG (CECOM)", "W91CRB": "ACC-APG (Natick)", "W31P4Q": "ACC-RSA",
                     "W58RGZ": "ACC-RSA (AMCOM)", "W912CH": "ACC-DTA", "W15QKN": "ACC-NJ (Picatinny)", "W900KK": "ACC-ORL"},
    "fpds_funding_agencies": {},
    "sam_dir": "sam_notices_army",
    "sam_orgs": {"500043662": "W56KGY", "500038571": "W15P7T", "500043793": "W91CRB", "500038573": "W31P4Q",
                 "500045573": "W58RGZ", "100255245": "W912CH", "500045967": "W15QKN", "500036903": "W900KK"},
    "sam_codes": (),
    "sam_org_nodes": {"500043662": "contracting:w56kgy", "500038571": "contracting:w15p7t", "500043793": "contracting:w91crb",
                      "500038573": "contracting:w31p4q", "500045573": "contracting:w58rgz", "100255245": "contracting:w912ch",
                      "500045967": "contracting:w15qkn", "500036903": "contracting:w900kk", "300000201": "agency:army"},
    "sbir_component": "ARMY",
    # The portal's command field against the memory; a code the memory has no node for falls to the department.
    "sbir_commands": {"ASA(ALT)": "office:asaalt"},
    # The DEVCOM centers and laboratories are often where the work is done rather than whose requirement it is.
    "performer_types": ("technical_center", "field_activity"),
    "office_key_re": r"(?!)",  # the forecast writes its program offices by name; no code pattern yet
    "shared_sources": ("sbir_sttr_topics", "govinfo_api"),
    "owner_types": (),
    "families": {"army_asaalt_chart": "organization", "amc_acquisition_forecast": "forecast", "army_budget_materials": "budget"},
    # Topic codes as the portal writes them (A20-179, A214-006, A20B-T018, A254-P007, ARM26BX06-NV012); contract and
    # solicitation numbers under an Army DoDAAC (W...).
    "topic_re": r"\b(?:A\d{2}[0-9A-Z]?-[A-Z]?\d{3}|ARM\d{2}[A-Z]{2}\d{2}-[A-Z]{2}\d{3})\b",
    "piid_re": r"\bW[A-Z0-9]{5}-?\d{2}-?[A-Z]-?\d{4}\b",
    "solicitation_re": r"\bW[A-Z0-9]{5}-?\d{2}-?[A-Z]-?[A-Z0-9]{4}\b",
    "generic_words": ("army", "u.s. army", "department of the army", "army contracting command", "acc", "army materiel command",
                      "amc", "sources sought", "industry day"),
    "fedreg_conditions": [("conditions[agencies][]", "army-department")],
    "fedreg_label": "Department of the Army",
    "fedreg_name_pattern": None,
    "congress_pattern": (r"\bArmy\b|\bARMY\b|\bASA\(ALT\)|\bArmy (?:Contracting|Materiel|Futures) Command\b"
                         r"|\b(?:TACOM|AMCOM|CECOM|DEVCOM|JPEO)\b|\bPortfolio Acquisition Executive\b"),
    "congress_label": "Army",
    "oversight": {"agency": "Department of the Army (the Army, its commands, its portfolio and program offices and its contracting centers)",
                  "queries": ("Army",),
                  "reviewed_re": r"Department of (War|Defense|the Army)\b|\bArmy\b",
                  "names_re": r"\b(Army|ASA\(ALT\)|TACOM|AMCOM|CECOM|DEVCOM|Army Contracting Command|Army Materiel Command)\b",
                  "gao_query": "GAO report Army acquisition program"},
    # army.mil refuses this address, so the speech archive is not read until a hosted-browser route is registered.
    "remarks": {"speeches": None, "testimony": None, "article_re": r"^(?!)",
                "names_re": r"\b(Army|ASA\(ALT\)|Army Contracting Command|Army Materiel Command|Army Futures Command)\b",
                "agency": "Department of the Army (the Army, its commands, its portfolio and program offices and its contracting centers)",
                "testimony_pages": [],
                "conference_query": 'defense conference agenda speakers Army "Program Executive Officer" OR "Army Materiel Command" OR "ASA(ALT)" keynote panel',
                "own_domains": ["army.mil", "dvidshub.net"],
                "providers": {"speech": "army_mil_speeches", "testimony": "house_committee_repository", "statement": "house_committee_repository",
                              "conference": "conference_pages_exa"}},
    "news": {"feeds": [
        {"publisher": "DVIDS", "url": "https://www.dvidshub.net/rss/unit/ACC"},
        {"publisher": "Department of Defense", "url": "https://www.war.gov/News/Contracts/", "index": True}],
        "official_names": {"www.dvidshub.net": "DVIDS", "www.army.mil": "U.S. Army", "www.war.gov": "Department of Defense",
                           "www.defense.gov": "Department of Defense"},
        "standing_terms": ["Army Contracting Command", "Portfolio Acquisition Executive", "Program Executive Office",
                           "Capability Program Executive", "program manager", "acquisition", "contract award"]},
    "protests": {"listing": "https://www.gao.gov/legal/bid-protests/search?agency=Department%20of%20the%20Army&page={page}",
                 "agency": "Department of the Army", "max_pages": 60},
    "budget": {"exhibit": "P-40", "pb_label": "Army", "books_dir": "jbooks_army", "provider": "army_budget_materials"},
    "people": {"department": "agency:army",
               "executive": ("secretary of the army", "assistant secretary", "under secretary", "chief of staff", "commanding general",
                             "portfolio acquisition executive", "program executive", "director"),
               "remarks_providers": None, "staff_listing": None},
    # The Army Materiel Command's acquisition forecast is the forecast; its Command and PM / Directorate columns and the
    # ASA(ALT) chart are the organization memory's sources.
    "forecast": {"pack_glob": "amc_*", "label": "acquisition forecast", "short": "forecast", "providers": {"amc": "amc_acquisition_forecast"}, "memory_tool": "org_memory_army.py",
                 "contract_re": r"W[A-Z0-9]{5}\d{2}[A-Z]\d{4}(?!\d)"},  # Army PIIDs as the forecast writes them, hyphens gone
    "pilot_offices": ("PEO AVIATION", "PEO MS", "JPEO AA", "PEO SOLDIER", "PEO GCS", "CPE C2IN"),
    "coverage_orgs": ["ASA(ALT)", "ACC", "AMC", "PEO AVIATION", "PEO MS", "JPEO AA", "PEO SOLDIER", "PEO GCS", "CPE C2IN"],
    # An Army notice names its office as a PEO, JPEO, CPE, PM or PdM followed by the office's word (PEO Aviation, PM UAS);
    # the Army has no hull designators. A first pattern from the forecast's office names, not yet run against a corpus.
    "reading": {"office_code_re": r"\b(?:J?PEO|CPE|P[dD]M|PM) [A-Z][A-Za-z0-9&()/-]+",
                "hull_re": r"(?!)"},
}

PROFILES = {"navy": NAVY, "darpa": DARPA, "army": ARMY}
if KEY not in PROFILES:
    sys.exit(f"AGENCY={KEY!r} is not a profile; known: {', '.join(sorted(PROFILES))}")
P = PROFILES[KEY]

# Where this agency's artefacts live. The Navy keeps the original folders; another agency gets its own tree.
RESEARCH = ROOT / "research" if KEY == "navy" else ROOT / "research" / "agencies" / KEY
MEMORY, EVENTS, RESULTS, SOURCES = RESEARCH / "memory", RESEARCH / "events", RESEARCH / "results", RESEARCH / "sources"
# The build folder (gitignored) the load and read-back stages write into.
BUILD = ROOT / "build" if KEY == "navy" else ROOT / "build" / KEY
# Shared by every agency: the ledger, the saved bytes, the cassettes.
MANIFEST = ROOT / "research" / "sources" / "documents_manifest.jsonl"
RAW = ROOT / "data" / "raw"
SAM_NOTICES = RAW / P["sam_dir"]
BOOKS = RAW / P["budget"]["books_dir"]
# What a requirement is called: a forecast row where the agency publishes a forecast, else the notices made it.
NEED_ROW = "forecast row" if P["forecast"]["pack_glob"] else "requirement"

# Another agency's tree starts empty; the tools write into it as the Navy tools write into folders
# that already exist, so the folders are made here rather than in each writer.
if KEY != "navy":
    for _folder in (MEMORY, EVENTS, RESULTS, SOURCES):
        _folder.mkdir(parents=True, exist_ok=True)


# The ledger is shared by every layer. A collector running under another profile marks its note with the profile
# key ("oversight watch [darpa]: ..."), and each reader keeps only the notes marked for it: the Navy, the original
# layer, owns the unmarked notes. Without this the DoW OIG reports taken for DARPA would read as Navy reports.
NOTE_TAG = "" if KEY == "navy" else f" [{KEY}]"
_OTHER_TAG = re.compile(r" \[[a-z0-9_]+\]")


def note_mark(note: str) -> str:
    """The profile mark in a note's head (the part before its first colon): "oversight watch [darpa]: ..." and
    "SAM notice detail [darpa] sweep: ..." are marked darpa; an unmarked head is the Navy's."""
    m = _OTHER_TAG.search(note.split(":", 1)[0])
    return m.group(0).strip()[1:-1] if m else ""


def note_is_ours(note: str) -> bool:
    """Whether a ledger row's note was written by a collector running under this profile."""
    return note_mark(note) == (KEY if NOTE_TAG else "")


def note_is_foreign(note: str) -> bool:
    """Whether a ledger row's note is marked for another profile (an unmarked note is nobody's mark)."""
    mark = note_mark(note)
    return bool(mark) and mark != KEY


def compiled(pattern: str, flags: int = 0) -> re.Pattern:
    return re.compile(pattern, flags)


def selfcheck() -> int:
    assert NAVY["fpds_offices"]["N00039"] == "NAVWAR HQ" and NAVY["sam_orgs"]["100076586"] == "N00039"
    assert DARPA["fpds_offices"] == {"HR0011": "DARPA Contracts Management Office"} and DARPA["fpds_funding_agencies"] == {"97AE": "DARPA"}
    assert compiled(NAVY["congress_pattern"]).search("the Secretary of the Navy shall") and not compiled(NAVY["congress_pattern"]).search("DARPA shall")
    assert compiled(DARPA["congress_pattern"]).search("directs DARPA to") and not compiled(DARPA["congress_pattern"]).search("the Navy shall")
    assert not compiled(DARPA["remarks"]["article_re"]).match("https://www.navy.mil/Press-Office/Speeches/display-speech/Article/1/x")
    assert compiled(ARMY["congress_pattern"]).search("directs the Secretary of the Army to") and not compiled(ARMY["congress_pattern"]).search("the Navy shall")
    assert all(compiled(ARMY["topic_re"]).search(c) for c in ("A20-179", "A214-006", "A20B-T018", "A254-P007", "ARM26BX06-NV012"))
    assert not compiled(ARMY["topic_re"]).search("N251-001") and compiled(ARMY["piid_re"]).search("W58RGZ-26-C-0001")
    for key, profile in PROFILES.items():
        assert profile["key"] == key and set(profile) == set(NAVY), key
        assert profile["agency"]["toptier_code"] == "097" and profile["agency"]["node"].startswith("agency:"), key
    assert (ROOT / "research").is_dir()
    print(f"selfcheck ok (profile {KEY}: {P['label']}; artefacts under {RESEARCH.relative_to(ROOT)})")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv else print(KEY, RESEARCH.relative_to(ROOT)))
