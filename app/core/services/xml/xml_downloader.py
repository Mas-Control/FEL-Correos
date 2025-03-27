import os
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)


class XMLDownloader:
    @staticmethod
    def download_xml(url: str, client_nit: str) -> str:
        """
        Descarga el archivo XML y lo guarda temporalmente en /tmp.
        Se debe eliminar el archivo una vez procesado.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Use /tmp for Cloud Run's writable space
            base_dir = os.path.join("/tmp", client_nit)
            os.makedirs(base_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"factura_{timestamp}.xml"
            filepath = os.path.join(base_dir, filename)

            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info("XML descargado correctamente: %s", filepath)
            return filepath

        except Exception as e:
            logger.error("Error descargando XML: %s", e)
            raise
