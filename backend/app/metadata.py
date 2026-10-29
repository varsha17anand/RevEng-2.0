"""TruthLens Metadata and XMP / C2PA Inspector.

Reads and writes XMP DigitalSourceType per IPTC Photo Metadata Standard,
detects C2PA / JUMBF box markers in raw image byte streams, and performs
metadata stripping (simulating screenshot attacks).
"""

from __future__ import annotations

import io
from typing import Optional, Tuple
from PIL import Image

# IPTC standard DigitalSourceType URIs
IPTC_TRAINED_ALGORITHMIC = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
IPTC_COMPOSITE_ALGORITHMIC = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"

# Standard C2PA / JUMBF magic byte sequences
C2PA_BOX = b"c2pa"
JUMB_BOX = b"jumb"


def create_xmp_packet(digital_source_type: str, provenance_payload: Optional[str] = None) -> bytes:
    """Create a standard W3C RDF/XMP metadata packet containing IPTC DigitalSourceType.

    Args:
        digital_source_type: IPTC DigitalSourceType URI.
        provenance_payload: Optional serialized signed provenance manifest string.

    Returns:
        bytes: Raw XMP packet bytes formatted for JPEG APP1 / PNG iTXt.
    """
    prov_tag = f"\n      <truthlens:ProvenanceManifest>{provenance_payload}</truthlens:ProvenanceManifest>" if provenance_payload else ""
    xmp_str = f"""<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="TruthLens Engine 1.0">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"
        xmlns:truthlens="http://truthlens.security/xmp/1.0/">
      <Iptc4xmpExt:DigitalSourceType>{digital_source_type}</Iptc4xmpExt:DigitalSourceType>{prov_tag}
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
    return xmp_str.encode("utf-8")


def embed_metadata(
    image: Image.Image,
    digital_source_type: str,
    provenance_json_str: Optional[str] = None,
    output_format: str = "PNG",
    quality: int = 95
) -> bytes:
    """Embed IPTC XMP and provenance metadata into image bytes.

    Args:
        image: PIL Image to serialize.
        digital_source_type: IPTC DigitalSourceType URI.
        provenance_json_str: Optional signed provenance JSON string.
        output_format: "PNG" or "JPEG".
        quality: JPEG compression quality (1-100, default 95).

    Returns:
        bytes: Encoded image bytes containing XMP metadata.
    """
    xmp_bytes = create_xmp_packet(digital_source_type, provenance_json_str)
    buf = io.BytesIO()

    if output_format.upper() == "PNG":
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo()
        # Embed in standard PNG text chunks and XMP chunk
        info.add_itxt("XML:com.adobe.xmp", xmp_bytes.decode("utf-8", errors="ignore"))
        info.add_text("Iptc4xmpExt:DigitalSourceType", digital_source_type)
        if provenance_json_str:
            info.add_text("TruthLens:Provenance", provenance_json_str)
        # Also embed c2pa marker in text to simulate C2PA tool presence
        info.add_text("c2pa_manifest", "present")
        image.save(buf, format="PNG", pnginfo=info)
    else:
        # Save as JPEG with APP1 XMP marker
        # JPEG APP1 XMP header: b"http://ns.adobe.com/xap/1.0/\x00"
        xmp_header = b"http://ns.adobe.com/xap/1.0/\x00"
        app1_data = xmp_header + xmp_bytes
        image.save(buf, format="JPEG", quality=quality, exif=app1_data)

    return buf.getvalue()


def read_digital_source_type(image_bytes: bytes) -> Optional[str]:
    """Inspect raw image bytes for IPTC DigitalSourceType in XMP metadata.

    Args:
        image_bytes: Raw image file bytes.

    Returns:
        Optional[str]: Found DigitalSourceType URI or None.
    """
    # Check for direct IPTC strings in bytes (robust across PNG, JPEG, WEBP)
    if IPTC_TRAINED_ALGORITHMIC.encode("utf-8") in image_bytes:
        return IPTC_TRAINED_ALGORITHMIC
    if IPTC_COMPOSITE_ALGORITHMIC.encode("utf-8") in image_bytes:
        return IPTC_COMPOSITE_ALGORITHMIC

    # Check for keywords or namespaces
    if b"trainedAlgorithmicMedia" in image_bytes:
        return IPTC_TRAINED_ALGORITHMIC
    if b"compositeWithTrainedAlgorithmicMedia" in image_bytes:
        return IPTC_COMPOSITE_ALGORITHMIC

    return None


def has_c2pa_markers(image_bytes: bytes) -> bool:
    """Check if byte stream contains C2PA or JUMBF manifest markers.

    Args:
        image_bytes: Raw image file bytes.

    Returns:
        bool: True if C2PA or JUMBF signature is present.
    """
    return C2PA_BOX in image_bytes or JUMB_BOX in image_bytes


def extract_provenance_raw(image_bytes: bytes) -> Optional[str]:
    """Extract raw TruthLens signed provenance manifest from image bytes."""
    # Check if embedded in XML / text
    token = b"<truthlens:ProvenanceManifest>"
    end_token = b"</truthlens:ProvenanceManifest>"
    idx = image_bytes.find(token)
    if idx != -1:
        end_idx = image_bytes.find(end_token, idx)
        if end_idx != -1:
            raw = image_bytes[idx + len(token):end_idx].decode("utf-8", errors="ignore")
            return raw.strip()

    # Check PNG tEXt / iTXt chunk
    if b"TruthLens:Provenance\x00" in image_bytes:
        pos = image_bytes.find(b"TruthLens:Provenance\x00") + len(b"TruthLens:Provenance\x00")
        end_pos = image_bytes.find(b"\x00", pos)
        if end_pos == -1 or end_pos - pos > 10000:
            end_pos = pos + 4000
        return image_bytes[pos:end_pos].decode("utf-8", errors="ignore").strip()

    return None


def strip_metadata(image_bytes: bytes, output_format: str = "PNG") -> bytes:
    """Strip all metadata (EXIF, XMP, IPTC, C2PA) by decoding and re-encoding raw pixels.

    This precisely emulates a user taking a desktop screenshot or uploading
    via a social media platform that strips non-pixel metadata.

    Args:
        image_bytes: Original image bytes.
        output_format: Target format ("PNG" or "JPEG").

    Returns:
        bytes: Stripped image bytes containing only pure pixel data.
    """
    in_buf = io.BytesIO(image_bytes)
    img = Image.open(in_buf).convert("RGB")
    out_buf = io.BytesIO()
    # Save pure pixels with no extra info
    img.save(out_buf, format=output_format)
    return out_buf.getvalue()
