import unittest
from unittest.mock import patch
from app.camera import Device, resolve_device

class CameraTests(unittest.TestCase):
    @patch("app.camera.list_devices", return_value=[Device(0,"FaceTime HD Camera"),Device(2,"Logitech Webcam C925e")])
    def test_resolves_name(self, _):
        self.assertEqual(resolve_device({"camera":{"preferred_name":"Logitech Webcam C925e","device_index":None}}).index, 2)
    @patch("app.camera.list_devices", return_value=[Device(2,"Anything")])
    def test_configured_index_wins(self, _):
        self.assertEqual(resolve_device({"camera":{"preferred_name":"no", "device_index":2}}).name, "Anything")
