from orion_ahop.ingestion.ccsds_kvn import parse_kvn_text
from orion_ahop.validation import validate_message, propagation_path

def test_omm_kvn_parse_and_compatibility():
    text = """CCSDS_OMM_VERS = 2.0
META_START
OBJECT_NAME = SAMPLE
META_STOP
OBJECT_ID = 2026-001A
EPOCH = 2026-01-01T00:00:00.000
MEAN_ELEMENT_THEORY = SGP4
MEAN_MOTION = 15.0
ECCENTRICITY = 0.001
INCLINATION = 51.6
RA_OF_ASC_NODE = 10.0
ARG_OF_PERICENTER = 20.0
MEAN_ANOMALY = 30.0
"""
    message = parse_kvn_text(text)
    assert message.message_type == "OMM"
    assert validate_message(message) == []
    assert propagation_path(message) == "SGP4"
