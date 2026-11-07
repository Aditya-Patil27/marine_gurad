import unittest

from app.api.aisstream import normalize


class StreamNormalizationTests(unittest.TestCase):
    def test_realistic_position_and_provider_time(self):
        event = {"MessageType": "PositionReport", "MetaData": {"MMSI": 123456789,
                 "ShipName": " TEST ", "time_utc": "2026-11-03T11:00:00+05:30"},
                 "Message": {"PositionReport": {"Latitude": 8.8, "Longitude": 78.9,
                 "Valid": True, "Sog": 102.3, "Cog": 360, "TrueHeading": 511}}}
        result = normalize(event)
        self.assertEqual(result["provider_received_at"], "2026-11-03T05:30:00+00:00")
        self.assertIsNone(result["speed_knots"])
        self.assertIsNone(result["course_degrees"])
        self.assertIsNone(result["heading_degrees"])
        self.assertEqual(result["name"], "TEST")

    def test_rejects_invalid_or_outside_position(self):
        event = {"MessageType": "PositionReport", "MetaData": {"MMSI": 123456789},
                 "Message": {"PositionReport": {"Latitude": 20, "Longitude": 78.9}}}
        self.assertIsNone(normalize(event))
        self.assertIsNone(normalize({"MessageType": "SubscriptionConfirmation"}))
