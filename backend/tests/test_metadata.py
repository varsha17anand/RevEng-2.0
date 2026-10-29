"""Unit tests for metadata reading, writing, C2PA checking, and stripping."""

from PIL import Image
import numpy as np

from app.metadata import (
    embed_metadata,
    read_digital_source_type,
    has_c2pa_markers,
    strip_metadata,
    IPTC_TRAINED_ALGORITHMIC,
    IPTC_COMPOSITE_ALGORITHMIC,
    C2PA_BOX
)


def test_embed_and_read_xmp_metadata():
    """Verify IPTC DigitalSourceType embedding and extraction."""
    img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
    
    # Test trainedAlgorithmicMedia
    data_gen = embed_metadata(img, IPTC_TRAINED_ALGORITHMIC, output_format="PNG")
    assert read_digital_source_type(data_gen) == IPTC_TRAINED_ALGORITHMIC
    assert has_c2pa_markers(data_gen) is False

    # Test compositeWithTrainedAlgorithmicMedia
    data_edit = embed_metadata(img, IPTC_COMPOSITE_ALGORITHMIC, output_format="PNG")
    assert read_digital_source_type(data_edit) == IPTC_COMPOSITE_ALGORITHMIC


def test_strip_metadata():
    """Verify that strip_metadata completely strips XMP, IPTC, and C2PA markers."""
    import io
    from PIL.PngImagePlugin import PngInfo
    from app.metadata import PNG_CABX

    img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
    data_with_meta = embed_metadata(img, IPTC_TRAINED_ALGORITHMIC, output_format="PNG")
    
    # Verify metadata is present before stripping
    assert read_digital_source_type(data_with_meta) is not None

    # Strip metadata (screenshot simulation)
    stripped = strip_metadata(data_with_meta, output_format="PNG")
    
    # Verify metadata is gone
    assert read_digital_source_type(stripped) is None

    # Also verify that a PNG containing a real caBX chunk has it completely stripped
    info = PngInfo()
    info.add(PNG_CABX, b"test_c2pa_manifest_data")
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=info)
    c2pa_png = buf.getvalue()
    assert has_c2pa_markers(c2pa_png) is True

    stripped_c2pa = strip_metadata(c2pa_png, output_format="PNG")
    assert has_c2pa_markers(stripped_c2pa) is False
