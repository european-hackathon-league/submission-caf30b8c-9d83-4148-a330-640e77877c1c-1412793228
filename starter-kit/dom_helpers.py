"""Resilient DOM sanitization, gate unlocking, and structured page extraction helpers.

Handles adversarial portal elements (zero-width characters, timed modal <dialog> overlays, decoy triplet
links, range+checkbox gates, canvas aria-label receipts/values, CSS-hidden [role=tooltip] elements, and
transient /notice error pages) without hardcoding any scenario-specific values.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

from calculator import (
    BonusBand,
    DeliveryCommitmentRule,
    ErpMaterial,
    MailRules,
    PriceCondition,
    QAClarification,
    RequirementSpec,
    TenderPosition,
    ZERO,
    parse_locale_decimal,
    parse_timestamp,
)

ZWC_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")
DECOY_HREF_PATTERNS = ("/portal-survey", "/tools", "/documents/supplier-guide", "/logout")


def strip_zwc(text: str | None) -> str:
    if not text:
        return ""
    return ZWC_RE.sub("", str(text))


PREPARE_PAGE_JS = """
() => {
    // 1. Close any modal <dialog> popups
    document.querySelectorAll('dialog').forEach(d => {
        try {
            const closeBtn = d.querySelector('button[data-close]');
            if (closeBtn) closeBtn.click();
            if (d.open) d.close();
            d.remove();
        } catch (e) {}
    });

    // 2. Unlock any range + checkbox access gates (Zugangsprüfung)
    document.querySelectorAll('section[aria-label="Zugangsprüfung"], [id$="-gate"]').forEach(sec => {
        try {
            const slider = sec.querySelector('input[type="range"]');
            if (slider) {
                slider.value = slider.max || '100';
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                slider.dispatchEvent(new Event('change', { bubbles: true }));
            }
            sec.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                if (cb.name !== 'acknowledged' && !cb.checked) {
                    cb.checked = true;
                    cb.dispatchEvent(new Event('input', { bubbles: true }));
                    cb.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        } catch (e) {}
    });

    // 3. Open all <details> elements
    document.querySelectorAll('details').forEach(d => {
        d.open = true;
    });

    // 4. Reveal all [role="tooltip"] elements so innerText includes them
    document.querySelectorAll('[role="tooltip"]').forEach(t => {
        t.style.setProperty('display', 'inline', 'important');
        t.style.setProperty('position', 'static', 'important');
        t.style.setProperty('visibility', 'visible', 'important');
        t.style.setProperty('opacity', '1', 'important');
        if (!t.dataset.prefixed) {
            t.dataset.prefixed = '1';
            t.insertAdjacentText('beforebegin', ' ');
            t.insertAdjacentText('afterend', ' ');
        }
    });

    // 5. Expose canvas[aria-label] as visible text while keeping [aria-hidden="true"] hidden
    document.querySelectorAll('canvas[aria-label]').forEach(c => {
        if (!c.dataset.unhidden) {
            c.dataset.unhidden = '1';
            const tag = document.createElement('div');
            tag.textContent = '[CANVAS: ' + c.getAttribute('aria-label') + ']';
            c.parentNode.insertBefore(tag, c);
        }
    });

    // 6. Expose time[datetime] UTC ISO attributes so innerText contains exact UTC timestamps
    document.querySelectorAll('time[datetime]').forEach(t => {
        if (!t.dataset.dtExposed) {
            t.dataset.dtExposed = '1';
            t.insertAdjacentText('beforeend', ' · ' + t.getAttribute('datetime'));
        }
    });
}
"""


async def prepare_page(page) -> None:
    """Close dialogs, unlock slider gates, open details, and expose tooltips & canvas aria-labels."""
    try:
        await page.evaluate(PREPARE_PAGE_JS)
    except Exception:
        pass


async def get_clean_text(page) -> str:
    """Prepare the page and return zero-width-stripped visible innerText."""
    await prepare_page(page)
    try:
        raw = await page.locator("body").inner_text(timeout=5000)
    except Exception:
        raw = await page.content()
    return strip_zwc(raw)


async def get_actionable_links(page, base_url: str) -> list[dict[str, str]]:
    """Return non-decoy visible links on the current page."""
    await prepare_page(page)
    raw_links = await page.evaluate(
        """() => {
        const out = [];
        document.querySelectorAll('a[href]').forEach(a => {
            if (a.hasAttribute('data-unavailable')) return;
            const href = a.getAttribute('href') || '';
            const text = (a.innerText || a.getAttribute('aria-label') || '').trim();
            out.push({ href, text });
        });
        return out;
    }"""
    )
    clean_links: list[dict[str, str]] = []
    seen = set()
    for item in raw_links:
        href = strip_zwc(item.get("href", "")).strip()
        text = strip_zwc(item.get("text", "")).strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if any(href.startswith(p) or href == p for p in DECOY_HREF_PATTERNS):
            continue
        full_url = urljoin(base_url, href)
        key = (full_url, text)
        if key not in seen:
            seen.add(key)
            clean_links.append({"url": full_url, "path": href, "text": text})
    return clean_links


async def handle_gates_and_notices(page, target_url: str) -> str:
    """Handle cookie consent, ERP /notice receipt gate, customer-portal document access gate, and 503 retries."""
    text = ""
    for _ in range(5):
        text = await get_clean_text(page)

        # 1. Cookie consent wall
        if "Cookies" in text:
            consent_btn = page.locator(
                'button[value="accept"], button:has-text("Cookies akzeptieren"), button:has-text("Auswahl bestätigen")'
            )
            if await consent_btn.count() > 0:
                await consent_btn.first.click()
                await page.wait_for_load_state("domcontentloaded")
                continue

        # 2. Transient error page ("Dienst vorübergehend nicht verfügbar")
        if "Dienst vorübergehend nicht verfügbar" in text or "Anfrage konnte nicht verarbeitet werden" in text:
            await asyncio.sleep(0.2)
            await page.goto(target_url, wait_until="domcontentloaded")
            continue

        # 3. ERP Systemmitteilung receipt gate on /notice
        if "Empfangsnummer" in text or "/notice" in page.url:
            erp_receipt = page.locator("canvas#erp-receipt")
            if await erp_receipt.count() > 0:
                label = strip_zwc(await erp_receipt.first.get_attribute("aria-label") or "")
                code = label.split(":", 1)[-1].strip() if ":" in label else label.strip()
                receipt_input = page.locator('input[name="receipt"]')
                if await receipt_input.count() > 0:
                    await receipt_input.first.fill(code)
                ack_cb = page.locator('input[name="acknowledged"]')
                if await ack_cb.count() > 0:
                    await ack_cb.first.check()
                submit_btn = page.locator('form[action="/notice"] button[type="submit"], button:has-text("Weiter")')
                if await submit_btn.count() > 0:
                    await submit_btn.first.click()
                    await page.wait_for_load_state("domcontentloaded")
                    if page.url.rstrip("/") != target_url.rstrip("/"):
                        await page.goto(target_url, wait_until="domcontentloaded")
                    continue

        # 4. Customer portal Dokumentenüberlassung gate
        if "Dokumentenüberlassung" in text or "Empfangszeichen" in text:
            access_receipt = page.locator("canvas#access-receipt")
            if await access_receipt.count() > 0:
                label = strip_zwc(await access_receipt.first.get_attribute("aria-label") or "")
                code = label.split(":", 1)[-1].strip() if ":" in label else label.strip()
                ref_radio = page.locator('input[name="purpose"][value="reference"]')
                if await ref_radio.count() > 0:
                    await ref_radio.first.check()
                receipt_input = page.locator('input[name="receipt"]')
                if await receipt_input.count() > 0:
                    await receipt_input.first.fill(code)
                ack_cb = page.locator('input[name="acknowledged"]')
                if await ack_cb.count() > 0:
                    await ack_cb.first.check()
                read_btn = page.locator('button[name="operation"][value="read"]')
                if await read_btn.count() > 0:
                    await read_btn.first.click()
                    await page.wait_for_load_state("domcontentloaded")
                    continue

        break
    return text


async def safe_goto(page, url: str) -> str:
    """Navigate to `url`, resolve any gates or transient error pages, and return clean page text."""
    for attempt in range(4):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            text = await handle_gates_and_notices(page, url)
            if "Dienst vorübergehend nicht verfügbar" in text and attempt < 3:
                await asyncio.sleep(0.25 * (attempt + 1))
                continue
            return text
        except Exception:
            if attempt == 3:
                raise
            await asyncio.sleep(0.25 * (attempt + 1))
    return await get_clean_text(page)


async def login_portal(page, site_access: dict[str, Any]) -> str:
    """Log into one of the portals using its access credentials and clear initial consent/notice gates."""
    base_url = site_access["url"].rstrip("/")
    creds = site_access.get("credentials") or {}
    username = creds.get("username", "")
    password = creds.get("password", "")

    await page.goto(base_url, wait_until="domcontentloaded", timeout=25000)
    await prepare_page(page)

    user_input = page.locator('input[name="username"]')
    if await user_input.count() > 0 and username:
        await user_input.first.fill(username)
        pwd_input = page.locator('input[name="password"]')
        if await pwd_input.count() > 0:
            await pwd_input.first.fill(password)
        login_btn = page.locator('form[action="/login"] button[type="submit"], button:has-text("Anmelden")')
        if await login_btn.count() > 0:
            await login_btn.first.click()
            await page.wait_for_load_state("domcontentloaded")

    await handle_gates_and_notices(page, base_url)
    return await get_clean_text(page)


async def paginate_pages(page, start_url: str, max_pages: int = 25) -> list[str]:
    """Visit `start_url` and follow 'Nächste Seite' links to collect clean text of all pages."""
    texts: list[str] = []
    current_url = start_url
    visited: set[str] = set()

    for _ in range(max_pages):
        if current_url in visited:
            break
        visited.add(current_url)
        text = await safe_goto(page, current_url)
        texts.append(text)

        # Look for Nächste Seite link
        next_href = await page.evaluate(
            """() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            for (const a of links) {
                const t = (a.innerText || '').replace(/[\\u200b\\u200c\\u200d\\ufeff\\u00ad]/g, '').trim();
                if (t === 'Nächste Seite' || t.includes('Nächste Seite') || t === 'Nächster Konditionssatz') {
                    return a.getAttribute('href');
                }
            }
            return null;
        }"""
        )
        if not next_href:
            break
        current_url = urljoin(current_url, strip_zwc(next_href))

    return texts


# ---------------------------------------------------------------------------
# Structured Extraction Parsers (Deterministic + Generalizable)
# ---------------------------------------------------------------------------

def parse_tender_positions_from_text(text: str) -> list[TenderPosition]:
    """Extract tender positions from CSV or table/block text on the tender portal."""
    positions: dict[str, TenderPosition] = {}
    cleaned = strip_zwc(text)

    # 1. CSV lines: Position;Kurztext;Menge;Einheit;Anforderung -> 01.01;...;24;Stk;A-1
    for line in cleaned.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) >= 5 and re.match(r"^\d{2}\.\d{2}$", parts[0]):
            pos_id, desc, qty_s, unit, req_ref = parts[0], parts[1], parts[2], parts[3], parts[4]
            try:
                positions[pos_id] = TenderPosition(
                    position=pos_id,
                    requirement_ref=req_ref,
                    original_quantity=int(parse_locale_decimal(qty_s)),
                    unit=unit,
                    description=desc,
                )
            except ValueError:
                pass

    # 2. Tabular or block lines: Position: 01.01 ... Menge: 24 Stk ... Anforderungsreferenz: A-1
    block_matches = re.finditer(
        r"Position:\s*(\d{2}\.\d{2}).*?Menge:\s*(\d+)\s*([A-Za-zÄÖÜäöüß]+).*?Anforderungsreferenz:\s*(A-\d+)",
        cleaned,
        re.DOTALL,
    )
    for m in block_matches:
        pos_id, qty_s, unit, req_ref = m.group(1), m.group(2), m.group(3), m.group(4)
        if pos_id not in positions:
            positions[pos_id] = TenderPosition(
                position=pos_id,
                requirement_ref=req_ref.strip(),
                original_quantity=int(qty_s),
                unit=unit.strip(),
            )

    # 3. Table rows: 01.01 \t ... \t 24 \t Stk \t A-1
    for line in cleaned.splitlines():
        m_row = re.search(
            r"\b(\d{2}\.\d{2})\b\s+([^\t\n]+?)\s+(\d+)\s+(Stk|Stück|Satz|ST)\s+(A-\d+)\b",
            line,
            re.IGNORECASE,
        )
        if m_row:
            pos_id, desc, qty_s, unit, req_ref = m_row.groups()
            if pos_id not in positions:
                positions[pos_id] = TenderPosition(
                    position=pos_id,
                    requirement_ref=req_ref.strip(),
                    original_quantity=int(qty_s),
                    unit=unit.strip(),
                    description=desc.strip(),
                )

    return sorted(positions.values(), key=lambda x: x.position)


def parse_qa_pages(qa_texts: list[str]) -> list[QAClarification]:
    """Parse paginated Q&A answers from the tender portal."""
    clarifications: list[QAClarification] = []
    seen_numbers: set[str] = set()

    for page_text in qa_texts:
        cleaned = strip_zwc(page_text)
        # Split by Q&A entry headers: "<number> \t Eingang ... \t"
        entries = re.split(r"(?m)^(?=\d{3,6}\s+Eingang)", cleaned)
        for entry in entries:
            m_head = re.match(
                r"^(\d{3,6})\s+Eingang\s*([^\t\n]*)\s*(.*)",
                entry.strip(),
                re.DOTALL,
            )
            if not m_head:
                continue
            q_num, date_part, body = m_head.groups()
            if q_num in seen_numbers:
                continue
            seen_numbers.add(q_num)

            ts = parse_timestamp(date_part) or parse_timestamp(body) or datetime(2027, 1, 1, tzinfo=timezone.utc)
            qa = QAClarification(number=q_num, timestamp=ts, text=body.strip())

            # 1. Check withdrawal: "Antwort auf Rückfrage NNNN wird ... zurückgezogen"
            m_with = re.search(
                r"(?:Rückfrage|Antwort|Frage)\s+(\d{3,6})\b[^\n.]*?(?:zurückgezogen|widerrufen|storniert|ungültig)",
                body,
                re.IGNORECASE,
            )
            if not m_with:
                m_with = re.search(
                    r"(?:zurückgezogen|widerrufen).*?(?:Rückfrage|Antwort|Frage)\s+(\d{3,6})\b",
                    body,
                    re.IGNORECASE,
                )
            if m_with:
                qa.withdrawn_number = m_with.group(1)

            # 2. Check quantity change (only if not a withdrawal notice)
            if not qa.withdrawn_number:
                # Look for canvas or prose quantity changes
                m_qty_canvas = re.search(
                    r"\[CANVAS:\s*Verbindliche Gesamtmenge:\s*Position\s*(\d{2}\.\d{2}):\s*(\d+)",
                    body,
                    re.IGNORECASE,
                )
                m_qty_prose = re.search(
                    r"Position\s*(\d{2}\.\d{2})\b[^\n.]*?(?:beträgt|nun|neu|Gesamtmenge|Menge)[^\d\n]*(\d+)\s*(Stück|Stk|Satz|ST)?",
                    body,
                    re.IGNORECASE,
                )
                if m_qty_canvas:
                    pos_id = m_qty_canvas.group(1)
                    qty_val = int(m_qty_canvas.group(2))
                    unit_val = m_qty_prose.group(3) if (m_qty_prose and m_qty_prose.group(3)) else ""
                    qa.quantity_changes.append((pos_id, qty_val, unit_val))
                elif m_qty_prose and ("menge" in body.lower() or "abrufmenge" in body.lower()):
                    pos_id = m_qty_prose.group(1)
                    qty_val = int(m_qty_prose.group(2))
                    unit_val = m_qty_prose.group(3) or ""
                    qa.quantity_changes.append((pos_id, qty_val, unit_val))

            # 3. Check scoped technical amendments: "Revision R-xxxx, Anforderung A-x: Hub/Stellweg = NNN mm"
            for m_amend in re.finditer(
                r"Revision\s+(R-\d+)\s*,\s*Anforderung\s+(A-\d+)\s*:\s*([^=:\n]+?)\s*[=:]\s*(\d+|\S+)",
                body,
                re.IGNORECASE,
            ):
                rev, req_ref, attr_name, attr_val = m_amend.groups()
                qa.tech_amendments.append((rev.strip(), req_ref.strip(), attr_name.strip(), attr_val.strip()))

            # 4. Check position assignments (Konditionsgruppe, Verpackungstarif, Terminschlüssel, Rüstpool, Bonusplan)
            pos_matches = re.findall(r"Position\s+(\d{2}\.\d{2})", body)
            target_pos = pos_matches[0] if pos_matches else None
            if target_pos:
                m_kg = re.search(r"Konditionsgruppe\s+(K-\d+)", body, re.IGNORECASE)
                if m_kg:
                    qa.condition_groups[target_pos] = m_kg.group(1)

                m_vp = re.search(r"Verpackungstarif\s+(VP-\d+)", body, re.IGNORECASE)
                if m_vp:
                    qa.packaging_tariffs[target_pos] = m_vp.group(1)

                m_tz = re.search(r"Terminschlüssel\s+(TZ-\d+)", body, re.IGNORECASE)
                if m_tz:
                    qa.delivery_commitments[target_pos] = m_tz.group(1)

                m_rp = re.search(r"Rüstpool\s+(RP-\d+)", body, re.IGNORECASE)
                if m_rp:
                    qa.setup_pools[target_pos] = m_rp.group(1)

                m_pb = re.search(r"Bonusplan\s+(PB-\d+)", body, re.IGNORECASE)
                if m_pb:
                    qa.bonus_plans[target_pos] = m_pb.group(1)

                # Ordinary setup fee: "Für Position 01.03 sind einmalig 85,00 EUR netto Rüstkosten anzusetzen"
                m_setup = re.search(
                    r"einmalig\s+([\d.,]+\s*(?:\((?:de-DE|en-US)\))?)\s*EUR\s*(?:netto\s*)?Rüstkosten",
                    body,
                    re.IGNORECASE,
                )
                if m_setup:
                    qa.ordinary_setup_fees[target_pos] = parse_locale_decimal(m_setup.group(1), "de-DE")

            clarifications.append(qa)

    return clarifications


def parse_spec_pages(spec_texts: list[str]) -> dict[str, RequirementSpec]:
    """Parse specification viewer pages into RequirementSpec objects."""
    reqs: dict[str, RequirementSpec] = {}
    for text in spec_texts:
        cleaned = strip_zwc(text)
        # Match requirement ID (A-1, A-2, etc.)
        m_req = re.search(r"\b(A-\d+)\b", cleaned)
        if not m_req:
            continue
        req_id = m_req.group(1)

        # Extract bore (from canvas or Originalwortlaut)
        bore = 0
        m_bore_canvas = re.search(r"Bohrung\s*\(mm\)\s*:\s*(\d+)", cleaned, re.IGNORECASE)
        m_bore_prose = re.search(r"Bohrung\s+(\d+)\s*mm", cleaned, re.IGNORECASE)
        if m_bore_canvas:
            bore = int(m_bore_canvas.group(1))
        elif m_bore_prose:
            bore = int(m_bore_prose.group(1))

        # Extract stroke
        stroke = 0
        m_stroke_prose = re.search(r"Hub\s+(\d+)\s*mm", cleaned, re.IGNORECASE)
        if m_stroke_prose:
            stroke = int(m_stroke_prose.group(1))
        else:
            m_stroke_col = re.search(r"\]\s*(\d+)\s*\((?:en-US|de-DE)\)", cleaned)
            if m_stroke_col:
                stroke = int(m_stroke_col.group(1))

        # Extract pressure
        pressure = 0
        m_press_prose = re.search(r"(?:Betriebsdruck|Druck)\s+(\d+)\s*bar", cleaned, re.IGNORECASE)
        if m_press_prose:
            pressure = int(m_press_prose.group(1))

        # Extract mounting
        mounting = ""
        m_mount = re.search(r"Befestigung\s+([A-Za-zÄÖÜäöüß\-]+?)(?:,|\.|;|\s+Zertifizierung)", cleaned)
        if m_mount:
            mounting = m_mount.group(1).strip()

        # Extract certification (prefer tooltip after Prüfvermerk, else prose)
        cert = "Keine"
        m_cert_tip = re.search(r"Prüfvermerk\s*(.+?)\s*siehe Freigabestand", cleaned, re.IGNORECASE)
        if m_cert_tip:
            c_raw = m_cert_tip.group(1).strip()
            cert = "Keine" if "keine" in c_raw.lower() else c_raw
        else:
            m_cert_prose = re.search(r"Zertifizierung\s+([^.,;\n]+)", cleaned, re.IGNORECASE)
            if m_cert_prose:
                c_raw = m_cert_prose.group(1).strip()
                cert = "Keine" if "keine" in c_raw.lower() else c_raw

        # Extract Kataloggruppe
        cat_group = ""
        m_cat = re.search(r"Kataloggruppe\s+(GR-\d+)", cleaned, re.IGNORECASE)
        if m_cat:
            cat_group = m_cat.group(1).strip()

        # Check nutzbarer Weg & Endreserve-Schlüssel
        is_usable = bool(re.search(r"nutzbarer\s+Weg", cleaned, re.IGNORECASE))
        end_res_key = None
        m_er = re.search(r"Endreserve-Schlüssel\s+(ER-\d+)", cleaned, re.IGNORECASE)
        if m_er:
            end_res_key = m_er.group(1).strip()

        # Check Satz conversion: "1 Satz = 5 Stück"
        pps = 1
        m_set = re.search(r"1\s*Satz\s*=\s*(\d+)\s*(?:Stück|Stk|ST)", cleaned, re.IGNORECASE)
        if m_set:
            pps = int(m_set.group(1))

        reqs[req_id] = RequirementSpec(
            req_id=req_id,
            bore_mm=bore,
            stroke_mm=stroke,
            pressure_bar=pressure,
            mounting=mounting,
            certification=cert,
            catalogue_group=cat_group,
            is_usable_stroke=is_usable,
            end_reserve_key=end_res_key,
            pieces_per_set=pps,
        )
    return reqs


def parse_erp_material(
    mat_no: str,
    basic_text: str,
    tech_text: str,
    plan_text: str,
    stock_text: str,
    vk_pages: list[str],
) -> ErpMaterial:
    """Parse all ERP views (MM03 basic/tech/planning, MMBE stock, VK13 conditions) into ErpMaterial."""
    b_clean = strip_zwc(basic_text)
    t_clean = strip_zwc(tech_text)
    p_clean = strip_zwc(plan_text)
    s_clean = strip_zwc(stock_text)
    combined_header = b_clean + "\n" + t_clean + "\n" + p_clean

    # Catalogue group
    m_cat = re.search(r"Kataloggruppe\s+(GR-\d+)", combined_header, re.IGNORECASE)
    cat_group = m_cat.group(1) if m_cat else ""

    # Packinhalt: "Packinhalt 11 Stück/Karton"
    m_pack = re.search(r"Packinhalt\s+(\d+)\s*Stück/Karton", combined_header, re.IGNORECASE)
    pack_size = int(m_pack.group(1)) if m_pack else 1

    # Umlagegewicht: "Umlagegewicht 3100 g/Stück"
    m_alloc = re.search(r"Umlagegewicht\s+([\d.,]+)\s*g/Stück", combined_header, re.IGNORECASE)
    alloc_weight = parse_locale_decimal(m_alloc.group(1)) if m_alloc else ZERO

    # Zuschlagsmasse: "Zuschlagsmasse 2125 g/Stück"
    m_sur = re.search(r"Zuschlagsmasse\s+([\d.,]+)\s*g/Stück", combined_header, re.IGNORECASE)
    sur_mass = parse_locale_decimal(m_sur.group(1)) if m_sur else ZERO

    # Preisindex: "Preisindex MET-xxxx"
    m_idx = re.search(r"Preisindex\s+(MET-\d+)", combined_header, re.IGNORECASE)
    price_idx = m_idx.group(1) if m_idx else None

    # Technical attributes (from MM03 technical tab or header description fallback)
    bore, stroke, pressure = 0, 0, 0
    mounting, cert = "", "Keine"

    m_bore = re.search(r"Bohrung\s+HYD_PRD\s+mm\s+(\d+)", t_clean)
    m_stroke = re.search(r"Hub\s+HYD_PRD\s+mm\s+(\d+)", t_clean)
    m_press = re.search(r"Betriebsdruck\s+HYD_PRD\s+bar\s+(\d+)", t_clean)
    m_mount = re.search(r"Befestigung\s+HYD_PRD\s+[—\-]\s+([^\n\t]+)", t_clean)
    m_cert = re.search(r"Zertifizierung\s*ⓘ\s*([^\n\t]+)", t_clean)

    # Also parse header description: "Hydraulikzylinder B/S, P bar, Mounting, Cert;"
    m_desc = re.search(
        r"Hydraulikzylinder\s+(\d+)/(\d+),\s*(\d+)\s*bar,\s*([^,;]+)(?:,\s*([^;]+))?;",
        combined_header,
    )
    if m_bore:
        bore = int(m_bore.group(1))
    elif m_desc:
        bore = int(m_desc.group(1))

    if m_stroke:
        stroke = int(m_stroke.group(1))
    elif m_desc:
        stroke = int(m_desc.group(2))

    if m_press:
        pressure = int(m_press.group(1))
    elif m_desc:
        pressure = int(m_desc.group(3))

    if m_mount:
        mounting = m_mount.group(1).strip()
    elif m_desc:
        mounting = m_desc.group(4).strip()

    if m_cert:
        cert = m_cert.group(1).strip()
    elif m_desc and m_desc.group(5):
        cert = m_desc.group(5).strip()

    # Planning tab: Materialstatus ("01" or "03"), Lieferzeit ab Lager, Produktionslieferzeit
    m_stat = re.search(r"Materialstatus\s*\n\s*(\d{2})\b", p_clean)
    status = m_stat.group(1) if m_stat else "01"

    m_stock_lead = re.search(r"Lieferzeit ab Lager:\s*(\d+)\s*Wochen", p_clean, re.IGNORECASE)
    stock_lead = int(m_stock_lead.group(1)) if m_stock_lead else 0

    m_prod_lead = re.search(r"Produktionslieferzeit:\s*(\d+)\s*Wochen", p_clean, re.IGNORECASE)
    prod_lead = int(m_prod_lead.group(1)) if m_prod_lead else 0

    # MMBE stock: prefer canvas "Verfügbarer Gesamtbestand: N Stück" or "Frei verwendbar \t N"
    free_stock = 0
    m_canvas_stock = re.search(r"Verfügbarer Gesamtbestand:\s*(\d+)\s*Stück", s_clean, re.IGNORECASE)
    m_row_stock = re.search(r"Frei verwendbar\s+(\d+)", s_clean, re.IGNORECASE)
    if m_canvas_stock:
        free_stock = int(m_canvas_stock.group(1))
    elif m_row_stock:
        free_stock = int(m_row_stock.group(1))

    # VK13 conditions
    conditions: list[PriceCondition] = []
    for vk_raw in vk_pages:
        vk_text = strip_zwc(vk_raw)
        m_from = re.search(r"Gültig von\s*\n\s*([^\n]+)", vk_text)
        m_to = re.search(r"Gültig bis\s*\n\s*([^\n]+)", vk_text)
        v_from = parse_timestamp(m_from.group(1)) if m_from else datetime(2020, 1, 1, tzinfo=timezone.utc)
        v_to = parse_timestamp(m_to.group(1)) if m_to else datetime(2030, 12, 31, tzinfo=timezone.utc)

        m_curr = re.search(r"Währung:\s*([A-Z]{3})(?:\s*·\s*Devisenschlüssel\s*(FX-\d+))?", vk_text)
        currency = m_curr.group(1) if m_curr else "EUR"
        fx_key = m_curr.group(2) if (m_curr and m_curr.group(2)) else None

        m_unit = re.search(
            r"Preiseinheit:\s*(\d+)\s*ST\s*·\s*Zahlenformat:\s*(de-DE|en-US)",
            vk_text,
            re.IGNORECASE,
        )
        price_unit = int(m_unit.group(1)) if m_unit else 1
        locale = m_unit.group(2) if m_unit else "de-DE"

        scales: list[tuple[int, Decimal]] = []
        # Match scale lines after "Staffel ab Menge (ST)"
        scale_section = vk_text.split("Nettopreis")[-1] if "Nettopreis" in vk_text else vk_text
        for line in scale_section.splitlines():
            m_sc = re.match(
                r"^\s*(\d+)\s*(?:\((?:de-DE|en-US)\))?\s+([\d.,]+\s*(?:\((?:de-DE|en-US)\))?)\s*$",
                line.strip(),
            )
            if m_sc:
                min_q = int(m_sc.group(1))
                p_val = parse_locale_decimal(m_sc.group(2), locale)
                scales.append((min_q, p_val))

        if scales:
            conditions.append(
                PriceCondition(
                    valid_from=v_from or datetime(2020, 1, 1, tzinfo=timezone.utc),
                    valid_to=v_to or datetime(2030, 12, 31, tzinfo=timezone.utc),
                    currency=currency,
                    fx_key=fx_key,
                    price_unit=price_unit,
                    locale=locale,
                    scales=scales,
                )
            )

    return ErpMaterial(
        material_number=mat_no,
        catalogue_group=cat_group,
        status=status,
        bore_mm=bore,
        stroke_mm=stroke,
        pressure_bar=pressure,
        mounting=mounting,
        certification=cert,
        pack_size=pack_size,
        allocation_weight_g=alloc_weight,
        surcharge_mass_g=sur_mass,
        price_index_key=price_idx,
        stock_lead_weeks=stock_lead,
        prod_lead_weeks=prod_lead,
        free_stock=free_stock,
        conditions=conditions,
    )


def parse_mail_messages_into_rules(
    messages: list[str],
    tender_reference: str,
    scenario_date: datetime,
    bidder_domain: str | None = None,
) -> MailRules:
    """Parse unlocked webmail messages and resolve latest valid records per authority & time rules."""
    rules = MailRules()

    # Collect structured message records: (timestamp, sender_local, sender_domain, subject, original_body)
    parsed_msgs: list[tuple[datetime, str, str, str, str]] = []

    for raw in messages:
        cleaned = strip_zwc(raw)
        # Extract header fields before "Lokale Vorschau"
        m_from = re.search(r"Von\s*\n\s*([^\s@\n]+)@([^\s\n]+)", cleaned)
        m_date = re.search(r"Datum\s*\n\s*([^\n]+)", cleaned)
        if not m_from or not m_date:
            continue
        sender_local = m_from.group(1).strip().lower()
        sender_dom = m_from.group(2).strip().lower()
        if bidder_domain and sender_dom != bidder_domain.lower() and "vergabe" not in sender_dom:
            continue

        msg_dt = parse_timestamp(m_date.group(1))
        if not msg_dt or msg_dt > scenario_date:
            # Future-dated messages never apply
            continue

        # Subject is the first non-chrome line
        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        subject = ""
        for ln in lines:
            if ln in ("←", "🔒", "↻") or ln.startswith("↓"):
                continue
            subject = ln
            break

        # Crucial: Only parse text AFTER "Original folgt" or "Nachrichtentext (Original)"
        # to ignore the decoy "Lokale Vorschau / nicht versandter Entwurf: Entwurfswert: 99 %"
        if "Original folgt" in cleaned:
            body = cleaned.split("Original folgt", 1)[1].strip()
        elif "Nachrichtentext (Original)" in cleaned:
            body = cleaned.split("Nachrichtentext (Original)", 1)[1].strip()
        else:
            body = cleaned

        # Check exact tender_reference match (must contain tender_reference NOT followed by -A, -B, etc.)
        exact_ref_pattern = re.compile(rf"\b{re.escape(tender_reference)}(?![-\w])")
        if not exact_ref_pattern.search(subject) and not exact_ref_pattern.search(body):
            continue

        parsed_msgs.append((msg_dt, sender_local, sender_dom, subject, body))

    # Sort chronologically (oldest first so newer records overwrite older ones)
    parsed_msgs.sort(key=lambda x: x[0])

    for msg_dt, sender_local, _sender_dom, subject, body in parsed_msgs:
        subj_lower = subject.lower()

        # 1. Sales director discount approval (leitung@)
        if sender_local == "leitung":
            # Ignore messages that explicitly say "keine Rabattfreigabe"
            if "keine rabattfreigabe" in body.lower():
                continue
            m_disc = re.search(r"genehmige\s+ich\s+(?:einen\s+\S+\s+von\s+)?([\d.,]+)\s*%", body, re.IGNORECASE)
            if m_disc:
                rules.discount_percent = parse_locale_decimal(m_disc.group(1), "de-DE")
                m_min = re.search(
                    r"mindestens\s+([\d.,]+)\s*EUR",
                    body,
                    re.IGNORECASE,
                )
                if m_min:
                    rules.discount_min_order_eur = parse_locale_decimal(m_min.group(1), "de-DE")
                else:
                    rules.discount_min_order_eur = ZERO

        # 2. Technikfreigabe (technik@) -> ER-xxxx: Revision R-xxxx; Endreserve N mm je Ende
        elif sender_local == "technik" and "technikfreigabe" in subj_lower:
            for m_er in re.finditer(
                r"(ER-\d+)\s*:\s*(?:Revision\s+(R-\d+)\s*;\s*)?Endreserve\s+(\d+)\s*mm",
                body,
                re.IGNORECASE,
            ):
                er_key, rev_id, mm_val = m_er.groups()
                rules.end_reserves[er_key] = (rev_id, int(mm_val))

        # 3. Verpackungstarife (logistik@) -> VP-xxxx: rate EUR je angefangenem Karton
        elif sender_local == "logistik" and "verpackungstarif" in subj_lower:
            loc = "en-US" if "dezimalpunkt" in body.lower() else "de-DE"
            for m_vp in re.finditer(r"(VP-\d+)\s*:\s*([\d.,]+)\s*EUR", body, re.IGNORECASE):
                vp_key, rate_s = m_vp.groups()
                rules.packaging_tariffs[vp_key] = parse_locale_decimal(rate_s, loc)

        # 4. Terminfreigabe (logistik@) -> TZ-xxxx: Artikel XX-xxxx; Zusage W Wochen bei höchstens M Stück
        elif sender_local == "logistik" and "terminfreigabe" in subj_lower:
            for m_tz in re.finditer(
                r"(TZ-\d+)\s*:\s*Artikel\s+([A-Z0-9\-]+)\s*;\s*Zusage\s+(\d+)\s*Wochen\s+bei\s+höchstens\s+(\d+)\s*Stück",
                body,
                re.IGNORECASE,
            ):
                tz_key, mat_no, weeks_s, max_q_s = m_tz.groups()
                rules.delivery_commitments[tz_key] = DeliveryCommitmentRule(
                    key=tz_key,
                    material_number=mat_no.strip(),
                    lead_weeks=int(weeks_s),
                    max_pooled_qty=int(max_q_s),
                )

        # 5. Devisenfixing (finanzen@) -> FX-xxxx: 1 USD = rate EUR
        elif sender_local == "finanzen" and "devisenfixing" in subj_lower:
            loc = "en-US" if "dezimalpunkt" in body.lower() else "de-DE"
            for m_fx in re.finditer(
                r"(FX-\d+)\s*:\s*1\s*[A-Z]{3}\s*=\s*([\d.,]+)\s*EUR",
                body,
                re.IGNORECASE,
            ):
                fx_key, rate_s = m_fx.groups()
                rules.fx_rates[fx_key] = parse_locale_decimal(rate_s, loc)

        # 6. Projektbonus (finanzen@) -> PB-xxxx: ... 0.00 bis 5000.00 EUR: 0%; ...
        elif sender_local == "finanzen" and "projektbonus" in subj_lower:
            loc = "en-US" if "dezimalpunkt" in body.lower() else "de-DE"
            for line in body.splitlines():
                m_pb = re.match(r"^\s*(PB-\d+)\s*:(.*)", line.strip())
                if not m_pb:
                    continue
                pb_key, pb_rest = m_pb.groups()
                bands: list[BonusBand] = []
                for m_band in re.finditer(
                    r"([\d.,]+)\s*bis\s*(unbegrenzt|[\d.,]+)\s*EUR\s*:\s*([\d.,]+)\s*%",
                    pb_rest,
                    re.IGNORECASE,
                ):
                    low_s, up_s, rate_s = m_band.groups()
                    low_val = parse_locale_decimal(low_s, loc)
                    up_val = None if "unbegrenzt" in up_s.lower() else parse_locale_decimal(up_s, loc)
                    rate_val = parse_locale_decimal(rate_s, loc)
                    bands.append(BonusBand(lower_eur=low_val, upper_eur=up_val, rate_percent=rate_val))
                if bands:
                    rules.bonus_plans[pb_key] = bands

        # 7. Rüstpools (kalkulation@) -> RP-xxxx: einmalig fee EUR
        elif sender_local == "kalkulation" and "rüstpool" in subj_lower:
            loc = "en-US" if "dezimalpunkt" in body.lower() else "de-DE"
            for m_rp in re.finditer(r"(RP-\d+)\s*:\s*einmalig\s+([\d.,]+)\s*EUR", body, re.IGNORECASE):
                rp_key, fee_s = m_rp.groups()
                rules.setup_pools[rp_key] = parse_locale_decimal(fee_s, loc)

        # 8. Konditionsregeln (kalkulation@) -> K-xxxx: prose describing base_only / base_and_surcharge / neither
        elif sender_local == "kalkulation" and "konditionsregeln" in subj_lower:
            for line in body.splitlines():
                m_k = re.match(r"^\s*(K-\d+)\s*:\s*(.+)$", line.strip())
                if not m_k:
                    continue
                k_key, clause_text = m_k.groups()
                cl_low = clause_text.lower()
                if "weder" in cl_low or "festpreis" in cl_low or "keine" in cl_low and "rabatt" in cl_low:
                    rules.condition_clauses[k_key] = "neither"
                elif (
                    "gemeinsam" in cl_low
                    or ("grundpreis und" in cl_low and "materialteuerung" in cl_low and "unkürz" not in cl_low and "ungekürz" not in cl_low)
                ):
                    rules.condition_clauses[k_key] = "base_and_surcharge"
                else:
                    rules.condition_clauses[k_key] = "base_only"

        # 9. Preisindizes (kalkulation@) -> MET-xxxx = rate EUR/kg (gültig DD.MM.YYYY bis DD.MM.YYYY)
        elif sender_local == "kalkulation" and "preisindizes" in subj_lower:
            loc = "en-US" if "dezimalpunkt" in body.lower() else "de-DE"
            scen_day = datetime(scenario_date.year, scenario_date.month, scenario_date.day, tzinfo=timezone.utc)
            # First check windowed entries: MET-xxxx = rate EUR/kg (gültig DD.MM.YYYY bis DD.MM.YYYY)
            matched_window_keys: set[str] = set()
            for m_win in re.finditer(
                r"(MET-\d+)\s*=\s*([\d.,]+)\s*EUR/kg\s*\(\s*gültig\s+(?:ab\s+)?(\d{2}\.\d{2}\.\d{4})(?:\s+bis\s+(\d{2}\.\d{2}\.\d{4}))?\s*\)",
                body,
                re.IGNORECASE,
            ):
                met_key, rate_s, d_from_s, d_to_s = m_win.groups()
                d_from = parse_timestamp(d_from_s)
                d_to = parse_timestamp(d_to_s) if d_to_s else datetime(2099, 12, 31, tzinfo=timezone.utc)
                if d_from and d_to and d_from <= scen_day <= d_to:
                    rules.metal_indices[met_key] = parse_locale_decimal(rate_s, loc)
                    matched_window_keys.add(met_key)

            # Fallback for non-windowed entries: MET-xxxx = rate EUR/kg
            for m_plain in re.finditer(r"(MET-\d+)\s*=\s*([\d.,]+)\s*EUR/kg", body, re.IGNORECASE):
                met_key, rate_s = m_plain.groups()
                if met_key not in matched_window_keys and f"{met_key} =" in body and "(gültig" not in body:
                    rules.metal_indices[met_key] = parse_locale_decimal(rate_s, loc)

    return rules


def parse_governing_revision(text: str, scenario_date: datetime) -> str | None:
    """Parse Revisionshistorie table text (with tooltips revealed) to find the governing current revision."""
    cleaned = strip_zwc(text)
    candidates: list[tuple[bool, datetime, str]] = []
    for line in cleaned.splitlines():
        m_rev = re.search(r"\bRevision\s+(R-\d+)\b", line, re.IGNORECASE)
        if not m_rev:
            continue
        rev_id = m_rev.group(1)
        low = line.lower()
        if "ersetzt" in low or "ungültig" in low or "zurückgezogen" in low or "entwurf" in low:
            continue
        dt = parse_timestamp(line) or datetime(2020, 1, 1, tzinfo=timezone.utc)
        if dt > scenario_date:
            continue
        is_explicit_valid = "gültig" in low or "aktuell" in low
        candidates.append((is_explicit_valid, dt, rev_id))

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[-1][2]

    # Fallback: any R-xxxx in text
    m_any = re.search(r"\b(R-\d+)\b", cleaned)
    return m_any.group(1) if m_any else None

