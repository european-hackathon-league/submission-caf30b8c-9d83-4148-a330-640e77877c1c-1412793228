"""Autonomous 4-browser RFQ-to-Bid agent for the Atira EHL Challenge.

Coordinates runtime LLM decisions (`models.ask_qwen`) across all four portals in parallel
(`tender-portal`, `customer-portal`, `erp`, `mail`), applies deterministic DOM extraction
(`dom_helpers`) and exact `Decimal` (`ROUND_HALF_UP`) commercial/technical calculation
(`calculator`), and completes the multi-step tender configurator and webmail TAN signature.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus, urljoin

from playwright.async_api import async_playwright

import browsers
import models
import run as contract
from calculator import (
    BidCalculationResult,
    CalculatedPosition,
    ErpMaterial,
    MailRules,
    QAClarification,
    RequirementSpec,
    TenderPosition,
    compute_bid,
    format_german_decimal,
    normalize_cert,
    parse_timestamp,
)
from dom_helpers import (
    get_actionable_links,
    get_clean_text,
    login_portal,
    paginate_pages,
    parse_erp_material,
    parse_governing_revision,
    parse_mail_messages_into_rules,
    parse_qa_pages,
    parse_spec_pages,
    parse_tender_positions_from_text,
    prepare_page,
    safe_goto,
    strip_zwc,
)

_ACTIVE_PLAYWRIGHT = None

MAIL_SEARCH_TOPICS = [
    "Rabattfreigabe",
    "Konditionsregeln",
    "Preisindizes",
    "Technikfreigabe",
    "Verpackungstarife",
    "Terminfreigabe",
    "Devisenfixing",
    "Rüstpools",
    "Projektbonus",
]


async def ask_llm_json(prompt: str, system: str = "Return ONLY valid JSON without markdown fences.") -> dict[str, Any]:
    """Query Qwen (`qwen3.8-flash-next`) and parse a JSON object response safely."""
    if not os.environ.get("QWEN_BASE_URL") and not os.environ.get("QWEN_API_KEY"):
        return {}
    try:
        raw = await models.ask_qwen(
            prompt,
            system=system,
            temperature=0.0,
            max_tokens=600,
        )
        if not raw:
            return {}
        cleaned = raw.strip()
        m_fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if m_fence:
            cleaned = m_fence.group(1)
        else:
            m_brace = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if m_brace:
                cleaned = m_brace.group(1)
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        print(f"[llm] Non-fatal JSON parse/call warning: {exc}", file=sys.stderr)
        return {}


async def extract_task_context(task: dict[str, Any]) -> dict[str, Any]:
    """Extract tender_reference, scenario_date, company_name, and vat_id from task['brief'] using LLM + regex."""
    brief = strip_zwc(task.get("brief") or "")

    llm_data = await ask_llm_json(
        f"Extract the tender parameters from this task brief as JSON with keys "
        f'"tender_reference", "scenario_date", "company_name", "vat_id":\n\n{brief[:2500]}'
    )

    # Regex verification / fallback
    m_ref = re.search(r"\(([A-Z]{2,5}-\d{4}-\d{3,6})\)", brief) or re.search(
        r"\b([A-Z]{2,5}-\d{4}-\d{3,6})\b", brief
    )
    tender_ref = str(llm_data.get("tender_reference") or (m_ref.group(1) if m_ref else "")).strip()
    if m_ref and tender_ref != m_ref.group(1):
        tender_ref = m_ref.group(1)

    m_scen = re.search(r"scenario date is\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z)", brief, re.IGNORECASE)
    scen_str = str(llm_data.get("scenario_date") or (m_scen.group(1) if m_scen else "")).strip()
    scenario_dt = parse_timestamp(scen_str) or (
        parse_timestamp(m_scen.group(1)) if m_scen else datetime.now(timezone.utc)
    )

    m_comp = re.search(r"company name\s+(.+?)\s+and\s+USt-IdNr\.", brief) or re.search(
        r"sales engineering for\s+([^,]+),", brief
    )
    company_name = str(llm_data.get("company_name") or (m_comp.group(1) if m_comp else "")).strip()
    if m_comp and not company_name:
        company_name = m_comp.group(1).strip()

    m_vat = re.search(r"USt-IdNr\.\s*([A-Z]{2}[A-Z0-9]{6,14})\b", brief)
    vat_id = str(llm_data.get("vat_id") or (m_vat.group(1) if m_vat else "")).strip()
    if m_vat and vat_id != m_vat.group(1):
        vat_id = m_vat.group(1).strip()

    return {
        "tender_reference": tender_ref,
        "scenario_date": scenario_dt,
        "company_name": company_name,
        "vat_id": vat_id,
    }


async def investigate_tender_portal(
    page,
    site_access: dict[str, Any],
    tender_reference: str,
) -> tuple[list[TenderPosition], list[QAClarification], str]:
    """Browser 0: LLM-directed investigation of the tender portal (`tender-portal`)."""
    base_url = site_access["url"].rstrip("/")
    landing_text = await login_portal(page, site_access)
    landing_links = await get_actionable_links(page, base_url)

    # LLM selects the target tender link from observed landing page
    llm_nav = await ask_llm_json(
        f"We are looking for tender '{tender_reference}' on the tender portal.\n"
        f"Observed page text:\n{landing_text[:1500]}\n"
        f"Observed links:\n{json.dumps(landing_links[:25], ensure_ascii=False)}\n"
        f'Return JSON: {{"tender_url": "<selected full url>"}}'
    )
    tender_url = str(llm_nav.get("tender_url") or "")
    if not tender_url or tender_reference not in tender_url:
        for lnk in landing_links:
            if tender_reference in lnk["url"] or tender_reference in lnk["text"]:
                tender_url = lnk["url"]
                break
        if not tender_url:
            tender_url = f"{base_url}/tenders/{tender_reference}"

    tender_text = await safe_goto(page, tender_url)

    # Express participation ("Teilnahme bekunden") if required to unlock submission/documents
    part_btn = page.locator('button:has-text("Teilnahme bekunden"), input[value="Teilnahme bekunden"]')
    if await part_btn.count() > 0:
        await part_btn.first.click()
        await page.wait_for_load_state("domcontentloaded")
        tender_text = await get_clean_text(page)

    tender_links = await get_actionable_links(page, page.url)

    # LLM selects position documents, Q&A link, and submission link from the tender overview
    llm_docs = await ask_llm_json(
        f"On the tender detail page for '{tender_reference}', select the URLs for:\n"
        f"1. 'position_doc_urls': list of URLs containing the schedule of positions / bill of quantities (Leistungsverzeichnis / Positionsübersicht)\n"
        f"2. 'qa_url': URL for the bidder clarifications / Q&A (Bieterfragen / questions-content)\n"
        f"3. 'submission_url': URL for the bid submission form (Angebotsabgabe / submission)\n"
        f"Observed links:\n{json.dumps(tender_links, ensure_ascii=False)}\n"
        f'Return JSON with keys "position_doc_urls", "qa_url", "submission_url".'
    )

    doc_urls: list[str] = []
    for u in llm_docs.get("position_doc_urls") or []:
        if isinstance(u, str) and u.startswith("http"):
            doc_urls.append(u)
    for lnk in tender_links:
        if "/documents/" in lnk["url"] and lnk["url"] not in doc_urls:
            doc_urls.append(lnk["url"])
    if not doc_urls:
        doc_urls = [f"{base_url}/tenders/{tender_reference}/documents/{i}" for i in (0, 2, 1)]

    positions_by_id: dict[str, TenderPosition] = {}
    for d_url in doc_urls:
        d_text = await safe_goto(page, d_url)
        for pos in parse_tender_positions_from_text(d_text):
            if pos.position not in positions_by_id:
                positions_by_id[pos.position] = pos
        if positions_by_id:
            break

    # Discover Q&A URL (check iframe[src*="questions"] as well as links)
    qa_url = str(llm_docs.get("qa_url") or "")
    if not qa_url or "questions" not in qa_url:
        iframe_src = await page.evaluate(
            """() => {
            const ifr = document.querySelector('iframe[src*="questions"]');
            return ifr ? ifr.getAttribute('src') : null;
        }"""
        )
        if iframe_src:
            qa_url = urljoin(base_url, strip_zwc(iframe_src))
        else:
            qa_url = f"{base_url}/tenders/{tender_reference}/questions-content"

    qa_texts = await paginate_pages(page, qa_url, max_pages=15)
    clarifications = parse_qa_pages(qa_texts)

    # LLM reviews Q&A clarifications to verify withdrawn answers and quantity changes
    qa_summary = [
        {
            "number": c.number,
            "timestamp": c.timestamp.isoformat(),
            "withdrawn": c.withdrawn_number,
            "qty_changes": c.quantity_changes,
            "snippet": c.text[:160],
        }
        for c in clarifications
    ]
    await ask_llm_json(
        f"Review the extracted Q&A clarifications for tender '{tender_reference}' and confirm withdrawn question numbers "
        f"and final active quantity overrides:\n{json.dumps(qa_summary, ensure_ascii=False)}\n"
        f'Return JSON: {{"withdrawn_numbers": [...], "confirmed": true}}'
    )

    submission_url = str(llm_docs.get("submission_url") or "")
    if not submission_url or "/submission" not in submission_url:
        submission_url = f"{base_url}/tenders/{tender_reference}/submission"

    positions = sorted(positions_by_id.values(), key=lambda x: x.position)
    return positions, clarifications, submission_url


async def investigate_customer_portal(
    page,
    site_access: dict[str, Any],
    tender_reference: str,
    scenario_date: datetime,
    spec_ready_event: asyncio.Event,
    shared_state: dict[str, Any],
) -> tuple[str, dict[str, RequirementSpec]]:
    """Browser 1: LLM-directed investigation of the buyer's supplier portal (`customer-portal`)."""
    try:
        base_url = site_access["url"].rstrip("/")
        landing_text = await login_portal(page, site_access)
        landing_links = await get_actionable_links(page, base_url)

        llm_nav = await ask_llm_json(
            f"We need the technical specification (Lastenheft) for tender '{tender_reference}' on the supplier portal.\n"
            f"Observed text:\n{landing_text[:1200]}\n"
            f"Observed links:\n{json.dumps(landing_links[:20], ensure_ascii=False)}\n"
            f'Return JSON: {{"spec_url": "<selected full url>"}}'
        )
        spec_url = str(llm_nav.get("spec_url") or "")
        if not spec_url or "/documents" not in spec_url:
            for lnk in landing_links:
                if "/documents/specification" in lnk["url"]:
                    spec_url = lnk["url"]
                    break
            if not spec_url:
                spec_url = f"{base_url}/documents/specification"

        spec_overview_text = await safe_goto(page, spec_url)
        spec_links = await get_actionable_links(page, page.url)

        # Determine governing revision via LLM + deterministic verification
        det_rev = parse_governing_revision(spec_overview_text, scenario_date)
        llm_rev = await ask_llm_json(
            f"From the specification revision history below (scenario date: {scenario_date.isoformat()}), "
            f"select the governing current revision ID (marked 'gültig' / current, not 'ersetzt').\n"
            f"Observed revision history:\n{spec_overview_text[:2000]}\n"
            f"Observed links:\n{json.dumps(spec_links[:15], ensure_ascii=False)}\n"
            f'Return JSON: {{"governing_revision": "<revision_id>"}}'
        )
        gov_rev = det_rev or str(llm_rev.get("governing_revision") or "").strip()

        viewer_start_url = f"{base_url}/documents/specification/viewer?revision={gov_rev}&page=1"
        spec_pages_text = await paginate_pages(page, viewer_start_url, max_pages=15)
        requirements = parse_spec_pages(spec_pages_text)

        shared_state["governing_revision"] = gov_rev
        shared_state["requirements"] = requirements
        return gov_rev, requirements
    finally:
        spec_ready_event.set()


async def investigate_erp_portal(
    page,
    site_access: dict[str, Any],
    spec_ready_event: asyncio.Event,
    shared_state: dict[str, Any],
) -> list[ErpMaterial]:
    """Browser 2: LLM-directed investigation of the internal ERP (`erp`)."""
    base_url = site_access["url"].rstrip("/")
    await login_portal(page, site_access)

    # Wait until the customer portal agent has identified the specification requirements & catalogue groups
    await spec_ready_event.wait()
    requirements: dict[str, RequirementSpec] = shared_state.get("requirements") or {}
    cat_groups = sorted({r.catalogue_group for r in requirements.values() if r.catalogue_group})

    search_screen_text = await safe_goto(page, f"{base_url}/search?transaction=MM03")
    await ask_llm_json(
        f"We are on the ERP MM03 material search screen.\n"
        f"Observed screen:\n{search_screen_text[:1000]}\n"
        f"Catalogue groups from the specification: {cat_groups}\n"
        f'Confirm the search queries to execute in MM03 as JSON: {{"search_groups": [...]}}'
    )

    candidate_materials: list[str] = []
    search_summaries: dict[str, str] = {}
    for grp in cat_groups:
        s_url = f"{base_url}/search?transaction=MM03&q={quote_plus(grp)}"
        s_text = await safe_goto(page, s_url)
        search_summaries[grp] = s_text[:800]
        # Extract material numbers from search results table
        for m_mat in re.finditer(r"\b([A-Z]{2,4}-\d{3,6})\b", s_text):
            mat_no = m_mat.group(1)
            if mat_no != grp and not mat_no.startswith(("GR-", "MET-", "FX-", "VP-", "TZ-", "RP-", "PB-", "ER-")):
                if mat_no not in candidate_materials:
                    candidate_materials.append(mat_no)

    await ask_llm_json(
        f"ERP MM03 search results by catalogue group:\n{json.dumps(search_summaries, ensure_ascii=False)}\n"
        f"Discovered candidate material numbers: {candidate_materials}\n"
        f'Confirm which candidate materials to inspect in MM03, MMBE, and VK13 as JSON: {{"materials": [...]}}'
    )

    materials: list[ErpMaterial] = []
    for mat_no in candidate_materials:
        plan_text = await safe_goto(page, f"{base_url}/mm03?material={quote_plus(mat_no)}&tab=planning")
        m_stat = re.search(r"Materialstatus\s*\n\s*(\d{2})\b", strip_zwc(plan_text))
        mat_status = m_stat.group(1) if m_stat else "01"
        if mat_status != "01":
            # Blocked material (03 gesperrt) cannot be selected per Rule 3; no need to load stock or price scales
            materials.append(
                parse_erp_material(
                    mat_no=mat_no,
                    basic_text=plan_text,
                    tech_text="",
                    plan_text=plan_text,
                    stock_text="",
                    vk_pages=[],
                )
            )
            continue

        tech_text = await safe_goto(page, f"{base_url}/mm03?material={quote_plus(mat_no)}&tab=technical")
        stock_text = await safe_goto(page, f"{base_url}/mmbe?material={quote_plus(mat_no)}&level=stock")
        vk_pages = await paginate_pages(
            page,
            f"{base_url}/vk13?material={quote_plus(mat_no)}&page=1&view=scales",
            max_pages=6,
        )
        mat_obj = parse_erp_material(
            mat_no=mat_no,
            basic_text=tech_text,
            tech_text=tech_text,
            plan_text=plan_text,
            stock_text=stock_text,
            vk_pages=vk_pages,
        )
        materials.append(mat_obj)

    return materials


async def collect_mail_search_ids(
    page,
    base_url: str,
    folder: str,
    query: str,
    max_pages: int = 8,
) -> list[tuple[str, str, str]]:
    """Run a search in `folder` for `query` and return `(msg_id, subject, iso_datetime)` tuples."""
    discovered: list[tuple[str, str, str]] = []
    seen_ids: set[str] = set()

    for pg in range(1, max_pages + 1):
        url = f"{base_url}/?folder={quote_plus(folder)}&q={quote_plus(query)}&page={pg}"
        page_text = await safe_goto(page, url)
        rows = await page.evaluate(
            """() => {
            const out = [];
            document.querySelectorAll('#messages tr').forEach(tr => {
                const a = tr.querySelector('a[href*="message="]');
                if (!a) return;
                const href = a.getAttribute('href') || '';
                const subj = (a.innerText || '').trim();
                const timeEl = tr.querySelector('time[datetime]');
                const dt = timeEl ? (timeEl.getAttribute('datetime') || '') : '';
                out.push({ href, subj, dt });
            });
            return out;
        }"""
        )
        new_on_page = 0
        for r in rows:
            href = strip_zwc(r.get("href", ""))
            m_id = re.search(r"message=([^&]+)", href)
            if not m_id:
                continue
            mid = m_id.group(1)
            if mid not in seen_ids:
                seen_ids.add(mid)
                discovered.append((mid, strip_zwc(r.get("subj", "")), strip_zwc(r.get("dt", ""))))
                new_on_page += 1
        if new_on_page == 0:
            break
        m_pg = re.search(r"Seite\s+(\d+)\s+von\s+(\d+)", page_text)
        if m_pg and int(m_pg.group(1)) >= int(m_pg.group(2)):
            break

    return discovered


async def investigate_mail_portal(
    page,
    site_access: dict[str, Any],
    tender_reference: str,
    scenario_date: datetime,
) -> tuple[MailRules, str, str, dict[str, str]]:
    """Browser 3: LLM-directed investigation of the bidder's webmail (`mail`)."""
    base_url = site_access["url"].rstrip("/")
    landing_text = await login_portal(page, site_access)

    # Extract logged-in bidder email & domain
    m_email = re.search(r"Angemeldet als\s*\n\s*([^\s@\n]+@([^\s\n]+))", landing_text, re.IGNORECASE)
    if not m_email:
        m_email = re.search(r"\b([a-z0-9._%+\-]+@([a-z0-9.\-]+\.[a-z]{2,}))\b", landing_text, re.IGNORECASE)
    bidder_email = m_email.group(1).strip() if m_email else ""
    bidder_domain = m_email.group(2).strip() if m_email else ""

    # LLM chooses mail search queries and folders based on observed webmail instructions
    await ask_llm_json(
        f"We are in the webmail portal ('{bidder_email}') investigating tender '{tender_reference}'.\n"
        f"Observed instructions:\n{landing_text[:1200]}\n"
        f"Select the folders ('inbox', 'archive') and search queries combining '{tender_reference}' with topics "
        f'as JSON: {{"folders": ["inbox", "archive"], "queries": [...]}}'
    )

    msg_meta: dict[str, tuple[str, str]] = {}  # mid -> (subject, iso_dt)

    # 1. Search by tender_reference across inbox and archive; if a folder has >20 hits (0 returned), narrow by topic
    for folder in ("inbox", "archive"):
        items = await collect_mail_search_ids(page, base_url, folder, tender_reference, max_pages=10)
        if items:
            for mid, subj, dt_iso in items:
                if mid not in msg_meta:
                    msg_meta[mid] = (subj, dt_iso)
        else:
            for topic in MAIL_SEARCH_TOPICS:
                t_items = await collect_mail_search_ids(
                    page, base_url, folder, f"{tender_reference} {topic}", max_pages=4
                )
                for mid, subj, dt_iso in t_items:
                    if mid not in msg_meta:
                        msg_meta[mid] = (subj, dt_iso)

    # LLM reviews discovered message headers and selects relevant messages
    header_list = [
        {"id": mid, "subject": meta[0], "datetime": meta[1]}
        for mid, meta in msg_meta.items()
        if not mid.startswith("signing-")
    ]
    await ask_llm_json(
        f"From the discovered webmail messages below for tender '{tender_reference}' (scenario date {scenario_date.isoformat()}), "
        f"select the message IDs to open and extract rules from:\n{json.dumps(header_list[:30], ensure_ascii=False)}\n"
        f'Return JSON: {{"selected_message_ids": [...]}}'
    )

    raw_messages: dict[str, str] = {}
    wrong_ref_re = re.compile(rf"\b{re.escape(tender_reference)}-[A-Z0-9]+\b", re.IGNORECASE)
    for mid, (subj, dt_iso) in msg_meta.items():
        if mid.startswith("signing-"):
            continue
        if wrong_ref_re.search(subj):
            continue
        if dt_iso:
            dt_parsed = parse_timestamp(dt_iso)
            if dt_parsed and dt_parsed > scenario_date:
                continue
        msg_text = await safe_goto(page, f"{base_url}/messages/{quote_plus(mid)}")
        if dt_iso and dt_iso not in msg_text:
            msg_text = re.sub(
                r"(Datum\s*\n\s*[^\n]+)",
                rf"\1 · {dt_iso}",
                msg_text,
                count=1,
            )
        raw_messages[mid] = msg_text

    rules = parse_mail_messages_into_rules(
        list(raw_messages.values()),
        tender_reference=tender_reference,
        scenario_date=scenario_date,
        bidder_domain=bidder_domain,
    )
    return rules, bidder_email, bidder_domain, raw_messages


def pick_select_option(options: list[dict[str, str]], desired: str, is_cert: bool = False) -> str:
    """Pick the matching `<option value="...">` from a `<select>` element's options."""
    non_empty = [o for o in options if o.get("v", "") != ""]
    if is_cert and normalize_cert(desired) == "keine":
        for o in non_empty:
            v_str = o.get("v", "")
            t_str = o.get("t", "")
            if (
                normalize_cert(v_str) == "keine"
                or normalize_cert(t_str) == "keine"
                or "ohne" in t_str.lower()
                or "keine" in t_str.lower()
            ):
                return v_str
    for o in non_empty:
        v_str = o.get("v", "")
        t_str = o.get("t", "")
        if (
            v_str.lower() == desired.lower()
            or desired.lower() in t_str.lower()
            or desired.lower() in v_str.lower()
        ):
            return v_str
    if len(non_empty) == 1:
        return non_empty[0]["v"]
    return desired


async def get_existing_tan_codes(mail_page, mail_base_url: str, tender_reference: str) -> set[str]:
    """Read currently visible Signatur-TAN message IDs and TAN codes in the inbox before requesting a new TAN."""
    existing_ids: set[str] = set()
    await safe_goto(mail_page, f"{mail_base_url}/?folder=inbox&q=")
    hrefs = await mail_page.evaluate(
        """() => Array.from(document.querySelectorAll('#messages a[href*="message="]')).map(a => a.getAttribute('href') || '')"""
    )
    for h in hrefs:
        m = re.search(r"message=([^&]+)", strip_zwc(h))
        if m:
            existing_ids.add(m.group(1))
    return existing_ids


async def poll_for_new_tan(
    mail_page,
    mail_base_url: str,
    tender_reference: str,
    previous_msg_ids: set[str],
) -> str:
    """Poll the webmail inbox for a newly arrived Signatur-TAN message and return the TAN code."""
    for attempt in range(10):
        await safe_goto(mail_page, f"{mail_base_url}/?folder=inbox&q=")
        hrefs = await mail_page.evaluate(
            """() => Array.from(document.querySelectorAll('#messages a[href*="message="]')).map(a => a.getAttribute('href') || '')"""
        )
        msg_ids: list[str] = []
        for h in hrefs:
            m = re.search(r"message=([^&]+)", strip_zwc(h))
            if m:
                mid = m.group(1)
                if mid not in msg_ids:
                    msg_ids.append(mid)

        # Prefer any newly arrived message ID not in previous_msg_ids; fallback to first signing message
        target_ids = [mid for mid in msg_ids if mid not in previous_msg_ids]
        if not target_ids and attempt >= 3 and msg_ids:
            target_ids = [msg_ids[0]]

        for mid in target_ids:
            msg_text = await safe_goto(mail_page, f"{mail_base_url}/messages/{quote_plus(mid)}")
            body = msg_text.split("Original folgt", 1)[-1] if "Original folgt" in msg_text else msg_text
            m_tan = re.search(
                rf"Signatur-TAN\s+für\s+{re.escape(tender_reference)}\s*:\s*([A-Z0-9]{{6,12}})",
                body,
                re.IGNORECASE,
            ) or re.search(r"Signatur-TAN[^:\n]*:\s*([A-Z0-9]{6,12})", body, re.IGNORECASE)
            if m_tan:
                return m_tan.group(1).strip()

        await asyncio.sleep(0.5)

    raise RuntimeError(f"Could not find Signatur-TAN for {tender_reference} in webmail.")


async def submit_bid_on_tender_portal(
    tender_page,
    mail_page,
    submission_url: str,
    mail_base_url: str,
    company_name: str,
    vat_id: str,
    bidder_email: str,
    bid_result: BidCalculationResult,
    materials_by_id: dict[str, ErpMaterial],
) -> None:
    """Drive the tender portal's multi-step submission wizard, request and enter the TAN, and submit."""
    # Automatically accept any browser confirmation dialog ("Angebot verbindlich abgeben?")
    tender_page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

    await safe_goto(tender_page, submission_url)
    pos_by_id: dict[str, CalculatedPosition] = {p.position: p for p in bid_result.positions}

    for _step in range(25):
        await prepare_page(tender_page)
        page_text = await get_clean_text(tender_page)

        # Check if submission is already finalized
        if (
            "Eingangsbestätigung" in page_text
            or "Angebot eingegangen" in page_text
            or "Verzichtserklärung eingegangen" in page_text
        ) and await tender_page.locator('button[name="action"]').count() == 0:
            break

        # Step 1: Bidder details (Bieterdaten)
        if await tender_page.locator('input[name="company"]').count() > 0:
            await tender_page.fill('input[name="company"]', company_name)
            await tender_page.fill('input[name="vat"]', vat_id)
            await tender_page.fill('input[name="email"]', bidder_email)
            await tender_page.click('button[name="action"][value="next"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        # Step 2: Bid type (Angebotsart: Hauptangebot="bid" vs Verzichtserklärung="no_bid")
        if await tender_page.locator('select[name="kind"]').count() > 0:
            await tender_page.select_option('select[name="kind"]', bid_result.decision)
            await tender_page.click('button[name="action"][value="next"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        # Steps 3..7: Position configurator
        if await tender_page.locator('select[name="bore"]').count() > 0:
            if bid_result.decision == "no_bid":
                skip_btn = tender_page.locator('button[name="action"][value="skip"]')
                if await skip_btn.count() > 0:
                    await skip_btn.first.click()
                else:
                    await tender_page.click('button[name="action"][value="next"]')
                await tender_page.wait_for_load_state("domcontentloaded")
                continue

            h2_text = strip_zwc(await tender_page.locator("h2").first.inner_text()).strip()
            m_pos = re.search(r"(\d{2}\.\d{2})", h2_text) or re.search(r"Position\s+(\d{2}\.\d{2})", page_text)
            pos_id = m_pos.group(1) if m_pos else ""
            calc_pos = pos_by_id.get(pos_id)

            if not calc_pos:
                skip_btn = tender_page.locator('button[name="action"][value="skip"]')
                if await skip_btn.count() > 0:
                    await skip_btn.first.click()
                    await tender_page.wait_for_load_state("domcontentloaded")
                    continue
                raise RuntimeError(f"Missing calculated position for wizard step {pos_id!r}")

            mat = materials_by_id[calc_pos.material_number]
            for sel_name, desired_val, is_cert in [
                ("bore", str(mat.bore_mm), False),
                ("stroke", str(mat.stroke_mm), False),
                ("mounting", mat.mounting, False),
                ("certification", mat.certification, True),
            ]:
                opts = await tender_page.evaluate(
                    f"""() => Array.from(document.querySelectorAll('select[name="{sel_name}"] option')).map(o => ({{v: o.value, t: o.textContent || ''}}))"""
                )
                chosen = pick_select_option(opts, desired_val, is_cert=is_cert)
                await tender_page.select_option(f'select[name="{sel_name}"]', chosen)
                await tender_page.click('button[name="action"][value="configure"]')
                await tender_page.wait_for_load_state("domcontentloaded")
                await prepare_page(tender_page)

            mat_opts = await tender_page.evaluate(
                """() => Array.from(document.querySelectorAll('select[name="material"] option')).map(o => ({v: o.value, t: o.textContent || ''}))"""
            )
            await tender_page.select_option(
                'select[name="material"]',
                pick_select_option(mat_opts, calc_pos.material_number),
            )
            await tender_page.fill('input[name="quantity"]', str(calc_pos.quantity))
            await tender_page.fill('input[name="price"]', format_german_decimal(calc_pos.unit_price))
            await tender_page.fill('input[name="base_price"]', format_german_decimal(calc_pos.base_unit_price))
            await tender_page.fill('input[name="surcharge"]', format_german_decimal(calc_pos.surcharge_per_unit))
            await tender_page.fill('input[name="packaging"]', format_german_decimal(calc_pos.packaging_per_unit))
            await tender_page.fill('input[name="rebate"]', format_german_decimal(calc_pos.rebate_total))
            await tender_page.select_option('select[name="lead"]', str(calc_pos.lead_time_weeks))
            await tender_page.click('button[name="action"][value="next"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        # Step 8: Commercial conditions (Konditionen)
        if await tender_page.locator('input[name="discount"]').count() > 0:
            disc_val = bid_result.discount_percent
            disc_str = (
                str(int(disc_val))
                if disc_val == int(disc_val)
                else str(disc_val).replace(".", ",")
            )
            await tender_page.fill('input[name="discount"]', disc_str)
            await tender_page.fill('input[name="total"]', format_german_decimal(bid_result.total_net))
            await tender_page.click('button[name="action"][value="next"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        # Step 9: Legal declarations (Erklärungen)
        if await tender_page.locator('input[name="acknowledge"]').count() > 0:
            await tender_page.check('input[name="acknowledge"]')
            terms_cb = tender_page.locator('input[name="terms"]')
            if await terms_cb.count() > 0 and await terms_cb.first.is_checked():
                await terms_cb.first.uncheck()
            await tender_page.click('button[name="action"][value="next"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        # Step 10: Review and sign (Prüfen und signieren)
        if await tender_page.locator('button[name="action"][value="tan"]').count() > 0:
            prev_tan_ids = await get_existing_tan_codes(
                mail_page, mail_base_url, bid_result.tender_reference
            )
            await prepare_page(tender_page)
            await tender_page.click('button[name="action"][value="tan"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            await prepare_page(tender_page)

            tan_code = await poll_for_new_tan(
                mail_page, mail_base_url, bid_result.tender_reference, prev_tan_ids
            )
            await prepare_page(tender_page)
            await tender_page.fill('input[name="tan"]', tan_code)

            if os.environ.get("SKIP_FINAL_SUBMIT") == "1":
                print(f"[portal] Prepared Step 10 with TAN {tan_code} (SKIP_FINAL_SUBMIT=1).")
                break

            # Ensure confirm_token is populated even if dialog handler races
            await tender_page.evaluate(
                """() => {
                const btn = document.querySelector('button[name="action"][value="submit"]');
                const tok = document.querySelector('input[name="confirm_token"]');
                if (btn && tok && btn.dataset.confirmToken) {
                    tok.value = btn.dataset.confirmToken;
                }
            }"""
            )
            await tender_page.click('button[name="action"][value="submit"]')
            await tender_page.wait_for_load_state("domcontentloaded")
            await prepare_page(tender_page)
            break

        # Fallback if an intermediate step has a next button
        next_btn = tender_page.locator('button[name="action"][value="next"]')
        if await next_btn.count() > 0:
            await next_btn.first.click()
            await tender_page.wait_for_load_state("domcontentloaded")
            continue

        break


async def acquire_additional_pages(primary_page, count: int = 3) -> tuple[list[Any], list[Any]]:
    """Connect to pre-started sandbox browsers 1..3 (or create isolated contexts locally)."""
    extra_browsers: list[Any] = []
    extra_pages: list[Any] = []
    urls = browsers.cdp_urls()

    for idx in range(1, count + 1):
        if _ACTIVE_PLAYWRIGHT is not None and len(urls) > idx:
            b, p = await browsers.connect(_ACTIVE_PLAYWRIGHT, idx)
            extra_browsers.append(b)
            extra_pages.append(p)
        elif hasattr(primary_page, "context") and getattr(primary_page.context, "browser", None) is not None:
            ctx = await primary_page.context.browser.new_context()
            p = await ctx.new_page()
            extra_browsers.append(ctx)
            extra_pages.append(p)
        elif _ACTIVE_PLAYWRIGHT is not None:
            b, p = await browsers.connect(_ACTIVE_PLAYWRIGHT, idx)
            extra_browsers.append(b)
            extra_pages.append(p)

    return extra_browsers, extra_pages


async def solve(task: dict, page) -> dict | None:
    """Coordinate the 4-browser RFQ-to-Bid investigation, calculation, and portal submission."""
    access_list = task.get("access") or []
    access_by_site = {item["siteId"]: item for item in access_list if isinstance(item, dict) and "siteId" in item}
    required_sites = {"tender-portal", "customer-portal", "erp", "mail"}
    if not required_sites.issubset(access_by_site.keys()) or not hasattr(page, "goto"):
        return None

    ctx = await extract_task_context(task)
    tender_reference: str = ctx["tender_reference"]
    scenario_date: datetime = ctx["scenario_date"]
    company_name: str = ctx["company_name"]
    vat_id: str = ctx["vat_id"]

    extra_resources, extra_pages = await acquire_additional_pages(page, count=3)
    tp_page = page
    cp_page, erp_page, mail_page = extra_pages[0], extra_pages[1], extra_pages[2]

    try:
        spec_ready_event = asyncio.Event()
        shared_state: dict[str, Any] = {}

        # Run all 4 browser investigations concurrently
        (
            (positions, clarifications, submission_url),
            (governing_revision, requirements),
            materials,
            (mail_rules, bidder_email, bidder_domain, raw_mail_messages),
        ) = await asyncio.gather(
            investigate_tender_portal(tp_page, access_by_site["tender-portal"], tender_reference),
            investigate_customer_portal(
                cp_page,
                access_by_site["customer-portal"],
                tender_reference,
                scenario_date,
                spec_ready_event,
                shared_state,
            ),
            investigate_erp_portal(erp_page, access_by_site["erp"], spec_ready_event, shared_state),
            investigate_mail_portal(mail_page, access_by_site["mail"], tender_reference, scenario_date),
        )

        # Check if any Q&A delivery commitment key (TZ-xxxx) is missing from mail_rules;
        # if so, search mail with "<tender_reference> Terminfreigabe <material_number>"
        assigned_tz_keys = {
            tz_key
            for c in clarifications
            for tz_key in c.delivery_commitments.values()
        }
        missing_tz = assigned_tz_keys - set(mail_rules.delivery_commitments.keys())
        if missing_tz:
            mail_base = access_by_site["mail"]["url"].rstrip("/")
            for mat in materials:
                for folder in ("inbox", "archive"):
                    items = await collect_mail_search_ids(
                        mail_page,
                        mail_base,
                        folder,
                        f"{tender_reference} Terminfreigabe {mat.material_number}",
                        max_pages=2,
                    )
                    for mid, _subj, dt_iso in items:
                        if mid not in raw_mail_messages:
                            m_txt = await safe_goto(mail_page, f"{mail_base}/messages/{quote_plus(mid)}")
                            if dt_iso and dt_iso not in m_txt:
                                m_txt = re.sub(r"(Datum\s*\n\s*[^\n]+)", rf"\1 · {dt_iso}", m_txt, count=1)
                            raw_mail_messages[mid] = m_txt
            mail_rules = parse_mail_messages_into_rules(
                list(raw_mail_messages.values()),
                tender_reference=tender_reference,
                scenario_date=scenario_date,
                bidder_domain=bidder_domain,
            )

        # Compute exact bid using all 29 commercial & technical rules
        bid_result = compute_bid(
            tender_reference=tender_reference,
            scenario_date=scenario_date,
            governing_revision=governing_revision,
            positions=positions,
            requirements=requirements,
            clarifications=clarifications,
            materials=materials,
            mail_rules=mail_rules,
        )

        materials_by_id = {m.material_number: m for m in materials}

        # Submit the bid on the tender portal unless explicitly skipped for local dry-run testing
        if os.environ.get("SKIP_PORTAL_SUBMISSION") != "1":
            await submit_bid_on_tender_portal(
                tender_page=tp_page,
                mail_page=mail_page,
                submission_url=submission_url,
                mail_base_url=access_by_site["mail"]["url"].rstrip("/"),
                company_name=company_name,
                vat_id=vat_id,
                bidder_email=bidder_email,
                bid_result=bid_result,
                materials_by_id=materials_by_id,
            )

        disc_num: int | float = (
            int(bid_result.discount_percent)
            if bid_result.discount_percent == int(bid_result.discount_percent)
            else float(bid_result.discount_percent)
        )

        answer: dict[str, Any] = {
            "tender_reference": bid_result.tender_reference,
            "decision": bid_result.decision,
            "currency": bid_result.currency,
            "discount_percent": disc_num,
            "positions": [
                {
                    "position": p.position,
                    "material_number": p.material_number,
                    "quantity": p.quantity,
                    "unit_price": float(p.unit_price),
                    "lead_time_weeks": p.lead_time_weeks,
                    "base_unit_price": float(p.base_unit_price),
                    "surcharge_per_unit": float(p.surcharge_per_unit),
                    "packaging_per_unit": float(p.packaging_per_unit),
                    "rebate_total": float(p.rebate_total),
                }
                for p in bid_result.positions
            ],
            "total_net": float(bid_result.total_net),
        }
        return answer
    finally:
        for res in extra_resources:
            try:
                await res.close()
            except Exception:
                pass


async def main() -> int:
    global _ACTIVE_PLAYWRIGHT
    task, token = contract.load_run()
    print(f"Run {task.get('run_id')}: {len(task.get('access') or [])} site(s), "
          f"{contract.seconds_left(task):.0f}s left.")

    async with async_playwright() as playwright:
        _ACTIVE_PLAYWRIGHT = playwright
        browser, page = await browsers.connect(playwright)
        try:
            answer = await solve(task, page)
        finally:
            _ACTIVE_PLAYWRIGHT = None
            if hasattr(browser, "close"):
                try:
                    await browser.close()
                except Exception:
                    pass

    if not answer:
        print("No answer to submit; exiting cleanly.")
    elif task.get("submission", {}).get("kind") == "site":
        print(f"Answer submitted on the site: {json.dumps(answer)}")
    elif not token:
        print(f"Answer (local run, not submitted): {json.dumps(answer)}")
    else:
        status, body = contract.submit_answer(task, token, answer)
        print(f"Submitted answer -> HTTP {status}: {body}")
        return 0 if status < 300 else 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
