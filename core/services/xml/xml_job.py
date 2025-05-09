"""Download, parse, and delete XML files."""
from pathlib import Path
from typing import Any, Dict, Optional, List
import time
from datetime import datetime
from uuid import UUID
from logging import getLogger
from sqlalchemy.orm import Session
import httpx
import xmltodict
from models.models import (
    Invoices, Issuer, Item, Recipient, Companies
)
import asyncio

logger = getLogger(__name__)

TMP_DIR = Path("/tmp")
TMP_DIR.mkdir(exist_ok=True)


async def download_parse_delete(xml_url: str, db: Session):
    """
    Download an XML file to /tmp, parse it to a dict, delete the file.
    Returns the parsed data or None if parsing failed.
    """

    ts = int(time.time() * 1000)
    tmp_path = TMP_DIR / f"xml_{ts}.xml"

    try:
        logger.info("[XML_job] Downloading XML...")
        await _download_xml(xml_url, tmp_path)
        if not tmp_path.exists():
            logger.error("[XML_job] Failed to download XML")
            return None

        xml_str: Optional[str] = None
        for enc in ("utf-8", "latin-1", "utf-8-sig", "utf-16"):
            try:
                xml_str = tmp_path.read_text(encoding=enc)
                break
            except UnicodeDecodeError:
                logger.error(
                    "[XML_job] Failed to decode XML with %s encoding",
                    enc
                )
                continue

        if xml_str is None:
            raw = tmp_path.read_bytes()
            xml_str = raw.decode("utf-8", errors="replace")

        logger.info(
            "[XML_job] Cleaning invalid control chars (<0x20 except TAB/LF/CR)"
        )
        allowed = {"\t", "\n", "\r"}
        xml_str = "".join(
            ch for ch in xml_str if ch >= "\x20" or ch in allowed
        )

        logger.info("[XML_job] Parsing XML into dict...")
        try:
            data = xmltodict.parse(
                xml_str,
                process_namespaces=True,
                namespaces={
                    "http://www.sat.gob.gt/dte/fel/0.2.0": "dte",
                    "http://www.w3.org/2000/09/xmldsig#": "ds",
                },
                attr_prefix="@",
                cdata_key="#text",
            )
            if not data:
                logger.error("[XML_job] Empty XML data: %s", xml_url)
                return None

            invoice = await _invoice_builder(data, xml_url, db)
            if not invoice:
                logger.error(
                    "[XML_job] Failed to build invoice object: %s", xml_url
                )
                return None

            await _save_invoice(invoice, db)

            logger.info("[XML_job] Invoice object built successfully")

        except Exception as e:
            logger.error(
                "[XML_job] Failed to parse XML: %s", e
            )
            raise ValueError(
                f"[XML_job] Failed to parse XML: {e}"
            ) from e

    finally:
        logger.info("[XML_job] Deleting temp file %s", tmp_path)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error(
                "[XML_job] Failed to delete temp file %s: %s",
                tmp_path, e
            )
            raise e


async def _invoice_builder(
    data: Dict[str, Any],
    xml_id: str,
    db: Session
) -> Optional[Invoices]:
    """
    Build the invoice object using parsed XML data.
    """
    try:
        logger.info("[XML_job] Building invoice object...")

        issuer, recipient, items = await _build_issuer_recipient_items(data)
        company_id = await _get_companyid_by_nit(
            recipient.nit, db
        )
        if not company_id:
            logger.error(
                "[XML_job] Company ID not found for NIT %s",
                issuer.nit
            )
            return None

        invoice = await _build_invoice(
            data, xml_id, issuer, recipient, items, company_id
        )

        return invoice
    except Exception as e:
        logger.error(
            "[XML_job] Failed to build invoice object: %s", str(e)
        )
        raise ValueError(
            f"[XML_job] Failed to build invoice object: {e}"
        ) from e


async def _build_issuer_recipient_items(
    data: Dict[str, Any]
) -> tuple[Issuer, Recipient, List[Item]]:
    """
    Extract and build Issuer, Recipient, and Items objects from XML data.
    """
    dte = data["dte:GTDocumento"]["dte:SAT"]["dte:DTE"]
    issuance_data = dte["dte:DatosEmision"]

    # Build Issuer
    issuer_data = issuance_data.get("dte:Emisor", {})
    issuer = Issuer()
    issuer.nit = issuer_data.get("@NITEmisor", "")
    issuer.name = issuer_data.get("@NombreEmisor", "")
    issuer.commercial_name = issuer_data.get("@NombreComercial", "")
    issuer.establishment_code = issuer_data.get("@CodigoEstablecimiento", "")
    issuer.address = issuer_data.get(
        "dte:DireccionEmisor", {}).get("dte:Direccion", "")
    issuer.municipality = issuer_data.get(
        "dte:DireccionEmisor", {}).get("dte:Municipio", "")
    issuer.department = issuer_data.get(
        "dte:DireccionEmisor", {}).get("dte:Departamento", "")
    issuer.postal_code = issuer_data.get(
        "dte:DireccionEmisor", {}).get("dte:CodigoPostal", "")
    issuer.country = issuer_data.get(
        "dte:DireccionEmisor", {}).get("dte:Pais", "")

    # Build Recipient
    recipient_data = issuance_data.get("dte:Receptor", {})
    recipient = Recipient()
    recipient.nit = recipient_data.get("@IDReceptor", "")
    recipient.name = recipient_data.get("@NombreReceptor", "")
    recipient.email = recipient_data.get("@CorreoReceptor", "")

    # Build Items
    items = await _map_items(
        issuance_data.get("dte:Items", {}).get("dte:Item", [])
    )

    return issuer, recipient, items


async def _build_invoice(
    data: Dict[str, Any],
    xml_id: str,
    issuer: Issuer,
    recipient: Recipient,
    items: List[Item],
    company_id: UUID,
) -> Optional[Invoices]:
    """
    Build the Invoices object using extracted data.
    """
    dte = data["dte:GTDocumento"]["dte:SAT"]["dte:DTE"]
    issuance_data = dte["dte:DatosEmision"]
    general = issuance_data["dte:DatosGenerales"]
    certif = dte["dte:Certificacion"]
    autor = certif["dte:NumeroAutorizacion"]

    totales = issuance_data["dte:Totales"]
    iva = (
        totales.get("dte:TotalImpuestos", {})
               .get("dte:TotalImpuesto", {})
               .get("@TotalMontoImpuesto", "0")
    )

    invoice = Invoices()
    invoice.authorization_number = autor.get("#text", "")
    invoice.series = autor.get("@Serie", "")
    invoice.number = autor.get("@Numero", "")
    invoice.emission_date = datetime.fromisoformat(
        general["@FechaHoraEmision"].replace("T", " ").split(".")[0]
    )
    invoice.document_type = general.get("@Tipo", "")
    invoice.issuer = issuer
    invoice.recipient = recipient
    invoice.items = items
    invoice.total = float(totales["dte:GranTotal"])
    invoice.xml_url = xml_id
    invoice.currency = general.get("@CodigoMoneda", "GTQ")
    invoice.vat = float(iva)
    invoice.company_id = company_id

    return invoice


async def _map_items(items_raw: Any) -> List[Item]:
    if not isinstance(items_raw, list):
        items_raw = [items_raw]
    mapped: List[Item] = []
    for it in items_raw:
        taxs = it.get("dte:Impuestos", {}).get("dte:Impuesto", {})
        mapped.append(
            Item(
                line_number=int(it.get("@NumeroLinea", 0)),
                good_or_service=it.get("@BienOServicio", ""),
                quantity=float(it.get("dte:Cantidad", "0")),
                unit_of_measure=it.get("dte:UnidadMedida", ""),
                description=it.get("dte:Descripcion", ""),
                unit_price=float(it.get("dte:PrecioUnitario", "0")),
                price=float(it.get("dte:Precio", "0")),
                discount=float(it.get("dte:Descuento", "0")),
                total=float(it.get("dte:Total", "0")),
                taxes={
                        "nombre": taxs.get("dte:NombreCorto", ""),
                        "codigo": taxs.get("dte:CodigoUnidadGravable", ""),
                        "monto_gravable": float(
                            taxs.get("dte:MontoGravable", "0")
                        ),
                        "monto_impuesto": float(
                            taxs.get("dte:MontoImpuesto", "0")
                        ),
                    },
            )
        )
    return mapped


async def _save_invoice(
    invoice: Invoices,
    db: Session,
):
    try:
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
    except Exception as e:
        logger.error(
            "[XML_job] Failed to save invoice to database: %s", str(e)
        )
        raise


async def _get_companyid_by_nit(
    nit: str,
    db: Session,
) -> Optional[UUID]:
    try:
        company = db.query(Companies).filter(
            Companies.nit == nit
        ).first()
        if not company:
            logger.error(
                "[XML_job] Company with NIT %s not found", nit
            )
            return None
        return company.id

    except Exception as e:
        logger.error(
            "[XML_job] Failed to get company by NIT %s: %s", nit, str(e)
        )
        raise


async def _download_xml(
    xml_url: str,
    tmp_path: Path,
) -> Optional[bytes]:

    max_retries = 5
    retry_delay = 1
    logger.info("[XML_job] Downloading XML...")

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(xml_url, follow_redirects=True)
                r.raise_for_status()
                tmp_path.write_bytes(r.content)
            break
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(
                "[XML_job] Failed to download XML (attempt %d/%d): %s",
                attempt + 1, max_retries, str(e)
            )
            if attempt + 1 == max_retries:
                raise
            logger.info(
                "[XML_job] Retrying in %d seconds...", retry_delay
            )
            await asyncio.sleep(retry_delay)
            retry_delay += 1
    return None
